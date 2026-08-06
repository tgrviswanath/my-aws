# Project 5.6 — AWS App Runner: Deploy from ECR, Auto-Scaling & Custom Domain

## Overview

Deploy a containerized application directly from an Amazon ECR image using AWS App Runner. No cluster management, no load balancer configuration, no networking setup required. Configure auto-scaling from 1 to 10 instances and optionally map a custom domain.

---

## Prerequisites Check

```bash
# Check AWS CLI
aws --version
# Expected: aws-cli/2.x (App Runner CLI support requires v2)

# Check credentials
aws sts get-caller-identity

AWS_REGION="us-east-1"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Verify App Runner is available in your region
aws apprunner list-services --region $AWS_REGION 2>&1 | grep -v "Error" && echo "App Runner available"

# Check ECR image exists (from project 5.1)
aws ecr describe-images \
  --repository-name flask-app \
  --image-id imageTag=1.0.0 \
  --region $AWS_REGION \
  --query 'imageDetails[0].imageTags' \
  --output text
```

**Required IAM permissions:**
- `apprunner:CreateService`
- `apprunner:DescribeService`
- `apprunner:UpdateService`
- `apprunner:DeleteService`
- `apprunner:ListServices`
- `apprunner:CreateConnection` (for ECR access)
- `iam:CreateRole`, `iam:AttachRolePolicy` (for App Runner ECR access role)

---

## Decision Point 1: App Runner vs ECS Fargate

| Factor | App Runner | ECS Fargate |
|--------|-----------|-------------|
| Setup time | ~5 minutes | 30-60 minutes |
| Networking | ✅ Automatic (no VPC required) | Manual VPC, subnets, SGs |
| Load balancer | ✅ Built-in (no ALB to manage) | Manual ALB setup |
| Auto-scaling | ✅ Automatic (request-based) | Manual: policies + CloudWatch |
| Cost | $0.064/vCPU-hr + $0.007/GB-hr | $0.04048/vCPU-hr + $0.004445/GB-hr |
| Paused service | $0 (scales to 0) | Fargate: still charges per task |
| Custom domain | ✅ Built-in | Via ALB + Route 53 |
| VPC integration | Optional (add-on) | Native |
| Full control | ❌ Less | ✅ Full |
| Best for | Quick deployments ✅, simple apps | Complex architectures ✅, VPC-required |

**Decision:** Use **App Runner** when you want the simplest possible deployment path. Use **Fargate** when you need VPC integration, specific networking, or fine-grained control.

---

## 1. Create the App Runner ECR Access Role

```bash
# App Runner needs permission to pull from ECR
aws iam create-role \
  --role-name AppRunnerECRAccessRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {
        "Service": "build.apprunner.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }]
  }' 2>/dev/null || echo "Role may already exist"

# Attach the ECR access policy
aws iam attach-role-policy \
  --role-name AppRunnerECRAccessRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess

ACCESS_ROLE_ARN="arn:aws:iam::$AWS_ACCOUNT_ID:role/AppRunnerECRAccessRole"
echo "Access Role ARN: $ACCESS_ROLE_ARN"
```

---

## 2. Prepare the ECR Image

```bash
ECR_REPO="flask-app"
ECR_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:1.0.0"

# Confirm image exists
aws ecr describe-images \
  --repository-name $ECR_REPO \
  --image-id imageTag=1.0.0 \
  --region $AWS_REGION \
  --query 'imageDetails[0].{Tags:imageTags,Size:imageSizeInBytes}' \
  --output table

echo "Image URI for App Runner: $ECR_URI"
```

---

## 3. Create the App Runner Service

### 3A. AWS Console: Create Service → Select ECR Image → Configure

See `steps_awsconsoleui.md` for the full Console walkthrough.

### 3B. AWS CLI: aws apprunner create-service

