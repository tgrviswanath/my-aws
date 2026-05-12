"""
ecs_deploy.py — Deploy a new Docker image to an ECS Fargate service.

Usage:
    python ecs_deploy.py --cluster CLUSTER --service SERVICE --image IMAGE_URI

Description:
    1. Fetches the current (active) task definition for the service.
    2. Registers a new task definition revision with the updated container image.
    3. Updates the ECS service to use the new task definition.
    4. Polls service events until the deployment completes or fails.
    5. Prints the final deployment status and the new task ARN.

Requirements:
    - AWS credentials with ecs:* permissions.
    - The service must already exist in the cluster.
"""

import sys
import time
import argparse
from datetime import datetime, timezone

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


# ── Helpers ───────────────────────────────────────────────────────────────────

POLL_INTERVAL_S = 15
MAX_WAIT_S      = 600  # 10 minutes


def get_active_task_def(ecs, cluster: str, service: str) -> str:
    """
    Return the ARN of the task definition currently used by the service.

    Args:
        ecs:     boto3 ECS client.
        cluster: ECS cluster name or ARN.
        service: ECS service name or ARN.

    Returns:
        Task definition ARN string.
    """
    response = ecs.describe_services(cluster=cluster, services=[service])
    services = response.get("services", [])
    if not services:
        err(f"Service '{service}' not found in cluster '{cluster}'.")
        sys.exit(1)
    return services[0]["taskDefinition"]


def register_new_task_def(ecs, current_td_arn: str, new_image: str) -> str:
    """
    Register a new task definition revision with the updated container image.

    Only the image URI of the first container definition is changed; all other
    settings (CPU, memory, environment variables, IAM roles, etc.) are preserved.

    Args:
        ecs:            boto3 ECS client.
        current_td_arn: ARN of the existing task definition to base the new one on.
        new_image:      Full image URI to deploy (e.g. 123.dkr.ecr…/app:v2).

    Returns:
        ARN of the newly registered task definition revision.
    """
    # Fetch the full task definition
    response = ecs.describe_task_definition(taskDefinition=current_td_arn)
    td = response["taskDefinition"]

    # Update the image in the first container definition
    containers = td["containerDefinitions"]
    if not containers:
        err("Task definition has no container definitions.")
        sys.exit(1)

    old_image = containers[0]["image"]
    containers[0]["image"] = new_image
    info(f"Updating image: {old_image}  →  {new_image}")

    # Keys that cannot be passed to register_task_definition
    _STRIP_KEYS = {
        "taskDefinitionArn", "revision", "status",
        "requiresAttributes", "compatibilities",
        "registeredAt", "registeredBy",
    }
    register_kwargs = {k: v for k, v in td.items() if k not in _STRIP_KEYS}
    register_kwargs["containerDefinitions"] = containers

    new_td = ecs.register_task_definition(**register_kwargs)
    new_arn = new_td["taskDefinition"]["taskDefinitionArn"]
    ok(f"Registered new task definition: {new_arn}")
    return new_arn


def update_service(ecs, cluster: str, service: str, task_def_arn: str) -> None:
    """
    Update the ECS service to use the new task definition revision.

    Args:
        ecs:          boto3 ECS client.
        cluster:      ECS cluster name or ARN.
        service:      ECS service name or ARN.
        task_def_arn: New task definition ARN.
    """
    ecs.update_service(
        cluster=cluster,
        service=service,
        taskDefinition=task_def_arn,
        forceNewDeployment=True,
    )
    ok(f"Service '{service}' updated — deployment in progress.")


def poll_deployment(ecs, cluster: str, service: str, new_td_arn: str) -> bool:
    """
    Poll the ECS service until the deployment using `new_td_arn` completes.

    Prints service events as they arrive. Returns True on success.

    Args:
        ecs:        boto3 ECS client.
        cluster:    ECS cluster name or ARN.
        service:    ECS service name or ARN.
        new_td_arn: Task definition ARN we are waiting for.

    Returns:
        True if deployment succeeded, False otherwise.
    """
    info("Polling deployment status …")
    deadline     = time.time() + MAX_WAIT_S
    seen_events: set[str] = set()

    while time.time() < deadline:
        response = ecs.describe_services(cluster=cluster, services=[service])
        svc = response["services"][0]

        # Print new events (ECS events are newest-first)
        for event in reversed(svc.get("events", [])):
            eid = event["id"]
            if eid not in seen_events:
                seen_events.add(eid)
                ts  = event["createdAt"].strftime("%H:%M:%S")
                msg = event["message"]
                print(f"  [{ts}] {msg}")

        # Find the deployment for our task definition
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


def get_running_task_arns(ecs, cluster: str, service: str) -> list[str]:
    """
    Return the ARNs of tasks currently running for the service.

    Args:
        ecs:     boto3 ECS client.
        cluster: ECS cluster name or ARN.
        service: ECS service name or ARN.

    Returns:
        List of task ARNs.
    """
    response = ecs.list_tasks(cluster=cluster, serviceName=service, desiredStatus="RUNNING")
    return response.get("taskArns", [])


# ── Main ──────────────────────────────────────────────────────────────────────

def deploy(cluster: str, service: str, image: str, region: str, profile: str | None) -> int:
    """
    Orchestrate the full ECS Fargate deployment.

    Args:
        cluster: ECS cluster name.
        service: ECS service name.
        image:   New container image URI.
        region:  AWS region.
        profile: Optional AWS CLI profile.

    Returns:
        0 on success, 1 on failure.
    """
    session = boto3.Session(region_name=region, profile_name=profile)
    ecs = session.client("ecs")

    print(f"\n{C.BOLD}ECS Fargate Deployment{C.RESET}")
    info(f"Cluster : {cluster}")
    info(f"Service : {service}")
    info(f"Image   : {image}")
    print()

    try:
        # 1. Get current task definition
        current_td = get_active_task_def(ecs, cluster, service)
        info(f"Current task definition: {current_td}")

        # 2. Register new revision
        new_td = register_new_task_def(ecs, current_td, image)

        # 3. Update service
        update_service(ecs, cluster, service, new_td)

        # 4. Poll until complete
        success = poll_deployment(ecs, cluster, service, new_td)

    except ClientError as exc:
        err(f"AWS API error: {exc}")
        return 1

    # 5. Print summary
    print(f"\n{'─' * 55}")
    if success:
        task_arns = get_running_task_arns(ecs, cluster, service)
        ok("Deployment SUCCEEDED")
        info(f"New task definition : {new_td}")
        for arn in task_arns:
            info(f"Running task        : {arn}")
    else:
        err("Deployment FAILED — check ECS console for details.")

    print(f"{'─' * 55}\n")
    return 0 if success else 1


# ── CLI entry point ───────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deploy a new image to an ECS Fargate service.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  python ecs_deploy.py --cluster prod-cluster --service api --image 123.dkr.ecr.us-east-1.amazonaws.com/api:v2",
    )
    parser.add_argument("--cluster", required=True, help="ECS cluster name.")
    parser.add_argument("--service", required=True, help="ECS service name.")
    parser.add_argument("--image",   required=True, help="Full container image URI.")
    parser.add_argument("--region",  default="us-east-1", help="AWS region (default: us-east-1).")
    parser.add_argument("--profile", default=None,        help="AWS CLI profile name.")
    args = parser.parse_args()

    try:
        rc = deploy(args.cluster, args.service, args.image, args.region, args.profile)
    except NoCredentialsError:
        err("AWS credentials not found.")
        rc = 1

    sys.exit(rc)


if __name__ == "__main__":
    main()
