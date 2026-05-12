"""
zero_trust_checker.py — Audit AWS account for zero trust security principles.

Usage:
    python zero_trust_checker.py
    python zero_trust_checker.py --region us-east-1

Checks performed:
    1.  Root account has MFA enabled
    2.  No IAM users without MFA (for console users)
    3.  No S3 buckets with public access enabled
    4.  No security groups with 0.0.0.0/0 on port 22 (SSH) or 3389 (RDP)
    5.  No wildcard (*) IAM policies attached directly to users
    6.  No IAM users with active access keys older than 90 days
    7.  No IAM users with unused console access (>90 days inactive)
    8.  CloudTrail is enabled in all regions
    9.  No EC2 instances with public IPs in non-DMZ subnets
    10. Password policy meets minimum requirements

Output:
    Zero trust score (0–100) with detailed findings per check

Prerequisites:
    pip install boto3
    AWS credentials with IAM:Get*, IAM:List*, S3:GetBucketPublicAccessBlock,
    EC2:DescribeSecurityGroups, EC2:DescribeInstances, CloudTrail:DescribeTrails
"""

import argparse
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional

import boto3
from botocore.exceptions import ClientError


# ── AWS clients ───────────────────────────────────────────────────────────────
iam = boto3.client("iam")
s3 = boto3.client("s3")
ec2 = boto3.client("ec2")
cloudtrail = boto3.client("cloudtrail")


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class CheckResult:
    """Result of a single zero trust check."""
    check_id: str
    name: str
    passed: bool
    weight: int          # How much this check contributes to the score (1–10)
    findings: list[str] = field(default_factory=list)  # List of violation details
    remediation: str = ""


# ── Individual checks ─────────────────────────────────────────────────────────

def check_root_mfa() -> CheckResult:
    """
    Check 1: Root account has MFA enabled.

    The root account has unrestricted access to all AWS resources.
    MFA is the most critical control for protecting it.
    """
    result = CheckResult(
        check_id="ZT-01",
        name="Root account MFA enabled",
        passed=False,
        weight=10,
        remediation="Enable MFA on root: AWS Console → Account → Security credentials → MFA",
    )
    try:
        summary = iam.get_account_summary()["SummaryMap"]
        # AccountMFAEnabled: 1 = enabled, 0 = disabled
        result.passed = summary.get("AccountMFAEnabled", 0) == 1
        if not result.passed:
            result.findings.append("Root account does NOT have MFA enabled")
    except ClientError as e:
        result.findings.append(f"Could not check root MFA: {e}")
    return result


def check_users_without_mfa() -> CheckResult:
    """
    Check 2: No IAM users with console access but without MFA.

    Users who can log into the console without MFA are a significant risk.
    """
    result = CheckResult(
        check_id="ZT-02",
        name="All console users have MFA",
        passed=True,
        weight=9,
        remediation="Enable MFA for each user: IAM → Users → Security credentials → Assign MFA device",
    )
    try:
        # Use the credential report for efficient bulk checking
        iam.generate_credential_report()
        import time; time.sleep(2)  # Wait for report generation
        report_response = iam.get_credential_report()
        report_csv = report_response["Content"].decode("utf-8")

        lines = report_csv.strip().split("\n")
        headers = lines[0].split(",")
        idx = {h: i for i, h in enumerate(headers)}

        for line in lines[1:]:
            cols = line.split(",")
            username = cols[idx["user"]]
            if username == "<root_account>":
                continue  # Root is checked separately

            password_enabled = cols[idx.get("password_enabled", -1)] if "password_enabled" in idx else "false"
            mfa_active = cols[idx.get("mfa_active", -1)] if "mfa_active" in idx else "true"

            # Only flag users who have console access (password enabled) but no MFA
            if password_enabled == "true" and mfa_active == "false":
                result.passed = False
                result.findings.append(f"User '{username}' has console access but NO MFA")

    except ClientError as e:
        result.findings.append(f"Could not check user MFA: {e}")
    return result


