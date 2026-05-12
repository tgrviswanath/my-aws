"""
chaos_simulator.py — Simulate failures to test application resilience.

⚠️  WARNING: Only run in non-production environments!
    This script intentionally disrupts AWS resources.
    All actions are logged for easy rollback.

Prerequisites:
    pip install boto3

IAM Permissions Required:
    ec2:DescribeInstances, ec2:StopInstances
    ec2:DescribeSecurityGroups, ec2:AuthorizeSecurityGroupIngress
    ec2:RevokeSecurityGroupIngress
    autoscaling:DescribeAutoScalingGroups
    rds:DescribeDBInstances, rds:RebootDBInstance

Usage:
    python chaos_simulator.py --action stop-ec2   --asg-name my-asg
    python chaos_simulator.py --action block-sg   --sg-id sg-xxxxxxxx
    python chaos_simulator.py --action simulate-db-fail --rds-id mydb
    python chaos_simulator.py --action restore    --rollback-file rollback_YYYYMMDD_HHMMSS.json

Actions:
    stop-ec2         Stop a random EC2 instance in an Auto Scaling Group
    block-sg         Add a DENY-all inbound rule to a security group
    simulate-db-fail Reboot an RDS instance to simulate a brief outage
    restore          Undo all changes using a rollback file
"""

import argparse
import json
import random
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import ClientError, NoCredentialsError


# ── Rollback log ──────────────────────────────────────────────────────────────

