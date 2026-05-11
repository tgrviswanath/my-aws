# Steps — Project 5.6 AWS App Runner Deployment

## Phase 1 — Deploy

```bash
cd terraform
terraform init
terraform apply \
  -var="ecr_image_url=$(cd ../../project_5.3_ecr/terraform && terraform output -raw ecr_url):latest" \
  -auto-approve

APP_URL=$(terraform output -raw app_runner_url)
echo "App URL: $APP_URL"
```

---

## Phase 2 — Test

```bash
# App Runner provides HTTPS automatically
curl $APP_URL/health | python3 -m json.tool
curl $APP_URL/items  | python3 -m json.tool

# Test auto-scaling (App Runner scales on demand)
# Send concurrent requests
for i in {1..20}; do curl -s $APP_URL/health & done; wait
```

---

## Phase 3 — Test Auto-deployment

```bash
# Push a new image to ECR
# App Runner detects the new image and redeploys automatically

# Build new version
cd ../../project_5.1_single_docker_app
sed -i 's/APP_VERSION = "1.0.0"/APP_VERSION = "3.0.0"/' app/app.py
docker build -t flask-api:3.0.0 .
docker tag flask-api:3.0.0 $ECR_URL:latest
docker push $ECR_URL:latest

# Watch App Runner detect and deploy the new image
aws apprunner list-operations \
  --service-arn $(cd ../project_5.6_app_runner/terraform && terraform output -raw service_arn)

# After ~2 minutes, check version
curl $APP_URL/info | python3 -m json.tool
# Should show version: 3.0.0
```

---

## Phase 4 — Compare with ECS Fargate

```bash
# App Runner:
# - URL: https://xxxxx.us-east-1.awsapprunner.com (HTTPS automatic)
# - No VPC config needed
# - No ALB to manage
# - Auto-deploys on ECR push

# ECS Fargate:
# - URL: http://alb-dns-name.us-east-1.elb.amazonaws.com (HTTP, need ACM for HTTPS)
# - Requires VPC, subnets, security groups
# - Requires ALB + target group + listener
# - Manual deployment trigger
```

---

## Screenshots to Take
- [ ] App Runner service in console (Running status)
- [ ] HTTPS URL working in browser
- [ ] Auto-deployment triggered after ECR push
- [ ] App Runner metrics (requests, latency)
- [ ] Side-by-side comparison: App Runner vs ECS setup complexity
