"""
compliance_checker.py — Check AWS Config compliance rules and report violations.

Usage:
    python compliance_checker.py
    python compliance_checker.py --region us-west-2
    python compliance_checker.py --severity CRITICAL HIGH

What this script does:
    1. Lists all AWS Config rules and their overall compliance status
    2. Fetches non-compliant resources for each failing rule
    3. Groups findings by severity (CRITICAL, HIGH, MEDIUM, LOW)
    4. Prints a compliance report with remediation hints
    5. Exits with code 1 if any CRITICAL/HIGH violations are found

Prerequisites:
    pip install boto3
    AWS credentials configured with config:Describe* and config:Get* permissions
"""

import argparse
import sys
from dataclasses import dataclass, field
from typing import Optional

import boto3
from botocore.exceptions import ClientError


# ── AWS client ────────────────────────────────────────────────────────────────
config_client = boto3.client("config")


# ── Severity mapping ──────────────────────────────────────────────────────────

# Map Config rule name patterns to severity levels.
# Rules not matching any pattern default to MEDIUM.
SEVERITY_MAP: dict[str, str] = {
    # CRITICAL — direct security exposure
    "root-account-mfa-enabled":              "CRITICAL",
    "iam-root-access-key-check":             "CRITICAL",
    "s3-bucket-public-read-prohibited":      "CRITICAL",
    "s3-bucket-public-write-prohibited":     "CRITICAL",
    "restricted-ssh":                        "CRITICAL",
    "restricted-common-ports":               "CRITICAL",
    "guardduty-enabled-centralized":         "CRITICAL",
    "securityhub-enabled":                   "CRITICAL",

    # HIGH — significant risk
    "mfa-enabled-for-iam-console-access":    "HIGH",
    "iam-password-policy":                   "HIGH",
    "cloudtrail-enabled":                    "HIGH",
    "multi-region-cloudtrail-enabled":       "HIGH",
    "s3-bucket-logging-enabled":             "HIGH",
    "s3-bucket-versioning-enabled":          "HIGH",
    "rds-instance-public-access-check":      "HIGH",
    "ec2-instance-no-public-ip":             "HIGH",
    "vpc-flow-logs-enabled":                 "HIGH",
    "ebs-snapshot-public-restorable-check":  "HIGH",
    "kms-cmk-not-scheduled-for-deletion":    "HIGH",

    # MEDIUM — best practice violations
    "ec2-volume-inuse-check":                "MEDIUM",
    "ebs-optimized-instance":                "MEDIUM",
    "rds-storage-encrypted":                 "MEDIUM",
    "s3-bucket-ssl-requests-only":           "MEDIUM",
    "cloudwatch-alarm-action-check":         "MEDIUM",
    "iam-user-unused-credentials-check":     "MEDIUM",
    "access-keys-rotated":                   "MEDIUM",
}

# Remediation hints for common Config rules
REMEDIATION_HINTS: dict[str, str] = {
    "root-account-mfa-enabled":
        "Enable MFA on the root account via IAM console → Security credentials",
    "iam-root-access-key-check":
        "Delete root access keys: IAM → Security credentials → Access keys",
    "s3-bucket-public-read-prohibited":
        "Block public access: S3 → Bucket → Permissions → Block public access",
    "s3-bucket-public-write-prohibited":
        "Block public write: S3 → Bucket → Permissions → Block public access",
    "restricted-ssh":
        "Remove 0.0.0.0/0 inbound rule on port 22 from the security group",
    "restricted-common-ports":
        "Restrict inbound rules on ports 20,21,23,25,110,135,143,3389",
    "mfa-enabled-for-iam-console-access":
        "Enable MFA for each IAM user: IAM → Users → Security credentials → MFA",
    "iam-password-policy":
        "Set password policy: IAM → Account settings → Password policy",
    "cloudtrail-enabled":
        "Enable CloudTrail: CloudTrail → Create trail → Apply to all regions",
    "rds-instance-public-access-check":
        "Disable public accessibility: RDS → Modify → Connectivity → Not publicly accessible",
    "vpc-flow-logs-enabled":
        "Enable VPC Flow Logs: VPC → Your VPC → Flow logs → Create flow log",
    "s3-bucket-ssl-requests-only":
        "Add bucket policy to deny non-HTTPS requests (aws:SecureTransport condition)",
    "access-keys-rotated":
        "Rotate access keys older than 90 days: IAM → Users → Security credentials",
}


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class NonCompliantResource:
    """A single non-compliant resource found by a Config rule."""
    resource_type: str
    resource_id: str
    annotation: str  # AWS Config's explanation of why it's non-compliant


