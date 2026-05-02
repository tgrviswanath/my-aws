# Lab 02: Deploy Serverless Application with Lambda + S3 + API Gateway

## Objective
Build a serverless image processing pipeline: upload image to S3 → Lambda generates thumbnail → store in output bucket → API to retrieve.

## Prerequisites
- AWS CLI configured
- Python 3.12 installed locally
- Pillow library: `pip install Pillow`

## Estimated Time: 60 minutes
## Estimated Cost: ~$0.00 (within free tier)

---

## Architecture

```
User → API Gateway → Lambda (get image URL)
                          ↑
S3 (uploads) → Lambda (resize) → S3 (thumbnails)
```

---

## Step 1: Create S3 Buckets

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="us-east-1"
UPLOAD_BUCKET="${ACCOUNT_ID}-lab-uploads"
THUMB_BUCKET="${ACCOUNT_ID}-lab-thumbnails"

# Create upload bucket
aws s3api create-bucket \
  --bucket $UPLOAD_BUCKET \
  --region $REGION

# Create thumbnail bucket
aws s3api create-bucket \
  --bucket $THUMB_BUCKET \
  --region $REGION

# Block public access on both
for BUCKET in $UPLOAD_BUCKET $THUMB_BUCKET; do
  aws s3api put-public-access-block \
    --bucket $BUCKET \
    --public-access-block-configuration \
      BlockPublicAcls=true,IgnorePublicAcls=true,\
      BlockPublicPolicy=true,RestrictPublicBuckets=true
done

echo "Buckets created: $UPLOAD_BUCKET, $THUMB_BUCKET"
```

## Step 2: Create Lambda Function Code

```bash
mkdir -p lab-lambda/src
cat > lab-lambda/src/thumbnail.py <<'PYTHON'
import boto3
import json
import os
import io
import logging
from PIL import Image

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')
THUMB_BUCKET = os.environ['THUMB_BUCKET']
THUMB_SIZE = (200, 200)

def handler(event, context):
    """Process S3 upload events and create thumbnails."""
    processed = []
    errors = []
    
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        
        logger.info(f"Processing: s3://{bucket}/{key}")
        
        try:
            # Download original image
            response = s3.get_object(Bucket=bucket, Key=key)
            image_data = response['Body'].read()
            
            # Create thumbnail
            image = Image.open(io.BytesIO(image_data))
            image.thumbnail(THUMB_SIZE, Image.Resampling.LANCZOS)
            
            # Convert to bytes
            output = io.BytesIO()
            fmt = image.format or 'JPEG'
            image.save(output, format=fmt, optimize=True)
            output.seek(0)
            
            # Upload thumbnail
            thumb_key = f"thumbnails/{key}"
            s3.put_object(
                Bucket=THUMB_BUCKET,
                Key=thumb_key,
                Body=output.getvalue(),
                ContentType=response['ContentType'],
                Metadata={
                    'original-bucket': bucket,
                    'original-key': key,
                    'original-size': str(response['ContentLength'])
                }
            )
            
            logger.info(f"Thumbnail created: s3://{THUMB_BUCKET}/{thumb_key}")
            processed.append({'key': key, 'thumbnail': thumb_key})
            
        except Exception as e:
            logger.error(f"Error processing {key}: {str(e)}", exc_info=True)
            errors.append({'key': key, 'error': str(e)})
    
    return {
        'processed': processed,
        'errors': errors
    }
PYTHON

# Create requirements.txt
cat > lab-lambda/requirements.txt <<'EOF'
Pillow==10.2.0
EOF

echo "Lambda code created"
```

## Step 3: Package Lambda with Dependencies

```bash
cd lab-lambda

# Install dependencies to package directory
pip install -r requirements.txt -t package/ --quiet

# Copy function code
cp src/thumbnail.py package/

# Create deployment zip
cd package
zip -r ../thumbnail-lambda.zip . -q
cd ..

echo "Package size: $(du -sh thumbnail-lambda.zip | cut -f1)"
cd ..
```

## Step 4: Create IAM Role for Lambda

```bash
# Create execution role
aws iam create-role \
  --role-name lab-thumbnail-lambda-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach basic Lambda execution policy
aws iam attach-role-policy \
  --role-name lab-thumbnail-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Add S3 permissions
aws iam put-role-policy \
  --role-name lab-thumbnail-lambda-role \
  --policy-name S3Access \
  --policy-document "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [
      {
        \"Effect\": \"Allow\",
        \"Action\": [\"s3:GetObject\"],
        \"Resource\": \"arn:aws:s3:::${UPLOAD_BUCKET}/*\"
      },
      {
        \"Effect\": \"Allow\",
        \"Action\": [\"s3:PutObject\"],
        \"Resource\": \"arn:aws:s3:::${THUMB_BUCKET}/*\"
      }
    ]
  }"

