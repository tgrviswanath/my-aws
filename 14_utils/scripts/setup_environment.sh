#!/bin/bash
# AWS Environment Setup Script
# Sets up a complete AWS environment with best practices
# Usage: ./setup_environment.sh <environment> <app-name> <region>
# Example: ./setup_environment.sh prod myapp us-east-1

set -euo pipefail

ENVIRONMENT="${1:-dev}"
APP_NAME="${2:-myapp}"
REGION="${3:-us-east-1}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "=== AWS Environment Setup ==="
echo "Environment: $ENVIRONMENT | App: $APP_NAME | Region: $REGION"
echo "Account: $ACCOUNT_ID"
echo ""

# ── Naming Convention ─────────────────────────────────────────────────────────
RG="${APP_NAME}-${ENVIRONMENT}"
KMS_ALIAS="alias/${APP_NAME}-${ENVIRONMENT}"
BUCKET="${ACCOUNT_ID}-${APP_NAME}-${ENVIRONMENT}-assets"
ECR_REPO="${APP_NAME}-${ENVIRONMENT}"
LOG_GROUP="/aws/${APP_NAME}/${ENVIRONMENT}"

# ── KMS Key ───────────────────────────────────────────────────────────────────
echo "1. Creating KMS Key..."
KEY_ID=$(aws kms create-key \
  --description "${APP_NAME} ${ENVIRONMENT} encryption key" \
  --key-usage ENCRYPT_DECRYPT \
  --key-spec SYMMETRIC_DEFAULT \
  --enable-key-rotation \
  --tags TagKey=Environment,TagValue=$ENVIRONMENT TagKey=Application,TagValue=$APP_NAME \
  --region $REGION \
  --query 'KeyMetadata.KeyId' --output text)

aws kms create-alias \
  --alias-name $KMS_ALIAS \
  --target-key-id $KEY_ID \
  --region $REGION

echo "   KMS Key: $KEY_ID (alias: $KMS_ALIAS)"

# ── S3 Bucket ─────────────────────────────────────────────────────────────────
echo "2. Creating S3 Bucket..."
aws s3api create-bucket \
  --bucket $BUCKET \
  --region $REGION \
  $([ "$REGION" != "us-east-1" ] && echo "--create-bucket-configuration LocationConstraint=$REGION" || echo "")

aws s3api put-bucket-versioning \
  --bucket $BUCKET \
  --versioning-configuration Status=Enabled

aws s3api put-bucket-encryption \
  --bucket $BUCKET \
  --server-side-encryption-configuration "{
    \"Rules\": [{
      \"ApplyServerSideEncryptionByDefault\": {
        \"SSEAlgorithm\": \"aws:kms\",
        \"KMSMasterKeyID\": \"$KEY_ID\"
      },
      \"BucketKeyEnabled\": true
    }]
  }"

aws s3api put-public-access-block \
  --bucket $BUCKET \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,\
    BlockPublicPolicy=true,RestrictPublicBuckets=true

echo "   S3 Bucket: $BUCKET"

# ── ECR Repository ────────────────────────────────────────────────────────────
echo "3. Creating ECR Repository..."
aws ecr create-repository \
  --repository-name $ECR_REPO \
  --image-scanning-configuration scanOnPush=true \
  --encryption-configuration encryptionType=KMS,kmsKey=$KEY_ID \
  --region $REGION 2>/dev/null || echo "   ECR repo already exists"

# Set lifecycle policy
aws ecr put-lifecycle-policy \
  --repository-name $ECR_REPO \
  --lifecycle-policy-text '{
    "rules": [{
      "rulePriority": 1,
      "description": "Keep last 20 images",
      "selection": {"tagStatus": "any", "countType": "imageCountMoreThan", "countNumber": 20},
      "action": {"type": "expire"}
    }]
  }' \
  --region $REGION

echo "   ECR: $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPO"

# ── CloudWatch Log Group ──────────────────────────────────────────────────────
echo "4. Creating CloudWatch Log Group..."
aws logs create-log-group \
  --log-group-name $LOG_GROUP \
  --region $REGION 2>/dev/null || true

aws logs put-retention-policy \
  --log-group-name $LOG_GROUP \
  --retention-in-days $([ "$ENVIRONMENT" = "prod" ] && echo 90 || echo 30) \
  --region $REGION

aws logs associate-kms-key \
  --log-group-name $LOG_GROUP \
  --kms-key-id $KEY_ID \
  --region $REGION

echo "   Log Group: $LOG_GROUP"

