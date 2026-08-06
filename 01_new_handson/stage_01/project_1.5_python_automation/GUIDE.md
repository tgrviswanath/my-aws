# Project 1.5 — Python Automation with boto3

## 1. Overview

**Problem:** Clicking through the AWS Console to start/stop EC2 instances, upload files to S3, or trigger RDS snapshots is repetitive and error-prone. Manual processes don't scale and can't be scheduled or version-controlled.

**Solution:** boto3 is the official AWS SDK for Python. It exposes the same AWS APIs that the Console and CLI use, allowing you to write scripts that automate any AWS operation: provisioning, monitoring, backups, cost reports, and more.

**Objectives:**
- Set up boto3 with IAM role authentication (for EC2) or `aws configure` (for local scripts)
- Automate EC2 operations: list instances, start/stop by tag, check status
- Automate S3 operations: create bucket, upload/download files, list objects, delete
- Automate RDS operations: list instances, create snapshots, describe status
- Build a simple resource inventory report script

**Expected Result:** Python scripts that automate common AWS tasks, runnable locally or from an EC2 instance, authenticated securely via IAM role or configured profile.

---

## 2. Architecture

```
Python Script (local or on EC2)
         │
         ▼ boto3 SDK calls
┌────────────────────────────┐
│  boto3 Client / Resource   │  ← Python objects wrapping AWS API calls
│  boto3.client('ec2')       │
│  boto3.client('s3')        │
│  boto3.client('rds')       │
└──────────┬─────────────────┘
           │ HTTPS requests (SigV4 signed)
           ▼
┌────────────────────────────┐
│  AWS Credential Chain       │  ← boto3 checks in order:
│  1. Env vars               │    1. AWS_ACCESS_KEY_ID env var
│  2. ~/.aws/credentials     │    2. ~/.aws/credentials file
│  3. EC2 Instance Profile   │    3. EC2 instance metadata (IAM role)
│  4. ECS Task Role          │    4. ECS task role
│  5. AWS SSO                │    5. SSO token
└──────────┬─────────────────┘
           │
           ▼
┌────────────────────────────┐
│  AWS APIs                   │
│  EC2 API → manage instances │
│  S3 API  → manage objects   │
│  RDS API → manage databases │
└────────────────────────────┘
```

**Key Concepts:**
| Term | Description |
|------|-------------|
| `boto3.client()` | Low-level API access, returns raw JSON dicts |
| `boto3.resource()` | Higher-level OO abstraction, returns objects |
| `Session` | Isolated credential/region context |
| `Paginator` | Handles responses with multiple pages automatically |
| `Waiter` | Polls until a resource reaches a desired state |

---

## 3. Prerequisites

### AWS Account & Permissions
- [ ] IAM role (for EC2/Lambda) or IAM user (for local) with policies:
  - `AmazonEC2ReadOnlyAccess` (or EC2 full access for start/stop)
  - `AmazonS3FullAccess`
  - `AmazonRDSReadOnlyAccess` (or RDS full for snapshots)
- [ ] AWS CLI configured: `aws configure` (sets `~/.aws/credentials`)

### Local Tools
- [ ] Python 3.8+: `python3 --version`
- [ ] pip: `pip --version`
- [ ] boto3: `pip install boto3`
- [ ] AWS CLI v2: for `aws configure`

### Verify Setup
```bash
# Confirm Python and boto3
python3 -c "import boto3; print('boto3 version:', boto3.__version__)"

# Confirm AWS credentials work
python3 -c "
import boto3
sts = boto3.client('sts')
identity = sts.get_caller_identity()
print('Account:', identity['Account'])
print('User/Role:', identity['Arn'])
"
```

---

## 4. Folder Structure

```
project_1.5_python_automation/
├── GUIDE.md                      ← This file
├── steps_awsconsoleui.md         ← Console setup walkthrough
├── cost_estimate.md              ← Cost breakdown
├── requirements.txt              ← Python dependencies
├── ec2/
│   ├── list_instances.py         ← List all EC2 instances
│   ├── start_stop.py             ← Start/stop by tag
│   └── instance_report.py       ← Generate status report
├── s3/
│   ├── bucket_ops.py             ← Create/delete buckets
│   ├── file_ops.py               ← Upload/download/list
│   └── sync_folder.py            ← Sync local folder to S3
├── rds/
│   ├── list_instances.py         ← List RDS instances
│   └── create_snapshot.py        ← Automated snapshot
└── utils/
    ├── aws_session.py            ← Reusable session/client helper
    └── inventory_report.py       ← Cross-service resource report
```