```bash
# Create App Runner service from ECR
SERVICE_ARN=$(aws apprunner create-service \
  --service-name "flask-app-runner" \
  --source-configuration "{
    \"imageRepository\": {
      \"imageIdentifier\": \"$ECR_URI\",
      \"imageRepositoryType\": \"ECR\",
      \"imageConfiguration\": {
        \"port\": \"8080\",
        \"runtimeEnvironmentVariables\": {
          \"APP_VERSION\": \"1.0.0\",
          \"APP_ENV\": \"production\"
        }
      }
    },
    \"authenticationConfiguration\": {
      \"accessRoleArn\": \"$ACCESS_ROLE_ARN\"
    },
    \"autoDeploymentsEnabled\": false
  }" \
  --instance-configuration "{
    \"cpu\": \"0.25 vCPU\",
    \"memory\": \"0.5 GB\"
  }" \
  --auto-scaling-configuration-arn "$(
    aws apprunner list-auto-scaling-configurations \
      --auto-scaling-configuration-name DefaultConfiguration \
      --region $AWS_REGION \
      --query 'AutoScalingConfigurationSummaryList[0].AutoScalingConfigurationArn' \
      --output text
  )" \
  --health-check-configuration "{
    \"protocol\": \"HTTP\",
    \"path\": \"/health\",
    \"interval\": 10,
    \"timeout\": 5,
    \"healthyThreshold\": 1,
    \"unhealthyThreshold\": 5
  }" \
  --region $AWS_REGION \
  --query 'Service.ServiceArn' \
  --output text)

echo "App Runner Service ARN: $SERVICE_ARN"
```

---

## 4. Wait for Service to Become Running

```bash
echo "Waiting for service to become RUNNING (this takes 1-3 minutes)..."

# Poll status
while true; do
  STATUS=$(aws apprunner describe-service \
    --service-arn $SERVICE_ARN \
    --region $AWS_REGION \
    --query 'Service.Status' \
    --output text)
  echo "Status: $STATUS"
  if [ "$STATUS" = "RUNNING" ]; then
    break
  elif [ "$STATUS" = "CREATE_FAILED" ]; then
    echo "Service creation failed!"
    break
  fi
  sleep 15
done

# Get service URL
SERVICE_URL=$(aws apprunner describe-service \
  --service-arn $SERVICE_ARN \
  --region $AWS_REGION \
  --query 'Service.ServiceUrl' \
  --output text)

echo "Service URL: https://$SERVICE_URL"
```

---

## 5. Test the Application

### 5A. Test via Browser

Open your browser and navigate to:
- `https://<SERVICE_URL>/` — root endpoint, returns JSON with status and version
- `https://<SERVICE_URL>/health` — health endpoint, returns `{"healthy": true}`

App Runner automatically provides HTTPS — no certificate setup needed.

### 5B. Test via curl (CLI)

```bash
# Test root endpoint
curl -s https://$SERVICE_URL/ | python3 -m json.tool

# Test health endpoint
curl -s https://$SERVICE_URL/health | python3 -m json.tool

# Check HTTP status code
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://$SERVICE_URL/health)
echo "Health check HTTP status: $HTTP_CODE"
# Expected: 200
```

---

## 6. Configure Custom Auto-Scaling Policy

```bash
# Create a custom auto-scaling configuration
AUTOSCALE_ARN=$(aws apprunner create-auto-scaling-configuration \
  --auto-scaling-configuration-name "flask-app-scaling" \
  --max-concurrency 25 \
  --min-size 1 \
  --max-size 10 \
  --region $AWS_REGION \
  --query 'AutoScalingConfiguration.AutoScalingConfigurationArn' \
  --output text)

echo "Auto-scaling config ARN: $AUTOSCALE_ARN"

# Update service to use custom auto-scaling
aws apprunner update-service \
  --service-arn $SERVICE_ARN \
  --auto-scaling-configuration-arn $AUTOSCALE_ARN \
  --region $AWS_REGION

echo "Auto-scaling config updated"
```

**Auto-scaling parameters explained:**
- `maxConcurrency: 25` — scale out when more than 25 concurrent requests per instance
- `minSize: 1` — always keep at least 1 instance running
- `maxSize: 10` — never scale beyond 10 instances

---

## 7. Update Service to Deploy a New Version

