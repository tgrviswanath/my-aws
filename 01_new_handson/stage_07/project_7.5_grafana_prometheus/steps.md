# Steps — Project 7.5 Grafana + Prometheus Monitoring

## Phase 1 — Deploy AWS Managed Prometheus + Grafana

```bash
cd terraform
terraform init && terraform apply -auto-approve

GRAFANA_URL=$(terraform output -raw grafana_url)
PROM_ENDPOINT=$(terraform output -raw prometheus_endpoint)
echo "Grafana: $GRAFANA_URL"
echo "Prometheus: $PROM_ENDPOINT"
```

---

## Phase 2 — Configure Prometheus remote_write on ECS

Add to your ECS task definition a Prometheus sidecar that scrapes the Flask app and remote_writes to AMP:

```yaml
# prometheus.yml (mounted into Prometheus container)
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: flask-api
    static_configs:
      - targets: ['localhost:5000']
    metrics_path: /metrics

remote_write:
  - url: https://aps-workspaces.us-east-1.amazonaws.com/workspaces/WORKSPACE_ID/api/v1/remote_write
    sigv4:
      region: us-east-1
```

---

## Phase 3 — Add Prometheus Metrics to Flask App

```python
# Add to requirements.txt: prometheus-client==0.20.0

from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP request latency', ['endpoint'])

@app.route('/metrics')
def metrics():
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

@app.before_request
def start_timer():
    request.start_time = time.time()

@app.after_request
def record_metrics(response):
    duration = time.time() - request.start_time
    REQUEST_COUNT.labels(request.method, request.path, response.status_code).inc()
    REQUEST_LATENCY.labels(request.path).observe(duration)
    return response
```

---

## Phase 4 — Configure Grafana Data Sources

```
1. Open Grafana URL from terraform output
2. Sign in with AWS SSO
3. Configuration → Data Sources → Add data source

Add CloudWatch:
  - Type: CloudWatch
  - Auth: AWS SDK Default
  - Region: us-east-1

Add Prometheus (AMP):
  - Type: Prometheus
  - URL: https://aps-workspaces.us-east-1.amazonaws.com/workspaces/WORKSPACE_ID/
  - Auth: SigV4
  - Region: us-east-1
```

---

## Phase 5 — Import Dashboards

```
1. Grafana → Dashboards → Import
2. Import by ID:
   - 13978 (AWS ECS)
   - 12006 (AWS ALB)
   - 3662  (Prometheus 2.0 Stats)

3. Create custom dashboard:
   - Panel 1: Request rate (PromQL: rate(http_requests_total[5m]))
   - Panel 2: Error rate (PromQL: rate(http_requests_total{status=~"5.."}[5m]))
   - Panel 3: P99 latency (PromQL: histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m])))
```

---

## Phase 6 — Set Up Grafana Alerts

```
1. Grafana → Alerting → Alert rules → New alert rule
2. Query: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
3. Condition: IS ABOVE 0.1
4. Evaluation: every 1m for 5m
5. Notification: SNS or email
```

---

## Screenshots to Take
- [ ] AWS Managed Prometheus workspace created
- [ ] AWS Managed Grafana workspace created
- [ ] CloudWatch data source connected (green)
- [ ] Prometheus data source connected (green)
- [ ] ECS dashboard showing CPU/memory graphs
- [ ] Custom dashboard with RED metrics (Rate, Errors, Duration)
- [ ] Alert rule configured
