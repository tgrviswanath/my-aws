# Project 5.1 — Verification Guide: Single Docker App

---

## Section 1: Infrastructure Verification

Verify the ECR repository was created correctly and the image was pushed.

### 1.1 ECR Repository Exists

```bash
AWS_REGION="us-east-1"
ECR_REPO="flask-app"

# Confirm repository exists and get details
aws ecr describe-repositories \
  --repository-names $ECR_REPO \
  --region $AWS_REGION \
  --query 'repositories[0].{Name:repositoryName,URI:repositoryUri,ScanOnPush:imageScanningConfiguration.scanOnPush,Immutable:imageTagMutability}' \
  --output table
```

Expected output:
```
---------------------------------------------------------------------------
| DescribeRepositories                                                     |
+----------+-----------+-------+------------+-----------------------------+
| Immutable | Name      | ScanOnPush | URI                               |
+----------+-----------+-------+------------+-----------------------------+
| IMMUTABLE | flask-app | True  | 123456789.dkr.ecr.us-east-1.../flask-app |
+----------+-----------+-------+------------+-----------------------------+
```

### 1.2 Image is Present with Correct Tag

```bash
aws ecr describe-images \
  --repository-name $ECR_REPO \
  --region $AWS_REGION \
  --query 'imageDetails[*].{Tags:imageTags,SizeMB:imageSizeInBytes,Pushed:imagePushedAt}' \
  --output table
```

Expected: image tag `1.0.0` visible, size between 50MB–200MB.

### 1.3 Lifecycle Policy Applied

```bash
aws ecr get-lifecycle-policy \
  --repository-name $ECR_REPO \
  --region $AWS_REGION \
  --query 'lifecyclePolicyText' \
  --output text | python3 -m json.tool
```

Expected: JSON with two rules (priority 1 and 2).

### 1.4 Scan Configuration Enabled

```bash
aws ecr get-repository-policy \
  --repository-name $ECR_REPO \
  --region $AWS_REGION 2>/dev/null || echo "No resource policy (OK for private repo)"

aws ecr describe-repositories \
  --repository-names $ECR_REPO \
  --region $AWS_REGION \
  --query 'repositories[0].imageScanningConfiguration'
```

Expected: `{"scanOnPush": true}`

---

## Section 2: Functionality Verification

Verify the container actually runs correctly and the image behaves as expected.

### 2.1 Local Container Runs

```bash
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO"

# Pull from ECR and run
docker pull $ECR_URI:1.0.0

docker run -d \
  --name flask-verify \
  -p 8080:8080 \
  $ECR_URI:1.0.0

sleep 3

# Test root endpoint
curl -s http://localhost:8080/ | python3 -m json.tool
```

Expected response:
```json
{
  "hostname": "abc123def456",
  "status": "ok",
  "version": "1.0.0"
}
```

### 2.2 Health Endpoint Returns 200

```bash
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health)
echo "Health check HTTP status: $HTTP_CODE"
# Expected: 200
```

### 2.3 Container Runs as Non-Root

```bash
docker exec flask-verify whoami
# Expected: appuser

docker exec flask-verify id
# Expected: uid=1001(appuser) gid=1001(appgroup)
```

### 2.4 Multi-Stage Build — Image Size Check

```bash
docker images flask-app:1.0.0 --format "Size: {{.Size}}"
# Expected: < 200MB (typically 120-160MB for python:3.11-slim base)
```

### 2.5 Scan Results — No Critical Findings

```bash
aws ecr describe-image-scan-findings \
  --repository-name $ECR_REPO \
  --image-id imageTag=1.0.0 \
  --region $AWS_REGION \
  --query 'imageScanFindings.findingSeverityCounts' \
  --output table
```

Expected: `CRITICAL: 0` (or key absent)

### 2.6 Cleanup Test Container

```bash
docker stop flask-verify && docker rm flask-verify
```

---

## Common Issues

| Issue | Symptom | Fix |
|-------|---------|-----|
| Auth token expired | `no basic auth credentials` on push | Re-run `aws ecr get-login-password \| docker login ...` (token expires after 12h) |
| Wrong region | Repository not found | Ensure `--region` matches where you created the repo; check top-right in Console |
| Container exits immediately | `docker ps` shows exited status | Run `docker logs flask-verify` — likely a Python import error; check requirements.txt |
| Non-root check fails | `whoami` returns `root` | Verify `USER appuser` line exists in Dockerfile final stage; rebuild image |
| Image size unexpectedly large | >400MB | Check Dockerfile uses `python:3.11-slim` not `python:3.11`; verify multi-stage is working with `docker history` |
