# Project 4.4 — Event-Driven Image Processing
# Complete Production-Oriented Implementation Guide

---

## 1. Project Overview

**Project Title:** Event-Driven Image Processing Pipeline with S3 + Lambda + Pillow

**Business / Problem Statement:**
Every web application that accepts image uploads needs to generate thumbnails and optimized versions — for product pages, profile pictures, and social media previews. Doing this synchronously in the request slows down the user experience. With an event-driven approach, users upload images to S3, and Lambda automatically processes them in the background: generating thumbnails, medium-size versions, and storing metadata to DynamoDB. Instagram, Cloudinary, and AWS Amplify Storage all use this exact pattern.

**Learning Objectives:**
- Understand S3 Event Notifications and how they trigger Lambda
- Package Python dependencies (Pillow) as a Lambda Layer
- Process binary data (images) in Lambda using in-memory IO (no disk)
- Write metadata to DynamoDB from a triggered Lambda
- Understand the "recursive trigger" problem and how to avoid it
- Learn how to monitor event-driven pipelines using CloudWatch Logs

---

## 2. Architecture & Concepts

**Core AWS Services:**

| Service | Role |
|---------|------|
| S3 (source bucket) | Receives uploaded images — triggers Lambda |
| S3 Event Notification | Fires on `s3:ObjectCreated:*` event |
| Lambda + Pillow Layer | Downloads image, resizes, uploads outputs |
| S3 (output bucket) | Stores processed images (thumbnail + medium) |
| DynamoDB | Stores image metadata (original size, outputs, timestamp) |
| CloudWatch Logs | Lambda execution logs |

**Service Interaction Flow:**
```
User uploads image to S3 source bucket
         │
         │ S3 ObjectCreated event fires automatically
         ▼
Lambda: handson-img-proc-processor
         │
         ├── Download original from source bucket
         ├── Open with Pillow (in-memory, no disk)
         ├── Resize → thumbnail (150×150)
         ├── Resize → medium (800×600)
         ├── Upload both to output bucket
         └── Write metadata record to DynamoDB
```

**High-Level Architecture:**
```
┌───────────────────────────────────────────────────────────────┐
│                         AWS Cloud                              │
│                                                                │
│  User ──upload──► S3: source bucket                           │
│                       │ ObjectCreated event                    │
│                       ▼                                        │
│                 Lambda (Python 3.11)                           │
│                 + Pillow Layer                                  │
│                       │                                        │
│           ┌───────────┼───────────────┐                       │
│           ▼           ▼               ▼                        │
│  S3: output bucket  DynamoDB       CloudWatch                  │
│  ├── processed/     metadata       Logs                        │
│  │   thumbnail/     (image_key,                                │
│  └── processed/      sizes, etc.)                              │
│      medium/                                                   │
└───────────────────────────────────────────────────────────────┘
```

**Processing Results:**

| Input | Output Size | Output Path |
|-------|-------------|-------------|
| Any image (JPEG/PNG/WebP) | 150×150 px | `processed/thumbnail/{original_key}` |
| Any image (JPEG/PNG/WebP) | max 800×600 px | `processed/medium/{original_key}` |

