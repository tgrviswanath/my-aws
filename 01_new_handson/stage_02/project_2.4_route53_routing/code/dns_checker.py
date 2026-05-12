"""
dns_checker.py — Check Route53 routing policies and health checks.

Prerequisites:
    pip install boto3

IAM Permissions Required:
    route53:ListResourceRecordSets
    route53:ListHostedZones
    route53:GetHostedZone
    route53:ListHealthChecks
    route53:GetHealthCheckStatus

Usage:
    python dns_checker.py --hosted-zone-id ZXXXXX [--profile <profile>]
    python dns_checker.py --list-zones          # List all hosted zones

What this script checks:
    1. List all record sets in the hosted zone
    2. Identify routing policy for each record (Simple, Weighted, Failover,
       Latency, Geolocation, Multivalue)
    3. Check health check status for associated records
    4. Print a DNS report
"""

import argparse
import sys
from typing import Any

import boto3
from botocore.exceptions import ClientError, NoCredentialsError


# ── Routing policy detection ──────────────────────────────────────────────────

def detect_routing_policy(record: dict) -> str:
    """
    Determine the routing policy of a Route53 record set.
    Route53 uses different fields to indicate the policy type.
    """
    if record.get("Failover"):
        return f"Failover ({record['Failover']})"
    if record.get("Weight") is not None:
        return f"Weighted (weight={record['Weight']})"
    if record.get("Region"):
        return f"Latency (region={record['Region']})"
    if record.get("GeoLocation"):
        geo = record["GeoLocation"]
        location = (
            geo.get("CountryCode") or
            geo.get("ContinentCode") or
            "Default"
        )
        return f"Geolocation ({location})"
    if record.get("MultiValueAnswer"):
        return "MultiValue"
    return "Simple"


# ── List hosted zones ─────────────────────────────────────────────────────────

def list_hosted_zones(route53) -> list[dict]:
    """List all hosted zones in the account."""
    print("\n── Hosted Zones ────────────────────────────────────────────────")

    try:
        paginator = route53.get_paginator("list_hosted_zones")
        zones = []
        for page in paginator.paginate():
            zones.extend(page.get("HostedZones", []))

        if not zones:
            print("  (No hosted zones found)")
            return []

        for zone in zones:
            zone_id = zone["Id"].split("/")[-1]
            name = zone["Name"]
            private = zone["Config"].get("PrivateZone", False)
            record_count = zone["ResourceRecordSetCount"]
            zone_type = "Private" if private else "Public"
            print(f"  {zone_id:<25} {name:<40} {zone_type:<10} {record_count} records")

        return zones

    except ClientError as e:
        print(f"  [ERROR] Failed to list hosted zones: {e}")
        return []


# ── List record sets ──────────────────────────────────────────────────────────

def list_record_sets(route53, hosted_zone_id: str) -> list[dict]:
    """
    List all record sets in the hosted zone.
    Uses pagination to handle zones with many records.
    """
    print(f"\n── Record Sets in Zone: {hosted_zone_id} ────────────────────────")

    try:
        paginator = route53.get_paginator("list_resource_record_sets")
        records = []
        for page in paginator.paginate(HostedZoneId=hosted_zone_id):
            records.extend(page.get("ResourceRecordSets", []))

        if not records:
            print("  (No records found)")
            return []

        print(f"  Found {len(records)} record(s)\n")

        # Group by name for cleaner output
        for record in records:
            name = record["Name"]
            rtype = record["Type"]
            ttl = record.get("TTL", "alias")
            policy = detect_routing_policy(record)
            set_id = record.get("SetIdentifier", "")
            health_check_id = record.get("HealthCheckId", "")

            # Get the value(s)
            if "AliasTarget" in record:
                alias = record["AliasTarget"]
                value = f"ALIAS → {alias['DNSName']}"
            elif "ResourceRecords" in record:
                values = [r["Value"] for r in record["ResourceRecords"]]
                value = ", ".join(values[:2])
                if len(values) > 2:
                    value += f" (+{len(values)-2} more)"
            else:
                value = "(no value)"

            # Print record
            print(f"  {name:<40} {rtype:<6} TTL:{str(ttl):<8} {policy}")
            if set_id:
                print(f"    SetIdentifier : {set_id}")
            if health_check_id:
                print(f"    HealthCheck   : {health_check_id}")
            print(f"    Value         : {value}")
            print()

        return records

    except ClientError as e:
        print(f"  [ERROR] Failed to list record sets: {e}")
        return []


# ── Health check status ───────────────────────────────────────────────────────

