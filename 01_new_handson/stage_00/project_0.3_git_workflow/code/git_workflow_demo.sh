#!/bin/bash
# =============================================================================
# git_workflow_demo.sh — Demonstrates a real Git feature branch workflow
#
# What this script covers:
#   1. Initialise a fresh repo (or use an existing one)
#   2. Set up a .gitignore for a Python/Node project
#   3. Create a feature branch using the conventional naming pattern
#   4. Make changes and commit with Conventional Commits format
#   5. Push the branch and simulate a PR merge (fast-forward + squash options)
#   6. Tag a release
#   7. Clean up merged branches
#
# Usage:
#   chmod +x git_workflow_demo.sh
#   ./git_workflow_demo.sh [--repo-path /path/to/repo] [--remote origin]
#
# Requirements:
#   git >= 2.28 (for --initial-branch support)
# =============================================================================

set -euo pipefail   # Exit on error, unset vars, pipe failures

# ── Defaults (override via flags) ─────────────────────────────────────────────
REPO_PATH="${REPO_PATH:-./demo-repo}"
REMOTE_NAME="${REMOTE_NAME:-origin}"
MAIN_BRANCH="main"
FEATURE_BRANCH="feature/add-user-auth"
RELEASE_TAG="v1.0.0"

# ── Colour helpers ─────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; RESET='\033[0m'

info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*" >&2; exit 1; }

# ── Parse CLI flags ────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --repo-path) REPO_PATH="$2"; shift 2 ;;
        --remote)    REMOTE_NAME="$2"; shift 2 ;;
        *) warn "Unknown flag: $1"; shift ;;
    esac
done

# =============================================================================
# STEP 1 — Initialise repository
# =============================================================================
step1_init_repo() {
    info "Step 1: Initialising repository at '${REPO_PATH}'"

    if [[ -d "${REPO_PATH}/.git" ]]; then
        warn "Repo already exists at '${REPO_PATH}' — skipping init."
    else
        mkdir -p "${REPO_PATH}"
        git -C "${REPO_PATH}" init --initial-branch="${MAIN_BRANCH}"
        success "Git repo initialised (branch: ${MAIN_BRANCH})"
    fi

    # Configure local identity (safe for demo — won't touch global config)
    git -C "${REPO_PATH}" config user.name  "Demo User"
    git -C "${REPO_PATH}" config user.email "demo@example.com"
}

# =============================================================================
# STEP 2 — Create .gitignore
# =============================================================================
step2_gitignore() {
    info "Step 2: Creating .gitignore"

    cat > "${REPO_PATH}/.gitignore" << 'EOF'
# ── Python ────────────────────────────────────────────────────────────────────
__pycache__/
*.py[cod]
*.pyo
*.pyd
.Python
env/
venv/
.venv/
*.egg-info/
dist/
build/
.pytest_cache/
.mypy_cache/
.ruff_cache/
htmlcov/
.coverage
coverage.xml

# ── Node / JS ─────────────────────────────────────────────────────────────────
node_modules/
npm-debug.log*
yarn-error.log
.pnp/
.pnp.js

# ── Environment & secrets ─────────────────────────────────────────────────────
.env
.env.*
!.env.example
*.pem
*.key
secrets.json

# ── IDE ───────────────────────────────────────────────────────────────────────
.vscode/
.idea/
*.swp
*.swo

# ── OS ────────────────────────────────────────────────────────────────────────
.DS_Store
Thumbs.db

# ── Terraform ─────────────────────────────────────────────────────────────────
.terraform/
*.tfstate
*.tfstate.backup
EOF

    git -C "${REPO_PATH}" add .gitignore
    git -C "${REPO_PATH}" commit -m "chore: add .gitignore for Python/Node/Terraform"
    success ".gitignore committed on ${MAIN_BRANCH}"
}

