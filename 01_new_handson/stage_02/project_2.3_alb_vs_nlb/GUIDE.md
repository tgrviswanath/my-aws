# Project 2.3 — ALB vs NLB: Layer 7 vs Layer 4 Load Balancing

---

## 1. Overview

**Problem Statement**
Developers frequently choose a load balancer without understanding the performance and feature trade-offs between layer 4 and layer 7. Picking ALB for a TCP-only gaming server adds unnecessary latency; picking NLB for a microservices HTTP API misses out on intelligent routing.

**What You'll Learn**
- How ALB (Application Load Balancer) routes HTTP/HTTPS traffic using content-based rules
- How NLB (Network Load Balancer) routes raw TCP/UDP traffic with ultra-low latency and static IP
- Path-based routing: `/api/*` → api-tg, `/web/*` → web-tg
- When each load balancer type is the right tool for the job

**Objectives**
1. Create an ALB with two target groups and path-based listener rules
2. Create an NLB with a TCP listener for comparison
3. Run load tests and compare latency characteristics
4. Understand sticky sessions, connection draining, and health check behavior per LB type

---

## 2. Architecture

```
Internet
    │
    ▼
┌─────────────────────────────────────┐
│  Application Load Balancer (L7)     │
│  Listener: HTTP :80                 │
│  Rule 1: /api/* → api-tg (:8080)   │
│  Rule 2: /web/* → web-tg (:80)     │
│  Default: web-tg                    │
└────────────┬────────────────────────┘
             │
     ┌───────┴────────┐
     ▼                ▼
┌─────────┐      ┌─────────┐
│  web-tg  │      │  api-tg │
│ EC2 :80  │      │ EC2:8080│
└─────────┘      └─────────┘

Internet (gaming / raw TCP)
    │
    ▼
┌─────────────────────────┐
│  Network Load Balancer  │
│  Listener: TCP :443     │
│  Static Elastic IP      │
│  Target Group: TCP :443 │
└────────────┬────────────┘
             ▼
         ┌─────────┐
         │  EC2    │
         │ TCP app │
         └─────────┘
```

**Key Differences**
- ALB terminates HTTP, inspects headers/path/host, adds `X-Forwarded-For`
- NLB passes raw TCP bytes — the target sees the original client IP (with Proxy Protocol or VPC flow logs)
- NLB supports Elastic IP addresses (static IP) — useful for firewall allowlisting
- ALB supports WebSocket, HTTP/2, gRPC, mutual TLS, authentication via Cognito/OIDC

---

## 3. Prerequisites

**AWS Account & Permissions**
- IAM permissions: `elasticloadbalancing:*`, `ec2:*`, `iam:PassRole`
- AWS CLI configured: `aws configure` with `us-east-1` as default region

**Infrastructure Requirements**
- VPC from Project 2.1 with at least 2 public subnets in different AZs (us-east-1a, us-east-1b)
- Security group allowing inbound HTTP (80) and custom TCP (8080) from 0.0.0.0/0
- 2 EC2 instances running (one serving `/web`, one serving `/api`) — can be t2.micro (Free Tier)
- Both EC2 instances must be running a web server (e.g., `python3 -m http.server 80`)

**Quick EC2 Check**
```bash
aws ec2 describe-instances \
  --filters "Name=instance-state-name,Values=running" \
  --query "Reservations[].Instances[].{ID:InstanceId,IP:PublicIpAddress,AZ:Placement.AvailabilityZone}" \
  --output table
```

---

## 4. Folder Structure

```
project_2.3_alb_vs_nlb/
├── GUIDE.md                    # This file
├── steps_awsconsoleui.md       # Console walkthrough with screenshots
├── cost_estimate.md            # ALB/NLB pricing breakdown
├── scripts/
│   ├── create_alb.sh           # CLI script: ALB + target groups + listener rules
│   ├── create_nlb.sh           # CLI script: NLB + target group + TCP listener
│   ├── test_routing.sh         # curl commands to verify path routing
│   └── cleanup.sh              # Delete all load balancer resources
├── configs/
│   ├── alb_listener_rules.json # Path-condition rule definitions
│   └── target_group_attrs.json # Stickiness, deregistration delay settings
└── userdata/
    ├── web_server.sh           # EC2 userdata: simple web server on port 80
    └── api_server.sh           # EC2 userdata: simple API server on port 8080
```

