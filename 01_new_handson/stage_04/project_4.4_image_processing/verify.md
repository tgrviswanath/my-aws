# Verification & Validation — Project 4.4 Event-driven Image Processing

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| Source S3 Bucket | S3 → Buckets | Source bucket exists, event notification configured |
| Output S3 Bucket | S3 → Buckets | Output bucket exists, separate from source |
| S3 Event Notification | Source bucket → Properties → Event notifications | Lambda trigger on `s3:ObjectCreated:*` (filtered to `.jpg` and `.png`) |
| Lambda Function | Lambda → Functions | `handson-img-proc-processor`, Runtime = Python 3.11, Memory = 512MB |
| Lambda Layer | Lambda → Layers | Pillow layer attached (added manually — not in Terraform) |
| DynamoDB Table | DynamoDB → Tables | `handson-img-proc-metadata`, Status = Active |

📸 Screenshot: S3 source bucket with event notification to Lambda  
📸 Screenshot: Output bucket showing `thumbnail/` and `medium/` folders after upload  
📸 Screenshot: Lambda CloudWatch logs showing processing steps  
📸 Screenshot: DynamoDB metadata record for processed image

---

## 2. AWS CLI Verification

```bash
SOURCE_BUCKET=$(cd terraform && terraform output -raw source_bucket)
OUTPUT_BUCKET=$(cd terraform && terraform output -raw output_bucket)
LAMBDA_NAME=$(cd terraform && terraform output -raw lambda_name)
TABLE=$(cd terraform && terraform output -raw table_name)

# 2.1 S3 event notification configured
aws s3api get-bucket-notification-configuration --bucket $SOURCE_BUCKET \
  --query "LambdaFunctionConfigurations[*].{Events:Events,Lambda:LambdaFunctionArn}"
# Expected: Events=["s3:ObjectCreated:*"], Lambda=handson-img-proc-processor ARN

# 2.2 Lambda has Pillow layer
aws lambda get-function --function-name $LAMBDA_NAME \
  --query "Configuration.Layers[*].Arn"
# Expected: Pillow layer ARN listed

# 2.3 Upload test image and trigger Lambda
curl -o /tmp/test.jpg https://picsum.photos/2000/1500
aws s3 cp /tmp/test.jpg s3://$SOURCE_BUCKET/photos/test.jpg
echo "Uploaded — waiting for Lambda to process..."
sleep 8

# 2.4 Output bucket has processed images
aws s3 ls s3://$OUTPUT_BUCKET/processed/ --recursive
# Expected:
# processed/thumbnail/photos/test.jpg
# processed/medium/photos/test.jpg

# 2.5 Download and verify thumbnail dimensions
# NOTE: Pillow thumbnail() preserves aspect ratio — a 2000x1500 image becomes 150x113, NOT 150x150
aws s3 cp s3://$OUTPUT_BUCKET/processed/thumbnail/photos/test.jpg /tmp/thumbnail.jpg
python3 -c "
from PIL import Image
img = Image.open('/tmp/thumbnail.jpg')
print(f'Thumbnail size: {img.size}')
w, h = img.size
assert w <= 150 and h <= 150, f'Expected max 150x150, got {img.size}'
print('✅ Thumbnail dimensions correct (aspect ratio preserved)')
"
# Expected: e.g. (150, 113) for a 2000x1500 source — longest side = 150, other scaled proportionally

# 2.6 Download and verify medium dimensions
aws s3 cp s3://$OUTPUT_BUCKET/processed/medium/photos/test.jpg /tmp/medium.jpg
python3 -c "
from PIL import Image
img = Image.open('/tmp/medium.jpg')
print(f'Medium size: {img.size}')
w, h = img.size
assert w <= 800 and h <= 600, f'Expected max 800x600, got {img.size}'
print('✅ Medium dimensions correct')
"

# 2.7 DynamoDB metadata record
aws dynamodb scan --table-name $TABLE \
  --query "Items[*].{key:image_key.S,original_size:original_size.S,format:format.S,processed_at:processed_at.S}"
# Expected: record with image_key=photos/test.jpg, original_size=2000x1500, format=JPEG
```

---

## 3. Terraform State Verification

```bash
cd terraform

terraform state list
# Expected:
# aws_s3_bucket.source
# aws_s3_bucket.output
# aws_s3_bucket_notification.source
# aws_lambda_function.processor
# aws_lambda_permission.s3
# aws_dynamodb_table.metadata
# aws_iam_role.lambda
# aws_iam_role_policy_attachment.lambda_basic
# aws_iam_role_policy.s3_dynamo
# NOTE: aws_lambda_layer_version is NOT in terraform — Pillow layer is added manually

terraform state show aws_s3_bucket_notification.source
# Shows: lambda_function with events=["s3:ObjectCreated:*"], filter_suffix=".jpg" and ".png"

terraform state show aws_lambda_function.processor
# Shows: function_name=handson-img-proc-processor, memory_size=512, timeout=60

terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

---

## 4. Health Check — Lambda Logs

```bash
# Check Lambda logs for the processing run
aws logs filter-log-events \
  --log-group-name /aws/lambda/$LAMBDA_NAME \
  --filter-pattern "Processing" \
  --start-time $(date -d '5 minutes ago' +%s000 2>/dev/null || date -v-5M +%s000) \
  --query "events[*].message"
# Expected: log lines showing "Processing photos/test.jpg", sizes, durations

# Check for any errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/$LAMBDA_NAME \
  --filter-pattern "ERROR" \
  --start-time $(date -d '5 minutes ago' +%s000 2>/dev/null || date -v-5M +%s000)
# Expected: no ERROR entries
```

---

## 5. Expected Successful Outputs

**S3 output listing:**
```
2024-01-01 12:00:05   8432 processed/thumbnail/photos/test.jpg
2024-01-01 12:00:05  98765 processed/medium/photos/test.jpg
```

**Lambda log (actual format from handler.py print statements):**
```
Processing: s3://handson-img-proc-source-123456789012/photos/test.jpg (245000 bytes)
  Created thumbnail: processed/thumbnail/photos/test.jpg (150, 113)
  Created medium: processed/medium/photos/test.jpg (800, 600)
Done: photos/test.jpg → ['thumbnail', 'medium']
```

**DynamoDB metadata:**
```json
{
  "image_key": "photos/test.jpg",
  "source_bucket": "handson-img-proc-source-123456789012",
  "output_bucket": "handson-img-proc-output-123456789012",
  "original_size": "2000x1500",
  "file_size_bytes": 245000,
  "format": "JPEG",
  "outputs": {
    "thumbnail": {"key": "processed/thumbnail/photos/test.jpg", "dimensions": "150x113"},
    "medium":    {"key": "processed/medium/photos/test.jpg",    "dimensions": "800x600"}
  },
  "processed_at": "2024-01-01T12:00:05Z"
}
```

---

## 6. Verification Checklist

- [ ] Source S3 bucket has event notification → Lambda on `s3:ObjectCreated:*`
- [ ] Output S3 bucket is separate from source (prevents recursive trigger)
- [ ] Lambda function active with Pillow layer attached
- [ ] Upload test image → Lambda triggers automatically within ~5s
- [ ] Output bucket has `processed/thumbnail/` and `processed/medium/` folders
- [ ] Thumbnail dimensions fit within 150×150 (aspect ratio preserved — e.g. 150×113 for landscape image)
- [ ] Medium dimensions fit within 800×600 (aspect ratio preserved)
- [ ] DynamoDB `handson-img-proc-metadata` record created with image_key, original_size, outputs, processed_at
- [ ] Lambda logs show processing steps without errors
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
