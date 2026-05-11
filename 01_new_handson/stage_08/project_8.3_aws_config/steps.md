# Steps — Project 8.3 AWS Config Compliance Automation

## Phase 1 — Deploy

```bash
cd terraform
terraform init
terraform apply -var="alert_email=your@email.com" -auto-approve
```

---

## Phase 2 — View Compliance Dashboard

```
1. AWS Console → Config → Dashboard
2. See: Compliant vs Non-Compliant resources
3. Click a rule → see which resources are non-compliant
4. Click a resource → see full configuration history
```

---

## Phase 3 — Trigger a Non-Compliance Event

```bash
# Create an unencrypted S3 bucket (violates s3-encryption rule)
aws s3 mb s3://test-unencrypted-bucket-$(date +%s)

# Wait 2-3 minutes for Config to evaluate
# Check compliance
aws configservice get-compliance-details-by-config-rule \
  --config-rule-name s3-bucket-server-side-encryption-enabled \
  --compliance-types NON_COMPLIANT \
  --query "EvaluationResults[*].EvaluationResultIdentifier.EvaluationResultQualifier.ResourceId"

# Check your email for the compliance alert
```

---

## Phase 4 — View Configuration History

```bash
# See all configuration changes for an EC2 instance
aws configservice get-resource-config-history \
  --resource-type AWS::EC2::Instance \
  --resource-id i-XXXXXXXXXX \
  --limit 5 \
  --query "configurationItems[*].{Time:configurationItemCaptureTime,Status:configurationItemStatus}"
```

---

## Phase 5 — Query Config with SQL

```bash
# Find all non-compliant resources
aws configservice select-resource-config \
  --expression "SELECT resourceId, resourceType, configuration WHERE configuration.publiclyAccessible = 'true' AND resourceType = 'AWS::RDS::DBInstance'"
```

---

## Screenshots to Take
- [ ] Config dashboard showing compliance percentage
- [ ] Non-compliant resource (unencrypted S3 bucket)
- [ ] Compliance alert email received
- [ ] Resource configuration history timeline
- [ ] Config rule evaluation results
