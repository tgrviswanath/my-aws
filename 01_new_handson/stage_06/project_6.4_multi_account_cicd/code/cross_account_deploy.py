"""
cross_account_deploy.py — Deploy to a target AWS account via IAM role assumption.

Usage:
    python cross_account_deploy.py \\
        --target-account 123456789012 \\
        --role DeployRole \\
        --cluster CLUSTER \\
        --service SERVICE \\
        --image IMAGE_URI \\
        [--region REGION]

Description:
    1. Uses STS AssumeRole to obtain temporary credentials for the target account.
    2. Prints the assumed-role session info (account, ARN, expiry).
    3. Uses the temporary credentials to update an ECS Fargate service in the
       target account with a new container image.
    4. Polls until the deployment completes and prints the final status.

Security notes:
    - The cross-account role must have a trust policy allowing the source account
      (or specific role/user) to assume it.
    - Temporary credentials expire after the session duration (default: 1 hour).
    - Credentials are never written to disk or logged.

Requirements:
    - AWS credentials in the source account with sts:AssumeRole permission.
    - Target account role with ECS deploy permissions.
"""

import sys
import time
import argparse
from datetime import timezone

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

POLL_INTERVAL_S = 15
MAX_WAIT_S      = 600   # 10 minutes
SESSION_NAME    = "CrossAccountDeploy"


# ── STS role assumption ───────────────────────────────────────────────────────

def assume_role(
    target_account: str,
    role_name: str,
    region: str,
    profile: str | None,
    session_duration: int = 3600,
) -> dict:
    """
    Assume a cross-account IAM role and return temporary credentials.

    Args:
        target_account:   12-digit AWS account ID of the target account.
        role_name:        Name of the IAM role to assume in the target account.
        region:           AWS region for the STS call.
        profile:          Optional AWS CLI profile for the source account.
        session_duration: Credential validity in seconds (default: 3600).

    Returns:
        Dict with keys: AccessKeyId, SecretAccessKey, SessionToken, Expiration.

    Raises:
        SystemExit: If the role assumption fails.
    """
    role_arn = f"arn:aws:iam::{target_account}:role/{role_name}"
    info(f"Assuming role: {role_arn}")

    source_session = boto3.Session(region_name=region, profile_name=profile)
    sts = source_session.client("sts")

    try:
        response = sts.assume_role(
            RoleArn=role_arn,
            RoleSessionName=SESSION_NAME,
            DurationSeconds=session_duration,
        )
    except ClientError as exc:
        err(f"Failed to assume role: {exc}")
        sys.exit(1)

    creds = response["Credentials"]
    assumed_arn = response["AssumedRoleUser"]["Arn"]
    expiry = creds["Expiration"].astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    ok(f"Role assumed successfully.")
    info(f"Assumed role ARN : {assumed_arn}")
    info(f"Credentials valid until: {expiry}")

    return creds


def build_target_session(creds: dict, region: str) -> boto3.Session:
    """
    Build a boto3 Session using temporary STS credentials.

    Args:
        creds:  Credentials dict from STS AssumeRole.
        region: AWS region for the target session.

    Returns:
        boto3.Session configured with temporary credentials.
    """
    return boto3.Session(
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"],
        region_name=region,
    )


# ── ECS deployment helpers (target account) ───────────────────────────────────

def get_current_task_def(ecs, cluster: str, service: str) -> str:
    """Return the active task definition ARN for the service."""
    response = ecs.describe_services(cluster=cluster, services=[service])
    services = response.get("services", [])
    if not services:
        err(f"Service '{service}' not found in cluster '{cluster}'.")
        sys.exit(1)
    return services[0]["taskDefinition"]


def register_updated_task_def(ecs, current_td_arn: str, new_image: str) -> str:
    """
    Register a new task definition revision with the updated image.

    Preserves all existing settings; only the first container's image is changed.

    Args:
        ecs:            boto3 ECS client (target account credentials).
        current_td_arn: Current task definition ARN.
        new_image:      New container image URI.

    Returns:
        New task definition ARN.
    """
    response = ecs.describe_task_definition(taskDefinition=current_td_arn)
    td = response["taskDefinition"]

    containers = td["containerDefinitions"]
    if not containers:
        err("Task definition has no container definitions.")
        sys.exit(1)

    old_image = containers[0]["image"]
    containers[0]["image"] = new_image
    info(f"Image update: {old_image}  →  {new_image}")

    # Strip read-only fields before re-registering
    _STRIP = {
        "taskDefinitionArn", "revision", "status",
        "requiresAttributes", "compatibilities",
        "registeredAt", "registeredBy",
    }
    kwargs = {k: v for k, v in td.items() if k not in _STRIP}
    kwargs["containerDefinitions"] = containers

    new_td = ecs.register_task_definition(**kwargs)
    new_arn = new_td["taskDefinition"]["taskDefinitionArn"]
    ok(f"Registered task definition: {new_arn}")
    return new_arn


def update_ecs_service(ecs, cluster: str, service: str, task_def_arn: str) -> None:
    """Update the ECS service to use the new task definition."""
    ecs.update_service(
        cluster=cluster,
        service=service,
        taskDefinition=task_def_arn,
        forceNewDeployment=True,
    )
    ok(f"Service '{service}' updated.")


