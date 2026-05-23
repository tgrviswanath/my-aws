"""
nacl_checker.py — Verify NACL configuration for Project 11.4
Usage: python nacl_checker.py --vpc-id vpc-xxxxxxxx [--profile my-profile]
"""
import argparse
import boto3


def check(vpc_id: str, session: boto3.Session) -> None:
    ec2 = session.client("ec2")
    print(f"\n{'='*60}\n  NACL Checker — Project 11.4  VPC={vpc_id}\n{'='*60}\n")

    nacls = ec2.describe_network_acls(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )["NetworkAcls"]

    for nacl in nacls:
        name = next((t["Value"] for t in nacl.get("Tags", []) if t["Key"] == "Name"), "—")
        is_default = nacl["IsDefault"]
        assoc_subnets = [a["SubnetId"] for a in nacl.get("Associations", [])]
        print(f"  NACL: {nacl['NetworkAclId']}  Name={name}  Default={is_default}")
        print(f"    Associated subnets: {assoc_subnets or 'none'}")

        inbound  = sorted([e for e in nacl["Entries"] if not e["Egress"]], key=lambda x: x["RuleNumber"])
        outbound = sorted([e for e in nacl["Entries"] if e["Egress"]],     key=lambda x: x["RuleNumber"])

        print(f"    Inbound rules ({len(inbound)}):")
        for r in inbound:
            ports = f"{r.get('PortRange', {}).get('From','*')}-{r.get('PortRange', {}).get('To','*')}"
            print(f"      Rule {r['RuleNumber']:5d}  {r['RuleAction'].upper():6s}  "
                  f"proto={r['Protocol']}  ports={ports}  src={r.get('CidrBlock','—')}")

        # Check for ephemeral port rule
        has_ephemeral = any(
            r.get("PortRange", {}).get("From", 0) <= 1024 and
            r.get("PortRange", {}).get("To", 0) >= 65535
            for r in inbound if r["RuleAction"] == "allow"
        )
        icon = "✅" if has_ephemeral else "⚠️ "
        print(f"    {icon}  Ephemeral ports (1024-65535) inbound: {has_ephemeral}")
        print()

    print(f"{'='*60}\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--vpc-id", required=True)
    p.add_argument("--profile", default=None)
    args = p.parse_args()
    check(args.vpc_id, boto3.Session(profile_name=args.profile))


if __name__ == "__main__":
    main()
