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

## Phase 6 — Verification & Validation

### 6.1 AWS Console Verification
1. **IAM** → **Identity providers** → confirm `token.actions.githubusercontent.com` exists
2. **IAM** → **Roles** → confirm 3 roles: `github-ci-role`, `github-cd-role`, `github-terraform-role`
3. **IAM** → each role → **Trust relationships** → confirm correct `sub` claim conditions
4. **CloudTrail** → **Event history** → filter `AssumeRoleWithWebIdentity` → confirm events appear after workflow runs

### 6.2 CLI Verification Commands
```bash
# Confirm OIDC provider exists
aws iam list-open-id-connect-providers \
  --query "OpenIDConnectProviderList[*].Arn"
# Expected: arn:aws:iam::ACCOUNT:oidc-provider/token.actions.githubusercontent.com

# Confirm provider thumbprint and audience
OIDC_ARN=$(aws iam list-open-id-connect-providers \
  --query "OpenIDConnectProviderList[0].Arn" --output text)
aws iam get-open-id-connect-provider --open-id-connect-provider-arn $OIDC_ARN \
  --query "{URL:Url,Audiences:ClientIDList,Thumbprints:ThumbprintList}"
# Expected: URL=token.actions.githubusercontent.com, Audience=sts.amazonaws.com

# Confirm all 3 roles exist
for ROLE in github-ci-role github-cd-role github-terraform-role; do
  aws iam get-role --role-name $ROLE \
    --query "Role.{Name:RoleName,ARN:Arn}" 2>/dev/null || echo "MISSING: $ROLE"
done
# Expected: all 3 roles found

# Confirm CI role trust allows any branch
aws iam get-role --role-name github-ci-role \
  --query "Role.AssumeRolePolicyDocument" | python3 -m json.tool
# Expected: sub condition uses wildcard (repo:ORG/REPO:*)

# Confirm CD role trust restricts to main branch only
aws iam get-role --role-name github-cd-role \
  --query "Role.AssumeRolePolicyDocument" | python3 -m json.tool
# Expected: sub condition = repo:ORG/REPO:ref:refs/heads/main

# Confirm Terraform role trust restricts to production environment
aws iam get-role --role-name github-terraform-role \
  --query "Role.AssumeRolePolicyDocument" | python3 -m json.tool
# Expected: sub condition = repo:ORG/REPO:environment:production
```

### 6.3 Functional Tests
```bash
# Test 1: CI role works from any branch
# Create a workflow that uses github-ci-role from a feature branch
# Push to feature branch → workflow should authenticate successfully
# Expected: AWS auth step succeeds, aws sts get-caller-identity returns CI role ARN

# Test 2: CD role BLOCKED from feature branch
# Create a workflow that uses github-cd-role from a feature branch
# Expected: AWS auth step FAILS with:
# "Error: Not authorized to perform sts:AssumeRoleWithWebIdentity"
# This proves the trust policy sub-claim restriction works

# Test 3: CD role works from main branch
# Merge to main → CD workflow uses github-cd-role
# Expected: auth succeeds, deployment proceeds

# Test 4: Terraform role requires production environment
# Workflow without environment: production → FAILS
# Workflow with environment: production → SUCCEEDS

# Test 5: Verify CloudTrail captures OIDC auth events
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=AssumeRoleWithWebIdentity \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --query "Events[*].{Time:EventTime,User:Username,Role:Resources[0].ResourceName}" \
  --output table
# Expected: events showing GitHub Actions assuming roles

# Test 6: Confirm no long-lived credentials exist
# Check that no AWS_ACCESS_KEY_ID secrets are in GitHub repo
# GitHub → Settings → Secrets → confirm only AWS_ROLE_ARN (no key/secret)
```

### 6.4 Terraform State Verification
```bash
cd terraform
terraform state list
# Expected: aws_iam_openid_connect_provider, aws_iam_role x3, aws_iam_role_policy_attachment resources

terraform output role_arns
# Expected: map of role names to ARNs

terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

### 6.5 Expected Successful Outputs
| Check | Expected Result |
|-------|----------------|
| OIDC provider | Exists with correct thumbprint |
| 3 IAM roles | All present with correct trust policies |
| CI role from feature branch | Auth succeeds |
| CD role from feature branch | Auth FAILS (AccessDenied) |
| CD role from main | Auth succeeds |
| Terraform role without env | Auth FAILS |
| CloudTrail | `AssumeRoleWithWebIdentity` events visible |

### 6.6 Verification Checklist
- [ ] OIDC provider `token.actions.githubusercontent.com` exists in IAM
- [ ] Provider audience = `sts.amazonaws.com`
- [ ] `github-ci-role` exists — trust allows any branch (`*`)
- [ ] `github-cd-role` exists — trust restricts to `ref:refs/heads/main`
- [ ] `github-terraform-role` exists — trust restricts to `environment:production`
- [ ] CI role authenticates from feature branch (test passes)
- [ ] CD role blocked from feature branch (AccessDenied confirmed)
- [ ] CD role authenticates from main branch (test passes)
- [ ] Terraform role blocked without production environment
- [ ] CloudTrail shows `AssumeRoleWithWebIdentity` events
- [ ] No long-lived AWS credentials in GitHub secrets

---

## Screenshots to Take
- [ ] OIDC provider created in IAM console
- [ ] Three roles with different trust policies
- [ ] CI role working from PR workflow
- [ ] CD role failing from feature branch (trust policy working)
- [ ] CloudTrail showing `AssumeRoleWithWebIdentity` events
- [ ] JWT token decoded showing `sub` claim with repo + ref
