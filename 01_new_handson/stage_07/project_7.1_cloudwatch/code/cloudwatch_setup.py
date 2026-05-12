"""
cloudwatch_setup.py — Set up CloudWatch monitoring: alarms, dashboards, log groups.

Usage:
    python cloudwatch_setup.py --ec2-id i-xxxxxxxx --sns-arn arn:aws:sns:us-east-1:123456789012:alerts

What this script does:
    1. Creates a CPU utilization alarm (>80% for 5 min → SNS alert)
    2. Creates a memory utilization alarm using a custom metric
    3. Creates a CloudWatch dashboard with EC2 + RDS widgets
    4. Creates a log group with 30-day retention policy
    5. Prints all created resource ARNs

Prerequisites:
    pip install boto3
    AWS credentials configured (aws configure or IAM role)
"""

import argparse
import json
import boto3
from botocore.exceptions import ClientError


# ── AWS clients ──────────────────────────────────────────────────────────────
cloudwatch = boto3.client("cloudwatch")
logs = boto3.client("logs")


# ── 1. CPU Alarm ─────────────────────────────────────────────────────────────

def create_cpu_alarm(ec2_instance_id: str, sns_arn: str) -> str:
    """
    Create a CloudWatch alarm that fires when EC2 CPU > 80% for 5 consecutive minutes.

    Args:
        ec2_instance_id: The EC2 instance ID to monitor (e.g. 'i-0abc123def456')
        sns_arn:         SNS topic ARN to notify when alarm triggers

    Returns:
        The alarm name (CloudWatch alarms are identified by name, not ARN)
    """
    alarm_name = f"HighCPU-{ec2_instance_id}"

    cloudwatch.put_metric_alarm(
        AlarmName=alarm_name,
        AlarmDescription=f"CPU utilization > 80% for 5 minutes on {ec2_instance_id}",
        ActionsEnabled=True,
        AlarmActions=[sns_arn],          # Notify this SNS topic when alarm triggers
        OKActions=[sns_arn],             # Also notify when alarm recovers
        MetricName="CPUUtilization",
        Namespace="AWS/EC2",
        Statistic="Average",
        Dimensions=[
            {"Name": "InstanceId", "Value": ec2_instance_id}
        ],
        Period=300,          # Evaluate every 5 minutes (300 seconds)
        EvaluationPeriods=1, # Trigger after 1 consecutive breach period
        Threshold=80.0,
        ComparisonOperator="GreaterThanThreshold",
        TreatMissingData="notBreaching",  # Don't alarm if no data (instance stopped)
    )

    print(f"  ✓ CPU alarm created: {alarm_name}")
    return alarm_name


# ── 2. Memory Alarm (custom metric) ──────────────────────────────────────────

def publish_sample_memory_metric(ec2_instance_id: str) -> None:
    """
    Publish a sample custom memory metric so the alarm has data to evaluate.

    In production, the CloudWatch Agent on the EC2 instance publishes this metric
    automatically. This function is only for demonstration / testing purposes.

    Args:
        ec2_instance_id: EC2 instance ID used as a dimension value
    """
    cloudwatch.put_metric_data(
        Namespace="CWAgent",   # Namespace used by the CloudWatch Agent
        MetricData=[
            {
                "MetricName": "mem_used_percent",
                "Dimensions": [
                    {"Name": "InstanceId", "Value": ec2_instance_id},
                    {"Name": "ImageId",    "Value": "ami-unknown"},
                    {"Name": "InstanceType", "Value": "t3.micro"},
                ],
                "Value": 45.0,   # Sample value: 45% memory used
                "Unit": "Percent",
            }
        ],
    )
    print("  ✓ Sample memory metric published to CWAgent namespace")


