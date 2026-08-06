# Project 5.3 — Amazon ECR: Repository Management, Lifecycle Policies & Cross-Account Pull

## Overview

Deep-dive into Amazon ECR: create a repository with best-practice settings, push an image, configure a lifecycle policy to keep only the last 5 tags, enable image scanning on push, and set up cross-account pull access via IAM repository policy.

---

## Prerequisites Check

```bash
# Check AWS CLI version (need v2 for ECR features)
aws --version
# Expected: aws-cli/2.x

# Check credentials and current account
aws sts get-caller-identity
# Note your Account ID — you'll need it

# Check Docker
docker --version

# Ensure Docker daemon is running
docker info | grep "Server Version"

# Verify ECR permissions
aws ecr describe-repositories --region us-east-1 2>&1 | grep -v "RepositoryNotFoundException" || echo "ECR accessible"
```

**Required IAM permissions for this project:**
- `ecr:CreateRepository`
- `ecr:DescribeRepositories`
- `ecr:DescribeImages`
- `ecr:GetRepositoryPolicy`
- `ecr:SetRepositoryPolicy`
- `ecr:DeleteRepositoryPolicy`
- `ecr:PutLifecyclePolicy`
- `ecr:GetLifecyclePolicy`
- `ecr:StartImageScan`
- `ecr:DescribeImageScanFindings`
- `ecr:GetAuthorizationToken`
- `ecr:BatchGetImage`
- `ecr:PutImage`
- `ecr:InitiateLayerUpload`
- `ecr:UploadLayerPart`
- `ecr:CompleteLayerUpload`

---

## Decision Point 1: ECR vs Docker Hub

| Factor | Amazon ECR | Docker Hub |
|--------|-----------|-----------|
| Privacy | Private by default | Public by default (paid for private) |
| Integration with AWS | Native (ECS, EKS, Lambda) | Requires credentials |
| Authentication | Temporary tokens via IAM | Username/password |
| Free tier | 500MB private storage | 1 free private repo |
| Scanning | Amazon Inspector built-in | Paid add-on |
| Cross-account access | Via IAM policies | Manual credential sharing |
| Pricing | $0.10/GB/month after 500MB | $0.0025/GB/month (Pro) |
| Best for | Private AWS workloads ✅ | Public images, open source ✅ |

**Decision:** Use **ECR** for any image that will be deployed on AWS. Use Docker Hub for public community images.

---

## 1. Set Up Variables

```bash
# Set your environment variables — update these for your account
AWS_REGION="us-east-1"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPO="my-app"
IMAGE_TAG="1.0.0"

# Cross-account variables (replace with real account if testing)
TRUSTED_ACCOUNT_ID="987654321098"   # Account that will pull images

echo "Main Account: $AWS_ACCOUNT_ID"
echo "Region: $AWS_REGION"
echo "ECR Base URI: $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
```

---

## 2. Create the ECR Repository

```bash
# Create repository with scanning and immutable tags enabled
aws ecr create-repository \
  --repository-name $ECR_REPO \
  --region $AWS_REGION \
  --image-scanning-configuration scanOnPush=true \
  --image-tag-mutability IMMUTABLE \
  --encryption-configuration encryptionType=AES256

# Capture the repository URI
ECR_URI=$(aws ecr describe-repositories \
  --repository-names $ECR_REPO \
  --region $AWS_REGION \
  --query 'repositories[0].repositoryUri' \
  --output text)

echo "Repository URI: $ECR_URI"
```

---

## 3. Authenticate Docker to ECR

```bash
# Get auth token and log in (token valid for 12 hours)
aws ecr get-login-password \
  --region $AWS_REGION | \
  docker login \
  --username AWS \
  --password-stdin \
  "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

# Expected output:
# Login Succeeded
```

---

## 4. Build, Tag, and Push Images

