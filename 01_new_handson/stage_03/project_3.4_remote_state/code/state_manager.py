"""
state_manager.py — Bootstrap and manage Terraform remote state backend.

Usage:
    python state_manager.py bootstrap --bucket BUCKET --table TABLE [--region REGION]
    python state_manager.py list      --bucket BUCKET [--region REGION]
    python state_manager.py unlock    --table TABLE --lock-id LOCK_ID [--region REGION]

Commands:
    bootstrap   Create S3 bucket (versioning + AES-256 encryption) and
                DynamoDB table for state locking, then print the backend block.
    list        List all .tfstate files stored in the S3 bucket.
    unlock      Remove a stuck DynamoDB lock entry by its LockID.
"""

import sys
import json
import argparse
import boto3
from botocore.exceptions import ClientError, NoCredentialsError


# ── ANSI colors ───────────────────────────────────────────────────────────────
class C:
    RESET  = "\033[0m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    RED    = "\033[91m"
    CYAN   = "\033[96m"
    BOLD   = "\033[1m"


def info(msg):  print(f"{C.CYAN}[INFO]{C.RESET}  {msg}")
def ok(msg):    print(f"{C.GREEN}[OK]{C.RESET}    {msg}")
def warn(msg):  print(f"{C.YELLOW}[WARN]{C.RESET}  {msg}")
def err(msg):   print(f"{C.RED}[ERR]{C.RESET}   {msg}", file=sys.stderr)


# ── Bootstrap ─────────────────────────────────────────────────────────────────

def bootstrap(bucket: str, table: str, region: str, profile: str | None) -> int:
    """
    Create the S3 bucket and DynamoDB table required for Terraform remote state.

    S3 bucket configuration:
        - Versioning enabled (allows state history and rollback)
        - AES-256 server-side encryption
        - Public access blocked

    DynamoDB table configuration:
        - Partition key: LockID (String)
        - PAY_PER_REQUEST billing (no capacity planning needed)

    Args:
        bucket:  S3 bucket name.
        table:   DynamoDB table name.
        region:  AWS region.
        profile: Optional AWS CLI profile.

    Returns:
        0 on success, 1 on failure.
    """
    session = boto3.Session(region_name=region, profile_name=profile)
    s3  = session.client("s3")
    ddb = session.client("dynamodb")

    # ── S3 bucket ─────────────────────────────────────────────────────────────
    info(f"Creating S3 bucket: {bucket} in {region}")
    try:
        if region == "us-east-1":
            # us-east-1 does NOT accept a LocationConstraint
            s3.create_bucket(Bucket=bucket)
        else:
            s3.create_bucket(
                Bucket=bucket,
                CreateBucketConfiguration={"LocationConstraint": region},
            )
        ok(f"Bucket created: {bucket}")
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        if code in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
            warn(f"Bucket already exists: {bucket} — skipping creation.")
        else:
            err(f"Failed to create bucket: {exc}")
            return 1

    # Enable versioning
    try:
        s3.put_bucket_versioning(
            Bucket=bucket,
            VersioningConfiguration={"Status": "Enabled"},
        )
        ok("Versioning enabled.")
    except ClientError as exc:
        err(f"Failed to enable versioning: {exc}")
        return 1

    # Enable AES-256 server-side encryption
    try:
        s3.put_bucket_encryption(
            Bucket=bucket,
            ServerSideEncryptionConfiguration={
                "Rules": [{
                    "ApplyServerSideEncryptionByDefault": {
                        "SSEAlgorithm": "AES256"
                    }
                }]
            },
        )
        ok("AES-256 encryption enabled.")
    except ClientError as exc:
        err(f"Failed to enable encryption: {exc}")
        return 1

    # Block all public access
    try:
        s3.put_public_access_block(
            Bucket=bucket,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls":       True,
                "IgnorePublicAcls":      True,
                "BlockPublicPolicy":     True,
                "RestrictPublicBuckets": True,
            },
        )
        ok("Public access blocked.")
    except ClientError as exc:
        err(f"Failed to block public access: {exc}")
        return 1

    # ── DynamoDB table ────────────────────────────────────────────────────────
    info(f"Creating DynamoDB table: {table}")
    try:
        ddb.create_table(
            TableName=table,
            AttributeDefinitions=[{"AttributeName": "LockID", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "LockID", "KeyType": "HASH"}],
            BillingMode="PAY_PER_REQUEST",
        )
        # Wait until the table is active
        waiter = ddb.get_waiter("table_exists")
        waiter.wait(TableName=table)
        ok(f"DynamoDB table created: {table}")
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ResourceInUseException":
            warn(f"DynamoDB table already exists: {table} — skipping creation.")
        else:
            err(f"Failed to create DynamoDB table: {exc}")
            return 1

    # ── Print backend config ──────────────────────────────────────────────────
    print(f"\n{C.BOLD}{'─' * 55}{C.RESET}")
    print(f"{C.BOLD}Paste this backend block into your main.tf:{C.RESET}\n")
    print(f'{C.GREEN}terraform {{{C.RESET}')
    print(f'{C.GREEN}  backend "s3" {{{C.RESET}')
    print(f'{C.GREEN}    bucket         = "{bucket}"{C.RESET}')
    print(f'{C.GREEN}    key            = "terraform.tfstate"{C.RESET}')
    print(f'{C.GREEN}    region         = "{region}"{C.RESET}')
    print(f'{C.GREEN}    dynamodb_table = "{table}"{C.RESET}')
    print(f'{C.GREEN}    encrypt        = true{C.RESET}')
    print(f'{C.GREEN}  }}{C.RESET}')
    print(f'{C.GREEN}}}{C.RESET}')
    print(f"{C.BOLD}{'─' * 55}{C.RESET}\n")

    return 0


