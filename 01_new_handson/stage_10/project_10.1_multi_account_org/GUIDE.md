# Project 10.1 — AWS Organizations: Multi-Account Setup
## Organization, OUs, SCPs, and Consolidated Billing

---

## Prerequisites Check

- [ ] AWS CLI configured with **management account**: `aws sts get-caller-identity`
- [ ] IAM permissions: `organizations:*`, `iam:*`
- [ ] Email addresses for member accounts (each needs unique email)
- [ ] Region: Organizations is global (us-east-1 recommended for CLI)
- [ ] Understand: Organizations management account cannot be changed

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Management Account: $ACCOUNT_ID"
```

---

## Decision Point 1

**Single account vs multi-account strategy — when does it matter?**

| Factor | Single Account | Multi-Account ✅ |
|--------|---------------|----------------|
| **Security isolation** | ❌ All resources share IAM boundary | ✅ Separate IAM namespaces per account |
| **Blast radius** | ❌ One mistake affects everything | ✅ Failures contained per account |
| **Billing visibility** | ❌ One bill, hard to allocate | ✅ Per-account cost allocation |
| **Compliance** | ❌ Mixed workloads | ✅ Separate compliance scope per account |
| **Operational complexity** | ✅ Simple | ❌ More tooling needed (SSO, cross-account roles) |

**When to use multi-account:**
- Team size > 10 engineers
- Need separate prod/staging/dev environments
- Regulatory compliance (PCI, HIPAA) requires isolation
- Multiple product lines or business units

**Verdict:** Multi-account ✅ — security isolation and blast radius reduction justify the complexity.

---

## 1. Architecture Overview

```
Root (Management Account: billing, Organizations)
│
├── OU: Security
│   ├── Security Tools Account (GuardDuty, Security Hub aggregation)
│   └── Log Archive Account (centralized CloudTrail/Config)
│
├── OU: Infrastructure
│   └── Shared Services Account (DNS, Transit Gateway, Shared AMIs)
│
├── OU: Workloads
│   ├── OU: Dev
│   │   └── dev-account (developers, permissive SCPs)
│   ├── OU: Staging
│   │   └── staging-account (CI/CD pipelines)
│   └── OU: Prod
│       └── prod-account (production workloads, restrictive SCPs)
│
└── OU: Sandbox
    └── sandbox-account (experimentation, auto-nuke policy)

SCPs flow down: Root → OU → Account
Consolidated Billing: all accounts billed under management account
```

---

## 2. Create AWS Organization

```bash
# Create organization with all features enabled
aws organizations create-organization \
  --feature-set ALL

# Verify organization created
aws organizations describe-organization \
  --query 'Organization.{Id:Id,MasterAccountId:MasterAccountId,FeatureSet:FeatureSet}'

# Get root ID (needed for OU creation)
ROOT_ID=$(aws organizations list-roots \
  --query 'Roots[0].Id' \
  --output text)
echo "Root ID: $ROOT_ID"

# Enable all policy types
aws organizations enable-policy-type \
  --root-id $ROOT_ID \
  --policy-type SERVICE_CONTROL_POLICY

aws organizations enable-policy-type \
  --root-id $ROOT_ID \
  --policy-type TAG_POLICY

aws organizations enable-policy-type \
  --root-id $ROOT_ID \
  --policy-type BACKUP_POLICY
```

---

## 3. Create Organizational Units (OUs)

```bash
# Create top-level OUs
SECURITY_OU=$(aws organizations create-organizational-unit \
  --parent-id $ROOT_ID \
  --name "Security" \
  --query 'OrganizationalUnit.Id' --output text)

INFRA_OU=$(aws organizations create-organizational-unit \
  --parent-id $ROOT_ID \
  --name "Infrastructure" \
  --query 'OrganizationalUnit.Id' --output text)

WORKLOADS_OU=$(aws organizations create-organizational-unit \
  --parent-id $ROOT_ID \
  --name "Workloads" \
  --query 'OrganizationalUnit.Id' --output text)

SANDBOX_OU=$(aws organizations create-organizational-unit \
  --parent-id $ROOT_ID \
  --name "Sandbox" \
  --query 'OrganizationalUnit.Id' --output text)

# Create child OUs under Workloads
DEV_OU=$(aws organizations create-organizational-unit \
  --parent-id $WORKLOADS_OU \
  --name "Dev" \
  --query 'OrganizationalUnit.Id' --output text)

