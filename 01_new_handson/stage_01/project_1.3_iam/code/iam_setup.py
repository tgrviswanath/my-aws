"""
iam_setup.py — Automate IAM setup: users, groups, roles, and policies.

Prerequisites:
    pip install boto3

IAM Permissions Required (run with admin or IAM full-access):
    iam:CreateGroup, iam:CreateUser, iam:CreateRole
    iam:AttachGroupPolicy, iam:AttachRolePolicy
    iam:AddUserToGroup, iam:CreateInstanceProfile
    iam:AddRoleToInstanceProfile

Usage:
    python iam_setup.py [--profile <aws-profile>] [--dry-run]

What this script creates:
    Groups:
        - developers   → AmazonS3ReadOnlyAccess + AmazonEC2ReadOnlyAccess
        - readonly     → ReadOnlyAccess (AWS managed)
    Users:
        - dev-user-1, dev-user-2  → added to 'developers' group
        - readonly-user-1         → added to 'readonly' group
    Roles:
        - ec2-s3-access-role      → EC2 instance role with S3 full access
    Instance Profile:
        - ec2-s3-access-profile   → wraps the EC2 role for instance attachment
"""

import argparse
import json
import sys
from typing import Any

import boto3
from botocore.exceptions import ClientError, NoCredentialsError


# ── IAM resource definitions ──────────────────────────────────────────────────

GROUPS = [
    {
        "name": "developers",
        "description": "Developer group — S3 read + EC2 describe",
        "policies": [
            "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess",
            "arn:aws:iam::aws:policy/AmazonEC2ReadOnlyAccess",
        ],
    },
    {
        "name": "readonly",
        "description": "Read-only access to all AWS services",
        "policies": [
            "arn:aws:iam::aws:policy/ReadOnlyAccess",
        ],
    },
]

USERS = [
    {"name": "dev-user-1",      "group": "developers"},
    {"name": "dev-user-2",      "group": "developers"},
    {"name": "readonly-user-1", "group": "readonly"},
]

ROLES = [
    {
        "name": "ec2-s3-access-role",
        "description": "EC2 instance role — allows S3 full access",
        "service": "ec2.amazonaws.com",
        "policies": [
            "arn:aws:iam::aws:policy/AmazonS3FullAccess",
        ],
        "create_instance_profile": True,
    },
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def safe_create(action_name: str, fn, *args, **kwargs) -> tuple[bool, Any]:
    """
    Call fn(*args, **kwargs) and handle EntityAlreadyExists gracefully.
    Returns (created: bool, response: Any).
    """
    try:
        result = fn(*args, **kwargs)
        return True, result
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code in ("EntityAlreadyExists", "NoSuchEntity"):
            return False, None
        raise


def build_assume_role_policy(service: str) -> str:
    """Return a trust policy document allowing the given AWS service to assume the role."""
    return json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": service},
                "Action": "sts:AssumeRole",
            }
        ],
    })


# ── Group setup ───────────────────────────────────────────────────────────────

def setup_groups(iam, dry_run: bool) -> list[str]:
    """Create IAM groups and attach managed policies."""
    print("\n── Groups ──────────────────────────────────────────────────────")
    created_groups = []

    for group_def in GROUPS:
        name = group_def["name"]

        if dry_run:
            print(f"  [DRY-RUN] Would create group: {name}")
            created_groups.append(name)
            continue

        created, _ = safe_create(
            f"create group {name}",
            iam.create_group,
            GroupName=name,
        )
        status = "created" if created else "already exists"
        print(f"  [+] Group '{name}' — {status}")

        # Attach managed policies
        for policy_arn in group_def["policies"]:
            try:
                iam.attach_group_policy(GroupName=name, PolicyArn=policy_arn)
                print(f"      ↳ Attached: {policy_arn.split('/')[-1]}")
            except ClientError as e:
                if e.response["Error"]["Code"] != "EntityAlreadyExists":
                    raise

        created_groups.append(name)

    return created_groups


# ── User setup ────────────────────────────────────────────────────────────────