def create_memory_alarm(ec2_instance_id: str, sns_arn: str) -> str:
    """
    Create a CloudWatch alarm for memory utilization > 85%.

    This uses the custom metric published by the CloudWatch Agent (namespace: CWAgent).
    The agent must be installed and configured on the EC2 instance for real data.

    Args:
        ec2_instance_id: EC2 instance ID
        sns_arn:         SNS topic ARN for notifications

    Returns:
        The alarm name
    """
    alarm_name = f"HighMemory-{ec2_instance_id}"

    cloudwatch.put_metric_alarm(
        AlarmName=alarm_name,
        AlarmDescription=f"Memory utilization > 85% on {ec2_instance_id}",
        ActionsEnabled=True,
        AlarmActions=[sns_arn],
        OKActions=[sns_arn],
        MetricName="mem_used_percent",
        Namespace="CWAgent",             # Custom namespace from CloudWatch Agent
        Statistic="Average",
        Dimensions=[
            {"Name": "InstanceId",   "Value": ec2_instance_id},
            {"Name": "ImageId",      "Value": "ami-unknown"},
            {"Name": "InstanceType", "Value": "t3.micro"},
        ],
        Period=300,
        EvaluationPeriods=2,   # Require 2 consecutive breaches (10 min) to reduce noise
        Threshold=85.0,
        ComparisonOperator="GreaterThanThreshold",
        TreatMissingData="missing",
    )

    print(f"  ✓ Memory alarm created: {alarm_name}")
    return alarm_name


# ── 3. CloudWatch Dashboard ───────────────────────────────────────────────────

def create_dashboard(ec2_instance_id: str, dashboard_name: str = "AppMonitoring") -> str:
    """
    Create a CloudWatch dashboard with EC2 CPU, memory, and RDS widgets.

    Dashboard layout (3 widgets):
        [0,0] EC2 CPU Utilization  (line chart, 6 hours)
        [0,6] EC2 Memory Usage     (line chart, 6 hours)
        [0,12] RDS DB Connections  (line chart, 6 hours)

    Args:
        ec2_instance_id: EC2 instance ID for the EC2 widgets
        dashboard_name:  Name for the CloudWatch dashboard

    Returns:
        Dashboard ARN
    """
    # Dashboard body is a JSON string describing widget layout
    dashboard_body = {
        "widgets": [
            # ── Widget 1: EC2 CPU ──────────────────────────────────────────
            {
                "type": "metric",
                "x": 0, "y": 0, "width": 8, "height": 6,
                "properties": {
                    "title": "EC2 CPU Utilization",
                    "metrics": [
                        ["AWS/EC2", "CPUUtilization",
                         "InstanceId", ec2_instance_id,
                         {"stat": "Average", "period": 300}]
                    ],
                    "view": "timeSeries",
                    "period": 300,
                    "yAxis": {"left": {"min": 0, "max": 100}},
                    "annotations": {
                        "horizontal": [
                            {"label": "Alarm threshold", "value": 80, "color": "#ff0000"}
                        ]
                    },
                },
            },
            # ── Widget 2: EC2 Memory (custom metric) ──────────────────────
            {
                "type": "metric",
                "x": 8, "y": 0, "width": 8, "height": 6,
                "properties": {
                    "title": "EC2 Memory Utilization",
                    "metrics": [
                        ["CWAgent", "mem_used_percent",
                         "InstanceId", ec2_instance_id,
                         "ImageId", "ami-unknown",
                         "InstanceType", "t3.micro",
                         {"stat": "Average", "period": 300}]
                    ],
                    "view": "timeSeries",
                    "period": 300,
                    "yAxis": {"left": {"min": 0, "max": 100}},
                },
            },
            # ── Widget 3: RDS DB Connections ───────────────────────────────
            {
                "type": "metric",
                "x": 16, "y": 0, "width": 8, "height": 6,
                "properties": {
                    "title": "RDS Database Connections",
                    "metrics": [
                        # Replace 'mydb' with your actual RDS instance identifier
                        ["AWS/RDS", "DatabaseConnections",
                         "DBInstanceIdentifier", "mydb",
                         {"stat": "Average", "period": 300}]
                    ],
                    "view": "timeSeries",
                    "period": 300,
                },
            },
        ]
    }

    response = cloudwatch.put_dashboard(
        DashboardName=dashboard_name,
        DashboardBody=json.dumps(dashboard_body),
    )

    # Derive the dashboard ARN from the response metadata
    region = boto3.session.Session().region_name or "us-east-1"
    account_id = boto3.client("sts").get_caller_identity()["Account"]
    dashboard_arn = f"arn:aws:cloudwatch::{account_id}:dashboard/{dashboard_name}"

    print(f"  ✓ Dashboard created: {dashboard_name}")
    print(f"    Validation messages: {response.get('DashboardValidationMessages', [])}")
    return dashboard_arn


