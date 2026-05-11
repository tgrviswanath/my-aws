# Steps — Project 5.4 ECS Fargate Deployment

## Phase 1 — Prerequisites

```bash
# Ensure image is in ECR (from Project 5.3)
ECR_URL=$(cd ../project_5.3_ecr/terraform && terraform output -raw ecr_url)
echo "ECR: $ECR_URL"

# Verify image exists
aws ecr list-images --repository-name handson-flask-api
```

---

## Phase 2 — Deploy with Terraform

```bash
cd terraform
terraform init
terraform plan -var-file="terraform.tfvars"
terraform apply -var-file="terraform.tfvars"

ALB_URL=$(terraform output -raw alb_url)
echo "App URL: $ALB_URL"
```

---

## Phase 3 — Verify Deployment

```bash
# Wait for tasks to be running (~2 minutes)
aws ecs wait services-stable \
  --cluster handson-cluster \
  --services handson-flask-api-service

# Check service status
aws ecs describe-services \
  --cluster handson-cluster \
  --services handson-flask-api-service \
  --query "services[0].{Status:status,Running:runningCount,Desired:desiredCount,Pending:pendingCount}"

# Test the app
curl $ALB_URL/health | python3 -m json.tool
curl $ALB_URL/items  | python3 -m json.tool
```

---

## Phase 4 — View Container Logs

```bash
# Get log stream names
aws logs describe-log-streams \
  --log-group-name /ecs/handson-flask-api \
  --order-by LastEventTime \
  --descending \
  --query "logStreams[0].logStreamName" \
  --output text

# Tail logs
aws logs tail /ecs/handson-flask-api --follow
```

---

## Phase 5 — Rolling Deployment (Update Image)

```bash
# Build and push a new version
cd ../../project_5.1_single_docker_app
docker build -t flask-api:2.0.0 .
docker tag flask-api:2.0.0 $ECR_URL:2.0.0
docker tag flask-api:2.0.0 $ECR_URL:latest
docker push $ECR_URL:latest
docker push $ECR_URL:2.0.0

# Force new deployment (ECS pulls latest image)
aws ecs update-service \
  --cluster handson-cluster \
  --service handson-flask-api-service \
  --force-new-deployment

# Watch rolling deployment
watch -n 5 "aws ecs describe-services \
  --cluster handson-cluster \
  --services handson-flask-api-service \
  --query 'services[0].{Running:runningCount,Pending:pendingCount,Desired:desiredCount}'"
```

---

## Phase 6 — Scale the Service

```bash
# Scale up to 4 tasks
aws ecs update-service \
  --cluster handson-cluster \
  --service handson-flask-api-service \
  --desired-count 4

# Verify load balancing (different task IDs in hostname)
for i in {1..6}; do
  curl -s $ALB_URL/info | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['hostname'])"
done
```

---

## Screenshots to Take
- [ ] ECS cluster with running service
- [ ] Task definition showing container config
- [ ] Running tasks with Fargate launch type
- [ ] ALB target group showing healthy tasks
- [ ] App responding at ALB URL
- [ ] CloudWatch logs showing container output
- [ ] Rolling deployment in progress
- [ ] Multiple hostnames from load-balanced requests