**`requirements.txt`:**
```
boto3==1.34.0
botocore==1.34.0
```

---

## 5. Implementation

### Decision Point 1: boto3 with Access Keys vs IAM Role

| Method | Best for | Security | Setup |
|--------|---------|---------|-------|
| `aws configure` (access key) | ✅ Local development scripts | Medium (key on disk) | `aws configure` |
| IAM Instance Profile | ✅ Scripts running on EC2 | High (no keys stored) | Attach role to EC2 |
| IAM Task Role | ✅ Scripts in Lambda/ECS | High (no keys stored) | Attach role to function |
| Environment variables | CI/CD pipelines | Medium (ephemeral) | Set `AWS_ACCESS_KEY_ID` |
| AWS SSO / Identity Center | ✅ Teams, orgs | High | `aws sso configure` |

**For local scripts:** Use `aws configure` with an IAM user.
**For EC2/Lambda:** Always use an IAM role (no access keys in code or disk).

---

### Prerequisites Check

```bash
# 1. Verify boto3 installation
pip show boto3

# 2. Test credentials
python3 -c "
import boto3
client = boto3.client('sts', region_name='us-east-1')
print(client.get_caller_identity())
"

# 3. Check Python version
python3 --version  # Need 3.8+

# 4. Check available regions
python3 -c "
import boto3
ec2 = boto3.client('ec2', region_name='us-east-1')
regions = ec2.describe_regions()
print([r['RegionName'] for r in regions['Regions']])
"
```

---

### 5A. Console Implementation (IAM Setup)

See `steps_awsconsoleui.md` for the full Console walkthrough.

**High-level Console steps:**
1. IAM → Create role `boto3-automation-role`
2. Trusted entity: EC2 (if running on EC2) or IAM user (for local scripts)
3. Attach policies: `AmazonEC2ReadOnlyAccess`, `AmazonS3FullAccess`, `AmazonRDSReadOnlyAccess`
4. If for local use: IAM → Users → Create user → attach same policies → create access key
5. Run `aws configure` with the access key
6. Verify: `python3 -c "import boto3; print(boto3.client('sts').get_caller_identity())"`

---

### 5B. CLI / Python Implementation

#### Setup: Install boto3

```bash
# Install in a virtual environment (best practice)
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

pip install boto3
pip freeze > requirements.txt
```

#### Configure AWS Credentials (Local Use)

```bash
aws configure
# AWS Access Key ID [None]: YOUR_ACCESS_KEY_ID
# AWS Secret Access Key [None]: YOUR_SECRET_ACCESS_KEY
# Default region name [None]: us-east-1
# Default output format [None]: json
```

---

#### EC2 Automation

**`ec2/list_instances.py` — List all EC2 instances**

```python
import boto3

def list_ec2_instances(region='us-east-1'):
    """List all EC2 instances with their status, type, and name tag."""
    ec2 = boto3.client('ec2', region_name=region)

    # Use paginator to handle > 100 instances
    paginator = ec2.get_paginator('describe_instances')
    pages = paginator.paginate()

    print(f"{'ID':<20} {'State':<12} {'Type':<14} {'Name':<25} {'Public IP':<15}")
    print("-" * 90)

    for page in pages:
        for reservation in page['Reservations']:
            for instance in reservation['Instances']:
                instance_id = instance['InstanceId']
                state = instance['State']['Name']
                instance_type = instance['InstanceType']
                public_ip = instance.get('PublicIpAddress', 'N/A')

                # Get Name tag
                name = 'N/A'
                for tag in instance.get('Tags', []):
                    if tag['Key'] == 'Name':
                        name = tag['Value']
                        break

                print(f"{instance_id:<20} {state:<12} {instance_type:<14} {name:<25} {public_ip:<15}")

if __name__ == '__main__':
    list_ec2_instances()
```

**`ec2/start_stop.py` — Start/Stop instances by tag**

