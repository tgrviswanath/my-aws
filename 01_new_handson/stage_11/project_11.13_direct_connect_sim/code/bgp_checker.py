"""
bgp_checker.py — Verify BGP VPN setup for Project 11.13
Usage: python bgp_checker.py --vpn-name vpn-bgp-11-13 [--profile my-profile]
"""
import argparse
import boto3


def check(vpn_name: str, session: boto3.Session) -> None:
    ec2 = session.client("ec2")
    print(f"\n{'='*65}\n  BGP/DX Sim Checker — Project 11.13  VPN={vpn_name}\n{'='*65}\n")

    vpns = ec2.describe_vpn_connections(
        Filters=[{"Name": "tag:Name", "Values": [vpn_name]},
                 {"Name": "state",    "Values": ["available", "pending"]}]
    )["VpnConnections"]

    if not vpns:
        print("❌  VPN connection not found")
        return

    for vpn in vpns:
        options = vpn.get("Options", {})
        is_bgp = not options.get("StaticRoutesOnly", True)
        print(f"{'✅' if is_bgp else '❌'}  Routing type: {'Dynamic (BGP)' if is_bgp else 'Static'}")
        print(f"  VPN ID: {vpn['VpnConnectionId']}  State={vpn['State']}")

        tunnels = vpn.get("VgwTelemetry", [])
        up = sum(1 for t in tunnels if t["Status"] == "UP")
        print(f"\n  Tunnels: {up}/{len(tunnels)} UP")
        for t in tunnels:
            icon = "✅" if t["Status"] == "UP" else "❌"
            routes = t.get("AcceptedRouteCount", 0)
            print(f"    {icon}  {t['OutsideIpAddress']}  Status={t['Status']}  BGP routes accepted={routes}")

        if up > 0 and is_bgp:
            print("\n  ✅  BGP session is UP and routing dynamically")
        elif up > 0:
            print("\n  ⚠️   Tunnel UP but using static routing (not BGP)")
        else:
            print("\n  ❌  No tunnels UP — check Bird BGP configuration")

    print(f"\n{'='*65}\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--vpn-name", required=True)
    p.add_argument("--profile",  default=None)
    args = p.parse_args()
    check(args.vpn_name, boto3.Session(profile_name=args.profile))


if __name__ == "__main__":
    main()
