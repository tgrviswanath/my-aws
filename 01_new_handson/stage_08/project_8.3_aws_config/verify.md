# Verification & Validation — Project 8.3 AWS Config Compliance Automation

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| Config Recorder | AWS Config → Settings | Recording = **ON**, all resource types |
| Delivery Channel | AWS Config → Settings | S3 bucket configured |
| Config Rules | AWS Config → Rules | All rules listed, evaluation status shown |
| Compliance Dashboard | AWS Config → Dashboard | Compliant/Non-compliant counts visible |
| SNS Notification | AWS Config → Settings | SNS topic for notifications configured |
| S3 Config Bucket | S3 → Buckets | `handson-config-*` bucket exists |

📸 Screenshot: AWS Config Dashboard showing compliant/non-compliant rule counts  
📸 Screenshot: Config Rules list with compliance status per rule  
📸 Screenshot: Non-compliant resource detail (e.g. unencrypted S3 bucket)  
📸 Screenshot: compliance_checker.py output

---

## 2. AWS CLI Verification

```bash
# 2.1 Confirm Config recorder is ON
aws configservice describe-configuration-recorder-status \
  --query "ConfigurationRecordersStatus[*].{Name:name,Recording:recording,LastStatus:lastStatus}"
# Expected: recording=true, lastStatus=SUCCESS

# 2.2 List all Config rules
aws configservice describe-config-rules \
  --query "ConfigRules[*].{Name:ConfigRuleName,Source:Source.Owner,State:ConfigRuleState}"
# Expected: all rules listed with State=ACTIVE

# 2.3 Get compliance summary
aws configservice get-compliance-summary-by-config-rule \
  --query "ComplianceSummariesByConfigRule[*].{Rule:ConfigRuleName,Compliant:Compliance.ComplianceContributorCount.CappedCount}"
# Expected: compliance counts per rule

# 2.4 Get non-compliant resources for a specific rule
aws configservice get-compliance-details-by-config-rule \
  --config-rule-name restricted-ssh \
  --compliance-types NON_COMPLIANT \
  --query "EvaluationResults[*].{Resource:EvaluationResultIdentifier.EvaluationResultQualifier.ResourceId,Type:EvaluationResultIdentifier.EvaluationResultQualifier.ResourceType}"
# Expected: empty list (no open SSH SGs) or list of violations

# 2.5 Check overall account compliance
aws configservice describe-compliance-by-config-rule \
  --query "ComplianceByConfigRules[*].{Rule:ConfigRuleName,Compliance:Compliance.ComplianceType}"
# Expected: COMPLIANT or NON_COMPLIANT per rule

# 2.6 Confirm delivery channel (S3 bucket)
aws configservice describe-delivery-channels \
  --query "DeliveryChannels[*].{Name:name,S3Bucket:s3BucketName,SNS:snsTopicARN}"
# Expected: S3 bucket and SNS topic configured

# 2.7 Run compliance checker
python code/compliance_checker.py
# Expected: summary showing X/Y rules compliant, violations listed
```

---

## 3. Terraform State Verification

```bash
cd terraform

# 3.1 List all resources
terraform state list
# Expected:
# aws_config_configuration_recorder.main
# aws_config_delivery_channel.main
# aws_config_configuration_recorder_status.main
# aws_config_config_rule.s3_encryption
# aws_config_config_rule.restricted_ssh
# aws_config_config_rule.restricted_ports
# aws_config_config_rule.required_tags
# aws_config_config_rule.rds_public_access
# aws_config_config_rule.cloudtrail_enabled
# aws_s3_bucket.config
# aws_sns_topic.config_alerts

# 3.2 Inspect recorder
terraform state show aws_config_configuration_recorder.main
# Shows: recording_group.all_supported=true

# 3.3 No drift
terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

---

## 4. Health Check — Trigger a Compliance Evaluation

```bash
# Force re-evaluation of all rules
aws configservice start-config-rules-evaluation \
  --config-rule-names restricted-ssh s3-bucket-server-side-encryption-enabled

# Wait ~30 seconds for evaluation
sleep 30