```python
import boto3
import sys

def get_instances_by_tag(ec2_client, tag_key, tag_value):
    """Return list of instance IDs matching a tag."""
    response = ec2_client.describe_instances(
        Filters=[
            {'Name': f'tag:{tag_key}', 'Values': [tag_value]},
            {'Name': 'instance-state-name', 'Values': ['running', 'stopped']}
        ]
    )
    instance_ids = []
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            instance_ids.append(instance['InstanceId'])
    return instance_ids

def start_instances(tag_key='Environment', tag_value='dev', region='us-east-1'):
    ec2 = boto3.client('ec2', region_name=region)
    ids = get_instances_by_tag(ec2, tag_key, tag_value)

    if not ids:
        print(f"No instances found with tag {tag_key}={tag_value}")
        return

    ec2.start_instances(InstanceIds=ids)
    print(f"Started {len(ids)} instance(s): {ids}")

    # Wait until running
    waiter = ec2.get_waiter('instance_running')
    waiter.wait(InstanceIds=ids)
    print("✅ All instances are running")

def stop_instances(tag_key='Environment', tag_value='dev', region='us-east-1'):
    ec2 = boto3.client('ec2', region_name=region)
    ids = get_instances_by_tag(ec2, tag_key, tag_value)

    if not ids:
        print(f"No instances found with tag {tag_key}={tag_value}")
        return

    ec2.stop_instances(InstanceIds=ids)
    print(f"Stopping {len(ids)} instance(s): {ids}")

    waiter = ec2.get_waiter('instance_stopped')
    waiter.wait(InstanceIds=ids)
    print("✅ All instances are stopped")

if __name__ == '__main__':
    action = sys.argv[1] if len(sys.argv) > 1 else 'list'
    if action == 'start':
        start_instances()
    elif action == 'stop':
        stop_instances()
    else:
        print("Usage: python start_stop.py [start|stop]")
```

---

#### S3 Automation

**`s3/file_ops.py` — Upload, download, list S3 objects**

```python
import boto3
import os
from pathlib import Path

def upload_file(local_path: str, bucket: str, s3_key: str = None):
    """Upload a local file to S3."""
    s3 = boto3.client('s3')
    s3_key = s3_key or Path(local_path).name  # Use filename if no key specified

    s3.upload_file(
        Filename=local_path,
        Bucket=bucket,
        Key=s3_key,
        ExtraArgs={'ContentType': 'text/html'} if local_path.endswith('.html') else {}
    )
    print(f"✅ Uploaded '{local_path}' → s3://{bucket}/{s3_key}")

def download_file(bucket: str, s3_key: str, local_path: str):
    """Download a file from S3."""
    s3 = boto3.client('s3')
    s3.download_file(Bucket=bucket, Key=s3_key, Filename=local_path)
    print(f"✅ Downloaded s3://{bucket}/{s3_key} → '{local_path}'")

def list_objects(bucket: str, prefix: str = ''):
    """List all objects in a bucket with optional prefix filter."""
    s3 = boto3.client('s3')
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket, Prefix=prefix)

    total_size = 0
    count = 0
    print(f"\nObjects in s3://{bucket}/{prefix}")
    print(f"{'Key':<50} {'Size':>10} {'Last Modified':<25}")
    print("-" * 90)

    for page in pages:
        for obj in page.get('Contents', []):
            size = obj['Size']
            total_size += size
            count += 1
            print(f"{obj['Key']:<50} {size:>10,} {str(obj['LastModified'])[:19]:<25}")

    print(f"\nTotal: {count} objects, {total_size:,} bytes ({total_size / 1024 / 1024:.2f} MB)")

def sync_folder_to_s3(local_folder: str, bucket: str, prefix: str = ''):
    """Upload all files in a local folder to S3."""
    s3 = boto3.client('s3')
    uploaded = 0

    for root, dirs, files in os.walk(local_folder):
        for filename in files:
            local_path = os.path.join(root, filename)
            relative_path = os.path.relpath(local_path, local_folder)
            s3_key = os.path.join(prefix, relative_path).replace('\\', '/')

            s3.upload_file(local_path, bucket, s3_key)
            uploaded += 1
            print(f"  Uploaded: {s3_key}")

    print(f"✅ Synced {uploaded} files to s3://{bucket}/{prefix}")
```

---

#### RDS Automation

**`rds/create_snapshot.py` — Automated RDS snapshots**

