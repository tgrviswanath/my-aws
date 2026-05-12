"""
infra_validator.py — Validate AWS infrastructure created by Terraform.

Usage:
    python infra_validator.py [--region REGION] [--profile PROFILE]

Checks performed:
    1. VPC with tag Project=handson exists
    2. Public and private subnets are tagged correctly
    3. At least one EC2 instance is in 'running' state
    4. RDS instance is in 'available' state

Exit code:
    0 — all checks passed
    1 — one or more checks failed
"""

import sys
import argparse
import boto3
from botocore.exceptions import ClientError, NoCredentialsError


# ── ANSI colors ───────────────────────────────────────────────────────────────
PASS  = "\033[92m[PASS]\033[0m"
FAIL  = "\033[91m[FAIL]\033[0m"
INFO  = "\033[96m[INFO]\033[0m"
WARN  = "\033[93m[WARN]\033[0m"
BOLD  = "\033[1m"
RESET = "\033[0m"

# Tag used to identify resources created by the Terraform project
PROJECT_TAG_KEY   = "Project"
PROJECT_TAG_VALUE = "handson"


# ── Helper ────────────────────────────────────────────────────────────────────

def get_tag(tags: list[dict], key: str) -> str | None:
    """Return the value of a tag by key, or None if not present."""
    for tag in tags or []:
        if tag.get("Key") == key:
            return tag.get("Value")
    return None


def print_result(label: str, passed: bool, detail: str = "") -> None:
    """Print a formatted pass/fail line."""
    status = PASS if passed else FAIL
    suffix = f"  → {detail}" if detail else ""
    print(f"  {status}  {label}{suffix}")


# ── Individual checks ─────────────────────────────────────────────────────────

def check_vpc(ec2) -> tuple[bool, str | None]:
    """
    Verify that a VPC tagged Project=handson exists.

    Returns:
        (passed, vpc_id) — vpc_id is None if not found.
    """
    response = ec2.describe_vpcs(
        Filters=[{"Name": f"tag:{PROJECT_TAG_KEY}", "Values": [PROJECT_TAG_VALUE]}]
    )
    vpcs = response.get("Vpcs", [])
    if vpcs:
        vpc_id = vpcs[0]["VpcId"]
        print_result("VPC exists with tag Project=handson", True, vpc_id)
        return True, vpc_id
    else:
        print_result("VPC exists with tag Project=handson", False, "No matching VPC found")
        return False, None


def check_subnets(ec2, vpc_id: str) -> bool:
    """
    Verify that both public and private subnets exist inside the VPC.

    Expects subnets tagged with:
        Tier=public  and  Tier=private

    Args:
        ec2:    boto3 EC2 client.
        vpc_id: VPC to search within.

    Returns:
        True if both subnet types are found.
    """
    response = ec2.describe_subnets(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )
    subnets = response.get("Subnets", [])

    public_subnets  = [s for s in subnets if get_tag(s.get("Tags", []), "Tier") == "public"]
    private_subnets = [s for s in subnets if get_tag(s.get("Tags", []), "Tier") == "private"]

    pub_ok  = len(public_subnets) > 0
    priv_ok = len(private_subnets) > 0

    print_result(
        "Public subnets tagged Tier=public",
        pub_ok,
        f"{len(public_subnets)} found" if pub_ok else "None found",
    )
    print_result(
        "Private subnets tagged Tier=private",
        priv_ok,
        f"{len(private_subnets)} found" if priv_ok else "None found",
    )

    return pub_ok and priv_ok


def check_ec2(ec2, vpc_id: str) -> bool:
    """
    Verify that at least one EC2 instance is running inside the VPC.

    Args:
        ec2:    boto3 EC2 client.
        vpc_id: VPC to search within.

    Returns:
        True if a running instance is found.
    """
    response = ec2.describe_instances(
        Filters=[
            {"Name": "vpc-id",          "Values": [vpc_id]},
            {"Name": "instance-state-name", "Values": ["running"]},
        ]
    )
    instances = [
        i
        for r in response.get("Reservations", [])
        for i in r.get("Instances", [])
    ]

    passed = len(instances) > 0
    detail = f"{len(instances)} running instance(s)" if passed else "No running instances found"
    print_result("EC2 instance(s) running in VPC", passed, detail)
    return passed


