"""
nfw_checker.py — Verify AWS Network Firewall for Project 11.14
Usage: python nfw_checker.py --firewall-name nfw-11-14 [--profile my-profile]
"""
import argparse
import boto3


def check(firewall_name: str, session: boto3.Session) -> None:
    nfw = session.client("network-firewall")
    ec2 = session.client("ec2")

    print(f"\n{'='*65}\n  NFW Checker — Project 11.14  Firewall={firewall_name}\n{'='*65}\n")

    # 1. Firewall status
    try:
        resp = nfw.describe_firewall(FirewallName=firewall_name)
        fw   = resp["Firewall"]
        status = resp["FirewallStatus"]["Status"]
        icon = "✅" if status == "READY" else "⚠️ "
        print(f"{icon}  Firewall: {fw['FirewallName']}  Status={status}")
        print(f"     VPC: {fw['VpcId']}")

        # Endpoint IDs per AZ
        sync = resp["FirewallStatus"].get("SyncStates", {})
        print(f"\n  Firewall Endpoints ({len(sync)} AZ):")
        for az, state in sync.items():
            ep = state.get("Attachment", {}).get("EndpointId", "—")
            ep_status = state.get("Attachment", {}).get("Status", "—")
            icon = "✅" if ep_status == "READY" else "⚠️ "
            print(f"    {icon}  AZ={az}  EndpointId={ep}  Status={ep_status}")

    except nfw.exceptions.ResourceNotFoundException:
        print(f"❌  Firewall '{firewall_name}' not found")
        return

    # 2. Firewall policy
    policy_arn = fw.get("FirewallPolicyArn", "")
    if policy_arn:
        try:
            policy_resp = nfw.describe_firewall_policy(FirewallPolicyArn=policy_arn)
            policy_status = policy_resp["FirewallPolicyResponse"]["FirewallPolicyStatus"]
            icon = "✅" if policy_status == "ACTIVE" else "⚠️ "
            print(f"\n{icon}  Policy: {policy_arn.split('/')[-1]}  Status={policy_status}")
        except Exception as e:
            print(f"\n⚠️   Could not describe policy: {e}")

    # 3. Check route tables for firewall endpoint routes
    vpc_id = fw["VpcId"]
    rts = ec2.describe_route_tables(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )["RouteTables"]

    endpoint_routes = []
    for rt in rts:
        for r in rt["Routes"]:
            if r.get("VpcEndpointId", "").startswith("vpce-"):
                name = next((t["Value"] for t in rt.get("Tags", []) if t["Key"] == "Name"), "—")
                endpoint_routes.append((name, r["DestinationCidrBlock"], r["VpcEndpointId"]))

    print(f"\n  Route table entries pointing to firewall endpoint: {len(endpoint_routes)}")
    if endpoint_routes:
        for rt_name, dest, ep in endpoint_routes:
            print(f"    ✅  RT={rt_name}  {dest} → {ep}")
    else:
        print("    ❌  No routes found pointing to firewall endpoint")
        print("       Check that route tables are configured to send traffic through the firewall")

    print(f"\n{'='*65}\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--firewall-name", required=True)
    p.add_argument("--profile",       default=None)
    args = p.parse_args()
    check(args.firewall_name, boto3.Session(profile_name=args.profile))


if __name__ == "__main__":
    main()