```python
import boto3
from datetime import datetime

def create_rds_snapshot(db_instance_id: str, region: str = 'us-east-1'):
    """Create a manual RDS snapshot with a timestamp-based name."""
    rds = boto3.client('rds', region_name=region)

    timestamp = datetime.utcnow().strftime('%Y%m%d-%H%M%S')
    snapshot_id = f"{db_instance_id}-auto-{timestamp}"

    response = rds.create_db_snapshot(
        DBInstanceIdentifier=db_instance_id,
        DBSnapshotIdentifier=snapshot_id,
        Tags=[
            {'Key': 'CreatedBy', 'Value': 'boto3-automation'},
            {'Key': 'Source', 'Value': db_instance_id},
            {'Key': 'Timestamp', 'Value': timestamp}
        ]
    )

    print(f"Snapshot creation started: {snapshot_id}")
    print(f"Status: {response['DBSnapshot']['Status']}")

    # Wait for completion
    waiter = rds.get_waiter('db_snapshot_completed')
    print("Waiting for snapshot to complete...")
    waiter.wait(DBSnapshotIdentifier=snapshot_id)
    print(f"✅ Snapshot complete: {snapshot_id}")

    return snapshot_id

def list_rds_instances(region: str = 'us-east-1'):
    """List all RDS instances with status and endpoint."""
    rds = boto3.client('rds', region_name=region)
    response = rds.describe_db_instances()

    print(f"\n{'DB ID':<25} {'Status':<12} {'Class':<15} {'Engine':<10} {'Endpoint'}")
    print("-" * 100)

    for db in response['DBInstances']:
        endpoint = db.get('Endpoint', {}).get('Address', 'N/A')
        print(f"{db['DBInstanceIdentifier']:<25} "
              f"{db['DBInstanceStatus']:<12} "
              f"{db['DBInstanceClass']:<15} "
              f"{db['Engine']:<10} "
              f"{endpoint}")

if __name__ == '__main__':
    list_rds_instances()
    # create_rds_snapshot('mydb')
```

---

#### Cross-Service Inventory Report

**`utils/inventory_report.py`**

```python
import boto3
import json
from datetime import datetime

def generate_inventory_report(region: str = 'us-east-1') -> dict:
    """Generate a simple AWS resource inventory report."""
    report = {
        'generated_at': datetime.utcnow().isoformat(),
        'region': region,
        'ec2': {'instances': []},
        's3': {'buckets': []},
        'rds': {'instances': []}
    }

    # EC2 instances
    ec2 = boto3.client('ec2', region_name=region)
    paginator = ec2.get_paginator('describe_instances')
    for page in paginator.paginate():
        for res in page['Reservations']:
            for inst in res['Instances']:
                name = next((t['Value'] for t in inst.get('Tags', []) if t['Key'] == 'Name'), 'N/A')
                report['ec2']['instances'].append({
                    'id': inst['InstanceId'],
                    'name': name,
                    'type': inst['InstanceType'],
                    'state': inst['State']['Name'],
                    'public_ip': inst.get('PublicIpAddress', 'N/A')
                })

    # S3 buckets
    s3 = boto3.client('s3')
    buckets = s3.list_buckets()
    for bucket in buckets['Buckets']:
        report['s3']['buckets'].append({
            'name': bucket['Name'],
            'created': bucket['CreationDate'].isoformat()
        })

    # RDS instances
    rds = boto3.client('rds', region_name=region)
    dbs = rds.describe_db_instances()
    for db in dbs['DBInstances']:
        report['rds']['instances'].append({
            'id': db['DBInstanceIdentifier'],
            'status': db['DBInstanceStatus'],
            'class': db['DBInstanceClass'],
            'engine': f"{db['Engine']} {db['EngineVersion']}"
        })

    return report

if __name__ == '__main__':
    report = generate_inventory_report()
    print(json.dumps(report, indent=2))
    print(f"\nSummary:")
    print(f"  EC2: {len(report['ec2']['instances'])} instances")
    print(f"  S3:  {len(report['s3']['buckets'])} buckets")
    print(f"  RDS: {len(report['rds']['instances'])} instances")
```

---

## 6. Code Deep Dive

### boto3 Client vs Resource

```python
import boto3

# Low-level client — returns raw dicts
s3_client = boto3.client('s3')
response = s3_client.list_buckets()
buckets = response['Buckets']  # List of dicts

# High-level resource — returns Python objects
s3_resource = boto3.resource('s3')
for bucket in s3_resource.buckets.all():
    print(bucket.name)  # Attribute access, not dict indexing
```

### Handling Pagination

```python
# WITHOUT paginator (only gets first page, misses data if > 1000 items)
response = ec2.describe_instances()  # ❌ May be incomplete

# WITH paginator (handles all pages automatically)
paginator = ec2.get_paginator('describe_instances')
for page in paginator.paginate():     # ✅ Always complete
    for res in page['Reservations']:
        ...
```

### Error Handling with botocore

