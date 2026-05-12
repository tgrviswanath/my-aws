"""
security_monitor.py — Fetch and triage GuardDuty + Security Hub findings.

Usage:
    python security_monitor.py
    python security_monitor.py --severity HIGH
    python security_monitor.py --severity HIGH MEDIUM --max-findings 50

What this script does:
    1. Lists active GuardDuty findings filtered by severity
    2. Lists Security Hub findings
    3. Groups findings by type
    4. Prints a security report with recommended remediation actions

Severity mapping:
    GuardDuty uses a numeric score (0.1–10.0):
        HIGH:   7.0 – 10.0
        MEDIUM: 4.0 – 6.9
        LOW:    0.1 – 3.9

    Security Hub uses string labels: CRITICAL, HIGH, MEDIUM, LOW, INFORMATIONAL

Prerequisites:
    pip install boto3
    GuardDuty and Security Hub must be enabled in the target account/region
    AWS credentials with guardduty:List*, securityhub:GetFindings permissions
"""

import argparse
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

import boto3
from botocore.exceptions import ClientError


# ── AWS clients ───────────────────────────────────────────────────────────────
guardduty = boto3.client("guardduty")
securityhub = boto3.client("securityhub")


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class SecurityFinding:
    """Normalized security finding from GuardDuty or Security Hub."""
    source: str           # "GuardDuty" or "SecurityHub"
    finding_id: str
    title: str
    finding_type: str     # e.g. "UnauthorizedAccess:EC2/SSHBruteForce"
    severity: str         # CRITICAL, HIGH, MEDIUM, LOW
    severity_score: float # Numeric score (0.1–10.0)
    resource_type: str    # e.g. "AwsEc2Instance"
    resource_id: str      # e.g. "i-0abc123def456789a"
    region: str
    account_id: str
    description: str
    updated_at: str
    recommended_action: str = ""


# ── Remediation hints ─────────────────────────────────────────────────────────

# Map GuardDuty/Security Hub finding type prefixes to recommended actions
REMEDIATION_MAP: dict[str, str] = {
    "UnauthorizedAccess:EC2/SSHBruteForce":
        "Restrict SSH access: update SG to allow only trusted IPs on port 22",
    "UnauthorizedAccess:EC2/RDPBruteForce":
        "Restrict RDP access: update SG to allow only trusted IPs on port 3389",
    "Recon:EC2/PortProbeUnprotectedPort":
        "Review open ports in security groups; close unnecessary ports",
    "Trojan:EC2/BlackholeTraffic":
        "Isolate the EC2 instance and investigate for malware",
    "CryptoCurrency:EC2/BitcoinTool":
        "Terminate or isolate instance; investigate for unauthorized crypto mining",
    "Backdoor:EC2/C&CActivity":
        "Immediately isolate instance; investigate for compromise",
    "UnauthorizedAccess:IAMUser/ConsoleLoginSuccess.B":
        "Review IAM user activity; rotate credentials; enable MFA",
    "Policy:IAMUser/RootCredentialUsage":
        "Stop using root credentials; create IAM users with least privilege",
    "Stealth:IAMUser/CloudTrailLoggingDisabled":
        "Re-enable CloudTrail immediately; investigate who disabled it",
    "Impact:S3/AnomalousBehavior":
        "Review S3 bucket access logs; check for data exfiltration",
    "Discovery:S3/BucketEnumeration":
        "Review S3 bucket policies; ensure no public access",
    "software-and-configuration-checks":
        "Review the specific configuration finding and apply the recommended fix",
    "aws-foundational-security-best-practices":
        "Follow AWS Foundational Security Best Practices remediation steps",
}


def get_remediation(finding_type: str) -> str:
    """
    Look up a remediation hint for a finding type.

    Args:
        finding_type: The finding type string

    Returns:
        Remediation hint string, or a generic message if not found
    """
    # Exact match first
    if finding_type in REMEDIATION_MAP:
        return REMEDIATION_MAP[finding_type]

    # Prefix/substring match
    for pattern, hint in REMEDIATION_MAP.items():
        if pattern.lower() in finding_type.lower():
            return hint

    return "Review the finding details in the AWS console and apply recommended remediation"


# ── GuardDuty helpers ─────────────────────────────────────────────────────────

def get_guardduty_detector_id() -> Optional[str]:
    """
    Get the active GuardDuty detector ID for the current region.

    Returns:
        Detector ID string, or None if GuardDuty is not enabled
    """
    try:
        response = guardduty.list_detectors()
        detectors = response.get("DetectorIds", [])
        return detectors[0] if detectors else None
    except ClientError as e:
        print(f"  ⚠ GuardDuty error: {e}")
        return None


def severity_label_from_score(score: float) -> str:
    """Convert a GuardDuty numeric severity score to a label."""
    if score >= 7.0:
        return "HIGH"
    elif score >= 4.0:
        return "MEDIUM"
    else:
        return "LOW"


