"""
iac_checker.py — Verify IaC-deployed network for Project 11.20
Usage: python iac_checker.py --tf-vpc-id vpc-xxx --cfn-stack vpc-11-20
       [--profile my-profile]
"""
import argparse
import boto3


def check_terraform_vpc(vpc_id: str, ec2) -> None:
    print(f"\n  [Terraform] VPC: {vpc_id}")
    try:
        vpcs = ec2.describe_vpcs(VpcIds=[vpc_id])["Vpcs"]
        if not vpcs:
            print("    ❌  VPC not found"); return
        vpc = vpcs[0]
        print(f"    ✅  State={vpc['State']}  CIDR={vpc['CidrBlock']}")

        subnets = ec2.describe_subnets(
            Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
        )["Subnets"]
        print(f"    ✅  Subnets: {len(subnets)}")
        for s in subnets:
            name = next((t["Value"] for t in s.get("Tags", []) if t["Key"] == "Name"), "—")
            print(f"         {name:30s}  {s['CidrBlock']}")

        nats = ec2.describe_nat_gateways(
            Filters=[{"Name": "vpc-id", "Values": [vpc_id]},
                     {"Name": "state",  "Values": ["available"]}]
        )["NatGateways"]
        print(f"    {'✅' if nats else '⚠️ '}  NAT Gateways: {len(nats)}")
    except Exception as e:
        print(f"    ❌  Error: {e}")


def check_cfn_stack(stack_name: str, cfn) -> None:
    print(f"\n  [CloudFormation] Stack: {stack_name}")
    try:
        stacks = cfn.describe_stacks(StackName=stack_name)["Stacks"]
        if not stacks:
            print("    ❌  Stack not found"); return
        stack = stacks[0]
        status = stack["StackStatus"]
        icon = "✅" if "COMPLETE" in status else ("⚠️ " if "IN_PROGRESS" in status else "❌")
        print(f"    {icon}  Status={status}")

        resources = cfn.list_stack_resources(StackName=stack_name)["StackResourceSummaries"]
        vpc_resources = [r for r in resources if "VPC" in r["ResourceType"] or "Subnet" in r["ResourceType"]]
        print(f"    ✅  Total resources: {len(resources)}")
        print(f"    ✅  VPC/Subnet resources: {len(vpc_resources)}")
        for r in vpc_resources[:6]:
            print(f"         {r['ResourceType']:40s}  {r['ResourceStatus']}")

        # Check for drift
        try:
            drift = cfn.describe_stacks(StackName=stack_name)["Stacks"][0].get("DriftInformation", {})
            drift_status = drift.get("StackDriftStatus", "NOT_CHECKED")
            icon = "✅" if drift_status == "IN_SYNC" else ("⚠️ " if drift_status == "DRIFTED" else "ℹ️ ")
            print(f"    {icon}  Drift status: {drift_status}")
        except Exception:
            pass
    except Exception as e:
        print(f"    ❌  Error: {e}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tf-vpc-id",  required=True, help="VPC ID created by Terraform")
    p.add_argument("--cfn-stack",  required=True, help="CloudFormation stack name")
    p.add_argument("--profile",    default=None)
    args = p.parse_args()

    session = boto3.Session(profile_name=args.profile)
    ec2 = session.client("ec2")
    cfn = session.client("cloudformation")

    print(f"\n{'='*65}\n  IaC Checker — Project 11.20\n{'='*65}")
    check_terraform_vpc(args.tf_vpc_id, ec2)
    check_cfn_stack(args.cfn_stack, cfn)
    print(f"\n{'='*65}\n")


if __name__ == "__main__":
    main()
