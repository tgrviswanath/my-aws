# Project 7.3 — AWS X-Ray Distributed Tracing

## What This Does
Adds distributed tracing to the Flask API using AWS X-Ray. Every request is traced end-to-end: API Gateway → Lambda/ECS → DynamoDB/RDS, showing exactly where time is spent and where errors occur.

## What X-Ray Shows
- Full request trace from entry to exit
- Time spent in each service/segment
- Downstream calls (DynamoDB, RDS, external APIs)
- Error rates and fault rates per service
- Service map (visual graph of all services)
- Performance bottlenecks (slowest traces)

## Services Instrumented
- Flask API (via `aws-xray-sdk`)
- boto3 calls (DynamoDB, S3 — auto-patched)
- Outbound HTTP calls (requests library — auto-patched)

## How to Deploy
```bash
cd terraform
terraform init && terraform apply
```

## Lessons Learned
- X-Ray sampling: trace 5% of requests by default — adjust for high-traffic services
- Segments vs subsegments: segment = one service; subsegment = one operation within a service
- Annotations: indexed key-value pairs — use for filtering traces (e.g. `user_id`, `order_id`)
- Metadata: non-indexed data — use for debugging details
- X-Ray daemon: runs as a sidecar container in ECS — collects and batches traces
- Service map: automatically built from trace data — no manual configuration

## Code

### `src/app_with_tracing.py` — Flask app instrumented with AWS X-Ray

```bash
pip install flask aws-xray-sdk boto3

export AWS_XRAY_DAEMON_ADDRESS=127.0.0.1:2000

# Start X-Ray daemon locally (Docker)
docker run -p 2000:2000/udp amazon/aws-xray-daemon

# Run the instrumented app
python src/app_with_tracing.py

# Make requests to generate traces
curl http://localhost:8080/api/orders
curl http://localhost:8080/api/users/123
```

X-Ray captures: incoming HTTP requests, DynamoDB calls, downstream HTTP calls, custom subsegments.
