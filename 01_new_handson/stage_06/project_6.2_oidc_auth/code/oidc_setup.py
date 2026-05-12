"""
oidc_setup.py — Set up OIDC trust between GitHub Actions and AWS IAM.

Usage:
    python oidc_setup.py --repo owner/repo --role-name ROLE_NAME [options]

Description:
    1. Creates (or reuses) the GitHub Actions OIDC identity provider in IAM.
    2. Creates an IAM role with a trust policy scoped to the specific GitHub repo.
    3. Attaches managed policies for ECR push and ECS deploy permissions.
    4. Prints the role ARN to use in your GitHub Actions workflow.

The trust policy restricts token acceptance to:
    - Issuer  : token.actions.githubusercontent.com
    - Audience: sts.amazonaws.com
    - Subject : repo:<owner>/<repo>:ref:refs/heads/<branch>  (or wildcard)

Requirements:
    - AWS credentials with iam:* permissions.
"""

import sys
import json
import argparse

import boto3
from botocore.exceptions import ClientError, NoCredentialsError


# ── ANSI colors ───────────────────────────────────────────────────────────────
class C:
    RESET  = "\033[0m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    RED    = "\033[91m"
    CYAN   = "\033[96m"
    BOLD   = "\033[1m"


def info(msg):  print(f"{C.CYAN}[INFO]{C.RESET}  {msg}")
def ok(msg):    print(f"{C.GREEN}[OK]{C.RESET}    {msg}")
def warn(msg):  print(f"{C.YELLOW}[WARN]{C.RESET}  {msg}")
def err(msg):   print(f"{C.RED}[ERR]{C.RESET}   {msg}", file=sys.stderr)


# ── Constants ─────────────────────────────────────────────────────────────────

GITHUB_OIDC_URL       = "https://token.actions.githubusercontent.com"
GITHUB_OIDC_THUMBPRINT = "6938fd4d98bab03faadb97b34396831e3780aea1"  # GitHub's current thumbprint

# Managed policies to attach to the role
MANAGED_POLICIES = [
    "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser",  # ECR push/pull
    "arn:aws:iam::aws:policy/AmazonECS_FullAccess",                 # ECS deploy
]


# ── OIDC provider ─────────────────────────────────────────────────────────────

def ensure_oidc_provider(iam, account_id: str) -> str:
    """
    Create the GitHub Actions OIDC identity provider if it does not exist.

    The provider is account-scoped; only one is needed per AWS account.

    Args:
        iam:        boto3 IAM client.
        account_id: AWS account ID (used to check for existing provider).

    Returns:
        ARN of the OIDC provider.
    """
    expected_arn = f"arn:aws:iam::{account_id}:oidc-provider/token.actions.githubusercontent.com"

    # Check if it already exists
    try:
        iam.get_open_id_connect_provider(OpenIDConnectProviderArn=expected_arn)
        warn(f"OIDC provider already exists: {expected_arn}")
        return expected_arn
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "NoSuchEntityException":
            raise

    # Create it
    info("Creating GitHub Actions OIDC identity provider …")
    response = iam.create_open_id_connect_provider(
        Url=GITHUB_OIDC_URL,
        ClientIDList=["sts.amazonaws.com"],
        ThumbprintList=[GITHUB_OIDC_THUMBPRINT],
    )
    arn = response["OpenIDConnectProviderArn"]
    ok(f"OIDC provider created: {arn}")
    return arn


# ── Trust policy ──────────────────────────────────────────────────────────────

def build_trust_policy(account_id: str, repo: str, branch: str) -> dict:
    """
    Build the IAM role trust policy for GitHub Actions OIDC.

    The subject condition restricts which GitHub Actions workflows can assume
    the role. Using a specific branch (e.g. 'main') is more secure than '*'.

    Args:
        account_id: AWS account ID.
        repo:       GitHub repository in 'owner/repo' format.
        branch:     Branch to restrict to, or '*' for any branch.

    Returns:
        Trust policy document as a dict.
    """
    if branch == "*":
        subject = f"repo:{repo}:*"
    else:
        subject = f"repo:{repo}:ref:refs/heads/{branch}"

    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Federated": f"arn:aws:iam::{account_id}:oidc-provider/token.actions.githubusercontent.com"
                },
                "Action": "sts:AssumeRoleWithWebIdentity",
                "Condition": {
                    "StringEquals": {
                        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
                    },
                    "StringLike": {
                        "token.actions.githubusercontent.com:sub": subject
                    },
                },
            }
        ],
    }


# ── IAM role ──────────────────────────────────────────────────────────────────

