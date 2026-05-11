# Steps — Project 10.1 Multi-account AWS Organization

## Phase 1 — Enable AWS Organizations

```
1. AWS Console → Organizations → Create organization
2. Choose: Enable all features (required for SCPs)
3. Verify email for management account
```

---

## Phase 2 — Deploy with Terraform

```bash
cd terraform
terraform init && terraform apply -auto-approve
terraform output
```

---

## Phase 3 — Create Member Accounts

```bash
# Create dev account
aws organizations create-account \
  --email dev@yourcompany.com \
  --account-name "Handson-Dev" \
  --iam-user-access-to-billing ALLOW

# Move to Dev OU
DEV_ACCOUNT_ID=$(aws organizations list-accounts \
  --query "Accounts[?Name=='Handson-Dev'].Id" --output text)

DEV_OU_ID=$(terraform output -raw dev_ou_id)

aws organizations move-account \
  --account-id $DEV_ACCOUNT_ID \
  --source-parent-id $(aws organizations list-roots --query "Roots[0].Id" --output text) \
  --destination-parent-id $DEV_OU_ID
```

---

## Phase 4 — Test SCPs

```bash
# Assume role in dev account
aws sts assume-role \
  --role-arn arn:aws:iam::DEV_ACCOUNT_ID:role/OrganizationAccountAccessRole \
  --role-session-name test-scp

# Try to create resource in blocked region (should fail)
AWS_DEFAULT_REGION=ap-southeast-1 aws s3 mb s3://test-bucket-scp
# Expected: AccessDenied (SCP blocks non-approved regions)

# Try to use root account (should fail)
# Log in as root → try any API call
# Expected: AccessDenied (DenyRootUsage SCP)
```

---

## Phase 5 — View Organization in Console

```
1. Organizations → Accounts → see all accounts
2. Organizations → Policies → see SCPs
3. Click an OU → see attached SCPs
4. Click an account → see effective policies
```

---

## Screenshots to Take
- [ ] Organization structure with OUs
- [ ] SCPs attached to Workloads OU
- [ ] SCP blocking API call in unapproved region
- [ ] Member accounts in correct OUs
- [ ] Cross-account role assumption working
