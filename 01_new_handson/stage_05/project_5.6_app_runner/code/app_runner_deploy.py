"""
app_runner_deploy.py — Deploy or update an AWS App Runner service.

Usage:
    python app_runner_deploy.py --service SERVICE --image IMAGE_URI [options]

Description:
    - If the named service does not exist, creates a new App Runner service
      from the given ECR image URI.
    - If the service already exists, triggers an update with the new image URI.
    - Waits for the service to reach the RUNNING state.
    - Prints the public service URL on success.

Requirements:
    - AWS credentials with apprunner:* and iam:PassRole permissions.
    - The ECR image must be accessible from App Runner (ECR access role required).
"""

import sys
import time
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

POLL_INTERVAL_S = 20
MAX_WAIT_S      = 900   # 15 minutes

# App Runner terminal service statuses
RUNNING_STATUS  = "RUNNING"
FAILED_STATUSES = {"CREATE_FAILED", "UPDATE_FAILED", "DELETE_FAILED"}


# ── Service lookup ────────────────────────────────────────────────────────────

def find_service(ar, service_name: str) -> dict | None:
    """
    Search for an App Runner service by name.

    Args:
        ar:           boto3 App Runner client.
        service_name: Service name to look for.

    Returns:
        Service summary dict if found, None otherwise.
    """
    paginator = ar.get_paginator("list_services")
    for page in paginator.paginate():
        for svc in page.get("ServiceSummaryList", []):
            if svc["ServiceName"] == service_name:
                return svc
    return None


def get_service_arn(ar, service_name: str) -> str | None:
    """Return the ARN of a service by name, or None."""
    svc = find_service(ar, service_name)
    return svc["ServiceArn"] if svc else None


# ── Create ────────────────────────────────────────────────────────────────────

def create_service(
    ar,
    service_name: str,
    image_uri: str,
    port: int,
    cpu: str,
    memory: str,
    access_role_arn: str | None,
) -> dict:
    """
    Create a new App Runner service from an ECR image.

    Args:
        ar:              boto3 App Runner client.
        service_name:    Name for the new service.
        image_uri:       Full ECR image URI (e.g. 123.dkr.ecr.us-east-1.amazonaws.com/app:v1).
        port:            Container port the application listens on.
        cpu:             vCPU allocation ('0.25 vCPU', '0.5 vCPU', '1 vCPU', '2 vCPU', '4 vCPU').
        memory:          Memory allocation ('0.5 GB', '1 GB', '2 GB', …).
        access_role_arn: IAM role ARN that grants App Runner access to ECR.
                         Required for private ECR images.

    Returns:
        Service dict from the API response.
    """
    image_config: dict = {
        "ImageIdentifier":     image_uri,
        "ImageRepositoryType": "ECR",
        "ImageConfiguration": {
            "Port": str(port),
        },
    }
    if access_role_arn:
        image_config["AuthenticationConfiguration"] = {
            "AccessRoleArn": access_role_arn
        }

    response = ar.create_service(
        ServiceName=service_name,
        SourceConfiguration={
            "ImageRepository":        image_config,
            "AutoDeploymentsEnabled": False,  # manual deploys only
        },
        InstanceConfiguration={
            "Cpu":    cpu,
            "Memory": memory,
        },
    )
    return response["Service"]


# ── Update ────────────────────────────────────────────────────────────────────

def update_service(ar, service_arn: str, image_uri: str) -> dict:
    """
    Update an existing App Runner service with a new image URI.

    Args:
        ar:          boto3 App Runner client.
        service_arn: ARN of the service to update.
        image_uri:   New image URI.

    Returns:
        Updated service dict.
    """
    response = ar.update_service(
        ServiceArn=service_arn,
        SourceConfiguration={
            "ImageRepository": {
                "ImageIdentifier":     image_uri,
                "ImageRepositoryType": "ECR",
                "ImageConfiguration":  {},
            },
            "AutoDeploymentsEnabled": False,
        },
    )
    return response["Service"]


# ── Wait for RUNNING ──────────────────────────────────────────────────────────

