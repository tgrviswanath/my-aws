"""
pipeline_trigger.py — Trigger and monitor a GitHub Actions Terraform pipeline.

Usage:
    python pipeline_trigger.py --repo owner/repo --env dev [--workflow terraform.yml]

Requirements:
    - GITHUB_TOKEN environment variable with 'actions:write' scope.
    - The target workflow must support the 'workflow_dispatch' event.

Behaviour:
    1. Triggers the workflow via the GitHub Actions REST API.
    2. Polls until the new run appears in the run list.
    3. Polls the run status until it reaches a terminal state.
    4. Prints the logs URL and a pass/fail result.
"""

import os
import sys
import time
import argparse
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    print("[ERR] 'requests' package not found. Install it: pip install requests")
    sys.exit(1)


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


# ── GitHub API client ─────────────────────────────────────────────────────────

class GitHubActions:
    """Thin wrapper around the GitHub Actions REST API."""

    BASE = "https://api.github.com"

    def __init__(self, token: str, repo: str) -> None:
        """
        Args:
            token: GitHub personal access token or GITHUB_TOKEN.
            repo:  Repository in 'owner/repo' format.
        """
        self.repo = repo
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept":        "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })

    def _url(self, path: str) -> str:
        return f"{self.BASE}/repos/{self.repo}/{path}"

    def trigger_workflow(self, workflow_id: str, ref: str, inputs: dict) -> None:
        """
        Trigger a workflow_dispatch event.

        Args:
            workflow_id: Workflow file name (e.g. 'terraform.yml') or numeric ID.
            ref:         Git ref (branch or tag) to run on.
            inputs:      Key/value inputs passed to the workflow.

        Raises:
            SystemExit: On non-204 response.
        """
        url = self._url(f"actions/workflows/{workflow_id}/dispatches")
        payload = {"ref": ref, "inputs": inputs}
        resp = self.session.post(url, json=payload)
        if resp.status_code != 204:
            err(f"Failed to trigger workflow: {resp.status_code} {resp.text}")
            sys.exit(1)

    def get_latest_run(self, workflow_id: str, triggered_after: datetime) -> dict | None:
        """
        Return the most recent workflow run created after `triggered_after`.

        Args:
            workflow_id:      Workflow file name or ID.
            triggered_after:  Datetime threshold (UTC).

        Returns:
            Run dict or None if not yet visible.
        """
        url = self._url(f"actions/workflows/{workflow_id}/runs")
        resp = self.session.get(url, params={"per_page": 10})
        resp.raise_for_status()
        runs = resp.json().get("workflow_runs", [])

        for run in runs:
            created = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
            if created >= triggered_after:
                return run
        return None

    def get_run(self, run_id: int) -> dict:
        """Fetch the current state of a workflow run."""
        url = self._url(f"actions/runs/{run_id}")
        resp = self.session.get(url)
        resp.raise_for_status()
        return resp.json()


# ── Polling helpers ───────────────────────────────────────────────────────────

TERMINAL_CONCLUSIONS = {"success", "failure", "cancelled", "skipped", "timed_out", "action_required"}
POLL_INTERVAL_S = 15   # seconds between status polls
MAX_WAIT_S      = 1800  # 30 minutes maximum wait


def wait_for_run(gh: GitHubActions, workflow_id: str, triggered_after: datetime) -> dict:
    """
    Poll until the triggered workflow run appears in the API.

    Args:
        gh:               GitHubActions client.
        workflow_id:      Workflow file name or ID.
        triggered_after:  Datetime the dispatch was sent (UTC).

    Returns:
        The workflow run dict.
    """
    info("Waiting for workflow run to appear …")
    deadline = time.time() + 60  # runs usually appear within 10 s
    while time.time() < deadline:
        run = gh.get_latest_run(workflow_id, triggered_after)
        if run:
            ok(f"Run found: #{run['run_number']} (id={run['id']})")
            return run
        time.sleep(5)

    err("Timed out waiting for the workflow run to appear.")
    sys.exit(1)


def poll_until_complete(gh: GitHubActions, run_id: int) -> dict:
    """
    Poll a workflow run until it reaches a terminal state.

    Args:
        gh:     GitHubActions client.
        run_id: Numeric run ID.

    Returns:
        Final run dict.
    """
    deadline = time.time() + MAX_WAIT_S
    spinner = ["|", "/", "-", "\\"]
    tick = 0

    while time.time() < deadline:
        run = gh.get_run(run_id)
        status     = run.get("status", "unknown")
        conclusion = run.get("conclusion")

        spin = spinner[tick % len(spinner)]
        print(f"\r  {spin} Status: {status:<15}", end="", flush=True)
        tick += 1

        if status == "completed":
            print()  # newline after spinner
            return run

        time.sleep(POLL_INTERVAL_S)

    print()
    err(f"Timed out after {MAX_WAIT_S // 60} minutes.")
    sys.exit(1)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Trigger and monitor a GitHub Actions Terraform pipeline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  export GITHUB_TOKEN=ghp_...\n"
               "  python pipeline_trigger.py --repo myorg/infra --env dev\n"
               "  python pipeline_trigger.py --repo myorg/infra --env prod --ref main",
    )
    parser.add_argument("--repo",     required=True, help="GitHub repository in 'owner/repo' format.")
    parser.add_argument("--env",      required=True, choices=["dev", "qa", "prod"], help="Target environment.")
    parser.add_argument("--workflow", default="terraform.yml", help="Workflow file name (default: terraform.yml).")
    parser.add_argument("--ref",      default="main",          help="Git branch or tag to run on (default: main).")
    args = parser.parse_args()

    # Retrieve token from environment (never pass secrets as CLI args)
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        err("GITHUB_TOKEN environment variable is not set.")
        sys.exit(1)

    gh = GitHubActions(token, args.repo)

    print(f"\n{C.BOLD}GitHub Actions Pipeline Trigger{C.RESET}")
    info(f"Repository : {args.repo}")
    info(f"Workflow   : {args.workflow}")
    info(f"Branch/ref : {args.ref}")
    info(f"Environment: {args.env}")
    print()

    # Record the time just before triggering so we can identify the new run
    triggered_at = datetime.now(tz=timezone.utc)

    # 1. Trigger the workflow
    info("Dispatching workflow …")
    gh.trigger_workflow(
        workflow_id=args.workflow,
        ref=args.ref,
        inputs={"environment": args.env},
    )
    ok("Workflow dispatch sent.")

    # 2. Wait for the run to appear
    run = wait_for_run(gh, args.workflow, triggered_at)
    run_id  = run["id"]
    run_url = run["html_url"]
    info(f"Tracking run: {run_url}")

    # 3. Poll until complete
    info("Polling for completion …")
    final_run = poll_until_complete(gh, run_id)

    conclusion = final_run.get("conclusion", "unknown")
    logs_url   = final_run.get("logs_url", run_url)

    # 4. Print result
    print(f"\n{'─' * 55}")
    if conclusion == "success":
        ok(f"Pipeline PASSED  (conclusion: {conclusion})")
    else:
        err(f"Pipeline FAILED  (conclusion: {conclusion})")

    info(f"Logs URL : {run_url}")
    print(f"{'─' * 55}\n")

    sys.exit(0 if conclusion == "success" else 1)


if __name__ == "__main__":
    main()
