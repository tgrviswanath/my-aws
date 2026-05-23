"""
vpc_checker.py — Verify Project 11.1 VPC architecture
Usage: python vpc_checker.py --vpc-id vpc-xxxxxxxx [--profile my-profile]
"""
import argparse
import boto3


def check_vpc(vpc_id: str, session: boto3.Session) -> None:
    ec2 = session.client("ec2")

    print(f"\n{'='*55}")
    print(f"  VPC Checker — Project 11.1")
    print(f"  VPC ID: {vpc_id}")
    print(f"{'='*55}\n")

    # 1. VPC
    vpcs = ec2.describe_vpcs(VpcIds=[vpc_id])["Vpcs"]
    if not vpcs:
        print("❌  VPC not found")
        return
    vpc = vpcs[0]
    state = vpc["State"]
    cidr = vpc["CidrBlock"]
    status = "✅" if state == "available" else "❌"
    print(f"{status}  VPC: {vpc_id}  CIDR={cidr}  State={state}")

    # 2. Subnets
    subnets = ec2.describe_subnets(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )["Subnets"]
    print(f"\n  Subnets ({len(subnets)} found):")
    for s in subnets:
        name = next((t["Value"] for t in s.get("Tags", []) if t["Key"] == "Name"), "—")
        pub = "PUBLIC" if s["MapPublicIpOnLaunch"] else "PRIVATE"
        print(f"    {'✅' if pub == 'PUBLIC' else '⚠️ '}  {name}  {s['CidrBlock']}  {s['AvailabilityZone']}  [{pub}]")

    # 3. Internet Gateway
    igws = ec2.describe_internet_gateways(
        Filters=[{"Name": "attachment.vpc-id", "Values": [vpc_id]}]
    )["InternetGateways"]
    if igws:
        igw = igws[0]
        name = next((t["Value"] for t in igw.get("Tags", []) if t["Key"] == "Name"), "—")
        print(f"\n✅  Internet Gateway: {igw['InternetGatewayId']}  Name={name}  Attached=True")
    else:
        print("\n❌  No Internet Gateway attached to this VPC")

    # 4. Route Tables
    rts = ec2.describe_route_tables(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )["RouteTables"]
    print(f"\n  Route Tables ({len(rts)} found):")
    for rt in rts:
        name = next((t["Value"] for t in rt.get("Tags", []) if t["Key"] == "Name"), "—")
        has_igw_route = any(
            r.get("GatewayId", "").startswith("igw-") and r.get("DestinationCidrBlock") == "0.0.0.0/0"
            for r in rt["Routes"]
        )
        icon = "✅" if has_igw_route else "ℹ️ "
        print(f"    {icon}  {rt['RouteTableId']}  Name={name}  IGW-route={has_igw_route}")

    print(f"\n{'='*55}\n")


def main():
    parser = argparse.ArgumentParser(description="VPC Checker — Project 11.1")
    parser.add_argument("--vpc-id", required=True, help="VPC ID to check")
    parser.add_argument("--profile", default=None, help="AWS profile name")
    args = parser.parse_args()

    session = boto3.Session(profile_name=args.profile)
    check_vpc(args.vpc_id, session)


if __name__ == "__main__":
    main()
