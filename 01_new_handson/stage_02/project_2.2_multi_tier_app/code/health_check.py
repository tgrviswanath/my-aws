"""
health_check.py — Check health of all tiers in the multi-tier application.

Prerequisites:
    pip install boto3

IAM Permissions Required:
    elasticloadbalancing:DescribeTargetGroups
    elasticloadbalancing:DescribeTargetHealth
    elasticloadbalancing:DescribeLoadBalancers
    ec2:DescribeInstances, ec2:DescribeInstanceStatus
    rds:DescribeDBInstances

Usage:
    python health_check.py [--profile <profile>] [--region <region>]
                           [--alb-arn <arn>] [--rds-id <db-instance-id>]

What this script checks:
    Tier 1 — Load Balancer : ALB state, listener count
    Tier 2 — Application   : EC2 instance status, target group health
    Tier 3 — Database      : RDS instance status, availability
"""

import argparse
import sys
from typing import Any

import boto3
from botocore.exceptions import ClientError, NoCredentialsError


# ── Status icons ──────────────────────────────────────────────────────────────
ICON_OK   = "✅"
ICON_WARN = "⚠️ "
ICON_FAIL = "❌"


def status_icon(condition: bool, warn_condition: bool = False) -> str:
    """Return a status icon based on health condition."""
    if condition:
        return ICON_OK
    if warn_condition:
        return ICON_WARN
    return ICON_FAIL


# ── Tier 1: ALB health ────────────────────────────────────────────────────────

def check_alb(elbv2, alb_arn: str | None) -> dict[str, Any]:
    """
    Check ALB state and listener configuration.
    If alb_arn is None, lists all ALBs in the account.
    """
    print("\n── Tier 1: Application Load Balancer ───────────────────────────")

    results = {"healthy": True, "albs": []}

    try:
        kwargs = {}
        if alb_arn:
            kwargs["LoadBalancerArns"] = [alb_arn]

        response = elbv2.describe_load_balancers(**kwargs)
        lbs = response.get("LoadBalancers", [])

        if not lbs:
            print("  [WARN] No load balancers found.")
            results["healthy"] = False
            return results

        for lb in lbs:
            lb_name = lb["LoadBalancerName"]
            lb_arn_val = lb["LoadBalancerArn"]
            state = lb["State"]["Code"]
            dns = lb["DNSName"]
            lb_type = lb["Type"]

            is_active = state == "active"
            icon = status_icon(is_active)

            print(f"  {icon} {lb_name} ({lb_type})")
            print(f"      State : {state}")
            print(f"      DNS   : {dns}")

            # Check listeners
            try:
                listeners = elbv2.describe_listeners(LoadBalancerArn=lb_arn_val)
                listener_count = len(listeners.get("Listeners", []))
                print(f"      Listeners: {listener_count}")
                for listener in listeners.get("Listeners", []):
                    port = listener["Port"]
                    protocol = listener["Protocol"]
                    print(f"        - {protocol}:{port}")
            except ClientError:
                print("      Listeners: (unable to fetch)")

            if not is_active:
                results["healthy"] = False

            results["albs"].append({
                "name": lb_name,
                "arn": lb_arn_val,
                "state": state,
                "dns": dns,
            })

    except ClientError as e:
        print(f"  [ERROR] Failed to describe load balancers: {e}")
        results["healthy"] = False

    return results


# ── Tier 1b: Target group health ──────────────────────────────────────────────