def check_rds(rds) -> bool:
    """
    Verify that at least one RDS instance tagged Project=handson is available.

    Args:
        rds: boto3 RDS client.

    Returns:
        True if an available RDS instance is found.
    """
    response = rds.describe_db_instances()
    db_instances = response.get("DBInstances", [])

    # Filter by tag (RDS tags require a separate API call per instance)
    available = []
    for db in db_instances:
        arn = db.get("DBInstanceArn", "")
        try:
            tag_response = rds.list_tags_for_resource(ResourceName=arn)
            tags = tag_response.get("TagList", [])
            if (
                get_tag(tags, PROJECT_TAG_KEY) == PROJECT_TAG_VALUE
                and db.get("DBInstanceStatus") == "available"
            ):
                available.append(db["DBInstanceIdentifier"])
        except ClientError:
            continue  # Skip instances we can't read tags for

    passed = len(available) > 0
    detail = f"identifier(s): {', '.join(available)}" if passed else "No available RDS instance with Project=handson tag"
    print_result("RDS instance available with tag Project=handson", passed, detail)
    return passed


# ── Main validation runner ────────────────────────────────────────────────────

def validate(region: str, profile: str | None) -> int:
    """
    Run all infrastructure validation checks.

    Args:
        region:  AWS region to validate.
        profile: Optional AWS CLI profile name.

    Returns:
        0 if all checks pass, 1 if any fail.
    """
    print(f"\n{BOLD}AWS Infrastructure Validation{RESET}")
    print(f"{INFO} Region : {region}")
    print(f"{INFO} Project: {PROJECT_TAG_VALUE}")
    print("-" * 55)

    # Build boto3 session
    session = boto3.Session(region_name=region, profile_name=profile)
    ec2 = session.client("ec2")
    rds = session.client("rds")

    results: list[bool] = []

    try:
        # 1. VPC
        vpc_ok, vpc_id = check_vpc(ec2)
        results.append(vpc_ok)

        if vpc_ok and vpc_id:
            # 2. Subnets (only meaningful if VPC exists)
            results.append(check_subnets(ec2, vpc_id))
            # 3. EC2
            results.append(check_ec2(ec2, vpc_id))
        else:
            print(f"  {WARN}  Skipping subnet and EC2 checks (no VPC found).")
            results += [False, False]

        # 4. RDS (not VPC-scoped in the API, filtered by tag)
        results.append(check_rds(rds))

    except NoCredentialsError:
        print(f"\n{FAIL}  AWS credentials not found. Configure via env vars or ~/.aws/credentials.")
        return 1
    except ClientError as exc:
        print(f"\n{FAIL}  AWS API error: {exc}")
        return 1

    # ── Summary ───────────────────────────────────────────────────────────────
    print("-" * 55)
    passed = sum(results)
    total  = len(results)
    if all(results):
        print(f"\n{PASS}  All {total}/{total} checks passed. Infrastructure looks good!\n")
        return 0
    else:
        print(f"\n{FAIL}  {passed}/{total} checks passed. Review the failures above.\n")
        return 1


# ── CLI entry point ───────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate AWS infrastructure created by Terraform.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  python infra_validator.py\n"
               "  python infra_validator.py --region us-east-1\n"
               "  python infra_validator.py --profile staging",
    )
    parser.add_argument("--region",  default="us-east-1", help="AWS region (default: us-east-1)")
    parser.add_argument("--profile", default=None,        help="AWS CLI profile name")
    args = parser.parse_args()

    sys.exit(validate(args.region, args.profile))


if __name__ == "__main__":
    main()