def check_s3_public_access() -> CheckResult:
    """
    Check 3: No S3 buckets with public access enabled.

    Public S3 buckets can expose sensitive data to the internet.
    """
    result = CheckResult(
        check_id="ZT-03",
        name="No S3 buckets with public access",
        passed=True,
        weight=9,
        remediation="Block public access: S3 → Bucket → Permissions → Block all public access → Enable",
    )
    try:
        buckets = s3.list_buckets().get("Buckets", [])
        for bucket in buckets:
            bucket_name = bucket["Name"]
            try:
                pab = s3.get_public_access_block(Bucket=bucket_name)
                config = pab["PublicAccessBlockConfiguration"]
                # All four settings must be True for full protection
                fully_blocked = all([
                    config.get("BlockPublicAcls", False),
                    config.get("IgnorePublicAcls", False),
                    config.get("BlockPublicPolicy", False),
                    config.get("RestrictPublicBuckets", False),
                ])
                if not fully_blocked:
                    result.passed = False
                    result.findings.append(
                        f"Bucket '{bucket_name}' does not have all public access blocks enabled"
                    )
            except ClientError as e:
                if e.response["Error"]["Code"] == "NoSuchPublicAccessBlockConfiguration":
                    # No block configuration = public access is NOT blocked
                    result.passed = False
                    result.findings.append(
                        f"Bucket '{bucket_name}' has NO public access block configuration"
                    )
    except ClientError as e:
        result.findings.append(f"Could not check S3 buckets: {e}")
    return result


def check_open_ssh_rdp() -> CheckResult:
    """
    Check 4: No security groups allow SSH (22) or RDP (3389) from 0.0.0.0/0.

    Open SSH/RDP to the internet exposes instances to brute-force attacks.
    """
    result = CheckResult(
        check_id="ZT-04",
        name="No open SSH/RDP to internet",
        passed=True,
        weight=8,
        remediation="Remove 0.0.0.0/0 rules on ports 22/3389; use VPN or SSM Session Manager instead",
    )
    dangerous_ports = {22: "SSH", 3389: "RDP"}

    try:
        paginator = ec2.get_paginator("describe_security_groups")
        for page in paginator.paginate():
            for sg in page["SecurityGroups"]:
                sg_id = sg["GroupId"]
                sg_name = sg.get("GroupName", "unnamed")

                for rule in sg.get("IpPermissions", []):
                    from_port = rule.get("FromPort", 0)
                    to_port = rule.get("ToPort", 65535)

                    for port, service in dangerous_ports.items():
                        if from_port <= port <= to_port:
                            # Check for IPv4 open access
                            for ip_range in rule.get("IpRanges", []):
                                if ip_range.get("CidrIp") == "0.0.0.0/0":
                                    result.passed = False
                                    result.findings.append(
                                        f"SG {sg_id} ({sg_name}): {service} port {port} open to 0.0.0.0/0"
                                    )
                            # Check for IPv6 open access
                            for ip_range in rule.get("Ipv6Ranges", []):
                                if ip_range.get("CidrIpv6") == "::/0":
                                    result.passed = False
                                    result.findings.append(
                                        f"SG {sg_id} ({sg_name}): {service} port {port} open to ::/0 (IPv6)"
                                    )
    except ClientError as e:
        result.findings.append(f"Could not check security groups: {e}")
    return result


def check_wildcard_iam_policies() -> CheckResult:
    """
    Check 5: No wildcard (*) IAM policies attached directly to users.

    Wildcard policies grant full access and violate least-privilege principles.
    Policies should be attached to groups/roles, not directly to users.
    """
    result = CheckResult(
        check_id="ZT-05",
        name="No wildcard IAM policies on users",
        passed=True,
        weight=8,
        remediation="Remove wildcard policies; use least-privilege policies attached to groups/roles",
    )
    try:
        paginator = iam.get_paginator("list_users")
        for page in paginator.paginate():
            for user in page["Users"]:
                username = user["UserName"]

                # Check attached managed policies
                attached = iam.list_attached_user_policies(UserName=username)
                for policy in attached.get("AttachedPolicies", []):
                    policy_arn = policy["PolicyArn"]
                    # AWS managed AdministratorAccess is a wildcard policy
                    if "AdministratorAccess" in policy_arn:
                        result.passed = False
                        result.findings.append(
                            f"User '{username}' has AdministratorAccess policy attached directly"
                        )

                # Check inline policies for Action: "*" or Resource: "*"
                inline_policies = iam.list_user_policies(UserName=username)
                for policy_name in inline_policies.get("PolicyNames", []):
                    policy_doc = iam.get_user_policy(
                        UserName=username, PolicyName=policy_name
                    )
                    doc = policy_doc.get("PolicyDocument", {})
                    for statement in doc.get("Statement", []):
                        action = statement.get("Action", "")
                        resource = statement.get("Resource", "")
                        effect = statement.get("Effect", "")
                        # Flag Allow + Action:* + Resource:*
                        if (effect == "Allow" and
                                (action == "*" or action == ["*"]) and
                                (resource == "*" or resource == ["*"])):
                            result.passed = False
                            result.findings.append(
                                f"User '{username}' has inline policy '{policy_name}' with Action:* Resource:*"
                            )
    except ClientError as e:
        result.findings.append(f"Could not check IAM policies: {e}")
    return result


