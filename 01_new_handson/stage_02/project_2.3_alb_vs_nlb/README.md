# Project 2.3 — ALB vs NLB Comparison

**Stage:** 02 | **Level:** Intermediate | **Est. Time:** 2–3 hours | **Cost:** ~$16–20/month per load balancer

Deploy both an Application Load Balancer and a Network Load Balancer pointing at the same EC2 targets. Configure ALB path-based routing so `/api` hits one target group and `/web` hits another. Configure the NLB with an Elastic IP for a static, predictable address and TCP pass-through. Run `curl` timing tests against both to measure the latency overhead of L7 inspection versus L4 pass-through, and document which load balancer type fits which real-world scenario.

## Services Used

| Tool | Purpose | Cost |
|---|---|---|
| ALB (Layer 7) | HTTP/HTTPS routing with path-based rules | ~$16/month + $0.008/LCU |
| NLB (Layer 4) | TCP pass-through with static Elastic IP | ~$16/month + $0.006/NLCU |
| EC2 targets (×2) | One instance serves `/api`, another serves `/web` | ~$8/month each (t3.micro) |
| Target Groups (×3) | api-tg, web-tg for ALB; tcp-tg for NLB | Free |
| Elastic IP | Static IP attached to NLB per AZ | $0.005/hr if unattached |
| Listeners (×2) | ALB HTTP:80, NLB TCP:80 | Free |

## Input / Output

### Input

| Parameter | Value |
|---|---|
| EC2 targets | 2× t3.micro in public subnet, both running on port 80 |
| ALB rule 1 | Path `/api*` → `api-tg` |
| ALB rule 2 | Path `/web*` → `web-tg` |
| NLB Elastic IP | 1× EIP allocated in us-east-1a |
| Health check (ALB) | HTTP GET `/health` expects 200 |
| Health check (NLB) | TCP connection to port 80 |

### Output

| Resource | Result |
|---|---|
| ALB DNS | `project23-alb-xxx.us-east-1.elb.amazonaws.com` |
| NLB static IP | EIP visible in `aws ec2 describe-addresses` |
| Path routing test | `curl .../api` → api-tg; `curl .../web` → web-tg |
| Client IP (ALB) | App sees ALB private IP; real IP in `X-Forwarded-For` |
| Client IP (NLB) | App sees actual client IP (TCP pass-through) |
| Latency delta | NLB typically 1–3ms lower than ALB at p99 |

## Architecture

```
  Internet
      │
  ┌───┴──────────────────┐    ┌──────────────────────┐
  │  ALB (Layer 7)       │    │  NLB (Layer 4)        │
  │  DNS: project23-alb  │    │  Static EIP: x.x.x.x  │
  │  Listener: HTTP:80   │    │  Listener: TCP:80      │
  │                      │    │                        │
  │  Rules:              │    │  No rules — pure       │
  │  /api*  → api-tg     │    │  TCP pass-through      │
  │  /web*  → web-tg     │    │  to tcp-tg             │
  └──┬───────────┬───────┘    └──────────┬─────────────┘
     │           │                       │
  [api-tg]   [web-tg]               [tcp-tg]
  EC2-api     EC2-web           EC2-api + EC2-web
  :80          :80                    :80
```

## Quick Start

