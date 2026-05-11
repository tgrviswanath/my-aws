"""
cost_optimizer.py — AWS cost optimization automation.
Identifies and optionally stops/deletes idle/unused resources.

Run modes:
  --dry-run   : report only, no changes
  --apply     : make changes
"""

import argparse
from datetime import datetime, timedelta, timezone
from typing import List, Dict

import boto3

ec2 = boto3.client("ec2", region_name="us-east-1")
cw  = boto3.client("cloudwatch", region_name="us-east-1")


# ─── Find Idle EC2 Instances ──────────────────────────────────────────────────

def find_idle_ec2(cpu_threshold: float = 5.0, days: int = 7) -> List[Dict]:
    """Find EC2 instances with average CPU < threshold for the past N days."""
    response = ec2.describe_instances(
        Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
    )

    idle = []
    end_time   = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=days)

    for reservation in response["Reservations"]:
        for instance in reservation["Instances"]:
            instance_id = instance["InstanceId"]
            name = next(
                (t["Value"] for t in instance.get("Tags", []) if t["Key"] == "Name"),
                "(no name)"
            )

            # Get average CPU utilization
            metrics = cw.get_metric_statistics(
                Namespace="AWS/EC2",
                MetricName="CPUUtilization",
                Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=86400,
                Statistics=["Average"],
            )

            if not metrics["Datapoints"]:
                continue

            avg_cpu = sum(d["Average"] for d in metrics["Datapoints"]) / len(metrics["Datapoints"])

            if avg_cpu < cpu_threshold:
                idle.append({
                    "instance_id":   instance_id,
                    "name":          name,
                    "instance_type": instance["InstanceType"],
                    "avg_cpu":       round(avg_cpu, 2),
                    "launch_time":   instance["LaunchTime"].isoformat(),
                })

    return idle


# ─── Find Unattached EBS Volumes ──────────────────────────────────────────────

def find_unattached_ebs() -> List[Dict]:
    """Find EBS volumes not attached to any instance."""
    response = ec2.describe_volumes(
        Filters=[{"Name": "status", "Values": ["available"]}]
    )

    unattached = []
    for volume in response["Volumes"]:
        name = next(
            (t["Value"] for t in volume.get("Tags", []) if t["Key"] == "Name"),
            "(no name)"
        )
        unattached.append({
            "volume_id":   volume["VolumeId"],
            "name":        name,
            "size_gb":     volume["Size"],
            "volume_type": volume["VolumeType"],
            "created":     volume["CreateTime"].isoformat(),
            "monthly_cost": round(volume["Size"] * 0.10, 2),  # ~$0.10/GB for gp2
        })

    return unattached


# ─── Find Old Snapshots ───────────────────────────────────────────────────────

def find_old_snapshots(days: int = 30) -> List[Dict]:
    """Find EBS snapshots older than N days."""
    account_id = boto3.client("sts").get_caller_identity()["Account"]
    response   = ec2.describe_snapshots(OwnerIds=[account_id])

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    old    = []

    for snap in response["Snapshots"]:
        if snap["StartTime"] < cutoff:
            old.append({
                "snapshot_id": snap["SnapshotId"],
                "size_gb":     snap["VolumeSize"],
                "created":     snap["StartTime"].isoformat(),
                "description": snap.get("Description", ""),
                "monthly_cost": round(snap["VolumeSize"] * 0.05, 2),
            })

    return old


# ─── Report ───────────────────────────────────────────────────────────────────

def print_report(dry_run: bool = True) -> None:
    print(f"\n{'='*60}")
    print(f"AWS Cost Optimization Report — {datetime.now().strftime('%Y-%m-%d')}")
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'APPLY (making changes)'}")
    print(f"{'='*60}\n")

    # Idle EC2
    idle_ec2 = find_idle_ec2()
    print(f"🖥️  Idle EC2 Instances (CPU < 5% for 7 days): {len(idle_ec2)}")
    for i in idle_ec2:
        print(f"   {i['instance_id']} ({i['name']}) — {i['instance_type']} — avg CPU: {i['avg_cpu']}%")
        if not dry_run:
            ec2.stop_instances(InstanceIds=[i["instance_id"]])
            print(f"   ✅ Stopped {i['instance_id']}")

    # Unattached EBS
    unattached = find_unattached_ebs()
    total_ebs_cost = sum(v["monthly_cost"] for v in unattached)
    print(f"\n💾 Unattached EBS Volumes: {len(unattached)} (${total_ebs_cost:.2f}/month)")
    for v in unattached:
        print(f"   {v['volume_id']} ({v['name']}) — {v['size_gb']} GB — ${v['monthly_cost']}/month")

    # Old snapshots
    old_snaps = find_old_snapshots(days=30)
    total_snap_cost = sum(s["monthly_cost"] for s in old_snaps)
    print(f"\n📸 Old Snapshots (> 30 days): {len(old_snaps)} (${total_snap_cost:.2f}/month)")
    for s in old_snaps[:5]:  # show first 5
        print(f"   {s['snapshot_id']} — {s['size_gb']} GB — created {s['created'][:10]}")

    total_savings = total_ebs_cost + total_snap_cost
    print(f"\n💰 Potential monthly savings: ${total_savings:.2f}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Apply changes (default: dry run)")
    args = parser.parse_args()
    print_report(dry_run=not args.apply)
