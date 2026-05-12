"""
env_switcher.py — Switch between Terraform environments (dev / qa / prod).

Usage:
    python env_switcher.py --env [dev|qa|prod] --action [plan|apply|destroy]

Description:
    - Selects the correct .tfvars file for the target environment.
    - Runs Terraform in the matching workspace (creates it if absent).
    - Displays a simple cost-estimate diff between environments.
    - Requires explicit confirmation before applying to prod.

Directory layout expected:
    .
    ├── main.tf
    ├── variables.tf
    ├── envs/
    │   ├── dev.tfvars
    │   ├── qa.tfvars
    │   └── prod.tfvars
"""

import subprocess
import sys
import argparse
import shutil
from pathlib import Path


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

VALID_ENVS    = ("dev", "qa", "prod")
VALID_ACTIONS = ("plan", "apply", "destroy")

# Rough monthly cost estimates per environment (USD) — update to match your infra
COST_ESTIMATES = {
    "dev":  {"ec2": 8.50,  "rds": 15.00, "misc": 5.00},
    "qa":   {"ec2": 17.00, "rds": 30.00, "misc": 8.00},
    "prod": {"ec2": 85.00, "rds": 150.00, "misc": 25.00},
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _tf() -> str:
    """Return path to terraform binary or exit."""
    path = shutil.which("terraform")
    if not path:
        err("terraform not found on PATH.")
        sys.exit(1)
    return path


def run(cmd: list[str], cwd: str = ".") -> int:
    """Run a command, stream output, return exit code."""
    info(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd)
    return result.returncode


def run_capture(cmd: list[str], cwd: str = ".") -> tuple[int, str]:
    """Run a command, capture stdout, return (exit_code, stdout)."""
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return result.returncode, result.stdout.strip()


# ── Workspace management ──────────────────────────────────────────────────────

def ensure_workspace(env: str, cwd: str) -> int:
    """
    Select the Terraform workspace for the given environment.
    Creates the workspace if it does not already exist.

    Args:
        env: Environment name (dev / qa / prod).
        cwd: Terraform working directory.

    Returns:
        Exit code (0 = success).
    """
    tf = _tf()

    # List existing workspaces
    rc, output = run_capture([tf, "workspace", "list"], cwd=cwd)
    if rc != 0:
        err("Failed to list Terraform workspaces.")
        return rc

    existing = [w.strip().lstrip("* ") for w in output.splitlines()]

    if env not in existing:
        info(f"Workspace '{env}' not found — creating it.")
        rc = run([tf, "workspace", "new", env], cwd=cwd)
        if rc != 0:
            err(f"Failed to create workspace '{env}'.")
            return rc
    else:
        rc = run([tf, "workspace", "select", env], cwd=cwd)
        if rc != 0:
            err(f"Failed to select workspace '{env}'.")
            return rc

    ok(f"Active workspace: {env}")
    return 0


# ── Cost estimate display ─────────────────────────────────────────────────────

def show_cost_estimates(target_env: str) -> None:
    """
    Print a simple cost comparison table across all environments,
    highlighting the target environment.

    Args:
        target_env: The environment about to be deployed.
    """
    print(f"\n{C.BOLD}Monthly Cost Estimates (USD){C.RESET}")
    print(f"  {'Env':<8} {'EC2':>10} {'RDS':>10} {'Misc':>10} {'Total':>10}")
    print("  " + "-" * 44)

    for env, costs in COST_ESTIMATES.items():
        total = sum(costs.values())
        marker = " ◀ target" if env == target_env else ""
        color  = C.YELLOW if env == target_env else ""
        print(
            f"  {color}{env:<8} "
            f"${costs['ec2']:>9.2f} "
            f"${costs['rds']:>9.2f} "
            f"${costs['misc']:>9.2f} "
            f"${total:>9.2f}{C.RESET}{marker}"
        )
    print()


# ── Prod confirmation ─────────────────────────────────────────────────────────

def confirm_prod(action: str) -> bool:
    """
    Prompt the user to confirm a destructive action against production.

    Args:
        action: The Terraform action (apply / destroy).

    Returns:
        True if the user confirms, False otherwise.
    """
    warn(f"You are about to run '{action}' against PRODUCTION.")
    warn("This affects live infrastructure. Double-check the plan output above.")
    answer = input(f"\n  Type 'yes' to confirm {action} on prod: ").strip().lower()
    return answer == "yes"


# ── Main workflow ─────────────────────────────────────────────────────────────

def switch_and_run(env: str, action: str, tf_dir: str, auto_approve: bool) -> int:
    """
    Full workflow: select workspace → run terraform action.

    Args:
        env:          Target environment (dev / qa / prod).
        action:       Terraform action (plan / apply / destroy).
        tf_dir:       Path to the Terraform configuration directory.
        auto_approve: Pass -auto-approve to apply/destroy.

    Returns:
        Exit code.
    """
    tf = _tf()
    cwd = str(Path(tf_dir).resolve())

    # Locate the tfvars file
    var_file = Path(cwd) / "envs" / f"{env}.tfvars"
    if not var_file.exists():
        err(f"tfvars file not found: {var_file}")
        err("Expected layout: <tf_dir>/envs/{dev,qa,prod}.tfvars")
        return 1

    print(f"\n{C.BOLD}Environment Switcher{C.RESET}")
    info(f"Environment : {env}")
    info(f"Action      : {action}")
    info(f"Config dir  : {cwd}")
    info(f"Vars file   : {var_file}")

    # Show cost estimates before any action
    show_cost_estimates(env)

    # 1. Init (idempotent — safe to run every time)
    rc = run([tf, "init", "-input=false"], cwd=cwd)
    if rc != 0:
        err("terraform init failed.")
        return rc

    # 2. Select / create workspace
    rc = ensure_workspace(env, cwd)
    if rc != 0:
        return rc

    # 3. Build the terraform command
    tf_args = [tf, action, "-input=false", f"-var-file={var_file}"]

    if action == "plan":
        tf_args += ["-out=plan.tfplan"]

    elif action in ("apply", "destroy"):
        # Require explicit confirmation for prod
        if env == "prod" and not auto_approve:
            if not confirm_prod(action):
                warn("Aborted by user.")
                return 0
        if auto_approve:
            tf_args.append("-auto-approve")
        if action == "apply":
            plan_file = Path(cwd) / "plan.tfplan"
            if plan_file.exists():
                tf_args.append("plan.tfplan")

    # 4. Run the action
    rc = run(tf_args, cwd=cwd)
    if rc == 0:
        ok(f"terraform {action} on '{env}' completed successfully.")
    else:
        err(f"terraform {action} on '{env}' failed (exit {rc}).")

    return rc


# ── CLI entry point ───────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Switch between Terraform environments and run actions.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  python env_switcher.py --env dev  --action plan\n"
               "  python env_switcher.py --env qa   --action apply\n"
               "  python env_switcher.py --env prod --action apply --auto-approve",
    )
    parser.add_argument("--env",    required=True, choices=VALID_ENVS,    help="Target environment.")
    parser.add_argument("--action", required=True, choices=VALID_ACTIONS, help="Terraform action to run.")
    parser.add_argument("--dir",    default=".",   help="Terraform config directory (default: current dir).")
    parser.add_argument("--auto-approve", action="store_true", help="Skip confirmation prompts.")

    args = parser.parse_args()
    rc = switch_and_run(args.env, args.action, args.dir, args.auto_approve)
    sys.exit(rc)


if __name__ == "__main__":
    main()