class RollbackLog:
    """
    Records every destructive action taken so they can be undone.
    Persists to a JSON file for safety (in case the script crashes).
    """

    def __init__(self):
        self.actions: list[dict[str, Any]] = []
        self.filename = f"rollback_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"

    def record(self, action_type: str, details: dict):
        """Record an action for later rollback."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action_type": action_type,
            "details": details,
        }
        self.actions.append(entry)
        self._save()
        print(f"  [LOG] Recorded rollback action: {action_type}")

    def _save(self):
        """Persist the rollback log to disk."""
        with open(self.filename, "w") as f:
            json.dump({"actions": self.actions}, f, indent=2)

    @classmethod
    def load(cls, filename: str) -> "RollbackLog":
        """Load a rollback log from a file."""
        log = cls()
        log.filename = filename
        with open(filename) as f:
            data = json.load(f)
        log.actions = data.get("actions", [])
        return log


# ── Action: stop-ec2 ──────────────────────────────────────────────────────────

def action_stop_ec2(ec2, autoscaling, asg_name: str, rollback: RollbackLog):
    """
    Stop a random running EC2 instance in the specified Auto Scaling Group.
    The ASG will detect the unhealthy instance and launch a replacement.
    """
    print(f"\n[*] Action: stop-ec2 | ASG: {asg_name}")
    print("    This simulates an unexpected instance failure.")

    # Get instances in the ASG
    try:
        response = autoscaling.describe_auto_scaling_groups(
            AutoScalingGroupNames=[asg_name]
        )
        groups = response.get("AutoScalingGroups", [])
        if not groups:
            print(f"  [ERROR] ASG '{asg_name}' not found.")
            return

        asg = groups[0]
        instances = [
            i for i in asg.get("Instances", [])
            if i["LifecycleState"] == "InService" and i["HealthStatus"] == "Healthy"
        ]

        if not instances:
            print("  [WARN] No healthy InService instances found in ASG.")
            return

        # Pick a random instance
        target = random.choice(instances)
        instance_id = target["InstanceId"]
        print(f"  [!] Stopping instance: {instance_id}")

        # Stop the instance
        ec2.stop_instances(InstanceIds=[instance_id])
        print(f"  [+] Stop command sent to {instance_id}")

        # Record for rollback
        rollback.record("stop-ec2", {
            "instance_id": instance_id,
            "asg_name": asg_name,
        })

        print(f"\n  Expected behavior:")
        print(f"    - ASG health check detects unhealthy instance (~2-3 min)")
        print(f"    - ASG terminates the stopped instance")
        print(f"    - ASG launches a replacement instance")
        print(f"    - ALB routes traffic away from the stopped instance")

    except ClientError as e:
        print(f"  [ERROR] {e}")


# ── Action: block-sg ──────────────────────────────────────────────────────────

# The CIDR we use to "block" traffic — a non-routable address range
# We add a rule that allows traffic from this range, then remove the
# real allow rules. In practice, the simplest approach is to add a
# restrictive rule and note the original rules for rollback.
BLOCK_CIDR = "192.0.2.0/24"   # TEST-NET-1 — never used in real traffic


def action_block_sg(ec2, sg_id: str, rollback: RollbackLog):
    """
    Simulate a security group misconfiguration by removing all inbound rules
    and replacing them with a rule that allows only from a non-routable CIDR.

    This simulates: "someone accidentally locked down the security group."
    """
    print(f"\n[*] Action: block-sg | Security Group: {sg_id}")
    print("    This simulates a security group misconfiguration.")

    try:
        response = ec2.describe_security_groups(GroupIds=[sg_id])
        sgs = response.get("SecurityGroups", [])
        if not sgs:
            print(f"  [ERROR] Security group {sg_id} not found.")
            return

        sg = sgs[0]
        original_ingress = sg.get("IpPermissions", [])

        if not original_ingress:
            print("  [WARN] Security group has no inbound rules — nothing to block.")
            return

        print(f"  [!] Removing {len(original_ingress)} inbound rule(s) from {sg_id}")

        # Save original rules for rollback
        rollback.record("block-sg", {
            "sg_id": sg_id,
            "original_ingress": original_ingress,
        })

        # Remove all existing inbound rules
        ec2.revoke_security_group_ingress(
            GroupId=sg_id,
            IpPermissions=original_ingress,
        )
        print(f"  [+] All inbound rules removed from {sg_id}")

        # Add a harmless rule (allows from non-routable CIDR — effectively blocks all)
        ec2.authorize_security_group_ingress(
            GroupId=sg_id,
            IpPermissions=[{
                "IpProtocol": "tcp",
                "FromPort": 80,
                "ToPort": 80,
                "IpRanges": [{"CidrIp": BLOCK_CIDR, "Description": "chaos-simulator-block"}],
            }],
        )
        print(f"  [+] Added restrictive rule (allows only from {BLOCK_CIDR})")

        print(f"\n  Expected behavior:")
        print(f"    - New connections to instances in this SG will be refused")
        print(f"    - ALB health checks will start failing (~30s)")
        print(f"    - ALB will mark targets as unhealthy")
        print(f"    - Run --action restore to undo this change")

    except ClientError as e:
        print(f"  [ERROR] {e}")


# ── Action: simulate-db-fail ──────────────────────────────────────────────────

def action_simulate_db_fail(rds, db_instance_id: str, rollback: RollbackLog):
    """
    Reboot an RDS instance to simulate a brief database outage.
    With Multi-AZ, this triggers a failover to the standby (~60s downtime).
    Without Multi-AZ, the instance reboots (~2-5 min downtime).
    """
    print(f"\n[*] Action: simulate-db-fail | RDS: {db_instance_id}")
    print("    This simulates a database failure/failover.")

    try:
        response = rds.describe_db_instances(DBInstanceIdentifier=db_instance_id)
        db_instances = response.get("DBInstances", [])
        if not db_instances:
            print(f"  [ERROR] RDS instance '{db_instance_id}' not found.")
            return

        db = db_instances[0]
        status = db["DBInstanceStatus"]
        multi_az = db.get("MultiAZ", False)
        engine = db["Engine"]

        if status != "available":
            print(f"  [WARN] RDS instance is '{status}' — expected 'available'.")
            return

        print(f"  Instance : {db_instance_id}")
        print(f"  Engine   : {engine}")
        print(f"  Multi-AZ : {'Yes (failover will occur)' if multi_az else 'No (reboot only)'}")

        # Record for rollback (RDS reboot is self-healing — no manual restore needed)
        rollback.record("simulate-db-fail", {
            "db_instance_id": db_instance_id,
            "multi_az": multi_az,
            "note": "RDS reboot is self-healing — no manual restore required",
        })

        # Reboot (with failover if Multi-AZ)
        rds.reboot_db_instance(
            DBInstanceIdentifier=db_instance_id,
            ForceFailover=multi_az,   # Trigger failover if Multi-AZ
        )

        print(f"  [+] Reboot initiated for {db_instance_id}")

        if multi_az:
            print(f"\n  Expected behavior (Multi-AZ failover):")
            print(f"    - DNS CNAME updated to standby (~60s)")
            print(f"    - Application connections will fail briefly")
            print(f"    - Connection pool should reconnect automatically")
        else:
            print(f"\n  Expected behavior (single-AZ reboot):")
            print(f"    - Instance unavailable for ~2-5 minutes")
            print(f"    - All connections dropped during reboot")
            print(f"    - Instance returns to 'available' automatically")

    except ClientError as e:
        print(f"  [ERROR] {e}")


# ── Action: restore ───────────────────────────────────────────────────────────

def action_restore(ec2, rollback_file: str):
    """
    Undo all changes recorded in a rollback file.
    Processes actions in reverse order (LIFO).
    """
    print(f"\n[*] Action: restore | Rollback file: {rollback_file}")

    if not Path(rollback_file).exists():
        print(f"  [ERROR] Rollback file not found: {rollback_file}")
        return

    rollback = RollbackLog.load(rollback_file)
    actions = list(reversed(rollback.actions))   # Undo in reverse order

    if not actions:
        print("  (No actions to undo)")
        return

    print(f"  Found {len(actions)} action(s) to undo.\n")

    for entry in actions:
        action_type = entry["action_type"]
        details = entry["details"]
        timestamp = entry["timestamp"]

        print(f"  Undoing: {action_type} (recorded at {timestamp})")

        if action_type == "stop-ec2":
            instance_id = details["instance_id"]
            try:
                ec2.start_instances(InstanceIds=[instance_id])
                print(f"  [+] Started instance: {instance_id}")
            except ClientError as e:
                print(f"  [WARN] Could not start {instance_id}: {e}")

        elif action_type == "block-sg":
            sg_id = details["sg_id"]
            original_ingress = details["original_ingress"]
            try:
                # Remove the block rule we added
                ec2.revoke_security_group_ingress(
                    GroupId=sg_id,
                    IpPermissions=[{
                        "IpProtocol": "tcp",
                        "FromPort": 80,
                        "ToPort": 80,
                        "IpRanges": [{"CidrIp": BLOCK_CIDR}],
                    }],
                )
                # Restore original rules
                ec2.authorize_security_group_ingress(
                    GroupId=sg_id,
                    IpPermissions=original_ingress,
                )
                print(f"  [+] Security group {sg_id} restored to original rules")
            except ClientError as e:
                print(f"  [WARN] Could not restore SG {sg_id}: {e}")

        elif action_type == "simulate-db-fail":
            print(f"  [INFO] RDS reboot is self-healing — no manual restore needed.")
            print(f"         Instance '{details['db_instance_id']}' will recover automatically.")

        else:
            print(f"  [WARN] Unknown action type: {action_type} — skipping")

    print(f"\n  [+] Restore complete.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Chaos simulator — test AWS resilience (NON-PRODUCTION ONLY).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python chaos_simulator.py --action stop-ec2 --asg-name my-asg
  python chaos_simulator.py --action block-sg --sg-id sg-0abc123
  python chaos_simulator.py --action simulate-db-fail --rds-id mydb
  python chaos_simulator.py --action restore --rollback-file rollback_20240101_120000.json
        """,
    )
    parser.add_argument(
        "--action",
        required=True,
        choices=["stop-ec2", "block-sg", "simulate-db-fail", "restore"],
        help="Chaos action to perform",
    )
    parser.add_argument("--asg-name",      help="Auto Scaling Group name (for stop-ec2)")
    parser.add_argument("--sg-id",         help="Security Group ID (for block-sg)")
    parser.add_argument("--rds-id",        help="RDS instance ID (for simulate-db-fail)")
    parser.add_argument("--rollback-file", help="Rollback JSON file (for restore)")
    parser.add_argument("--profile",       help="AWS profile name", default=None)
    parser.add_argument("--region",        help="AWS region",       default="us-east-1")
    parser.add_argument("--yes",           action="store_true",
                        help="Skip confirmation prompt")
    args = parser.parse_args()

    # Safety confirmation
    if args.action != "restore" and not args.yes:
        print("\n" + "=" * 60)
        print("  ⚠️  CHAOS SIMULATOR — DESTRUCTIVE ACTION")
        print("=" * 60)
        print(f"  Action : {args.action}")
        print(f"  Region : {args.region}")
        print("\n  This will intentionally disrupt AWS resources.")
        print("  Only run in non-production environments!\n")
        confirm = input("  Type 'yes' to continue: ").strip().lower()
        if confirm != "yes":
            print("  Aborted.")
            sys.exit(0)

    try:
        session = boto3.Session(profile_name=args.profile, region_name=args.region)
        ec2 = session.client("ec2")
        autoscaling = session.client("autoscaling")
        rds = session.client("rds")
    except NoCredentialsError:
        print("[ERROR] No AWS credentials found. Run 'aws configure'.")
        sys.exit(1)

    rollback = RollbackLog()

    print("\n" + "=" * 60)
    print("  Chaos Simulator")
    print("=" * 60)

    if args.action == "stop-ec2":
        if not args.asg_name:
            parser.error("--asg-name is required for stop-ec2")
        action_stop_ec2(ec2, autoscaling, args.asg_name, rollback)

    elif args.action == "block-sg":
        if not args.sg_id:
            parser.error("--sg-id is required for block-sg")
        action_block_sg(ec2, args.sg_id, rollback)

    elif args.action == "simulate-db-fail":
        if not args.rds_id:
            parser.error("--rds-id is required for simulate-db-fail")
        action_simulate_db_fail(rds, args.rds_id, rollback)

    elif args.action == "restore":
        if not args.rollback_file:
            parser.error("--rollback-file is required for restore")
        action_restore(ec2, args.rollback_file)

    if args.action != "restore" and rollback.actions:
        print(f"\n  [+] Rollback file saved: {rollback.filename}")
        print(f"      To undo: python chaos_simulator.py --action restore --rollback-file {rollback.filename}")

    print()


if __name__ == "__main__":
    main()
