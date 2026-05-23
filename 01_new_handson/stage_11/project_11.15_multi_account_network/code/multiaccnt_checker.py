"""
multiaccnt_checker.py — Verify multi-account network for Project 11.15
Usage: python multiaccnt_checker.py --share-name share-subnets-11-15
       --profile-mgmt management --profile-dev dev
"""
import argparse
import boto3


def check(share_name: str, profile_mgmt: str, profile_dev: str) -> None:
    sess_mgmt = boto3.Session(profile_name=profile_mgmt)
    sess_dev  = boto3.Session(profile_name=profile_dev)
    ram_mgmt  = sess_mgmt.client("ram")
    ec2_dev   = sess_dev.client("ec2")
    sts_dev   = sess_dev.client("sts")

    print(f"\n{'='*65}\n  Multi-Account Checker — Project 11.15\n{'='*65}\n")

    # 1. RAM share status
    shares = ram_mgmt.get_resource_shares(
        resourceOwner="SELF",
        name=share_name
    )["resourceShares"]

    if not shares:
        print(f"❌  RAM share '{share_name}' not found in management account")
    else:
        for s in shares:
            icon = "✅" if s["status"] == "ACTIVE" else "❌"
            print(f"{icon}  RAM Share: {s['name']}  Status={s['status']}")

        # List shared resources
        resources = ram_mgmt.list_resources(
            resourceOwner="SELF",
            resourceShareArns=[shares[0]["resourceShareArn"]]
        )["resources"]
        print(f"\n  Shared resources ({len(resources)}):")
        for r in resources:
            print(f"    ✅  {r['arn'].split(':')[-1]}  Type={r['type']}  Status={r['status']}")

    # 2. Verify shared subnets visible in Dev account
    dev_account_id = sts_dev.get_caller_identity()["Account"]
    subnets = ec2_dev.describe_subnets()["Subnets"]
    shared_subnets = [s for s in subnets if s["OwnerId"] != dev_account_id]

    print(f"\n  Shared subnets visible in Dev account ({len(shared_subnets)}):")
    if shared_subnets:
        for s in shared_subnets:
            name = next((t["Value"] for t in s.get("Tags", []) if t["Key"] == "Name"), "—")
            print(f"    ✅  {s['SubnetId']}  Name={name}  CIDR={s['CidrBlock']}  Owner={s['OwnerId']}")
    else:
        print("    ❌  No shared subnets found in Dev account")

    print(f"\n{'='*65}\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--share-name",   required=True)
    p.add_argument("--profile-mgmt", required=True)
    p.add_argument("--profile-dev",  required=True)
    args = p.parse_args()
    check(args.share_name, args.profile_mgmt, args.profile_dev)


if __name__ == "__main__":
    main()
