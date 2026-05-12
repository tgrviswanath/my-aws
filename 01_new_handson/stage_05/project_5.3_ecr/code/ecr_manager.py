"""
ecr_manager.py — Manage Docker images in Amazon ECR.

Usage:
    python ecr_manager.py push  --repo REPO --tag TAG  [--dockerfile PATH]
    python ecr_manager.py list  --repo REPO
    python ecr_manager.py clean --repo REPO --keep N

Commands:
    push    Authenticate to ECR, build the Docker image, tag it, and push.
    list    List all images in the repository with tags and compressed sizes.
    clean   Delete old images, keeping only the N most recently pushed.

Requirements:
    - Docker daemon running and `docker` CLI on PATH.
    - AWS credentials with ECR permissions (ecr:GetAuthorizationToken, etc.).
"""

import sys
import json
import argparse
import subprocess
import base64
from datetime import datetime

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

def run_docker(args: list[str]) -> int:
    """
    Run a docker CLI command, streaming output to the terminal.

    Args:
        args: Arguments to pass after `docker`.

    Returns:
        Exit code.
    """
    cmd = ["docker"] + args
    info(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode


def bytes_to_mb(size_bytes: int) -> str:
    """Convert bytes to a human-readable MB string."""
    return f"{size_bytes / (1024 ** 2):.1f} MB"


def get_ecr_client(region: str, profile: str | None):
    """Return a boto3 ECR client."""
    session = boto3.Session(region_name=region, profile_name=profile)
    return session.client("ecr")


def get_registry_uri(ecr, repo: str) -> str:
    """
    Return the full ECR registry URI for the given repository.

    Args:
        ecr:  boto3 ECR client.
        repo: Repository name.

    Returns:
        Full URI, e.g. 123456789012.dkr.ecr.us-east-1.amazonaws.com/my-repo
    """
    response = ecr.describe_repositories(repositoryNames=[repo])
    return response["repositories"][0]["repositoryUri"]


def ecr_login(ecr, registry: str) -> int:
    """
    Authenticate Docker to the ECR registry using a temporary token.

    Args:
        ecr:      boto3 ECR client.
        registry: ECR registry hostname (account.dkr.ecr.region.amazonaws.com).

    Returns:
        Exit code (0 = success).
    """
    info("Fetching ECR authorization token …")
    response = ecr.get_authorization_token()
    auth_data = response["authorizationData"][0]

    # Token is base64-encoded "AWS:<password>"
    token = base64.b64decode(auth_data["authorizationToken"]).decode()
    _, password = token.split(":", 1)

    rc = run_docker([
        "login",
        "--username", "AWS",
        "--password-stdin",
        registry,
    ])
    # Pass password via stdin to avoid it appearing in process list
    result = subprocess.run(
        ["docker", "login", "--username", "AWS", "--password-stdin", registry],
        input=password,
        text=True,
        capture_output=True,
    )
    if result.returncode == 0:
        ok("Docker logged in to ECR.")
    else:
        err(f"Docker login failed:\n{result.stderr}")
    return result.returncode


# ── push ──────────────────────────────────────────────────────────────────────

def cmd_push(repo: str, tag: str, dockerfile: str, region: str, profile: str | None) -> int:
    """
    Build a Docker image and push it to ECR.

    Steps:
        1. Retrieve the ECR repository URI.
        2. Authenticate Docker to the ECR registry.
        3. Build the image from the Dockerfile.
        4. Tag the image with the full ECR URI.
        5. Push the image.

    Args:
        repo:       ECR repository name.
        tag:        Image tag (e.g. 'latest', 'v1.2.3').
        dockerfile: Path to the directory containing the Dockerfile.
        region:     AWS region.
        profile:    Optional AWS CLI profile.

    Returns:
        Exit code.
    """
    ecr = get_ecr_client(region, profile)

    try:
        repo_uri = get_registry_uri(ecr, repo)
    except ClientError as exc:
        err(f"Repository '{repo}' not found: {exc}")
        return 1

    registry = repo_uri.split("/")[0]  # account.dkr.ecr.region.amazonaws.com
    full_tag  = f"{repo_uri}:{tag}"

    info(f"Repository URI : {repo_uri}")
    info(f"Image tag      : {full_tag}")

    # Login
    rc = ecr_login(ecr, registry)
    if rc != 0:
        return rc

    # Build
    rc = run_docker(["build", "-t", full_tag, dockerfile])
    if rc != 0:
        err("Docker build failed.")
        return rc

    # Push
    rc = run_docker(["push", full_tag])
    if rc != 0:
        err("Docker push failed.")
        return rc

    ok(f"Image pushed: {full_tag}")
    return 0


# ── list ──────────────────────────────────────────────────────────────────────

def cmd_list(repo: str, region: str, profile: str | None) -> int:
    """
    List all images in an ECR repository, sorted by push date (newest first).

    Args:
        repo:    ECR repository name.
        region:  AWS region.
        profile: Optional AWS CLI profile.

    Returns:
        Exit code.
    """
    ecr = get_ecr_client(region, profile)

    info(f"Listing images in repository: {repo}")
    try:
        paginator = ecr.get_paginator("describe_images")
        images = []
        for page in paginator.paginate(repositoryName=repo):
            images.extend(page.get("imageDetails", []))
    except ClientError as exc:
        err(f"Failed to list images: {exc}")
        return 1

    if not images:
        warn("No images found in this repository.")
        return 0

    # Sort newest first
    images.sort(key=lambda i: i.get("imagePushedAt", datetime.min), reverse=True)

    print(f"\n{C.BOLD}Images in {repo}{C.RESET}")
    print(f"  {'Tags':<35} {'Size':>10}  {'Pushed at'}")
    print("  " + "-" * 65)

    for img in images:
        tags      = ", ".join(img.get("imageTags", ["<untagged>"]))
        size      = bytes_to_mb(img.get("imageSizeInBytes", 0))
        pushed_at = img.get("imagePushedAt")
        ts        = pushed_at.strftime("%Y-%m-%d %H:%M UTC") if pushed_at else "unknown"
        print(f"  {tags:<35} {size:>10}  {ts}")

    print(f"\n  Total: {len(images)} image(s)\n")
    return 0


# ── clean ─────────────────────────────────────────────────────────────────────

def cmd_clean(repo: str, keep: int, region: str, profile: str | None) -> int:
    """
    Delete old images from an ECR repository, keeping the N most recent.

    Images are sorted by push date. The oldest (len - keep) images are deleted.
    Untagged images are always eligible for deletion.

    Args:
        repo:    ECR repository name.
        keep:    Number of most-recent images to retain.
        region:  AWS region.
        profile: Optional AWS CLI profile.

    Returns:
        Exit code.
    """
    ecr = get_ecr_client(region, profile)

    info(f"Fetching images from repository: {repo}")
    try:
        paginator = ecr.get_paginator("describe_images")
        images = []
        for page in paginator.paginate(repositoryName=repo):
            images.extend(page.get("imageDetails", []))
    except ClientError as exc:
        err(f"Failed to list images: {exc}")
        return 1

    if len(images) <= keep:
        ok(f"Only {len(images)} image(s) present — nothing to delete (keep={keep}).")
        return 0

    # Sort newest first; images beyond index `keep` are candidates for deletion
    images.sort(key=lambda i: i.get("imagePushedAt", datetime.min), reverse=True)
    to_delete = images[keep:]

    warn(f"Deleting {len(to_delete)} image(s) (keeping {keep} most recent) …")

    # Build image identifiers for batch delete
    ids = [{"imageDigest": img["imageDigest"]} for img in to_delete]

    # ECR batch delete accepts up to 100 images per call
    batch_size = 100
    deleted_count = 0

    for i in range(0, len(ids), batch_size):
        batch = ids[i : i + batch_size]
        try:
            response = ecr.batch_delete_image(repositoryName=repo, imageIds=batch)
            deleted_count += len(response.get("imageIds", []))
            failures = response.get("failures", [])
            for f in failures:
                warn(f"  Failed to delete {f['imageId']}: {f['failureReason']}")
        except ClientError as exc:
            err(f"Batch delete failed: {exc}")
            return 1

    ok(f"Deleted {deleted_count} image(s). Repository now has {keep} image(s).")
    return 0


# ── CLI entry point ───────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Manage Docker images in Amazon ECR.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  python ecr_manager.py push  --repo my-app --tag v1.0.0\n"
               "  python ecr_manager.py list  --repo my-app\n"
               "  python ecr_manager.py clean --repo my-app --keep 5",
    )
    parser.add_argument("--region",  default="us-east-1", help="AWS region (default: us-east-1)")
    parser.add_argument("--profile", default=None,        help="AWS CLI profile name")

    sub = parser.add_subparsers(dest="command", required=True)

    # push
    p_push = sub.add_parser("push", help="Build and push an image to ECR.")
    p_push.add_argument("--repo",       required=True, help="ECR repository name.")
    p_push.add_argument("--tag",        required=True, help="Image tag.")
    p_push.add_argument("--dockerfile", default=".",   help="Path to Dockerfile directory (default: .).")

    # list
    p_list = sub.add_parser("list", help="List images in an ECR repository.")
    p_list.add_argument("--repo", required=True, help="ECR repository name.")

    # clean
    p_clean = sub.add_parser("clean", help="Delete old images, keeping the N most recent.")
    p_clean.add_argument("--repo", required=True, help="ECR repository name.")
    p_clean.add_argument("--keep", required=True, type=int, help="Number of images to keep.")

    args = parser.parse_args()

    try:
        if args.command == "push":
            rc = cmd_push(args.repo, args.tag, args.dockerfile, args.region, args.profile)
        elif args.command == "list":
            rc = cmd_list(args.repo, args.region, args.profile)
        elif args.command == "clean":
            rc = cmd_clean(args.repo, args.keep, args.region, args.profile)
        else:
            rc = 1
    except NoCredentialsError:
        err("AWS credentials not found.")
        rc = 1

    sys.exit(rc)


if __name__ == "__main__":
    main()
