"""
flowlog_checker.py — Verify VPC Flow Logs for Project 11.9
Usage: python flowlog_checker.py --vpc-id vpc-xxx --log-group /vpc/flowlogs/11-9 [--profile p]
"""
import argparse
import time
import boto3


def check(vpc_id: str, log_group: str, session: boto3.Session) -> None:
    ec2  = session.client("ec2")
    logs = session.client("logs")

    print(f"\n{'='*65}\n  Flow Log Checker — Project 11.9  VPC={vpc_id}\n{'='*65}\n")

    # 1. Check flow log status
    flow_logs = ec2.describe_flow_logs(
        Filters=[{"Name": "resource-id", "Values": [vpc_id]}]
    )["FlowLogs"]

    if not flow_logs:
        print("❌  No flow logs found for this VPC")
    else:
        for fl in flow_logs:
            status = fl["FlowLogStatus"]
            dest   = fl.get("LogDestinationType", "unknown")
            icon   = "✅" if status == "ACTIVE" else "❌"
            print(f"{icon}  Flow Log: {fl['FlowLogId']}  Status={status}  Dest={dest}")

    # 2. Check CloudWatch log group exists
    try:
        groups = logs.describe_log_groups(logGroupNamePrefix=log_group)["logGroups"]
        if groups:
            print(f"\n✅  CloudWatch Log Group: {log_group}  exists")
            streams = logs.describe_log_streams(
                logGroupName=log_group, orderBy="LastEventTime", descending=True, limit=3
            )["logStreams"]
            print(f"   Recent streams ({len(streams)}):")
            for s in streams:
                print(f"     - {s['logStreamName']}")
        else:
            print(f"\n⚠️   CloudWatch Log Group {log_group} not found yet (may take a few minutes)")
    except Exception as e:
        print(f"\n⚠️   Could not check CloudWatch: {e}")

    # 3. Run a quick Insights query for REJECT records
    print(f"\n  Running CloudWatch Insights query for REJECT records...")
    try:
        end   = int(time.time())
        start = end - 3600  # last 1 hour
        resp  = logs.start_query(
            logGroupName=log_group,
            startTime=start,
            endTime=end,
            queryString="fields srcAddr, dstAddr, dstPort, action | filter action = 'REJECT' | limit 5"
        )
        qid = resp["queryId"]
        time.sleep(5)
        result = logs.get_query_results(queryId=qid)
        records = result["results"]
        print(f"  {'✅' if records else 'ℹ️ '}  REJECT records found: {len(records)}")
        for row in records[:3]:
            vals = {f["field"]: f["value"] for f in row}
            print(f"     {vals.get('srcAddr','?')} → {vals.get('dstAddr','?')}:{vals.get('dstPort','?')}  [{vals.get('action','?')}]")
    except Exception as e:
        print(f"  ⚠️   Insights query failed: {e}")

    print(f"\n{'='*65}\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--vpc-id",    required=True)
    p.add_argument("--log-group", required=True)
    p.add_argument("--profile",   default=None)
    args = p.parse_args()
    check(args.vpc_id, args.log_group, boto3.Session(profile_name=args.profile))


if __name__ == "__main__":
    main()
