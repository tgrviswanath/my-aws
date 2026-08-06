# Verification & Validation — Project 1.3 IAM Security Foundations

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| Admin IAM User | IAM → Users | `admin-yourname` exists, Console access enabled |
| MFA Device | IAM → Users → Security credentials | MFA device = **Assigned** |
| Groups | IAM → User groups | `developers`, `data-engineers`, `ops` exist |
| Group Policies | IAM → Groups → Permissions | Correct managed policies attached per group |
| Dev User | IAM → Users | `dev-user-01` in `developers` group |
| EC2 Role | IAM → Roles | `ec2-s3-read-role` with EC2 trust policy |
| Custom Policy | IAM → Policies | `S3ReadSpecificBucket` policy exists |
| Instance Profile | IAM → Roles → `ec2-s3-read-role` | Instance profile attached |

📸 Screenshot: IAM users list showing created users  
📸 Screenshot: `developers` group with policies attached  
📸 Screenshot: MFA device assigned to admin user  
📸 Screenshot: Permission denied error when dev-user tries a restricted action

---

## 2. AWS CLI Verification

```bash
# 2.1 Users exist
aws iam list-users \
  --query "Users[?contains(UserName,'dev-user') || contains(UserName,'admin')].UserName"
# Expected: admin-yourname, dev-user-01, de-user-01

# 2.2 Groups exist with correct policies
aws iam list-attached-group-policies --group-name developers \
  --query "AttachedPolicies[*].PolicyName"
# Expected: AmazonEC2ReadOnlyAccess, AmazonS3ReadOnlyAccess

# 2.3 dev-user-01 is in developers group
aws iam list-groups-for-user --user-name dev-user-01 \
  --query "Groups[*].GroupName"
# Expected: ["developers"]

# 2.4 EC2 role exists with correct trust policy
aws iam get-role --role-name ec2-s3-read-role \
  --query "Role.{Name:RoleName,Principal:AssumeRolePolicyDocument.Statement[0].Principal.Service}"
# Expected: Principal=ec2.amazonaws.com

# 2.5 Custom policy attached to role
aws iam list-attached-role-policies --role-name ec2-s3-read-role \
  --query "AttachedPolicies[*].PolicyName"
# Expected: S3ReadSpecificBucket

# 2.6 Permission boundary test — dev-user cannot create EC2
aws ec2 run-instances \
  --image-id ami-0c02fb55956c7d316 \
  --instance-type t3.micro \
  --profile dev-user 2>&1 | grep -i "AccessDenied\|not authorized"
# Expected: AccessDenied error

# 2.7 dev-user CAN read EC2
aws ec2 describe-instances --profile dev-user
# Expected: returns instance list (no error)
```

---

## 3. Terraform State Verification

```bash
cd terraform

terraform state list
# Expected:
# aws_iam_user.admin
# aws_iam_user.dev_user_01
# aws_iam_group.developers
# aws_iam_group.data_engineers
# aws_iam_group.ops
# aws_iam_group_membership.developers
# aws_iam_role.ec2_s3_read
# aws_iam_policy.s3_read_specific
# aws_iam_role_policy_attachment.ec2_s3_read
# aws_iam_instance_profile.ec2_s3_read

terraform state show aws_iam_role.ec2_s3_read
# Shows: assume_role_policy with ec2.amazonaws.com principal

terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

---

## 4. Health Check — Permission Boundary Tests

```bash
# Configure dev-user profile first
aws configure --profile dev-user
# Use dev-user-01 access keys

# ALLOWED actions (should succeed):
aws ec2 describe-instances --profile dev-user        # ✅ EC2 read
aws s3 ls --profile dev-user                         # ✅ S3 read

# DENIED actions (should fail with AccessDenied):
aws ec2 run-instances \
  --image-id ami-0c02fb55956c7d316 \
  --instance-type t3.micro \
  --profile dev-user 2>&1                            # ❌ EC2 write
aws s3 rb s3://some-bucket --profile dev-user 2>&1   # ❌ S3 delete
aws iam create-user --user-name test --profile dev-user 2>&1  # ❌ IAM write
```

---

## 5. Expected Successful Outputs

**Group policies:**
```json
["AmazonEC2ReadOnlyAccess", "AmazonS3ReadOnlyAccess"]
```

**EC2 role trust policy:**
```json
{ "Name": "ec2-s3-read-role", "Principal": "ec2.amazonaws.com" }
```

**Permission denied (expected):**
```
An error occurred (UnauthorizedOperation) when calling the RunInstances operation:
You are not authorized to perform this operation.
```

---

## 6. Verification Checklist

- [ ] Admin IAM user created, console access enabled
- [ ] MFA device assigned to admin user
- [ ] Root account not used for daily work
- [ ] Groups created: `developers`, `data-engineers`, `ops`
- [ ] Correct policies attached to each group
- [ ] `dev-user-01` in `developers` group
- [ ] EC2 role `ec2-s3-read-role` with EC2 trust policy
- [ ] Custom policy `S3ReadSpecificBucket` restricts to specific bucket
- [ ] Instance profile created and role attached
- [ ] dev-user CAN read EC2 and S3
- [ ] dev-user CANNOT create EC2 (AccessDenied confirmed)
- [ ] dev-user CANNOT delete S3 (AccessDenied confirmed)
- [ ] `terraform plan` shows no changes
- [ ] `iam_setup.py --dry-run` runs without errors

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
