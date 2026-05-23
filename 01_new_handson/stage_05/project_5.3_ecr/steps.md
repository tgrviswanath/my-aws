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

## Phase 7 — Verification & Validation

### 7.1 AWS Console Verification
1. **ECR** → **Repositories** → `handson-flask-api`
   - Images tab: confirm `latest` and `1.0.0` tags exist
   - Image size: confirm < 200MB
   - Scan status: confirm scan completed (if enabled)
2. **ECR** → **Lifecycle policies**: confirm policy is attached

### 7.2 CLI Verification Commands
```bash
# Confirm ECR repository exists
aws ecr describe-repositories \
  --repository-names handson-flask-api \
  --query "repositories[0].{Name:repositoryName,URI:repositoryUri,Scan:imageScanningConfiguration.scanOnPush}"
# Expected: name, URI, scanOnPush=true

# Confirm images are present with correct tags
aws ecr list-images \
  --repository-name handson-flask-api \
  --query "imageIds[*].{Tag:imageTag}" \
  --output table
# Expected: latest, 1.0.0 tags visible

# Confirm image digest matches local build
LOCAL_DIGEST=$(docker inspect flask-api:latest --format "{{.Id}}")
REMOTE_DIGEST=$(aws ecr describe-images \
  --repository-name handson-flask-api \
  --image-ids imageTag=latest \
  --query "imageDetails[0].imageDigest" --output text)
echo "Local:  $LOCAL_DIGEST"
echo "Remote: $REMOTE_DIGEST"
# Digests should match (same image)

# Confirm lifecycle policy is set
aws ecr get-lifecycle-policy \
  --repository-name handson-flask-api \
  --query "lifecyclePolicyText" | python3 -m json.tool
# Expected: policy keeping last 10 images
```

### 7.3 Functional Tests
```bash
# Test 1: Pull image from ECR and run it
docker pull $ECR_URL:latest
docker run -d --name ecr-test -p 5001:5000 $ECR_URL:latest
sleep 3
curl -s http://localhost:5001/health | python3 -m json.tool
# Expected: {"status": "ok"}
docker stop ecr-test && docker rm ecr-test

# Test 2: Verify image scan results
aws ecr describe-image-scan-findings \
  --repository-name handson-flask-api \
  --image-id imageTag=latest \
  --query "imageScanFindings.findingSeverityCounts"
# Expected: no CRITICAL findings

# Test 3: Verify lifecycle policy works (push 12 test images, only 10 kept)
for i in {1..12}; do
  docker tag flask-api:latest $ECR_URL:lifecycle-test-$i
  docker push $ECR_URL:lifecycle-test-$i
done
sleep 10
COUNT=$(aws ecr list-images --repository-name handson-flask-api \
  --filter tagStatus=TAGGED \
  --query "length(imageIds)" --output text)
echo "Total tagged images: $COUNT"
# Expected: lifecycle policy keeps only last 10 of the test tags
```

### 7.4 Terraform State Verification
```bash
cd terraform
# Confirm ECR resource in state
terraform state list
# Expected: aws_ecr_repository.flask_api, aws_ecr_lifecycle_policy.flask_api

terraform output
# Expected: ecr_url, ecr_arn
```

### 7.5 Expected Successful Outputs
| Check | Expected Result |
|-------|----------------|
| ECR repository exists | `repositoryUri` returned |
| `latest` tag in ECR | Image visible in console/CLI |
| Pull from ECR | `docker pull` succeeds |
| Run from ECR | `/health` returns 200 |
| Image scan | No CRITICAL vulnerabilities |
| Lifecycle policy | Attached to repository |

### 7.6 Verification Checklist
- [ ] ECR repository `handson-flask-api` created
- [ ] `docker login` to ECR succeeded
- [ ] `latest` and `1.0.0` tags pushed to ECR
- [ ] Image pulled from ECR and runs successfully
- [ ] `/health` returns 200 from ECR-pulled image
- [ ] Image scan completed (no CRITICAL findings)
- [ ] Lifecycle policy attached (keeps last 10 images)
- [ ] Terraform state shows ECR resources

---

## Screenshots to Take
- [ ] ECR repository created in console
- [ ] `docker login` success
- [ ] `docker push` output showing layers uploaded
- [ ] ECR console showing image with tags and size
- [ ] Image scan results (CVE findings)
- [ ] Lifecycle policy configured