```cmd
REM Step 1: Create ALB
aws elbv2 create-load-balancer ^
  --name project23-alb ^
  --subnets <PUBLIC_SUBNET_1A_ID> <PUBLIC_SUBNET_1B_ID> ^
  --security-groups <ALB_SG_ID> ^
  --type application

REM Step 2: Create target groups for ALB path routing
aws elbv2 create-target-group ^
  --name api-tg ^
  --protocol HTTP --port 80 ^
  --vpc-id <VPC_ID> ^
  --health-check-path /health

aws elbv2 create-target-group ^
  --name web-tg ^
  --protocol HTTP --port 80 ^
  --vpc-id <VPC_ID> ^
  --health-check-path /health

REM Step 3: Register targets to each ALB target group
aws elbv2 register-targets --target-group-arn <API_TG_ARN> --targets Id=<EC2_API_ID>
aws elbv2 register-targets --target-group-arn <WEB_TG_ARN> --targets Id=<EC2_WEB_ID>

REM Step 4: Create ALB listener (default 404), then add path rules
aws elbv2 create-listener --load-balancer-arn <ALB_ARN> ^
  --protocol HTTP --port 80 ^
  --default-actions Type=fixed-response,FixedResponseConfig="{StatusCode=404}"

aws elbv2 create-rule --listener-arn <ALB_LISTENER_ARN> --priority 10 ^
  --conditions Field=path-pattern,Values="/api*" ^
  --actions Type=forward,TargetGroupArn=<API_TG_ARN>

aws elbv2 create-rule --listener-arn <ALB_LISTENER_ARN> --priority 20 ^
  --conditions Field=path-pattern,Values="/web*" ^
  --actions Type=forward,TargetGroupArn=<WEB_TG_ARN>

REM Step 5: Allocate EIP, create NLB with static IP in us-east-1a
aws ec2 allocate-address --domain vpc

aws elbv2 create-load-balancer --name project23-nlb --type network ^
  --subnet-mappings SubnetId=<PUBLIC_SUBNET_1A_ID>,AllocationId=<EIP_ALLOC_ID>

REM Step 6: Create NLB TCP target group, register targets, create listener
aws elbv2 create-target-group --name tcp-tg ^
  --protocol TCP --port 80 --vpc-id <VPC_ID>

aws elbv2 register-targets --target-group-arn <TCP_TG_ARN> ^
  --targets Id=<EC2_API_ID> Id=<EC2_WEB_ID>

aws elbv2 create-listener --load-balancer-arn <NLB_ARN> ^
  --protocol TCP --port 80 ^
  --default-actions Type=forward,TargetGroupArn=<TCP_TG_ARN>

REM Step 7: Test path routing on ALB and static IP on NLB
curl -v http://<ALB_DNS>/api/status
curl -v http://<ALB_DNS>/web/index.html
curl -v http://<NLB_EIP>/
```

## Data Flow

1. ALB path routing: client sends `GET /api/status` → ALB listener receives on port 80.
2. ALB parses the HTTP request, evaluates listener rules in priority order; rule 10 matches `/api*`.
3. ALB forwards to `api-tg`, opening a new TCP connection to the selected EC2 — client IP is not preserved.
4. EC2 receives the request with ALB's IP as source; real client IP is in the `X-Forwarded-For` header.
5. NLB pass-through: client sends `GET /` → NLB listener receives on TCP port 80.
6. NLB selects a target from `tcp-tg` using flow hash (src IP + dst IP + src port + dst port + protocol).
7. NLB forwards the TCP segment unmodified — EC2 sees the actual client IP as the source address.
8. Response from EC2 travels directly back through NLB without content inspection; NLB does not terminate TLS unless configured.

## Project Files

| File | Description |
|---|---|
| `README.md` | This document |
| `alb-setup.sh` | Creates ALB, target groups, and path-based listener rules |
| `nlb-setup.sh` | Allocates EIP, creates NLB with static IP mapping |
| `latency-test.sh` | `curl -w "%{time_total}"` loops against ALB and NLB DNS |
| `results.md` | Recorded latency measurements and comparison notes |

## Lessons Learned

- **ALB terminates HTTP/HTTPS at Layer 7:** The ALB reads the HTTP request fully before forwarding. This enables path routing, header inspection, and cookie-based stickiness — but adds a small processing overhead compared to pure TCP forwarding.
- **NLB preserves the client IP natively:** Because NLB operates at Layer 4 and does not terminate the TCP connection, the application receives the original client IP in the socket. No `X-Forwarded-For` header is needed or added.
- **NLB gets a static IP per AZ:** You can assign an Elastic IP to each AZ mapping when creating an NLB. The IP never changes, making NLB the right choice when clients need to whitelist a fixed IP (firewalls, payment gateways).
- **ALB cannot have a static IP — but there's a pattern:** ALB DNS resolves to different IPs that change over time. If a static IP is required with L7 features, put NLB in front of ALB using the "ALB-NLB chaining" pattern — NLB forwards TCP to the ALB's DNS.
- **ALB slow-start mode prevents thundering herd on new targets:** When enabled (10–900 seconds), a newly registered target receives a linearly increasing share of traffic instead of full load immediately. Useful after auto-scaling adds instances.
- **NLB health checks are TCP connection-based by default:** NLB opens a TCP connection to the target port. If the port responds, the target is healthy. You can also configure HTTP health checks on NLB, but the default is simpler and faster.
- **ALB listener rule priorities are integers — gaps matter:** Assign priorities like 10, 20, 30 (not 1, 2, 3) so you can insert rules later without re-numbering. Rules are evaluated lowest-number-first; the default rule has no priority and always fires last.
