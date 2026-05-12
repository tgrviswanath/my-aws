"""
terraform_runner.py — Python wrapper for Terraform CLI operations.

Usage:
    python terraform_runner.py [init|plan|apply|destroy|output]

Description:
    Wraps common Terraform commands with colored output, JSON parsing,
    and graceful error handling. Suitable for use in CI/CD pipelines
    or local development workflows.
"""

import subprocess
import sys
import json
import shutil
import argparse
from pathlib import Path


# ── ANSI color codes ──────────────────────────────────────────────────────────
class Color:
    RESET   = "\033[0m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    RED     = "\033[91m"
    CYAN    = "\033[96m"
    BOLD    = "\033[1m"


def info(msg: str) -> None:
    """Print an informational message in cyan."""
    print(f"{Color.CYAN}[INFO]{Color.RESET} {msg}")


def success(msg: str) -> None:
    """Print a success message in green."""
    print(f"{Color.GREEN}[OK]{Color.RESET}   {msg}")


def warn(msg: str) -> None:
    """Print a warning message in yellow."""
    print(f"{Color.YELLOW}[WARN]{Color.RESET} {msg}")


def error(msg: str) -> None:
    """Print an error message in red."""
    print(f"{Color.RED}[ERR]{Color.RESET}  {msg}", file=sys.stderr)


# ── Terraform helpers ─────────────────────────────────────────────────────────

def _check_terraform() -> str:
    """
    Verify that the `terraform` binary is available on PATH.

    Returns:
        str: Full path to the terraform executable.

    Raises:
        SystemExit: If terraform is not found.
    """
    tf_path = shutil.which("terraform")
    if not tf_path:
        error("terraform binary not found. Install it from https://developer.hashicorp.com/terraform/downloads")
        sys.exit(1)
    return tf_path


def run_terraform(args: list[str], cwd: str | None = None, capture_output: bool = False) -> subprocess.CompletedProcess:
    """
    Execute a terraform command as a subprocess.

    Args:
        args:           List of arguments to pass after `terraform`.
        cwd:            Working directory (defaults to current directory).
        capture_output: If True, capture stdout/stderr instead of streaming.

    Returns:
        subprocess.CompletedProcess with returncode, stdout, stderr.
    """
    tf = _check_terraform()
    cmd = [tf] + args
    info(f"Running: {' '.join(cmd)}")

    result = subprocess.run(
        cmd,
        cwd=cwd or ".",
        capture_output=capture_output,
        text=True,
    )
    return result


# ── Command implementations ───────────────────────────────────────────────────

def cmd_init(cwd: str) -> int:
    """
    Run `terraform init` to initialize the working directory.

    Args:
        cwd: Path to the Terraform configuration directory.

    Returns:
        Exit code (0 = success).
    """
    info("Initializing Terraform working directory …")
    result = run_terraform(["init", "-input=false"], cwd=cwd)
    if result.returncode == 0:
        success("terraform init completed.")
    else:
        error("terraform init failed.")
    return result.returncode


def cmd_plan(cwd: str, var_file: str | None = None) -> int:
    """
    Run `terraform plan` and save the plan to plan.tfplan.

    Args:
        cwd:      Path to the Terraform configuration directory.
        var_file: Optional path to a .tfvars file.

    Returns:
        Exit code (0 = success, 2 = changes present, other = error).
    """
    info("Generating Terraform execution plan …")
    args = ["plan", "-input=false", "-out=plan.tfplan"]
    if var_file:
        args += [f"-var-file={var_file}"]

    result = run_terraform(args, cwd=cwd)
    if result.returncode == 0:
        success("No changes. Infrastructure is up-to-date.")
    elif result.returncode == 2:
        warn("Changes detected. Review the plan before applying.")
    else:
        error("terraform plan failed.")
    return result.returncode


def cmd_apply(cwd: str, auto_approve: bool = False) -> int:
    """
    Run `terraform apply` using the saved plan file.

    Args:
        cwd:          Path to the Terraform configuration directory.
        auto_approve: Skip interactive approval prompt.

    Returns:
        Exit code (0 = success).
    """
    plan_file = Path(cwd) / "plan.tfplan"
    if not plan_file.exists():
        warn("No plan.tfplan found — running plan first.")
        rc = cmd_plan(cwd)
        if rc not in (0, 2):
            return rc

    info("Applying Terraform plan …")
    args = ["apply", "-input=false"]
    if auto_approve:
        args.append("-auto-approve")
    args.append("plan.tfplan")

    result = run_terraform(args, cwd=cwd)
    if result.returncode == 0:
        success("terraform apply completed successfully.")
    else:
        error("terraform apply failed.")
    return result.returncode


def cmd_destroy(cwd: str, auto_approve: bool = False) -> int:
    """
    Run `terraform destroy` to tear down all managed resources.

    Args:
        cwd:          Path to the Terraform configuration directory.
        auto_approve: Skip interactive approval prompt.

    Returns:
        Exit code (0 = success).
    """
    warn("This will DESTROY all resources managed by this configuration!")
    args = ["destroy", "-input=false"]
    if auto_approve:
        args.append("-auto-approve")

    result = run_terraform(args, cwd=cwd)
    if result.returncode == 0:
        success("terraform destroy completed.")
    else:
        error("terraform destroy failed.")
    return result.returncode


def cmd_output(cwd: str) -> int:
    """
    Run `terraform output -json` and pretty-print the parsed values.

    Args:
        cwd: Path to the Terraform configuration directory.

    Returns:
        Exit code (0 = success).
    """
    info("Fetching Terraform outputs …")
    result = run_terraform(["output", "-json"], cwd=cwd, capture_output=True)

    if result.returncode != 0:
        error(f"terraform output failed:\n{result.stderr}")
        return result.returncode

    try:
        outputs: dict = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        error(f"Failed to parse terraform output JSON: {exc}")
        return 1

    if not outputs:
        warn("No outputs defined in this configuration.")
        return 0

    print(f"\n{Color.BOLD}Terraform Outputs:{Color.RESET}")
    for key, meta in outputs.items():
        value = meta.get("value", "")
        sensitive = meta.get("sensitive", False)
        display = "<sensitive>" if sensitive else value
        print(f"  {Color.GREEN}{key}{Color.RESET} = {display}")

    return 0


# ── CLI entry point ───────────────────────────────────────────────────────────

COMMANDS = {
    "init":    cmd_init,
    "plan":    cmd_plan,
    "apply":   cmd_apply,
    "destroy": cmd_destroy,
    "output":  cmd_output,
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Python wrapper for common Terraform CLI operations.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  python terraform_runner.py init\n"
               "  python terraform_runner.py plan --var-file dev.tfvars\n"
               "  python terraform_runner.py apply --auto-approve\n"
               "  python terraform_runner.py destroy\n"
               "  python terraform_runner.py output",
    )
    parser.add_argument(
        "command",
        choices=list(COMMANDS.keys()),
        help="Terraform command to execute.",
    )
    parser.add_argument(
        "--dir",
        default=".",
        help="Path to the Terraform configuration directory (default: current dir).",
    )
    parser.add_argument(
        "--var-file",
        default=None,
        help="Path to a .tfvars file (used with plan).",
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Skip interactive approval for apply/destroy.",
    )

    args = parser.parse_args()
    cwd = str(Path(args.dir).resolve())

    # Dispatch to the appropriate command function
    if args.command == "init":
        rc = cmd_init(cwd)
    elif args.command == "plan":
        rc = cmd_plan(cwd, var_file=args.var_file)
    elif args.command == "apply":
        rc = cmd_apply(cwd, auto_approve=args.auto_approve)
    elif args.command == "destroy":
        rc = cmd_destroy(cwd, auto_approve=args.auto_approve)
    elif args.command == "output":
        rc = cmd_output(cwd)
    else:
        error(f"Unknown command: {args.command}")
        rc = 1

    sys.exit(rc)


if __name__ == "__main__":
    main()