STAGING_OU=$(aws organizations create-organizational-unit \
  --parent-id $WORKLOADS_OU \
  --name "Staging" \
  --query 'OrganizationalUnit.Id' --output text)

PROD_OU=$(aws organizations create-organizational-unit \
  --parent-id $WORKLOADS_OU \
  --name "Prod" \
  --query 'OrganizationalUnit.Id' --output text)

echo "OUs created:"
echo "Security: $SECURITY_OU"
echo "Workloads/Dev: $DEV_OU"
echo "Workloads/Staging: $STAGING_OU"
echo "Workloads/Prod: $PROD_OU"
echo "Sandbox: $SANDBOX_OU"
```

---

## 4. Invite or Create Member Accounts

```bash
# Option A: Invite existing AWS account
aws organizations invite-account-to-organization \
  --target '{"Type": "EMAIL", "Id": "dev-team@yourcompany.com"}' \
  --notes "Joining as dev account under Workloads/Dev OU"

# Check invitation status
aws organizations list-handshakes-for-organization \
  --filter '{"ActionType": "INVITE"}' \
  --query 'Handshakes[].{Id:Id,State:State,Target:Parties[1].Id}'

# Option B: Create new account (automated — takes 5-15 minutes)
DEV_ACCOUNT_ID=$(aws organizations create-account \
  --email "aws-dev@yourcompany.com" \
  --account-name "myapp-dev" \
  --iam-user-access-to-billing ALLOW \
  --query 'CreateAccountStatus.AccountId' \
  --output text)

# Wait for account creation
aws organizations describe-create-account-status \
  --create-account-request-id \
    $(aws organizations list-create-account-status \
      --query 'CreateAccountStatuses[0].Id' --output text) \
  --query 'CreateAccountStatus.State'

# Move account to correct OU
aws organizations move-account \
  --account-id $DEV_ACCOUNT_ID \
  --source-parent-id $ROOT_ID \
  --destination-parent-id $DEV_OU

echo "Dev account $DEV_ACCOUNT_ID moved to Dev OU"
```

---

## 5A. Console: Create Organization and OUs

1. Navigate to **AWS Organizations**
2. Click **Create an organization** → **Create organization**
3. Organization created — you see the account tree
4. Click on **Root** → **Create organizational unit**:
   - Name: `Security` → Click **Create organizational unit**
   - Repeat for: `Infrastructure`, `Workloads`, `Sandbox`
5. Click on `Workloads` OU → **Create organizational unit**:
   - Name: `Dev`, then `Staging`, then `Prod`
6. To invite accounts: Click **Add an AWS account** → **Invite an existing AWS account**
7. To create new account: Click **Add an AWS account** → **Create an AWS account**

---

## 5B. CLI: Create and Attach SCPs

```bash
# SCP 1: Production — deny non-approved regions + security controls
cat > /tmp/scp-prod.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyNonProdRegions",
      "Effect": "Deny",
      "NotAction": [
        "iam:*", "organizations:*", "route53:*",
        "budgets:*", "sts:*", "support:*", "cloudfront:*"
      ],
      "Resource": "*",
      "Condition": {
        "StringNotEquals": {
          "aws:RequestedRegion": ["us-east-1", "us-west-2"]
        }
      }
    },
    {
      "Sid": "DenyDisableSecurityControls",
      "Effect": "Deny",
      "Action": [
        "cloudtrail:StopLogging",
        "cloudtrail:DeleteTrail",
        "guardduty:DeleteDetector",
        "securityhub:DisableSecurityHub",
        "config:StopConfigurationRecorder",
        "config:DeleteConfigurationRecorder"
      ],
      "Resource": "*"
    },
    {
      "Sid": "DenyRootAccountActions",
      "Effect": "Deny",
      "Action": "*",
      "Resource": "*",
      "Condition": {
        "ArnLike": {
          "aws:PrincipalArn": "arn:aws:iam::*:root"
        }
      }
    }
  ]
}
EOF

PROD_SCP=$(aws organizations create-policy \
  --content file:///tmp/scp-prod.json \
  --name "ProductionGuardrails" \
  --type SERVICE_CONTROL_POLICY \
  --description "Production security controls — restrict regions, protect audit services" \
  --query 'Policy.PolicySummary.Id' --output text)

