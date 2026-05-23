"""
ipv6_checker.py — Verify IPv6 dual-stack setup for Project 11.19
Usage: python ipv6_checker.py --vpc-id vpc-xxxxxxxx [--profile my-profile]
"""
import argparse
import boto3


def check(vpc_id: str, session: boto3.Session) -> None:
    ec2 = session.client("ec2")
    print(f"\n{'='*65}\n  IPv6 Checker — Project 11.19  VPC={vpc_id}\n{'='*65}\n")

    # 1. VPC IPv6 CIDR
    vpcs = ec2.describe_vpcs(VpcIds=[vpc_id])["Vpcs"]
    if not vpcs:
        print("❌  VPC not found"); return
    vpc = vpcs[0]
    ipv4 = vpc["CidrBlock"]
    ipv6_assocs = vpc.get("Ipv6CidrBlockAssociationSet", [])
    ipv6 = ipv6_assocs[0]["Ipv6CidrBlock"] if ipv6_assocs else None
    print(f"{'✅' if ipv6 else '❌'}  VPC: {vpc_id}")
    print(f"     IPv4 CIDR: {ipv4}")
    print(f"     IPv6 CIDR: {ipv6 or 'NOT ASSIGNED'}")

    # 2. Subnets
    subnets = ec2.describe_subnets(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )["Subnets"]
    print(f"\n  Subnets ({len(subnets)}):")
    for s in subnets:
        name = next((t["Value"] for t in s.get("Tags", []) if t["Key"] == "Name"), "—")
        s_ipv6 = s.get("Ipv6CidrBlockAssociationSet", [])
        s_ipv6_cidr = s_ipv6[0]["Ipv6CidrBlock"] if s_ipv6 else None
        auto_ipv6 = s.get("AssignIpv6AddressOnCreation", False)
        icon = "✅" if s_ipv6_cidr else "❌"
        print(f"    {icon}  {name:25s}  IPv4={s['CidrBlock']:18s}  "
              f"IPv6={s_ipv6_cidr or 'NONE':30s}  AutoIPv6={auto_ipv6}")

    # 3. Egress-Only IGW
    eigws = ec2.describe_egress_only_internet_gateways(
        Filters=[{"Name": "attachment.vpc-id", "Values": [vpc_id]}]
    )["EgressOnlyInternetGateways"]
    if eigws:
        eigw = eigws[0]
        state = eigw["Attachments"][0]["State"]
        icon = "✅" if state == "attached" else "⚠️ "
        print(f"\n{icon}  Egress-Only IGW: {eigw['EgressOnlyInternetGatewayId']}  State={state}")
    else:
        print(f"\n❌  No Egress-Only IGW found for this VPC")

    # 4. Route tables — check for ::/0 routes
    rts = ec2.describe_route_tables(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )["RouteTables"]
    print(f"\n  Route Tables — IPv6 routes:")
    for rt in rts:
        name = next((t["Value"] for t in rt.get("Tags", []) if t["Key"] == "Name"), "—")
        ipv6_routes = [r for r in rt["Routes"]
                       if r.get("DestinationIpv6CidrBlock") == "::/0"]
        if ipv6_routes:
            for r in ipv6_routes:
                target = r.get("GatewayId") or r.get("EgressOnlyInternetGatewayId", "?")
                is_eigw = "EgressOnly" in target if target else False
                icon = "✅"
                rtype = "EIGW (outbound-only)" if is_eigw else "IGW (bidirectional)"
                print(f"    {icon}  {name:25s}  ::/0 → {target}  [{rtype}]")

    # 5. EC2 instances — check IPv6 addresses
    instances = ec2.describe_instances(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]},
                 {"Name": "instance-state-name", "Values": ["running"]}]
    )["Reservations"]
    print(f"\n  EC2 Instances:")
    for res in instances:
        for inst in res["Instances"]:
            name = next((t["Value"] for t in inst.get("Tags", []) if t["Key"] == "Name"), "—")
            ipv4_priv = inst.get("PrivateIpAddress", "—")
            ipv6_addrs = inst["NetworkInterfaces"][0].get("Ipv6Addresses", []) \
                         if inst.get("NetworkInterfaces") else []
            ipv6_addr = ipv6_addrs[0]["Ipv6Address"] if ipv6_addrs else None
            icon = "✅" if ipv6_addr else "❌"
            print(f"    {icon}  {name:25s}  IPv4={ipv4_priv:15s}  "
                  f"IPv6={ipv6_addr or 'NONE'}")

    print(f"\n{'='*65}\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--vpc-id",  required=True)
    p.add_argument("--profile", default=None)
    args = p.parse_args()
    check(args.vpc_id, boto3.Session(profile_name=args.profile))


if __name__ == "__main__":
    main()