# ── Secrets Manager ───────────────────────────────────────────────────────────
echo "5. Creating Secrets Manager entries..."
aws secretsmanager create-secret \
  --name "${APP_NAME}/${ENVIRONMENT}/config" \
  --description "Application configuration for ${APP_NAME} ${ENVIRONMENT}" \
  --kms-key-id $KEY_ID \
  --secret-string "{
    \"environment\": \"$ENVIRONMENT\",
    \"region\": \"$REGION\",
    \"s3_bucket\": \"$BUCKET\",
    \"ecr_repo\": \"$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPO\"
  }" \
  --region $REGION 2>/dev/null || echo "   Secret already exists"

echo "   Secrets Manager: ${APP_NAME}/${ENVIRONMENT}/config"

# ── CloudTrail ────────────────────────────────────────────────────────────────
echo "6. Checking CloudTrail..."
TRAIL_EXISTS=$(aws cloudtrail describe-trails \
  --query "trailList[?IsMultiRegionTrail==\`true\`].Name" \
  --output text --region $REGION)

if [ -z "$TRAIL_EXISTS" ]; then
  TRAIL_BUCKET="${ACCOUNT_ID}-cloudtrail-logs"
  aws s3api create-bucket --bucket $TRAIL_BUCKET --region $REGION \
    $([ "$REGION" != "us-east-1" ] && echo "--create-bucket-configuration LocationConstraint=$REGION" || echo "")

  aws cloudtrail create-trail \
    --name "${APP_NAME}-audit-trail" \
    --s3-bucket-name $TRAIL_BUCKET \
    --is-multi-region-trail \
    --enable-log-file-validation \
    --kms-key-id $KEY_ID \
    --region $REGION

  aws cloudtrail start-logging \
    --name "${APP_NAME}-audit-trail" \
    --region $REGION

  echo "   CloudTrail created: ${APP_NAME}-audit-trail"
else
  echo "   CloudTrail already exists: $TRAIL_EXISTS"
fi

# ── GuardDuty ─────────────────────────────────────────────────────────────────
echo "7. Checking GuardDuty..."
DETECTOR_ID=$(aws guardduty list-detectors \
  --query 'DetectorIds[0]' --output text --region $REGION 2>/dev/null || echo "")

if [ -z "$DETECTOR_ID" ] || [ "$DETECTOR_ID" = "None" ]; then
  DETECTOR_ID=$(aws guardduty create-detector \
    --enable \
    --finding-publishing-frequency FIFTEEN_MINUTES \
    --region $REGION \
    --query 'DetectorId' --output text)
  echo "   GuardDuty enabled: $DETECTOR_ID"
else
  echo "   GuardDuty already enabled: $DETECTOR_ID"
fi

# ── Budget Alert ──────────────────────────────────────────────────────────────
echo "8. Creating Budget Alert..."
BUDGET_AMOUNT=$([ "$ENVIRONMENT" = "prod" ] && echo "5000" || echo "500")

aws budgets create-budget \
  --account-id $ACCOUNT_ID \
  --budget "{
    \"BudgetName\": \"${APP_NAME}-${ENVIRONMENT}-monthly\",
    \"BudgetLimit\": {\"Amount\": \"$BUDGET_AMOUNT\", \"Unit\": \"USD\"},
    \"TimeUnit\": \"MONTHLY\",
    \"BudgetType\": \"COST\"
  }" \
  --notifications-with-subscribers "[
    {
      \"Notification\": {
        \"NotificationType\": \"ACTUAL\",
        \"ComparisonOperator\": \"GREATER_THAN\",
        \"Threshold\": 80,
        \"ThresholdType\": \"PERCENTAGE\"
      },
      \"Subscribers\": [{
        \"SubscriptionType\": \"EMAIL\",
        \"Address\": \"team@company.com\"
      }]
    }
  ]" 2>/dev/null || echo "   Budget already exists"

echo "   Budget: \$$BUDGET_AMOUNT/month with 80% alert"

# ── Output Summary ────────────────────────────────────────────────────────────
echo ""
echo "=== Environment Setup Complete ==="
echo ""
echo "KMS Key:        $KEY_ID ($KMS_ALIAS)"
echo "S3 Bucket:      $BUCKET"
echo "ECR Repository: $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPO"
echo "Log Group:      $LOG_GROUP"
echo "Secret:         ${APP_NAME}/${ENVIRONMENT}/config"
echo ""
echo "Next steps:"
echo "  1. Create VPC: terraform apply -var-file=environments/${ENVIRONMENT}.tfvars"
echo "  2. Deploy application infrastructure"
echo "  3. Set up CI/CD pipeline"
echo ""
echo "Save these values:"
echo "  export KMS_KEY_ID=$KEY_ID"
echo "  export ASSETS_BUCKET=$BUCKET"
echo "  export ECR_REPO=$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPO"