@dataclass
class RuleViolation:
    """A Config rule with its compliance status and non-compliant resources."""
    rule_name: str
    severity: str
    compliance_type: str          # COMPLIANT, NON_COMPLIANT, INSUFFICIENT_DATA, NOT_APPLICABLE
    non_compliant_resources: list[NonCompliantResource] = field(default_factory=list)
    remediation_hint: str = ""


# ── AWS Config helpers ────────────────────────────────────────────────────────

def get_all_config_rules() -> list[dict]:
    """
    Fetch all AWS Config rules using pagination.

    Returns:
        List of Config rule dicts from the AWS API
    """
    rules = []
    paginator = config_client.get_paginator("describe_config_rules")
    for page in paginator.paginate():
        rules.extend(page.get("ConfigRules", []))
    return rules


def get_compliance_by_rule() -> dict[str, str]:
    """
    Fetch compliance status for all Config rules.

    Returns:
        Dict mapping rule_name → compliance_type
    """
    compliance_map = {}
    paginator = config_client.get_paginator("describe_compliance_by_config_rule")
    for page in paginator.paginate():
        for item in page.get("ComplianceByConfigRules", []):
            rule_name = item["ConfigRuleName"]
            compliance_type = item["Compliance"]["ComplianceType"]
            compliance_map[rule_name] = compliance_type
    return compliance_map


def get_non_compliant_resources(rule_name: str) -> list[NonCompliantResource]:
    """
    Fetch non-compliant resources for a specific Config rule.

    Args:
        rule_name: The Config rule name

    Returns:
        List of NonCompliantResource objects
    """
    resources = []
    try:
        paginator = config_client.get_paginator(
            "get_compliance_details_by_config_rule"
        )
        for page in paginator.paginate(
            ConfigRuleName=rule_name,
            ComplianceTypes=["NON_COMPLIANT"],
        ):
            for result in page.get("EvaluationResults", []):
                qualifier = result["EvaluationResultIdentifier"]["EvaluationResultQualifier"]
                resources.append(NonCompliantResource(
                    resource_type=qualifier.get("ResourceType", "Unknown"),
                    resource_id=qualifier.get("ResourceId", "Unknown"),
                    annotation=result.get("Annotation", "No details provided"),
                ))
    except ClientError as e:
        # Some rules (e.g. account-level) don't support resource-level details
        if e.response["Error"]["Code"] != "NoSuchConfigRuleException":
            print(f"  ⚠ Could not fetch resources for {rule_name}: {e}")
    return resources


def get_severity(rule_name: str) -> str:
    """
    Determine severity for a Config rule by matching against SEVERITY_MAP.

    Checks for exact match first, then substring match.

    Args:
        rule_name: Config rule name (may include a numeric suffix)

    Returns:
        Severity string: CRITICAL, HIGH, MEDIUM, or LOW
    """
    # Exact match
    if rule_name in SEVERITY_MAP:
        return SEVERITY_MAP[rule_name]

    # Substring match (handles rules with numeric suffixes like 'restricted-ssh-1')
    rule_lower = rule_name.lower()
    for pattern, severity in SEVERITY_MAP.items():
        if pattern in rule_lower:
            return severity

    return "LOW"  # Default for unknown rules


# ── Report printer ────────────────────────────────────────────────────────────

