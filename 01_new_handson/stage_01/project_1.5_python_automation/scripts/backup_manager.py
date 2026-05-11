"""
backup_manager.py — Automate RDS snapshots and S3 backups
Usage:
  python backup_manager.py rds-snapshot  --instance mysql-lab-01
  python backup_manager.py s3-backup     --source src-bucket --destination dst-bucket
  python backup_manager.py list-snapshots --instance mysql-lab-01
"""

import argparse
from datetime import datetime
import boto3
from botocore.exceptions import ClientError


def create_rds_snapshot(instance_id: str) -> None:
    rds = boto3.client("rds", region_name="us-east-1")
    snapshot_id = f"{instance_id}-backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    try:
        response = rds.create_db_snapshot(
            DBInstanceIdentifier=instance_id,
            DBSnapshotIdentifier=snapshot_id,
            Tags=[
                {"Key": "Project", "Value": "handson"},
                {"Key": "CreatedBy", "Value": "backup-manager"},
            ]
        )
        status = response["DBSnapshot"]["Status"]
        print(f"✅ Snapshot {snapshot_id} created — status: {status}")
    except ClientError as e:
        print(f"❌ Snapshot failed: {e}")


def list_snapshots(instance_id: str) -> None:
    rds = boto3.client("rds", region_name="us-east-1")
    response = rds.describe_db_snapshots(DBInstanceIdentifier=instance_id)

    snapshots = sorted(
        response["DBSnapshots"],
        key=lambda x: x["SnapshotCreateTime"],
        reverse=True
    )

    print(f"\nSnapshots for {instance_id}:")
    print(f"{'Snapshot ID':<50} {'Status':<12} {'Size (GB)':<10} {'Created'}")
    print("-" * 90)

    for snap in snapshots:
        created = snap["SnapshotCreateTime"].strftime("%Y-%m-%d %H:%M")
        print(
            f"{snap['DBSnapshotIdentifier']:<50} "
            f"{snap['Status']:<12} "
            f"{snap.get('AllocatedStorage', 0):<10} "
            f"{created}"
        )


def s3_backup(source_bucket: str, dest_bucket: str) -> None:
    s3 = boto3.client("s3")
    paginator = s3.get_paginator("list_objects_v2")

    copied = 0
    failed = 0
    timestamp = datetime.now().strftime("%Y%m%d")

    for page in paginator.paginate(Bucket=source_bucket):
        for obj in page.get("Contents", []):
            dest_key = f"backup-{timestamp}/{obj['Key']}"
            try:
                s3.copy_object(
                    CopySource={"Bucket": source_bucket, "Key": obj["Key"]},
                    Bucket=dest_bucket,
                    Key=dest_key
                )
                print(f"✅ Copied: {obj['Key']} → {dest_key}")
                copied += 1
            except ClientError as e:
                print(f"❌ Failed: {obj['Key']}: {e}")
                failed += 1

    print(f"\nBackup complete: {copied} copied, {failed} failed")


def main():
    parser = argparse.ArgumentParser(description="AWS backup manager")
    subparsers = parser.add_subparsers(dest="command")

    snap_parser = subparsers.add_parser("rds-snapshot")
    snap_parser.add_argument("--instance", required=True)

    list_parser = subparsers.add_parser("list-snapshots")
    list_parser.add_argument("--instance", required=True)

    s3_parser = subparsers.add_parser("s3-backup")
    s3_parser.add_argument("--source", required=True)
    s3_parser.add_argument("--destination", required=True)

    args = parser.parse_args()

    if args.command == "rds-snapshot":
        create_rds_snapshot(args.instance)
    elif args.command == "list-snapshots":
        list_snapshots(args.instance)
    elif args.command == "s3-backup":
        s3_backup(args.source, args.destination)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
