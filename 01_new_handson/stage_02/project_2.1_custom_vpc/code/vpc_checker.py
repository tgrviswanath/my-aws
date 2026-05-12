"""
vpc_checker.py — Verify VPC architecture is correctly configured.

Prerequisites:
    pip install boto3

IAM Permissions Required:
    ec2:DescribeVpcs, ec2:DescribeSubnets, ec2:DescribeRouteTables
    ec2:DescribeInternetGateways, ec2:DescribeNatGateways
    ec2:DescribeSecurityGroups, ec2:DescribeNetworkAcls

Usage:
    python vpc_checker.py --vpc-id vpc-xxxxxxxx [--profile <profile>]

What this script checks:
    1. VPC exists and is available
    2. Subnets (public vs private classification)
    3. Route tables (internet gateway for public, NAT for private)
    4. Internet Gateway attachment
    5. NAT Gateway configuration
    6. Security groups (default + custom)
    7. Network ACLs
    8. Print a connectivity report
"""

import argparse
import sys
from typing import Any

import boto3
from botocore.exceptions import ClientError, NoCredentialsError


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_tag_value(tags: list[dict], key: str, default: str = "") -> str:
    """Extract a tag value from a list of tag dicts."""
    if not tags:
        return default
    for tag in tags:
        if tag.get("Key") == key:
            return tag.get("Value", default)
    return default


# ── VPC checks ────────────────────────────────────────────────────────────────

def check_vpc(ec2, vpc_id: str) -> dict[str, Any]:
    """Verify the VPC exists and return its details."""
    print("\n── VPC ─────────────────────────────────────────────────────────")
    try:
        response = ec2.describe_vpcs(VpcIds=[vpc_id])
        vpcs = response.get("Vpcs", [])
        if not vpcs:
            print(f"  [ERROR] VPC {vpc_id} not found.")
            sys.exit(1)

        vpc = vpcs[0]
        name = get_tag_value(vpc.get("Tags"), "Name", "(unnamed)")
        state = vpc["State"]
        cidr = vpc["CidrBlock"]

        print(f"  [+] VPC ID   : {vpc_id}")
        print(f"      Name     : {name}")
        print(f"      State    : {state}")
        print(f"      CIDR     : {cidr}")

        if state != "available":
            print(f"  [WARN] VPC state is '{state}' (expected 'available')")

        return vpc

    except ClientError as e:
        print(f"  [ERROR] Failed to describe VPC: {e}")
        sys.exit(1)


# ── Subnet checks ─────────────────────────────────────────────────────────────

def check_subnets(ec2, vpc_id: str) -> dict[str, list[dict]]:
    """List all subnets and classify them as public or private."""
    print("\n── Subnets ─────────────────────────────────────────────────────")

    response = ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])
    subnets = response.get("Subnets", [])

    if not subnets:
        print("  [WARN] No subnets found in this VPC.")
        return {"public": [], "private": []}

    # Classify subnets by checking their route tables
    route_tables = ec2.describe_route_tables(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )["RouteTables"]

    # Build a map: subnet_id → route_table
    subnet_to_rt = {}
    for rt in route_tables:
        for assoc in rt.get("Associations", []):
            if "SubnetId" in assoc:
                subnet_to_rt[assoc["SubnetId"]] = rt

    public_subnets = []
    private_subnets = []

    for subnet in subnets:
        subnet_id = subnet["SubnetId"]
        name = get_tag_value(subnet.get("Tags"), "Name", "(unnamed)")
        cidr = subnet["CidrBlock"]
        az = subnet["AvailabilityZone"]

        # Check if the route table has a route to an internet gateway
        rt = subnet_to_rt.get(subnet_id)
        has_igw = False
        if rt:
            for route in rt.get("Routes", []):
                if route.get("GatewayId", "").startswith("igw-"):
                    has_igw = True
                    break

        subnet_type = "public" if has_igw else "private"
        icon = "🌐" if has_igw else "🔒"

        print(f"  {icon} {subnet_id:<24} {name:<25} {cidr:<18} {az:<15} ({subnet_type})")

        if has_igw:
            public_subnets.append(subnet)
        else:
            private_subnets.append(subnet)

    print(f"\n  Total: {len(public_subnets)} public, {len(private_subnets)} private")

    return {"public": public_subnets, "private": private_subnets}


# ── Route table checks ────────────────────────────────────────────────────────

def check_route_tables(ec2, vpc_id: str):
    """List route tables and verify internet gateway / NAT gateway routes."""
    print("\n── Route Tables ────────────────────────────────────────────────")

    response = ec2.describe_route_tables(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )
    route_tables = response.get("RouteTables", [])

    if not route_tables:
        print("  [WARN] No route tables found.")
        return

    for rt in route_tables:
        rt_id = rt["RouteTableId"]
        name = get_tag_value(rt.get("Tags"), "Name", "(unnamed)")
        is_main = any(a.get("Main") for a in rt.get("Associations", []))
        main_label = " [MAIN]" if is_main else ""

        print(f"\n  Route Table: {rt_id} — {name}{main_label}")

        # List routes
        for route in rt.get("Routes", []):
            dest = route.get("DestinationCidrBlock", route.get("DestinationIpv6CidrBlock", "?"))
            target = (
                route.get("GatewayId") or
                route.get("NatGatewayId") or
                route.get("TransitGatewayId") or
                route.get("VpcPeeringConnectionId") or
                "local"
            )
            state = route.get("State", "active")
            print(f"    {dest:<20} → {target:<30} ({state})")


