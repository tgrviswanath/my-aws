"""
blue_green_deploy.py — Control blue-green deployments via AWS CodeDeploy.

Usage:
    python blue_green_deploy.py --app APP --group GROUP --revision IMAGE
    python blue_green_deploy.py --app APP --group GROUP --revision IMAGE --rollback

Description:
    1. Creates a CodeDeploy deployment for the given application and group.
    2. Monitors deployment status, printing traffic-shift progress.
    3. Supports automatic rollback on failure.

Revision format:
    For ECS blue-green deployments the revision is an AppSpec stored in S3:
        s3://bucket/path/appspec.yaml
    Or an inline AppSpec JSON string (passed as --revision).

Requirements:
    - AWS credentials with codedeploy:* permissions.
    - CodeDeploy application and deployment group already configured.
"""

import sys
import time
import json
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

POLL_INTERVAL_S = 15
MAX_WAIT_S      = 1800  # 30 minutes

# CodeDeploy terminal deployment statuses
TERMINAL_STATUSES = {"Succeeded", "Failed", "Stopped"}

# Traffic shift lifecycle events (ECS blue-green)
TRAFFIC_EVENTS = [
    ("BeforeAllowTraffic",  "0%   → Hooks running before traffic shift"),
    ("AllowTrafficToNewSet", "10%  → Shifting traffic to new (green) set"),
    ("AfterAllowTraffic",   "100% → All traffic on green, hooks running"),
]


# ── Revision builder ──────────────────────────────────────────────────────────

def build_revision(revision_str: str) -> dict:
    """
    Build a CodeDeploy revision location dict from the --revision argument.

    Supports two formats:
        s3://bucket/key[#version]  → S3 revision
        <anything else>            → Treated as a raw AppSpec string (GitHub/string)

    Args:
        revision_str: Value passed via --revision CLI argument.

    Returns:
        CodeDeploy RevisionLocation dict.
    """
    if revision_str.startswith("s3://"):
        # Parse s3://bucket/key or s3://bucket/key#version
        without_scheme = revision_str[5:]
        bucket, _, rest = without_scheme.partition("/")
        key, _, version = rest.partition("#")
        location: dict = {
            "revisionType": "S3",
            "s3Location": {
                "bucket":     bucket,
                "key":        key,
                "bundleType": "YAML",
            },
        }
        if version:
            location["s3Location"]["version"] = version
        return location

    # Fallback: treat as a raw AppSpec string
    return {
        "revisionType": "String",
        "string": {
            "content":    revision_str,
            "sha256":     "",  # CodeDeploy will compute this
        },
    }


# ── Deployment creation ───────────────────────────────────────────────────────

def create_deployment(
    cd,
    app: str,
    group: str,
    revision: dict,
    description: str,
    auto_rollback: bool,
) -> str:
    """
    Create a new CodeDeploy deployment.

    Args:
        cd:            boto3 CodeDeploy client.
        app:           CodeDeploy application name.
        group:         Deployment group name.
        revision:      RevisionLocation dict.
        description:   Human-readable deployment description.
        auto_rollback: Enable automatic rollback on failure.

    Returns:
        Deployment ID string.
    """
    kwargs: dict = {
        "applicationName":     app,
        "deploymentGroupName": group,
        "revision":            revision,
        "description":         description,
        "fileExistsBehavior":  "OVERWRITE",
    }

    if auto_rollback:
        kwargs["autoRollbackConfiguration"] = {
            "enabled": True,
            "events":  ["DEPLOYMENT_FAILURE", "DEPLOYMENT_STOP_ON_ALARM"],
        }

    response = cd.create_deployment(**kwargs)
    return response["deploymentId"]


# ── Status polling ────────────────────────────────────────────────────────────

def get_deployment_info(cd, deployment_id: str) -> dict:
    """Fetch the current deployment info dict."""
    response = cd.get_deployment(deploymentId=deployment_id)
    return response["deploymentInfo"]


def print_traffic_progress(deployment_info: dict) -> None:
    """
    Print a traffic-shift progress line based on deployment lifecycle events.

    Args:
        deployment_info: Deployment info dict from get_deployment.
    """
    overview = deployment_info.get("deploymentOverview", {})
    pending   = overview.get("Pending",   0)
    in_prog   = overview.get("InProgress", 0)
    succeeded = overview.get("Succeeded", 0)
    failed    = overview.get("Failed",    0)
    skipped   = overview.get("Skipped",   0)

    print(
        f"\r  Instances — "
        f"pending={pending}  in-progress={in_prog}  "
        f"succeeded={succeeded}  failed={failed}  skipped={skipped}   ",
        end="",
        flush=True,
    )