def print_compliance_report(
    violations: list[RuleViolation],
    filter_severities: Optional[list[str]] = None,
) -> None:
    """
    Print a formatted compliance report grouped by severity.

    Args:
        violations:         List of RuleViolation objects
        filter_severities:  If provided, only show these severity levels
    """
    severity_order = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    severity_icons = {
        "CRITICAL": "🔴",
        "HIGH":     "🟠",
        "MEDIUM":   "🟡",
        "LOW":      "🔵",
    }

    # Filter to only non-compliant rules
    non_compliant = [v for v in violations if v.compliance_type == "NON_COMPLIANT"]
    compliant_count = sum(1 for v in violations if v.compliance_type == "COMPLIANT")
    insufficient_count = sum(1 for v in violations if v.compliance_type == "INSUFFICIENT_DATA")

    if filter_severities:
        non_compliant = [v for v in non_compliant if v.severity in filter_severities]

    print("\n" + "=" * 80)
    print("  AWS CONFIG COMPLIANCE REPORT")
    print("=" * 80)
    print(f"  Total rules evaluated: {len(violations)}")
    print(f"  ✓ Compliant:           {compliant_count}")
    print(f"  ✗ Non-compliant:       {len(non_compliant)}")
    print(f"  ? Insufficient data:   {insufficient_count}")
    print()

    if not non_compliant:
        print("  ✓ No violations found! Your account is fully compliant.")
        print("=" * 80 + "\n")
        return

    # Group by severity
    by_severity: dict[str, list[RuleViolation]] = {}
    for v in non_compliant:
        by_severity.setdefault(v.severity, []).append(v)

    for severity in severity_order:
        rules = by_severity.get(severity, [])
        if not rules:
            continue

        icon = severity_icons.get(severity, "⚪")
        print(f"  {icon} {severity} ({len(rules)} rule(s))")
        print("  " + "-" * 76)

        for rule in rules:
            print(f"\n  Rule: {rule.rule_name}")
            if rule.remediation_hint:
                print(f"  Fix:  {rule.remediation_hint}")

            if rule.non_compliant_resources:
                print(f"  Non-compliant resources ({len(rule.non_compliant_resources)}):")
                # Show up to 5 resources to keep output readable
                for res in rule.non_compliant_resources[:5]:
                    print(f"    • [{res.resource_type}] {res.resource_id}")
                    if res.annotation and res.annotation != "No details provided":
                        print(f"      → {res.annotation}")
                if len(rule.non_compliant_resources) > 5:
                    remaining = len(rule.non_compliant_resources) - 5
                    print(f"    ... and {remaining} more resource(s)")
            else:
                print("  Non-compliant resources: (account-level rule — no resource details)")

        print()

    print("=" * 80)
    critical_high = sum(1 for v in non_compliant if v.severity in ("CRITICAL", "HIGH"))
    if critical_high > 0:
        print(f"  ⚠  ACTION REQUIRED: {critical_high} CRITICAL/HIGH violation(s) need immediate attention")
    print("=" * 80 + "\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Check AWS Config compliance rules and report violations"
    )
    parser.add_argument(
        "--region", default=None,
        help="AWS region (default: from AWS config/env)"
    )
    parser.add_argument(
        "--severity", nargs="+",
        choices=["CRITICAL", "HIGH", "MEDIUM", "LOW"],
        default=None,
        help="Filter report to specific severity levels (e.g. --severity CRITICAL HIGH)"
    )
    parser.add_argument(
        "--include-resources", action="store_true",
        help="Fetch non-compliant resource details (slower — makes extra API calls)"
    )
    args = parser.parse_args()

    global config_client
    if args.region:
        config_client = boto3.client("config", region_name=args.region)

    print("\n=== AWS Config Compliance Checker ===\n")

    # Step 1 — Fetch all rules
    print("  Fetching Config rules...")
    rules = get_all_config_rules()
    print(f"  Found {len(rules)} rule(s)")

    # Step 2 — Fetch compliance status for all rules
    print("  Fetching compliance status...")
    compliance_map = get_compliance_by_rule()

    # Step 3 — Build violation objects
    violations: list[RuleViolation] = []
    for rule in rules:
        rule_name = rule["ConfigRuleName"]
        compliance_type = compliance_map.get(rule_name, "INSUFFICIENT_DATA")
        severity = get_severity(rule_name)
        hint = REMEDIATION_HINTS.get(rule_name, "")

        # Match hint by substring if no exact match
        if not hint:
            for pattern, h in REMEDIATION_HINTS.items():
                if pattern in rule_name.lower():
                    hint = h
                    break

        violation = RuleViolation(
            rule_name=rule_name,
            severity=severity,
            compliance_type=compliance_type,
            remediation_hint=hint,
        )

        # Optionally fetch resource-level details for non-compliant rules
        if args.include_resources and compliance_type == "NON_COMPLIANT":
            print(f"  Fetching resources for: {rule_name}...")
            violation.non_compliant_resources = get_non_compliant_resources(rule_name)

        violations.append(violation)

    # Step 4 — Print report
    print_compliance_report(violations, filter_severities=args.severity)

    # Exit with non-zero code if CRITICAL or HIGH violations exist
    critical_high = sum(
        1 for v in violations
        if v.compliance_type == "NON_COMPLIANT" and v.severity in ("CRITICAL", "HIGH")
    )
    sys.exit(1 if critical_high > 0 else 0)


if __name__ == "__main__":
    main()
