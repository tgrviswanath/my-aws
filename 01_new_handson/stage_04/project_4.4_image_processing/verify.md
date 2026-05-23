# Verification & Validation — Project 4.4 Event-driven Image Processing

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| Source S3 Bucket | S3 → Buckets | Source bucket exists, event notification configured |
| Output S3 Bucket | S3 → Buckets | Output bucket exists, separate from source |
| S3 Event Notification | Source bucket → Properties → Event notifications | Lambda trigger on `s3:ObjectCreated:*` |
| Lambda Function | Lambda → Functions | `handson-image-processor`, Runtime = Python 3.11 |
| Lambda Layer | Lambda → Layers | Pillow layer attached to function |
| DynamoDB Table | DynamoDB → Tables | `handson-image-metadata`, Status = Active |

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
# Expected: Events=["s3:ObjectCreated:*"], Lambda=handson-image-processor ARN

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
aws s3 cp s3://$OUTPUT_BUCKET/processed/thumbnail/photos/test.jpg /tmp/thumbnail.jpg
python3 -c "
from PIL import Image
img = Image.open('/tmp/thumbnail.jpg')
print(f'Thumbnail size: {img.size}')
assert img.size == (150, 150), f'Expected 150x150, got {img.size}'
print('✅ Thumbnail dimensions correct')
"
# Expected: Thumbnail size: (150, 150)

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
  --query "Items[*].{key:s3_key.S,status:status.S,thumbnail:thumbnail_key.S}"
# Expected: record with status=processed, thumbnail_key set
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
# aws_lambda_layer_version.pillow
# aws_lambda_permission.s3
# aws_dynamodb_table.metadata
# aws_iam_role.lambda_exec

terraform state show aws_s3_bucket_notification.source
# Shows: lambda_function with events=["s3:ObjectCreated:*"]

terraform state show aws_lambda_function.processor
# Shows: layers containing Pillow layer ARN

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

**Lambda log:**
```
Processing photos/test.jpg (2000x1500, 245KB)
Created thumbnail: 150x150 (8KB)
Created medium: 800x600 (98KB)
Metadata saved to DynamoDB
Duration: 1.2s
```

**DynamoDB metadata:**
```json
{ "s3_key": "photos/test.jpg", "status": "processed", "thumbnail_key": "processed/thumbnail/photos/test.jpg", "original_size": "245KB" }
```

---

## 6. Verification Checklist

- [ ] Source S3 bucket has event notification → Lambda on `s3:ObjectCreated:*`
- [ ] Output S3 bucket is separate from source (prevents recursive trigger)
- [ ] Lambda function active with Pillow layer attached
- [ ] Upload test image → Lambda triggers automatically within ~5s
- [ ] Output bucket has `processed/thumbnail/` and `processed/medium/` folders
- [ ] Thumbnail dimensions = 150×150
- [ ] Medium dimensions ≤ 800×600
- [ ] DynamoDB metadata record created with status = processed
- [ ] Lambda logs show processing steps without errors
- [ ] `terraform plan` shows no changes
