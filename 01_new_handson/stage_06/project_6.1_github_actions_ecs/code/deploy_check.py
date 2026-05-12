"""
deploy_check.py — Post-deployment verification for ECS services.

Usage:
    python deploy_check.py --cluster CLUSTER --service SERVICE --url URL
                           [--tg-arn TARGET_GROUP_ARN] [--region REGION]

Checks performed:
    1. ECS service: desired task count == running task count.
    2. ALB target group: all registered targets are healthy (if --tg-arn given).
    3. HTTP endpoint: service URL returns HTTP 200.

Exit code:
    0 — all checks passed
    1 — one or more checks failed
"""

import sys
import argparse

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

try:
    import requests as http_lib
    _HAS_REQUESTS = True
except ImportError:
    import urllib.request as _urllib_req
    _HAS_REQUESTS = False


# ── ANSI colors ───────────────────────────────────────────────────────────────
PASS  = "\033[92m[PASS]\033[0m"
FAIL  = "\033[91m[FAIL]\033[0m"
SKIP  = "\033[93m[SKIP]\033[0m"
INFO  = "\033[96m[INFO]\033[0m"
BOLD  = "\033[1m"
RESET = "\033[0m"


def print_result(label: str, passed: bool, detail: str = "") -> None:
    """Print a formatted PASS/FAIL line."""
    status = PASS if passed else FAIL
    suffix = f"  → {detail}" if detail else ""
    print(f"  {status}  {label}{suffix}")


# ── Check 1: ECS task counts ──────────────────────────────────────────────────

def check_ecs_tasks(ecs, cluster: str, service: str) -> bool:
    """
    Verify that the ECS service has all desired tasks in the running state.

    Args:
        ecs:     boto3 ECS client.
        cluster: ECS cluster name or ARN.
        service: ECS service name or ARN.

    Returns:
        True if desired == running and running > 0.
    """
    response = ecs.describe_services(cluster=cluster, services=[service])
    services = response.get("services", [])

    if not services:
        print_result("ECS service exists", False, f"Service '{service}' not found in cluster '{cluster}'")
        return False

    svc     = services[0]
    desired = svc.get("desiredCount", 0)
    running = svc.get("runningCount", 0)
    pending = svc.get("pendingCount", 0)
    status  = svc.get("status", "UNKNOWN")

    passed = (desired > 0) and (running == desired) and (pending == 0)
    detail = f"desired={desired}  running={running}  pending={pending}  status={status}"
    print_result("ECS tasks: desired == running", passed, detail)
    return passed


# ── Check 2: ALB target group health ─────────────────────────────────────────

def check_target_group(elbv2, tg_arn: str) -> bool:
    """
    Verify that all targets in the ALB target group are healthy.

    Args:
        elbv2:  boto3 ELBv2 client.
        tg_arn: Target group ARN.

    Returns:
        True if all registered targets are healthy.
    """
    response = elbv2.describe_target_health(TargetGroupArn=tg_arn)
    health_descriptions = response.get("TargetHealthDescriptions", [])

    if not health_descriptions:
        print_result("ALB target group: targets registered", False, "No targets registered")
        return False

    unhealthy = [
        t for t in health_descriptions
        if t["TargetHealth"]["State"] != "healthy"
    ]

    total     = len(health_descriptions)
    n_healthy = total - len(unhealthy)
    passed    = len(unhealthy) == 0

    detail = f"{n_healthy}/{total} healthy"
    if unhealthy:
        reasons = ", ".join(
            f"{t['Target']['Id']}:{t['TargetHealth'].get('Reason', 'unknown')}"
            for t in unhealthy
        )
        detail += f"  unhealthy: {reasons}"

    print_result("ALB target group: all targets healthy", passed, detail)
    return passed


# ── Check 3: HTTP endpoint ────────────────────────────────────────────────────