def fetch_guardduty_findings(
    detector_id: str,
    min_severity: float = 4.0,
    max_results: int = 50,
) -> list[SecurityFinding]:
    """
    Fetch active GuardDuty findings above a minimum severity score.

    Args:
        detector_id:  GuardDuty detector ID
        min_severity: Minimum severity score (default: 4.0 = MEDIUM+)
        max_results:  Maximum number of findings to return

    Returns:
        List of SecurityFinding objects
    """
    findings = []

    # Step 1 — List finding IDs matching the severity filter
    try:
        response = guardduty.list_findings(
            DetectorId=detector_id,
            FindingCriteria={
                "Criterion": {
                    "severity": {"Gte": min_severity},
                    "service.archived": {"Eq": ["false"]},  # Only active findings
                }
            },
            MaxResults=min(max_results, 50),  # API max is 50 per call
        )
        finding_ids = response.get("FindingIds", [])
    except ClientError as e:
        print(f"  ⚠ Could not list GuardDuty findings: {e}")
        return []

    if not finding_ids:
        return []

    # Step 2 — Fetch full details for those IDs
    try:
        details_response = guardduty.get_findings(
            DetectorId=detector_id,
            FindingIds=finding_ids,
        )
    except ClientError as e:
        print(f"  ⚠ Could not get GuardDuty finding details: {e}")
        return []

    for f in details_response.get("Findings", []):
        score = f.get("Severity", 0.0)
        resource = f.get("Resource", {})
        resource_type = resource.get("ResourceType", "Unknown")

        # Extract resource ID based on resource type
        resource_id = "Unknown"
        if resource_type == "Instance":
            resource_id = resource.get("InstanceDetails", {}).get("InstanceId", "Unknown")
        elif resource_type == "AccessKey":
            resource_id = resource.get("AccessKeyDetails", {}).get("AccessKeyId", "Unknown")
        elif resource_type == "S3Bucket":
            buckets = resource.get("S3BucketDetails", [])
            resource_id = buckets[0].get("Name", "Unknown") if buckets else "Unknown"

        finding_type = f.get("Type", "Unknown")
        findings.append(SecurityFinding(
            source="GuardDuty",
            finding_id=f["Id"],
            title=f.get("Title", "No title"),
            finding_type=finding_type,
            severity=severity_label_from_score(score),
            severity_score=score,
            resource_type=resource_type,
            resource_id=resource_id,
            region=f.get("Region", "Unknown"),
            account_id=f.get("AccountId", "Unknown"),
            description=f.get("Description", ""),
            updated_at=str(f.get("UpdatedAt", "")),
            recommended_action=get_remediation(finding_type),
        ))

    return findings


# ── Security Hub helpers ──────────────────────────────────────────────────────

SEVERITY_SCORE_MAP = {
    "CRITICAL": 9.0,
    "HIGH":     7.0,
    "MEDIUM":   5.0,
    "LOW":      2.0,
    "INFORMATIONAL": 0.5,
}


def fetch_securityhub_findings(
    severities: list[str],
    max_results: int = 50,
) -> list[SecurityFinding]:
    """
    Fetch active Security Hub findings for the specified severity levels.

    Args:
        severities:  List of severity labels to include (e.g. ['HIGH', 'MEDIUM'])
        max_results: Maximum number of findings to return

    Returns:
        List of SecurityFinding objects
    """
    findings = []

    # Build severity filter — Security Hub uses Label field
    severity_filters = [{"Label": {"Value": s, "Comparison": "EQUALS"}} for s in severities]

    try:
        response = securityhub.get_findings(
            Filters={
                "SeverityLabel": severity_filters,
                "RecordState": [{"Value": "ACTIVE", "Comparison": "EQUALS"}],
                "WorkflowStatus": [{"Value": "NEW", "Comparison": "EQUALS"}],
            },
            MaxResults=min(max_results, 100),  # API max is 100
        )
    except ClientError as e:
        if "not subscribed" in str(e).lower() or "InvalidAccessException" in str(e):
            print("  ⚠ Security Hub is not enabled in this region — skipping")
        else:
            print(f"  ⚠ Security Hub error: {e}")
        return []

    for f in response.get("Findings", []):
        severity_label = f.get("Severity", {}).get("Label", "MEDIUM")
        resources = f.get("Resources", [{}])
        resource = resources[0] if resources else {}
        finding_type = f.get("Types", ["Unknown"])[0] if f.get("Types") else "Unknown"

        findings.append(SecurityFinding(
            source="SecurityHub",
            finding_id=f["Id"],
            title=f.get("Title", "No title"),
            finding_type=finding_type,
            severity=severity_label,
            severity_score=SEVERITY_SCORE_MAP.get(severity_label, 5.0),
            resource_type=resource.get("Type", "Unknown"),
            resource_id=resource.get("Id", "Unknown"),
            region=f.get("Region", "Unknown"),
            account_id=f.get("AwsAccountId", "Unknown"),
            description=f.get("Description", ""),
            updated_at=str(f.get("UpdatedAt", "")),
            recommended_action=get_remediation(finding_type),
        ))

    return findings


