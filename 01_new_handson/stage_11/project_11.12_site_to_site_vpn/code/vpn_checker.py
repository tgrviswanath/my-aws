"""
vpn_checker.py — Verify Site-to-Site VPN for Project 11.12
Usage: python vpn_checker.py --vpn-name vpn-11-12 [--profile my-profile]
"""
import argparse
import boto3


def check(vpn_name: str, session: boto3.Session) -> None:
    ec2 = session.client("ec2")
    print(f"\n{'='*65}\n  VPN Checker — Project 11.12  VPN={vpn_name}\n{'='*65}\n")

    vpns = ec2.describe_vpn_connections(
        Filters=[{"Name": "tag:Name", "Values": [vpn_name]},
                 {"Name": "state",    "Values": ["available", "pending"]}]
    )["VpnConnections"]

    if not vpns:
        print("❌  VPN connection not found")
        return

    for vpn in vpns:
        state = vpn["State"]
        icon = "✅" if state == "available" else "⚠️ "
        print(f"{icon}  VPN: {vpn['VpnConnectionId']}  State={state}")

        tunnels = vpn.get("VgwTelemetry", [])
        up_count = sum(1 for t in tunnels if t["Status"] == "UP")
        print(f"\n  Tunnels ({len(tunnels)} total, {up_count} UP):")
        for t in tunnels:
            icon = "✅" if t["Status"] == "UP" else "❌"
            print(f"    {icon}  Outside IP: {t['OutsideIpAddress']}  "
                  f"Status={t['Status']}  "
                  f"AcceptedRoutes={t.get('AcceptedRouteCount', 0)}")

        if up_count == 0:
            print("\n  ⚠️   Both tunnels DOWN — check strongSwan configuration")
        elif up_count == 1:
            print("\n  ⚠️   Only 1 tunnel UP — configure second tunnel for HA")
        else:
            print("\n  ✅  Both tunnels UP — full HA achieved")

    # Check VGW
    vgws = ec2.describe_vpn_gateways(
        Filters=[{"Name": "attachment.state", "Values": ["attached"]}]
    )["VpnGateways"]
    print(f"\n  Virtual Private Gateways (attached): {len(vgws)}")
    for vgw in vgws:
        name = next((t["Value"] for t in vgw.get("Tags", []) if t["Key"] == "Name"), "—")
        print(f"    ✅  {vgw['VpnGatewayId']}  Name={name}  State={vgw['State']}")

    print(f"\n{'='*65}\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--vpn-name", required=True)
    p.add_argument("--profile",  default=None)
    args = p.parse_args()
    check(args.vpn_name, boto3.Session(profile_name=args.profile))


if __name__ == "__main__":
    main()
