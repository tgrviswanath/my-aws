# Console UI Guide — Project 2.3: ALB vs NLB

> This guide walks through each step in the AWS Management Console with decision points, screenshot markers, and troubleshooting for every action.

---

## Prerequisites Check

Before opening the console, confirm all of the following:

| Check | How to Verify | Required Value |
|---|---|---|
| AWS Region | Top-right corner of console | `US East (N. Virginia) us-east-1` |
| EC2 instances running | EC2 → Instances | At least 2 instances, state = "running" |
| Instances in different AZs | EC2 → Instances → Availability Zone column | us-east-1a AND us-east-1b |
| VPC with 2+ public subnets | VPC → Subnets | Subnets in 2 different AZs |
| Security group open on port 80 | EC2 → Security Groups → Inbound rules | 0.0.0.0/0 on TCP 80 |
| ELB permissions | IAM → Your user → Permissions | `elasticloadbalancing:*` policy |

> ⚠️ Do not proceed until all checks pass. A missing subnet in a second AZ is the most common blocker — ALB requires at least 2 AZs.

---

## Step 1 — Create Application Load Balancer (ALB)

### Decision Point 1: ALB vs NLB vs Gateway LB — Which to Create First?

| Load Balancer | Layer | Best For | Create in this step? |
|---|---|---|---|
| ✅ Application LB (ALB) | L7 (HTTP/HTTPS) | Microservices, path routing, gRPC, WebSockets | ✅ Yes — Step 1 |
| Network LB (NLB) | L4 (TCP/UDP) | Gaming, streaming, static IP, ultra-low latency | Step 3 |
| Gateway LB | L3/L4 | Network appliances (firewalls, intrusion detection) | Out of scope |

**Navigate:** EC2 → Load Balancers (left sidebar under "Load Balancing") → Create Load Balancer

1. Click "Application Load Balancer" → **Create**
2. **Load balancer name:** `alb-lab-23`
3. **Scheme:** Internet-facing *(makes it publicly accessible)*
4. **IP address type:** IPv4
5. **Network mapping:**
   - VPC: select your lab VPC
   - Mappings: check boxes for `us-east-1a` and `us-east-1b`
   - Select one subnet per AZ
6. **Security groups:** Remove default, add your lab security group (port 80 allowed)
7. **Listeners and routing:** Protocol HTTP, Port 80

> Do NOT click "Create" yet — first create target groups in the next section.

### 📸 Screenshot
> Take a screenshot of the load balancer creation form showing:
> - Name: `alb-lab-23`
> - Both AZ checkboxes selected (us-east-1a, us-east-1b)
> - Security group attached
> Label it: `01_alb_creation_form.png`

