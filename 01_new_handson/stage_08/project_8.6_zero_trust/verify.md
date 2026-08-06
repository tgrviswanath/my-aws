# Verification & Validation — Project 8.6 Zero Trust Security Lab

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| IAM Identity Center | IAM Identity Center → Dashboard | Status = **Enabled** |
| MFA on root | IAM → Dashboard → Security recommendations | Root MFA = **Enabled** |
| IAM users MFA | IAM → Users | All users have MFA device assigned |
| S3 Block Public Access | S3 → Block Public Access (account settings) | All 4 settings = **On** |
| Security Groups | EC2 → Security Groups | No SG with `0.0.0.0/0` on port 22 or 3389 |
| IAM Password Policy | IAM → Account settings | Password policy enforced |
| VPC Flow Logs | VPC → Your VPCs → Flow logs tab | Flow logs enabled |

📸 Screenshot: IAM Identity Center enabled  
📸 Screenshot: S3 Block Public Access all ON at account level  
📸 Screenshot: zero_trust_checker.py output with score

---

## 2. AWS CLI Verification

```bash
# 2.1 Check root MFA status
aws iam get-account-summary \
  --query "SummaryMap.{AccountMFAEnabled:AccountMFAEnabled,UsersWithMFA:AccountAccessKeysPresent}"
# Expected: AccountMFAEnabled=1

# 2.2 Check IAM users without MFA
aws iam generate-credential-report
sleep 5
aws iam get-credential-report --query "Content" --output text | base64 -d | \
  python3 -c "
import sys, csv
reader = csv.DictReader(sys.stdin)
no_mfa = [r['user'] for r in reader if r.get('mfa_active') == 'false' and r['user'] != '<root_account>']
print('Users without MFA:', no_mfa if no_mfa else 'None ✅')
"
# Expected: empty list (all users have MFA)

# 2.3 Check S3 account-level block public access
aws s3control get-public-access-block \
  --account-id $(aws sts get-caller-identity --query Account --output text) \
  --query "PublicAccessBlockConfiguration"
# Expected: all 4 settings = true

# 2.4 Check for security groups with open SSH
aws ec2 describe-security-groups \
  --filters "Name=ip-permission.from-port,Values=22" \
             "Name=ip-permission.cidr,Values=0.0.0.0/0" \
  --query "SecurityGroups[*].{ID:GroupId,Name:GroupName,VPC:VpcId}"
# Expected: empty list (no open SSH)

# 2.5 Check for security groups with open RDP
aws ec2 describe-security-groups \
  --filters "Name=ip-permission.from-port,Values=3389" \
             "Name=ip-permission.cidr,Values=0.0.0.0/0" \
  --query "SecurityGroups[*].{ID:GroupId,Name:GroupName}"
# Expected: empty list (no open RDP)

# 2.6 Check IAM password policy
aws iam get-account-password-policy \
  --query "PasswordPolicy.{MinLength:MinimumPasswordLength,RequireSymbols:RequireSymbols,RequireNumbers:RequireNumbers,MaxAge:MaxPasswordAge}"
# Expected: MinLength>=12, RequireSymbols=true, RequireNumbers=true

# 2.7 Check for IAM users with wildcard policies
aws iam list-users --query "Users[*].UserName" --output text | \
  tr '\t' '\n' | while read user; do
    POLICIES=$(aws iam list-user-policies --user-name $user --query "PolicyNames" --output text)
    [ -n "$POLICIES" ] && echo "User $user has inline policies: $POLICIES"
  done
# Expected: no output (no inline wildcard policies)

# 2.8 Run zero trust checker
python code/zero_trust_checker.py
# Expected: score printed with findings and remediation steps
```

---

## 3. Terraform State Verification

```bash
cd terraform

# 3.1 List all resources
terraform state list
# Expected:
# aws_iam_account_password_policy.main
# aws_s3_account_public_access_block.main
# aws_vpc_flow_log.main (if VPC flow logs configured)
# aws_iam_role.flow_logs
# aws_cloudwatch_log_group.flow_logs

# 3.2 Inspect password policy
terraform state show aws_iam_account_password_policy.main
# Shows: minimum_password_length>=12, require_symbols=true, require_numbers=true

# 3.3 Inspect S3 block public access
terraform state show aws_s3_account_public_access_block.main
# Shows: all 4 block settings = true

# 3.4 No drift
terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

---

## 4. Health Check — Zero Trust Score

```bash
# Run full zero trust audit
python code/zero_trust_checker.py

# Expected output structure:
# Zero Trust Score: XX/100
# ✅ Root MFA enabled
# ✅ No IAM users without MFA
# ✅ S3 Block Public Access enabled (account level)
# ✅ No security groups with open SSH (0.0.0.0/0:22)
# ✅ No security groups with open RDP (0.0.0.0/0:3389)
# ⚠️  Finding: [any issues found]
```

---

## 5. Expected Successful Outputs

**CLI — get-public-access-block:**
```json
{
  "BlockPublicAcls": true,
  "IgnorePublicAcls": true,
  "BlockPublicPolicy": true,
  "RestrictPublicBuckets": true
}
```

**CLI — open SSH check:**
```json
[]
```

**zero_trust_checker.py output:**
```
=== Zero Trust Security Audit ===
✅ Root MFA:          ENABLED
✅ User MFA:          All 3 users have MFA
✅ Public S3:         No public buckets (account block enabled)
✅ Open SSH/RDP:      No security groups with 0.0.0.0/0 on 22/3389
✅ Wildcard policies: No users with * action policies

Zero Trust Score: 95/100
Findings: 1 low-severity finding
  - 2 IAM access keys older than 90 days (rotate recommended)
```

---

## 6. Verification Checklist

- [ ] Root account MFA = enabled
- [ ] All IAM users have MFA devices assigned
- [ ] S3 Block Public Access = all 4 settings ON at account level
- [ ] No security groups with `0.0.0.0/0` on port 22 (SSH)
- [ ] No security groups with `0.0.0.0/0` on port 3389 (RDP)
- [ ] IAM password policy: min length ≥ 12, symbols required, numbers required
- [ ] No IAM users with inline wildcard (`*`) action policies
- [ ] VPC Flow Logs enabled
- [ ] `zero_trust_checker.py` runs and prints score ≥ 80/100
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