# Check results
aws configservice describe-compliance-by-config-rule \
  --config-rule-names restricted-ssh s3-bucket-server-side-encryption-enabled \
  --query "ComplianceByConfigRules[*].{Rule:ConfigRuleName,Status:Compliance.ComplianceType}"
# Expected: COMPLIANT (if your resources are properly configured)

# Verify Config is recording changes — create and delete a test resource
aws ec2 create-security-group \
  --group-name test-config-sg \
  --description "Config test SG" \
  --vpc-id $(aws ec2 describe-vpcs --query "Vpcs[0].VpcId" --output text)

# Check Config recorded it
sleep 10
aws configservice get-resource-config-history \
  --resource-type AWS::EC2::SecurityGroup \
  --resource-id $(aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=test-config-sg" \
    --query "SecurityGroups[0].GroupId" --output text) \
  --limit 1 \
  --query "configurationItems[0].{ResourceId:resourceId,Status:configurationItemStatus}"
# Expected: configuration item recorded

# Cleanup test SG
aws ec2 delete-security-group \
  --group-id $(aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=test-config-sg" \
    --query "SecurityGroups[0].GroupId" --output text)
```

---

## 5. Expected Successful Outputs

**CLI — describe-compliance-by-config-rule:**
```json
[
  { "Rule": "restricted-ssh",                              "Compliance": "COMPLIANT" },
  { "Rule": "s3-bucket-server-side-encryption-enabled",   "Compliance": "COMPLIANT" },
  { "Rule": "rds-instance-public-access-check",           "Compliance": "COMPLIANT" },
  { "Rule": "cloudtrail-enabled",                         "Compliance": "COMPLIANT" }
]
```

**compliance_checker.py output:**
```
=== AWS Config Compliance Report ===
✅ COMPLIANT     restricted-ssh
✅ COMPLIANT     s3-bucket-server-side-encryption-enabled
✅ COMPLIANT     rds-instance-public-access-check
⚠️  NON_COMPLIANT required-tags  → 2 EC2 instances missing required tags
✅ COMPLIANT     cloudtrail-enabled

Summary: 7/8 rules compliant | 1 violation found
```

---

## 6. Verification Checklist

- [ ] Config recorder status = recording=true, lastStatus=SUCCESS
- [ ] All Config rules listed with State=ACTIVE
- [ ] S3 delivery bucket exists and receives Config snapshots
- [ ] SNS topic configured for Config notifications
- [ ] `restricted-ssh` rule evaluates (no open SSH SGs)
- [ ] `s3-bucket-server-side-encryption-enabled` rule evaluates
- [ ] `rds-instance-public-access-check` rule evaluates
- [ ] `cloudtrail-enabled` rule shows COMPLIANT
- [ ] Config records new resource creation (test SG captured)
- [ ] `compliance_checker.py` runs and prints summary
- [ ] `terraform plan` shows no changes

---

## Section 1: Prerequisites Verified

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 1 | AWS CLI installed | ws --version returns 2.x | Download from aws.amazon.com/cli |
| 2 | Logged in | ws sts get-caller-identity returns JSON | Run ws configure |
| 3 | Correct region | ws configure get region returns us-east-1 | Run ws configure again |

`ash
aws sts get-caller-identity
aws configure list
`

## Section 2: Resources Created

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 4 | Primary resource | Status: Active/Running/Available | Re-run creation command |
| 5 | Configuration applied | Settings match intended values | Check resource details |
| 6 | Service responding | Expected response code/output | Check security groups and logs |

`ash
# Verify resources exist
aws ec2 describe-instances --query 'Reservations[*].Instances[*].{ID:InstanceId,State:State.Name}' --output table
`

## Section 3: Validation Complete

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 7 | End-to-end test | Correct output from service | Check CloudWatch Logs |
| 8 | No errors in logs | Zero error entries | Review CloudWatch Log groups |

## Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| AccessDenied error | Missing IAM permissions | Add required policy to IAM user/role |
| Resource not found | Wrong region or name | Check ws configure get region |
| Timeout connecting | Security group blocking | Add inbound rule for required port |
| Quota exceeded | Service limit reached | Request limit increase or use different region |
| Authentication failure | Expired credentials | Run ws configure with fresh access keys |
