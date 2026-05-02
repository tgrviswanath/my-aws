# Elastic Load Balancing (ELB) — ALB, NLB, CLB Deep Dive

## Overview

ELB distributes incoming traffic across multiple targets (EC2, containers, Lambda, IPs) in one or more AZs.

| Type | Layer | Protocol | Use Case |
|------|-------|---------|---------|
| ALB (Application) | L7 | HTTP/HTTPS/gRPC | Web apps, microservices, path routing |
| NLB (Network) | L4 | TCP/UDP/TLS | High performance, static IP, gaming, IoT |
| CLB (Classic) | L4/L7 | HTTP/HTTPS/TCP | Legacy only — avoid |
| GWLB (Gateway) | L3 | IP | Inline security appliances (firewalls) |

---

## Application Load Balancer (ALB)

### Key Features
- Content-based routing (path, host, headers, query strings)
- Native WebSocket and HTTP/2 support
- Lambda as a target
- User authentication (Cognito, OIDC)
- WAF integration
- Access logs to S3

### Routing Rules

```
Listener (port 443 HTTPS)
├── Rule 1: /api/* → Target Group: api-servers
├── Rule 2: /static/* → Target Group: cdn-servers
├── Rule 3: Host: admin.example.com → Target Group: admin-servers
├── Rule 4: Header: X-Version=v2 → Target Group: v2-servers
└── Default: → Target Group: web-servers
```

```bash
# Create ALB
aws elbv2 create-load-balancer \
  --name my-alb \
  --subnets subnet-aaa subnet-bbb \
  --security-groups sg-12345678 \
  --scheme internet-facing \
  --type application

# Create target group
aws elbv2 create-target-group \
  --name web-tg \
  --protocol HTTP \
  --port 80 \
  --vpc-id vpc-12345678 \
  --health-check-path /health \
  --health-check-interval-seconds 30 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3

# Create listener with HTTPS
aws elbv2 create-listener \
  --load-balancer-arn arn:aws:elasticloadbalancing:... \
  --protocol HTTPS \
  --port 443 \
  --certificates CertificateArn=arn:aws:acm:... \
  --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:...

# Add path-based routing rule
aws elbv2 create-rule \
  --listener-arn arn:aws:elasticloadbalancing:... \
  --priority 10 \
  --conditions '[{"Field":"path-pattern","Values":["/api/*"]}]' \
  --actions '[{"Type":"forward","TargetGroupArn":"arn:aws:elasticloadbalancing:..."}]'
```

### ALB Access Logs
```bash
# Enable access logs
aws elbv2 modify-load-balancer-attributes \
  --load-balancer-arn arn:aws:elasticloadbalancing:... \
  --attributes \
    Key=access_logs.s3.enabled,Value=true \
    Key=access_logs.s3.bucket,Value=my-alb-logs \
    Key=access_logs.s3.prefix,Value=my-alb
```

---

## Network Load Balancer (NLB)

### Key Features
- Handles millions of requests per second
- Static IP per AZ (or Elastic IP)
- Preserves source IP address
- Ultra-low latency (~100ms vs ALB ~400ms)
- TLS termination
- No security groups (traffic passes through)

```bash
# Create NLB
aws elbv2 create-load-balancer \
  --name my-nlb \
  --subnets subnet-aaa subnet-bbb \
  --type network \
  --scheme internet-facing

# Create TCP target group
aws elbv2 create-target-group \
  --name tcp-tg \
  --protocol TCP \
  --port 80 \
  --vpc-id vpc-12345678 \
  --health-check-protocol TCP

# Assign Elastic IPs to NLB
aws elbv2 create-load-balancer \
  --name my-nlb-eip \
  --type network \
  --subnet-mappings \
    SubnetId=subnet-aaa,AllocationId=eipalloc-111 \
    SubnetId=subnet-bbb,AllocationId=eipalloc-222
```

---

## Health Checks

```
Healthy threshold:   2 consecutive successes → healthy
Unhealthy threshold: 3 consecutive failures  → unhealthy
Interval:            30 seconds
Timeout:             5 seconds
```

```bash
# Update health check settings
aws elbv2 modify-target-group \
  --target-group-arn arn:aws:elasticloadbalancing:... \
  --health-check-path /health \
  --health-check-interval-seconds 10 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 2 \
  --health-check-timeout-seconds 5
```

**Best practice**: Use a dedicated `/health` endpoint that checks DB connectivity, cache, and dependencies — not just HTTP 200.

---

## Connection Draining (Deregistration Delay)

When an instance is deregistered, ELB stops sending new requests but waits for in-flight requests to complete.