**Best Practices Followed:**
- Source and output buckets are **separate** (prevents recursive trigger loop)
- Pillow packaged as Lambda Layer (keeps deployment package small, reusable)
- RGBA/palette images converted to RGB before JPEG output
- `image.thumbnail()` preserves aspect ratio — doesn't distort
- Error handling per-record (one bad image doesn't fail the batch)
- DynamoDB metadata for observability and auditing

---

## 3. Prerequisites

**Additional Requirements for this project:**

| Requirement | Why |
|-------------|-----|
| Docker (recommended) | Build Pillow layer compatible with Lambda's Amazon Linux environment |
| `pip` with `--platform` flag | Alternative to Docker for building layers |
| A test image file | For upload testing |

**⚠️ Critical Warning — Pillow must be built for Linux:**
Pillow has C extensions. If you `pip install Pillow` on Windows/Mac and zip it, it will fail on Lambda (Amazon Linux). You must build it for the Lambda runtime environment.

**Pillow Layer Build (choose one method):**

**Method 1 — Docker (recommended):**
```bash
mkdir -p layer/python
docker run --rm \
  -v $(pwd)/layer:/layer \
  public.ecr.aws/lambda/python:3.11 \
  pip install Pillow -t /layer/python
cd layer && zip -r ../pillow-layer.zip python/ && cd ..
```

**Method 2 — pip with platform flag (no Docker needed):**
```bash
mkdir -p layer/python
pip install Pillow \
  --platform manylinux2014_x86_64 \
  --target layer/python \
  --implementation cp \
  --python-version 3.11 \
  --only-binary=:all:
cd layer && zip -r ../pillow-layer.zip python/ && cd ..
```

---

## 4. Project Folder Structure

```
project_4.4_image_processing/
│
├── README.md               ← Architecture, Pillow layer setup, lessons learned
├── GUIDE.md                ← This file
├── steps.md                ← Build layer, deploy, upload test image, verify
├── verify.md               ← Verify trigger, output dimensions, DynamoDB metadata
├── cost_estimate.md        ← $0 (all free tier)
│
├── src/
│   └── handler.py          ← S3-triggered Lambda — downloads, resizes, uploads
│
├── docs/
│   └── architecture.md     ← Event flow, recursive trigger warning
│
└── terraform/
    └── main.tf             ← S3 buckets, Lambda, Layer, Event Notification, DynamoDB
```

---

## 5. Project Input & Output

**INPUT:**
```
Any image file uploaded to S3 source bucket:
s3://handson-img-proc-source/photos/vacation.jpg
s3://handson-img-proc-source/profile/avatar.png
s3://handson-img-proc-source/products/item-001.webp

Supported formats: JPEG (.jpg, .jpeg), PNG (.png), WebP (.webp), GIF (.gif)
```

**OUTPUT — S3:**
```
Uploaded: s3://handson-img-proc-source/photos/vacation.jpg (3000×2000, 4MB)

Generated:
s3://handson-img-proc-output/processed/thumbnail/photos/vacation.jpg  (150×150, ~8KB)
s3://handson-img-proc-output/processed/medium/photos/vacation.jpg     (800×600, ~120KB)
```

**OUTPUT — DynamoDB:**
```json
{
  "image_key":       "photos/vacation.jpg",
  "source_bucket":   "handson-img-proc-source",
  "output_bucket":   "handson-img-proc-output",
  "original_size":   "3000x2000",
  "file_size_bytes": 4194304,
  "format":          "JPEG",
  "outputs": {
    "thumbnail": {"key": "processed/thumbnail/photos/vacation.jpg", "dimensions": "150x150"},
    "medium":    {"key": "processed/medium/photos/vacation.jpg",    "dimensions": "800x533"}
  },
  "processed_at": "2024-01-15T12:00:01.234Z"
}
```

**OUTPUT — CloudWatch Logs:**
```
Processing: s3://handson-img-proc-source/photos/vacation.jpg (4194304 bytes)
  Created thumbnail: processed/thumbnail/photos/vacation.jpg (150, 150)
  Created medium: processed/medium/photos/vacation.jpg (800, 533)
Done: photos/vacation.jpg → ['thumbnail', 'medium']
```

---

## 6. Hands-on Implementation

### METHOD A — AWS Management Console (UI Method)

---

#### Step 1 — Create Source and Output S3 Buckets

**Prerequisites Check:**
- ✅ Required permissions: `s3:CreateBucket`, `s3:PutBucketNotification`
- ✅ Services enabled: Amazon S3
- ✅ Region: us-east-1 selected

**Step 1.1: Navigate and Verify**
1. Go to [S3 Console](https://console.aws.amazon.com/s3)
2. **Expected View:** S3 dashboard with "Create bucket" button
3. Click **Create bucket**

**Step 1.2: Create Source Bucket**

**Decision Point 1:** Bucket Naming Strategy

| Option | Use Case | For This Project |
|--------|----------|-----------------|
| Simple name | Risk of conflicts | ❌ Names are globally unique |
| Name with account ID suffix | Guaranteed uniqueness | ✅ Use this |

| Field | Value | Explanation |
|-------|-------|-------------|
| Bucket name | `handson-img-proc-source-[ACCOUNT_ID]` | Replace [ACCOUNT_ID] |
| Region | us-east-1 | Match Lambda region |
| Block all public access | ✅ All checked | Images are private |
| Versioning | Disabled | Not needed for processing |
| Encryption | SSE-S3 | Default, free |

Click **Create bucket**

**Step 1.3: Create Output Bucket**

Repeat — create a **second** bucket:

| Field | Value |
|-------|-------|
| Bucket name | `handson-img-proc-output-[ACCOUNT_ID]` |
| All other settings | Same as source |

**⚠️ Critical:** Source and output buckets MUST be different. If they're the same:
- Lambda uploads processed image → triggers another Lambda → triggers another → infinite loop!

**📸 Screenshot:** S3 bucket list showing both source and output buckets

---

#### Step 2 — Create Lambda Layer (Pillow)

**Prerequisites Check:**
- ✅ Required permissions: `lambda:PublishLayerVersion`
- ✅ `pillow-layer.zip` built using Docker or pip (see Prerequisites section)

**Step 2.1: Navigate and Verify**
1. Go to [Lambda Console](https://console.aws.amazon.com/lambda)
2. Click **Layers** in left sidebar
3. Click **Create layer**

**Step 2.2: Make Selections**

**Decision Point 1:** Layer Upload Method

| Option | Use Case | For This Project |
|--------|----------|-----------------|
| Upload .zip file | File < 50MB | ✅ Use this (Pillow is ~15MB) |
| Upload from S3 | File > 50MB | ❌ Not needed |

**Step 2.3: Configure Layer**

| Field | Value | Explanation |
|-------|-------|-------------|
| Name | `pillow-layer` | Descriptive |
| Description | Pillow image library for Python 3.11 | |
| Upload | Select `pillow-layer.zip` | Built in Prerequisites |
| Compatible runtimes | ✅ Python 3.11 | Must match Lambda runtime |
| Compatible architectures | x86_64 | Must match Lambda arch |

Click **Create**

**📸 Screenshot:** Lambda Layers page showing `pillow-layer` with Python 3.11 compatibility

**Step 2.4: Validate**

**Expected Outcome:** Layer appears with Version 1

**Troubleshooting:**
- Upload fails (>50MB): Upload to S3 first, then reference the S3 URL
- Lambda gets `ModuleNotFoundError: No module named 'PIL'`: Layer was built for wrong platform — rebuild with Docker

---

#### Step 3 — Create Lambda Function with Pillow Layer

**Step 3.1: Create Function**
1. Lambda → **Create function** → **Author from scratch**

| Field | Value |
|-------|-------|
| Function name | `handson-img-proc-processor` |
| Runtime | Python 3.11 |
| Architecture | x86_64 |
| Execution role | `handson-img-proc-lambda-role` |

Click **Create function**

**Step 3.2: Paste Code**
1. Paste entire content of `src/handler.py`
2. Click **Deploy**

**Step 3.3: Add Pillow Layer**
1. Scroll down to **Layers** section
2. Click **Add a layer**
3. Select **Custom layers**
4. Choose `pillow-layer`, Version 1
5. Click **Add**

**📸 Screenshot:** Lambda function showing Pillow layer attached in Layers section

**Step 3.4: Configure Settings**

Go to **Configuration** tab:

**Memory (important!):**

| Memory | Processing Speed | Cost |
|--------|----------------|------|
| 128 MB | Slow (~5-8s) | Cheapest |
| 512 MB | Medium (~2s) | ✅ Good balance |
| 1024 MB | Fast (~1s) | Higher cost |

Set Memory: **512 MB** (Lambda CPU scales with memory — more memory = faster image processing)

Set Timeout: **60 seconds** (image processing can take a few seconds for large images)

**Step 3.5: Set Environment Variables**

| Key | Value |
|-----|-------|
| `OUTPUT_BUCKET` | `handson-img-proc-output-[ACCOUNT_ID]` |
| `TABLE_NAME` | `handson-img-proc-metadata` |

---

#### Step 4 — Create DynamoDB Metadata Table

1. DynamoDB → Create table

| Field | Value |
|-------|-------|
| Table name | `handson-img-proc-metadata` |
| Partition key | `image_key` (String) |
| Billing mode | On-demand |

---

#### Step 5 — Configure S3 Event Notification

**Prerequisites Check:**
- ✅ Required permissions: `s3:PutBucketNotification`, `lambda:AddPermission`
- ✅ Lambda function deployed
- ✅ Source bucket created

**Step 5.1: Navigate**
1. S3 → Click `handson-img-proc-source-[ACCOUNT_ID]`
2. **Properties** tab
3. Scroll to **Event notifications** → Click **Create event notification**

**Step 5.2: Make Selections**

**Decision Point 1:** Event Type

| Event | When triggered | For This Project |
|-------|---------------|-----------------|
| s3:ObjectCreated:Put | On direct PUT uploads | ✅ Select |
| s3:ObjectCreated:Post | On multipart uploads | ✅ Select |
| s3:ObjectCreated:* | All create events | ✅ Use this (covers all) |

**Step 5.3: Configure**

| Field | Value | Explanation |
|-------|-------|-------------|
| Event name | `trigger-image-processor` | Descriptive |
| Prefix | *(leave empty)* | Trigger on all upload paths |
| Suffix | `.jpg` | First notification — JPEG files only |
| Event types | ✅ `s3:ObjectCreated:*` | All creation events |
| Destination | **Lambda function** | |
| Lambda function | `handson-img-proc-processor` | Select from dropdown |

Click **Save changes**

> **Two notifications needed to match Terraform:** Terraform creates two separate event notifications — one for `.jpg` suffix and one for `.png` suffix. Repeat the above to create a second notification with Suffix `.png` pointing to the same Lambda. The Lambda handler also handles `.webp` and `.gif` internally — add more notifications if needed.

**Alternatively (simpler):** Set Suffix to *(leave empty)* — this triggers on ALL uploads. The Lambda handler in `src/handler.py` already filters by extension internally:
```python
if ext not in ("jpg", "jpeg", "png", "webp", "gif"):
    print(f"Skipping non-image file: {object_key}")
    return
```
This is safe — non-image files are silently skipped. However it differs from the Terraform configuration which pre-filters at the S3 level.

**Step 5.4: Validate**

**Expected Outcome:** Event notification appears in Properties tab

**📸 Screenshot:** S3 bucket Properties showing Event notification → `handson-img-proc-processor` Lambda

**What AWS does automatically:** AWS adds a `lambda:InvokeFunction` permission to the Lambda function allowing the S3 bucket to invoke it. You can verify this in Lambda → Configuration → Permissions → Resource-based policy.

**Step 5.5: Test the Trigger**

```bash
# Download a test image
curl -o test.jpg "https://picsum.photos/2000/1500"

# Upload to source bucket — Lambda fires automatically
aws s3 cp test.jpg s3://handson-img-proc-source-[ACCOUNT_ID]/photos/test.jpg

# Wait ~5 seconds, then check output bucket
sleep 8
aws s3 ls s3://handson-img-proc-output-[ACCOUNT_ID]/processed/ --recursive
# Expected: thumbnail/photos/test.jpg and medium/photos/test.jpg
```

**📸 Screenshot:** Output bucket showing `processed/thumbnail/` and `processed/medium/` folders after upload

---

### METHOD B — AWS CLI Method

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
SOURCE_BUCKET="handson-img-proc-source-$ACCOUNT_ID"
OUTPUT_BUCKET="handson-img-proc-output-$ACCOUNT_ID"
TABLE_NAME="handson-img-proc-metadata"
LAMBDA_NAME="handson-img-proc-processor"

# ── 1. Create S3 Buckets ──────────────────────────────────────────────────────
for BUCKET in $SOURCE_BUCKET $OUTPUT_BUCKET; do
  aws s3api create-bucket \
    --bucket $BUCKET \
    --region us-east-1
  aws s3api put-public-access-block \
    --bucket $BUCKET \
    --public-access-block-configuration \
      BlockPublicAcls=true,IgnorePublicAcls=true,\
BlockPublicPolicy=true,RestrictPublicBuckets=true
  echo "✅ Bucket created: $BUCKET"
done

# ── 2. Create DynamoDB Table ──────────────────────────────────────────────────
aws dynamodb create-table \
  --table-name $TABLE_NAME \
  --attribute-definitions AttributeName=image_key,AttributeType=S \
  --key-schema AttributeName=image_key,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

aws dynamodb wait table-exists --table-name $TABLE_NAME
echo "✅ DynamoDB table created"

# ── 3. Publish Pillow Lambda Layer ────────────────────────────────────────────
# (build pillow-layer.zip first — see Prerequisites section)
LAYER_ARN=$(aws lambda publish-layer-version \
  --layer-name pillow-layer \
  --description "Pillow for Python 3.11 Lambda" \
  --zip-file fileb://pillow-layer.zip \
  --compatible-runtimes python3.11 \
  --compatible-architectures x86_64 \
  --query LayerVersionArn --output text)

echo "✅ Pillow Layer ARN: $LAYER_ARN"

# ── 4. Deploy Lambda ──────────────────────────────────────────────────────────
ROLE_ARN=$(aws iam get-role --role-name handson-lambda-exec-role \
  --query Role.Arn --output text)

cd src && zip ../image_handler.zip handler.py && cd ..

aws lambda create-function \
  --function-name $LAMBDA_NAME \
  --runtime python3.11 \
  --role $ROLE_ARN \
  --handler handler.handler \
  --zip-file fileb://image_handler.zip \
  --timeout 60 \
  --memory-size 512 \
  --layers $LAYER_ARN \
  --environment Variables="{OUTPUT_BUCKET=$OUTPUT_BUCKET,TABLE_NAME=$TABLE_NAME}"

aws lambda wait function-active --function-name $LAMBDA_NAME
LAMBDA_ARN=$(aws lambda get-function --function-name $LAMBDA_NAME \
  --query Configuration.FunctionArn --output text)
echo "✅ Lambda deployed"

# ── 5. Add permission for S3 to invoke Lambda ─────────────────────────────────
aws lambda add-permission \
  --function-name $LAMBDA_NAME \
  --statement-id s3-invoke \
  --action lambda:InvokeFunction \
  --principal s3.amazonaws.com \
  --source-arn "arn:aws:s3:::$SOURCE_BUCKET"

# ── 6. Configure S3 Event Notification ───────────────────────────────────────
aws s3api put-bucket-notification-configuration \
  --bucket $SOURCE_BUCKET \
  --notification-configuration "{
    \"LambdaFunctionConfigurations\": [{
      \"LambdaFunctionArn\": \"$LAMBDA_ARN\",
      \"Events\": [\"s3:ObjectCreated:*\"]
    }]
  }"

