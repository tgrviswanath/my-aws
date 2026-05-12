"""
cloudtrail_analyzer.py — Analyze CloudTrail logs for suspicious activity.

Usage:
    python cloudtrail_analyzer.py --bucket my-cloudtrail-bucket --days 7
    python cloudtrail_analyzer.py --bucket my-cloudtrail-bucket --days 1 --prefix AWSLogs/123456789012/CloudTrail/

What this script does:
    1. Downloads recent CloudTrail log files from S3 (last N days)
    2. Parses the gzipped JSON log files
    3. Detects suspicious patterns:
        - Root account usage
        - Failed console logins (ConsoleLoginFailure)
        - API calls from unusual/unexpected regions
        - IAM changes (CreateUser, AttachPolicy, etc.)
        - Security group modifications
        - S3 bucket policy changes
    4. Prints security events sorted by severity

Prerequisites:
    pip install boto3
    AWS credentials with s3:GetObject and s3:ListBucket permissions on the CloudTrail bucket
"""

import argparse
import gzip
import io
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

import boto3
from botocore.exceptions import ClientError


# ── AWS clients ───────────────────────────────────────────────────────────────
s3 = boto3.client("s3")


# ── Detection rules ───────────────────────────────────────────────────────────

# IAM-related API calls that indicate privilege changes
IAM_CHANGE_EVENTS = {
    "CreateUser", "DeleteUser", "CreateRole", "DeleteRole",
    "AttachUserPolicy", "DetachUserPolicy", "AttachRolePolicy", "DetachRolePolicy",
    "PutUserPolicy", "DeleteUserPolicy", "PutRolePolicy", "DeleteRolePolicy",
    "CreateAccessKey", "DeleteAccessKey", "UpdateAccessKey",
    "AddUserToGroup", "RemoveUserFromGroup",
    "CreateLoginProfile", "UpdateLoginProfile", "DeleteLoginProfile",
    "CreatePolicy", "DeletePolicy", "CreatePolicyVersion",
}

# Security group modification events
SG_CHANGE_EVENTS = {
    "AuthorizeSecurityGroupIngress", "AuthorizeSecurityGroupEgress",
    "RevokeSecurityGroupIngress", "RevokeSecurityGroupEgress",
    "CreateSecurityGroup", "DeleteSecurityGroup",
}

# S3 bucket policy/ACL changes
S3_POLICY_EVENTS = {
    "PutBucketPolicy", "DeleteBucketPolicy",
    "PutBucketAcl", "PutBucketPublicAccessBlock",
}

# CloudTrail tampering events
CLOUDTRAIL_EVENTS = {
    "StopLogging", "DeleteTrail", "UpdateTrail", "PutEventSelectors",
}

# Expected regions — calls from outside these regions are flagged
# Customize this list for your organization
EXPECTED_REGIONS = {
    "us-east-1", "us-east-2", "us-west-1", "us-west-2",
    "eu-west-1", "eu-central-1", "ap-southeast-1",
}


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class SecurityEvent:
    """A suspicious CloudTrail event detected by the analyzer."""
    severity: str          # CRITICAL, HIGH, MEDIUM, LOW
    category: str          # ROOT_USAGE, FAILED_LOGIN, IAM_CHANGE, etc.
    event_time: str
    event_name: str
    user_identity: str     # Who performed the action
    source_ip: str
    region: str
    account_id: str
    detail: str            # Human-readable description
    raw_event: dict = field(default_factory=dict, repr=False)


# ── S3 log discovery ──────────────────────────────────────────────────────────

def list_cloudtrail_log_keys(
    bucket: str,
    prefix: str,
    days: int,
) -> list[str]:
    """
    List S3 keys for CloudTrail log files from the last N days.

    CloudTrail stores logs at:
        {prefix}/{account_id}/CloudTrail/{region}/{year}/{month}/{day}/

    Args:
        bucket: S3 bucket name
        prefix: Key prefix (e.g. 'AWSLogs/123456789012/CloudTrail/')
        days:   Number of days to look back

    Returns:
        List of S3 object keys for .json.gz log files
    """
    keys = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    paginator = s3.get_paginator("list_objects_v2")
    try:
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                last_modified = obj["LastModified"]

                # Only include files modified within the lookback window
                if last_modified >= cutoff and key.endswith(".json.gz"):
                    keys.append(key)
    except ClientError as e:
        print(f"  ✗ Error listing S3 objects: {e}")
        raise

    return keys


# ── Log parsing ───────────────────────────────────────────────────────────────

def download_and_parse_log(bucket: str, key: str) -> list[dict]:
    """
    Download a CloudTrail log file from S3 and parse its events.

    CloudTrail logs are gzipped JSON files with the structure:
        {"Records": [{event1}, {event2}, ...]}

    Args:
        bucket: S3 bucket name
        key:    S3 object key

    Returns:
        List of CloudTrail event dicts
    """
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        compressed_data = response["Body"].read()

        # Decompress gzip content
        with gzip.GzipFile(fileobj=io.BytesIO(compressed_data)) as gz:
            log_data = json.loads(gz.read().decode("utf-8"))

        return log_data.get("Records", [])
    except Exception as e:
        print(f"  ⚠ Could not parse {key}: {e}")
        return []