---

## 5. Implementation

### 5A. Console Walkthrough

#### Prerequisites Check
Before starting, verify:
- [ ] You are in `us-east-1` (check top-right of console)
- [ ] EC2 → Instances shows at least 2 running instances
- [ ] VPC → Subnets shows subnets in 2 different AZs
- [ ] IAM → Your user has `elasticloadbalancing:*` permissions

#### Decision Point 1: Which Load Balancer for Your Use Case?

| Use Case | Recommended LB | Reason |
|---|---|---|
| HTTP/HTTPS microservices routing | ✅ ALB | Path/host/header routing rules |
| REST API with path-based routing | ✅ ALB | Rule-based target selection |
| Gaming server (UDP/TCP) | ✅ NLB | Ultra-low latency, no HTTP overhead |
| Real-time streaming (raw TCP) | ✅ NLB | Passes TCP bytes unchanged |
| Need static IP for firewall rules | ✅ NLB | Supports Elastic IP assignment |
| gRPC / WebSocket | ✅ ALB | Native protocol support |
| Network appliance (firewall, IDS) | ✅ Gateway LB | Transparent bump-in-the-wire |
| Lambda as backend | ✅ ALB | ALB supports Lambda target type |

**Create ALB via Console**
1. Navigate to EC2 → Load Balancers → Create Load Balancer
2. Choose "Application Load Balancer" → Create
3. Name: `alb-lab-23`
4. Scheme: Internet-facing
5. IP address type: IPv4
6. Network mapping: select your VPC, check subnets in us-east-1a AND us-east-1b
7. Security groups: select your lab security group (port 80 open)
8. Listener: HTTP:80 (leave default for now)
9. Default action: Forward to → Create target group (follow below)

**Create Target Groups**
1. Target group 1: `web-tg`
   - Target type: Instances
   - Protocol: HTTP, Port: 80
   - Health check path: `/`
   - Register your web EC2 instance
2. Target group 2: `api-tg`
   - Target type: Instances
   - Protocol: HTTP, Port: 8080
   - Health check path: `/health`
   - Register your API EC2 instance

**Create Listener Rules (Path Routing)**
1. Listeners tab → View/edit rules
2. Add rule:
   - IF Path is `/api/*` → Forward to `api-tg`
   - Priority: 10
3. Add rule:
   - IF Path is `/web/*` → Forward to `web-tg`
   - Priority: 20
4. Default rule: Forward to `web-tg`

**Expected Outcome**
- ALB DNS name is shown: `alb-lab-23-xxxxxxxx.us-east-1.elb.amazonaws.com`
- State: Active (may take 1-3 minutes to provision)
- Both target groups show healthy targets (green checkmarks)
- Curl to `/api/anything` routes to port 8080 on EC2; `/web/page` routes to port 80

**Troubleshooting**
- `502 Bad Gateway`: Target is unhealthy. Check EC2 security group allows the LB's SG on ports 80/8080.
- `504 Gateway Timeout`: EC2 web server not running. SSH in and run `python3 -m http.server 80`.
- Targets stay "unhealthy": Health check path must return HTTP 200. Adjust health check path or success codes.
- ALB not routing to correct target: Verify rule priorities — lower priority number = evaluated first.

---

### 5B. CLI Implementation