# ── 4. Log Group ──────────────────────────────────────────────────────────────

def create_log_group(log_group_name: str = "/app/myservice", retention_days: int = 30) -> str:
    """
    Create a CloudWatch Logs log group with a retention policy.

    Args:
        log_group_name: Name of the log group (e.g. '/app/myservice')
        retention_days: How many days to retain log data (default: 30)

    Returns:
        Log group ARN
    """
    # Create the log group (idempotent — safe to call if it already exists)
    try:
        logs.create_log_group(logGroupName=log_group_name)
        print(f"  ✓ Log group created: {log_group_name}")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceAlreadyExistsException":
            print(f"  ℹ Log group already exists: {log_group_name}")
        else:
            raise

    # Apply retention policy (overrides any existing policy)
    logs.put_retention_policy(
        logGroupName=log_group_name,
        retentionInDays=retention_days,
    )
    print(f"  ✓ Retention policy set: {retention_days} days")

    # Fetch the ARN from the describe response
    response = logs.describe_log_groups(logGroupNamePrefix=log_group_name)
    for group in response.get("logGroups", []):
        if group["logGroupName"] == log_group_name:
            return group.get("arn", "arn-not-available")

    return "arn-not-available"


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Set up CloudWatch monitoring: alarms, dashboard, log group"
    )
    parser.add_argument(
        "--ec2-id", required=True,
        help="EC2 instance ID to monitor (e.g. i-0abc123def456789a)"
    )
    parser.add_argument(
        "--sns-arn", required=True,
        help="SNS topic ARN for alarm notifications"
    )
    parser.add_argument(
        "--dashboard-name", default="AppMonitoring",
        help="Name for the CloudWatch dashboard (default: AppMonitoring)"
    )
    parser.add_argument(
        "--log-group", default="/app/myservice",
        help="Log group name to create (default: /app/myservice)"
    )
    args = parser.parse_args()

    print("\n=== CloudWatch Monitoring Setup ===\n")

    # Step 1 — CPU alarm
    print("1. Creating CPU alarm...")
    cpu_alarm_name = create_cpu_alarm(args.ec2_id, args.sns_arn)

    # Step 2 — Memory alarm (publish sample metric first so alarm has a target)
    print("\n2. Creating memory alarm...")
    publish_sample_memory_metric(args.ec2_id)
    mem_alarm_name = create_memory_alarm(args.ec2_id, args.sns_arn)

    # Step 3 — Dashboard
    print("\n3. Creating dashboard...")
    dashboard_arn = create_dashboard(args.ec2_id, args.dashboard_name)

    # Step 4 — Log group
    print("\n4. Creating log group...")
    log_group_arn = create_log_group(args.log_group)

    # Summary
    region = boto3.session.Session().region_name or "us-east-1"
    print("\n=== Created Resources ===")
    print(f"  CPU Alarm:    {cpu_alarm_name}")
    print(f"  Memory Alarm: {mem_alarm_name}")
    print(f"  Dashboard:    {dashboard_arn}")
    print(f"  Log Group:    {log_group_arn}")
    print(f"\n  Console: https://{region}.console.aws.amazon.com/cloudwatch/home")


if __name__ == "__main__":
    main()
