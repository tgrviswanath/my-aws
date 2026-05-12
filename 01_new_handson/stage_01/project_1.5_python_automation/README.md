# Project 1.5 — Python AWS Automation

## What This Does
Uses Python + boto3 to automate common AWS tasks: S3 file management, EC2 status checking, and automated backups.

## Skills Used
- Python 3
- boto3 (AWS SDK for Python)
- AWS CLI profiles

## Scripts Built
| Script | Purpose |
|--------|---------|
| `s3_uploader.py` | Upload files/folders to S3 with progress |
| `ec2_manager.py` | List, start, stop EC2 instances |
| `backup_manager.py` | Create RDS snapshots and S3 backups on schedule |
| `cost_reporter.py` | Pull daily cost data from Cost Explorer |

## How to Run
```bash
pip install boto3
python s3_uploader.py --bucket my-bucket --path ./files/
python ec2_manager.py --action list
python backup_manager.py --instance mysql-lab-01
```

## Lessons Learned
- Always use IAM roles (not access keys) when running on EC2
- Use `boto3.Session(profile_name='...')` to switch between AWS profiles
- Paginate API calls — AWS returns max 1000 items per call
- Handle `ClientError` exceptions for proper error handling
- Use `--dry-run` flag on EC2 operations to test permissions without executing

## Code

### `scripts/s3_uploader.py` — Upload files to S3

```bash
pip install boto3

# Upload a single file
python scripts/s3_uploader.py upload --bucket my-bucket --file ./data.csv --key uploads/data.csv

# Sync an entire folder
python scripts/s3_uploader.py sync --bucket my-bucket --folder ./data --prefix backups/

# List bucket contents
python scripts/s3_uploader.py list --bucket my-bucket
```
