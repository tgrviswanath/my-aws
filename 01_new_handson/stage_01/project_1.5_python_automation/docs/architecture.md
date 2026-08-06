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

## Input / Output

### Input
| Type | Description | Example |
|------|-------------|---------|
| AWS Account | Active subscription | IAM user with required permissions |
| Configuration | Service settings | CIDR blocks, instance types, regions |
| Source Data | Application or data files | Docker images, SQL scripts, CSV files |

### Output
| Type | Description | Access |
|------|-------------|--------|
| AWS Resources | Deployed infrastructure | AWS Console or CLI |
| Service Endpoints | HTTP/HTTPS URLs, connection strings | Resource overview |
| CloudWatch Logs | Execution and audit trail | CloudWatch Log groups |
| Metrics | Performance data | CloudWatch Metrics |

## Key Concepts
| Concept | Explanation |
|---------|-------------|
| IAM Role | AWS identity for services â€” no static credentials |
| Security Group | Virtual firewall for EC2/RDS â€” stateful |
| VPC | Isolated network â€” your private AWS cloud |
| Region | Geographic AWS datacenter location |
| Availability Zone | Isolated datacenters within a region |
| CloudWatch | AWS monitoring and logging service |
| Free Tier | AWS free usage limits per service per month |
