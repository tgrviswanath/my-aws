# Project 4.4 — Image Processing Pipeline

**Stage:** 04 | **Level:** Intermediate | **Est. Time:** 2–3 hours | **Cost:** ~$0.30/month

This project builds a serverless image processing pipeline triggered automatically when a JPEG or PNG
file lands in the `raw/` prefix of an S3 bucket. An S3 event notification fires a Lambda function
that downloads the image to `/tmp`, uses the Pillow library to produce three resized variants —
thumbnail (150px), medium (600px), and large (1200px) — while preserving the original aspect ratio,
then uploads all three to the `processed/` prefix. A DynamoDB item records the original filename,
output keys, pixel dimensions, file sizes, and an ISO-8601 timestamp for every processed image.

---

## Services Used

| Tool | Purpose | Cost |
|---|---|---|
| S3 | Stores raw uploads (`raw/`) and resized outputs (`processed/`) | ~$0.023/GB/month |
| S3 Event Notification | Triggers Lambda on `s3:ObjectCreated:*` for `raw/` prefix | Free |
| Lambda (Python 3.12) | Downloads image, resizes to 3 sizes with Pillow, uploads results | ~$0.20/1M requests |
| Pillow (PIL) | Image resizing library bundled in Lambda layer or deployment package | Free |
| DynamoDB | Stores metadata: filename, output keys, dimensions, timestamp | Free tier / ~$0.25/WCU |
| IAM | Execution role granting Lambda access to S3 and DynamoDB | Free |
| CloudWatch Logs | Lambda execution logs for debugging and monitoring | ~$0.50/GB ingested |

---

## Input / Output

### Input

| Field | Value | Notes |
|---|---|---|
| S3 bucket | `my-images-bucket` | Must exist before deploying |
| S3 key prefix | `raw/` | Only keys under this prefix trigger Lambda |
| File formats | `.jpg`, `.jpeg`, `.png` | Other formats are skipped with a log warning |
| Max file size | ~300 MB practical limit | Lambda `/tmp` is 512 MB by default (up to 10 GB) |
| Event source | `s3:ObjectCreated:*` | Covers PUT, POST, COPY, multipart complete |

### Output

| Artifact | Location | Details |
|---|---|---|
| Thumbnail | `s3://my-images-bucket/processed/<name>_thumb.jpg` | 150 × auto px, JPEG |
| Medium | `s3://my-images-bucket/processed/<name>_medium.jpg` | 600 × auto px, JPEG |
| Large | `s3://my-images-bucket/processed/<name>_large.jpg` | 1200 × auto px, JPEG |
| DynamoDB record | Table `image-metadata`, PK = original S3 key | filename, sizes, dimensions, processed_at |

---

## Architecture

```
  User / App
      |
      | PUT s3://my-images-bucket/raw/photo.jpg
      v
 +----------+
 |    S3    |  raw/ prefix
 | (source) |
 +----------+
      | s3:ObjectCreated:*  (event notification)
      v
 +--------------------+
 |  Lambda Function   |
 |  image_processor   |
 |  Python 3.12       |
 |  + Pillow layer    |
 |                    |
 |  1. Download to    |
 |     /tmp           |
 |  2. thumbnail()    |
 |     150 / 600 /    |
 |     1200 px        |
 |  3. Upload 3 files |
 +--------------------+
      |                  \
      | PUT processed/    | PutItem
      v                   v
 +----------+       +------------------+
 |    S3    |       |    DynamoDB      |
 | processed|       | image-metadata   |
 | prefix   |       | (filename, sizes,|
 +----------+       |  timestamp)      |
                    +------------------+
```

---

## Quick Start

