# Steps — Project 7.3 AWS X-Ray Distributed Tracing

## Phase 1 — Add X-Ray to ECS Task Definition

```bash
# Add X-Ray daemon as a sidecar container in the task definition
# See terraform/main.tf for the full task definition with X-Ray sidecar

cd terraform
terraform init && terraform apply -auto-approve
```

---

## Phase 2 — Install X-Ray SDK in Flask App

```bash
# Add to requirements.txt
echo "aws-xray-sdk==2.14.0" >> app/requirements.txt

# Rebuild and push image
docker build -t flask-api:xray .
docker tag flask-api:xray $ECR_URL:xray
docker push $ECR_URL:xray

# Force new ECS deployment
aws ecs update-service \
  --cluster handson-cluster \
  --service handson-flask-api-service \
  --force-new-deployment
```

---

## Phase 3 — Generate Traces

```bash
ALB_URL="http://your-alb-dns.us-east-1.elb.amazonaws.com"

# Generate various request types
for i in {1..20}; do
  curl -s $ALB_URL/health > /dev/null
  curl -s $ALB_URL/items  > /dev/null
  curl -s -X POST $ALB_URL/items \
    -H "Content-Type: application/json" \
    -d '{"name": "Test Item '$i'"}' > /dev/null
done

# Generate some errors
curl $ALB_URL/items/nonexistent-id
```

---

## Phase 4 — Explore X-Ray Console

```
1. AWS Console → X-Ray → Service Map
   → See visual graph: ALB → Flask API → DynamoDB

2. X-Ray → Traces
   → Filter by: annotation.endpoint = "list_items"
   → Sort by: Response time (find slowest)
   → Click a trace → see full timeline

3. X-Ray → Analytics
   → Response time distribution
   → Error rate over time
   → Compare time ranges
```

---

## Phase 5 — Find Performance Bottlenecks

```bash
# Get traces with high latency via CLI
aws xray get-trace-summaries \
  --start-time $(date -d '1 hour ago' +%s) \
  --end-time $(date +%s) \
  --filter-expression 'responsetime > 1' \
  --query "TraceSummaries[*].{Id:Id,Duration:Duration,Error:HasError}"
```

---

## Screenshots to Take
- [ ] X-Ray Service Map showing all services connected
- [ ] Individual trace timeline (segments + subsegments)
- [ ] DynamoDB subsegment showing query time
- [ ] Error trace showing 404 response
- [ ] X-Ray Analytics showing response time distribution
- [ ] Annotation filter working (filter by endpoint name)
