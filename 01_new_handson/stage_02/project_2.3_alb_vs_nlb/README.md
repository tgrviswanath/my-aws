# Project 2.3 — ALB vs NLB Comparison Lab

## What This Does
Deploys both an Application Load Balancer and a Network Load Balancer side by side to understand the real differences through hands-on testing.

## Key Differences

| Feature | ALB (Layer 7) | NLB (Layer 4) |
|---------|--------------|--------------|
| OSI Layer | 7 (Application) | 4 (Transport) |
| Protocol | HTTP, HTTPS, gRPC | TCP, UDP, TLS |
| Routing | Path, host, header, query | IP + port only |
| Latency | ~1ms | ~100µs (ultra-low) |
| Static IP | No (DNS only) | Yes (Elastic IP) |
| WebSockets | Yes | Yes |
| SSL termination | Yes | Yes (passthrough option) |
| Use case | Web apps, APIs, microservices | Gaming, IoT, financial, VoIP |
| Price | Higher | Lower |

## Services Used
- ALB (Application Load Balancer)
- NLB (Network Load Balancer)
- EC2 Target Groups
- VPC from Project 2.1

## How to Deploy
```bash
cd terraform
terraform init
terraform plan -var-file="terraform.tfvars"
terraform apply -var-file="terraform.tfvars"
```

## Lessons Learned
- ALB can route `/api/*` to one target group and `/web/*` to another — NLB cannot
- NLB preserves the client's source IP — ALB replaces it with its own IP
- NLB supports static Elastic IPs — useful when clients whitelist IPs
- Use ALB for 99% of web applications; NLB for raw TCP/UDP or extreme performance
- WebSockets work on both, but NLB is better for long-lived connections

## Code

### `code/load_test.py` — Measure and compare ALB vs NLB latency

```bash
pip install requests

# Test a single endpoint (100 requests, 10 concurrent)
python code/load_test.py --url https://your-alb-dns-name

# Custom request count and concurrency
python code/load_test.py --url https://your-alb-dns-name --requests 500 --concurrency 25

# Side-by-side ALB vs NLB comparison
python code/load_test.py \
  --url https://your-alb-dns-name \
  --compare-url https://your-nlb-dns-name \
  --requests 200
```

Metrics reported:
- Min / Mean / Median / P95 / P99 / Max latency (ms)
- Requests per second (throughput)
- Success rate (2xx responses)
- Status code breakdown
- Side-by-side comparison table when `--compare-url` is used
