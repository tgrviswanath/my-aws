# Steps — Project 4.4 Event-driven Image Processing

## Phase 1 — Build Lambda Layer (Pillow)

```bash
# Pillow must be packaged for Lambda's Amazon Linux environment
mkdir -p layer/python

# Option A: Use Docker (recommended — matches Lambda runtime)
docker run --rm \
  -v $(pwd)/layer:/layer \
  public.ecr.aws/lambda/python:3.11 \
  pip install Pillow -t /layer/python

# Zip the layer
cd layer && zip -r ../pillow-layer.zip python/ && cd ..

# Option B: Use pip with platform flag
pip install Pillow \
  --platform mlinux_2_x86_64 \
  --target layer/python \
  --implementation cp \
  --python-version 3.11 \
  --only-binary=:all:
```

---

## Phase 2 — Deploy

```bash
cd terraform
terraform init
terraform apply -auto-approve

SOURCE_BUCKET=$(terraform output -raw source_bucket)
OUTPUT_BUCKET=$(terraform output -raw output_bucket)
echo "Upload to: $SOURCE_BUCKET"
```

---

## Phase 3 — Test

```bash
# Download a test image
curl -o test.jpg https://picsum.photos/2000/1500

# Upload to source bucket — this triggers Lambda automatically
aws s3 cp test.jpg s3://$SOURCE_BUCKET/photos/test.jpg

# Wait ~5 seconds for Lambda to process
sleep 5

# Check output bucket for processed images
aws s3 ls s3://$OUTPUT_BUCKET/processed/ --recursive

# Download and verify thumbnail
aws s3 cp s3://$OUTPUT_BUCKET/processed/thumbnail/photos/test.jpg thumbnail.jpg
# Open thumbnail.jpg — should be 150x150
```

---

## Phase 4 — View Lambda Logs

```bash
LAMBDA_NAME=$(terraform output -raw lambda_name)

aws logs tail /aws/lambda/$LAMBDA_NAME --follow &

# Upload another image to see live logs
aws s3 cp test.jpg s3://$SOURCE_BUCKET/photos/test2.jpg
```

---

## Phase 5 — Check DynamoDB Metadata

```bash
TABLE=$(terraform output -raw table_name)
aws dynamodb scan --table-name $TABLE | python3 -m json.tool
```

---

## Screenshots to Take
- [ ] S3 source bucket with uploaded image
- [ ] Lambda triggered automatically (CloudWatch logs)
- [ ] Output bucket with thumbnail/ and medium/ folders
- [ ] Original vs thumbnail size comparison
- [ ] DynamoDB metadata record
- [ ] Lambda execution duration and memory usage
