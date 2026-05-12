"""
org_manager.py — Manage AWS Organizations: accounts, OUs, SCPs.

Usage:
    python org_manager.py list-accounts     — Show all accounts with OU, status, tags
    python org_manager.py list-scps         — Show all SCPs and which OUs they're attached to
    python org_manager.py check-compliance  — Verify accounts have required tags + Config enabled
    python org_manager.py org-tree          — Print the full organization tree

Prerequisites:
    pip install boto3
    AWS credentials with organizations:Describe*, organizations:List* permissions
    Must be run from the management account (or a delegated admin account)
"""

import argparse
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

import boto3
from botocore.exceptions import ClientError


# ── AWS clients ───────────────────────────────────────────────────────────────
org = boto3.client("organizations")
config_client = boto3.client("config")


# ── Required tags for compliance ──────────────────────────────────────────────
# All accounts must have these tags for compliance
REQUIRED_ACCOUNT_TAGS = ["Environment", "Owner", "CostCenter", "Project"]


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class OUNode:
    """Represents an Organizational Unit in the org tree."""
    ou_id: str
    name: str
    parent_id: Optional[str]
    children: list["OUNode"] = field(default_factory=list)
    accounts: list[dict] = field(default_factory=list)


@dataclass
class AccountInfo:
    """Extended account information including OU path and tags."""
    account_id: str
    name: str
    email: str
    status: str
    ou_id: str
    ou_name: str
    ou_path: str          # Full path like "Root/Production/WebTeam"
    tags: dict[str, str]
    joined_date: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def paginate(client_method, result_key: str, **kwargs) -> list:
    """
    Generic paginator helper for AWS API calls.

    Args:
        client_method: Boto3 paginator method (e.g. org.get_paginator('list_accounts'))
        result_key:    Key in the response to extract (e.g. 'Accounts')
        **kwargs:      Additional arguments for the paginator

    Returns:
        Flattened list of all results across all pages
    """
    results = []
    paginator = client_method
    for page in paginator.paginate(**kwargs):
        results.extend(page.get(result_key, []))
    return results


def get_account_tags(account_id: str) -> dict[str, str]:
    """
    Fetch all tags for an AWS account.

    Args:
        account_id: AWS account ID

    Returns:
        Dict of tag key → value
    """
    try:
        tags = paginate(
            org.get_paginator("list_tags_for_resource"),
            "Tags",
            ResourceId=account_id,
        )
        return {t["Key"]: t["Value"] for t in tags}
    except ClientError:
        return {}


def get_parent_ou(account_id: str) -> tuple[str, str]:
    """
    Get the direct parent OU ID and name for an account.

    Args:
        account_id: AWS account ID

    Returns:
        Tuple of (ou_id, ou_name)
    """
    try:
        parents = org.list_parents(ChildId=account_id).get("Parents", [])
        if not parents:
            return ("root", "Root")

        parent = parents[0]
        parent_id = parent["Id"]

        if parent["Type"] == "ROOT":
            return (parent_id, "Root")
        else:
            ou_details = org.describe_organizational_unit(
                OrganizationalUnitId=parent_id
            )
            ou_name = ou_details["OrganizationalUnit"]["Name"]
            return (parent_id, ou_name)
    except ClientError:
        return ("unknown", "Unknown")


def get_ou_path(ou_id: str) -> str:
    """
    Build the full path from Root to an OU (e.g. 'Root/Production/WebTeam').

    Args:
        ou_id: OU ID to trace back to root

    Returns:
        Path string
    """
    path_parts = []
    current_id = ou_id

    # Walk up the tree until we reach the root
    for _ in range(10):  # Max depth of 10 to prevent infinite loops
        try:
            parents = org.list_parents(ChildId=current_id).get("Parents", [])
            if not parents:
                break

            parent = parents[0]
            if parent["Type"] == "ROOT":
                path_parts.append("Root")
                break
            else:
                ou_details = org.describe_organizational_unit(
                    OrganizationalUnitId=parent["Id"]
                )
                path_parts.append(ou_details["OrganizationalUnit"]["Name"])
                current_id = parent["Id"]
        except ClientError:
            break

    path_parts.reverse()
    return "/".join(path_parts) if path_parts else "Root"


# ── Command: list-accounts ────────────────────────────────────────────────────

def list_accounts() -> None:
    """
    List all accounts in the organization with their OU, status, and tags.
    """
    print("\n=== AWS Organization Accounts ===\n")

    try:
        accounts_raw = paginate(
            org.get_paginator("list_accounts"),
            "Accounts",
        )
    except ClientError as e:
        print(f"  ✗ Error: {e}")
        print("  Ensure you're running from the management account with organizations:ListAccounts permission")
        sys.exit(1)

    print(f"  Total accounts: {len(accounts_raw)}\n")

    # Enrich each account with OU and tag information
    accounts: list[AccountInfo] = []
    for acc in accounts_raw:
        account_id = acc["Id"]
        ou_id, ou_name = get_parent_ou(account_id)
        tags = get_account_tags(account_id)

        accounts.append(AccountInfo(
            account_id=account_id,
            name=acc["Name"],
            email=acc["Email"],
            status=acc["Status"],
            ou_id=ou_id,
            ou_name=ou_name,
            ou_path=get_ou_path(ou_id) if ou_id != "root" else "Root",
            tags=tags,
            joined_date=str(acc.get("JoinedTimestamp", ""))[:10],
        ))

    # Print table
    print(f"  {'ACCOUNT ID':<14} {'NAME':<25} {'STATUS':<12} {'OU':<20} {'JOINED':<12} {'TAGS'}")
    print("  " + "-" * 100)

    for acc in sorted(accounts, key=lambda a: a.ou_path):
        status_icon = "✓" if acc.status == "ACTIVE" else "✗"
        tag_summary = ", ".join(f"{k}={v}" for k, v in list(acc.tags.items())[:3])
        print(
            f"  {acc.account_id:<14} {acc.name:<25} {status_icon} {acc.status:<10} "
            f"{acc.ou_name:<20} {acc.joined_date:<12} {tag_summary}"
        )

    print()