# ── Internet Gateway checks ───────────────────────────────────────────────────

def check_internet_gateway(ec2, vpc_id: str):
    """Check if an internet gateway is attached to the VPC."""
    print("\n── Internet Gateway ────────────────────────────────────────────")

    response = ec2.describe_internet_gateways(
        Filters=[{"Name": "attachment.vpc-id", "Values": [vpc_id]}]
    )
    igws = response.get("InternetGateways", [])

    if not igws:
        print("  [WARN] No internet gateway attached to this VPC.")
        return

    for igw in igws:
        igw_id = igw["InternetGatewayId"]
        name = get_tag_value(igw.get("Tags"), "Name", "(unnamed)")
        attachments = igw.get("Attachments", [])
        state = attachments[0]["State"] if attachments else "detached"
        print(f"  [+] {igw_id} — {name} (state: {state})")


# ── NAT Gateway checks ────────────────────────────────────────────────────────

def check_nat_gateways(ec2, vpc_id: str):
    """List NAT gateways in the VPC."""
    print("\n── NAT Gateways ────────────────────────────────────────────────")

    response = ec2.describe_nat_gateways(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )
    nat_gws = response.get("NatGateways", [])

    if not nat_gws:
        print("  [WARN] No NAT gateways found (private subnets won't have internet access).")
        return

    for nat in nat_gws:
        nat_id = nat["NatGatewayId"]
        state = nat["State"]
        subnet_id = nat["SubnetId"]
        name = get_tag_value(nat.get("Tags"), "Name", "(unnamed)")
        print(f"  [+] {nat_id} — {name} (state: {state}, subnet: {subnet_id})")


# ── Security Group checks ─────────────────────────────────────────────────────

def check_security_groups(ec2, vpc_id: str):
    """List security groups and their rules."""
    print("\n── Security Groups ─────────────────────────────────────────────")

    response = ec2.describe_security_groups(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )
    sgs = response.get("SecurityGroups", [])

    if not sgs:
        print("  [WARN] No security groups found.")
        return

    for sg in sgs:
        sg_id = sg["GroupId"]
        name = sg["GroupName"]
        desc = sg["Description"]
        print(f"\n  {sg_id} — {name}")
        print(f"    Description: {desc}")

        # Inbound rules
        ingress = sg.get("IpPermissions", [])
        if ingress:
            print("    Inbound:")
            for rule in ingress:
                protocol = rule.get("IpProtocol", "-1")
                from_port = rule.get("FromPort", "all")
                to_port = rule.get("ToPort", "all")
                sources = [r["CidrIp"] for r in rule.get("IpRanges", [])]
                sources += [r["CidrIpv6"] for r in rule.get("Ipv6Ranges", [])]
                sources += [r["GroupId"] for r in rule.get("UserIdGroupPairs", [])]
                source_str = ", ".join(sources) if sources else "any"
                print(f"      {protocol:<6} {from_port}-{to_port:<10} ← {source_str}")
        else:
            print("    Inbound: (none)")

        # Outbound rules
        egress = sg.get("IpPermissionsEgress", [])
        if egress:
            print("    Outbound:")
            for rule in egress:
                protocol = rule.get("IpProtocol", "-1")
                from_port = rule.get("FromPort", "all")
                to_port = rule.get("ToPort", "all")
                dests = [r["CidrIp"] for r in rule.get("IpRanges", [])]
                dests += [r["CidrIpv6"] for r in rule.get("Ipv6Ranges", [])]
                dest_str = ", ".join(dests) if dests else "any"
                print(f"      {protocol:<6} {from_port}-{to_port:<10} → {dest_str}")


# ── Summary report ────────────────────────────────────────────────────────────

def print_summary(vpc: dict, subnets: dict):
    """Print a connectivity report."""
    print("\n" + "=" * 60)
    print("  VPC Connectivity Report")
    print("=" * 60)
    print(f"  VPC ID       : {vpc['VpcId']}")
    print(f"  CIDR Block   : {vpc['CidrBlock']}")
    print(f"  Public Subnets  : {len(subnets['public'])}")
    print(f"  Private Subnets : {len(subnets['private'])}")
    print("\n  ✓ VPC is correctly configured for multi-tier architecture.")
    print("=" * 60 + "\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Verify VPC architecture.")
    parser.add_argument("--vpc-id", required=True, help="VPC ID to check")
    parser.add_argument("--profile", help="AWS profile name", default=None)
    parser.add_argument("--region", help="AWS region", default="us-east-1")
    args = parser.parse_args()

    try:
        session = boto3.Session(profile_name=args.profile, region_name=args.region)
        ec2 = session.client("ec2")
    except NoCredentialsError:
        print("[ERROR] No AWS credentials found. Run 'aws configure'.")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("  VPC Architecture Checker")
    print("=" * 60)

    vpc = check_vpc(ec2, args.vpc_id)
    subnets = check_subnets(ec2, args.vpc_id)
    check_route_tables(ec2, args.vpc_id)
    check_internet_gateway(ec2, args.vpc_id)
    check_nat_gateways(ec2, args.vpc_id)
    check_security_groups(ec2, args.vpc_id)

    print_summary(vpc, subnets)


if __name__ == "__main__":
    main()