```bash
# Pull a base image to use for testing (or use your own Flask/Node image)
docker pull python:3.11-slim

# Tag it as our app image
docker tag python:3.11-slim $ECR_URI:$IMAGE_TAG
docker tag python:3.11-slim $ECR_URI:latest

# Push both tags
docker push $ECR_URI:$IMAGE_TAG
docker push $ECR_URI:latest

# Push a few more version tags to test lifecycle policy later
for v in "1.0.1" "1.0.2" "1.0.3" "1.0.4" "1.0.5" "1.0.6"; do
  docker tag python:3.11-slim $ECR_URI:$v
  docker push $ECR_URI:$v
  echo "Pushed $v"
done

# Confirm all images are in ECR
aws ecr describe-images \
  --repository-name $ECR_REPO \
  --region $AWS_REGION \
  --query 'sort_by(imageDetails, &imagePushedAt)[*].{Tag:imageTags[0],Size:imageSizeInBytes}' \
  --output table
```

---

## 5. Configure Lifecycle Policy

### 5A. AWS Console: ECR Console → Create Lifecycle Policy

1. Go to ECR → Repositories → `my-app`
2. Click **Lifecycle policy** in the left sidebar
3. Click **Create rule**
4. Set:
   - Rule priority: `1`
   - Description: `Keep last 5 tagged images`
   - Image status: **Tagged**
   - Tag prefixes: (leave empty to match all tagged images) or enter `1`
   - Match criteria: **Image count more than** → `5`
   - Action: **Expire**
5. Click **Save**

### 5B. AWS CLI: put-lifecycle-policy

```bash
# Lifecycle policy: keep last 5 tagged images, purge untagged after 1 day
aws ecr put-lifecycle-policy \
  --repository-name $ECR_REPO \
  --region $AWS_REGION \
  --lifecycle-policy-text '{
    "rules": [
      {
        "rulePriority": 1,
        "description": "Keep last 5 tagged images",
        "selection": {
          "tagStatus": "tagged",
          "tagPrefixList": ["1", "v", "latest"],
          "countType": "imageCountMoreThan",
          "countNumber": 5
        },
        "action": {
          "type": "expire"
        }
      },
      {
        "rulePriority": 2,
        "description": "Remove untagged images after 1 day",
        "selection": {
          "tagStatus": "untagged",
          "countType": "sinceImagePushed",
          "countUnit": "days",
          "countNumber": 1
        },
        "action": {
          "type": "expire"
        }
      }
    ]
  }'

# Preview what the lifecycle policy WOULD expire (dry run)
aws ecr get-lifecycle-policy-preview \
  --repository-name $ECR_REPO \
  --region $AWS_REGION \
  --query 'previewResults[*].{Tag:imageDigest,Action:action.type}' \
  --output table 2>/dev/null || echo "Preview not available — policy executes nightly"
```

---

## 6. Verify Scan Results

```bash
# Describe scan findings for a specific image
aws ecr describe-image-scan-findings \
  --repository-name $ECR_REPO \
  --region $AWS_REGION \
  --image-id imageTag=$IMAGE_TAG \
  --query '{
    Status: imageScanStatus.status,
    Counts: imageScanFindings.findingSeverityCounts
  }' \
  --output json

# Manually trigger a scan on an existing image
aws ecr start-image-scan \
  --repository-name $ECR_REPO \
  --region $AWS_REGION \
  --image-id imageTag=$IMAGE_TAG

# Wait for scan to complete and check again
sleep 30
aws ecr describe-image-scan-findings \
  --repository-name $ECR_REPO \
  --region $AWS_REGION \
  --image-id imageTag=$IMAGE_TAG \
  --query 'imageScanFindings.findingSeverityCounts'
```

---

## 7. Cross-Account Pull: Set Repository Policy

