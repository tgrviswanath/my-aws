# Amazon S3 — Simple Storage Service Deep Dive

## What is S3?
S3 is object storage — store any amount of data, retrieve it from anywhere. Objects are stored in buckets. S3 is the foundation of most AWS data architectures.

```
S3 Object:
├── Key (path/filename.ext)
├── Value (data, up to 5TB)
├── Version ID (if versioning enabled)
├── Metadata (system + user-defined)
└── Tags (up to 10 key-value pairs)
```

---

## Storage Classes

| Class | Availability | Retrieval | Min Duration | Use Case |
|-------|-------------|-----------|-------------|---------|
| Standard | 99.99% | Instant | None | Frequently accessed data |
| Standard-IA | 99.9% | Instant | 30 days | Infrequent access, backups |
| One Zone-IA | 99.5% | Instant | 30 days | Reproducible infrequent data |
| Intelligent-Tiering | 99.9% | Instant/minutes/hours | None | Unknown access patterns |
| Glacier Instant | 99.9% | Instant | 90 days | Archives accessed quarterly |
| Glacier Flexible | 99.99% | 1-12 hours | 90 days | Long-term archives |
| Glacier Deep Archive | 99.99% | 12-48 hours | 180 days | 7-10 year compliance archives |

**Durability**: All classes = 99.999999999% (11 nines) — data replicated across 3+ AZs (except One Zone-IA).

---

## Lifecycle Policies

Automatically transition objects between storage classes or expire them.

```json
{
  "Rules": [
    {
      "ID": "archive-old-logs",
      "Status": "Enabled",
      "Filter": {"Prefix": "logs/"},
      "Transitions": [
        {"Days": 30, "StorageClass": "STANDARD_IA"},
        {"Days": 90, "StorageClass": "GLACIER"},
        {"Days": 365, "StorageClass": "DEEP_ARCHIVE"}
      ],
      "Expiration": {"Days": 2555}
    },
    {
      "ID": "delete-incomplete-multipart",
      "Status": "Enabled",
      "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 7}
    }
  ]
}
```

```bash
aws s3api put-bucket-lifecycle-configuration \
  --bucket my-bucket \
  --lifecycle-configuration file://lifecycle.json
```

---

## Versioning

```bash
# Enable versioning
aws s3api put-bucket-versioning \
  --bucket my-bucket \
  --versioning-configuration Status=Enabled

# List versions
aws s3api list-object-versions --bucket my-bucket --prefix myfile.txt

# Restore previous version (delete the delete marker)
aws s3api delete-object \
  --bucket my-bucket \
  --key myfile.txt \
  --version-id <delete-marker-version-id>

# Permanently delete a specific version
aws s3api delete-object \
  --bucket my-bucket \
  --key myfile.txt \
  --version-id <version-id>
```

---

## Security