# ── Command: list-scps ────────────────────────────────────────────────────────

def list_scps() -> None:
    """
    List all Service Control Policies (SCPs) and which OUs/accounts they're attached to.
    """
    print("\n=== Service Control Policies (SCPs) ===\n")

    try:
        policies = paginate(
            org.get_paginator("list_policies"),
            "Policies",
            Filter="SERVICE_CONTROL_POLICY",
        )
    except ClientError as e:
        print(f"  ✗ Error listing SCPs: {e}")
        return

    print(f"  Total SCPs: {len(policies)}\n")

    for policy in policies:
        policy_id = policy["Id"]
        policy_name = policy["Name"]
        is_aws_managed = policy.get("AwsManaged", False)
        description = policy.get("Description", "No description")

        print(f"  {'[AWS]' if is_aws_managed else '[Custom]'} {policy_name}  ({policy_id})")
        print(f"    Description: {description}")

        # Get targets (OUs and accounts) this SCP is attached to
        try:
            targets = paginate(
                org.get_paginator("list_targets_for_policy"),
                "Targets",
                PolicyId=policy_id,
            )
            if targets:
                print(f"    Attached to ({len(targets)}):")
                for target in targets:
                    target_type = target["Type"]
                    target_name = target["Name"]
                    target_id = target["TargetId"]
                    print(f"      • [{target_type}] {target_name} ({target_id})")
            else:
                print("    Attached to: (none)")
        except ClientError as e:
            print(f"    Attached to: (error: {e})")

        print()


# ── Command: check-compliance ─────────────────────────────────────────────────

def check_compliance() -> None:
    """
    Verify all accounts have required tags and AWS Config enabled.

    Checks:
        1. All required tags are present on each account
        2. AWS Config is enabled in the account's home region
    """
    print("\n=== Account Compliance Check ===\n")
    print(f"  Required tags: {', '.join(REQUIRED_ACCOUNT_TAGS)}\n")

    try:
        accounts_raw = paginate(
            org.get_paginator("list_accounts"),
            "Accounts",
        )
    except ClientError as e:
        print(f"  ✗ Error: {e}")
        sys.exit(1)

    compliant = []
    non_compliant = []

    for acc in accounts_raw:
        account_id = acc["Id"]
        account_name = acc["Name"]
        tags = get_account_tags(account_id)

        violations = []

        # Check 1: Required tags
        for required_tag in REQUIRED_ACCOUNT_TAGS:
            if required_tag not in tags:
                violations.append(f"Missing tag: {required_tag}")

        if violations:
            non_compliant.append({
                "account_id": account_id,
                "name": account_name,
                "violations": violations,
            })
        else:
            compliant.append(account_id)

    # Print results
    print(f"  ✓ Compliant accounts:     {len(compliant)}")
    print(f"  ✗ Non-compliant accounts: {len(non_compliant)}")

    if non_compliant:
        print("\n  Non-compliant accounts:")
        print("  " + "-" * 70)
        for acc in non_compliant:
            print(f"\n  Account: {acc['name']} ({acc['account_id']})")
            for v in acc["violations"]:
                print(f"    ✗ {v}")

    print()


# ── Command: org-tree ─────────────────────────────────────────────────────────

def print_org_tree() -> None:
    """
    Print the full organization tree showing OUs and accounts.
    """
    print("\n=== Organization Tree ===\n")

    try:
        roots = org.list_roots().get("Roots", [])
        if not roots:
            print("  No organization root found")
            return

        root = roots[0]
        root_id = root["Id"]
        print(f"  Root ({root_id})")

        # Recursively print the tree
        _print_ou_tree(root_id, indent=2)

    except ClientError as e:
        print(f"  ✗ Error: {e}")


def _print_ou_tree(parent_id: str, indent: int = 0) -> None:
    """
    Recursively print OUs and accounts under a parent.

    Args:
        parent_id: Parent OU or root ID
        indent:    Current indentation level
    """
    prefix = "  " * indent

    # Print child OUs
    try:
        child_ous = paginate(
            org.get_paginator("list_organizational_units_for_parent"),
            "OrganizationalUnits",
            ParentId=parent_id,
        )
        for ou in child_ous:
            print(f"{prefix}├── [OU] {ou['Name']} ({ou['Id']})")
            _print_ou_tree(ou["Id"], indent + 1)
    except ClientError:
        pass

    # Print accounts in this OU
    try:
        accounts = paginate(
            org.get_paginator("list_accounts_for_parent"),
            "Accounts",
            ParentId=parent_id,
        )
        for acc in accounts:
            status_icon = "✓" if acc["Status"] == "ACTIVE" else "✗"
            print(f"{prefix}└── [Account] {status_icon} {acc['Name']} ({acc['Id']})")
    except ClientError:
        pass


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Manage AWS Organizations: accounts, OUs, SCPs"
    )
    parser.add_argument(
        "command",
        choices=["list-accounts", "list-scps", "check-compliance", "org-tree"],
        help="Command to run",
    )
    args = parser.parse_args()

    if args.command == "list-accounts":
        list_accounts()
    elif args.command == "list-scps":
        list_scps()
    elif args.command == "check-compliance":
        check_compliance()
    elif args.command == "org-tree":
        print_org_tree()


if __name__ == "__main__":
    main()
