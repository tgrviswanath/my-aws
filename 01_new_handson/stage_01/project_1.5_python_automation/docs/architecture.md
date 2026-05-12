# Architecture — Project 1.5 Python AWS Automation

## Script Overview

```
Your Machine
    │
    │ boto3 (AWS SDK for Python)
    │ Uses: ~/.aws/credentials or IAM role
    ▼
AWS API
    ├── s3_uploader.py   → S3 (upload, sync, list)
    ├── ec2_manager.py   → EC2 (list, start, stop)
    └── backup_manager.py → RDS snapshots + S3 copy
```

## Authentication Flow

```
boto3.client("s3")
    │
    ├── Check: AWS_ACCESS_KEY_ID env var
    ├── Check: ~/.aws/credentials file
    ├── Check: IAM instance profile (if on EC2)
    └── Check: IAM role (if on Lambda/ECS)
```

## Script Patterns

```python
# Always paginate — AWS returns max 1000 items per call
paginator = s3.get_paginator("list_objects_v2")
for page in paginator.paginate(Bucket="my-bucket"):
    for obj in page["Contents"]:
        process(obj)

# Always handle errors
try:
    s3.upload_file(...)
except ClientError as e:
    if e.response["Error"]["Code"] == "AccessDenied":
        print("Permission denied")
    raise
```