def check_target_groups(elbv2, alb_arn: str | None) -> dict[str, Any]:
    """Check target group health for all targets."""
    print("\n── Target Group Health ─────────────────────────────────────────")

    results = {"healthy": True, "groups": []}

    try:
        kwargs = {}
        if alb_arn:
            kwargs["LoadBalancerArn"] = alb_arn

        response = elbv2.describe_target_groups(**kwargs)
        tgs = response.get("TargetGroups", [])

        if not tgs:
            print("  [WARN] No target groups found.")
            return results

        for tg in tgs:
            tg_name = tg["TargetGroupName"]
            tg_arn = tg["TargetGroupArn"]
            protocol = tg.get("Protocol", "N/A")
            port = tg.get("Port", "N/A")

            # Get target health
            health_response = elbv2.describe_target_health(TargetGroupArn=tg_arn)
            targets = health_response.get("TargetHealthDescriptions", [])

            healthy_count = sum(
                1 for t in targets
                if t["TargetHealth"]["State"] == "healthy"
            )
            total_count = len(targets)
            all_healthy = healthy_count == total_count and total_count > 0

            icon = status_icon(all_healthy, warn_condition=(healthy_count > 0))
            print(f"\n  {icon} {tg_name} ({protocol}:{port})")
            print(f"      Healthy: {healthy_count}/{total_count}")

            for target in targets:
                target_id = target["Target"]["Id"]
                target_port = target["Target"].get("Port", port)
                state = target["TargetHealth"]["State"]
                reason = target["TargetHealth"].get("Description", "")
                t_icon = status_icon(state == "healthy")
                print(f"      {t_icon} {target_id}:{target_port} — {state} {reason}")

            if not all_healthy:
                results["healthy"] = False

            results["groups"].append({
                "name": tg_name,
                "healthy": healthy_count,
                "total": total_count,
            })

    except ClientError as e:
        print(f"  [ERROR] Failed to describe target groups: {e}")
        results["healthy"] = False

    return results


# ── Tier 2: EC2 instance health ───────────────────────────────────────────────

def check_ec2_instances(ec2) -> dict[str, Any]:
    """Check EC2 instance status checks."""
    print("\n── Tier 2: EC2 Instances ───────────────────────────────────────")

    results = {"healthy": True, "instances": []}

    try:
        # Get all running instances
        response = ec2.describe_instances(
            Filters=[{"Name": "instance-state-name", "Values": ["running", "stopped", "pending"]}]
        )

        instances = []
        for reservation in response.get("Reservations", []):
            instances.extend(reservation.get("Instances", []))

        if not instances:
            print("  [WARN] No EC2 instances found.")
            return results

        # Get status checks
        instance_ids = [i["InstanceId"] for i in instances]
        status_response = ec2.describe_instance_status(
            InstanceIds=instance_ids,
            IncludeAllInstances=True,
        )
        status_map = {
            s["InstanceId"]: s
            for s in status_response.get("InstanceStatuses", [])
        }

        for instance in instances:
            instance_id = instance["InstanceId"]
            state = instance["State"]["Name"]
            instance_type = instance["InstanceType"]
            az = instance["Placement"]["AvailabilityZone"]
            name = ""
            for tag in instance.get("Tags", []):
                if tag["Key"] == "Name":
                    name = tag["Value"]
                    break

            status = status_map.get(instance_id, {})
            system_status = status.get("SystemStatus", {}).get("Status", "unknown")
            instance_status = status.get("InstanceStatus", {}).get("Status", "unknown")

            is_healthy = (
                state == "running" and
                system_status == "ok" and
                instance_status == "ok"
            )
            icon = status_icon(is_healthy, warn_condition=(state == "running"))

            print(f"  {icon} {instance_id} ({name or 'unnamed'})")
            print(f"      Type   : {instance_type} | AZ: {az}")
            print(f"      State  : {state}")
            print(f"      System : {system_status} | Instance: {instance_status}")

            if not is_healthy:
                results["healthy"] = False

            results["instances"].append({
                "id": instance_id,
                "name": name,
                "state": state,
                "healthy": is_healthy,
            })

    except ClientError as e:
        print(f"  [ERROR] Failed to describe EC2 instances: {e}")
        results["healthy"] = False

    return results


# ── Tier 3: RDS health ────────────────────────────────────────────────────────