echo "✅ S3 event notification configured"
echo "✅ Upload images to: s3://$SOURCE_BUCKET"

# ── 7. Test the pipeline ──────────────────────────────────────────────────────
curl -o test.jpg "https://picsum.photos/2000/1500"
aws s3 cp test.jpg s3://$SOURCE_BUCKET/photos/test.jpg
echo "Uploaded — waiting 8 seconds for Lambda to process..."
sleep 8
aws s3 ls s3://$OUTPUT_BUCKET/processed/ --recursive
```

---

## 7. Code Deep Dive

**`src/handler.py` — Key Sections:**

```python
# In-memory image processing — no disk I/O needed
response = s3.get_object(Bucket=source_bucket, Key=object_key)
image_data = response["Body"].read()          # Read image bytes into memory

img = Image.open(io.BytesIO(image_data))      # Pillow reads from BytesIO buffer
# Lambda /tmp has only 512MB — for large images, in-memory is safer than disk writes
```

```python
# RGBA to RGB conversion — required for JPEG output
if img.mode in ("RGBA", "P"):
    img = img.convert("RGB")
# JPEG doesn't support alpha channels (transparency)
# PNG files often have RGBA mode (R,G,B,Alpha)
# Without conversion: "OSError: cannot write mode RGBA as JPEG"
```

```python
# Thumbnail vs resize — important distinction
resized.thumbnail(dimensions, Image.LANCZOS)
# thumbnail() PRESERVES aspect ratio and fits within the given size
# So (150,150) on a 2000x1500 image → 150x113 (not exactly 150x150)
# Use Image.resize() if you want exact dimensions (but it distorts)
# Image.LANCZOS = best quality downscaling filter (formerly Image.ANTIALIAS)
```

```python
# Upload processed image with metadata
s3.put_object(
    Bucket=OUTPUT_BUCKET,
    Key=output_key,
    Body=buffer,
    ContentType=f"image/{img_format.lower()}",    # Sets MIME type for browsers
    Metadata={
        "original-key": object_key,
        "size": size_name,
        "dimensions": f"{resized.size[0]}x{resized.size[1]}",
    },
)
# S3 object metadata — viewable in console, passed in HTTP response headers
```

**S3 Event Notification Payload Structure:**
```json
{
  "Records": [{
    "s3": {
      "bucket": {"name": "handson-img-proc-source-123456789"},
      "object": {
        "key": "photos/vacation.jpg",   ← URL-encoded! Use urllib.parse.unquote_plus()
        "size": 4194304
      }
    }
  }]
}
```

**Common Mistakes:**

| Mistake | Fix |
|---------|-----|
| Source = output bucket | Use separate buckets — different names! |
| `pip install Pillow` on Mac/Windows | Build for `manylinux2014_x86_64` or use Docker |
| `Image.ANTIALIAS` | Use `Image.LANCZOS` (renamed in Pillow 9.1) |
| Not URL-decoding S3 key | Use `urllib.parse.unquote_plus(key)` — spaces become `+` |
| No RGB conversion | Convert RGBA/P mode before saving JPEG |

---

## 8. Verification & Validation

```bash
SOURCE_BUCKET="handson-img-proc-source-$(aws sts get-caller-identity --query Account --output text)"
OUTPUT_BUCKET="handson-img-proc-output-$(aws sts get-caller-identity --query Account --output text)"
TABLE_NAME="handson-img-proc-metadata"
LAMBDA_NAME="handson-img-proc-processor"