```bash
# Create a resource-based policy allowing another account to pull
aws ecr set-repository-policy \
  --repository-name $ECR_REPO \
  --region $AWS_REGION \
  --policy-text "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [
      {
        \"Sid\": \"AllowCrossAccountPull\",
        \"Effect\": \"Allow\",
        \"Principal\": {
          \"AWS\": \"arn:aws:iam::$TRUSTED_ACCOUNT_ID:root\"
        },
        \"Action\": [
          \"ecr:BatchCheckLayerAvailability\",
          \"ecr:BatchGetImage\",
          \"ecr:GetDownloadUrlForLayer\",
          \"ecr:GetRepositoryPolicy\"
        ]
      }
    ]
  }"

# Verify the policy was set
aws ecr get-repository-policy \
  --repository-name $ECR_REPO \
  --region $AWS_REGION \
  --query 'policyText' \
  --output text | python3 -m json.tool

# Note: The trusted account also needs permission to call ecr:GetAuthorizationToken
# Add this to an IAM policy in the TRUSTED account:
cat << 'EOF'
{
  "Effect": "Allow",
  "Action": "ecr:GetAuthorizationToken",
  "Resource": "*"
}
EOF
```

---

## 8. Pulling from the Trusted Account

On the trusted account side (run these commands with trusted account credentials):

```bash
# Authenticate (from trusted account)
aws ecr get-login-password \
  --region $AWS_REGION | \
  docker login \
  --username AWS \
  --password-stdin \
  "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
  # Note: use the SOURCE account ID here, not trusted account ID

# Pull the image from the source account's ECR
docker pull "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:$IMAGE_TAG"
```

---

## 9. Enhanced Image Scanning Configuration

```bash
# Upgrade to Amazon Inspector Enhanced Scanning (requires Inspector v2 enabled)
# This enables OS and language package scanning, not just OS
aws ecr put-registry-scanning-configuration \
  --region $AWS_REGION \
  --scan-type ENHANCED \
  --rules '[
    {
      "scanFrequency": "SCAN_ON_PUSH",
      "repositoryFilters": [
        {
          "filter": "*",
          "filterType": "WILDCARD"
        }
      ]
    }
  ]' 2>/dev/null || echo "Enhanced scanning requires Amazon Inspector v2 enabled in your account"

# Check current scanning configuration
aws ecr get-registry-scanning-configuration \
  --region $AWS_REGION
```

---

## 10. Cleanup

```bash
# Remove cross-account policy
aws ecr delete-repository-policy \
  --repository-name $ECR_REPO \
  --region $AWS_REGION

# Delete the repository and all images
aws ecr delete-repository \
  --repository-name $ECR_REPO \
  --region $AWS_REGION \
  --force

# Remove local images
docker rmi $ECR_URI:$IMAGE_TAG $ECR_URI:latest 2>/dev/null || true
for v in "1.0.1" "1.0.2" "1.0.3" "1.0.4" "1.0.5" "1.0.6"; do
  docker rmi $ECR_URI:$v 2>/dev/null || true
done

# Verify deletion
aws ecr describe-repositories \
  --repository-names $ECR_REPO \
  --region $AWS_REGION 2>&1 | grep -i "repositorynotfound" && echo "Repo deleted successfully"
```

---

## Troubleshooting

**`UnsupportedImageTypeException` on scan:**
- ECR only scans Linux images — Windows images are not supported for scanning

**Lifecycle policy not expiring images:**
- Lifecycle policies run once per day at a time chosen by AWS (not immediate)
- Test using the preview feature or wait 24 hours after first push

**Cross-account pull fails with AccessDenied:**
```bash
# Check the repository policy is set correctly
aws ecr get-repository-policy --repository-name $ECR_REPO --region $AWS_REGION
# Ensure the trusted account has ecr:GetAuthorizationToken in their IAM policy
# The GetAuthorizationToken permission must be on the IAM identity, not the resource policy
```

**`LifecyclePolicyPreviewNotFoundException`:**
- Normal — preview only works after a preview request; policy applies nightly

---

## Expected Outcome

After completing this guide:

- ✅ ECR repository created with immutable tags and scan-on-push enabled
- ✅ 7+ image versions pushed successfully
- ✅ Lifecycle policy keeping only last 5 tagged images configured
- ✅ Image scan results available showing severity counts
- ✅ Cross-account repository policy set allowing pull from trusted account
- ✅ `aws ecr describe-images` shows all pushed images with correct metadata