```bash
# --- Variables ---
VPC_ID="vpc-xxxxxxxxx"           # Replace with your VPC ID from project 2.1
SUBNET_1="subnet-xxxxxxxx"       # us-east-1a subnet
SUBNET_2="subnet-yyyyyyyy"       # us-east-1b subnet
SG_ID="sg-xxxxxxxx"              # Security group ID
WEB_EC2_ID="i-xxxxxxxxx"         # Web server instance
API_EC2_ID="i-yyyyyyyyy"         # API server instance
REGION="us-east-1"

# --- Create ALB ---
ALB_ARN=$(aws elbv2 create-load-balancer \
  --name alb-lab-23 \
  --subnets ${SUBNET_1} ${SUBNET_2} \
  --security-groups ${SG_ID} \
  --scheme internet-facing \
  --type application \
  --ip-address-type ipv4 \
  --query "LoadBalancers[0].LoadBalancerArn" \
  --output text)
echo "ALB ARN: ${ALB_ARN}"

# Wait for ALB to become active
aws elbv2 wait load-balancer-available --load-balancer-arns ${ALB_ARN}
echo "ALB is active"

# --- Create Target Groups ---
WEB_TG_ARN=$(aws elbv2 create-target-group \
  --name web-tg \
  --protocol HTTP \
  --port 80 \
  --vpc-id ${VPC_ID} \
  --health-check-path "/" \
  --health-check-interval-seconds 30 \
  --healthy-threshold-count 2 \
  --query "TargetGroups[0].TargetGroupArn" \
  --output text)
echo "Web TG ARN: ${WEB_TG_ARN}"

API_TG_ARN=$(aws elbv2 create-target-group \
  --name api-tg \
  --protocol HTTP \
  --port 8080 \
  --vpc-id ${VPC_ID} \
  --health-check-path "/health" \
  --health-check-interval-seconds 30 \
  --healthy-threshold-count 2 \
  --query "TargetGroups[0].TargetGroupArn" \
  --output text)
echo "API TG ARN: ${API_TG_ARN}"

# --- Register Instances in Target Groups ---
aws elbv2 register-targets \
  --target-group-arn ${WEB_TG_ARN} \
  --targets Id=${WEB_EC2_ID},Port=80

aws elbv2 register-targets \
  --target-group-arn ${API_TG_ARN} \
  --targets Id=${API_EC2_ID},Port=8080

# --- Create ALB Listener (default → web-tg) ---
LISTENER_ARN=$(aws elbv2 create-listener \
  --load-balancer-arn ${ALB_ARN} \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=${WEB_TG_ARN} \
  --query "Listeners[0].ListenerArn" \
  --output text)
echo "Listener ARN: ${LISTENER_ARN}"

# --- Create Path-Based Routing Rules ---
# Rule 1: /api/* → api-tg (priority 10)
aws elbv2 create-rule \
  --listener-arn ${LISTENER_ARN} \
  --priority 10 \
  --conditions '[{"Field":"path-pattern","Values":["/api/*"]}]' \
  --actions "[{\"Type\":\"forward\",\"TargetGroupArn\":\"${API_TG_ARN}\"}]"

# Rule 2: /web/* → web-tg (priority 20)
aws elbv2 create-rule \
  --listener-arn ${LISTENER_ARN} \
  --priority 20 \
  --conditions '[{"Field":"path-pattern","Values":["/web/*"]}]' \
  --actions "[{\"Type\":\"forward\",\"TargetGroupArn\":\"${WEB_TG_ARN}\"}]"

echo "ALB path routing rules created"

# --- Create NLB ---
NLB_ARN=$(aws elbv2 create-load-balancer \
  --name nlb-lab-23 \
  --subnets ${SUBNET_1} ${SUBNET_2} \
  --scheme internet-facing \
  --type network \
  --ip-address-type ipv4 \
  --query "LoadBalancers[0].LoadBalancerArn" \
  --output text)
echo "NLB ARN: ${NLB_ARN}"

# NLB Target Group (TCP)
NLB_TG_ARN=$(aws elbv2 create-target-group \
  --name nlb-tcp-tg \
  --protocol TCP \
  --port 443 \
  --vpc-id ${VPC_ID} \
  --query "TargetGroups[0].TargetGroupArn" \
  --output text)

# NLB TCP Listener
aws elbv2 create-listener \
  --load-balancer-arn ${NLB_ARN} \
  --protocol TCP \
  --port 443 \
  --default-actions Type=forward,TargetGroupArn=${NLB_TG_ARN}

echo "NLB with TCP listener created"
```

---

## 6. Code Deep Dive

### Listener Rule JSON Structure
```json
{
  "Field": "path-pattern",
  "PathPatternConfig": {
    "Values": ["/api/*"]
  }
}
```

### Other Condition Types Available in ALB Rules
```json
{ "Field": "host-header", "Values": ["api.example.com"] }
{ "Field": "http-header", "HttpHeaderConfig": { "HttpHeaderName": "X-Tenant", "Values": ["premium"] } }
{ "Field": "http-request-method", "Values": ["POST", "PUT"] }
{ "Field": "query-string", "Values": [{"Key": "version", "Value": "v2"}] }
{ "Field": "source-ip", "Values": ["203.0.113.0/24"] }
```

