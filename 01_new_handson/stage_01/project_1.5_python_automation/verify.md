# Verification & Validation — Project 1.5 Python AWS Automation

---

## 1. Environment Verification

```bash
# Python and boto3 installed
python3 --version
# Expected: Python 3.8+

pip show boto3 | grep Version
# Expected: Version: 1.x.x

# AWS credentials configured
aws configure list
# Expected: access_key, secret_key, region all set

# boto3 can connect
python3 -c "import boto3; print(boto3.client('sts').get_caller_identity()['Account'])"
# Expected: your AWS account ID (no error)
```

📸 Screenshot: boto3 identity check returning account ID

---

## 2. s3_uploader.py Verification

```bash
# Create a test file
echo "boto3 upload test" > /tmp/test_upload.txt

# Upload single file
python scripts/s3_uploader.py upload \
  --bucket your-bucket-name \
  --file /tmp/test_upload.txt \
  --key uploads/test_upload.txt
# Expected: ✅ Uploaded: uploads/test_upload.txt

# Verify file exists in S3
aws s3 ls s3://your-bucket-name/uploads/
# Expected: test_upload.txt listed

# List bucket contents via script
python scripts/s3_uploader.py list --bucket your-bucket-name
# Expected: formatted list of objects with sizes

# Sync a folder
mkdir -p /tmp/test_folder && echo "file1" > /tmp/test_folder/a.txt && echo "file2" > /tmp/test_folder/b.txt
python scripts/s3_uploader.py sync \
  --bucket your-bucket-name \
  --folder /tmp/test_folder \
  --prefix test-sync/
# Expected: ✅ Synced 2 files
```

📸 Screenshot: s3_uploader.py output showing uploaded files

---

## 3. ec2_manager.py Verification

```bash
# List all instances
python scripts/ec2_manager.py list
# Expected: table showing instance IDs, names, states, types, IPs

# Stop an instance
python scripts/ec2_manager.py stop --instance-id i-XXXXXXXXXX
# Expected: ✅ Stopping i-XXXXXXXXXX

# Verify stopped
aws ec2 describe-instances --instance-ids i-XXXXXXXXXX \
  --query "Reservations[0].Instances[0].State.Name"
# Expected: stopping or stopped

# Start it back
python scripts/ec2_manager.py start --instance-id i-XXXXXXXXXX
# Expected: ✅ Starting i-XXXXXXXXXX

# Stop by tag
python scripts/ec2_manager.py stop-tagged \
  --tag-key Environment --tag-value learning
# Expected: lists and stops all matching instances
```

📸 Screenshot: ec2_manager.py list output showing instances

---

## 4. backup_manager.py Verification

```bash
# Create RDS snapshot
python scripts/backup_manager.py rds-snapshot --instance mysql-lab-01
# Expected: ✅ Snapshot created: mysql-lab-01-backup-YYYYMMDD-HHMMSS

# Verify snapshot exists
aws rds describe-db-snapshots \
  --db-instance-identifier mysql-lab-01 \
  --query "DBSnapshots[?SnapshotType=='manual'].{ID:DBSnapshotIdentifier,Status:Status}"
# Expected: snapshot with Status=available or creating

# List snapshots via script
python scripts/backup_manager.py list-snapshots --instance mysql-lab-01
# Expected: formatted list of snapshots with dates and status

# S3 backup
python scripts/backup_manager.py s3-backup \
  --source my-source-bucket \
  --destination my-backup-bucket
# Expected: ✅ Backed up X objects
```

📸 Screenshot: backup_manager.py creating RDS snapshot with output

---

## 5. Terraform State Verification

```bash
cd terraform

terraform state list
# Expected:
# aws_s3_bucket.automation_bucket
# aws_iam_role.automation_role
# aws_iam_instance_profile.automation

terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

---

## 6. Expected Successful Outputs

**s3_uploader.py upload:**
```
✅ Uploaded: uploads/test_upload.txt (18 bytes)
```

**ec2_manager.py list:**
```
Instance ID          Name           State    Type      Public IP
i-0abc123456789      web-server-01  running  t3.micro  54.x.x.x
i-0def987654321      db-bastion     stopped  t3.micro  -
```

**backup_manager.py rds-snapshot:**
```
✅ Snapshot created: mysql-lab-01-backup-20240101-120000
   Status: creating → available (wait ~5 min)
```

---

## 7. Verification Checklist

- [ ] Python 3.8+ installed
- [ ] boto3 installed
- [ ] AWS credentials configured and working
- [ ] `boto3.client('sts').get_caller_identity()` returns account ID
- [ ] `s3_uploader.py upload` uploads file successfully
- [ ] Uploaded file visible in S3 via `aws s3 ls`
- [ ] `s3_uploader.py sync` syncs folder successfully
- [ ] `ec2_manager.py list` shows instances
- [ ] `ec2_manager.py stop` stops instance (state = stopped)
- [ ] `ec2_manager.py start` starts instance (state = running)
- [ ] `backup_manager.py rds-snapshot` creates snapshot
- [ ] Snapshot visible in RDS console
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