# 1. Check S3 event notification is configured
aws s3api get-bucket-notification-configuration \
  --bucket $SOURCE_BUCKET \
  --query "LambdaFunctionConfigurations[*].{Events:Events,Lambda:LambdaFunctionArn}"
# Expected: Events=["s3:ObjectCreated:*"], Lambda ARN pointing to handson-img-proc-processor

# 2. Check Lambda has Pillow layer
aws lambda get-function \
  --function-name $LAMBDA_NAME \
  --query "Configuration.Layers[*].Arn"
# Expected: pillow-layer ARN listed

# 3. Upload test image and trigger Lambda
curl -o /tmp/test.jpg "https://picsum.photos/2000/1500"
aws s3 cp /tmp/test.jpg s3://$SOURCE_BUCKET/photos/test.jpg
echo "Uploaded — waiting for Lambda..."
sleep 10

# 4. Check output bucket
aws s3 ls s3://$OUTPUT_BUCKET/processed/ --recursive
# Expected:
# processed/thumbnail/photos/test.jpg
# processed/medium/photos/test.jpg

# 5. Download and verify thumbnail dimensions
aws s3 cp s3://$OUTPUT_BUCKET/processed/thumbnail/photos/test.jpg /tmp/thumb.jpg
python3 -c "
from PIL import Image
img = Image.open('/tmp/thumb.jpg')
print(f'Thumbnail: {img.size}')
assert img.size[0] <= 150 and img.size[1] <= 150, 'Too large!'
print('✅ Thumbnail size correct')
"

