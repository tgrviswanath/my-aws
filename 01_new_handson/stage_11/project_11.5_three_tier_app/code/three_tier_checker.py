"""
three_tier_checker.py — Verify three-tier VPC for Project 11.5
Usage: python three_tier_checker.py --vpc-id vpc-xxxxxxxx [--profile my-profile]
"""
import argparse
import boto3


def check(vpc_id: str, session: boto3.Session) -> None:
    ec2 = session.client("ec2")
    print(f"\n{'='*60}\n  Three-Tier Checker — Project 11.5  VPC={vpc_id}\n{'='*60}\n")

    # Subnets
    subnets = ec2.describe_subnets(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )["Subnets"]
    print(f"  Subnets ({len(subnets)}):")
    for s in subnets:
        name = next((t["Value"] for t in s.get("Tags", []) if t["Key"] == "Name"), "—")
        pub = "PUBLIC " if s["MapPublicIpOnLaunch"] else "PRIVATE"
        print(f"    {'✅' if pub == 'PUBLIC ' else 'ℹ️ '}  {name:20s}  {s['CidrBlock']:18s}  {s['AvailabilityZone']}  [{pub}]")

    # NAT Gateways
    nats = ec2.describe_nat_gateways(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]},
                 {"Name": "state", "Values": ["available"]}]
    )["NatGateways"]
    print(f"\n  NAT Gateways ({len(nats)}):")
    for n in nats:
        name = next((t["Value"] for t in n.get("Tags", []) if t["Key"] == "Name"), "—")
        eip = n["NatGatewayAddresses"][0].get("PublicIp", "—")
        icon = "✅" if n["State"] == "available" else "❌"
        print(f"    {icon}  {name}  {n['NatGatewayId']}  EIP={eip}")

    ha_ok = len(nats) >= 2
    print(f"\n  {'✅' if ha_ok else '⚠️ '}  Multi-AZ NAT: {ha_ok} ({len(nats)} NAT GWs found, need 2 for HA)")

    # Route tables
    rts = ec2.describe_route_tables(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )["RouteTables"]
    print(f"\n  Route Tables ({len(rts)}):")
    for rt in rts:
        name = next((t["Value"] for t in rt.get("Tags", []) if t["Key"] == "Name"), "—")
        igw_route = any(r.get("GatewayId", "").startswith("igw-") for r in rt["Routes"])
        nat_route = any(r.get("NatGatewayId") for r in rt["Routes"])
        route_type = "→ IGW" if igw_route else ("→ NAT" if nat_route else "local only")
        print(f"    ℹ️   {name:25s}  {route_type}")

    print(f"\n{'='*60}\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--vpc-id", required=True)
    p.add_argument("--profile", default=None)
    args = p.parse_args()
    check(args.vpc_id, boto3.Session(profile_name=args.profile))


if __name__ == "__main__":
    main()