# ── List state files ──────────────────────────────────────────────────────────

def list_states(bucket: str, region: str, profile: str | None) -> int:
    """
    List all Terraform state files (.tfstate) stored in the S3 bucket.

    Args:
        bucket:  S3 bucket name.
        region:  AWS region.
        profile: Optional AWS CLI profile.

    Returns:
        0 on success, 1 on failure.
    """
    session = boto3.Session(region_name=region, profile_name=profile)
    s3 = session.client("s3")

    info(f"Listing state files in s3://{bucket}/")
    paginator = s3.get_paginator("list_object_versions")

    state_files: dict[str, list[dict]] = {}

    try:
        for page in paginator.paginate(Bucket=bucket):
            for obj in page.get("Versions", []):
                key = obj["Key"]
                if key.endswith(".tfstate"):
                    state_files.setdefault(key, []).append(obj)
    except ClientError as exc:
        err(f"Failed to list bucket contents: {exc}")
        return 1

    if not state_files:
        warn("No .tfstate files found in the bucket.")
        return 0

    print(f"\n{C.BOLD}State files in s3://{bucket}/{C.RESET}")
    print(f"  {'Key':<50} {'Versions':>8}  {'Latest modified'}")
    print("  " + "-" * 80)

    for key, versions in sorted(state_files.items()):
        latest = max(versions, key=lambda v: v["LastModified"])
        ts = latest["LastModified"].strftime("%Y-%m-%d %H:%M UTC")
        print(f"  {key:<50} {len(versions):>8}  {ts}")

    print()
    return 0


# ── Unlock ────────────────────────────────────────────────────────────────────

def unlock(table: str, lock_id: str, region: str, profile: str | None) -> int:
    """
    Remove a stuck Terraform state lock from DynamoDB.

    Terraform stores lock info as an item with the key LockID = <lock_id>.
    This function deletes that item, freeing the lock.

    Args:
        table:   DynamoDB table name used for locking.
        lock_id: The LockID value to delete (shown in the Terraform lock error).
        region:  AWS region.
        profile: Optional AWS CLI profile.

    Returns:
        0 on success, 1 on failure.
    """
    session = boto3.Session(region_name=region, profile_name=profile)
    ddb = session.client("dynamodb")

    # First, show the lock info so the operator can verify
    info(f"Looking up lock '{lock_id}' in table '{table}' …")
    try:
        response = ddb.get_item(
            TableName=table,
            Key={"LockID": {"S": lock_id}},
        )
    except ClientError as exc:
        err(f"Failed to read DynamoDB table: {exc}")
        return 1

    item = response.get("Item")
    if not item:
        warn(f"No lock found with LockID='{lock_id}'. Nothing to do.")
        return 0

    # Pretty-print the lock info
    print(f"\n{C.BOLD}Lock details:{C.RESET}")
    for attr, val in item.items():
        v = list(val.values())[0]
        print(f"  {attr}: {v}")

    confirm = input(f"\n  Delete this lock? Type 'yes' to confirm: ").strip().lower()
    if confirm != "yes":
        warn("Aborted.")
        return 0

    try:
        ddb.delete_item(
            TableName=table,
            Key={"LockID": {"S": lock_id}},
        )
        ok(f"Lock '{lock_id}' removed successfully.")
    except ClientError as exc:
        err(f"Failed to delete lock: {exc}")
        return 1

    return 0


# ── CLI entry point ───────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bootstrap and manage Terraform remote state backend.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  python state_manager.py bootstrap --bucket my-tf-state --table my-tf-locks\n"
               "  python state_manager.py list      --bucket my-tf-state\n"
               "  python state_manager.py unlock    --table my-tf-locks --lock-id abc123",
    )
    parser.add_argument("--region",  default="us-east-1", help="AWS region (default: us-east-1)")
    parser.add_argument("--profile", default=None,        help="AWS CLI profile name")

    sub = parser.add_subparsers(dest="command", required=True)

    # bootstrap
    p_boot = sub.add_parser("bootstrap", help="Create S3 bucket + DynamoDB table.")
    p_boot.add_argument("--bucket", required=True, help="S3 bucket name for state storage.")
    p_boot.add_argument("--table",  required=True, help="DynamoDB table name for locking.")

    # list
    p_list = sub.add_parser("list", help="List state files in the S3 bucket.")
    p_list.add_argument("--bucket", required=True, help="S3 bucket name.")

    # unlock
    p_unlock = sub.add_parser("unlock", help="Remove a stuck DynamoDB lock.")
    p_unlock.add_argument("--table",   required=True, help="DynamoDB table name.")
    p_unlock.add_argument("--lock-id", required=True, help="LockID value to delete.")

    args = parser.parse_args()

    try:
        if args.command == "bootstrap":
            rc = bootstrap(args.bucket, args.table, args.region, args.profile)
        elif args.command == "list":
            rc = list_states(args.bucket, args.region, args.profile)
        elif args.command == "unlock":
            rc = unlock(args.table, args.lock_id, args.region, args.profile)
        else:
            rc = 1
    except NoCredentialsError:
        err("AWS credentials not found. Configure via env vars or ~/.aws/credentials.")
        rc = 1

    sys.exit(rc)


if __name__ == "__main__":
    main()