def check_http(url: str, expected_status: int = 200, timeout: int = 10) -> bool:
    """
    Send an HTTP GET request to the service URL and verify the response code.

    Uses the `requests` library if available, falls back to urllib.

    Args:
        url:             URL to check.
        expected_status: Expected HTTP status code (default: 200).
        timeout:         Request timeout in seconds.

    Returns:
        True if the response status matches expected_status.
    """
    try:
        if _HAS_REQUESTS:
            resp   = http_lib.get(url, timeout=timeout, allow_redirects=True)
            status = resp.status_code
        else:
            with _urllib_req.urlopen(url, timeout=timeout) as resp:
                status = resp.status

        passed = (status == expected_status)
        print_result(
            f"HTTP endpoint returns {expected_status}",
            passed,
            f"got {status} from {url}",
        )
        return passed

    except Exception as exc:
        print_result(f"HTTP endpoint returns {expected_status}", False, str(exc))
        return False


# ── Report builder ────────────────────────────────────────────────────────────

def run_checks(
    cluster: str,
    service: str,
    url: str,
    tg_arn: str | None,
    region: str,
    profile: str | None,
) -> int:
    """
    Run all post-deployment verification checks and print a summary report.

    Args:
        cluster: ECS cluster name.
        service: ECS service name.
        url:     Service URL to probe.
        tg_arn:  ALB target group ARN (optional).
        region:  AWS region.
        profile: Optional AWS CLI profile.

    Returns:
        0 if all checks pass, 1 otherwise.
    """
    session = boto3.Session(region_name=region, profile_name=profile)
    ecs   = session.client("ecs")
    elbv2 = session.client("elbv2")

    print(f"\n{BOLD}Post-Deployment Verification Report{RESET}")
    print(f"{INFO} Cluster : {cluster}")
    print(f"{INFO} Service : {service}")
    print(f"{INFO} URL     : {url}")
    if tg_arn:
        print(f"{INFO} TG ARN  : {tg_arn}")
    print("-" * 60)

    results: list[bool] = []

    try:
        # Check 1 — ECS task counts
        results.append(check_ecs_tasks(ecs, cluster, service))

        # Check 2 — ALB target group (optional)
        if tg_arn:
            results.append(check_target_group(elbv2, tg_arn))
        else:
            print(f"  {SKIP}  ALB target group check skipped (--tg-arn not provided)")

        # Check 3 — HTTP endpoint
        results.append(check_http(url))

    except NoCredentialsError:
        print(f"\n{FAIL}  AWS credentials not found.")
        return 1
    except ClientError as exc:
        print(f"\n{FAIL}  AWS API error: {exc}")
        return 1

    # Summary
    print("-" * 60)
    passed = sum(results)
    total  = len(results)

    if all(results):
        print(f"\n{PASS}  All {total}/{total} checks passed. Deployment verified!\n")
        return 0
    else:
        print(f"\n{FAIL}  {passed}/{total} checks passed. Review failures above.\n")
        return 1


# ── CLI entry point ───────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify ECS deployment health after GitHub Actions CI/CD.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  python deploy_check.py --cluster prod --service api --url https://api.example.com/health\n"
               "  python deploy_check.py --cluster prod --service api --url https://api.example.com/health \\\n"
               "                         --tg-arn arn:aws:elasticloadbalancing:us-east-1:123:targetgroup/api/abc",
    )
    parser.add_argument("--cluster", required=True, help="ECS cluster name.")
    parser.add_argument("--service", required=True, help="ECS service name.")
    parser.add_argument("--url",     required=True, help="Service URL to probe (HTTP GET).")
    parser.add_argument("--tg-arn",  default=None,  help="ALB target group ARN (optional).")
    parser.add_argument("--region",  default="us-east-1", help="AWS region (default: us-east-1).")
    parser.add_argument("--profile", default=None,        help="AWS CLI profile name.")
    args = parser.parse_args()

    rc = run_checks(args.cluster, args.service, args.url, args.tg_arn, args.region, args.profile)
    sys.exit(rc)


if __name__ == "__main__":
    main()