# SCP 2: Sandbox — restrict costs
cat > /tmp/scp-sandbox.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyExpensiveServices",
      "Effect": "Deny",
      "Action": [
        "ec2:RunInstances"
      ],
      "Resource": "arn:aws:ec2:*:*:instance/*",
      "Condition": {
        "ForAnyValue:StringNotLike": {
          "ec2:InstanceType": [
            "t2.*", "t3.*", "t3a.*"
          ]
        }
      }
    },
    {
      "Sid": "DenyProductionServices",
      "Effect": "Deny",
      "Action": [
        "shield:CreateSubscription",
        "route53domains:RegisterDomain",
        "directconnect:*",
        "outposts:*"
      ],
      "Resource": "*"
    }
  ]
}
EOF

SANDBOX_SCP=$(aws organizations create-policy \
  --content file:///tmp/scp-sandbox.json \
  --name "SandboxRestrictions" \
  --type SERVICE_CONTROL_POLICY \
  --description "Sandbox: restrict to t3 family only, no expensive services" \
  --query 'Policy.PolicySummary.Id' --output text)

# Attach SCPs
aws organizations attach-policy \
  --policy-id $PROD_SCP \
  --target-id $PROD_OU

aws organizations attach-policy \
  --policy-id $SANDBOX_SCP \
  --target-id $SANDBOX_OU

echo "SCPs attached to OUs"
```

---

## 6. Set Up Consolidated Billing Budgets

```bash
# Create budget for dev account
cat > /tmp/budget-dev.json << EOF
{
  "BudgetName": "dev-monthly-budget",
  "BudgetLimit": {"Amount": "100", "Unit": "USD"},
  "TimeUnit": "MONTHLY",
  "BudgetType": "COST",
  "CostFilters": {
    "LinkedAccount": ["$DEV_ACCOUNT_ID"]
  }
}
EOF

cat > /tmp/budget-notifications.json << 'EOF'
[{
  "Notification": {
    "NotificationType": "ACTUAL",
    "ComparisonOperator": "GREATER_THAN",
    "Threshold": 80
  },
  "Subscribers": [{
    "SubscriptionType": "EMAIL",
    "Address": "finops@yourcompany.com"
  }]
}]
EOF

aws budgets create-budget \
  --account-id $ACCOUNT_ID \
  --budget file:///tmp/budget-dev.json \
  --notifications-with-subscribers file:///tmp/budget-notifications.json
```

---

## 7. Enable AWS SSO (IAM Identity Center) for Cross-Account Access

```bash
# Enable IAM Identity Center (formerly SSO)
aws sso-admin list-instances \
  --query 'Instances[].{InstanceArn:InstanceArn,IdentityStoreId:IdentityStoreId}'

# If not enabled, use console: IAM Identity Center → Enable
# After enabling, create permission sets per OU:
# - AdministratorAccess for infrastructure engineers
# - ReadOnlyAccess for auditors
# - DeveloperAccess for dev teams (custom permission set)
```

---

## 8. Cross-Account Role Access

```bash
# In management account: create cross-account role for operations
cat > /tmp/cross-account-trust.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "AWS": "arn:aws:iam::${ACCOUNT_ID}:root"
    },
    "Action": "sts:AssumeRole",
    "Condition": {
      "BoolIfExists": {
        "aws:MultiFactorAuthPresent": "true"
      }
    }
  }]
}
EOF

# Run this in each member account:
aws iam create-role \
  --role-name OrganizationAdminRole \
  --assume-role-policy-document file:///tmp/cross-account-trust.json

aws iam attach-role-policy \
  --role-name OrganizationAdminRole \
  --policy-arn arn:aws:iam::aws:policy/AdministratorAccess

# From management account, assume role in member account:
aws sts assume-role \
  --role-arn "arn:aws:iam::$DEV_ACCOUNT_ID:role/OrganizationAdminRole" \
  --role-session-name "admin-session"
```

---

## 9. Tag Policies for Cost Allocation

```bash
# Create tag policy requiring environment tag on all resources
cat > /tmp/tag-policy.json << 'EOF'
{
  "tags": {
    "Environment": {
      "tag_key": {"@@assign": "Environment"},
      "tag_value": {
        "@@assign": ["dev", "staging", "production", "sandbox"]
      },
      "enforced_for": {
        "@@assign": [
          "ec2:instance",
          "rds:db",
          "s3:bucket",
          "lambda:function"
        ]
      }
    },
    "Owner": {
      "tag_key": {"@@assign": "Owner"},
      "enforced_for": {
        "@@assign": ["ec2:instance"]
      }
    }
  }
}
EOF

