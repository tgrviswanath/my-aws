# Verification & Validation — Project 10.1 Multi-account AWS Organization

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| Organization | AWS Organizations → AWS accounts | Organization created, management account listed |
| OUs | Organizations → AWS accounts → tree view | Security, Infrastructure, Workloads, Sandbox OUs visible |
| Member Accounts | Organizations → AWS accounts | Dev, Staging, Prod accounts listed under Workloads OU |
| SCPs | Organizations → Policies → Service control policies | All SCPs listed |
| SCP Attachments | SCP → Targets tab | SCPs attached to correct OUs |
| CloudTrail (Org) | CloudTrail → Trails | Organization trail enabled |

📸 Screenshot: Organizations account tree showing OU structure  
📸 Screenshot: SCPs list with attachment targets  
📸 Screenshot: org_manager.py list-accounts output

---

## 2. AWS CLI Verification

```bash
# 2.1 Confirm organization exists
aws organizations describe-organization \
  --query "Organization.{Id:Id,MasterAccountId:MasterAccountId,FeatureSet:FeatureSet}"
# Expected: FeatureSet=ALL (full features enabled)

# 2.2 List all accounts
aws organizations list-accounts \
  --query "Accounts[*].{Name:Name,Id:Id,Status:Status,Email:Email}" \
  --output table
# Expected: management + member accounts listed, all Status=ACTIVE

# 2.3 List all OUs
ROOT_ID=$(aws organizations list-roots --query "Roots[0].Id" --output text)
aws organizations list-organizational-units-for-parent \
  --parent-id $ROOT_ID \
  --query "OrganizationalUnits[*].{Name:Name,Id:Id}"
# Expected: Security, Infrastructure, Workloads, Sandbox OUs listed

# 2.4 List all SCPs
aws organizations list-policies \
  --filter SERVICE_CONTROL_POLICY \
  --query "Policies[*].{Name:Name,Id:Id,Description:Description}"
# Expected: DenyRootUsage, DenyRegionOutsideApproved, RequireEncryption, etc.

# 2.5 Verify SCP attached to correct OU
WORKLOADS_OU=$(aws organizations list-organizational-units-for-parent \
  --parent-id $ROOT_ID \
  --query "OrganizationalUnits[?Name=='Workloads'].Id" --output text)
aws organizations list-policies-for-target \
  --target-id $WORKLOADS_OU \
  --filter SERVICE_CONTROL_POLICY \
  --query "Policies[*].{Name:Name,Id:Id}"
# Expected: DenyRegionOutsideApproved and RequireEncryption listed

# 2.6 Test SCP enforcement — try to create resource in blocked region
# (This should FAIL if DenyRegionOutsideApproved SCP is active on your account)
aws ec2 describe-instances --region ap-southeast-1 2>&1 | head -3
# Expected: AccessDenied error (if SCP blocks this region)

# 2.7 Run org manager
python code/org_manager.py list-accounts
python code/org_manager.py list-scps
python code/org_manager.py check-compliance
# Expected: accounts, SCPs, and compliance status printed
```

---

## 3. Terraform State Verification

```bash
cd terraform

terraform state list
# Expected:
# aws_organizations_organization.main
# aws_organizations_organizational_unit.security
# aws_organizations_organizational_unit.infrastructure
# aws_organizations_organizational_unit.workloads
# aws_organizations_organizational_unit.sandbox
# aws_organizations_policy.deny_root
# aws_organizations_policy.deny_regions
# aws_organizations_policy.require_encryption
# aws_organizations_policy_attachment.deny_root_root
# aws_organizations_policy_attachment.deny_regions_workloads

terraform state show aws_organizations_organization.main
# Shows: feature_set=ALL, master_account_id

terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

---

## 4. Health Check — SCP Enforcement Test

```bash
# Verify DenyRootUsage SCP is attached to root
ROOT_ID=$(aws organizations list-roots --query "Roots[0].Id" --output text)
aws organizations list-policies-for-target \
  --target-id $ROOT_ID \
  --filter SERVICE_CONTROL_POLICY \
  --query "Policies[*].Name"
# Expected: DenyRootUsage listed

# Verify account count matches expected
ACCOUNT_COUNT=$(aws organizations list-accounts --query "length(Accounts)")
echo "Total accounts: $ACCOUNT_COUNT"
# Expected: >= 2 (management + at least 1 member)

# Check compliance across accounts
python code/org_manager.py check-compliance
# Expected: compliance report showing required tags and Config status per account
```

---

## 5. Expected Successful Outputs

**CLI — list-accounts:**
```
| Name        | Id           | Status | Email                    |
|-------------|--------------|--------|--------------------------|
| Management  | 123456789012 | ACTIVE | management@example.com   |
| Dev         | 234567890123 | ACTIVE | dev@example.com          |
| Staging     | 345678901234 | ACTIVE | staging@example.com      |
| Prod        | 456789012345 | ACTIVE | prod@example.com         |
```

**org_manager.py list-scps:**
```
SCPs in Organization:
  DenyRootUsage          → Attached to: Root
  DenyRegionOutsideApproved → Attached to: Workloads OU
  RequireEncryption      → Attached to: Workloads OU
  LimitEC2InstanceTypes  → Attached to: Dev OU
```

---

## 6. Verification Checklist

- [ ] Organization exists with FeatureSet = ALL
- [ ] Management account listed as master
- [ ] OUs created: Security, Infrastructure, Workloads, Sandbox
- [ ] Member accounts in correct OUs (Dev/Staging/Prod under Workloads)
- [ ] All SCPs created and listed
- [ ] `DenyRootUsage` SCP attached to Root
- [ ] `DenyRegionOutsideApproved` SCP attached to Workloads OU
- [ ] SCP enforcement verified (blocked region returns AccessDenied)
- [ ] `org_manager.py list-accounts` prints all accounts
- [ ] `org_manager.py list-scps` prints SCP attachments
- [ ] `terraform plan` shows no changes