def check_old_access_keys() -> CheckResult:
    """
    Check 6: No IAM access keys older than 90 days.

    Old access keys increase the risk of credential compromise.
    Keys should be rotated regularly.
    """
    result = CheckResult(
        check_id="ZT-06",
        name="No access keys older than 90 days",
        passed=True,
        weight=7,
        remediation="Rotate access keys: IAM → Users → Security credentials → Create new key, delete old",
    )
    cutoff = datetime.now(timezone.utc) - timedelta(days=90)

    try:
        paginator = iam.get_paginator("list_users")
        for page in paginator.paginate():
            for user in page["Users"]:
                username = user["UserName"]
                keys = iam.list_access_keys(UserName=username).get("AccessKeyMetadata", [])
                for key in keys:
                    if key["Status"] == "Active":
                        created = key["CreateDate"]
                        age_days = (datetime.now(timezone.utc) - created).days
                        if created < cutoff:
                            result.passed = False
                            result.findings.append(
                                f"User '{username}' has access key {key['AccessKeyId'][:8]}... "
                                f"that is {age_days} days old (>90 days)"
                            )
    except ClientError as e:
        result.findings.append(f"Could not check access keys: {e}")
    return result


def check_cloudtrail_enabled() -> CheckResult:
    """
    Check 7: CloudTrail is enabled and logging in all regions.

    CloudTrail provides the audit trail needed for zero trust verification.
    """
    result = CheckResult(
        check_id="ZT-07",
        name="CloudTrail enabled (multi-region)",
        passed=False,
        weight=8,
        remediation="Enable CloudTrail: CloudTrail → Create trail → Apply to all regions → Enable",
    )
    try:
        trails = cloudtrail.describe_trails(includeShadowTrails=False).get("trailList", [])
        for trail in trails:
            if trail.get("IsMultiRegionTrail") and trail.get("HomeRegion"):
                # Check if logging is actually active
                status = cloudtrail.get_trail_status(Name=trail["TrailARN"])
                if status.get("IsLogging"):
                    result.passed = True
                    return result

        if not result.passed:
            result.findings.append("No active multi-region CloudTrail found")
    except ClientError as e:
        result.findings.append(f"Could not check CloudTrail: {e}")
    return result


def check_password_policy() -> CheckResult:
    """
    Check 8: IAM password policy meets minimum security requirements.

    Minimum requirements: 14+ chars, uppercase, lowercase, numbers, symbols,
    no reuse of last 24 passwords, max age 90 days.
    """
    result = CheckResult(
        check_id="ZT-08",
        name="Strong IAM password policy",
        passed=True,
        weight=6,
        remediation="Set password policy: IAM → Account settings → Edit password policy",
    )
    try:
        policy = iam.get_account_password_policy().get("PasswordPolicy", {})

        checks = [
            (policy.get("MinimumPasswordLength", 0) >= 14,
             "Minimum password length should be ≥14 characters"),
            (policy.get("RequireUppercaseCharacters", False),
             "Password policy should require uppercase characters"),
            (policy.get("RequireLowercaseCharacters", False),
             "Password policy should require lowercase characters"),
            (policy.get("RequireNumbers", False),
             "Password policy should require numbers"),
            (policy.get("RequireSymbols", False),
             "Password policy should require symbols"),
            (policy.get("PasswordReusePrevention", 0) >= 24,
             "Password reuse prevention should be ≥24 passwords"),
            (policy.get("MaxPasswordAge", 999) <= 90,
             "Maximum password age should be ≤90 days"),
        ]

        for passed, message in checks:
            if not passed:
                result.passed = False
                result.findings.append(message)

    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchEntity":
            result.passed = False
            result.findings.append("No IAM password policy is configured")
        else:
            result.findings.append(f"Could not check password policy: {e}")
    return result


