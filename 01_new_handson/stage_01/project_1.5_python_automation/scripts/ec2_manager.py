"""
ec2_manager.py — Manage EC2 instances using boto3
Usage:
  python ec2_manager.py list
  python ec2_manager.py stop  --instance-id i-XXXXXXXXXX
  python ec2_manager.py start --instance-id i-XXXXXXXXXX
  python ec2_manager.py stop-tagged --tag-key Environment --tag-value learning
"""

import argparse
import boto3
from botocore.exceptions import ClientError


def get_ec2_client():
    return boto3.client("ec2", region_name="us-east-1")


def list_instances() -> None:
    ec2 = get_ec2_client()
    paginator = ec2.get_paginator("describe_instances")

    print(f"\n{'Instance ID':<22} {'Type':<14} {'State':<12} {'Public IP':<16} {'Name'}")
    print("-" * 80)

    for page in paginator.paginate():
        for reservation in page["Reservations"]:
            for instance in reservation["Instances"]:
                name = next(
                    (tag["Value"] for tag in instance.get("Tags", []) if tag["Key"] == "Name"),
                    "(no name)"
                )
                public_ip = instance.get("PublicIpAddress", "-")
                print(
                    f"{instance['InstanceId']:<22} "
                    f"{instance['InstanceType']:<14} "
                    f"{instance['State']['Name']:<12} "
                    f"{public_ip:<16} "
                    f"{name}"
                )


def stop_instance(instance_id: str) -> None:
    ec2 = get_ec2_client()
    try:
        response = ec2.stop_instances(InstanceIds=[instance_id])
        state = response["StoppingInstances"][0]["CurrentState"]["Name"]
        print(f"✅ Instance {instance_id} is now: {state}")
    except ClientError as e:
        print(f"❌ Failed to stop {instance_id}: {e}")


def start_instance(instance_id: str) -> None:
    ec2 = get_ec2_client()
    try:
        response = ec2.start_instances(InstanceIds=[instance_id])
        state = response["StartingInstances"][0]["CurrentState"]["Name"]
        print(f"✅ Instance {instance_id} is now: {state}")
    except ClientError as e:
        print(f"❌ Failed to start {instance_id}: {e}")


def stop_tagged_instances(tag_key: str, tag_value: str) -> None:
    ec2 = get_ec2_client()
    response = ec2.describe_instances(
        Filters=[
            {"Name": f"tag:{tag_key}", "Values": [tag_value]},
            {"Name": "instance-state-name", "Values": ["running"]}
        ]
    )

    instance_ids = [
        instance["InstanceId"]
        for reservation in response["Reservations"]
        for instance in reservation["Instances"]
    ]

    if not instance_ids:
        print(f"No running instances found with tag {tag_key}={tag_value}")
        return

    print(f"Stopping {len(instance_ids)} instances: {instance_ids}")
    ec2.stop_instances(InstanceIds=instance_ids)
    print("✅ Stop command sent")


def main():
    parser = argparse.ArgumentParser(description="EC2 instance manager")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("list")

    stop_parser = subparsers.add_parser("stop")
    stop_parser.add_argument("--instance-id", required=True)

    start_parser = subparsers.add_parser("start")
    start_parser.add_argument("--instance-id", required=True)

    tagged_parser = subparsers.add_parser("stop-tagged")
    tagged_parser.add_argument("--tag-key", required=True)
    tagged_parser.add_argument("--tag-value", required=True)

    args = parser.parse_args()

    if args.command == "list":
        list_instances()
    elif args.command == "stop":
        stop_instance(args.instance_id)
    elif args.command == "start":
        start_instance(args.instance_id)
    elif args.command == "stop-tagged":
        stop_tagged_instances(args.tag_key, args.tag_value)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
