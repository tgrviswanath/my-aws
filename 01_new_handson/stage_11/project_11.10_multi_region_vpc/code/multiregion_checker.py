"""
multiregion_checker.py — Verify multi-region VPC peering for Project 11.10
Usage: python multiregion_checker.py --vpc-east vpc-xxx --vpc-west vpc-yyy
       --region-east us-east-1 --region-west us-west-2 [--profile p]
"""
import argparse
import boto3


def check(vpc_east: str, vpc_west: str, region_east: str, region_west: str,
          session: boto3.Session) -> None:
    ec2_east = session.client("ec2", region_name=region_east)
    ec2_west = session.client("ec2", region_name=region_west)

    print(f"\n{'='*65}\n  Multi-Region Checker — Project 11.10\n{'='*65}\n")

    # Find peering connection
    pcxs = ec2_east.describe_vpc_peering_connections(
        Filters=[{"Name": "requester-vpc-info.vpc-id", "Values": [vpc_east]}]
    )["VpcPeeringConnections"]

    if not pcxs:
        print("❌  No peering connection found from VPC-East")
        return

    for pcx in pcxs:
        status = pcx["Status"]["Code"]
        accepter_region = pcx["AccepterVpcInfo"].get("Region", "unknown")
        icon = "✅" if status == "active" else "❌"
        print(f"{icon}  Peering: {pcx['VpcPeeringConnectionId']}  "
              f"Status={status}  AccepterRegion={accepter_region}")

    pcx_id = pcxs[0]["VpcPeeringConnectionId"]

    # Check routes in East
    rts_east = ec2_east.describe_route_tables(
        Filters=[{"Name": "vpc-id", "Values": [vpc_east]}]
    )["RouteTables"]
    east_has_route = any(
        r.get("VpcPeeringConnectionId") == pcx_id
        for rt in rts_east for r in rt["Routes"]
    )
    print(f"{'✅' if east_has_route else '❌'}  {region_east} route table has peering route: {east_has_route}")

    # Check routes in West
    rts_west = ec2_west.describe_route_tables(
        Filters=[{"Name": "vpc-id", "Values": [vpc_west]}]
    )["RouteTables"]
    west_has_route = any(
        r.get("VpcPeeringConnectionId") == pcx_id
        for rt in rts_west for r in rt["Routes"]
    )
    print(f"{'✅' if west_has_route else '❌'}  {region_west} route table has peering route: {west_has_route}")

    print(f"\n{'='*65}\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--vpc-east",    required=True)
    p.add_argument("--vpc-west",    required=True)
    p.add_argument("--region-east", default="us-east-1")
    p.add_argument("--region-west", default="us-west-2")
    p.add_argument("--profile",     default=None)
    args = p.parse_args()
    check(args.vpc_east, args.vpc_west, args.region_east, args.region_west,
          boto3.Session(profile_name=args.profile))


if __name__ == "__main__":
    main()
