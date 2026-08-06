# Project 1.5 — Python Automation with boto3

**Stage:** 01 | **Level:** Beginner | **Est. Time:** 2–3 hours | **Cost:** varies by resources created

Automate AWS resource management with Python boto3. Three scripts cover the most common automation tasks: EC2 start/stop/describe, S3 upload/download/list, and RDS describe/snapshot. Runs locally using `~/.aws/credentials` or from EC2 using an instance metadata role — no hard-coded keys.

---

## Services Used

| Tool | Purpose | Cost |
|------|---------|------|
| boto3 | Python AWS SDK — wraps all AWS service APIs | Free |
| EC2 | Target resource: start, stop, describe instances | See project 1.2 |
| S3 | Target resource: upload, download, list objects | $0.023/GB/month |
| RDS | Target resource: describe instances, create snapshot | See project 1.4 |
| IAM | Role or user credentials used by boto3 | Free |

---

## Input / Output

### Input
| Type | Description |
|------|-------------|
| Python 3.x | `python --version` 3.8 or later |
| `boto3` installed | `pip install boto3` |
| AWS credentials | `~/.aws/credentials` (local) or IAM role (on EC2/Lambda) |
| Instance ID | e.g. `i-0abc123...` for EC2 scripts |
| Bucket name | e.g. `my-lab-bucket-abc123` for S3 scripts |
| DB instance ID | e.g. `mydb` for RDS scripts |

### Output
| Type | Description |
|------|-------------|
| EC2 script output | Instance state transitions: `running` → `stopped` → `running`; describe prints InstanceId, State, Type, PublicIp |
| S3 script output | Upload confirms `ETag`; list shows key + size + LastModified; download saves file locally |
| RDS script output | Describe prints endpoint, status, engine version; snapshot ID returned and status tracked |
| boto3 error output | `botocore.exceptions.ClientError` with `Code` and `Message` on API failures |

---

## Architecture

```
Python script (local or on EC2)
  │
  ├── boto3.client('ec2') / boto3.resource('ec2')
  │     └── HTTPS (SigV4) → ec2.us-east-1.amazonaws.com
  │           └── start/stop/describe instances
  │
  ├── boto3.client('s3') / boto3.resource('s3')
  │     └── HTTPS (SigV4) → s3.amazonaws.com
  │           └── put_object / get_object / list_objects_v2 (paginated)
  │
  └── boto3.client('rds')
        └── HTTPS (SigV4) → rds.us-east-1.amazonaws.com
              └── describe_db_instances / create_db_snapshot

Credential chain (boto3 checks in order):
  1. Environment vars (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
  2. ~/.aws/credentials (named profile or [default])
  3. EC2 instance metadata service (IMDSv2 at 169.254.169.254)
  4. IAM role attached to EC2/Lambda
```

---

## Quick Start

```cmd
REM 1. Install boto3
pip install boto3

REM 2. Verify credentials (same chain as AWS CLI)
python -c "import boto3; print(boto3.client('sts').get_caller_identity())"

REM 3. Run EC2 automation script
python scripts\ec2_manager.py --action describe --region us-east-1

REM 4. Stop a specific instance
python scripts\ec2_manager.py --action stop --instance-id i-0abc123

REM 5. Start it again
python scripts\ec2_manager.py --action start --instance-id i-0abc123

REM 6. Run S3 script — upload a file
python scripts\s3_manager.py --action upload --bucket my-lab-bucket ^
    --file data\sample.txt --key uploads/sample.txt

REM 7. List all objects in bucket (handles pagination automatically)
python scripts\s3_manager.py --action list --bucket my-lab-bucket

REM 8. RDS snapshot
python scripts\rds_manager.py --action snapshot --db-id mydb ^
    --snapshot-id mydb-manual-snap-001
```

---

## Data Flow

```
1. boto3.client() reads credentials using the credential chain — env vars first, then ~/.aws, then IMDS
2. Each API call is signed with SigV4 (HMAC-SHA256 of headers + payload) — boto3 handles signing automatically
3. ec2_manager.py calls ec2.stop_instances([instance_id]) — EC2 transitions state: running → stopping → stopped
4. ec2_manager.py uses waiters: ec2.get_waiter('instance_stopped').wait() — polls DescribeInstances every 15s
5. s3_manager.py calls s3.upload_file() which multipart-uploads files > 8 MB automatically
6. s3_manager.py uses a paginator for list: s3.get_paginator('list_objects_v2') — iterates pages of max 1000 keys
7. rds_manager.py calls rds.create_db_snapshot() — snapshot status: creating → available (5-20 min)
8. Error handling wraps all calls: botocore.exceptions.ClientError exposes error['Code'] (e.g. InvalidInstanceID.NotFound)
9. All API responses are Python dicts — scripts extract only needed fields (InstanceId, State, Endpoint, etc.)
```

---

## Project Files

| File | Purpose |
|------|---------|
| `README.md` | This file — automation overview |
| `GUIDE.md` | Full walkthrough: boto3 setup, client vs resource, pagination, waiters |
| `steps.md` | Windows CMD quick-reference to run each script |
| `steps_awsconsoleui.md` | Verify results in console after running scripts |
| `verify.md` | Checklist: each script produces expected output, errors handled |
| `cost_estimate.md` | Cost of resources created by scripts |
| `scripts/ec2_manager.py` | Start, stop, describe EC2 instances; uses waiters |
| `scripts/s3_manager.py` | Upload, download, list S3 objects; paginator for large buckets |
| `scripts/rds_manager.py` | Describe RDS instances, create and monitor snapshots |
| `docs/` | boto3 credential chain diagram, client vs resource comparison table |

---

## Lessons Learned

- boto3 uses the **same credential chain as the AWS CLI** — if `aws sts get-caller-identity` works in CMD, boto3 scripts work with no extra configuration; the chain checks env vars first, then `~/.aws/credentials`, then instance metadata
- `boto3.resource('s3')` provides a high-level OO interface (Bucket, Object classes); `boto3.client('s3')` exposes the raw API methods — use `client` when you need full control over request parameters, `resource` for simple day-to-day tasks
- `list_objects_v2` returns at most **1,000 keys per response** — buckets with more objects require pagination; always use `get_paginator('list_objects_v2')` to avoid silently truncated results
- The **waiter pattern** (`ec2.get_waiter('instance_running').wait(InstanceIds=[id])`) polls the API on a configurable interval until the desired state is reached — it prevents races where a script continues before the resource is ready
- `botocore.exceptions.ClientError` wraps all AWS API error responses — the error code is at `e.response['Error']['Code']` and the message at `e.response['Error']['Message']`; always catch this instead of bare `Exception`
- boto3 sessions (`boto3.Session(profile_name='myaws')`) let scripts switch between named profiles programmatically — useful for scripts that must operate across multiple accounts
- EC2 `stop_instances` is non-blocking — the API returns immediately with state `stopping`; the instance takes 20–60 seconds to reach `stopped`; skipping the waiter causes downstream scripts to fail on "instance not stopped" errors
