# S3 — Real-World Use Cases

## Use Case 1: Host a React/Angular SPA (Static Website)

**Business Problem**: Deploy a React app globally with HTTPS, custom domain, and automatic cache invalidation on deploy.

```bash
BUCKET="my-spa-app-prod"
DOMAIN="app.mycompany.com"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# 1. Create bucket (name must match domain for Route 53)
aws s3api create-bucket --bucket $BUCKET --region us-east-1

# 2. Block all public access (CloudFront will serve it, not S3 directly)
aws s3api put-public-access-block \
  --bucket $BUCKET \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,\
    BlockPublicPolicy=true,RestrictPublicBuckets=true

# 3. Enable versioning (for rollbacks)
aws s3api put-bucket-versioning \
  --bucket $BUCKET \
  --versioning-configuration Status=Enabled

# 4. Build and deploy React app
npm run build
aws s3 sync ./build s3://$BUCKET/ \
  --delete \
  --cache-control "max-age=31536000,immutable" \
  --exclude "index.html"

# index.html should NOT be cached (always fresh)
aws s3 cp ./build/index.html s3://$BUCKET/index.html \
  --cache-control "no-cache,no-store,must-revalidate" \
  --content-type "text/html"

# 5. Invalidate CloudFront cache after deploy
DIST_ID="E1234567890ABC"
aws cloudfront create-invalidation \
  --distribution-id $DIST_ID \
  --paths "/*"

echo "Deployed! Site live at https://$DOMAIN"
```

**What you learn**: S3 + CloudFront pattern, cache-control headers, versioning for rollbacks, invalidation.

---

## Use Case 2: Data Lake with Lifecycle Policies

**Business Problem**: Store 10TB of application logs. Keep hot data for 30 days, archive after 90 days, delete after 7 years.

```bash
BUCKET="company-data-lake-prod"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# 1. Create data lake bucket with versioning + encryption
aws s3api create-bucket --bucket $BUCKET --region us-east-1

aws s3api put-bucket-versioning \
  --bucket $BUCKET \
  --versioning-configuration Status=Enabled

aws s3api put-bucket-encryption \
  --bucket $BUCKET \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "aws:kms"
      },
      "BucketKeyEnabled": true
    }]
  }'

# 2. Lifecycle policy: auto-tier and expire
aws s3api put-bucket-lifecycle-configuration \
  --bucket $BUCKET \
  --lifecycle-configuration '{
    "Rules": [
      {
        "ID": "logs-lifecycle",
        "Status": "Enabled",
        "Filter": {"Prefix": "logs/"},
        "Transitions": [
          {"Days": 30,  "StorageClass": "STANDARD_IA"},
          {"Days": 90,  "StorageClass": "GLACIER"},
          {"Days": 365, "StorageClass": "DEEP_ARCHIVE"}
        ],
        "Expiration": {"Days": 2555},
        "NoncurrentVersionExpiration": {"NoncurrentDays": 30}
      },
      {
        "ID": "abort-incomplete-multipart",
        "Status": "Enabled",
        "Filter": {"Prefix": ""},
        "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 7}
      }
    ]
  }'

# 3. Upload data with partitioning (Hive-style for Athena)
DATE=$(date +%Y/%m/%d)
aws s3 cp app.log s3://$BUCKET/logs/year=$(date +%Y)/month=$(date +%m)/day=$(date +%d)/app.log

# 4. Check storage class distribution
aws s3api list-objects-v2 \
  --bucket $BUCKET \
  --prefix "logs/" \
  --query 'Contents[*].{Key:Key,StorageClass:StorageClass,Size:Size}' \
  --output table

# 5. Restore from Glacier (when needed)
aws s3api restore-object \
  --bucket $BUCKET \
  --key "logs/year=2023/month=01/day=01/app.log" \
  --restore-request '{"Days": 7, "GlacierJobParameters": {"Tier": "Standard"}}'

# Check restore status
aws s3api head-object \
  --bucket $BUCKET \
  --key "logs/year=2023/month=01/day=01/app.log" \
  --query 'Restore'
```

**What you learn**: Storage tiers, lifecycle policies, Hive partitioning for Athena, Glacier restore.

---

## Use Case 3: Secure Cross-Account S3 Access

**Business Problem**: Account A (data team) needs to read from Account B's (production) S3 bucket without copying data.

```bash
# ── In Account B (bucket owner) ──────────────────────────────────────────────
BUCKET="prod-data-bucket"
ACCOUNT_A_ID="111111111111"
ACCOUNT_B_ID="222222222222"

# Bucket policy: allow Account A to read
aws s3api put-bucket-policy \
  --bucket $BUCKET \
  --policy "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [
      {
        \"Sid\": \"AllowAccountARead\",
        \"Effect\": \"Allow\",
        \"Principal\": {\"AWS\": \"arn:aws:iam::${ACCOUNT_A_ID}:root\"},
        \"Action\": [\"s3:GetObject\", \"s3:ListBucket\"],
        \"Resource\": [
          \"arn:aws:s3:::${BUCKET}\",
          \"arn:aws:s3:::${BUCKET}/*\"
        ]
      }
    ]
  }"

# ── In Account A (data team) ──────────────────────────────────────────────────
# IAM policy for data team role
aws iam put-role-policy \
  --role-name "data-analyst-role" \
  --policy-name "CrossAccountS3Access" \
  --policy-document "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [{
      \"Effect\": \"Allow\",
      \"Action\": [\"s3:GetObject\", \"s3:ListBucket\"],
      \"Resource\": [
        \"arn:aws:s3:::${BUCKET}\",
        \"arn:aws:s3:::${BUCKET}/*\"
      ]
    }]
  }"

# Now data team can access prod bucket directly
aws s3 ls s3://$BUCKET/ --profile data-analyst
aws s3 cp s3://$BUCKET/data.parquet ./local/ --profile data-analyst
```