def check_health_checks(route53, records: list[dict]):
    """
    Find all health check IDs referenced by records and check their status.
    """
    print("\n── Health Check Status ─────────────────────────────────────────")

    # Collect unique health check IDs from records
    health_check_ids = list({
        r["HealthCheckId"]
        for r in records
        if r.get("HealthCheckId")
    })

    if not health_check_ids:
        print("  (No health checks associated with these records)")
        return

    print(f"  Found {len(health_check_ids)} health check(s)\n")

    for hc_id in health_check_ids:
        try:
            # Get health check config
            hc_response = route53.get_health_check(HealthCheckId=hc_id)
            hc = hc_response["HealthCheck"]
            config = hc["HealthCheckConfig"]

            hc_type = config.get("Type", "unknown")
            fqdn = config.get("FullyQualifiedDomainName", "")
            ip = config.get("IPAddress", "")
            port = config.get("Port", "")
            path = config.get("ResourcePath", "/")
            threshold = config.get("FailureThreshold", 3)

            target = fqdn or ip or "unknown"

            # Get current health status
            status_response = route53.get_health_check_status(HealthCheckId=hc_id)
            checker_statuses = status_response.get("HealthCheckObservations", [])

            healthy_count = sum(
                1 for obs in checker_statuses
                if obs.get("StatusReport", {}).get("Status", "").startswith("Success")
            )
            total_checkers = len(checker_statuses)

            is_healthy = healthy_count >= (total_checkers - threshold + 1) if total_checkers else False
            icon = "✅" if is_healthy else "❌"

            print(f"  {icon} Health Check: {hc_id}")
            print(f"      Type      : {hc_type}")
            print(f"      Target    : {target}:{port}{path}")
            print(f"      Checkers  : {healthy_count}/{total_checkers} healthy")
            print()

        except ClientError as e:
            print(f"  [WARN] Could not get status for {hc_id}: {e}")


# ── Routing policy summary ────────────────────────────────────────────────────

def print_routing_summary(records: list[dict]):
    """Print a summary of routing policies used in the zone."""
    print("\n── Routing Policy Summary ──────────────────────────────────────")

    policy_counts: dict[str, int] = {}
    for record in records:
        policy = detect_routing_policy(record).split(" ")[0]  # Just the policy name
        policy_counts[policy] = policy_counts.get(policy, 0) + 1

    if not policy_counts:
        print("  (No records)")
        return

    for policy, count in sorted(policy_counts.items(), key=lambda x: -x[1]):
        bar = "█" * count
        print(f"  {policy:<15} {count:>4}  {bar}")


# ── DNS report ────────────────────────────────────────────────────────────────

def print_dns_report(hosted_zone_id: str, records: list[dict]):
    """Print the final DNS report."""
    print("\n" + "=" * 60)
    print("  Route53 DNS Report")
    print("=" * 60)
    print(f"  Hosted Zone : {hosted_zone_id}")
    print(f"  Total Records: {len(records)}")

    # Count records with health checks
    with_hc = sum(1 for r in records if r.get("HealthCheckId"))
    print(f"  With Health Checks: {with_hc}")

    # Count by routing policy
    policies = {}
    for r in records:
        p = detect_routing_policy(r).split(" ")[0]
        policies[p] = policies.get(p, 0) + 1

    print("\n  Routing Policies:")
    for policy, count in sorted(policies.items()):
        print(f"    {policy:<15} : {count}")

    print("=" * 60 + "\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Check Route53 routing policies and health checks.")
    parser.add_argument("--hosted-zone-id", help="Hosted zone ID (e.g. Z1234567890ABC)")
    parser.add_argument("--list-zones",     action="store_true", help="List all hosted zones and exit")
    parser.add_argument("--profile",        help="AWS profile name", default=None)
    parser.add_argument("--region",         help="AWS region (Route53 is global)", default="us-east-1")
    args = parser.parse_args()

    if not args.hosted_zone_id and not args.list_zones:
        parser.error("Provide --hosted-zone-id or --list-zones")

    try:
        session = boto3.Session(profile_name=args.profile, region_name=args.region)
        # Route53 is a global service — always use us-east-1 endpoint
        route53 = session.client("route53", region_name="us-east-1")
    except NoCredentialsError:
        print("[ERROR] No AWS credentials found. Run 'aws configure'.")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("  Route53 DNS Checker")
    print("=" * 60)

    if args.list_zones:
        list_hosted_zones(route53)
        return

    # Full check for a specific zone
    records = list_record_sets(route53, args.hosted_zone_id)
    check_health_checks(route53, records)
    print_routing_summary(records)
    print_dns_report(args.hosted_zone_id, records)


if __name__ == "__main__":
    main()