# =============================================================================
# STEP 3 — Initial project scaffold on main
# =============================================================================
step3_initial_commit() {
    info "Step 3: Creating initial project scaffold"

    mkdir -p "${REPO_PATH}/src" "${REPO_PATH}/tests"

    cat > "${REPO_PATH}/README.md" << 'EOF'
# Demo Project

A sample project to demonstrate the Git feature branch workflow.

## Getting Started

```bash
pip install -r requirements.txt
python src/app.py
```
EOF

    cat > "${REPO_PATH}/src/app.py" << 'EOF'
"""app.py — Entry point for the demo application."""


def main():
    print("Hello from the demo app!")


if __name__ == "__main__":
    main()
EOF

    cat > "${REPO_PATH}/requirements.txt" << 'EOF'
boto3==1.34.0
requests==2.31.0
EOF

    git -C "${REPO_PATH}" add .
    git -C "${REPO_PATH}" commit -m "feat: initial project scaffold"
    success "Initial scaffold committed on ${MAIN_BRANCH}"
}

# =============================================================================
# STEP 4 — Create feature branch
# =============================================================================
step4_create_feature_branch() {
    info "Step 4: Creating feature branch '${FEATURE_BRANCH}'"

    # Always branch off the latest main
    git -C "${REPO_PATH}" checkout -b "${FEATURE_BRANCH}" "${MAIN_BRANCH}"
    success "Switched to branch '${FEATURE_BRANCH}'"

    # ── Commit 1: add auth module ──────────────────────────────────────────────
    cat > "${REPO_PATH}/src/auth.py" << 'EOF'
"""
auth.py — Simple user authentication module.

In production, replace the in-memory store with a database lookup
and use a proper password hashing library (e.g., bcrypt).
"""

import hashlib
import secrets
from typing import Optional

# In-memory user store (demo only — use a DB in production)
_USERS: dict[str, str] = {}


def hash_password(password: str) -> str:
    """Return a salted SHA-256 hash of the password."""
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return f"{salt}:{hashed}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a plaintext password against a stored hash."""
    salt, hashed = stored_hash.split(":", 1)
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest() == hashed


def register_user(username: str, password: str) -> bool:
    """Register a new user. Returns False if username already exists."""
    if username in _USERS:
        return False
    _USERS[username] = hash_password(password)
    return True


def authenticate(username: str, password: str) -> Optional[str]:
    """Authenticate a user. Returns a session token or None."""
    stored = _USERS.get(username)
    if stored and verify_password(password, stored):
        return secrets.token_urlsafe(32)
    return None
EOF

    git -C "${REPO_PATH}" add src/auth.py
    # Conventional commit: feat(<scope>): <description>
    git -C "${REPO_PATH}" commit -m "feat(auth): add user registration and authentication module"

    # ── Commit 2: add tests ────────────────────────────────────────────────────
    cat > "${REPO_PATH}/tests/test_auth.py" << 'EOF'
"""test_auth.py — Unit tests for the auth module."""

import pytest
from src.auth import register_user, authenticate


def test_register_new_user():
    assert register_user("alice", "secret123") is True


def test_register_duplicate_user():
    register_user("bob", "pass")
    assert register_user("bob", "pass") is False


def test_authenticate_valid():
    register_user("carol", "mypassword")
    token = authenticate("carol", "mypassword")
    assert token is not None
    assert len(token) > 0


def test_authenticate_wrong_password():
    register_user("dave", "correct")
    assert authenticate("dave", "wrong") is None


def test_authenticate_unknown_user():
    assert authenticate("nobody", "pass") is None
EOF

    git -C "${REPO_PATH}" add tests/test_auth.py
    git -C "${REPO_PATH}" commit -m "test(auth): add unit tests for registration and authentication"

    # ── Commit 3: fix a bug ────────────────────────────────────────────────────
    # Simulate a small bug-fix commit on the feature branch
    sed -i 's/return f"{salt}:{hashed}"/return f"{salt}:{hashed}"  # format: salt:hash/' \
        "${REPO_PATH}/src/auth.py" 2>/dev/null || true

    git -C "${REPO_PATH}" add src/auth.py
    git -C "${REPO_PATH}" commit -m "fix(auth): clarify stored hash format in comment"

    success "Feature branch has 3 commits"
    git -C "${REPO_PATH}" log --oneline -5
}

