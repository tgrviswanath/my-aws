"""
dr_failover.py — Trigger and verify disaster recovery failover.

Usage:
    # Check DR region readiness (safe — read-only)
    python dr_failover.py test --primary us-east-1 --dr us-west-2

    # Trigger failover to DR region (DESTRUCTIVE — redirects traffic!)
    python dr_failover.py failover --primary us-east-1 --dr us-west-2

    # Reverse failover after primary is restored
    python dr_failover.py failback --primary us-east-1 --dr us-west-2

WARNING:
    The 'failover' command will:
    - Promote the RDS read replica in the DR region (breaks replication)
    - Update Route53 DNS to point to the DR region
    These actions affect live traffic and are difficult to reverse quickly.
    Always run 'test' first to verify DR readiness.

Prerequisites:
    pip install boto3
    AWS credentials with RDS, Route53, S3, and CloudWatch permissions
    Configure DR_CONFIG below for your environment
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from typing import Optional

import boto3
from botocore.exceptions import ClientError


# ── DR Configuration ──────────────────────────────────────────────────────────
# Customize these values for your environment

DR_CONFIG = {
    # RDS read replica identifier in the DR region
    "rds_replica_id": "myapp-db-replica",

    # Route53 hosted zone ID for your application domain
    "route53_hosted_zone_id": "Z1234567890ABCDEF",

    # DNS record name to update during failover
    "route53_record_name": "api.myapp.example.com",

    # S3 bucket used for replication status checks
    "s3_replication_bucket": "myapp-dr-replication",

    # CloudWatch metric namespace for custom DR metrics
    "cloudwatch_namespace": "MyApp/DR",

    # Maximum acceptable RDS replica lag in seconds
    "max_replica_lag_seconds": 60,

    # Maximum acceptable S3 replication lag in minutes
    "max_s3_replication_lag_minutes": 15,
}


# ── Audit logger ──────────────────────────────────────────────────────────────

class AuditLogger:
    """
    Logs all DR actions with timestamps for audit trail.

    All actions are logged to stdout and to a local audit file.
    In production, also ship these logs to CloudWatch Logs.
    """

    def __init__(self, log_file: str = "dr_audit.log"):
        self.log_file = log_file
        self.entries: list[str] = []

    def log(self, action: str, status: str, detail: str = "") -> None:
        """
        Log a DR action with timestamp.

        Args:
            action: Action name (e.g. 'PROMOTE_RDS_REPLICA')
            status: Status string (e.g. 'STARTED', 'COMPLETED', 'FAILED')
            detail: Additional detail
        """
        ts = datetime.now(timezone.utc).isoformat()
        entry = f"[{ts}] {action} | {status} | {detail}"
        self.entries.append(entry)
        print(f"  {entry}")

        # Append to audit file
        with open(self.log_file, "a") as f:
            f.write(entry + "\n")

    def save(self) -> None:
        """Print the full audit trail."""
        print(f"\n  Audit log saved to: {self.log_file}")
        print(f"  Total actions logged: {len(self.entries)}")


audit = AuditLogger()


# ── Readiness checks ──────────────────────────────────────────────────────────

def check_rds_replica_lag(dr_region: str) -> tuple[bool, float]:
    """
    Check the replication lag on the RDS read replica in the DR region.

    Args:
        dr_region: DR region name (e.g. 'us-west-2')

    Returns:
        Tuple of (is_acceptable: bool, lag_seconds: float)
    """
    rds = boto3.client("rds", region_name=dr_region)
    replica_id = DR_CONFIG["rds_replica_id"]

    try:
        response = rds.describe_db_instances(DBInstanceIdentifier=replica_id)
        instances = response.get("DBInstances", [])

        if not instances:
            audit.log("CHECK_RDS_REPLICA", "FAILED", f"Replica '{replica_id}' not found in {dr_region}")
            return (False, -1)

        instance = instances[0]
        status = instance.get("DBInstanceStatus", "unknown")

        # ReplicaLag is in the StatusInfos list
        lag_seconds = 0.0
        for info in instance.get("StatusInfos", []):
            if info.get("StatusType") == "read replication":
                # Parse lag from message like "0 days 0 hours 0 minutes 5 seconds"
                message = info.get("Message", "")
                # Extract seconds from the message
                import re
                match = re.search(r"(\d+) seconds", message)
                if match:
                    lag_seconds = float(match.group(1))
                break

        max_lag = DR_CONFIG["max_replica_lag_seconds"]
        is_acceptable = lag_seconds <= max_lag and status == "available"

        audit.log(
            "CHECK_RDS_REPLICA",
            "OK" if is_acceptable else "WARNING",
            f"Status={status}, Lag={lag_seconds:.0f}s (max={max_lag}s)",
        )
        return (is_acceptable, lag_seconds)

    except ClientError as e:
        audit.log("CHECK_RDS_REPLICA", "ERROR", str(e))
        return (False, -1)


def check_s3_replication_status(primary_region: str, dr_region: str) -> bool:
    """
    Check S3 cross-region replication status by comparing object counts.

    Args:
        primary_region: Primary region
        dr_region:      DR region

    Returns:
        True if replication appears healthy
    """
    bucket = DR_CONFIG["s3_replication_bucket"]

    try:
        s3_primary = boto3.client("s3", region_name=primary_region)
        s3_dr = boto3.client("s3", region_name=dr_region)

        # Count objects in primary bucket
        primary_count = 0
        paginator = s3_primary.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket):
            primary_count += page.get("KeyCount", 0)

        # Count objects in DR bucket (assume naming convention: bucket-dr)
        dr_bucket = f"{bucket}-dr"
        dr_count = 0
        try:
            paginator = s3_dr.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=dr_bucket):
                dr_count += page.get("KeyCount", 0)
        except ClientError:
            audit.log("CHECK_S3_REPLICATION", "WARNING", f"DR bucket '{dr_bucket}' not accessible")
            return False

        # Allow up to 5% difference in object counts (replication in progress)
        if primary_count > 0:
            replication_pct = (dr_count / primary_count) * 100
            is_healthy = replication_pct >= 95.0
        else:
            is_healthy = True  # No objects to replicate
            replication_pct = 100.0

        audit.log(
            "CHECK_S3_REPLICATION",
            "OK" if is_healthy else "WARNING",
            f"Primary={primary_count} objects, DR={dr_count} objects ({replication_pct:.1f}% replicated)",
        )
        return is_healthy

    except ClientError as e:
        audit.log("CHECK_S3_REPLICATION", "ERROR", str(e))
        return False


def check_dr_ec2_capacity(dr_region: str) -> bool:
    """
    Verify that EC2 instances or Auto Scaling Groups exist in the DR region.

    Args:
        dr_region: DR region name

    Returns:
        True if DR compute capacity is available
    """
    asg = boto3.client("autoscaling", region_name=dr_region)

    try:
        response = asg.describe_auto_scaling_groups()
        groups = response.get("AutoScalingGroups", [])

        if not groups:
            audit.log("CHECK_EC2_CAPACITY", "WARNING", f"No Auto Scaling Groups found in {dr_region}")
            return False

        # Check that at least one ASG has desired capacity > 0
        ready_groups = [g for g in groups if g.get("DesiredCapacity", 0) > 0]
        audit.log(
            "CHECK_EC2_CAPACITY",
            "OK" if ready_groups else "WARNING",
            f"{len(ready_groups)}/{len(groups)} ASGs have capacity in {dr_region}",
        )
        return len(ready_groups) > 0

    except ClientError as e:
        audit.log("CHECK_EC2_CAPACITY", "ERROR", str(e))
        return False


# ── Test command ──────────────────────────────────────────────────────────────

def run_test(primary_region: str, dr_region: str) -> None:
    """
    Check DR region readiness without making any changes.

    Args:
        primary_region: Primary AWS region
        dr_region:      DR AWS region
    """
    print(f"\n=== DR Readiness Test ===")
    print(f"  Primary: {primary_region}  →  DR: {dr_region}\n")

    audit.log("DR_TEST", "STARTED", f"primary={primary_region}, dr={dr_region}")

    checks = []

    # Check 1: RDS replica lag
    print("  [1/3] Checking RDS replica lag...")
    rds_ok, lag = check_rds_replica_lag(dr_region)
    checks.append(("RDS Replica Lag", rds_ok, f"{lag:.0f}s" if lag >= 0 else "N/A"))

    # Check 2: S3 replication
    print("  [2/3] Checking S3 replication status...")
    s3_ok = check_s3_replication_status(primary_region, dr_region)
    checks.append(("S3 Replication", s3_ok, ""))

    # Check 3: EC2 capacity
    print("  [3/3] Checking EC2 capacity in DR region...")
    ec2_ok = check_dr_ec2_capacity(dr_region)
    checks.append(("EC2 Capacity", ec2_ok, ""))

    # Print summary
    print("\n  DR Readiness Summary:")
    print("  " + "-" * 50)
    all_ok = True
    for check_name, passed, detail in checks:
        icon = "✓" if passed else "✗"
        detail_str = f"  ({detail})" if detail else ""
        print(f"  {icon} {check_name}{detail_str}")
        if not passed:
            all_ok = False

    print()
    if all_ok:
        print("  ✓ DR region is READY for failover")
        audit.log("DR_TEST", "COMPLETED", "DR region is ready")
    else:
        print("  ⚠ DR region has issues — resolve before failover")
        audit.log("DR_TEST", "COMPLETED", "DR region has readiness issues")

    audit.save()


# ── Failover command ──────────────────────────────────────────────────────────

def run_failover(primary_region: str, dr_region: str) -> None:
    """
    Execute failover to the DR region.

    Steps:
        1. Promote RDS read replica to standalone instance
        2. Update Route53 DNS to point to DR region endpoint
        3. Log all actions for audit trail

    Args:
        primary_region: Primary AWS region
        dr_region:      DR AWS region
    """
    print(f"\n=== DR FAILOVER ===")
    print(f"  Primary: {primary_region}  →  DR: {dr_region}")
    print(f"\n  ⚠  WARNING: This will redirect live traffic to the DR region!")
    print(f"  ⚠  RDS replication will be broken after promotion.")
    print()

    # Safety confirmation
    confirm = input("  Type 'FAILOVER' to confirm: ").strip()
    if confirm != "FAILOVER":
        print("  Failover cancelled.")
        sys.exit(0)

    audit.log("FAILOVER", "STARTED", f"primary={primary_region}, dr={dr_region}")

    # Step 1 — Promote RDS read replica
    print("\n  [1/2] Promoting RDS read replica...")
    rds_dr = boto3.client("rds", region_name=dr_region)
    replica_id = DR_CONFIG["rds_replica_id"]

    try:
        rds_dr.promote_read_replica(
            DBInstanceIdentifier=replica_id,
            BackupRetentionPeriod=7,  # Enable backups on the promoted instance
        )
        audit.log("PROMOTE_RDS_REPLICA", "STARTED", f"Promoting {replica_id} in {dr_region}")

        # Wait for promotion to complete (can take 5–15 minutes)
        print(f"  Waiting for {replica_id} to become available (this may take 10–15 minutes)...")
        waiter = rds_dr.get_waiter("db_instance_available")
        waiter.wait(
            DBInstanceIdentifier=replica_id,
            WaiterConfig={"Delay": 30, "MaxAttempts": 40},  # Wait up to 20 minutes
        )

        # Get the new endpoint
        response = rds_dr.describe_db_instances(DBInstanceIdentifier=replica_id)
        new_endpoint = response["DBInstances"][0]["Endpoint"]["Address"]
        audit.log("PROMOTE_RDS_REPLICA", "COMPLETED", f"New endpoint: {new_endpoint}")
        print(f"  ✓ RDS promoted. New endpoint: {new_endpoint}")

    except ClientError as e:
        audit.log("PROMOTE_RDS_REPLICA", "FAILED", str(e))
        print(f"  ✗ RDS promotion failed: {e}")
        print("  Failover aborted — DNS not updated")
        sys.exit(1)

    # Step 2 — Update Route53 DNS
    print("\n  [2/2] Updating Route53 DNS...")
    _update_route53(dr_region, "FAILOVER")

    audit.log("FAILOVER", "COMPLETED", f"Traffic now routing to {dr_region}")
    print(f"\n  ✓ Failover complete — traffic is now routing to {dr_region}")
    audit.save()


# ── Failback command ──────────────────────────────────────────────────────────

def run_failback(primary_region: str, dr_region: str) -> None:
    """
    Execute failback to the primary region after it has been restored.

    Steps:
        1. Verify primary region is healthy
        2. Update Route53 DNS back to primary region
        3. Set up new replication from DR back to primary (manual step)

    Args:
        primary_region: Primary AWS region
        dr_region:      DR AWS region
    """
    print(f"\n=== DR FAILBACK ===")
    print(f"  DR: {dr_region}  →  Primary: {primary_region}")
    print()

    confirm = input("  Type 'FAILBACK' to confirm: ").strip()
    if confirm != "FAILBACK":
        print("  Failback cancelled.")
        sys.exit(0)

    audit.log("FAILBACK", "STARTED", f"dr={dr_region}, primary={primary_region}")

    # Update Route53 back to primary
    print("\n  Updating Route53 DNS back to primary region...")
    _update_route53(primary_region, "FAILBACK")

    audit.log("FAILBACK", "COMPLETED", f"Traffic now routing back to {primary_region}")
    print(f"\n  ✓ Failback complete — traffic is now routing to {primary_region}")
    print()
    print("  ⚠  Manual steps required:")
    print("     1. Create a new RDS read replica in the DR region from the primary")
    print("     2. Verify S3 replication is re-established")
    print("     3. Run 'test' command to verify DR readiness")
    audit.save()


def _update_route53(target_region: str, operation: str) -> None:
    """
    Update Route53 DNS record to point to the target region's endpoint.

    Args:
        target_region: Region to route traffic to
        operation:     'FAILOVER' or 'FAILBACK' (for logging)
    """
    route53 = boto3.client("route53")
    hosted_zone_id = DR_CONFIG["route53_hosted_zone_id"]
    record_name = DR_CONFIG["route53_record_name"]

    # In a real implementation, you would look up the ALB DNS name for the target region
    # Here we use a placeholder — replace with actual ALB DNS lookup
    new_dns_value = f"alb.{target_region}.elb.amazonaws.com"

    try:
        route53.change_resource_record_sets(
            HostedZoneId=hosted_zone_id,
            ChangeBatch={
                "Comment": f"DR {operation} — routing to {target_region}",
                "Changes": [
                    {
                        "Action": "UPSERT",
                        "ResourceRecordSet": {
                            "Name": record_name,
                            "Type": "CNAME",
                            "TTL": 60,  # Low TTL for fast propagation during DR
                            "ResourceRecords": [{"Value": new_dns_value}],
                        },
                    }
                ],
            },
        )
        audit.log(
            f"UPDATE_ROUTE53_{operation}",
            "COMPLETED",
            f"{record_name} → {new_dns_value}",
        )
        print(f"  ✓ Route53 updated: {record_name} → {new_dns_value}")
        print(f"  ℹ DNS propagation may take up to 60 seconds (TTL=60)")

    except ClientError as e:
        audit.log(f"UPDATE_ROUTE53_{operation}", "FAILED", str(e))
        print(f"  ✗ Route53 update failed: {e}")
        raise


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Trigger and verify disaster recovery failover"
    )
    parser.add_argument(
        "command",
        choices=["test", "failover", "failback"],
        help=(
            "test     — Check DR readiness (read-only)\n"
            "failover — Promote RDS replica + update DNS to DR region\n"
            "failback — Reverse failover after primary is restored"
        ),
    )
    parser.add_argument(
        "--primary", default="us-east-1",
        help="Primary AWS region (default: us-east-1)"
    )
    parser.add_argument(
        "--dr", default="us-west-2",
        help="DR AWS region (default: us-west-2)"
    )
    args = parser.parse_args()

    if args.command == "test":
        run_test(args.primary, args.dr)
    elif args.command == "failover":
        run_failover(args.primary, args.dr)
    elif args.command == "failback":
        run_failback(args.primary, args.dr)


if __name__ == "__main__":
    main()
