"""
s3_uploader.py — Upload files to S3 using boto3
Usage:
  python s3_uploader.py upload --bucket BUCKET --file FILE --key KEY
  python s3_uploader.py sync   --bucket BUCKET --folder FOLDER --prefix PREFIX
  python s3_uploader.py list   --bucket BUCKET
"""

import argparse
import os
import sys
import boto3
from botocore.exceptions import ClientError


def get_s3_client():
    return boto3.client("s3")


def upload_file(bucket: str, file_path: str, s3_key: str) -> bool:
    s3 = get_s3_client()
    try:
        file_size = os.path.getsize(file_path)
        print(f"Uploading {file_path} ({file_size} bytes) → s3://{bucket}/{s3_key}")
        s3.upload_file(file_path, bucket, s3_key)
        print(f"✅ Upload complete: s3://{bucket}/{s3_key}")
        return True
    except ClientError as e:
        print(f"❌ Upload failed: {e}")
        return False


def sync_folder(bucket: str, folder: str, prefix: str = "") -> None:
    s3 = get_s3_client()
    uploaded = 0
    failed = 0

    for root, _, files in os.walk(folder):
        for filename in files:
            local_path = os.path.join(root, filename)
            relative_path = os.path.relpath(local_path, folder)
            s3_key = os.path.join(prefix, relative_path).replace("\\", "/")

            try:
                s3.upload_file(local_path, bucket, s3_key)
                print(f"✅ {local_path} → s3://{bucket}/{s3_key}")
                uploaded += 1
            except ClientError as e:
                print(f"❌ Failed {local_path}: {e}")
                failed += 1

    print(f"\nSync complete: {uploaded} uploaded, {failed} failed")


def list_bucket(bucket: str, prefix: str = "") -> None:
    s3 = get_s3_client()
    paginator = s3.get_paginator("list_objects_v2")

    total_size = 0
    total_files = 0

    print(f"\nContents of s3://{bucket}/{prefix}")
    print("-" * 60)

    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            size_kb = obj["Size"] / 1024
            print(f"  {obj['Key']:<50} {size_kb:>8.1f} KB  {obj['LastModified'].strftime('%Y-%m-%d %H:%M')}")
            total_size += obj["Size"]
            total_files += 1

    print("-" * 60)
    print(f"Total: {total_files} files, {total_size / 1024 / 1024:.2f} MB")


def main():
    parser = argparse.ArgumentParser(description="S3 file uploader")
    subparsers = parser.add_subparsers(dest="command")

    # upload command
    upload_parser = subparsers.add_parser("upload")
    upload_parser.add_argument("--bucket", required=True)
    upload_parser.add_argument("--file", required=True)
    upload_parser.add_argument("--key", required=True)

    # sync command
    sync_parser = subparsers.add_parser("sync")
    sync_parser.add_argument("--bucket", required=True)
    sync_parser.add_argument("--folder", required=True)
    sync_parser.add_argument("--prefix", default="")

    # list command
    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--bucket", required=True)
    list_parser.add_argument("--prefix", default="")

    args = parser.parse_args()

    if args.command == "upload":
        success = upload_file(args.bucket, args.file, args.key)
        sys.exit(0 if success else 1)
    elif args.command == "sync":
        sync_folder(args.bucket, args.folder, args.prefix)
    elif args.command == "list":
        list_bucket(args.bucket, args.prefix)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