TAG_POLICY_ID=$(aws organizations create-policy \
  --content file:///tmp/tag-policy.json \
  --name "RequiredResourceTags" \
  --type TAG_POLICY \
  --description "Enforce Environment and Owner tags" \
  --query 'Policy.PolicySummary.Id' --output text)

aws organizations attach-policy \
  --policy-id $TAG_POLICY_ID \
  --target-id $ROOT_ID
```

---

## 10. Verify Complete Setup

```bash
echo "=== AWS Organizations Verification ==="

# 1. Organization exists
aws organizations describe-organization \
  --query 'Organization.{Id:Id,FeatureSet:FeatureSet,MasterAccountId:MasterAccountId}'

# 2. OU structure
aws organizations list-children \
  --parent-id $ROOT_ID \
  --child-type ORGANIZATIONAL_UNIT \
  --query 'Children[].{Id:Id}' | \
  xargs -I{} aws organizations describe-organizational-unit --organizational-unit-id {} \
  --query 'OrganizationalUnit.Name' 2>/dev/null

# 3. SCPs attached
aws organizations list-policies --filter SERVICE_CONTROL_POLICY \
  --query 'Policies[].{Name:Name,Id:Id}'

# 4. Accounts in org
aws organizations list-accounts \
  --query 'Accounts[].{Name:Name,Id:Id,Status:Status}'

echo "=== Verification Complete ==="
```

---

## Troubleshooting

**"Organizations already exists":**
```bash
# Your account is already in an org
aws organizations describe-organization
```

**Account creation fails:**
```bash
# Check creation status
aws organizations list-create-account-status \
  --query 'CreateAccountStatuses[0].{State:State,FailureReason:FailureReason}'
# Common: email already used, account limits reached (default 10 accounts)
```

**SCP not blocking expected actions:**
```bash
# Test SCP effect
aws organizations describe-effective-policy \
  --policy-type SERVICE_CONTROL_POLICY \
  --target-id $DEV_ACCOUNT_ID
```

---

## Expected Outcome

- ✅ Organization created with all features enabled
- ✅ OU hierarchy: Security, Infrastructure, Workloads (Dev/Staging/Prod), Sandbox
- ✅ Member accounts created and placed in appropriate OUs
- ✅ Production SCP: deny non-approved regions, protect audit services
- ✅ Sandbox SCP: restrict to t3 instances only
- ✅ Tag policies enforcing Environment and Owner tags
- ✅ Consolidated billing — one bill for all accounts
- ✅ Cross-account admin role for operations

---

## Cleanup

```bash
# Remove SCPs from OUs first
aws organizations detach-policy --policy-id $PROD_SCP --target-id $PROD_OU
aws organizations detach-policy --policy-id $SANDBOX_SCP --target-id $SANDBOX_OU
aws organizations detach-policy --policy-id $TAG_POLICY_ID --target-id $ROOT_ID

# Delete policies
aws organizations delete-policy --policy-id $PROD_SCP
aws organizations delete-policy --policy-id $SANDBOX_SCP
aws organizations delete-policy --policy-id $TAG_POLICY_ID

# Remove member accounts from org (must close or move to root first)
aws organizations remove-account-from-organization \
  --account-id $DEV_ACCOUNT_ID

# Delete OUs (must be empty first)
aws organizations delete-organizational-unit --organizational-unit-id $DEV_OU
aws organizations delete-organizational-unit --organizational-unit-id $STAGING_OU
aws organizations delete-organizational-unit --organizational-unit-id $PROD_OU
aws organizations delete-organizational-unit --organizational-unit-id $WORKLOADS_OU
aws organizations delete-organizational-unit --organizational-unit-id $SECURITY_OU
aws organizations delete-organizational-unit --organizational-unit-id $INFRA_OU
aws organizations delete-organizational-unit --organizational-unit-id $SANDBOX_OU

# Delete organization (all member accounts must be removed first)
aws organizations delete-organization

echo "Organization cleanup complete"
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