```bash
# Set deregistration delay (default 300s)
aws elbv2 modify-target-group-attributes \
  --target-group-arn arn:aws:elasticloadbalancing:... \
  --attributes Key=deregistration_delay.timeout_seconds,Value=60
```

---

## Sticky Sessions

Routes a user to the same target for the duration of a session.

```bash
# Enable sticky sessions (ALB)
aws elbv2 modify-target-group-attributes \
  --target-group-arn arn:aws:elasticloadbalancing:... \
  --attributes \
    Key=stickiness.enabled,Value=true \
    Key=stickiness.type,Value=lb_cookie \
    Key=stickiness.lb_cookie.duration_seconds,Value=86400
```

**Warning**: Sticky sessions reduce the effectiveness of load balancing. Prefer stateless design with external session storage (ElastiCache).

---

## SSL/TLS Termination

```
Client → HTTPS → ALB (terminates TLS) → HTTP → Backend
Client → HTTPS → ALB (re-encrypts)    → HTTPS → Backend (end-to-end)
```

```bash
# Request ACM certificate
aws acm request-certificate \
  --domain-name example.com \
  --subject-alternative-names "*.example.com" \
  --validation-method DNS

# Add certificate to listener
aws elbv2 add-listener-certificates \
  --listener-arn arn:aws:elasticloadbalancing:... \
  --certificates CertificateArn=arn:aws:acm:...
```

---

## CloudFormation Template

```yaml
AWSTemplateFormatVersion: '2010-09-09'

Resources:
  ALB:
    Type: AWS::ElasticLoadBalancingV2::LoadBalancer
    Properties:
      Name: web-alb
      Scheme: internet-facing
      Type: application
      Subnets:
        - !Ref PublicSubnet1
        - !Ref PublicSubnet2
      SecurityGroups:
        - !Ref ALBSecurityGroup

  TargetGroup:
    Type: AWS::ElasticLoadBalancingV2::TargetGroup
    Properties:
      Name: web-tg
      Protocol: HTTP
      Port: 80
      VpcId: !Ref VPC
      HealthCheckPath: /health
      HealthCheckIntervalSeconds: 30
      HealthyThresholdCount: 2
      UnhealthyThresholdCount: 3
      TargetType: instance

  HTTPSListener:
    Type: AWS::ElasticLoadBalancingV2::Listener
    Properties:
      LoadBalancerArn: !Ref ALB
      Protocol: HTTPS
      Port: 443
      Certificates:
        - CertificateArn: !Ref ACMCertificate
      DefaultActions:
        - Type: forward
          TargetGroupArn: !Ref TargetGroup

  HTTPRedirect:
    Type: AWS::ElasticLoadBalancingV2::Listener
    Properties:
      LoadBalancerArn: !Ref ALB
      Protocol: HTTP
      Port: 80
      DefaultActions:
        - Type: redirect
          RedirectConfig:
            Protocol: HTTPS
            Port: 443
            StatusCode: HTTP_301
```

---

## Interview Q&A

### Q1: What is the difference between ALB and NLB?
**ALB**: Layer 7, understands HTTP/HTTPS. Supports path/host/header routing, WebSockets, Lambda targets, WAF. ~400ms latency. Best for web apps and microservices.
**NLB**: Layer 4, TCP/UDP. Millions of RPS, static IP, preserves source IP, ~100ms latency. Best for high-performance, low-latency, non-HTTP workloads (gaming, IoT, financial trading).

### Q2: How does ALB path-based routing work?
ALB evaluates listener rules in priority order. Each rule has conditions (path pattern, host header, HTTP headers, query strings) and actions (forward, redirect, fixed response). First matching rule wins. Use this to route `/api/*` to backend servers and `/` to frontend servers with a single load balancer.

### Q3: What is connection draining and why is it important?
When you remove an instance from a target group (scale-in, deployment), ELB stops sending new requests but waits for existing connections to complete before fully deregistering. Without it, in-flight requests get dropped, causing errors for users. Set the timeout to slightly longer than your longest expected request duration.

### Q4: How do you achieve zero-downtime deployments with ALB?
1. Register new instances in target group
2. Wait for health checks to pass
3. Deregister old instances (connection draining handles in-flight requests)
4. With ASG: use rolling update or blue/green with separate target groups
5. With CodeDeploy: automated blue/green with ALB traffic shifting

### Q5: When would you use NLB over ALB?
- Need static IP addresses (whitelisting by clients)
- Need to preserve client source IP at the instance level
- Ultra-low latency requirements
- Non-HTTP protocols (TCP, UDP, custom protocols)
- Handling millions of concurrent connections
- Gaming servers, IoT, financial trading systems