def check_rds(rds, db_instance_id: str | None) -> dict[str, Any]:
    """Check RDS instance status."""
    print("\n── Tier 3: RDS Database ────────────────────────────────────────")

    results = {"healthy": True, "instances": []}

    try:
        kwargs = {}
        if db_instance_id:
            kwargs["DBInstanceIdentifier"] = db_instance_id

        response = rds.describe_db_instances(**kwargs)
        db_instances = response.get("DBInstances", [])

        if not db_instances:
            print("  [WARN] No RDS instances found.")
            return results

        for db in db_instances:
            db_id = db["DBInstanceIdentifier"]
            status = db["DBInstanceStatus"]
            engine = db["Engine"]
            engine_version = db["EngineVersion"]
            instance_class = db["DBInstanceClass"]
            multi_az = db.get("MultiAZ", False)
            endpoint = db.get("Endpoint", {}).get("Address", "N/A")
            port = db.get("Endpoint", {}).get("Port", "N/A")

            is_available = status == "available"
            icon = status_icon(is_available)

            print(f"  {icon} {db_id}")
            print(f"      Status   : {status}")
            print(f"      Engine   : {engine} {engine_version}")
            print(f"      Class    : {instance_class}")
            print(f"      Multi-AZ : {'Yes' if multi_az else 'No'}")
            print(f"      Endpoint : {endpoint}:{port}")

            if not multi_az:
                print(f"  {ICON_WARN} Single-AZ deployment — consider Multi-AZ for production")

            if not is_available:
                results["healthy"] = False

            results["instances"].append({
                "id": db_id,
                "status": status,
                "healthy": is_available,
                "multi_az": multi_az,
            })

    except ClientError as e:
        print(f"  [ERROR] Failed to describe RDS instances: {e}")
        results["healthy"] = False

    return results


# ── Summary report ────────────────────────────────────────────────────────────

def print_summary(alb_result, tg_result, ec2_result, rds_result):
    """Print overall health report."""
    all_healthy = all([
        alb_result["healthy"],
        tg_result["healthy"],
        ec2_result["healthy"],
        rds_result["healthy"],
    ])

    overall_icon = ICON_OK if all_healthy else ICON_FAIL
    overall_text = "ALL SYSTEMS HEALTHY" if all_healthy else "ISSUES DETECTED"

    print("\n" + "=" * 60)
    print(f"  {overall_icon} Overall Health: {overall_text}")
    print("=" * 60)
    print(f"  {status_icon(alb_result['healthy'])} Tier 1 — Load Balancer : {'OK' if alb_result['healthy'] else 'DEGRADED'}")
    print(f"  {status_icon(tg_result['healthy'])}  Tier 1 — Target Groups : {'OK' if tg_result['healthy'] else 'DEGRADED'}")
    print(f"  {status_icon(ec2_result['healthy'])} Tier 2 — EC2 Instances : {'OK' if ec2_result['healthy'] else 'DEGRADED'}")
    print(f"  {status_icon(rds_result['healthy'])} Tier 3 — RDS Database  : {'OK' if rds_result['healthy'] else 'DEGRADED'}")
    print("=" * 60 + "\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Multi-tier app health checker.")
    parser.add_argument("--profile", help="AWS profile name", default=None)
    parser.add_argument("--region",  help="AWS region",       default="us-east-1")
    parser.add_argument("--alb-arn", help="ALB ARN (optional — checks all if omitted)", default=None)
    parser.add_argument("--rds-id",  help="RDS instance ID (optional)", default=None)
    args = parser.parse_args()

    try:
        session = boto3.Session(profile_name=args.profile, region_name=args.region)
        elbv2 = session.client("elbv2")
        ec2   = session.client("ec2")
        rds   = session.client("rds")
    except NoCredentialsError:
        print("[ERROR] No AWS credentials found. Run 'aws configure'.")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("  Multi-Tier Application Health Check")
    print("=" * 60)

    alb_result = check_alb(elbv2, args.alb_arn)
    tg_result  = check_target_groups(elbv2, args.alb_arn)
    ec2_result = check_ec2_instances(ec2)
    rds_result = check_rds(rds, args.rds_id)

    print_summary(alb_result, tg_result, ec2_result, rds_result)


if __name__ == "__main__":
    main()
