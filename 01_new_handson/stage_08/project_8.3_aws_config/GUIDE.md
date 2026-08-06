# Project 8.3 — AWS Config
## Configuration Recorder, Conformance Pack (CIS Level 1), Custom Rules, Auto-Remediation

---

## Prerequisites Check

- [ ] AWS CLI configured: `aws sts get-caller-identity`
- [ ] IAM permissions: `config:*`, `s3:*`, `sns:*`, `iam:CreateRole`, `ssm:*`
- [ ] S3 bucket for Config delivery: `aws s3 mb s3://my-config-bucket-$(aws sts get-caller-identity --query Account --output text)`
- [ ] SNS topic for notifications (optional)
- [ ] Region: `us-east-1`
- [ ] Note: Config charges $0.003 per configuration item recorded

```bash
# Verify access
aws sts get-caller-identity
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Account: $ACCOUNT_ID"
```

---

## Decision Point 1

**AWS Config vs CloudTrail — what's the difference?**

| Service | What It Answers | Data | Use For |
|---------|----------------|------|---------|
| **AWS Config** ✅ | "What do my resources look like now and over time?" | Resource configurations, compliance state | Drift detection, compliance, audit |
| **CloudTrail** | "What API calls were made, by whom, when?" | API event logs | Security incidents, access audit |
| **Both together** | Full picture | Config state + who changed it | Complete compliance program |

**Config tells you:**
- An S3 bucket has public access (non-compliant)
- An EBS volume is unencrypted
- An EC2 security group has port 0.0.0.0/0 open
- How a resource's configuration changed over 90 days

**CloudTrail tells you:**
- Who ran `DeleteBucket` at 2pm yesterday
- Which IAM user modified a security group
- All `AssumeRole` calls today

**Verdict:** Use Config for compliance posture, CloudTrail for security investigation.

---

## 1. Architecture Overview

```
AWS Resources (EC2, S3, RDS, IAM...)
        │
        │  Configuration changes
        ▼
  Config Recorder
        │
        ├──→ S3 Bucket (configuration history)
        ├──→ SNS Topic (change notifications)
        │
        ▼
  Config Rules
  ├── Managed Rules (AWS-provided)
  │   └── ec2-ebs-encryption-by-default
  ├── Conformance Pack (CIS Level 1)
  │   └── 30+ bundled rules
  └── Custom Rule (Lambda)
      └── check-unencrypted-ebs
              │
              ▼
  Auto-Remediation (SSM Automation)
      └── EncryptEBSVolume document
```

---

## 2. Create S3 Bucket and IAM Role for Config

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
CONFIG_BUCKET="aws-config-delivery-${ACCOUNT_ID}"

# Create S3 bucket
aws s3 mb s3://${CONFIG_BUCKET} --region us-east-1

# Block public access
aws s3api put-public-access-block \
  --bucket $CONFIG_BUCKET \
  --public-access-block-configuration \
  "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

