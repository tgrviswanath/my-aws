# Cost Estimate — Python Automation with boto3

> boto3 itself is free. Costs come from the AWS resources your scripts interact with.

---

## Free Tier

boto3 is the AWS SDK for Python — it is not a service and has no direct cost.

| Component | Cost | Notes |
|-----------|------|-------|
| boto3 library | $0.00 | Open source, free to use |
| IAM user/role for boto3 | $0.00 | IAM is always free |
| AWS CLI (`aws configure`) | $0.00 | CLI tool is free |
| Python runtime (local) | $0.00 | Open source |

---

## API Call Costs

boto3 makes API calls on your behalf. Most AWS API calls are free (with limits):

### EC2 API Calls

| API Call | Cost |
|----------|------|
| `describe_instances` | $0.00 |
| `describe_regions` | $0.00 |
| `start_instances` | $0.00 |
| `stop_instances` | $0.00 |
| EC2 Data Transfer API | Free (metadata) |

**EC2 API = Free** — all EC2 control plane API calls are free.

### S3 API Calls

| Operation | Free Tier | After Free Tier |
|-----------|-----------|----------------|
| PUT, COPY, POST, LIST requests | 2,000/month | $0.005 per 1,000 requests |
| GET, SELECT, and all others | 20,000/month | $0.0004 per 1,000 requests |
| Data retrievals | 2,000/month | $0.0004 per 1,000 |

**Typical boto3 script usage:** 50–200 API calls per run → well within free tier.

Example cost for a script running 10 times/day (30 days = 300 runs, ~100 calls each):
- 30,000 PUT/LIST calls × ($0.005/1000) = **$0.15/month**
- 30,000 GET calls × ($0.0004/1000) = **$0.012/month**

### RDS API Calls

| API Call | Cost |
|----------|------|
| `describe_db_instances` | $0.00 |
| `create_db_snapshot` | $0.00 (snapshot storage has a cost) |
| All RDS control plane API calls | $0.00 |

**RDS API = Free** — API calls themselves have no charge.

---

## Actual Resource Costs

While boto3 API calls are cheap/free, the resources you create with boto3 are billed normally:

| Resource Created | Approximate Cost |
|-----------------|-----------------|
| S3 bucket (5 GB stored) | $0.115/GB = $0.58/month |
| EC2 t2.micro (boto3 starts it) | $0.0116/hour = $8.50/month (after free tier) |
| RDS snapshot (20 GB) | First 20 GB = free (100% of DB size) |
| EC2 Elastic IP (if allocated) | $0.005/hour if unattached = $3.60/month |

**For this learning project (running scripts, not leaving resources up):** ~$0.00

---

## Total

| Scenario | Monthly Cost |
|----------|-------------|
| **API calls only** (no persistent resources) | **~$0.00** |
| Running automation scripts 10×/day, deleting resources after | **< $0.05** |
| Leaving S3 buckets with data from scripts | ~$0.01–$1.00 depending on storage |
| Accidentally leaving EC2 instances running | $8.50+/month (EC2 cost, not boto3) |

**Bottom line:** boto3 + IAM = **$0.00**. Pay only for the AWS resources your scripts create and keep running.

---

## Free Tier Summary Table

| Item | Free? | Notes |
|------|-------|-------|
| boto3 SDK | ✅ Always free | |
| IAM users/roles | ✅ Always free | |
| EC2 API calls | ✅ Always free | |
| RDS API calls | ✅ Always free | |
| S3 API calls | ✅ Free tier: 20K GET, 2K PUT/month | |
| S3 storage | ✅ Free tier: 5 GB/month (12 months) | |
| S3 data transfer out | ✅ Free tier: 1 GB/month | |
| EC2 instances created | Free tier: 750 hrs t2.micro (12 months) | Resource cost, not SDK |
| RDS instances created | Free tier: 750 hrs t2.micro (12 months) | Resource cost, not SDK |

---

## Cleanup

Clean up any resources created during automation testing:

```bash
# Delete any test S3 buckets (empty them first)
python3 << 'EOF'
import boto3

s3 = boto3.client('s3')
# List all buckets
buckets = s3.list_buckets()['Buckets']
test_buckets = [b['Name'] for b in buckets if 'boto3-test' in b['Name'] or 'test-auto' in b['Name']]

for bucket in test_buckets:
    # Delete all objects first
    objs = s3.list_objects_v2(Bucket=bucket).get('Contents', [])
    if objs:
        s3.delete_objects(Bucket=bucket, Delete={'Objects': [{'Key': o['Key']} for o in objs]})
    s3.delete_bucket(Bucket=bucket)
    print(f"Deleted bucket: {bucket}")
EOF

# Delete any automation snapshots
aws rds describe-db-snapshots \
  --snapshot-type manual \
  --query 'DBSnapshots[?contains(DBSnapshotIdentifier, `auto`)].DBSnapshotIdentifier' \
  --output text | xargs -n1 -I {} \
  aws rds delete-db-snapshot --db-snapshot-identifier {} 2>/dev/null

# Revoke the access key if you're done with this project
# IAM → Users → boto3-local-user → Security credentials → Delete access key

echo "✅ Cleanup complete — $0 ongoing costs from boto3"
```

### Console Cleanup

1. IAM → Users → `boto3-local-user` → Security credentials → Deactivate and delete access key
2. IAM → Users → `boto3-local-user` → Delete user (if project complete)
3. IAM → Roles → `boto3-ec2-automation-role` → Delete role
4. S3 → Delete any test buckets created during exercises

**After cleanup:** $0.00/month. boto3 itself never charges anything.