def wait_for_running(ar, service_arn: str) -> tuple[bool, str]:
    """
    Poll the service until it reaches RUNNING or a failed state.

    Args:
        ar:          boto3 App Runner client.
        service_arn: Service ARN to monitor.

    Returns:
        (success, service_url) — service_url is empty on failure.
    """
    info("Waiting for service to reach RUNNING state …")
    deadline = time.time() + MAX_WAIT_S
    spinner  = ["|", "/", "-", "\\"]
    tick     = 0

    while time.time() < deadline:
        response = ar.describe_service(ServiceArn=service_arn)
        svc    = response["Service"]
        status = svc["Status"]

        spin = spinner[tick % len(spinner)]
        print(f"\r  {spin} Status: {status:<30}", end="", flush=True)
        tick += 1

        if status == RUNNING_STATUS:
            print()
            return True, svc.get("ServiceUrl", "")

        if status in FAILED_STATUSES:
            print()
            return False, ""

        time.sleep(POLL_INTERVAL_S)

    print()
    err(f"Timed out after {MAX_WAIT_S // 60} minutes.")
    return False, ""


# ── Main ──────────────────────────────────────────────────────────────────────

def deploy(
    service_name: str,
    image_uri: str,
    port: int,
    cpu: str,
    memory: str,
    access_role_arn: str | None,
    region: str,
    profile: str | None,
) -> int:
    """
    Create or update an App Runner service and wait for it to be RUNNING.

    Returns:
        0 on success, 1 on failure.
    """
    session = boto3.Session(region_name=region, profile_name=profile)
    ar = session.client("apprunner")

    print(f"\n{C.BOLD}App Runner Deployment{C.RESET}")
    info(f"Service : {service_name}")
    info(f"Image   : {image_uri}")
    info(f"Port    : {port}")
    info(f"CPU     : {cpu}  |  Memory: {memory}")
    print()

    try:
        existing_arn = get_service_arn(ar, service_name)

        if existing_arn:
            info(f"Service exists ({existing_arn}) — updating image …")
            svc = update_service(ar, existing_arn, image_uri)
            service_arn = svc["ServiceArn"]
            ok("Update triggered.")
        else:
            info("Service not found — creating new service …")
            svc = create_service(ar, service_name, image_uri, port, cpu, memory, access_role_arn)
            service_arn = svc["ServiceArn"]
            ok(f"Service created: {service_arn}")

        # Wait for RUNNING
        success, service_url = wait_for_running(ar, service_arn)

    except ClientError as exc:
        err(f"AWS API error: {exc}")
        return 1

    # Summary
    print(f"\n{'─' * 55}")
    if success:
        ok("Service is RUNNING")
        info(f"Service URL : https://{service_url}")
    else:
        err("Service failed to reach RUNNING state.")
        info("Check the App Runner console for event logs.")
    print(f"{'─' * 55}\n")

    return 0 if success else 1


# ── CLI entry point ───────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deploy or update an AWS App Runner service from ECR.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  python app_runner_deploy.py --service my-api --image 123.dkr.ecr.us-east-1.amazonaws.com/my-api:v2\n"
               "  python app_runner_deploy.py --service my-api --image 123.dkr.ecr.us-east-1.amazonaws.com/my-api:v2 --port 8080",
    )
    parser.add_argument("--service",          required=True, help="App Runner service name.")
    parser.add_argument("--image",            required=True, help="Full ECR image URI.")
    parser.add_argument("--port",             default=8080,  type=int, help="Container port (default: 8080).")
    parser.add_argument("--cpu",              default="1 vCPU",  help="vCPU allocation (default: '1 vCPU').")
    parser.add_argument("--memory",           default="2 GB",    help="Memory allocation (default: '2 GB').")
    parser.add_argument("--access-role-arn",  default=None,  help="IAM role ARN for ECR access (required for private ECR).")
    parser.add_argument("--region",           default="us-east-1", help="AWS region (default: us-east-1).")
    parser.add_argument("--profile",          default=None,        help="AWS CLI profile name.")
    args = parser.parse_args()

    try:
        rc = deploy(
            args.service, args.image, args.port,
            args.cpu, args.memory, args.access_role_arn,
            args.region, args.profile,
        )
    except NoCredentialsError:
        err("AWS credentials not found.")
        rc = 1

    sys.exit(rc)


if __name__ == "__main__":
    main()