### Priority Numbers
- Rules are evaluated lowest number first (priority 1 wins over priority 100)
- Default rule has no priority number — always evaluated last
- Gap your priorities (10, 20, 30) to allow inserting new rules without renumbering

---

## 7. Verification

```bash
# Get ALB DNS name
ALB_DNS=$(aws elbv2 describe-load-balancers \
  --names alb-lab-23 \
  --query "LoadBalancers[0].DNSName" \
  --output text)
echo "ALB DNS: ${ALB_DNS}"

# Check listener rules
aws elbv2 describe-rules \
  --listener-arn ${LISTENER_ARN} \
  --query "Rules[].{Priority:Priority,Conditions:Conditions[0].Values,Actions:Actions[0].TargetGroupArn}" \
  --output table

# Test path routing
echo "Testing /api route:"
curl -s -o /dev/null -w "Status: %{http_code}, Routed via: ALB rule 1\n" http://${ALB_DNS}/api/test

echo "Testing /web route:"
curl -s -o /dev/null -w "Status: %{http_code}, Routed via: ALB rule 2\n" http://${ALB_DNS}/web/index

# Check target health
aws elbv2 describe-target-health --target-group-arn ${WEB_TG_ARN} \
  --query "TargetHealthDescriptions[].{Target:Target.Id,State:TargetHealth.State}" \
  --output table

aws elbv2 describe-target-health --target-group-arn ${API_TG_ARN} \
  --query "TargetHealthDescriptions[].{Target:Target.Id,State:TargetHealth.State}" \
  --output table
```

---

## 8. Observations

**ALB Characteristics**
| Feature | ALB Behavior |
|---|---|
| Latency | ~1-5ms added (HTTP parsing overhead) |
| Sticky Sessions | Cookie-based (AWSALB cookie, 1 day default) |
| Connection Draining | Deregistration delay 300s by default |
| Request Tracing | `X-Amzn-Trace-Id` header added |
| Max Rules per Listener | 100 |
| SSL Termination | Yes — certificate on ALB, HTTP to backend |

**NLB Characteristics**
| Feature | NLB Behavior |
|---|---|
| Latency | ~100μs (microseconds) — ultra low |
| Sticky Sessions | Source IP-based (flow hash) |
| Connection Draining | Same deregistration delay feature |
| Static IP | Yes — assign Elastic IP per AZ |
| TLS Termination | Optional TLS listener (can pass-through) |
| Preserve Client IP | Yes — client IP seen by targets |

---

## 9. Screenshots

Take screenshots at these points for your lab notes:
1. ALB creation form with subnets in 2 AZs selected
2. Target group registration showing healthy instance
3. Listener rules list showing path-pattern priorities 10 and 20
4. `curl` output in terminal showing correct routing behavior
5. NLB detail page showing Elastic IP assignment per AZ
6. CloudWatch metrics: RequestCount and TargetResponseTime for ALB

---

## 10. Cleanup

Delete resources in this order (dependencies must be removed first):

```bash
# Step 1: Delete Listener Rules (before deleting listener)
RULES=$(aws elbv2 describe-rules --listener-arn ${LISTENER_ARN} \
  --query "Rules[?Priority!='default'].RuleArn" --output text)
for RULE in ${RULES}; do
  aws elbv2 delete-rule --rule-arn ${RULE}
done

# Step 2: Delete Listeners
aws elbv2 delete-listener --listener-arn ${LISTENER_ARN}

# Step 3: Delete Load Balancers
aws elbv2 delete-load-balancer --load-balancer-arn ${ALB_ARN}
aws elbv2 delete-load-balancer --load-balancer-arn ${NLB_ARN}

# Wait for LBs to be deleted before deleting target groups
aws elbv2 wait load-balancers-deleted --load-balancer-arns ${ALB_ARN} ${NLB_ARN}

# Step 4: Delete Target Groups
aws elbv2 delete-target-group --target-group-arn ${WEB_TG_ARN}
aws elbv2 delete-target-group --target-group-arn ${API_TG_ARN}
aws elbv2 delete-target-group --target-group-arn ${NLB_TG_ARN}

echo "All load balancer resources deleted"

# Verify cleanup
aws elbv2 describe-load-balancers --query "LoadBalancers[?starts_with(LoadBalancerName,'alb-lab') || starts_with(LoadBalancerName,'nlb-lab')]" --output text
```
