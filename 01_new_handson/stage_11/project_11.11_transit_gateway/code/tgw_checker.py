"""
tgw_checker.py — Verify Transit Gateway setup for Project 11.11
Usage: python tgw_checker.py --tgw-id tgw-xxxxxxxx [--profile my-profile]
"""
import argparse
import boto3


def check(tgw_id: str, session: boto3.Session) -> None:
    ec2 = session.client("ec2")
    print(f"\n{'='*65}\n  TGW Checker — Project 11.11  TGW={tgw_id}\n{'='*65}\n")

    # 1. TGW state
    tgws = ec2.describe_transit_gateways(
        TransitGatewayIds=[tgw_id]
    )["TransitGateways"]
    if not tgws:
        print("❌  Transit Gateway not found")
        return
    tgw = tgws[0]
    state = tgw["State"]
    icon = "✅" if state == "available" else "❌"
    print(f"{icon}  Transit Gateway: {tgw_id}  State={state}")

    # 2. VPC Attachments
    attachments = ec2.describe_transit_gateway_vpc_attachments(
        Filters=[{"Name": "transit-gateway-id", "Values": [tgw_id]}]
    )["TransitGatewayVpcAttachments"]
    print(f"\n  VPC Attachments ({len(attachments)}):")
    for a in attachments:
        name = next((t["Value"] for t in a.get("Tags", []) if t["Key"] == "Name"), "—")
        astate = a["State"]
        icon = "✅" if astate == "available" else "⚠️ "
        print(f"    {icon}  {name:25s}  VPC={a['VpcId']}  State={astate}")

    # 3. TGW Route Tables
    rts = ec2.describe_transit_gateway_route_tables(
        Filters=[{"Name": "transit-gateway-id", "Values": [tgw_id]}]
    )["TransitGatewayRouteTables"]
    print(f"\n  TGW Route Tables ({len(rts)}):")
    for rt in rts:
        name = next((t["Value"] for t in rt.get("Tags", []) if t["Key"] == "Name"), "default")
        print(f"    ℹ️   {rt['TransitGatewayRouteTableId']}  Name={name}  State={rt['State']}")

        # Show active routes
        try:
            routes = ec2.search_transit_gateway_routes(
                TransitGatewayRouteTableId=rt["TransitGatewayRouteTableId"],
                Filters=[{"Name": "state", "Values": ["active"]}]
            )["Routes"]
            for r in routes:
                print(f"         → {r['DestinationCidrBlock']:20s}  State={r['State']}")
        except Exception:
            pass

    all_available = all(a["State"] == "available" for a in attachments)
    print(f"\n{'✅' if all_available else '❌'}  All attachments available: {all_available}")
    print(f"\n{'='*65}\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tgw-id",  required=True)
    p.add_argument("--profile", default=None)
    args = p.parse_args()
    check(args.tgw_id, boto3.Session(profile_name=args.profile))


if __name__ == "__main__":
    main()
