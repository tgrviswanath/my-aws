"""
sg_checker.py — Verify Security Group chaining for Project 11.3
Usage: python sg_checker.py --vpc-id vpc-xxxxxxxx [--profile my-profile]
"""
import argparse
import boto3


def check(vpc_id: str, session: boto3.Session) -> None:
    ec2 = session.client("ec2")
    print(f"\n{'='*60}\n  SG Checker — Project 11.3  VPC={vpc_id}\n{'='*60}\n")

    sgs = ec2.describe_security_groups(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )["SecurityGroups"]

    sg_map = {sg["GroupName"]: sg for sg in sgs}

    checks = [
        ("alb-sg-11-3",  "inbound", 80,   "0.0.0.0/0",    "CIDR"),
        ("web-sg-11-3",  "inbound", 80,   "alb-sg-11-3",  "SG"),
        ("app-sg-11-3",  "inbound", 8080, "web-sg-11-3",  "SG"),
        ("db-sg-11-3",   "inbound", 3306, "app-sg-11-3",  "SG"),
    ]

    for sg_name, direction, port, source, src_type in checks:
        sg = sg_map.get(sg_name)
        if not sg:
            print(f"❌  SG '{sg_name}' not found")
            continue

        found = False
        for rule in sg["IpPermissions"]:
            if rule.get("FromPort") == port:
                if src_type == "CIDR":
                    found = any(r["CidrIp"] == source for r in rule.get("IpRanges", []))
                else:
                    src_sg = sg_map.get(source, {})
                    found = any(
                        p.get("GroupId") == src_sg.get("GroupId")
                        for p in rule.get("UserIdGroupPairs", [])
                    )
        icon = "✅" if found else "❌"
        print(f"{icon}  {sg_name}: port {port} from {source} ({src_type})")

    print(f"\n{'='*60}\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--vpc-id", required=True)
    p.add_argument("--profile", default=None)
    args = p.parse_args()
    check(args.vpc_id, boto3.Session(profile_name=args.profile))


if __name__ == "__main__":
    main()
