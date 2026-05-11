# Steps — Project 6.2 Secure OIDC GitHub Authentication

## Phase 1 — Deploy OIDC Infrastructure

```bash
cd terraform
terraform init
terraform apply \
  -var="github_org=YOUR_GITHUB_USERNAME" \
  -var="github_repo=YOUR_REPO_NAME"

terraform output role_arns
```

---

## Phase 2 — Test Each Role

```bash
# Test CI role (should work from any branch)
# In GitHub Actions workflow:
- uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: ${{ secrets.GITHUB_CI_ROLE_ARN }}
    aws-region: us-east-1

# Test CD role (only works from main branch)
# If triggered from a feature branch → should FAIL with AccessDenied

# Test Terraform role (only works from production environment)
# Must have GitHub Environment "production" configured
```

---

## Phase 3 — Verify in CloudTrail

```bash
# Find OIDC authentication events
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=AssumeRoleWithWebIdentity \
  --start-time $(date -d '1 hour ago' --iso-8601=seconds) \
  --query "Events[*].{Time:EventTime,User:Username,Role:Resources[0].ResourceName}" \
  --output table
```

---

## Phase 4 — Test Trust Policy Restrictions

```bash
# Create a test workflow that tries to use the CD role from a feature branch
# It should fail with:
# Error: Not authorized to perform sts:AssumeRoleWithWebIdentity

# This proves the trust policy is working correctly
```

---

## Phase 5 — Audit OIDC Configuration

```bash
# List all OIDC providers
aws iam list-open-id-connect-providers

# Get provider details
aws iam get-open-id-connect-provider \
  --open-id-connect-provider-arn $(terraform output -raw oidc_provider_arn)

# List roles that trust GitHub OIDC
aws iam list-roles \
  --query "Roles[?contains(AssumeRolePolicyDocument, 'token.actions.githubusercontent.com')].{Name:RoleName,ARN:Arn}" \
  --output table
```

---

## Screenshots to Take
- [ ] OIDC provider created in IAM console
- [ ] Three roles with different trust policies
- [ ] CI role working from PR workflow
- [ ] CD role failing from feature branch (trust policy working)
- [ ] CloudTrail showing `AssumeRoleWithWebIdentity` events
- [ ] JWT token decoded showing `sub` claim with repo + ref