```python
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

s3 = boto3.client('s3')

try:
    s3.download_file('my-bucket', 'myfile.txt', '/tmp/myfile.txt')
except ClientError as e:
    error_code = e.response['Error']['Code']
    if error_code == '404':
        print("File not found in S3")
    elif error_code == 'AccessDenied':
        print("No permission to access this file")
    else:
        raise
except NoCredentialsError:
    print("AWS credentials not configured — run 'aws configure'")
```

---

## 7. Verification

```bash
# Run the EC2 list script
python3 ec2/list_instances.py

# Run the inventory report
python3 utils/inventory_report.py

# Test S3 upload (creates a test file)
echo "Hello boto3" > /tmp/test.txt
python3 -c "
import boto3
s3 = boto3.client('s3')
s3.upload_file('/tmp/test.txt', 'your-bucket-name', 'test.txt')
print('Upload successful')
response = s3.get_object(Bucket='your-bucket-name', Key='test.txt')
print('Content:', response['Body'].read().decode())
"

# Verify credentials
python3 -c "
import boto3
sts = boto3.client('sts')
print(sts.get_caller_identity())
"
```

---

## 8. Observations

### boto3 Credential Chain in Practice

```python
import boto3

# Check which credentials boto3 is using
session = boto3.Session()
credentials = session.get_credentials()
print(f"Credential method: {credentials.method}")
# Possible values: explicit, env, shared-credentials-file, ec2-metadata
```

### Comparing boto3 to AWS CLI

```bash
# CLI: list EC2 instances
aws ec2 describe-instances --query 'Reservations[].Instances[].InstanceId'

# boto3 equivalent:
python3 -c "
import boto3
ec2 = boto3.client('ec2')
resp = ec2.describe_instances()
ids = [i['InstanceId'] for r in resp['Reservations'] for i in r['Instances']]
print(ids)
"
```

Both call the same underlying API — boto3 gives you the full power of Python (loops, conditions, data processing, scheduling) on top of those API calls.

---

## 9. Screenshots

Capture at these key steps:
1. Terminal showing `python3 -c "import boto3; print(boto3.__version__)"` — confirming installation
2. Terminal showing `aws configure` being run with region and output format set
3. Terminal showing `python3 -c "import boto3; print(boto3.client('sts').get_caller_identity())"` — confirming auth
4. Terminal showing `python3 ec2/list_instances.py` output with instance table
5. Terminal showing `python3 s3/file_ops.py` upload and download working
6. Terminal showing `python3 rds/create_snapshot.py` snapshot completion
7. Terminal showing the full inventory report output from `utils/inventory_report.py`

---

## 10. Cleanup

boto3 itself has no resources to clean up. Clean up any AWS resources created during the exercises:

```bash
# Delete any test S3 buckets created by scripts
python3 -c "
import boto3
s3 = boto3.client('s3')
# List all objects and delete them first
bucket = 'your-test-bucket-name'
s3.delete_objects(
    Bucket=bucket,
    Delete={'Objects': [{'Key': obj['Key']} for obj in
        s3.list_objects_v2(Bucket=bucket).get('Contents', [])]}
)
s3.delete_bucket(Bucket=bucket)
print('Bucket deleted')
"

# Delete any RDS snapshots created by automation scripts
aws rds describe-db-snapshots \
  --snapshot-type manual \
  --query 'DBSnapshots[?contains(DBSnapshotIdentifier, `auto`)].DBSnapshotIdentifier' \
  --output text | xargs -I {} aws rds delete-db-snapshot --db-snapshot-identifier {}

# Deactivate virtual environment
deactivate
```

**Verify:** Run the inventory report one final time to confirm no unexpected resources remain:
```bash
python3 utils/inventory_report.py
```

---

**Prerequisites Check:**
- âœ… Required permissions: Contributor/Admin IAM role
- âœ… AWS CLI configured: ws sts get-caller-identity
- âœ… Region set: ws configure get region

**Decision Point 1:** Choose your implementation approach
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| AWS Console | Visual, learning | âœ… Good for first time |
| AWS CLI | Automation, scripting | âœ… Recommended for repeatability |

### 5A. AWS Console Method
Follow the steps_awsconsoleui.md guide for detailed console walkthrough.

### 5B. AWS CLI Method
Follow the steps.md guide for complete CLI command reference.

**Expected Outcome:**
- All AWS resources created and in Running/Active/Available state
- Service responding to requests correctly
- No errors in CloudWatch Logs

**Troubleshooting:**
- Resource creation fails: verify IAM permissions with ws iam get-user
- Service unreachable: check security group inbound rules
- CLI errors: run ws sts get-caller-identity to verify authentication
