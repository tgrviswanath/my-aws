"""
dr_checker.py — Verify DR network setup for Project 11.16
Usage: python dr_checker.py --hc-id <health-check-id> --domain app.yourdomain.com
       [--profile my-profile]
"""
import argparse
import socket
import boto3


def check(hc_id: str, domain: str, session: boto3.Session) -> None:
    r53 = session.client("route53")

    print(f"\n{'='*65}\n  DR Checker — Project 11.16\n{'='*65}\n")

    # 1. Health check status
    try:
        status_resp = r53.get_health_check_status(HealthCheckId=hc_id)
        observations = status_resp["HealthCheckObservations"]
        healthy = sum(1 for o in observations
                      if o["StatusReport"]["Status"].startswith("Success"))
        total = len(observations)
        icon = "✅" if healthy == total else ("⚠️ " if healthy > 0 else "❌")
        print(f"{icon}  Health Check {hc_id}: {healthy}/{total} regions healthy")
        for obs in observations[:3]:
            s = obs["StatusReport"]["Status"]
            region = obs.get("Region", "—")
            print(f"     {region}: {s[:60]}")
    except Exception as e:
        print(f"❌  Could not get health check status: {e}")

    # 2. Health check config
    try:
        hc_resp = r53.get_health_check(HealthCheckId=hc_id)
        cfg = hc_resp["HealthCheck"]["HealthCheckConfig"]
        print(f"\n  Health Check Config:")
        print(f"    Endpoint: {cfg.get('FullyQualifiedDomainName', cfg.get('IPAddress', '—'))}")
        print(f"    Path:     {cfg.get('ResourcePath', '/')}")
        print(f"    Interval: {cfg.get('RequestInterval', '—')}s")
        print(f"    Threshold:{cfg.get('FailureThreshold', '—')} failures")
    except Exception as e:
        print(f"⚠️   Could not get health check config: {e}")

    # 3. DNS resolution
    print(f"\n  DNS Resolution for {domain}:")
    try:
        ips = socket.getaddrinfo(domain, 80, socket.AF_INET)
        resolved = list({r[4][0] for r in ips})
        print(f"    ✅  Resolves to: {resolved}")
    except socket.gaierror as e:
        print(f"    ❌  DNS resolution failed: {e}")

    # 4. Failover record check
    try:
        zones = r53.list_hosted_zones()["HostedZones"]
        for zone in zones:
            records = r53.list_resource_record_sets(
                HostedZoneId=zone["Id"],
                StartRecordName=domain,
                StartRecordType="A",
                MaxItems="10"
            )["ResourceRecordSets"]
            failover_records = [r for r in records
                                if r.get("Name", "").rstrip(".") == domain.rstrip(".")
                                and r.get("Failover")]
            if failover_records:
                print(f"\n  Failover Records in zone {zone['Name'].rstrip('.')}:")
                for r in failover_records:
                    icon = "✅" if r["Failover"] in ("PRIMARY", "SECONDARY") else "⚠️ "
                    hc = r.get("HealthCheckId", "none")
                    print(f"    {icon}  {r['Failover']:10s}  HealthCheck={hc}")
    except Exception as e:
        print(f"⚠️   Could not check failover records: {e}")

    print(f"\n{'='*65}\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--hc-id",   required=True, help="Route 53 health check ID")
    p.add_argument("--domain",  required=True, help="Domain name to check DNS for")
    p.add_argument("--profile", default=None)
    args = p.parse_args()
    check(args.hc_id, args.domain, boto3.Session(profile_name=args.profile))


if __name__ == "__main__":
    main()