# ── Report printer ────────────────────────────────────────────────────────────

def print_security_report(findings: list[SecurityFinding]) -> None:
    """
    Print a formatted security report grouped by finding type.

    Args:
        findings: Combined list of GuardDuty + Security Hub findings
    """
    severity_order = ["HIGH", "CRITICAL", "MEDIUM", "LOW"]
    severity_icons = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🔵"}

    print("\n" + "=" * 80)
    print("  SECURITY FINDINGS REPORT")
    print("=" * 80)

    if not findings:
        print("  ✓ No active findings found for the selected severity levels.")
        print("=" * 80 + "\n")
        return

    # Summary counts
    gd_count = sum(1 for f in findings if f.source == "GuardDuty")
    sh_count = sum(1 for f in findings if f.source == "SecurityHub")
    print(f"  Total findings: {len(findings)}  (GuardDuty: {gd_count}, SecurityHub: {sh_count})")
    print()

    # Group by severity, then by finding type
    by_severity: dict[str, list[SecurityFinding]] = defaultdict(list)
    for f in findings:
        by_severity[f.severity].append(f)

    for severity in severity_order:
        sev_findings = by_severity.get(severity, [])
        if not sev_findings:
            continue

        icon = severity_icons.get(severity, "⚪")
        print(f"  {icon} {severity} — {len(sev_findings)} finding(s)")
        print("  " + "-" * 76)

        # Group by finding type within this severity
        by_type: dict[str, list[SecurityFinding]] = defaultdict(list)
        for f in sev_findings:
            by_type[f.finding_type].append(f)

        for finding_type, type_findings in sorted(by_type.items()):
            print(f"\n  [{finding_type}]  ({len(type_findings)} occurrence(s))")
            for f in type_findings[:3]:  # Show up to 3 per type
                print(f"    • [{f.source}] {f.resource_type}: {f.resource_id}")
                print(f"      {f.title}")
                if f.description:
                    # Truncate long descriptions
                    desc = f.description[:120] + "..." if len(f.description) > 120 else f.description
                    print(f"      {desc}")
            if len(type_findings) > 3:
                print(f"    ... and {len(type_findings) - 3} more")

            print(f"    → Recommended action: {type_findings[0].recommended_action}")

        print()

    print("=" * 80)
    high_critical = sum(1 for f in findings if f.severity in ("HIGH", "CRITICAL"))
    if high_critical > 0:
        print(f"  ⚠  {high_critical} HIGH/CRITICAL finding(s) require immediate attention")
    print("=" * 80 + "\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Fetch and triage GuardDuty + Security Hub security findings"
    )
    parser.add_argument(
        "--severity", nargs="+",
        choices=["CRITICAL", "HIGH", "MEDIUM", "LOW"],
        default=["HIGH", "MEDIUM"],
        help="Severity levels to include (default: HIGH MEDIUM)"
    )
    parser.add_argument(
        "--max-findings", type=int, default=50,
        help="Maximum findings to fetch per source (default: 50)"
    )
    parser.add_argument(
        "--region", default=None,
        help="AWS region (default: from AWS config/env)"
    )
    args = parser.parse_args()

    global guardduty, securityhub
    if args.region:
        guardduty = boto3.client("guardduty", region_name=args.region)
        securityhub = boto3.client("securityhub", region_name=args.region)

    # Map severity labels to GuardDuty numeric scores
    severity_score_map = {"CRITICAL": 7.0, "HIGH": 7.0, "MEDIUM": 4.0, "LOW": 0.1}
    min_score = min(severity_score_map.get(s, 4.0) for s in args.severity)

    print(f"\n=== Security Monitor ===")
    print(f"  Severities: {', '.join(args.severity)}")
    print()

    all_findings: list[SecurityFinding] = []

    # ── GuardDuty ──────────────────────────────────────────────────────────
    print("  Fetching GuardDuty findings...")
    detector_id = get_guardduty_detector_id()
    if detector_id:
        gd_findings = fetch_guardduty_findings(detector_id, min_score, args.max_findings)
        print(f"  Found {len(gd_findings)} GuardDuty finding(s)")
        all_findings.extend(gd_findings)
    else:
        print("  ⚠ GuardDuty is not enabled in this region — skipping")

    # ── Security Hub ───────────────────────────────────────────────────────
    print("  Fetching Security Hub findings...")
    sh_findings = fetch_securityhub_findings(args.severity, args.max_findings)
    print(f"  Found {len(sh_findings)} Security Hub finding(s)")
    all_findings.extend(sh_findings)

    # Sort by severity score descending (most critical first)
    all_findings.sort(key=lambda f: f.severity_score, reverse=True)

    print_security_report(all_findings)


if __name__ == "__main__":
    main()
