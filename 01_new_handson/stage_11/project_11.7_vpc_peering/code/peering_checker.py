"""
peering_checker.py — Verify VPC Peering for Project 11.7
Usage: python peering_checker.py --vpc-a vpc-xxx --vpc-b vpc-yyy [--profile my-profile]
"""
import argparse
import boto3


def check(vpc_a: str, vpc_b: str, session: boto3.Session) -> None:
    ec2 = session.client("ec2")
    print(f"\n{'='*60}\n  Peering Checker — Project 11.7\n  VPC-A={vpc_a}  VPC-B={vpc_b}\n{'='*60}\n")

    # Find peering connection
    pcxs = ec2.describe_vpc_peering_connections(
        Filters=[
            {"Name": "requester-vpc-info.vpc-id", "Values": [vpc_a, vpc_b]},
            {"Name": "accepter-vpc-info.vpc-id",  "Values": [vpc_a, vpc_b]},
        ]
    )["VpcPeeringConnections"]

    if not pcxs:
        print("❌  No peering connection found between these VPCs")
        return

    for pcx in pcxs:
        status = pcx["Status"]["Code"]
        icon = "✅" if status == "active" else "❌"
        print(f"{icon}  Peering: {pcx['VpcPeeringConnectionId']}  Status={status}")

    pcx_id = pcxs[0]["VpcPeeringConnectionId"]

    # Check routes in both VPCs
    for vpc_id, other_cidr_label in [(vpc_a, "VPC-B CIDR"), (vpc_b, "VPC-A CIDR")]:
        rts = ec2.describe_route_tables(
            Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
        )["RouteTables"]
        has_pcx_route = any(
            r.get("VpcPeeringConnectionId") == pcx_id
            for rt in rts for r in rt["Routes"]
        )
        icon = "✅" if has_pcx_route else "❌"
        print(f"{icon}  VPC {vpc_id}: route to {other_cidr_label} via peering = {has_pcx_route}")

    print(f"\n{'='*60}\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--vpc-a", required=True)
    p.add_argument("--vpc-b", required=True)
    p.add_argument("--profile", default=None)
    args = p.parse_args()
    check(args.vpc_a, args.vpc_b, boto3.Session(profile_name=args.profile))


if __name__ == "__main__":
    main()