```bash
# Tag new image version
docker pull $ECR_URI  # reuse existing for demo
docker tag $ECR_URI "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:2.0.0"
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin \
  "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:2.0.0"

# Update the service to use the new image
NEW_ECR_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:2.0.0"

aws apprunner update-service \
  --service-arn $SERVICE_ARN \
  --source-configuration "{
    \"imageRepository\": {
      \"imageIdentifier\": \"$NEW_ECR_URI\",
      \"imageRepositoryType\": \"ECR\",
      \"imageConfiguration\": {
        \"port\": \"8080\",
        \"runtimeEnvironmentVariables\": {
          \"APP_VERSION\": \"2.0.0\"
        }
      }
    },
    \"authenticationConfiguration\": {
      \"accessRoleArn\": \"$ACCESS_ROLE_ARN\"
    }
  }" \
  --region $AWS_REGION

echo "Update initiated. Waiting for RUNNING..."
```

---

## 8. Associate a Custom Domain (Optional)

```bash
# Associate a custom domain (requires Route 53 hosted zone or external DNS)
DOMAIN="app.yourdomain.com"

aws apprunner associate-custom-domain \
  --service-arn $SERVICE_ARN \
  --domain-name $DOMAIN \
  --region $AWS_REGION

# Get DNS validation records
aws apprunner describe-custom-domains \
  --service-arn $SERVICE_ARN \
  --region $AWS_REGION \
  --query 'CustomDomains[0].{Domain:DomainName,Status:Status,DNSTarget:DNSTarget}' \
  --output table

# Note: After association, add CNAME records in your DNS provider:
# <domain> -> <service-url>
# For certificate validation records, check the output of describe-custom-domains
```

---

## 9. View Logs and Metrics

```bash
# List App Runner log groups
aws logs describe-log-groups \
  --log-group-name-prefix "/aws/apprunner/flask-app-runner" \
  --region $AWS_REGION \
  --query 'logGroups[*].logGroupName' \
  --output text

# View application logs
aws logs tail "/aws/apprunner/flask-app-runner/$SERVICE_ARN/application" \
  --region $AWS_REGION \
  --since 1h 2>/dev/null || \
aws logs describe-log-streams \
  --log-group-name "/aws/apprunner/flask-app-runner" \
  --region $AWS_REGION \
  --query 'logStreams[0].logStreamName' \
  --output text
```

---

## 10. Cleanup

```bash
# Delete App Runner service
aws apprunner delete-service \
  --service-arn $SERVICE_ARN \
  --region $AWS_REGION

# Wait for deletion
while true; do
  STATUS=$(aws apprunner describe-service \
    --service-arn $SERVICE_ARN \
    --region $AWS_REGION \
    --query 'Service.Status' \
    --output text 2>/dev/null)
  if [ -z "$STATUS" ] || [ "$STATUS" = "DELETED" ]; then
    echo "Service deleted"
    break
  fi
  echo "Waiting for deletion... ($STATUS)"
  sleep 10
done

# Delete custom auto-scaling config
aws apprunner delete-auto-scaling-configuration \
  --auto-scaling-configuration-arn $AUTOSCALE_ARN \
  --region $AWS_REGION 2>/dev/null || true

# Delete IAM role (optional)
aws iam detach-role-policy \
  --role-name AppRunnerECRAccessRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess
aws iam delete-role --role-name AppRunnerECRAccessRole
```

---

## Troubleshooting

**Service stuck in `OPERATION_IN_PROGRESS`:**
- This is normal for up to 5 minutes during creation
- Check the App Runner Console for deployment logs

**`CREATE_FAILED` with "Unable to pull image":**
```bash
# Verify the access role has ECR permissions
aws iam list-attached-role-policies --role-name AppRunnerECRAccessRole
# Check the image URI is correct
aws ecr describe-images --repository-name flask-app --region $AWS_REGION
```

**`CREATE_FAILED` with "Health check failed":**
- Container must listen on the configured port (8080)
- Health check path `/health` must return HTTP 200
- Test locally: `docker run -p 8080:8080 <image>` and `curl localhost:8080/health`

**Custom domain shows "PENDING_CERTIFICATE_DNS_VALIDATION":**
- You need to add the CNAME validation record to your DNS provider
- Check the validation records: `aws apprunner describe-custom-domains`

---

## Expected Outcome

After completing this guide:

- ✅ App Runner service in RUNNING state
- ✅ Service URL returns HTTP 200 on `/` and `/health`
- ✅ Auto-scaling configured (min 1, max 10 instances)
- ✅ New image version deployable with `aws apprunner update-service`
- ✅ App Runner handles HTTPS, TLS, and load balancing automatically
- ✅ No VPC, no ALB, no security groups needed
