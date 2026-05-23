# Verification & Validation — Project 7.5 Grafana + Prometheus Monitoring

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| AMP Workspace | Amazon Managed Prometheus → Workspaces | Workspace listed, Status = **Active** |
| AMG Workspace | Amazon Managed Grafana → Workspaces | Workspace listed, Status = **Active** |
| Grafana URL | AMG → Workspace → Grafana workspace URL | Grafana login page loads |
| IAM Role | IAM → Roles | Grafana workspace role with CloudWatch + AMP read access |
| ECS Task Definition | ECS → Task Definitions | Prometheus sidecar container present |

📸 Screenshot: AWS Managed Prometheus workspace Active  
📸 Screenshot: AWS Managed Grafana workspace Active  
📸 Screenshot: Grafana CloudWatch data source connected (green)  
📸 Screenshot: Grafana Prometheus data source connected (green)  
📸 Screenshot: ECS dashboard showing CPU/memory graphs  
📸 Screenshot: Custom RED metrics dashboard

---

## 2. AWS CLI Verification

```bash
# 2.1 Confirm AMP workspace active
aws amp list-workspaces \
  --query "workspaces[*].{Alias:alias,Status:status.statusCode,WorkspaceId:workspaceId}"
# Expected: statusCode=ACTIVE

# 2.2 Get AMP workspace endpoint
WORKSPACE_ID=$(aws amp list-workspaces \
  --query "workspaces[0].workspaceId" --output text)
aws amp describe-workspace \
  --workspace-id $WORKSPACE_ID \
  --query "workspace.{Alias:alias,Status:status.statusCode,Endpoint:prometheusEndpoint}"
# Expected: Status=ACTIVE, Endpoint populated

# 2.3 Confirm AMG workspace active
aws grafana list-workspaces \
  --query "workspaces[*].{Name:name,Status:status,GrafanaVersion:grafanaVersion}"
# Expected: status=ACTIVE

# 2.4 Get Grafana workspace URL
aws grafana list-workspaces \
  --query "workspaces[0].endpoint" --output text
# Expected: https://xxx.grafana-workspace.us-east-1.amazonaws.com

# 2.5 Verify metrics are being written to AMP
# (requires awscurl or sigv4 signing — use console for quick check)
# Via console: AMP → Workspace → Metrics → query: up
# Expected: metric 'up' with value 1 for flask-api job

# 2.6 Confirm Flask app /metrics endpoint is live
ALB_URL="http://your-alb-dns.us-east-1.elb.amazonaws.com"
curl -s $ALB_URL/metrics | head -20
# Expected: Prometheus text format metrics:
# # HELP http_requests_total Total HTTP requests
# # TYPE http_requests_total counter
# http_requests_total{method="GET",endpoint="/health",status="200"} 42.0

# 2.7 Confirm ECS task has Prometheus sidecar
aws ecs describe-task-definition \
  --task-definition handson-flask-api \
  --query "taskDefinition.containerDefinitions[*].{Name:name,Image:image}" \
  --output table
# Expected: flask-api container + prometheus sidecar container listed
```

---

## 3. Terraform State Verification

```bash
cd terraform

# 3.1 List all resources
terraform state list
# Expected:
# aws_prometheus_workspace.main
# aws_grafana_workspace.main
# aws_grafana_role_association.admin
# aws_iam_role.grafana
# aws_iam_role_policy_attachment.grafana_cloudwatch
# aws_iam_role_policy_attachment.grafana_amp

# 3.2 Inspect AMP workspace
terraform state show aws_prometheus_workspace.main
# Shows: alias, prometheus_endpoint, status

# 3.3 Confirm outputs
terraform output grafana_url
# Expected: https://xxx.grafana-workspace.us-east-1.amazonaws.com

terraform output prometheus_endpoint
# Expected: https://aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-xxx/

# 3.4 No drift
terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

---

## 4. Health Check — Metrics Pipeline

```bash
ALB_URL="http://your-alb-dns.us-east-1.elb.amazonaws.com"

# Step 1: Generate traffic to produce metrics
for i in {1..30}; do
  curl -s $ALB_URL/health > /dev/null
  curl -s $ALB_URL/api/orders > /dev/null
  curl -s $ALB_URL/nonexistent > /dev/null
done

# Step 2: Verify /metrics endpoint shows incremented counters
curl -s $ALB_URL/metrics | grep http_requests_total
# Expected: counter values > 0 for GET /health, GET /api/orders, GET /nonexistent

# Step 3: Verify Grafana data sources (manual — open Grafana UI)
# Configuration → Data Sources → CloudWatch → Save & Test → "Data source is working"
# Configuration → Data Sources → Prometheus → Save & Test → "Data source is working"

# Step 4: Run PromQL query in Grafana Explore
# Query: rate(http_requests_total[5m])
# Expected: time-series graph with request rate per endpoint
```

---

## 5. Expected Successful Outputs

**CLI — list-workspaces (AMP):**
```json
[{ "alias": "handson-prometheus", "statusCode": "ACTIVE", "workspaceId": "ws-abc123" }]
```

**CLI — list-workspaces (AMG):**
```json
[{ "name": "handson-grafana", "status": "ACTIVE", "grafanaVersion": "10.4" }]
```

**Flask /metrics endpoint:**
```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{endpoint="/health",method="GET",status="200"} 30.0
http_requests_total{endpoint="/api/orders",method="GET",status="200"} 30.0
http_requests_total{endpoint="/nonexistent",method="GET",status="404"} 30.0
# HELP http_request_duration_seconds HTTP request latency
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{endpoint="/health",le="0.005"} 28.0
```

**terraform output:**
```
grafana_url          = "https://xxx.grafana-workspace.us-east-1.amazonaws.com"
prometheus_endpoint  = "https://aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-xxx/"
```

---

## 6. Verification Checklist

- [ ] AMP workspace status = ACTIVE, endpoint populated
- [ ] AMG workspace status = ACTIVE, Grafana URL accessible
- [ ] Grafana login page loads
- [ ] CloudWatch data source connected (green "Data source is working")
- [ ] Prometheus (AMP) data source connected (green "Data source is working")
- [ ] ECS task definition has Prometheus sidecar container
- [ ] Flask app `/metrics` endpoint returns Prometheus text format
- [ ] `http_requests_total` counter increments after traffic generation
- [ ] ECS dashboard imported and showing CPU/memory graphs
- [ ] Custom RED dashboard panels render (rate, errors, P99 latency)
- [ ] Grafana alert rule configured
- [ ] `terraform plan` shows no changes
- [ ] `terraform state list` shows AMP + AMG + IAM resources
