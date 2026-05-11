"""
handler.py — S3-triggered image resizer using Pillow.
Triggered by S3 ObjectCreated events.
"""

import io
import json
import os
import urllib.parse
from datetime import datetime, timezone

import boto3
from PIL import Image

s3       = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

OUTPUT_BUCKET = os.environ["OUTPUT_BUCKET"]
TABLE_NAME    = os.environ["TABLE_NAME"]
table         = dynamodb.Table(TABLE_NAME)

SIZES = {
    "thumbnail": (150, 150),
    "medium":    (800, 600),
}


def handler(event: dict, context) -> None:
    """Process each S3 upload event."""
    for record in event.get("Records", []):
        try:
            process_record(record)
        except Exception as e:
            print(f"Error processing record: {e}")
            raise


def process_record(record: dict) -> None:
    source_bucket = record["s3"]["bucket"]["name"]
    object_key    = urllib.parse.unquote_plus(record["s3"]["object"]["key"])
    file_size     = record["s3"]["object"]["size"]

    print(f"Processing: s3://{source_bucket}/{object_key} ({file_size} bytes)")

    # Skip non-image files
    ext = object_key.lower().rsplit(".", 1)[-1]
    if ext not in ("jpg", "jpeg", "png", "webp", "gif"):
        print(f"Skipping non-image file: {object_key}")
        return

    # Download original image
    response = s3.get_object(Bucket=source_bucket, Key=object_key)
    image_data = response["Body"].read()

    # Open with Pillow
    img = Image.open(io.BytesIO(image_data))
    original_size = img.size
    img_format = img.format or "JPEG"

    # Convert RGBA to RGB for JPEG output
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    outputs = {}

    # Generate each size
    for size_name, dimensions in SIZES.items():
        resized = img.copy()
        resized.thumbnail(dimensions, Image.LANCZOS)

        buffer = io.BytesIO()
        resized.save(buffer, format=img_format, quality=85, optimize=True)
        buffer.seek(0)

        output_key = f"processed/{size_name}/{object_key}"
        s3.put_object(
            Bucket=OUTPUT_BUCKET,
            Key=output_key,
            Body=buffer,
            ContentType=f"image/{img_format.lower()}",
            Metadata={
                "original-key": object_key,
                "size":         size_name,
                "dimensions":   f"{resized.size[0]}x{resized.size[1]}",
            },
        )

        outputs[size_name] = {
            "key":        output_key,
            "dimensions": f"{resized.size[0]}x{resized.size[1]}",
        }
        print(f"  Created {size_name}: {output_key} ({resized.size})")

    # Log metadata to DynamoDB
    table.put_item(Item={
        "image_key":       object_key,
        "source_bucket":   source_bucket,
        "output_bucket":   OUTPUT_BUCKET,
        "original_size":   f"{original_size[0]}x{original_size[1]}",
        "file_size_bytes": file_size,
        "format":          img_format,
        "outputs":         outputs,
        "processed_at":    datetime.now(timezone.utc).isoformat(),
    })

    print(f"Done: {object_key} → {list(outputs.keys())}")