### Bucket Policies (Resource-based)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowCloudFrontOnly",
      "Effect": "Allow",
      "Principal": {
        "Service": "cloudfront.amazonaws.com"
      },
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::my-bucket/*",
      "Condition": {
        "StringEquals": {
          "AWS:SourceArn": "arn:aws:cloudfront::123456789:distribution/ABCDEF"
        }
      }
    },
    {
      "Sid": "DenyNonHTTPS",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": ["arn:aws:s3:::my-bucket", "arn:aws:s3:::my-bucket/*"],
      "Condition": {
        "Bool": {"aws:SecureTransport": "false"}
      }
    }
  ]
}
```

### Block Public Access (Always enable for private buckets)

```bash
aws s3api put-public-access-block \
  --bucket my-bucket \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,\
    BlockPublicPolicy=true,RestrictPublicBuckets=true
```

### Encryption

```bash
# Enable default encryption (SSE-S3)
aws s3api put-bucket-encryption \
  --bucket my-bucket \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      },
      "BucketKeyEnabled": true
    }]
  }'

# Use KMS key (SSE-KMS)
aws s3api put-bucket-encryption \
  --bucket my-bucket \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "aws:kms",
        "KMSMasterKeyID": "arn:aws:kms:us-east-1:123456789:key/abc-123"
      },
      "BucketKeyEnabled": true
    }]
  }'
```

---

## Performance Optimization

### Multipart Upload (files > 100MB)

```bash
# AWS CLI handles this automatically with aws s3 cp
aws s3 cp large-file.zip s3://my-bucket/ \
  --storage-class STANDARD \
  --expected-size 5368709120  # 5GB

# Manual multipart (for SDK)
# 1. Initiate
aws s3api create-multipart-upload \
  --bucket my-bucket --key large-file.zip

# 2. Upload parts (parallel)
aws s3api upload-part \
  --bucket my-bucket --key large-file.zip \
  --upload-id <upload-id> \
  --part-number 1 \
  --body part1.zip

# 3. Complete
aws s3api complete-multipart-upload \
  --bucket my-bucket --key large-file.zip \
  --upload-id <upload-id> \
  --multipart-upload file://parts.json
```

### S3 Transfer Acceleration

Routes uploads through CloudFront edge locations — faster for global uploads.

```bash
# Enable
aws s3api put-bucket-accelerate-configuration \
  --bucket my-bucket \
  --accelerate-configuration Status=Enabled

# Use accelerated endpoint
aws s3 cp file.zip s3://my-bucket/ \
  --endpoint-url https://my-bucket.s3-accelerate.amazonaws.com
```

### Prefix Partitioning
S3 scales to 3,500 PUT/COPY/POST/DELETE and 5,500 GET/HEAD requests per second **per prefix**.

```
# Good: distribute across prefixes
s3://bucket/2024/01/user123/file.jpg
s3://bucket/2024/02/user456/file.jpg

# Bad: all in one prefix (bottleneck)
s3://bucket/uploads/file1.jpg
s3://bucket/uploads/file2.jpg
```

---

## S3 Event Notifications

```bash
# Trigger Lambda on object creation
aws s3api put-bucket-notification-configuration \
  --bucket my-bucket \
  --notification-configuration '{
    "LambdaFunctionConfigurations": [{
      "LambdaFunctionArn": "arn:aws:lambda:us-east-1:123456789:function:process-upload",
      "Events": ["s3:ObjectCreated:*"],
      "Filter": {
        "Key": {
          "FilterRules": [
            {"Name": "prefix", "Value": "uploads/"},
            {"Name": "suffix", "Value": ".jpg"}
          ]
        }
      }
    }]
  }'
```

---

## S3 Replication

```bash
# Cross-Region Replication (CRR) — requires versioning on both buckets
aws s3api put-bucket-replication \
  --bucket source-bucket \
  --replication-configuration '{
    "Role": "arn:aws:iam::123456789:role/s3-replication-role",
    "Rules": [{
      "Status": "Enabled",
      "Filter": {"Prefix": ""},
      "Destination": {
        "Bucket": "arn:aws:s3:::destination-bucket",
        "StorageClass": "STANDARD_IA",
        "ReplicationTime": {
          "Status": "Enabled",
          "Time": {"Minutes": 15}
        }
      },
      "DeleteMarkerReplication": {"Status": "Enabled"}
    }]
  }'
```

---

## Pre-signed URLs

```bash
# Generate pre-signed URL (valid 1 hour)
aws s3 presign s3://my-bucket/private-file.pdf \
  --expires-in 3600

# Python SDK
import boto3
s3 = boto3.client('s3')
url = s3.generate_presigned_url(
    'get_object',
    Params={'Bucket': 'my-bucket', 'Key': 'private-file.pdf'},
    ExpiresIn=3600
)

# Pre-signed POST (for browser uploads)
response = s3.generate_presigned_post(
    'my-bucket',
    'uploads/${filename}',
    Fields={'Content-Type': 'image/jpeg'},
    Conditions=[
        ['content-length-range', 1, 10485760],  # 1B to 10MB
        {'Content-Type': 'image/jpeg'}
    ],
    ExpiresIn=3600
)
```

---

## CloudFormation Template

```yaml
Resources:
  DataBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Sub "${AWS::AccountId}-data-${AWS::Region}"
      VersioningConfiguration:
        Status: Enabled
      BucketEncryption:
        ServerSideEncryptionConfiguration:
          - ServerSideEncryptionByDefault:
              SSEAlgorithm: aws:kms
              KMSMasterKeyID: !Ref KMSKey
            BucketKeyEnabled: true
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        IgnorePublicAcls: true
        BlockPublicPolicy: true
        RestrictPublicBuckets: true
      LifecycleConfiguration:
        Rules:
          - Id: archive-old-data
            Status: Enabled
            Transitions:
              - TransitionInDays: 90
                StorageClass: GLACIER
            ExpirationInDays: 2555
      NotificationConfiguration:
        LambdaConfigurations:
          - Event: s3:ObjectCreated:*
            Filter:
              S3Key:
                Rules:
                  - Name: prefix
                    Value: uploads/
            Function: !GetAtt ProcessFunction.Arn
      Tags:
        - Key: Environment
          Value: production
```

---

## Interview Q&A

### Q1: What is the difference between S3 storage classes?
Standard: frequent access, highest cost. Standard-IA: infrequent access, lower storage cost but retrieval fee + 30-day minimum. Glacier: archival, hours to retrieve. Deep Archive: cheapest, 12-48hr retrieval. Intelligent-Tiering: automatically moves objects between tiers based on access patterns — best when access patterns are unknown.

### Q2: How does S3 achieve 11 nines of durability?
S3 stores data redundantly across a minimum of 3 AZs (except One Zone-IA). Uses erasure coding — data is split into chunks with parity, so multiple drive/AZ failures can be tolerated. Continuous integrity checking with checksums. Automatic repair of corrupted data.

### Q3: What is the difference between S3 bucket policies and IAM policies?
**Bucket policy**: Resource-based, attached to the bucket. Controls who can access the bucket (cross-account, public access, service principals). Evaluated alongside IAM policies.
**IAM policy**: Identity-based, attached to users/roles. Controls what S3 actions an identity can perform. For cross-account access, both bucket policy AND IAM policy must allow the action.

### Q4: How do you secure S3 data?
1. Block Public Access at account and bucket level
2. Bucket policies: deny non-HTTPS, restrict to specific principals
3. Default encryption (SSE-S3 or SSE-KMS)
4. Versioning + MFA Delete for critical data
5. S3 Object Lock for compliance (WORM)
6. VPC Endpoints to keep traffic off internet
7. CloudTrail + S3 access logs for auditing
8. Macie for sensitive data discovery

### Q5: What is S3 Object Lock and when would you use it?
Object Lock prevents objects from being deleted or overwritten for a fixed period or indefinitely. Two modes: **Governance** (users with special permission can override), **Compliance** (no one can delete, including root). Use for: regulatory compliance (SEC, FINRA), ransomware protection, audit logs that must not be tampered with.