# =============================================================================
# STEP 5 — Simulate PR review (diff + log)
# =============================================================================
step5_simulate_pr_review() {
    info "Step 5: Simulating PR review"

    echo ""
    echo "  ── Commits on feature branch (not yet on main) ──"
    git -C "${REPO_PATH}" log "${MAIN_BRANCH}..${FEATURE_BRANCH}" --oneline

    echo ""
    echo "  ── Files changed ──"
    git -C "${REPO_PATH}" diff --stat "${MAIN_BRANCH}..${FEATURE_BRANCH}"

    success "PR review simulation complete"
}

# =============================================================================
# STEP 6 — Merge strategies
# =============================================================================
step6_merge() {
    info "Step 6: Merging '${FEATURE_BRANCH}' into '${MAIN_BRANCH}'"

    git -C "${REPO_PATH}" checkout "${MAIN_BRANCH}"

    # Option A — Squash merge (recommended for clean history)
    # git -C "${REPO_PATH}" merge --squash "${FEATURE_BRANCH}"
    # git -C "${REPO_PATH}" commit -m "feat(auth): add user authentication (#1)"

    # Option B — Merge commit (preserves full feature history)
    git -C "${REPO_PATH}" merge --no-ff "${FEATURE_BRANCH}" \
        -m "feat(auth): merge user authentication feature (#1)"

    success "Feature branch merged into ${MAIN_BRANCH}"

    echo ""
    echo "  ── Full commit graph ──"
    git -C "${REPO_PATH}" log --oneline --graph --all -10
}

# =============================================================================
# STEP 7 — Tag a release
# =============================================================================
step7_tag_release() {
    info "Step 7: Tagging release ${RELEASE_TAG}"

    git -C "${REPO_PATH}" tag -a "${RELEASE_TAG}" \
        -m "Release ${RELEASE_TAG} — adds user authentication"

    success "Tag ${RELEASE_TAG} created"
    git -C "${REPO_PATH}" tag -l
}

# =============================================================================
# STEP 8 — Clean up merged branch
# =============================================================================
step8_cleanup() {
    info "Step 8: Cleaning up merged branch"

    git -C "${REPO_PATH}" branch -d "${FEATURE_BRANCH}"
    success "Branch '${FEATURE_BRANCH}' deleted (already merged)"

    echo ""
    echo "  ── Remaining branches ──"
    git -C "${REPO_PATH}" branch -a
}

# =============================================================================
# STEP 9 — Branch protection concepts (informational)
# =============================================================================
step9_branch_protection_info() {
    info "Step 9: Branch protection best practices (GitHub/GitLab)"

    cat << 'EOF'

  ── Branch Protection Rules (configure in GitHub → Settings → Branches) ──

  For 'main' branch:
    ✓ Require pull request reviews before merging (min 1 reviewer)
    ✓ Require status checks to pass (CI: lint, test, build)
    ✓ Require branches to be up to date before merging
    ✓ Restrict who can push to matching branches
    ✓ Require signed commits (optional but recommended)
    ✗ Allow force pushes — DISABLED
    ✗ Allow deletions — DISABLED

  ── Conventional Commits cheat sheet ──

    feat:     A new feature
    fix:      A bug fix
    docs:     Documentation only changes
    style:    Formatting, missing semicolons, etc.
    refactor: Code change that neither fixes a bug nor adds a feature
    test:     Adding or correcting tests
    chore:    Build process, dependency updates, tooling
    perf:     Performance improvement
    ci:       CI/CD configuration changes

  ── Branch naming conventions ──

    feature/<ticket-id>-short-description
    fix/<ticket-id>-short-description
    hotfix/<ticket-id>-short-description
    release/<version>
    chore/<description>

EOF
}

# =============================================================================
# Main
# =============================================================================
main() {
    echo ""
    echo "============================================================"
    echo "  Git Feature Branch Workflow Demo"
    echo "============================================================"

    step1_init_repo
    step2_gitignore
    step3_initial_commit
    step4_create_feature_branch
    step5_simulate_pr_review
    step6_merge
    step7_tag_release
    step8_cleanup
    step9_branch_protection_info

    echo ""
    echo "============================================================"
    echo "  Demo complete — repo is at: ${REPO_PATH}"
    echo "============================================================"
    echo ""
}

main "$@"
