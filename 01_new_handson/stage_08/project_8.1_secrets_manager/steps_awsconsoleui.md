# Project 8.1 — AWS Secrets Manager: Console UI Steps
## Visual Walkthrough for AWS Management Console

---

## Prerequisites Check

Before opening the console:
- [ ] Logged in with an IAM user/role that has `secretsmanager:*` permissions
- [ ] RDS instance exists (needed for RDS rotation setup)
- [ ] Region selected: **US East (N. Virginia) us-east-1**
- [ ] KMS key created (optional, for CMK encryption)

---

## Overview

This guide walks through the AWS Console UI to:
1. Create a secret for RDS credentials
2. Configure automatic 30-day rotation
3. Test secret retrieval
4. View secret versions and rotation history

---

## Step 1 — Open Secrets Manager

1. Sign in to the **AWS Management Console**
2. In the search bar, type **Secrets Manager**
3. Click **AWS Secrets Manager** from the results
4. You land on the **Secrets** list page

📸 Screenshot: Secrets Manager home — shows list of secrets (empty if new account)

---

## Step 2 — Store a New Secret

1. Click the orange **Store a new secret** button (top right)
2. **Secret type** page appears — choose your type:

**Decision Point: What type of secret?**
- `Credentials for Amazon RDS database` → Use when you have an RDS instance (enables rotation)
- `Credentials for other database` → For non-RDS databases
- `Other type of secret` → API keys, arbitrary JSON

For this project: select **Credentials for Amazon RDS database**

📸 Screenshot: Secret type selection screen with RDS option highlighted

---

## Step 3 — Enter RDS Credentials

1. **Username**: Enter your RDS admin username (e.g., `admin`)
2. **Password**: Enter the initial password
3. **Encryption key**: 
   - Default: `aws/secretsmanager` (AWS-managed)
   - Custom: Select your CMK from the dropdown
4. **Database**: Select your RDS instance from the list
   - If not shown, enter the DB connection info manually
5. Click **Next**

📸 Screenshot: Credential entry form with RDS database dropdown

---

## Step 4 — Configure Secret Name and Description

1. **Secret name**: Enter `prod/myapp/rds-credentials`
   - Use `/` for logical grouping (acts like folders)
   - Common patterns: `prod/service/resource`, `dev/myapp/db`
2. **Description**: `RDS PostgreSQL credentials for myapp production`
3. **Tags** — click **Add tag**:
   - Key: `Environment` | Value: `production`
   - Key: `Project` | Value: `myapp`
   - Key: `ManagedBy` | Value: `secrets-manager`
4. **Resource permissions** — leave blank for now (configure after)
5. Click **Next**

📸 Screenshot: Secret name/description form with tags section expanded

---

## Step 5 — Configure Rotation

**Decision Point: Enable rotation now or later?**
- Enable now ✅ — rotation Lambda created automatically for RDS
- Enable later — you must configure rotation Lambda manually

1. Toggle **Automatic rotation** to **ON**
2. **Rotation schedule**:
   - Select **Days** and enter `30`
   - Or use cron expression: `cron(0 2 */30 * ? *)`
3. **Rotation function**:
   - Select **Create a new Lambda function**
   - Function name: `SecretsManagerRDSPostgreSQLRotation` (auto-populated)
   - AWS creates the rotation Lambda with correct IAM permissions
4. **Use separate credentials** (optional):
   - If your rotation user is different from the app user, enable this
5. Click **Next**

📸 Screenshot: Rotation configuration with 30-day schedule and Lambda creation

---

## Step 6 — Review and Store

1. Review all settings on the summary page
2. **Sample code** section shows auto-generated boto3/SDK code — copy this!
3. Click **Store**
4. You return to the Secrets list — new secret appears

📸 Screenshot: Review page with sample code section and Store button

---

## Step 7 — View Secret Details

1. Click on your secret name `prod/myapp/rds-credentials`
2. **Secret details** page shows:
   - **Secret value**: Click **Retrieve secret value** → JSON displayed
   - **Rotation configuration**: Shows Lambda ARN and schedule
   - **Tags**: Your Environment/Project tags
   - **Resource policy**: Currently empty
3. Under **Secret versions**:
   - `AWSCURRENT` — current active version
   - `AWSPENDING` — during rotation
   - `AWSPREVIOUS` — previous version (kept for rollback)

📸 Screenshot: Secret details page with Secret value section expanded

**Troubleshooting — Can't retrieve value:**
- Check IAM: your user needs `secretsmanager:GetSecretValue`
- Check KMS: your user needs `kms:Decrypt` on the key
- Error "ResourceNotFoundException": wrong region selected

---

## Step 8 — Test Rotation Manually

1. On the secret detail page, click **Rotate secret immediately**
2. Confirm in the dialog: **Rotate**
3. The rotation status shows **Pending** then **Success**
4. Click **Retrieve secret value** again — password has changed
5. Check **Secret versions** — new `AWSCURRENT` version created

📸 Screenshot: "Rotate secret immediately" button and rotation status indicator

**Troubleshooting — Rotation fails:**
- Lambda must have VPC access to RDS (check VPC/security groups)
- Lambda execution role needs `rds:ModifyDBInstance` permission
- Check Lambda logs: CloudWatch → Log groups → `/aws/lambda/SecretsManagerRDS...`

---

## Step 9 — Add Resource Policy (Restrict Access)

1. On secret detail page, scroll to **Resource permissions**
2. Click **Edit permissions**
3. Paste the JSON policy restricting access to specific IAM role:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "AWS": "arn:aws:iam::ACCOUNT_ID:role/myapp-role"
    },
    "Action": "secretsmanager:GetSecretValue",
    "Resource": "*"
  }]
}
```
4. Click **Save**

📸 Screenshot: Resource policy editor with JSON policy entered

---

## Step 10 — Monitor with CloudTrail

1. Navigate to **CloudTrail** → **Event history**
2. Filter: **Event name** = `GetSecretValue`
3. See all access events: who accessed the secret, when, from which IP
4. For alerts: create a CloudWatch metric filter on these events

📸 Screenshot: CloudTrail event history filtered on GetSecretValue

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Secret not visible | Wrong region | Check region selector (top right) |
| Rotation Lambda fails | No VPC access to RDS | Add Lambda to same VPC/SG as RDS |
| AccessDeniedException | Missing IAM permissions | Add `secretsmanager:GetSecretValue` to policy |
| KMS error | Key policy restrictive | Add `kms:Decrypt` for your principal |
| Rotation stuck in AWSPENDING | Lambda error | Check Lambda CloudWatch logs |

---

## Console Navigation Quick Reference

```
AWS Console Search → "Secrets Manager"
├── Store a new secret          (create)
├── [Secret Name] → View        (detail page)
│   ├── Retrieve secret value   (read)
│   ├── Rotate secret immediately (force rotation)
│   ├── Edit rotation            (modify schedule)
│   └── Resource permissions    (IAM policy)
└── Settings                    (account-level config)
```
