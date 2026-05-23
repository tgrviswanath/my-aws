"""
nat_checker.py — Verify NAT Gateway setup for Project 11.2
Usage: python nat_checker.py --vpc-id vpc-xxxxxxxx [--profile my-profile]
"""
import argparse
import boto3


def check(vpc_id: str, session: boto3.Session) -> None:
    ec2 = session.client("ec2")
    print(f"\n{'='*55}\n  NAT Checker — Project 11.2  VPC={vpc_id}\n{'='*55}\n")

    # NAT Gateways
    nats = ec2.describe_nat_gateways(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]},
                 {"Name": "state", "Values": ["available"]}]
    )["NatGateways"]
    if nats:
        for n in nats:
            eip = n["NatGatewayAddresses"][0].get("PublicIp", "—")
            print(f"✅  NAT Gateway: {n['NatGatewayId']}  State={n['State']}  EIP={eip}")
    else:
        print("❌  No available NAT Gateway found in this VPC")

    # Route tables — check for NAT route
    rts = ec2.describe_route_tables(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )["RouteTables"]
    for rt in rts:
        name = next((t["Value"] for t in rt.get("Tags", []) if t["Key"] == "Name"), "—")
        nat_route = any(
            r.get("NatGatewayId") and r.get("DestinationCidrBlock") == "0.0.0.0/0"
            for r in rt["Routes"]
        )
        if nat_route:
            print(f"✅  Route table {rt['RouteTableId']} ({name}) has NAT route")

    print(f"\n{'='*55}\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--vpc-id", required=True)
    p.add_argument("--profile", default=None)
    args = p.parse_args()
    check(args.vpc_id, boto3.Session(profile_name=args.profile))


if __name__ == "__main__":
    main()