# Bucket policy (required for Config to write)
cat > /tmp/config-bucket-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AWSConfigBucketPermissionsCheck",
      "Effect": "Allow",
      "Principal": {"Service": "config.amazonaws.com"},
      "Action": "s3:GetBucketAcl",
      "Resource": "arn:aws:s3:::${CONFIG_BUCKET}",
      "Condition": {
        "StringEquals": {"AWS:SourceAccount": "$ACCOUNT_ID"}
      }
    },
    {
      "Sid": "AWSConfigBucketDelivery",
      "Effect": "Allow",
      "Principal": {"Service": "config.amazonaws.com"},
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::${CONFIG_BUCKET}/AWSLogs/${ACCOUNT_ID}/Config/*",
      "Condition": {
        "StringEquals": {
          "s3:x-amz-acl": "bucket-owner-full-control",
          "AWS:SourceAccount": "$ACCOUNT_ID"
        }
      }
    }
  ]
}
EOF

aws s3api put-bucket-policy \
  --bucket $CONFIG_BUCKET \
  --policy file:///tmp/config-bucket-policy.json
```

---

## 3. Enable Configuration Recorder

```bash
# Create Config service role
aws iam create-service-linked-role \
  --aws-service-name config.amazonaws.com 2>/dev/null || echo "Role exists"

# Create configuration recorder (record all supported resources)
aws configservice put-configuration-recorder \
  --configuration-recorder '{
    "name": "default",
    "roleARN": "arn:aws:iam::'"$ACCOUNT_ID"':role/aws-service-role/config.amazonaws.com/AWSServiceRoleForConfig",
    "recordingGroup": {
      "allSupported": true,
      "includeGlobalResourceTypes": true
    }
  }'

# Create delivery channel
aws configservice put-delivery-channel \
  --delivery-channel '{
    "name": "default",
    "s3BucketName": "'"$CONFIG_BUCKET"'",
    "configSnapshotDeliveryProperties": {
      "deliveryFrequency": "TwentyFour_Hours"
    }
  }'

# Start recording
aws configservice start-configuration-recorder \
  --configuration-recorder-name default

# Verify
aws configservice describe-configuration-recorder-status \
  --query 'ConfigurationRecordersStatus[0].{Name:name,Recording:recording}'
```

---

## 4. Add Conformance Pack (CIS Level 1)

```bash
# Deploy CIS AWS Foundations Benchmark Level 1 conformance pack
# This deploys 30+ managed Config rules aligned to CIS controls

aws configservice put-conformance-pack \
  --conformance-pack-name "CIS-Level1-Benchmark" \
  --template-s3-uri "s3://aws-conformance-packs-us-east-1/Operational-Best-Practices-for-CIS-AWS-v1.4-Level1.yaml" \
  --delivery-s3-bucket "$CONFIG_BUCKET"

# Check deployment status
aws configservice describe-conformance-pack-status \
  --conformance-pack-names "CIS-Level1-Benchmark" \
  --query 'ConformancePackStatusDetails[0].{Status:ConformancePackState,Reason:ConformancePackStatusReason}'

# List rules in conformance pack
aws configservice describe-conformance-pack-compliance \
  --conformance-pack-name "CIS-Level1-Benchmark" \
  --query 'ConformancePackRuleComplianceList[].[ConfigRuleName,ComplianceType]' \
  --output table
```

---

## 5A. Console: Enable Config with Conformance Pack

**Step-by-step in AWS Management Console:**

1. Navigate to **AWS Config** → **Get started** (if first time)
2. **Settings**:
   - Record all resources supported in this region: ✅
   - Include global resources (IAM): ✅
   - AWS Config role: Create AWS Config service-linked role
   - S3 bucket: Create new or use existing `aws-config-delivery-ACCOUNT_ID`
3. Click **Next** → **Rules** (skip for now, add via conformance pack)
4. Click **Confirm** → Recording starts
5. Navigate to **Conformance packs** → **Deploy conformance pack**
6. Select template: **AWS-provided template** → find `CIS AWS Foundations Benchmark Level 1`
7. Enter name: `CIS-Level1-Benchmark`
8. Click **Deploy conformance pack**

---

## 5B. CLI: Create Custom Rule for Unencrypted EBS

```bash
# Create Lambda function for custom Config rule
cat > /tmp/check_ebs_encryption.py << 'PYEOF'
import json
import boto3

def lambda_handler(event, context):
    invoking_event = json.loads(event['invokingEvent'])
    config_item = invoking_event['configurationItem']
    
    if config_item['resourceType'] != 'AWS::EC2::Volume':
        return put_evaluations(event, 'NOT_APPLICABLE', config_item)
    
    # Check if volume is encrypted
    encrypted = config_item['configuration'].get('encrypted', False)
    
    compliance = 'COMPLIANT' if encrypted else 'NON_COMPLIANT'
    annotation = 'EBS volume is encrypted' if encrypted else 'EBS volume is NOT encrypted'
    
    return put_evaluations(event, compliance, config_item, annotation)

def put_evaluations(event, compliance, item, annotation=''):
    config = boto3.client('config')
    config.put_evaluations(
        Evaluations=[{
            'ComplianceResourceType': item['resourceType'],
            'ComplianceResourceId': item['resourceId'],
            'ComplianceType': compliance,
            'Annotation': annotation,
            'OrderingTimestamp': item['configurationItemCaptureTime']
        }],
        ResultToken=event['resultToken']
    )
PYEOF

# Zip and create Lambda
zip /tmp/check_ebs_encryption.zip /tmp/check_ebs_encryption.py

aws lambda create-function \
  --function-name config-check-ebs-encryption \
  --runtime python3.11 \
  --role "arn:aws:iam::${ACCOUNT_ID}:role/config-lambda-role" \
  --handler check_ebs_encryption.lambda_handler \
  --zip-file fileb:///tmp/check_ebs_encryption.zip

# Create Config rule pointing to Lambda
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "check-ebs-volume-encryption",
    "Description": "Checks that all EBS volumes are encrypted",
    "Scope": {
      "ComplianceResourceTypes": ["AWS::EC2::Volume"]
    },
    "Source": {
      "Owner": "CUSTOM_LAMBDA",
      "SourceIdentifier": "arn:aws:lambda:us-east-1:'"$ACCOUNT_ID"':function:config-check-ebs-encryption",
      "SourceDetails": [{
        "EventSource": "aws.config",
        "MessageType": "ConfigurationItemChangeNotification"
      }]
    }
  }'
```

---

## 6. Configure Auto-Remediation with SSM

```bash
# Add remediation configuration to Config rule
# Uses SSM Automation to encrypt non-compliant EBS volumes

aws configservice put-remediation-configurations \
  --remediation-configurations '[
    {
      "ConfigRuleName": "check-ebs-volume-encryption",
      "TargetType": "SSM_DOCUMENT",
      "TargetId": "AWSConfigRemediation-EncryptEBSVolume",
      "Parameters": {
        "AutomationAssumeRole": {
          "StaticValue": {
            "Values": ["arn:aws:iam::'"$ACCOUNT_ID"':role/config-remediation-role"]
          }
        },
        "VolumeId": {
          "ResourceValue": {
            "Value": "RESOURCE_ID"
          }
        },
        "KmsKeyId": {
          "StaticValue": {
            "Values": ["alias/aws/ebs"]
          }
        }
      },
      "Automatic": false,
      "MaximumAutomaticAttempts": 3,
      "RetryAttemptSeconds": 60
    }
  ]'
```

---

## 7. Query Compliance Status

```bash
# Overall compliance summary
aws configservice get-compliance-summary-by-config-rule \
  --query 'ComplianceSummariesByConfigRule[].{Rule:ConfigRuleName,Compliant:ComplianceContributorCount.CappedCount}'

# Non-compliant resources
aws configservice get-compliance-details-by-config-rule \
  --config-rule-name "check-ebs-volume-encryption" \
  --compliance-types NON_COMPLIANT \
  --query 'EvaluationResults[].{ResourceId:EvaluationResultIdentifier.EvaluationResultQualifier.ResourceId,Type:EvaluationResultIdentifier.EvaluationResultQualifier.ResourceType}'

# Configuration history for a resource
aws configservice get-resource-config-history \
  --resource-type AWS::EC2::Volume \
  --resource-id vol-xxxx \
  --limit 5
```

---

## 8. Set Up Config Notifications

```bash
# Create SNS topic for Config notifications
SNS_ARN=$(aws sns create-topic \
  --name aws-config-changes \
  --query TopicArn \
  --output text)

# Subscribe email
aws sns subscribe \
  --topic-arn $SNS_ARN \
  --protocol email \
  --notification-endpoint your-email@example.com

# Update delivery channel to include SNS
aws configservice put-delivery-channel \
  --delivery-channel '{
    "name": "default",
    "s3BucketName": "'"$CONFIG_BUCKET"'",
    "snsTopicARN": "'"$SNS_ARN"'",
    "configSnapshotDeliveryProperties": {
      "deliveryFrequency": "TwentyFour_Hours"
    }
  }'
```

---

## 9. Advanced: Config Aggregator (Multi-Account)

```bash
# Create aggregator to collect Config data from multiple accounts/regions
aws configservice put-configuration-aggregator \
  --configuration-aggregator-name "org-config-aggregator" \
  --organization-aggregation-source '{
    "RoleArn": "arn:aws:iam::'"$ACCOUNT_ID"':role/config-aggregator-role",
    "AllAwsRegions": true
  }'

# Query aggregated data
aws configservice list-aggregate-discovered-resources \
  --configuration-aggregator-name "org-config-aggregator" \
  --resource-type AWS::EC2::Volume \
  --limit 10
```

---

## 10. Verify Complete Setup

```bash
echo "=== AWS Config Verification ==="

# 1. Recorder running
aws configservice describe-configuration-recorder-status \
  --query 'ConfigurationRecordersStatus[0].recording'

# 2. Delivery channel configured
aws configservice describe-delivery-channels \
  --query 'DeliveryChannels[0].{S3:s3BucketName,SNS:snsTopicARN}'

# 3. Config rules active
aws configservice describe-config-rules \
  --query 'ConfigRules[].{Name:ConfigRuleName,State:ConfigRuleState}'

# 4. Conformance pack deployed
aws configservice describe-conformance-pack-status \
  --conformance-pack-names "CIS-Level1-Benchmark" \
  --query 'ConformancePackStatusDetails[0].ConformancePackState'

# 5. Overall compliance
aws configservice get-compliance-summary-by-config-rule \
  --query 'ComplianceSummariesByConfigRule | length(@)'

echo "=== Config Setup Complete ==="
```

---

## Troubleshooting

**Recorder not recording:**
```bash
aws configservice start-configuration-recorder \
  --configuration-recorder-name default
aws configservice describe-configuration-recorder-status
```

**S3 delivery failures:**
```bash
# Check delivery status
aws configservice describe-delivery-channel-status
# Common cause: bucket policy missing or wrong account
```

**Custom rule Lambda not invoked:**
```bash
# Add Lambda permission for Config
aws lambda add-permission \
  --function-name config-check-ebs-encryption \
  --statement-id config-permission \
  --action lambda:InvokeFunction \
  --principal config.amazonaws.com
```

---

## Expected Outcome

- ✅ Config recorder running, capturing all resource changes
- ✅ CIS Level 1 conformance pack deployed (30+ rules)
- ✅ Custom rule detecting unencrypted EBS volumes
- ✅ Auto-remediation configured for non-compliant volumes
- ✅ Configuration history queryable via CLI
- ✅ SNS notifications for compliance changes

---

## Cleanup

```bash
# Stop recorder (stops per-item charges)
aws configservice stop-configuration-recorder \
  --configuration-recorder-name default

# Delete conformance pack
aws configservice delete-conformance-pack \
  --conformance-pack-name "CIS-Level1-Benchmark"

# Delete custom rules
aws configservice delete-config-rule \
  --config-rule-name "check-ebs-volume-encryption"

# Delete recorder
aws configservice delete-configuration-recorder \
  --configuration-recorder-name default

# Delete delivery channel
aws configservice delete-delivery-channel \
  --delivery-channel-name default

# Clean up S3 bucket
aws s3 rm s3://${CONFIG_BUCKET} --recursive
aws s3 rb s3://${CONFIG_BUCKET}

echo "Config cleanup complete — billing stops immediately"
```

---

## 5. Hands-on Implementation

### 5A. AWS Console Method
Follow the steps_awsconsoleui.md guide for step-by-step console walkthrough.

**Summary:**
1. Navigate to the relevant AWS service console
2. Create required resources using the wizard
3. Configure settings per the architecture
4. Test the deployment

### 5B. AWS CLI Method
Follow the steps.md guide for complete CLI command reference.

`ash
# Set region
export AWS_DEFAULT_REGION=us-east-1

# Verify identity
aws sts get-caller-identity

# Create main resource (see steps.md for full commands)
aws ec2 describe-vpcs --output table
`

**Prerequisites Check:**
- âœ… AWS CLI configured with ws configure
- âœ… Correct region set to us-east-1
- âœ… IAM permissions verified

**Decision Point 1:** Console vs CLI implementation
| Option | Pros | For This Project |
|--------|------|-----------------|
| AWS Console | Visual, beginner-friendly | âœ… First time |
| AWS CLI | Repeatable, scriptable | âœ… Automation |

**Expected Outcome:** All resources deployed and healthy in AWS Console.

**Troubleshooting:** If deployment fails, check IAM permissions and CloudWatch Logs.