def poll_deployment(ecs, cluster: str, service: str, new_td_arn: str) -> bool:
    """
    Poll the ECS service until the deployment completes.

    Args:
        ecs:        boto3 ECS client.
        cluster:    ECS cluster name.
        service:    ECS service name.
        new_td_arn: Task definition ARN we are waiting for.

    Returns:
        True on success, False on failure or timeout.
    """
    info("Polling deployment in target account …")
    deadline = time.time() + MAX_WAIT_S
    seen_events: set[str] = set()

    while time.time() < deadline:
        response = ecs.describe_services(cluster=cluster, services=[service])
        svc = response["services"][0]

        # Print new service events
        for event in reversed(svc.get("events", [])):
            eid = event["id"]
            if eid not in seen_events:
                seen_events.add(eid)
                ts  = event["createdAt"].strftime("%H:%M:%S")
                msg = event["message"]
                print(f"  [{ts}] {msg}")

        for deployment in svc.get("deployments", []):
            if deployment["taskDefinition"] == new_td_arn:
                status  = deployment["status"]
                desired = deployment["desiredCount"]
                running = deployment["runningCount"]
                failed  = deployment["failedTasks"]

                print(
                    f"\r  Deployment: {status}  "
                    f"desired={desired}  running={running}  failed={failed}   ",
                    end="",
                    flush=True,
                )

                if status == "PRIMARY" and running == desired and failed == 0:
                    print()
                    return True
                if failed > 0:
                    print()
                    err(f"Deployment has {failed} failed task(s).")
                    return False

        time.sleep(POLL_INTERVAL_S)

    print()
    err(f"Deployment timed out after {MAX_WAIT_S // 60} minutes.")
    return False


def verify_deployment(ecs, cluster: str, service: str) -> None:
    """Print a quick verification summary for the deployed service."""
    response = ecs.describe_services(cluster=cluster, services=[service])
    svc = response["services"][0]
    info(f"Service status  : {svc.get('status')}")
    info(f"Desired tasks   : {svc.get('desiredCount')}")
    info(f"Running tasks   : {svc.get('runningCount')}")
    info(f"Pending tasks   : {svc.get('pendingCount')}")


# ── Main ──────────────────────────────────────────────────────────────────────

def cross_account_deploy(
    target_account: str,
    role_name: str,
    cluster: str,
    service: str,
    image: str,
    region: str,
    profile: str | None,
) -> int:
    """
    Full cross-account deployment workflow.

    Args:
        target_account: 12-digit AWS account ID.
        role_name:      IAM role name in the target account.
        cluster:        ECS cluster name in the target account.
        service:        ECS service name in the target account.
        image:          New container image URI.
        region:         AWS region.
        profile:        Optional AWS CLI profile for the source account.

    Returns:
        0 on success, 1 on failure.
    """
    print(f"\n{C.BOLD}Cross-Account ECS Deployment{C.RESET}")
    info(f"Target account : {target_account}")
    info(f"Role           : {role_name}")
    info(f"Cluster        : {cluster}")
    info(f"Service        : {service}")
    info(f"Image          : {image}")
    print()

    try:
        # 1. Assume cross-account role
        creds = assume_role(target_account, role_name, region, profile)

        # 2. Build session with temporary credentials
        target_session = build_target_session(creds, region)
        ecs = target_session.client("ecs")

        # 3. Get current task definition
        current_td = get_current_task_def(ecs, cluster, service)
        info(f"Current task definition: {current_td}")

        # 4. Register new task definition revision
        new_td = register_updated_task_def(ecs, current_td, image)

        # 5. Update service
        update_ecs_service(ecs, cluster, service, new_td)

        # 6. Poll until complete
        success = poll_deployment(ecs, cluster, service, new_td)

    except ClientError as exc:
        err(f"AWS API error: {exc}")
        return 1

    # 7. Summary
    print(f"\n{'─' * 60}")
    if success:
        ok("Cross-account deployment SUCCEEDED")
        verify_deployment(ecs, cluster, service)
    else:
        err("Cross-account deployment FAILED — check ECS console in target account.")
    print(f"{'─' * 60}\n")

    return 0 if success else 1


# ── CLI entry point ───────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deploy to a target AWS account by assuming a cross-account IAM role.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  python cross_account_deploy.py \\\n"
               "      --target-account 123456789012 \\\n"
               "      --role DeployRole \\\n"
               "      --cluster prod-cluster \\\n"
               "      --service api \\\n"
               "      --image 123456789012.dkr.ecr.us-east-1.amazonaws.com/api:v3",
    )
    parser.add_argument("--target-account", required=True, help="12-digit AWS account ID of the target account.")
    parser.add_argument("--role",           required=True, help="IAM role name to assume in the target account.")
    parser.add_argument("--cluster",        required=True, help="ECS cluster name in the target account.")
    parser.add_argument("--service",        required=True, help="ECS service name in the target account.")
    parser.add_argument("--image",          required=True, help="Full container image URI to deploy.")
    parser.add_argument("--region",         default="us-east-1", help="AWS region (default: us-east-1).")
    parser.add_argument("--profile",        default=None,        help="AWS CLI profile for the source account.")
    args = parser.parse_args()

    try:
        rc = cross_account_deploy(
            args.target_account, args.role,
            args.cluster, args.service, args.image,
            args.region, args.profile,
        )
    except NoCredentialsError:
        err("AWS credentials not found in source account.")
        rc = 1

    sys.exit(rc)


if __name__ == "__main__":
    main()