```cmd
REM 1. Create the S3 bucket
aws s3 mb s3://my-images-bucket --region us-east-1

REM 2. Create the DynamoDB table (PAY_PER_REQUEST for low-volume dev)
aws dynamodb create-table ^
  --table-name image-metadata ^
  --attribute-definitions AttributeName=image_key,AttributeType=S ^
  --key-schema AttributeName=image_key,KeyType=HASH ^
  --billing-mode PAY_PER_REQUEST ^
  --region us-east-1

REM 3. Create Lambda execution role
aws iam create-role ^
  --role-name image-processor-role ^
  --assume-role-policy-document file://trust-policy.json

REM 4. Attach S3 + DynamoDB permissions to the role
aws iam attach-role-policy ^
  --role-name image-processor-role ^
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

aws iam attach-role-policy ^
  --role-name image-processor-role ^
  --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess

REM 5. Package and deploy Lambda (Pillow must be in the zip or a layer)
aws lambda create-function ^
  --function-name image-processor ^
  --runtime python3.12 ^
  --role arn:aws:iam::123456789012:role/image-processor-role ^
  --handler lambda_function.lambda_handler ^
  --zip-file fileb://function.zip ^
  --timeout 60 ^
  --memory-size 512 ^
  --region us-east-1

REM 6. Allow S3 to invoke the Lambda function (resource-based policy)
aws lambda add-permission ^
  --function-name image-processor ^
  --statement-id s3-invoke ^
  --action lambda:InvokeFunction ^
  --principal s3.amazonaws.com ^
  --source-arn arn:aws:s3:::my-images-bucket ^
  --region us-east-1

REM 7. Add S3 event notification to trigger Lambda on raw/ prefix
aws s3api put-bucket-notification-configuration ^
  --bucket my-images-bucket ^
  --notification-configuration file://s3-notification.json

REM 8. Test — upload an image and check processed/ and DynamoDB
aws s3 cp test_photo.jpg s3://my-images-bucket/raw/test_photo.jpg
aws s3 ls s3://my-images-bucket/processed/
aws dynamodb get-item ^
  --table-name image-metadata ^
  --key "{\"image_key\":{\"S\":\"raw/test_photo.jpg\"}}"
```

---

## Data Flow

1. A client uploads `photo.jpg` to `s3://my-images-bucket/raw/photo.jpg` via PUT.
2. S3 detects the `s3:ObjectCreated:*` event on the `raw/` prefix and publishes it to Lambda synchronously.
3. Lambda receives the event, extracts the bucket name and object key from `event['Records'][0]['s3']`.
4. Lambda downloads the object to `/tmp/photo.jpg` using `boto3.client('s3').download_file()`.
5. Pillow opens the file and calls `thumbnail((150, 150))`, `thumbnail((600, 600))`, and `thumbnail((1200, 1200))` — aspect ratio is preserved automatically.
6. Each resized image is saved to `/tmp/` then uploaded to `s3://my-images-bucket/processed/` with the appropriate suffix (`_thumb`, `_medium`, `_large`).
7. Lambda calls `dynamodb.put_item()` writing the original key, three output keys, pixel dimensions, file sizes in bytes, and `processed_at` UTC timestamp.
8. Lambda returns 200; CloudWatch Logs captures the execution summary including any Pillow warnings.

---

## Project Files

| File | Description |
|---|---|
| `lambda_function.py` | Main handler — downloads, resizes with Pillow, uploads, writes DynamoDB |
| `requirements.txt` | Contains `Pillow==10.3.0` for local packaging |
| `build.cmd` | Windows script to pip-install Pillow into `package/` and zip with handler |
| `s3-notification.json` | S3 event notification config pointing to Lambda ARN, prefix `raw/` |
| `trust-policy.json` | IAM trust policy allowing Lambda service to assume the execution role |
| `test_photo.jpg` | Sample JPEG for manual upload testing |
| `README.md` | This file |

---

## Lessons Learned

- **S3 event notification vs EventBridge** — S3 event notifications fire directly to Lambda with no extra cost and ~1s latency; EventBridge adds flexibility (filtering, multiple targets) but adds complexity and cost. For a single-bucket trigger, event notification is the right choice.
- **Lambda `/tmp` is ephemeral and sized** — default is 512 MB but can be raised to 10 GB. Pillow writes intermediate files there; for images over 200 MB uncompressed, bump the `/tmp` size and Lambda memory together.
- **Resource-based policy is mandatory for S3 → Lambda** — S3 uses `s3.amazonaws.com` as the invoking principal. Without `lambda:add-permission` granting that principal, the invocation silently fails with no error visible in S3.
- **Prefix filter prevents the feedback loop** — if `processed/` lives in the same bucket and you use an `s3:ObjectCreated:*` rule with no prefix, Lambda will re-trigger on its own output indefinitely until concurrency limits kick in. Always scope the notification to `raw/` only.
- **`thumbnail()` vs `resize()`** — `thumbnail()` treats the argument as a bounding box and shrinks proportionally, never enlarging. `resize()` stretches to exact dimensions and distorts non-square images. Use `thumbnail()` for user photos where you want natural proportions.
- **Cold start with Pillow** — the Pillow wheel is ~4 MB; bundling it in a Lambda layer shared across functions avoids re-deploying the dependency on every code change and keeps the deployment package under 3 MB for console editing.
- **DynamoDB PK design matters early** — using the original S3 key (`raw/photo.jpg`) as the partition key makes lookups by filename O(1) but prevents querying by date without a GSI. Add a `processed_at` GSI if you need time-range queries later.
