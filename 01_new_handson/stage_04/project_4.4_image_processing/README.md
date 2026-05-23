# Project 4.4 — Event-driven Image Processing

## What This Does
Automatically resizes images when uploaded to S3. S3 triggers Lambda on every upload, Lambda resizes the image and stores the output in a separate bucket.

## Architecture
```
User uploads image → S3 (source bucket)
  → S3 Event Notification → Lambda
    → Resize image (thumbnail + medium)
    → Store in S3 (output bucket)
    → Log metadata to DynamoDB
```

## Processing Pipeline
| Input | Output |
|-------|--------|
| Any image (JPEG, PNG, WebP) | thumbnail: 150×150 |
| | medium: 800×600 |
| | original: preserved |

## Services Used
| Service | Role |
|---------|------|
| S3 (source) | Receives uploaded images |
| S3 (output) | Stores processed images |
| Lambda | Resize logic using Pillow |
| S3 Event Notification | Triggers Lambda on upload |
| DynamoDB | Stores image metadata |
| CloudWatch | Lambda logs |

## How to Deploy
```bash
cd terraform
terraform init && terraform apply
terraform output source_bucket
```

## Lessons Learned
- Lambda layers: package large dependencies (Pillow) as a layer to keep deployment package small
- S3 event notifications are eventually consistent — don't rely on exact timing
- Avoid recursive triggers: source and output buckets must be different, or use prefix/suffix filters
- Lambda memory affects CPU — more memory = faster image processing
- Use S3 presigned URLs to give temporary upload access without exposing credentials

## Files
| File | Purpose |
|------|---------|
| `steps.md` | Deploy, upload test image, verify resize outputs, DynamoDB metadata check |
| `verify.md` | Console verification, CLI upload/output checks, DynamoDB metadata, trigger test, expected outputs |
| `cost_estimate.md` | Per-resource cost breakdown |
| `terraform/main.tf` | Terraform — S3 buckets, Lambda, S3 event notification, DynamoDB, IAM |
| `src/handler.py` | Image resize Lambda using Pillow |
| `docs/architecture.md` | Architecture diagrams and notes |

## Code

### `src/processor.py` — S3-triggered image resize Lambda

```bash
pip install boto3 Pillow

# Test locally with a sample S3 event
export OUTPUT_BUCKET=my-processed-bucket
python -c "
from src.processor import handler
event = {
    'Records': [{
        's3': {
            'bucket': {'name': 'my-upload-bucket'},
            'object': {'key': 'uploads/photo.jpg'}
        }
    }]
}
handler(event, None)
"
```

Flow: S3 upload → Lambda trigger → resize to 800×600 → save to output bucket.