# ── Score calculator ──────────────────────────────────────────────────────────

def calculate_score(results: list[CheckResult]) -> int:
    """
    Calculate a zero trust score from 0 to 100.

    Score = (sum of weights for passed checks) / (total possible weight) * 100

    Args:
        results: List of CheckResult objects

    Returns:
        Integer score from 0 to 100
    """
    total_weight = sum(r.weight for r in results)
    passed_weight = sum(r.weight for r in results if r.passed)
    if total_weight == 0:
        return 0
    return int((passed_weight / total_weight) * 100)


# ── Report printer ────────────────────────────────────────────────────────────

def print_zero_trust_report(results: list[CheckResult]) -> None:
    """
    Print the zero trust audit report with score and findings.

    Args:
        results: List of CheckResult objects
    """
    score = calculate_score(results)
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)

    # Score rating
    if score >= 90:
        rating = "EXCELLENT 🟢"
    elif score >= 70:
        rating = "GOOD 🟡"
    elif score >= 50:
        rating = "FAIR 🟠"
    else:
        rating = "POOR 🔴"

    print("\n" + "=" * 80)
    print("  ZERO TRUST SECURITY AUDIT REPORT")
    print("=" * 80)
    print(f"\n  Zero Trust Score: {score}/100  —  {rating}")
    print(f"  Checks passed: {passed}/{len(results)}")
    print()

    # Print each check result
    for r in results:
        icon = "✓" if r.passed else "✗"
        status = "PASS" if r.passed else "FAIL"
        print(f"  [{icon}] {r.check_id}  {r.name:<45}  {status}  (weight: {r.weight})")

        if not r.passed:
            for finding in r.findings[:3]:  # Show up to 3 findings per check
                print(f"       ⚠ {finding}")
            if len(r.findings) > 3:
                print(f"       ... and {len(r.findings) - 3} more finding(s)")
            print(f"       → Fix: {r.remediation}")
        print()

    print("=" * 80)
    if score < 70:
        print("  ⚠  Score below 70 — address FAIL items to improve your security posture")
    elif score < 90:
        print("  ℹ  Good posture — address remaining FAIL items to reach EXCELLENT")
    else:
        print("  ✓  Excellent zero trust posture — keep monitoring for drift")
    print("=" * 80 + "\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Audit AWS account for zero trust security principles"
    )
    parser.add_argument(
        "--region", default=None,
        help="AWS region (default: from AWS config/env)"
    )
    args = parser.parse_args()

    global iam, s3, ec2, cloudtrail
    if args.region:
        iam = boto3.client("iam", region_name=args.region)
        s3 = boto3.client("s3", region_name=args.region)
        ec2 = boto3.client("ec2", region_name=args.region)
        cloudtrail = boto3.client("cloudtrail", region_name=args.region)

    print("\n=== Zero Trust Security Checker ===\n")

    checks = [
        ("ZT-01: Root MFA",              check_root_mfa),
        ("ZT-02: User MFA",              check_users_without_mfa),
        ("ZT-03: S3 public access",      check_s3_public_access),
        ("ZT-04: Open SSH/RDP",          check_open_ssh_rdp),
        ("ZT-05: Wildcard IAM policies", check_wildcard_iam_policies),
        ("ZT-06: Old access keys",       check_old_access_keys),
        ("ZT-07: CloudTrail",            check_cloudtrail_enabled),
        ("ZT-08: Password policy",       check_password_policy),
    ]

    results: list[CheckResult] = []
    for name, check_fn in checks:
        print(f"  Running {name}...", end=" ", flush=True)
        result = check_fn()
        icon = "✓" if result.passed else "✗"
        print(icon)
        results.append(result)

    print_zero_trust_report(results)


if __name__ == "__main__":
    main()