# ── Detection functions ───────────────────────────────────────────────────────

def extract_user_identity(event: dict) -> str:
    """
    Extract a human-readable identity string from a CloudTrail event.

    Args:
        event: CloudTrail event dict

    Returns:
        Identity string (e.g. 'root', 'IAMUser:alice', 'AssumedRole:arn:...')
    """
    identity = event.get("userIdentity", {})
    identity_type = identity.get("type", "Unknown")

    if identity_type == "Root":
        return "root"
    elif identity_type == "IAMUser":
        return f"IAMUser:{identity.get('userName', 'unknown')}"
    elif identity_type == "AssumedRole":
        arn = identity.get("arn", "")
        # Extract role session name from ARN (last component)
        session = arn.split("/")[-1] if "/" in arn else arn
        return f"AssumedRole:{session}"
    elif identity_type == "AWSService":
        return f"AWSService:{identity.get('invokedBy', 'unknown')}"
    else:
        return f"{identity_type}:{identity.get('principalId', 'unknown')}"


def analyze_event(event: dict) -> Optional[SecurityEvent]:
    """
    Analyze a single CloudTrail event and return a SecurityEvent if suspicious.

    Args:
        event: CloudTrail event dict

    Returns:
        SecurityEvent if the event is suspicious, None otherwise
    """
    event_name = event.get("eventName", "")
    event_time = event.get("eventTime", "")
    region = event.get("awsRegion", "")
    account_id = event.get("recipientAccountId", event.get("userIdentity", {}).get("accountId", ""))
    source_ip = event.get("sourceIPAddress", "")
    user_identity = extract_user_identity(event)
    error_code = event.get("errorCode", "")

    # ── Rule 1: Root account usage ─────────────────────────────────────────
    if event.get("userIdentity", {}).get("type") == "Root":
        return SecurityEvent(
            severity="CRITICAL",
            category="ROOT_USAGE",
            event_time=event_time,
            event_name=event_name,
            user_identity=user_identity,
            source_ip=source_ip,
            region=region,
            account_id=account_id,
            detail=f"Root account used to call {event_name} from {source_ip}",
            raw_event=event,
        )

    # ── Rule 2: Failed console logins ──────────────────────────────────────
    if event_name == "ConsoleLogin" and error_code == "Failed authentication":
        return SecurityEvent(
            severity="HIGH",
            category="FAILED_LOGIN",
            event_time=event_time,
            event_name=event_name,
            user_identity=user_identity,
            source_ip=source_ip,
            region=region,
            account_id=account_id,
            detail=f"Failed console login for {user_identity} from {source_ip}",
            raw_event=event,
        )

    # ── Rule 3: CloudTrail tampering ───────────────────────────────────────
    if event_name in CLOUDTRAIL_EVENTS:
        return SecurityEvent(
            severity="CRITICAL",
            category="CLOUDTRAIL_TAMPER",
            event_time=event_time,
            event_name=event_name,
            user_identity=user_identity,
            source_ip=source_ip,
            region=region,
            account_id=account_id,
            detail=f"CloudTrail tampered: {event_name} by {user_identity}",
            raw_event=event,
        )

    # ── Rule 4: IAM changes ────────────────────────────────────────────────
    if event_name in IAM_CHANGE_EVENTS and not error_code:
        # Extract the target resource from request parameters
        params = event.get("requestParameters") or {}
        target = (
            params.get("userName") or params.get("roleName") or
            params.get("policyArn") or params.get("groupName") or "unknown"
        )
        return SecurityEvent(
            severity="HIGH",
            category="IAM_CHANGE",
            event_time=event_time,
            event_name=event_name,
            user_identity=user_identity,
            source_ip=source_ip,
            region=region,
            account_id=account_id,
            detail=f"IAM change: {event_name} on {target} by {user_identity}",
            raw_event=event,
        )

    # ── Rule 5: Security group changes ────────────────────────────────────
    if event_name in SG_CHANGE_EVENTS and not error_code:
        params = event.get("requestParameters") or {}
        sg_id = params.get("groupId", "unknown")
        return SecurityEvent(
            severity="MEDIUM",
            category="SG_CHANGE",
            event_time=event_time,
            event_name=event_name,
            user_identity=user_identity,
            source_ip=source_ip,
            region=region,
            account_id=account_id,
            detail=f"Security group modified: {event_name} on {sg_id} by {user_identity}",
            raw_event=event,
        )

    # ── Rule 6: S3 bucket policy changes ──────────────────────────────────
    if event_name in S3_POLICY_EVENTS and not error_code:
        params = event.get("requestParameters") or {}
        bucket_name = params.get("bucketName", "unknown")
        return SecurityEvent(
            severity="HIGH",
            category="S3_POLICY_CHANGE",
            event_time=event_time,
            event_name=event_name,
            user_identity=user_identity,
            source_ip=source_ip,
            region=region,
            account_id=account_id,
            detail=f"S3 policy changed: {event_name} on bucket '{bucket_name}' by {user_identity}",
            raw_event=event,
        )

    # ── Rule 7: API calls from unexpected regions ──────────────────────────
    if region and region not in EXPECTED_REGIONS and not error_code:
        # Only flag meaningful API calls (not describe/list operations)
        if not any(event_name.startswith(p) for p in ("Describe", "List", "Get", "Head")):
            return SecurityEvent(
                severity="MEDIUM",
                category="UNUSUAL_REGION",
                event_time=event_time,
                event_name=event_name,
                user_identity=user_identity,
                source_ip=source_ip,
                region=region,
                account_id=account_id,
                detail=f"API call from unexpected region '{region}': {event_name} by {user_identity}",
                raw_event=event,
            )

    return None  # Event is not suspicious


