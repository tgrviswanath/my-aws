# Project 4.4 — Event-Driven Image Processing
# AWS Console UI — Step-by-Step Implementation

---

#### Step 1 — Create Source and Output S3 Buckets

**Prerequisites Check:**
- ✅ Required permissions: `s3:CreateBucket`, `s3:PutBucketNotification`
- ✅ Services enabled: Amazon S3 (global service)
- ✅ Region availability: us-east-1 — both buckets must be in same region as Lambda

**Step 1.1: Navigate and Verify**
1. Go to [S3 Console](https://console.aws.amazon.com/s3)
2. **Expected View:** S3 dashboard with bucket list and "Create bucket" button
3. Click **Create bucket** (you will do this twice — once for source, once for output)

**Step 1.2: Create Source Bucket**

**Decision Point 1:** Bucket Naming

| Option | Risk | For This Project |
|--------|------|-----------------|
| Simple name (e.g. `my-images`) | Already taken — S3 names are globally unique | ❌ |
| Name with Account ID suffix | Guaranteed unique | ✅ Use this |

| Field | Value | Explanation |
|-------|-------|-------------|
| Bucket name | `handson-img-proc-source-[YOUR_ACCOUNT_ID]` | Replace [YOUR_ACCOUNT_ID] with your 12-digit AWS account number |
| AWS Region | us-east-1 | Must match Lambda region |
| Object Ownership | ACLs disabled | Modern secure default |
| Block all public access | ✅ All 4 boxes checked | Images must stay private |
| Versioning | Disable | Not needed for processing |
| Encryption | SSE-S3 (default) | Free, automatic |

Click **Create bucket**

**📸 Screenshot:** Source bucket creation form filled in

**Step 1.3: Create Output Bucket**

Click **Create bucket** again. Repeat with:

| Field | Value |
|-------|-------|
| Bucket name | `handson-img-proc-output-[YOUR_ACCOUNT_ID]` |
| All other settings | Same as source bucket |

**⚠️ CRITICAL — Why MUST they be different buckets?**

```
WRONG (same bucket):
  User uploads → source bucket → Lambda triggered
  Lambda uploads processed image → SAME bucket → Lambda triggered AGAIN
  Lambda uploads again → triggers Lambda AGAIN → infinite loop!
  Result: runaway Lambda invocations → potential $100+ bill

CORRECT (different buckets):
  User uploads → source bucket → Lambda triggered (once)
  Lambda uploads to OUTPUT bucket → no trigger → done ✅
```

**📸 Screenshot:** S3 bucket list showing both source and output buckets

---

#### Step 2 — Build and Upload Pillow Lambda Layer

**Prerequisites Check:**
- ✅ Docker installed locally (recommended) OR pip with platform flag
- ✅ Required permissions: `lambda:PublishLayerVersion`

**Step 2.1: Build Pillow Layer Locally**

Open your local terminal:

**Option A — Docker (recommended, matches Lambda runtime exactly):**
```bash
mkdir -p layer/python
docker run --rm \
  -v $(pwd)/layer:/layer \
  public.ecr.aws/lambda/python:3.11 \
  pip install Pillow -t /layer/python
cd layer && zip -r ../pillow-layer.zip python/ && cd ..
```

**Option B — pip with platform flag (no Docker needed):**
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

**Step 2.2: Upload Layer to AWS Console**

**Decision Point 1:** Why a Lambda Layer?

| Approach | Deployment Size | For This Project |
|----------|----------------|-----------------|
| Include Pillow in function zip | ~15MB per deploy | ❌ Slow, can exceed 50MB limit |
| Lambda Layer | Shared, cached | ✅ Function zip stays tiny |

1. Go to [Lambda Console](https://console.aws.amazon.com/lambda)
2. Left sidebar → **Layers** → **Create layer**

| Field | Value |
|-------|-------|
| Name | `pillow-layer` |
| Description | Pillow image library for Python 3.11 Lambda |
| Upload | Click **Upload** → select your `pillow-layer.zip` |
| Compatible runtimes | ✅ Python 3.11 |
| Compatible architectures | x86_64 |

Click **Create**

**Expected Outcome:** Layer created with Version 1

**📸 Screenshot:** Lambda Layers page showing `pillow-layer` Version 1 with Python 3.11

**Troubleshooting:**
- Upload fails (file > 50MB): Upload to S3 first, then reference the S3 URL in the layer
- `ModuleNotFoundError: No module named 'PIL'` on Lambda: Layer was built for wrong OS — rebuild with Docker

---

#### Step 3 — Create Lambda IAM Role

Role name: `handson-lambda-exec-role` (reuse from 4.1 or create fresh)

Policies needed:
- `AWSLambdaBasicExecutionRole` — CloudWatch logs
- `AmazonS3FullAccess` — Read from source, write to output bucket
- `AmazonDynamoDBFullAccess` — Write image metadata

---

#### Step 4 — Deploy Image Processor Lambda

**Step 4.1: Create Function**

Lambda Console → **Create function** → Author from scratch

| Field | Value |
|-------|-------|
| Function name | `handson-img-proc-processor` |
| Runtime | Python 3.11 |
| Architecture | x86_64 (must match Pillow layer architecture) |
| Execution role | `handson-lambda-exec-role` |

**Step 4.2: Upload Code**

Paste entire content of `src/handler.py` → Click **Deploy**

**Step 4.3: Attach Pillow Layer**

1. Scroll down to **Layers** section on the function page
2. Click **Add a layer**
3. Select **Custom layers**
4. Layer: `pillow-layer` → Version: 1
5. Click **Add**

**📸 Screenshot:** Lambda function showing Pillow layer in the Layers section

**Step 4.4: Configure Memory and Timeout**

**Decision Point 1:** Memory size matters for image processing

| Memory | CPU Allocation | Processing Speed | Cost |
|--------|---------------|-----------------|------|
| 128 MB | Minimal | ~6-8 seconds/image | Cheapest |
| 512 MB | Medium | ~1-2 seconds/image | ✅ Good balance |
| 1024 MB | High | ~0.5 seconds/image | Higher |

Configuration → General configuration → Edit:

| Setting | Value | Why |
|---------|-------|-----|
| Memory | `512` MB | Lambda CPU scales with memory |
| Timeout | `60` seconds | Large images can take a few seconds |

**Step 4.5: Set Environment Variables**

Configuration → Environment variables → Edit → Add:

| Key | Value | Explanation |
|-----|-------|-------------|
| `OUTPUT_BUCKET` | `handson-img-proc-output-[ACCOUNT_ID]` | Where to write processed images |
| `TABLE_NAME` | `handson-img-proc-metadata` | DynamoDB table for metadata |

**📸 Screenshot:** Lambda environment variables showing OUTPUT_BUCKET and TABLE_NAME

---

#### Step 5 — Create DynamoDB Metadata Table

DynamoDB Console → **Create table**

| Field | Value |
|-------|-------|
| Table name | `handson-img-proc-metadata` |
| Partition key | `image_key` (String) |
| Billing mode | On-demand |

Click **Create table** → Wait for Active status.

---

#### Step 6 — Configure S3 Event Notification

**Prerequisites Check:**
- ✅ Required permissions: `s3:PutBucketNotification`
- ✅ Lambda function `handson-img-proc-processor` deployed
- ✅ Source bucket created

**Step 6.1: Navigate**
1. S3 Console → Click `handson-img-proc-source-[ACCOUNT_ID]`
2. Click **Properties** tab
3. Scroll to **Event notifications** section
4. Click **Create event notification**

**Step 6.2: Make Selections**

**Decision Point 1:** Event Type

| Event | When triggered | For This Project |
|-------|---------------|-----------------|
| `s3:ObjectCreated:Put` | Direct PUT uploads | ✅ Include |
| `s3:ObjectCreated:Post` | Multipart / form uploads | ✅ Include |
| `s3:ObjectCreated:*` | ALL object creation events | ✅ Use this (covers all) |

**Step 6.3: Configure Details**

| Field | Value | Explanation |
|-------|-------|-------------|
| Event name | `trigger-image-processor` | |
| Prefix | *(leave empty)* | Trigger on all paths |
| Suffix | *(leave empty)* | Trigger on all file types (handler filters internally) |
| Event types | ✅ `s3:ObjectCreated:*` | All uploads |
| Destination | **Lambda function** | |
| Lambda function | `handson-img-proc-processor` | From dropdown |

Click **Save changes**

**Step 6.4: Validate Result**

**Expected Outcome:** Event notification appears in list, Destination = `handson-img-proc-processor`

**📸 Screenshot:** S3 source bucket Properties → Event notifications → showing `trigger-image-processor` → `handson-img-proc-processor` Lambda

> **What AWS does automatically:** AWS adds a `lambda:InvokeFunction` resource-based policy to the Lambda function, allowing the S3 bucket to invoke it. You can verify in Lambda → Configuration → Permissions → Resource-based policy statements.

**Troubleshooting:**
- `Unable to validate the following destination configurations`: Lambda doesn't have the permission yet — AWS should add it automatically. If not, add manually via Lambda → Permissions → Add permission
- Event not triggering: Check bucket name in notification matches the source bucket exactly

---

#### Step 7 — Test End-to-End Pipeline

**Step 7.1: Upload a Test Image**

Download a test image first:
```bash
curl -o test.jpg "https://picsum.photos/2000/1500"
```

1. S3 Console → Click source bucket `handson-img-proc-source-[ACCOUNT_ID]`
2. Click **Upload** → Drag `test.jpg` into the upload area
3. Click **Upload**

**📸 Screenshot:** Source bucket showing `test.jpg` just uploaded

**Step 7.2: Wait and Check Output Bucket**

Wait ~5-10 seconds, then:

1. S3 Console → Click output bucket `handson-img-proc-output-[ACCOUNT_ID]`
2. **Expected View:** `processed/` folder appeared
3. Navigate into `processed/` → `thumbnail/` → find your image

**📸 Screenshot:** Output bucket showing `processed/thumbnail/` and `processed/medium/` folders

**Step 7.3: Download and Verify Thumbnail**

1. Click `processed/thumbnail/test.jpg` → **Download**
2. Open downloaded image — should be small (≤150×150 pixels)

**Decision Point 2:** Verify dimensions in terminal

```bash
# Install Pillow locally if needed: pip install Pillow
python3 -c "
from PIL import Image
img = Image.open('path/to/downloaded/thumbnail.jpg')
print(f'Thumbnail size: {img.size}')
# Expected: (150, X) where X ≤ 150
"
```

**Step 7.4: Check Lambda CloudWatch Logs**

1. CloudWatch → Log groups → `/aws/lambda/handson-img-proc-processor`
2. Click latest log stream
3. **Expected log entries:**
```
Processing: s3://handson-img-proc-source-.../test.jpg (XXXX bytes)
  Created thumbnail: processed/thumbnail/test.jpg (150, 113)
  Created medium: processed/medium/test.jpg (800, 600)
Done: test.jpg → ['thumbnail', 'medium']
```

**📸 Screenshot:** CloudWatch log stream showing all processing steps

**Step 7.5: Verify DynamoDB Metadata**

1. DynamoDB → Tables → `handson-img-proc-metadata`
2. Click **Explore table items**
3. **Expected Outcome:** Item with these attributes:
   - `image_key`: `test.jpg`
   - `original_size`: `2000x1500`
   - `format`: `JPEG`
   - `outputs`: `{thumbnail: {...}, medium: {...}}`
   - `processed_at`: ISO timestamp

**📸 Screenshot:** DynamoDB item showing full metadata with outputs nested object