def poll_deployment(cd, deployment_id: str) -> str:
    """
    Poll a CodeDeploy deployment until it reaches a terminal state.

    Prints traffic-shift progress at each poll interval.

    Args:
        cd:            boto3 CodeDeploy client.
        deployment_id: Deployment ID to monitor.

    Returns:
        Final deployment status string (e.g. 'Succeeded', 'Failed').
    """
    info(f"Monitoring deployment: {deployment_id}")
    deadline = time.time() + MAX_WAIT_S

    # Print traffic shift milestones once
    printed_milestones: set[str] = set()

    while time.time() < deadline:
        dep_info = get_deployment_info(cd, deployment_id)
        status   = dep_info.get("status", "Unknown")

        # Print traffic shift milestones based on lifecycle events
        lifecycle = dep_info.get("deploymentLifecycleEvents", [])
        for event in lifecycle:
            name  = event.get("lifecycleEventName", "")
            state = event.get("status", "")
            key   = f"{name}:{state}"
            if key not in printed_milestones and state in ("InProgress", "Succeeded"):
                printed_milestones.add(key)
                for milestone_name, milestone_desc in TRAFFIC_EVENTS:
                    if milestone_name == name:
                        print(f"\n  {C.YELLOW}▶{C.RESET} {milestone_desc}")

        print_traffic_progress(dep_info)

        if status in TERMINAL_STATUSES:
            print()  # newline after progress line
            return status

        time.sleep(POLL_INTERVAL_S)

    print()
    err(f"Timed out after {MAX_WAIT_S // 60} minutes.")
    return "TimedOut"


# ── Rollback ──────────────────────────────────────────────────────────────────

def stop_and_rollback(cd, deployment_id: str) -> None:
    """
    Stop the deployment and trigger a rollback.

    Args:
        cd:            boto3 CodeDeploy client.
        deployment_id: Deployment ID to roll back.
    """
    warn("Initiating rollback …")
    try:
        cd.stop_deployment(
            deploymentId=deployment_id,
            autoRollbackEnabled=True,
        )
        ok("Rollback initiated.")
    except ClientError as exc:
        err(f"Failed to initiate rollback: {exc}")


# ── Main ──────────────────────────────────────────────────────────────────────

def deploy(
    app: str,
    group: str,
    revision_str: str,
    region: str,
    profile: str | None,
    auto_rollback: bool,
) -> int:
    """
    Orchestrate the full blue-green deployment workflow.

    Args:
        app:           CodeDeploy application name.
        group:         Deployment group name.
        revision_str:  Revision string (S3 URI or AppSpec content).
        region:        AWS region.
        profile:       Optional AWS CLI profile.
        auto_rollback: Enable automatic rollback on failure.

    Returns:
        0 on success, 1 on failure.
    """
    session = boto3.Session(region_name=region, profile_name=profile)
    cd = session.client("codedeploy")

    print(f"\n{C.BOLD}Blue-Green Deployment{C.RESET}")
    info(f"Application      : {app}")
    info(f"Deployment group : {group}")
    info(f"Revision         : {revision_str[:80]}{'…' if len(revision_str) > 80 else ''}")
    info(f"Auto-rollback    : {auto_rollback}")
    print()

    revision = build_revision(revision_str)

    try:
        # 1. Create deployment
        deployment_id = create_deployment(
            cd, app, group, revision,
            description=f"Deployed via blue_green_deploy.py",
            auto_rollback=auto_rollback,
        )
        ok(f"Deployment created: {deployment_id}")

        # 2. Poll until complete
        final_status = poll_deployment(cd, deployment_id)

    except ClientError as exc:
        err(f"AWS API error: {exc}")
        return 1

    # 3. Print result
    print(f"\n{'─' * 55}")
    if final_status == "Succeeded":
        ok(f"Deployment SUCCEEDED  (id={deployment_id})")
        print(f"  {C.GREEN}100% traffic now on the green (new) environment.{C.RESET}")
    else:
        err(f"Deployment {final_status}  (id={deployment_id})")
        if auto_rollback:
            stop_and_rollback(cd, deployment_id)
    print(f"{'─' * 55}\n")

    return 0 if final_status == "Succeeded" else 1


# ── CLI entry point ───────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Control blue-green deployments via AWS CodeDeploy.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  python blue_green_deploy.py --app MyApp --group prod-bg --revision s3://my-bucket/appspec.yaml\n"
               "  python blue_green_deploy.py --app MyApp --group prod-bg --revision s3://my-bucket/appspec.yaml --rollback",
    )
    parser.add_argument("--app",      required=True, help="CodeDeploy application name.")
    parser.add_argument("--group",    required=True, help="Deployment group name.")
    parser.add_argument("--revision", required=True, help="S3 URI (s3://bucket/key) or AppSpec string.")
    parser.add_argument("--rollback", action="store_true", help="Enable auto-rollback on failure.")
    parser.add_argument("--region",   default="us-east-1", help="AWS region (default: us-east-1).")
    parser.add_argument("--profile",  default=None,        help="AWS CLI profile name.")
    args = parser.parse_args()

    try:
        rc = deploy(args.app, args.group, args.revision, args.region, args.profile, args.rollback)
    except NoCredentialsError:
        err("AWS credentials not found.")
        rc = 1

    sys.exit(rc)


if __name__ == "__main__":
    main()