**What you learn**: Cross-account bucket policies, principal ARNs, least-privilege access.

---

## Use Case 4: Pre-signed URLs for Secure File Upload

**Business Problem**: Users upload profile photos directly to S3 from the browser. You don't want to proxy through your server (bandwidth cost).

```python
# Backend: generate pre-signed URL (Python/FastAPI)
import boto3
import uuid
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()
s3 = boto3.client('s3', region_name='us-east-1')
BUCKET = "user-uploads-prod"

class UploadRequest(BaseModel):
    filename: str
    content_type: str
    user_id: str

@app.post("/upload-url")
def get_upload_url(req: UploadRequest):
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if req.content_type not in allowed_types:
        return {"error": "File type not allowed"}

    # Generate unique key (prevent path traversal)
    ext = req.filename.rsplit(".", 1)[-1].lower()
    key = f"users/{req.user_id}/avatar/{uuid.uuid4()}.{ext}"

    # Generate pre-signed POST (more secure than PUT — enforces conditions)
    presigned = s3.generate_presigned_post(
        Bucket=BUCKET,
        Key=key,
        Fields={
            "Content-Type": req.content_type,
            "x-amz-meta-user-id": req.user_id,
        },
        Conditions=[
            {"Content-Type": req.content_type},
            ["content-length-range", 1, 5_242_880],  # 1B to 5MB
            {"x-amz-meta-user-id": req.user_id},
        ],
        ExpiresIn=300  # 5 minutes
    )
    return {"upload_url": presigned["url"], "fields": presigned["fields"], "key": key}
```

```javascript
// Frontend: upload directly to S3
async function uploadAvatar(file) {
  // 1. Get pre-signed URL from your backend
  const { upload_url, fields, key } = await fetch('/upload-url', {
    method: 'POST',
    body: JSON.stringify({ filename: file.name, content_type: file.type, user_id: userId })
  }).then(r => r.json());

  // 2. Upload directly to S3 (no server proxy!)
  const formData = new FormData();
  Object.entries(fields).forEach(([k, v]) => formData.append(k, v));
  formData.append('file', file);  // Must be last!

  const response = await fetch(upload_url, { method: 'POST', body: formData });
  if (response.ok) console.log('Uploaded to S3:', key);
}
```

**What you learn**: Pre-signed POST vs PUT, content-length-range conditions, direct browser-to-S3 upload pattern.

---

## Use Case 5: S3 Event-Driven Processing

**Business Problem**: When a CSV is uploaded to S3, automatically validate it, convert to Parquet, and notify the data team.

```bash
# 1. Create Lambda function for processing
aws lambda create-function \
  --function-name "s3-csv-processor" \
  --runtime python3.12 \
  --role arn:aws:iam::123456789:role/lambda-s3-role \
  --handler handler.handler \
  --zip-file fileb://function.zip \
  --timeout 300 \
  --memory-size 1024 \
  --environment Variables='{
    "OUTPUT_BUCKET": "processed-data",
    "SNS_TOPIC": "arn:aws:sns:us-east-1:123456789:data-team-alerts"
  }'

# 2. Grant S3 permission to invoke Lambda
aws lambda add-permission \
  --function-name "s3-csv-processor" \
  --statement-id "s3-trigger" \
  --action "lambda:InvokeFunction" \
  --principal "s3.amazonaws.com" \
  --source-arn "arn:aws:s3:::raw-uploads" \
  --source-account "123456789"

# 3. Configure S3 event notification
aws s3api put-bucket-notification-configuration \
  --bucket "raw-uploads" \
  --notification-configuration '{
    "LambdaFunctionConfigurations": [{
      "LambdaFunctionArn": "arn:aws:lambda:us-east-1:123456789:function:s3-csv-processor",
      "Events": ["s3:ObjectCreated:*"],
      "Filter": {
        "Key": {
          "FilterRules": [
            {"Name": "prefix", "Value": "uploads/"},
            {"Name": "suffix", "Value": ".csv"}
          ]
        }
      }
    }]
  }'

# 4. Test: upload a CSV and watch it process
aws s3 cp test_data.csv s3://raw-uploads/uploads/test_data.csv
aws logs tail /aws/lambda/s3-csv-processor --follow
```

**What you learn**: S3 event notifications, Lambda triggers, prefix/suffix filters, event-driven architecture.

---

## Common Mistakes

| Mistake | Impact | Fix |
|---------|--------|-----|
| Public bucket for static website | Data exposure | Use CloudFront + OAC instead |
| No lifecycle policy | Costs grow unbounded | Add lifecycle rules from day 1 |
| Using `s3:*` in bucket policy | Over-permissive | Specify exact actions needed |
| Not enabling versioning | Can't recover deleted files | Enable versioning on critical buckets |
| Storing secrets in S3 objects | Credential exposure | Use Secrets Manager |
| Large files without multipart | Slow uploads, failures | Use multipart for files > 100MB |
