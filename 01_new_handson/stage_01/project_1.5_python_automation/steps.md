# Steps — Project 1.5 Python AWS Automation

## Phase 1 — Setup

```bash
# Install boto3
pip install boto3

# Verify AWS credentials are configured
aws configure list

# Test boto3 connection
python3 -c "import boto3; print(boto3.client('sts').get_caller_identity())"
```

---

## Phase 2 — S3 Uploader

See `scripts/s3_uploader.py`

```bash
# Upload a single file
python scripts/s3_uploader.py upload \
  --bucket your-bucket-name \
  --file ./test.txt \
  --key uploads/test.txt

# Upload a folder
python scripts/s3_uploader.py sync \
  --bucket your-bucket-name \
  --folder ./website/ \
  --prefix website/

# List bucket contents
python scripts/s3_uploader.py list \
  --bucket your-bucket-name
```

---

## Phase 3 — EC2 Manager

See `scripts/ec2_manager.py`

```bash
# List all instances with status
python scripts/ec2_manager.py list

# Stop an instance
python scripts/ec2_manager.py stop --instance-id i-XXXXXXXXXX

# Start an instance
python scripts/ec2_manager.py start --instance-id i-XXXXXXXXXX

# Stop all instances tagged with Environment=learning
python scripts/ec2_manager.py stop-tagged --tag-key Environment --tag-value learning
```

---

## Phase 4 — Backup Manager

See `scripts/backup_manager.py`

```bash
# Create RDS snapshot
python scripts/backup_manager.py rds-snapshot \
  --instance mysql-lab-01

# Backup S3 bucket to another bucket
python scripts/backup_manager.py s3-backup \
  --source my-source-bucket \
  --destination my-backup-bucket

# List recent snapshots
python scripts/backup_manager.py list-snapshots \
  --instance mysql-lab-01
```

---

## Phase 5 — Cost Reporter

See `scripts/cost_reporter.py`

```bash
# Get costs for last 7 days by service
python scripts/cost_reporter.py --days 7

# Get costs for current month
python scripts/cost_reporter.py --month current
```

---

## Screenshots to Take
- [ ] `s3_uploader.py` uploading files with output
- [ ] `ec2_manager.py list` showing instances
- [ ] `backup_manager.py` creating RDS snapshot
- [ ] `cost_reporter.py` showing cost breakdown
