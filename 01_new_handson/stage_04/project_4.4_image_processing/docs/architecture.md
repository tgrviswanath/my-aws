# Architecture — Project 4.4 Event-driven Image Processing

## Event Flow

```
User uploads image
    │
    ▼
S3 source bucket (handson-img-proc-source)
    │
    │ S3 ObjectCreated event (*.jpg, *.png)
    ▼
Lambda: handson-img-proc-processor
    │
    ├── Download original from S3
    ├── Open with Pillow
    ├── Resize to thumbnail (150×150)
    ├── Resize to medium (800×600)
    ├── Upload both to output bucket
    └── Write metadata to DynamoDB
    │
    ▼
S3 output bucket (handson-img-proc-output)
    ├── processed/thumbnail/photos/image.jpg
    └── processed/medium/photos/image.jpg

DynamoDB: handson-img-proc-metadata
    └── {image_key, original_size, outputs, processed_at}
```

## Lambda Layer (Pillow)

```
Lambda function (Python 3.11)
    └── Layer: pillow-layer.zip
          └── python/
                └── PIL/  ← Pillow library
                      └── Image.py, ...

Build layer:
  docker run --rm -v $(pwd)/layer:/layer \
    public.ecr.aws/lambda/python:3.11 \
    pip install Pillow -t /layer/python
```

## ⚠️ Avoid Recursive Triggers

```
WRONG: source and output are the SAME bucket
  → Lambda uploads to same bucket
  → Triggers Lambda again
  → Infinite loop!

CORRECT: source ≠ output (different buckets)
  → No recursive trigger
```
