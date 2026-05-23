"""
endpoint_checker.py — Verify VPC Endpoints for Project 11.8
Usage: python endpoint_checker.py --vpc-id vpc-xxxxxxxx [--profile my-profile]
"""
import argparse
import boto3


EXPECTED_SERVICES = [
    ("com.amazonaws.us-east-1.s3",        "Gateway"),
    ("com.amazonaws.us-east-1.dynamodb",  "Gateway"),
    ("com.amazonaws.us-east-1.ssm",       "Interface"),
]


def check(vpc_id: str, session: boto3.Session) -> None:
    ec2 = session.client("ec2")
    print(f"\n{'='*65}\n  Endpoint Checker — Project 11.8  VPC={vpc_id}\n{'='*65}\n")

    endpoints = ec2.describe_vpc_endpoints(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]},
                 {"Name": "state",  "Values": ["available", "pending"]}]
    )["VpcEndpoints"]

    found = {ep["ServiceName"]: ep for ep in endpoints}

    for service, ep_type in EXPECTED_SERVICES:
        ep = found.get(service)
        if ep:
            state = ep["State"]
            icon = "✅" if state == "available" else "⚠️ "
            print(f"{icon}  {ep_type:10s}  {service.split('.')[-1]:15s}  State={state}")
        else:
            print(f"❌  {ep_type:10s}  {service.split('.')[-1]:15s}  NOT FOUND")

    # Check route table for prefix list routes (Gateway endpoints)
    rts = ec2.describe_route_tables(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )["RouteTables"]
    prefix_routes = [
        r for rt in rts for r in rt["Routes"]
        if r.get("DestinationPrefixListId")
    ]
    print(f"\n  Prefix list routes in route tables: {len(prefix_routes)}")
    for r in prefix_routes:
        print(f"    ✅  {r['DestinationPrefixListId']}  →  {r.get('GatewayId', r.get('VpcEndpointId', '?'))}")

    print(f"\n{'='*65}\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--vpc-id", required=True)
    p.add_argument("--profile", default=None)
    args = p.parse_args()
    check(args.vpc_id, boto3.Session(profile_name=args.profile))


if __name__ == "__main__":
    main()