### Expected Outcome
After clicking Create:
- ALB appears in load balancers list with State: "Provisioning" → changes to "Active" in 1–3 minutes
- DNS name assigned: `alb-lab-23-xxxxxxxx.us-east-1.elb.amazonaws.com`
- No targets yet (we'll add them in Step 2)

### Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| "At least 2 subnets must be selected" | Only 1 AZ mapped | Map subnets in both us-east-1a and us-east-1b |
| "Security group not found" | Wrong VPC selected | Ensure SG and VPC match |
| ALB stays "Provisioning" > 5 min | Service issue or subnet ACL blocking | Check subnet's NACL allows outbound traffic |

---

## Step 2 — Create Target Groups and Listener Rules

### Decision Point 2: Target Group Type and Routing Logic

| Routing Type | Console Setting | Use Case |
|---|---|---|
| ✅ Path-based | "Path is /api/*" condition | Microservices with URL namespacing |
| Host-based | "Host header is api.example.com" | Multi-tenant, subdomain routing |
| Header-based | "HTTP header X-Version is v2" | A/B testing, feature flags |
| Query string | "Query string version=2" | API versioning |
| IP source | "Source IP is 10.0.0.0/8" | Internal vs external traffic |

**Create web-tg (Target Group 1)**
1. EC2 → Target Groups → Create target group
2. **Target type:** Instances
3. **Target group name:** `web-tg`
4. **Protocol:** HTTP, **Port:** 80
5. **VPC:** your lab VPC
6. **Health check protocol:** HTTP
7. **Health check path:** `/`
8. **Healthy threshold:** 2, **Interval:** 30 seconds
9. Click Next → Register targets
10. Select your "web" EC2 instance → Include as pending
11. Click Create target group

**Create api-tg (Target Group 2)**
1. Repeat above with:
   - **Name:** `api-tg`
   - **Port:** 8080
   - **Health check path:** `/health`
   - Register your "API" EC2 instance on port 8080

**Attach Default Action to ALB**
1. Go back to your ALB → Listeners tab
2. Edit the HTTP:80 listener
3. Default action: Forward to `web-tg`
4. Save

**Add Path Routing Rules**
1. Listeners tab → Click "View/edit rules" (pencil icon)
2. Click "+" (Insert Rule) icon
3. Rule 1:
   - **IF** → Add condition → Path → `/api/*`
   - **THEN** → Forward to → `api-tg`
   - **Priority:** 10
4. Rule 2:
   - **IF** → Add condition → Path → `/web/*`
   - **THEN** → Forward to → `web-tg`
   - **Priority:** 20
5. Save rules

### 📸 Screenshot
> Take a screenshot of the listener rules list showing:
> - Priority 10: Path `/api/*` → api-tg
> - Priority 20: Path `/web/*` → web-tg
> - Default: web-tg
> Label it: `02_listener_rules_path_routing.png`

### Expected Outcome
- Both target groups show "healthy" next to registered instances
- Rules appear in priority order in the listener rules list
- A `curl http://ALB_DNS/api/test` returns response from port 8080 backend
- A `curl http://ALB_DNS/web/page` returns response from port 80 backend

### Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Target shows "unhealthy" | Health check failing | SSH to EC2 and verify `curl localhost/health` returns 200 |
| 502 Bad Gateway | Target not running | Confirm web server running: `ps aux | grep python` |
| Requests all going to web-tg | Rule priority wrong or path not matching | Verify request URL exactly matches `/api/` prefix |
| "Target group in use" error | Deleting before detaching | Remove from listener first, then delete target group |

---

## Step 3 — Create NLB for Comparison

### Decision Point 3: NLB Static IP via Elastic IP

| Feature | Without Elastic IP | With Elastic IP |
|---|---|---|
| IP address | AWS-assigned, changes on re-creation | ✅ Fixed, deterministic IP address |
| Firewall allowlisting | Must update rules when LB recreated | Set-and-forget IP in firewall rules |
| Cost | $0 for NLB IP | $0.005/hr per Elastic IP |
| Assignment method | Automatic | Allocate EIP first, assign during NLB creation |

> **For this lab:** Use automatic IP (no Elastic IP needed). In production TCP apps where clients hardcode IPs or you use firewall allowlists, assign Elastic IP.

**Navigate:** EC2 → Load Balancers → Create Load Balancer → Network Load Balancer → Create

1. **Name:** `nlb-lab-23`
2. **Scheme:** Internet-facing
3. **IP address type:** IPv4
4. **Network mapping:** Select both subnets (same as ALB)
5. **Listeners:**
   - Protocol: TCP
   - Port: 443
6. **Default action:** Create target group (new tab)
   - Name: `nlb-tcp-tg`
   - Protocol: TCP, Port: 443
   - Target type: Instances
   - Register same EC2 instance(s)
7. Return to NLB creation, select `nlb-tcp-tg` as default action
8. Click Create load balancer

### 📸 Screenshot
> Take a screenshot of the NLB creation confirmation showing:
> - Type: Network
> - Availability Zones with assigned IPs
> - TCP:443 listener
> Label it: `03_nlb_creation_complete.png`

### Expected Outcome
- NLB State: Active (NLBs typically provision faster than ALBs — ~60 seconds)
- No security group shown (NLBs do not use security groups — traffic controlled by NACL and EC2 SG)
- Each AZ shows an assigned IP address

### Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| NLB targets always "unhealthy" | EC2 SG doesn't allow NLB subnet IP range | Add inbound rule on EC2 SG for VPC CIDR on port 443 |
| Cannot connect to NLB on TCP:443 | No service listening on EC2 port 443 | Start a TCP listener or use port 80 for testing |
| NLB has no security group option | Expected — NLBs are transparent L4 pass-through | Control access via NACL or EC2 security groups |

---

## Step 4 — Test Path Routing

### 📸 Screenshot
> Take a screenshot of your terminal showing both curl commands and their outputs.
> Label it: `04_curl_routing_verification.png`

**Get ALB DNS Name**
1. EC2 → Load Balancers → Select `alb-lab-23`
2. Copy the DNS name from the Description tab

**Test in Terminal (or AWS CloudShell)**

Open AWS CloudShell (icon in top navigation bar) and run:

```bash
ALB_DNS="alb-lab-23-xxxxxxxx.us-east-1.elb.amazonaws.com"

# Test 1: API route — should hit port 8080 backend
echo "=== Testing /api route ==="
curl -v http://${ALB_DNS}/api/test 2>&1 | grep -E "< HTTP|Server:|Connected"

# Test 2: Web route — should hit port 80 backend
echo "=== Testing /web route ==="
curl -v http://${ALB_DNS}/web/index 2>&1 | grep -E "< HTTP|Server:|Connected"

# Test 3: Default route — should hit web-tg
echo "=== Testing default route ==="
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://${ALB_DNS}/

# Test 4: Load test (10 rapid requests)
echo "=== 10 rapid requests to verify distribution ==="
for i in {1..10}; do
  curl -s -o /dev/null -w "Request $i: %{http_code} - %{time_total}s\n" http://${ALB_DNS}/api/test
done
```

**Expected Results**
- `/api/test` → HTTP 200, response from port 8080 backend
- `/web/index` → HTTP 200, response from port 80 backend  
- `/` (default) → HTTP 200, response from web-tg (port 80)
- All 10 requests complete < 100ms (healthy LB performance)

### ALB vs NLB Latency Comparison

```bash
NLB_DNS="nlb-lab-23-xxxxxxxx.us-east-1.elb.amazonaws.com"

echo "=== ALB Response Time ==="
for i in {1..5}; do
  curl -s -o /dev/null -w "ALB: %{time_total}s\n" http://${ALB_DNS}/
done

echo "=== NLB Response Time ==="
for i in {1..5}; do
  curl -s -o /dev/null -w "NLB: %{time_total}s\n" http://${NLB_DNS}:80/
done
# NLB should show lower latency (~100μs overhead vs ~1-5ms for ALB)
```

### Expected Outcome
- ALB path routing correctly separates `/api/*` and `/web/*` traffic
- NLB passes raw TCP without header inspection
- Both load balancers respond within acceptable time bounds
- CloudWatch metrics show RequestCount increasing for both LBs

### Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `curl: (6) Could not resolve host` | DNS not propagated yet | Wait 2-3 minutes after ALB creation |
| All requests return 404 | Path not matching any rule | Check URL starts with exactly `/api/` or `/web/` (case-sensitive) |
| Inconsistent routing | Two instances registered in same target group | Expected — ALB round-robins within a target group |
| NLB connection refused | No service listening on that port | Check EC2 security group allows inbound from NLB subnets |

---

## Summary: ALB vs NLB Feature Comparison

| Feature | ALB | NLB |
|---|---|---|
| OSI Layer | 7 (Application) | 4 (Transport) |
| Protocols | HTTP, HTTPS, gRPC, WebSocket | TCP, UDP, TLS |
| Routing logic | Path, host, header, query string | IP:Port only |
| Security groups | ✅ Yes | ❌ No |
| Static IP | ❌ No (use CNAME) | ✅ Via Elastic IP |
| Latency overhead | ~1–5ms | ~100μs |
| SSL termination | ✅ Yes | ✅ Optional (TLS passthrough available) |
| Lambda targets | ✅ Yes | ❌ No |
| Sticky sessions | Cookie-based | Source IP hash |
| Free Tier | ❌ None | ❌ None |
| Cost | $0.0225/hr + LCU | $0.006/NLCU-hr |
