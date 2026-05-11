# Steps — Project 5.3 Push Containers to ECR

## Phase 1 — Create ECR Repository (Terraform)

```bash
cd terraform
terraform init && terraform apply -auto-approve
ECR_URL=$(terraform output -raw ecr_url)
echo "ECR: $ECR_URL"
```

---

## Phase 2 — Authenticate Docker to ECR

```bash
# Get ECR login token and pipe to docker login
aws ecr get-login-password --region us-east-1 \
  | docker login --username AWS --password-stdin $ECR_URL

# Expected: Login Succeeded
```

---

## Phase 3 — Build, Tag, and Push

```bash
# Build the image (from Project 5.1)
cd ../project_5.1_single_docker_app
docker build -t flask-api:latest .

# Tag with ECR URL
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URL="${ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/handson-flask-api"

# Multiple tags
docker tag flask-api:latest $ECR_URL:latest
docker tag flask-api:latest $ECR_URL:1.0.0
docker tag flask-api:latest $ECR_URL:$(git rev-parse --short HEAD 2>/dev/null || echo "manual")

# Push all tags
docker push $ECR_URL:latest
docker push $ECR_URL:1.0.0

# Verify images in ECR
aws ecr list-images \
  --repository-name handson-flask-api \
  --query "imageIds[*].{Tag:imageTag,Digest:imageDigest}" \
  --output table
```

---

## Phase 4 — Pull and Run from ECR

```bash
# Pull from ECR (simulates what ECS does)
docker pull $ECR_URL:latest

# Run from ECR image
docker run -d -p 5000:5000 $ECR_URL:latest
curl http://localhost:5000/health
```

---

## Phase 5 — Verify Lifecycle Policy

```bash
# Push 15 images with different tags to trigger lifecycle policy
for i in {1..15}; do
  docker tag flask-api:latest $ECR_URL:test-$i
  docker push $ECR_URL:test-$i
done

# List images — should see lifecycle policy keeping only last 10
aws ecr list-images --repository-name handson-flask-api --output table
```

---

## Phase 6 — Image Scanning

```bash
# Trigger a manual scan
aws ecr start-image-scan \
  --repository-name handson-flask-api \
  --image-id imageTag=latest

# Wait for scan to complete
aws ecr wait image-scan-complete \
  --repository-name handson-flask-api \
  --image-id imageTag=latest

# View scan results
aws ecr describe-image-scan-findings \
  --repository-name handson-flask-api \
  --image-id imageTag=latest \
  --query "imageScanFindings.findings[*].{Severity:severity,Name:name}" \
  --output table
```

---

## Screenshots to Take
- [ ] ECR repository created in console
- [ ] `docker login` success
- [ ] `docker push` output showing layers uploaded
- [ ] ECR console showing image with tags and size
- [ ] Image scan results (CVE findings)
- [ ] Lifecycle policy configured
