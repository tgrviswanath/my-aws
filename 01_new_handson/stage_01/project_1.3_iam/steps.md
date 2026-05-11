# Steps — Project 1.3 IAM Security Foundations

## Phase 1 — Console

### 1.1 Create Admin IAM User (stop using root)
1. Go to **IAM** → **Users** → **Create user**
2. Username: `admin-yourname`
3. Enable **AWS Management Console access**
4. Set a strong password
5. Attach policy: `AdministratorAccess`
6. Log out of root, log in as this user from now on

### 1.2 Enable MFA on Admin User
1. Go to **IAM** → **Users** → select your admin user
2. **Security credentials** tab → **Assign MFA device**
3. Choose **Authenticator app**
4. Scan QR code with Google Authenticator or Authy
5. Enter two consecutive codes to verify

### 1.3 Create Groups and Users
1. Create groups:
   - `developers` — attach `AmazonEC2ReadOnlyAccess` + `AmazonS3ReadOnlyAccess`
   - `data-engineers` — attach `AmazonS3FullAccess` + `AWSGlueConsoleFullAccess`
   - `ops` — attach `AmazonEC2FullAccess` + `CloudWatchFullAccess`

2. Create users:
   - `dev-user-01` → add to `developers` group
   - `de-user-01` → add to `data-engineers` group

---

## Phase 2 — AWS CLI

```bash
# Create a group
aws iam create-group --group-name developers

# Attach policy to group
aws iam attach-group-policy \
  --group-name developers \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ReadOnlyAccess

# Create a user
aws iam create-user --user-name dev-user-01

# Add user to group
aws iam add-user-to-group \
  --user-name dev-user-01 \
  --group-name developers

# Create access keys for programmatic access
aws iam create-access-key --user-name dev-user-01

# List users
aws iam list-users

# List groups for a user
aws iam list-groups-for-user --user-name dev-user-01
```

---

## Phase 3 — Create EC2 Role with S3 Read Access

```bash
# Create trust policy (allows EC2 to assume this role)
cat > ec2-trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "ec2.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
EOF

# Create the role
aws iam create-role \
  --role-name ec2-s3-read-role \
  --assume-role-policy-document file://ec2-trust-policy.json

# Create a custom policy — restrict to specific bucket
cat > s3-read-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["s3:GetObject", "s3:ListBucket"],
    "Resource": [
      "arn:aws:s3:::your-specific-bucket",
      "arn:aws:s3:::your-specific-bucket/*"
    ]
  }]
}
EOF

aws iam create-policy \
  --policy-name S3ReadSpecificBucket \
  --policy-document file://s3-read-policy.json

# Attach policy to role
aws iam attach-role-policy \
  --role-name ec2-s3-read-role \
  --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/S3ReadSpecificBucket

# Create instance profile (needed to attach role to EC2)
aws iam create-instance-profile \
  --instance-profile-name ec2-s3-read-profile

aws iam add-role-to-instance-profile \
  --instance-profile-name ec2-s3-read-profile \
  --role-name ec2-s3-read-role
```

---

## Phase 4 — Test Permissions

```bash
# Switch to dev-user-01 profile
aws configure --profile dev-user

# Test: can read EC2 (should work)
aws ec2 describe-instances --profile dev-user

# Test: can create EC2 (should FAIL — read only)
aws ec2 run-instances \
  --image-id ami-0c02fb55956c7d316 \
  --instance-type t3.micro \
  --profile dev-user
# Expected: AccessDenied error

# Test: can read S3 (should work)
aws s3 ls --profile dev-user

# Test: can delete S3 bucket (should FAIL)
aws s3 rb s3://some-bucket --profile dev-user
# Expected: AccessDenied error
```

---

## Phase 5 — Terraform

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

---

## Screenshots to Take
- [ ] IAM users list showing created users
- [ ] Groups with policies attached
- [ ] MFA device assigned to admin user
- [ ] EC2 role with trust policy visible
- [ ] Custom S3 policy JSON
- [ ] Permission denied error when testing restricted action
- [ ] `terraform apply` success output