# ── Report printer ────────────────────────────────────────────────────────────

def print_security_events(events: list[SecurityEvent]) -> None:
    """
    Print security events sorted by severity, grouped by category.

    Args:
        events: List of SecurityEvent objects
    """
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    severity_icons = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🔵"}

    # Sort by severity (most critical first), then by time
    events.sort(key=lambda e: (severity_order.get(e.severity, 99), e.event_time))

    print("\n" + "=" * 80)
    print("  CLOUDTRAIL SECURITY ANALYSIS REPORT")
    print("=" * 80)

    if not events:
        print("  ✓ No suspicious events detected in the analyzed log files.")
        print("=" * 80 + "\n")
        return

    # Count by category
    by_category: dict[str, list[SecurityEvent]] = defaultdict(list)
    for e in events:
        by_category[e.category].append(e)

    print(f"  Total suspicious events: {len(events)}")
    for category, cat_events in sorted(by_category.items()):
        print(f"    {category}: {len(cat_events)}")
    print()

    # Print events grouped by severity
    by_severity: dict[str, list[SecurityEvent]] = defaultdict(list)
    for e in events:
        by_severity[e.severity].append(e)

    for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        sev_events = by_severity.get(severity, [])
        if not sev_events:
            continue

        icon = severity_icons.get(severity, "⚪")
        print(f"  {icon} {severity} ({len(sev_events)} event(s))")
        print("  " + "-" * 76)

        for e in sev_events:
            print(f"\n  [{e.event_time}] {e.category}")
            print(f"  {e.detail}")
            print(f"  Source IP: {e.source_ip}  |  Region: {e.region}  |  Account: {e.account_id}")

        print()

    print("=" * 80 + "\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Analyze CloudTrail logs for suspicious activity"
    )
    parser.add_argument(
        "--bucket", required=True,
        help="S3 bucket containing CloudTrail logs"
    )
    parser.add_argument(
        "--days", type=int, default=7,
        help="Number of days to look back (default: 7)"
    )
    parser.add_argument(
        "--prefix", default="AWSLogs/",
        help="S3 key prefix for CloudTrail logs (default: AWSLogs/)"
    )
    parser.add_argument(
        "--max-files", type=int, default=100,
        help="Maximum number of log files to process (default: 100)"
    )
    args = parser.parse_args()

    print(f"\n=== CloudTrail Log Analyzer ===")
    print(f"  Bucket: {args.bucket}")
    print(f"  Prefix: {args.prefix}")
    print(f"  Lookback: {args.days} day(s)")
    print()

    # Step 1 — Discover log files
    print("  Discovering log files...")
    keys = list_cloudtrail_log_keys(args.bucket, args.prefix, args.days)
    print(f"  Found {len(keys)} log file(s)")

    if not keys:
        print("  No log files found. Check the bucket name and prefix.")
        return

    # Limit to max_files to avoid very long runs
    if len(keys) > args.max_files:
        print(f"  Limiting to {args.max_files} most recent files")
        keys = sorted(keys)[-args.max_files:]

    # Step 2 — Parse and analyze events
    print(f"  Analyzing {len(keys)} file(s)...\n")
    all_suspicious_events: list[SecurityEvent] = []
    total_events = 0

    for i, key in enumerate(keys, 1):
        print(f"  [{i:03d}/{len(keys)}] {key.split('/')[-1]}", end=" ")
        events = download_and_parse_log(args.bucket, key)
        total_events += len(events)

        suspicious = [e for e in (analyze_event(ev) for ev in events) if e is not None]
        all_suspicious_events.extend(suspicious)
        print(f"→ {len(events)} events, {len(suspicious)} suspicious")

    print(f"\n  Total events analyzed: {total_events}")
    print(f"  Suspicious events found: {len(all_suspicious_events)}")

    # Step 3 — Print report
    print_security_events(all_suspicious_events)


if __name__ == "__main__":
    main()