# 6. Verify DynamoDB metadata
aws dynamodb scan \
  --table-name $TABLE_NAME \
  --query "Items[*].{key:image_key.S,size:original_size.S,status:processed_at.S}"

# 7. Check Lambda logs for processing details
aws logs tail /aws/lambda/$LAMBDA_NAME --since 5m
# Expected: "Processing:", "Created thumbnail:", "Created medium:", "Done:"
```

---

## 9. Observations & Learning Notes

1. **S3 eventual consistency:** S3 events are delivered at-least-once — Lambda could be invoked multiple times for the same upload in rare cases. Your handler should be idempotent (safe to run twice).

2. **Lambda memory = CPU:** At 512MB, image processing takes ~1-2s. At 128MB, it takes ~6-8s. Lambda CPU allocation scales with memory size. For image processing, more memory = significantly faster.

3. **Lambda layer caching:** The Pillow layer is cached after first use — no download overhead per invocation. Layers are mounted at `/opt/python/` in Lambda's filesystem.

4. **S3 event delivery timing:** The event reaches Lambda within 1-5 seconds of upload. For production SLAs, assume up to 30 seconds for event delivery in worst case.

5. **Avoid recursive trigger — the golden rule:**
   - Same bucket source + output → infinite loop → Lambda gets throttled
   - DynamoDB usage spike → $100+ bill
   - Solution: Always use different buckets, or use prefix/suffix filters

6. **JPEG quality=85:** The `quality=85` parameter in `resized.save()` is a balance. Quality 100 = largest file, quality 60 = smallest but visible artifacts. 85 is the industry standard.

---

## 10. Screenshots Guidance

| When | What to Capture |
|------|----------------|
| Before | Empty S3 source and output buckets |
| After Step 2 | Lambda Layers showing `pillow-layer` with Python 3.11 compat |
| After Step 3 | Lambda function with Pillow layer attached + memory=512MB |
| After Step 4 | DynamoDB table `handson-img-proc-metadata` Active |
| After Step 5 | S3 source bucket Properties → Event notifications → Lambda |
| Testing | Terminal showing `aws s3 cp` upload command |
| After upload | Output bucket showing `processed/thumbnail/` and `processed/medium/` folders |
| Testing | Thumbnail image (150px) vs original (2000px) comparison |
| After | DynamoDB item with full metadata JSON |
| After | Lambda CloudWatch logs showing processing steps |

---

## 11. Cleanup Steps

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# 1. Remove S3 objects first (buckets must be empty to delete)
aws s3 rm s3://handson-img-proc-source-$ACCOUNT_ID --recursive
aws s3 rm s3://handson-img-proc-output-$ACCOUNT_ID --recursive

# 2. Delete buckets
aws s3api delete-bucket --bucket handson-img-proc-source-$ACCOUNT_ID
aws s3api delete-bucket --bucket handson-img-proc-output-$ACCOUNT_ID

# 3. Delete Lambda and Layer
aws lambda delete-function --function-name handson-img-proc-processor

LAYER_VERSION=$(aws lambda list-layer-versions --layer-name pillow-layer \
  --query "LayerVersions[0].Version" --output text)
aws lambda delete-layer-version --layer-name pillow-layer --version-number $LAYER_VERSION

# 4. Delete DynamoDB table
aws dynamodb delete-table --table-name handson-img-proc-metadata

# 5. Delete logs
aws logs delete-log-group --log-group-name /aws/lambda/handson-img-proc-processor

echo "✅ All image processing resources deleted"
```

---

## 12. Estimated AWS Cost

| Resource | Free Tier | Notes |
|----------|-----------|-------|
| Lambda (512MB, 2s avg) | 400K GB-s free | 512MB × 2s = 1 GB-s per image |
| S3 PUT (uploads) | 2,000 PUT requests free | |
| S3 Storage | 5 GB free | |
| DynamoDB | 25 GB + 25 RCU/WCU free | |
| **Total for lab** | **$0** | |

> **Free tier math:** Lambda free tier = 400,000 GB-seconds/month. At 512MB × 2s = 1 GB-s per image, you can process **400,000 images/month** for free.

> ✅ **Free Tier Eligible:** Entirely within AWS Free Tier for lab-scale usage.

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
