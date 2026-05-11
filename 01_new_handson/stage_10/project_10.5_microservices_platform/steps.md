# Steps — Project 10.5 Production-grade Microservices Platform

## This is the Capstone Project
All previous projects feed into this one. Follow this order:

---

## Phase 1 — Foundation (Stages 0-3)
```
✅ Stage 0: Local dev setup, billing alerts
✅ Stage 1: EC2, IAM, RDS, Python automation
✅ Stage 2: Custom VPC, multi-tier app, failure simulation
✅ Stage 3: Terraform modules, remote state, CI/CD pipeline
```

---

## Phase 2 — Application Layer (Stages 4-5)
```
✅ Stage 4: Serverless API, auth, URL shortener, image processing
✅ Stage 5: Docker, ECR, ECS Fargate, blue-green, Redis
```

---

## Phase 3 — DevOps (Stage 6)
```
✅ Stage 6: GitHub Actions CI/CD, OIDC, Jenkins, multi-account, ArgoCD
```

---

## Phase 4 — Observability (Stage 7)
```
✅ Stage 7: CloudWatch, centralized logging, X-Ray, Athena, Grafana
```

---

## Phase 5 — Security (Stage 8)
```
✅ Stage 8: Secrets Manager, WAF, Config, GuardDuty, CloudTrail, Zero Trust
```

---

## Phase 6 — Data Engineering (Stage 9)
```
✅ Stage 9: Data lake, Glue ETL, Kinesis, Spark, Airflow, dbt, Redshift
```

---

## Phase 7 — Assemble the Platform

```bash
# 1. Deploy VPC (from Stage 2)
cd stage_02/project_2.1_custom_vpc/terraform
terraform apply

# 2. Deploy ECS services (from Stage 5)
cd stage_05/project_5.4_ecs_fargate/terraform
terraform apply -var="ecr_image_url=$ECR_URL:latest"

# 3. Deploy API Gateway with auth (from Stage 4)
cd stage_04/project_4.2_api_auth/terraform
terraform apply

# 4. Deploy WAF (from Stage 8)
cd stage_08/project_8.2_waf/terraform
terraform apply -var="alb_arn=$ALB_ARN"

# 5. Deploy monitoring (from Stage 7)
cd stage_07/project_7.1_cloudwatch/terraform
terraform apply -var="alert_email=your@email.com"

# 6. Deploy data pipeline (from Stage 9)
cd stage_09/project_9.3_kinesis_streaming/terraform
terraform apply

# 7. Set up CI/CD (from Stage 6)
# Configure GitHub Actions with OIDC
# Push code → automatic deployment
```

---

## Phase 8 — Verify the Full Platform

```bash
API_URL="https://your-api-gateway-url.execute-api.us-east-1.amazonaws.com"

# 1. Register and login
TOKEN=$(curl -s -X POST $API_URL/auth/login \
  -d '{"username":"test","password":"Test@1234"}' | jq -r .id_token)

# 2. Create an order (triggers Kinesis event)
curl -s -X POST $API_URL/orders \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"product":"Widget A","quantity":2,"amount":59.98}'

# 3. Verify event in Kinesis
aws kinesis get-records ...

# 4. Check CloudWatch logs
aws logs tail /ecs/handson-flask-api --follow

# 5. View X-Ray trace
# AWS Console → X-Ray → Traces → find your request

# 6. Check Grafana dashboard
# Open Grafana URL → see request rate, latency, errors

# 7. Verify WAF blocked a SQL injection
curl "$API_URL/orders?id=1' OR '1'='1"
# Expected: 403 Forbidden
```

---

## Phase 9 — Load Test

```bash
# Install k6 (load testing tool)
# https://k6.io/docs/getting-started/installation/

cat > load_test.js << 'EOF'
import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  stages: [
    { duration: '1m', target: 10 },   // ramp up
    { duration: '3m', target: 50 },   // sustained load
    { duration: '1m', target: 0 },    // ramp down
  ],
};

export default function() {
  let res = http.get('https://YOUR_API_URL/health');
  check(res, { 'status is 200': (r) => r.status === 200 });
  sleep(1);
}
EOF

k6 run load_test.js

# Watch HPA scale up in EKS
kubectl get hpa -n production -w

# Watch ECS scale up
aws ecs describe-services \
  --cluster handson-cluster \
  --services handson-flask-api-service \
  --query "services[0].{Running:runningCount,Desired:desiredCount}"
```

---

## Screenshots to Take
- [ ] Full architecture diagram (draw.io or Lucidchart)
- [ ] All services running (ECS, EKS, RDS, Redis, Kinesis)
- [ ] API request flowing through WAF → API Gateway → ECS → RDS
- [ ] X-Ray trace showing full request path
- [ ] Grafana dashboard with all metrics
- [ ] Load test results (requests/sec, latency, error rate)
- [ ] HPA scaling up under load
- [ ] CI/CD pipeline deploying new version
- [ ] Security Hub showing compliance score
- [ ] Cost Explorer showing monthly spend by service
