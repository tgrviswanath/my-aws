# Project 8.3 — AWS Config: Console UI Steps
## Visual Walkthrough for AWS Management Console

---

## Prerequisites Check

- [ ] IAM permissions: `config:*`, `s3:CreateBucket`, `iam:CreateServiceLinkedRole`
- [ ] Region: **US East (N. Virginia) us-east-1**
- [ ] S3 bucket for delivery (console can create one automatically)

---

## Step 1 — Open AWS Config

1. Sign in to **AWS Management Console**
2. Search for **Config** in the search bar
3. Click **AWS Config**
4. If first time: you see the **Get started** page
5. If already enabled: you see the **Dashboard** with compliance summary

📸 Screenshot: AWS Config welcome screen with "Get started" button

---

## Step 2 — Configure Settings (Enable Recording)

1. Click **Get started** (or **Settings** in left nav if already configured)
2. **Recording** section:
   - **Record all current and future resource types supported in this region**: ✅ Selected
   - Alternatively: **Specific resource types** — choose just EC2, S3, IAM if cost-conscious
3. **AWS Config role**:
   - Select **Create AWS Config service-linked role** (recommended)
   - Or use existing role: `AWSConfigRole`
4. **Delivery method** section:
   - **Amazon S3 bucket**: Create a new bucket (auto-named) or select existing
   - **Amazon SNS topic** (optional): Create new or select existing for notifications
5. Click **Next**

📸 Screenshot: Config settings page showing recording options and S3 bucket selection

**Decision Point: Record all vs specific types?**
- **All types** → comprehensive compliance but higher cost ($0.003/config item)
- **Specific types** → cheaper, focus on key resources (EC2, S3, IAM, RDS)

---

## Step 3 — Add Config Rules (Optional at Setup)

1. **Rules** page appears during setup wizard
2. You can skip this step and add rules separately
3. Or search for and add individual rules:
   - Type `encrypted` → find `encrypted-volumes` (checks EBS encryption)
   - Type `s3` → find `s3-bucket-public-read-prohibited`
   - Type `root-access` → find `root-account-mfa-enabled`
4. Click **Next** → **Confirm**
5. Config begins recording

📸 Screenshot: Config rules list with search box and several rules checked

---

## Step 4 — View the Config Dashboard

1. After setup, navigate to **AWS Config** → **Dashboard**
2. **Compliance summary** shows:
   - Rules: X compliant, Y non-compliant
   - Resources: Total recorded resources
3. **Config timeline** shows recent configuration changes
4. **Inventory** shows all discovered resources

📸 Screenshot: Config dashboard with compliance pie chart and resource counts

---

## Step 5 — Deploy Conformance Pack (CIS Level 1)

1. In left nav: click **Conformance packs**
2. Click **Deploy conformance pack**
3. **Template details**:
   - Select **Use a sample template from AWS**
   - Browse or search: `CIS AWS Foundations Benchmark Level 1`
   - Full name: `Operational-Best-Practices-for-CIS-AWS-v1.4-Level1`
4. Click **Next**
5. **Conformance pack name**: `CIS-Level1-Benchmark`
6. **Delivery location**: Select your S3 bucket
7. Click **Next** → **Deploy conformance pack**
8. Wait 2-5 minutes for deployment to complete

📸 Screenshot: Conformance pack template selection with CIS Level 1 highlighted

**Troubleshooting — Deployment fails:**
- Check IAM: Config needs `iam:CreateServiceLinkedRole`
- Check S3 bucket policy: Config must be able to write
- Some rules require specific Config prerequisites (e.g., multi-region recording)

---

## Step 6 — View Conformance Pack Compliance

1. Click on `CIS-Level1-Benchmark` in the list
2. See compliance status for each CIS control:
   - ✅ COMPLIANT — resource meets the control
   - ❌ NON_COMPLIANT — resource violates the control
   - ⚪ NOT_APPLICABLE — resource type not applicable
3. Click on any non-compliant rule to see which resources fail
4. Example non-compliant findings:
   - `cis-aws-foundations-benchmark-iam-root-access-key-check` — root has access key
   - `cis-aws-foundations-benchmark-s3-bucket-public-read-prohibited` — public S3 bucket

📸 Screenshot: Conformance pack compliance detail showing pass/fail per CIS control

---

## Step 7 — Create Custom Rule (Unencrypted EBS Check)

1. In left nav: click **Rules**
2. Click **Add rule**
3. **Step 1 — Choose rule type**:
   - Select **Create custom Lambda rule**
4. **Step 2 — Configure rule**:
   - **Name**: `check-ebs-volume-encryption`
   - **Description**: `Checks that all EBS volumes are encrypted`
   - **AWS Lambda function ARN**: Paste your Lambda function ARN
   - **Trigger type**: `Configuration changes`
   - **Resource type**: `EC2 Volume` (AWS::EC2::Volume)
5. Click **Next** → **Save**

📸 Screenshot: Custom rule creation form with Lambda ARN field and EC2 Volume resource type

---

## Step 8 — Configure Auto-Remediation

1. Click on your rule `check-ebs-volume-encryption`
2. Click **Actions** → **Manage remediation**
3. **Remediation action**:
   - Select: `AWSConfigRemediation-EncryptEBSVolume`
4. **Resource ID parameter**: `VolumeId` → select `RESOURCE_ID`
5. **KMS Key ID**: Enter `alias/aws/ebs`
6. **Auto remediation**: Toggle ON for automatic (or leave OFF for manual)
7. Click **Save changes**

📸 Screenshot: Remediation configuration panel with SSM document selection

---

## Step 9 — Browse Resource Timeline

1. Navigate to **Resources** in left nav
2. Select resource type: `AWS EC2 Volume`
3. Click on any volume ID
4. **Timeline** shows all configuration changes over time:
   - Blue dots = configuration changes
   - Yellow dots = compliance evaluation changes
5. Click any point to see the full configuration snapshot at that time

📸 Screenshot: Resource timeline for an EBS volume showing configuration history

---

## Step 10 — Run Compliance Query

1. Navigate to **Advanced queries** (left nav)
2. Use built-in SQL-like queries:
```sql
SELECT
  resourceId,
  resourceType,
  configuration.encrypted
WHERE
  resourceType = 'AWS::EC2::Volume'
  AND configuration.encrypted = 'false'
```
3. Click **Run** — results show all unencrypted EBS volumes
4. Export results as CSV for reporting

📸 Screenshot: Advanced queries editor with SQL query and results table

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Config recorder not recording | Recorder stopped | Settings → Start recording |
| No resources showing | Just enabled, wait 15 min | Config scans take time initially |
| Conformance pack stuck | IAM permissions | Check Config role has required permissions |
| Custom rule always NOT_APPLICABLE | Wrong resource type scope | Verify resource type in rule config |
| S3 delivery failing | Bucket policy | Run `put-bucket-policy` with Config principal |

---

## Console Navigation Quick Reference

```
AWS Config
├── Dashboard          → Compliance overview
├── Rules              → Individual compliance rules
├── Conformance packs  → Bundled rule sets (CIS, PCI, HIPAA)
├── Resources          → Inventory + timeline per resource
├── Advanced queries   → SQL-like resource queries
└── Settings           → Recorder + delivery config
    └── [Rule Name]
        ├── Compliance details   → Which resources fail
        ├── Manage remediation   → SSM auto-fix
        └── Edit rule            → Modify scope/parameters
```