ROLE_ARN=$(aws iam get-role \
  --role-name lab-thumbnail-lambda-role \
  --query 'Role.Arn' --output text)

echo "Role ARN: $ROLE_ARN"
sleep 10  # IAM propagation
```

## Step 5: Deploy Lambda Function

```bash
# Create Lambda function
FUNCTION_ARN=$(aws lambda create-function \
  --function-name lab-thumbnail-processor \
  --runtime python3.12 \
  --role $ROLE_ARN \
  --handler thumbnail.handler \
  --zip-file fileb://lab-lambda/thumbnail-lambda.zip \
  --timeout 30 \
  --memory-size 512 \
  --environment Variables="{THUMB_BUCKET=${THUMB_BUCKET}}" \
  --query 'FunctionArn' --output text)

echo "Function ARN: $FUNCTION_ARN"

# Wait for function to be active
aws lambda wait function-active --function-name lab-thumbnail-processor
echo "Lambda function is active"
```

## Step 6: Configure S3 Trigger

```bash
# Grant S3 permission to invoke Lambda
aws lambda add-permission \
  --function-name lab-thumbnail-processor \
  --statement-id s3-trigger \
  --action lambda:InvokeFunction \
  --principal s3.amazonaws.com \
  --source-arn arn:aws:s3:::${UPLOAD_BUCKET} \
  --source-account $ACCOUNT_ID

# Configure S3 event notification
aws s3api put-bucket-notification-configuration \
  --bucket $UPLOAD_BUCKET \
  --notification-configuration "{
    \"LambdaFunctionConfigurations\": [{
      \"LambdaFunctionArn\": \"${FUNCTION_ARN}\",
      \"Events\": [\"s3:ObjectCreated:*\"],
      \"Filter\": {
        \"Key\": {
          \"FilterRules\": [
            {\"Name\": \"suffix\", \"Value\": \".jpg\"},
            {\"Name\": \"prefix\", \"Value\": \"uploads/\"}
          ]
        }
      }
    }]
  }"

echo "S3 trigger configured"
```

## Step 7: Test the Pipeline

```bash
# Download a test image
curl -s -o /tmp/test-image.jpg \
  "https://via.placeholder.com/800x600.jpg"

# Upload to S3
aws s3 cp /tmp/test-image.jpg \
  s3://${UPLOAD_BUCKET}/uploads/test-image.jpg

echo "Image uploaded. Waiting for processing..."
sleep 5

# Check if thumbnail was created
aws s3 ls s3://${THUMB_BUCKET}/thumbnails/uploads/

# Check Lambda logs
aws logs tail /aws/lambda/lab-thumbnail-processor --since 5m

# Download and verify thumbnail
aws s3 cp \
  s3://${THUMB_BUCKET}/thumbnails/uploads/test-image.jpg \
  /tmp/thumbnail.jpg

echo "Thumbnail size: $(du -sh /tmp/thumbnail.jpg | cut -f1)"
echo "Original size: $(du -sh /tmp/test-image.jpg | cut -f1)"
```

## Step 8: Add API Gateway for Pre-signed URLs

```bash
# Create Lambda for API
cat > /tmp/api_handler.py <<'PYTHON'
import boto3
import json
import os

s3 = boto3.client('s3')
UPLOAD_BUCKET = os.environ['UPLOAD_BUCKET']
THUMB_BUCKET = os.environ['THUMB_BUCKET']

def handler(event, context):
    path = event.get('rawPath', '/')
    method = event.get('requestContext', {}).get('http', {}).get('method', 'GET')
    
    if path == '/upload-url' and method == 'POST':
        # Generate pre-signed upload URL
        body = json.loads(event.get('body', '{}'))
        filename = body.get('filename', 'image.jpg')
        
        url = s3.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': UPLOAD_BUCKET,
                'Key': f'uploads/{filename}',
                'ContentType': 'image/jpeg'
            },
            ExpiresIn=300
        )
        return {
            'statusCode': 200,
            'body': json.dumps({'uploadUrl': url, 'key': f'uploads/{filename}'})
        }
    
    elif path.startswith('/thumbnail/') and method == 'GET':
        # Generate pre-signed download URL for thumbnail
        key = path.replace('/thumbnail/', 'thumbnails/uploads/')
        
        try:
            s3.head_object(Bucket=THUMB_BUCKET, Key=key)
            url = s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': THUMB_BUCKET, 'Key': key},
                ExpiresIn=3600
            )
            return {
                'statusCode': 200,
                'body': json.dumps({'thumbnailUrl': url})
            }
        except s3.exceptions.ClientError:
            return {'statusCode': 404, 'body': json.dumps({'error': 'Thumbnail not found'})}
    
    return {'statusCode': 404, 'body': json.dumps({'error': 'Not found'})}