def create_or_update_role(iam, role_name: str, trust_policy: dict, description: str) -> str:
    """
    Create an IAM role with the given trust policy, or update the trust policy
    if the role already exists.

    Args:
        iam:          boto3 IAM client.
        role_name:    IAM role name.
        trust_policy: Trust policy document dict.
        description:  Role description.

    Returns:
        Role ARN.
    """
    trust_json = json.dumps(trust_policy)

    try:
        response = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=trust_json,
            Description=description,
            MaxSessionDuration=3600,  # 1 hour
        )
        arn = response["Role"]["Arn"]
        ok(f"IAM role created: {arn}")
        return arn
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "EntityAlreadyExists":
            raise
        warn(f"Role '{role_name}' already exists — updating trust policy.")
        iam.update_assume_role_policy(
            RoleName=role_name,
            PolicyDocument=trust_json,
        )
        response = iam.get_role(RoleName=role_name)
        arn = response["Role"]["Arn"]
        ok(f"Trust policy updated for role: {arn}")
        return arn


def attach_policies(iam, role_name: str, policy_arns: list[str]) -> None:
    """
    Attach managed policies to the IAM role.

    Args:
        iam:         boto3 IAM client.
        role_name:   IAM role name.
        policy_arns: List of managed policy ARNs to attach.
    """
    for arn in policy_arns:
        try:
            iam.attach_role_policy(RoleName=role_name, PolicyArn=arn)
            ok(f"Attached policy: {arn.split('/')[-1]}")
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "EntityAlreadyExists":
                warn(f"Policy already attached: {arn.split('/')[-1]}")
            else:
                raise


# ── Main ──────────────────────────────────────────────────────────────────────

def setup_oidc(
    repo: str,
    role_name: str,
    branch: str,
    region: str,
    profile: str | None,
) -> int:
    """
    Full OIDC setup workflow.

    Args:
        repo:      GitHub repository ('owner/repo').
        role_name: IAM role name to create.
        branch:    Branch to restrict the trust to.
        region:    AWS region.
        profile:   Optional AWS CLI profile.

    Returns:
        0 on success, 1 on failure.
    """
    session    = boto3.Session(region_name=region, profile_name=profile)
    iam        = session.client("iam")
    sts        = session.client("sts")

    print(f"\n{C.BOLD}GitHub Actions OIDC Setup{C.RESET}")
    info(f"Repository : {repo}")
    info(f"Role name  : {role_name}")
    info(f"Branch     : {branch}")
    print()

    try:
        # Get account ID
        account_id = sts.get_caller_identity()["Account"]
        info(f"AWS account: {account_id}")

        # 1. Ensure OIDC provider exists
        ensure_oidc_provider(iam, account_id)

        # 2. Build trust policy
        trust_policy = build_trust_policy(account_id, repo, branch)

        # 3. Create or update the IAM role
        role_arn = create_or_update_role(
            iam, role_name, trust_policy,
            description=f"GitHub Actions OIDC role for {repo}",
        )

        # 4. Attach permissions
        info("Attaching permissions …")
        attach_policies(iam, role_name, MANAGED_POLICIES)

    except ClientError as exc:
        err(f"AWS API error: {exc}")
        return 1

    # 5. Print usage instructions
    print(f"\n{C.BOLD}{'─' * 60}{C.RESET}")
    print(f"{C.BOLD}Role ARN (add to GitHub Actions workflow):{C.RESET}\n")
    print(f"  {C.GREEN}{role_arn}{C.RESET}\n")
    print(f"{C.BOLD}Example GitHub Actions step:{C.RESET}\n")
    print(f"  - name: Configure AWS credentials")
    print(f"    uses: aws-actions/configure-aws-credentials@v4")
    print(f"    with:")
    print(f"      role-to-assume: {role_arn}")
    print(f"      aws-region: {region}")
    print(f"\n{C.BOLD}Required workflow permissions:{C.RESET}")
    print(f"  permissions:")
    print(f"    id-token: write")
    print(f"    contents: read")
    print(f"{C.BOLD}{'─' * 60}{C.RESET}\n")

    return 0


# ── CLI entry point ───────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Set up OIDC trust between GitHub Actions and AWS IAM.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  python oidc_setup.py --repo myorg/my-app --role-name GitHubActionsRole\n"
               "  python oidc_setup.py --repo myorg/my-app --role-name GitHubActionsRole --branch main",
    )
    parser.add_argument("--repo",      required=True, help="GitHub repository in 'owner/repo' format.")
    parser.add_argument("--role-name", required=True, help="IAM role name to create.")
    parser.add_argument("--branch",    default="main", help="Branch to restrict trust to (default: main). Use '*' for any branch.")
    parser.add_argument("--region",    default="us-east-1", help="AWS region (default: us-east-1).")
    parser.add_argument("--profile",   default=None,        help="AWS CLI profile name.")
    args = parser.parse_args()

    try:
        rc = setup_oidc(args.repo, args.role_name, args.branch, args.region, args.profile)
    except NoCredentialsError:
        err("AWS credentials not found.")
        rc = 1

    sys.exit(rc)


if __name__ == "__main__":
    main()
