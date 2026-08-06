# Project 5.3 — Verification Guide: Amazon ECR

---

## Section 1: Infrastructure Verification

Verify the ECR repository, configuration, lifecycle policy, and permissions.

### 1.1 Repository Exists with Correct Settings

```bash
AWS_REGION="us-east-1"
ECR_REPO="my-app"

aws ecr describe-repositories \
  --repository-names $ECR_REPO \
  --region $AWS_REGION \
  --query 'repositories[0].{
    Name: repositoryName,
    URI: repositoryUri,
    Immutable: imageTagMutability,
    ScanOnPush: imageScanningConfiguration.scanOnPush,
    Encryption: encryptionConfiguration.encryptionType
  }' \
  --output table
```

Expected:
- `Immutable`: `IMMUTABLE`
- `ScanOnPush`: `True`
- `Encryption`: `AES256`

### 1.2 Multiple Image Tags Present

```bash
aws ecr describe-images \
  --repository-name $ECR_REPO \
  --region $AWS_REGION \
  --query 'sort_by(imageDetails, &imagePushedAt)[*].{
    Tag: imageTags[0],
    Size: imageSizeInBytes,
    Pushed: imagePushedAt,
    Scan: imageScanStatus.status
  }' \
  --output table
```

Expected: 7+ rows with tags `1.0.0` through `1.0.6` and `latest`.

### 1.3 Lifecycle Policy Applied

```bash
aws ecr get-lifecycle-policy \
  --repository-name $ECR_REPO \
  --region $AWS_REGION \
  --query 'lifecyclePolicyText' \
  --output text | python3 -m json.tool
```

Expected: JSON with `rules` array containing 2 rules (priorities 1 and 2).

### 1.4 Cross-Account Repository Policy Set

```bash
aws ecr get-repository-policy \
  --repository-name $ECR_REPO \
  --region $AWS_REGION \
  --query 'policyText' \
  --output text | python3 -m json.tool
```

Expected: JSON showing `AllowCrossAccountPull` statement with trusted account ARN.

---

## Section 2: Functionality Verification

### 2.1 Authentication Works

```bash
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin \
  "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

# Expected: Login Succeeded
```

### 2.2 Image Pull from ECR

```bash
ECR_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO"

docker pull $ECR_URI:1.0.0
# Expected: layers pulled or "Already up to date"
```

### 2.3 Scan Results Available

```bash
aws ecr describe-image-scan-findings \
  --repository-name $ECR_REPO \
  --region $AWS_REGION \
  --image-id imageTag=1.0.0 \
  --query '{
    Status: imageScanStatus.status,
    Severity: imageScanFindings.findingSeverityCounts
  }' \
  --output json
```

Expected: `Status` = `COMPLETE`, severity counts present (CRITICAL should be 0 for official base images).

### 2.4 IMMUTABLE Tags Reject Overwrites

```bash
# This should FAIL because tags are immutable
docker pull python:3.11-slim
docker tag python:3.11-slim $ECR_URI:1.0.0
docker push $ECR_URI:1.0.0 2>&1 | grep -i "tag already exists\|immutable"
# Expected: error message mentioning immutable or tag already exists
```

### 2.5 Image Count (Lifecycle Policy Test)

```bash
IMAGE_COUNT=$(aws ecr describe-images \
  --repository-name $ECR_REPO \
  --region $AWS_REGION \
  --query 'length(imageDetails)' \
  --output text)
echo "Total images in repo: $IMAGE_COUNT"
# After lifecycle runs (next day): should be <= 5 tagged + 1 untagged
```

---

## Common Issues

| Issue | Symptom | Fix |
|-------|---------|-----|
| Authorization token expired | `no basic auth credentials` | Re-run `aws ecr get-login-password \| docker login ...` (valid 12h) |
| `ImageTagAlreadyExistsException` | Push fails with tag conflict | Tags are IMMUTABLE — use a new version tag; or recreate repo with MUTABLE if needed for dev |
| Lifecycle policy not deleting images | Old tags still present after 24h | Check tag prefix filter — `tagPrefixList: ["1"]` only matches tags starting with "1"; use `tagStatus: tagged` with no prefix to match all |
| Scan status shows `UNSUPPORTED_IMAGE` | Multi-arch or Windows images | ECR scanning only supports Linux AMD64 images |
| Cross-account pull denied | `AccessDenied` on `BatchGetImage` | Ensure the repository policy AND the pulling account's IAM policy both allow required actions; `GetAuthorizationToken` must be in IAM not resource policy |