def setup_users(iam, dry_run: bool) -> list[str]:
    """Create IAM users and add them to their respective groups."""
    print("\n── Users ───────────────────────────────────────────────────────")
    created_users = []

    for user_def in USERS:
        name = user_def["name"]
        group = user_def["group"]

        if dry_run:
            print(f"  [DRY-RUN] Would create user: {name} → group: {group}")
            created_users.append(name)
            continue

        created, _ = safe_create(
            f"create user {name}",
            iam.create_user,
            UserName=name,
            Tags=[
                {"Key": "ManagedBy", "Value": "iam_setup.py"},
                {"Key": "Group",     "Value": group},
            ],
        )
        status = "created" if created else "already exists"
        print(f"  [+] User '{name}' — {status}")

        # Add to group
        try:
            iam.add_user_to_group(GroupName=group, UserName=name)
            print(f"      ↳ Added to group: {group}")
        except ClientError as e:
            if e.response["Error"]["Code"] != "EntityAlreadyExists":
                raise

        created_users.append(name)

    return created_users


# ── Role setup ────────────────────────────────────────────────────────────────

def setup_roles(iam, dry_run: bool) -> list[str]:
    """Create IAM roles, attach policies, and optionally create instance profiles."""
    print("\n── Roles ───────────────────────────────────────────────────────")
    created_roles = []

    for role_def in ROLES:
        name = role_def["name"]
        service = role_def["service"]

        if dry_run:
            print(f"  [DRY-RUN] Would create role: {name} (service: {service})")
            created_roles.append(name)
            continue

        trust_policy = build_assume_role_policy(service)

        created, _ = safe_create(
            f"create role {name}",
            iam.create_role,
            RoleName=name,
            AssumeRolePolicyDocument=trust_policy,
            Description=role_def["description"],
            Tags=[
                {"Key": "ManagedBy", "Value": "iam_setup.py"},
            ],
        )
        status = "created" if created else "already exists"
        print(f"  [+] Role '{name}' — {status}")

        # Attach managed policies
        for policy_arn in role_def["policies"]:
            try:
                iam.attach_role_policy(RoleName=name, PolicyArn=policy_arn)
                print(f"      ↳ Attached: {policy_arn.split('/')[-1]}")
            except ClientError as e:
                if e.response["Error"]["Code"] != "EntityAlreadyExists":
                    raise

        # Create instance profile (needed to attach role to EC2 instances)
        if role_def.get("create_instance_profile"):
            profile_name = f"{name}-profile"
            created_profile, _ = safe_create(
                f"create instance profile {profile_name}",
                iam.create_instance_profile,
                InstanceProfileName=profile_name,
            )
            if created_profile:
                iam.add_role_to_instance_profile(
                    InstanceProfileName=profile_name,
                    RoleName=name,
                )
                print(f"      ↳ Instance profile '{profile_name}' created and linked")
            else:
                print(f"      ↳ Instance profile '{profile_name}' already exists")

        created_roles.append(name)

    return created_roles


# ── Summary ───────────────────────────────────────────────────────────────────

def print_summary(groups: list, users: list, roles: list, dry_run: bool):
    """Print a summary of all IAM resources created."""
    mode = " [DRY-RUN]" if dry_run else ""
    print("\n" + "=" * 60)
    print(f"  IAM Setup Summary{mode}")
    print("=" * 60)
    print(f"  Groups created : {len(groups)}")
    for g in groups:
        print(f"    - {g}")
    print(f"  Users created  : {len(users)}")
    for u in users:
        print(f"    - {u}")
    print(f"  Roles created  : {len(roles)}")
    for r in roles:
        print(f"    - {r}")
    print("=" * 60)
    if not dry_run:
        print("\n  Next steps:")
        print("  1. Generate access keys for users via AWS Console or CLI")
        print("  2. Attach the EC2 instance profile to your EC2 instances")
        print("  3. Review permissions in IAM Console → Access Analyzer")
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Automate IAM setup.")
    parser.add_argument("--profile", help="AWS profile name", default=None)
    parser.add_argument("--region",  help="AWS region",       default="us-east-1")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be created without making changes")
    args = parser.parse_args()

    if args.dry_run:
        print("[DRY-RUN MODE] No changes will be made to AWS.")

    try:
        session = boto3.Session(profile_name=args.profile, region_name=args.region)
        iam = session.client("iam")
    except NoCredentialsError:
        print("[ERROR] No AWS credentials found. Run 'aws configure'.")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("  IAM Setup — Creating Groups, Users, and Roles")
    print("=" * 60)

    groups = setup_groups(iam, args.dry_run)
    users  = setup_users(iam, args.dry_run)
    roles  = setup_roles(iam, args.dry_run)

    print_summary(groups, users, roles, args.dry_run)


if __name__ == "__main__":
    main()