PYTHON

zip /tmp/api-lambda.zip /tmp/api_handler.py

# Add S3 read permission to role
aws iam put-role-policy \
  --role-name lab-thumbnail-lambda-role \
  --policy-name S3PresignAccess \
  --policy-document "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [{
      \"Effect\": \"Allow\",
      \"Action\": [\"s3:GetObject\", \"s3:PutObject\", \"s3:HeadObject\"],
      \"Resource\": [
        \"arn:aws:s3:::${UPLOAD_BUCKET}/*\",
        \"arn:aws:s3:::${THUMB_BUCKET}/*\"
      ]
    }]
  }"

# Create API Lambda
API_ARN=$(aws lambda create-function \
  --function-name lab-thumbnail-api \
  --runtime python3.12 \
  --role $ROLE_ARN \
  --handler api_handler.handler \
  --zip-file fileb:///tmp/api-lambda.zip \
  --timeout 10 \
  --memory-size 256 \
  --environment Variables="{UPLOAD_BUCKET=${UPLOAD_BUCKET},THUMB_BUCKET=${THUMB_BUCKET}}" \
  --query 'FunctionArn' --output text)

# Create HTTP API
API_ID=$(aws apigatewayv2 create-api \
  --name lab-thumbnail-api \
  --protocol-type HTTP \
  --query 'ApiId' --output text)

# Create Lambda integration
INTEGRATION_ID=$(aws apigatewayv2 create-integration \
  --api-id $API_ID \
  --integration-type AWS_PROXY \
  --integration-uri $API_ARN \
  --payload-format-version 2.0 \
  --query 'IntegrationId' --output text)

# Create routes
aws apigatewayv2 create-route \
  --api-id $API_ID \
  --route-key "POST /upload-url" \
  --target integrations/$INTEGRATION_ID

aws apigatewayv2 create-route \
  --api-id $API_ID \
  --route-key "GET /thumbnail/{key}" \
  --target integrations/$INTEGRATION_ID

# Deploy
aws apigatewayv2 create-stage \
  --api-id $API_ID \
  --stage-name prod \
  --auto-deploy

# Grant API Gateway permission to invoke Lambda
aws lambda add-permission \
  --function-name lab-thumbnail-api \
  --statement-id apigw-invoke \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:${REGION}:${ACCOUNT_ID}:${API_ID}/*/*"

API_URL="https://${API_ID}.execute-api.${REGION}.amazonaws.com/prod"
echo "API URL: $API_URL"

# Test API
curl -s -X POST "${API_URL}/upload-url" \
  -H "Content-Type: application/json" \
  -d '{"filename": "my-photo.jpg"}' | python3 -m json.tool
```

## Step 9: Cleanup

```bash
# Delete Lambda functions
aws lambda delete-function --function-name lab-thumbnail-processor
aws lambda delete-function --function-name lab-thumbnail-api

# Delete API Gateway
aws apigatewayv2 delete-api --api-id $API_ID

# Empty and delete S3 buckets
aws s3 rm s3://${UPLOAD_BUCKET} --recursive
aws s3 rm s3://${THUMB_BUCKET} --recursive
aws s3api delete-bucket --bucket $UPLOAD_BUCKET
aws s3api delete-bucket --bucket $THUMB_BUCKET

# Delete IAM role
aws iam delete-role-policy \
  --role-name lab-thumbnail-lambda-role \
  --policy-name S3Access
aws iam delete-role-policy \
  --role-name lab-thumbnail-lambda-role \
  --policy-name S3PresignAccess
aws iam detach-role-policy \
  --role-name lab-thumbnail-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam delete-role --role-name lab-thumbnail-lambda-role

# Clean up local files
rm -rf lab-lambda /tmp/test-image.jpg /tmp/thumbnail.jpg \
       /tmp/api_handler.py /tmp/api-lambda.zip

echo "Cleanup complete!"
```

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Lambda not triggered | S3 notification misconfigured | Check bucket notification config |
| Permission denied | Lambda role missing S3 permissions | Add s3:GetObject/PutObject |
| Pillow import error | Missing in deployment package | Ensure pip install to package/ dir |
| Thumbnail not created | Image format not supported | Check Lambda logs for error |
| API returns 500 | Lambda error | Check CloudWatch Logs |

---

## What You Learned

✅ Create and configure S3 buckets with security settings
✅ Package Lambda with external dependencies
✅ Configure S3 event triggers for Lambda
✅ Use IAM roles with least-privilege permissions
✅ Build a serverless API with API Gateway HTTP API
✅ Generate pre-signed URLs for secure S3 access
✅ Debug Lambda using CloudWatch Logs
