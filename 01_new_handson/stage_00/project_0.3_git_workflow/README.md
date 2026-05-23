# Project 0.3 — Git & GitHub Workflow

## What This Does
Establishes the Git workflow and repository structure used for every project in this roadmap.

## Skills Covered
- Repository initialization and structure
- Branching strategy (feature branches)
- Conventional commit messages
- Pull request workflow
- GitHub Actions for Terraform validation
- .gitignore for AWS/Terraform projects

## Repository Structure
```
aws-handson-projects/
├── .github/
│   └── workflows/
│       └── validate.yml
├── .gitignore
├── README.md
├── stage_00/
│   ├── project_0.1_local_dev_setup/
│   ├── project_0.2_linux_lab/
│   └── ...
├── stage_01/
└── ...
```

## Branching Strategy
```
main          ← always deployable, protected
  └── feature/project-X.X-name   ← one branch per project
```

## Commit Convention
| Prefix | Use |
|--------|-----|
| `feat:` | New project or feature |
| `fix:` | Bug fix |
| `docs:` | Documentation only |
| `chore:` | Maintenance, cleanup |
| `refactor:` | Code restructure, no behavior change |

## How to Run
```bash
# Run the Git workflow demo script
chmod +x code/git_workflow_demo.sh
./code/git_workflow_demo.sh

# Or step through manually
git init my-project && cd my-project
git checkout -b feature/my-feature
git add . && git commit -m "feat: add initial implementation"
git push -u origin feature/my-feature
# Open PR on GitHub → review → merge
```

## Lessons Learned
- Never commit `.terraform/`, `*.tfstate`, or `*.pem` files
- One branch per project keeps history clean
- Conventional commits make the log readable at a glance

## Files
| File | Purpose |
|------|---------|
| `steps.md` | Phase-by-phase Git workflow: init, .gitignore, branches, GitHub, Actions |
| `verify.md` | Git config check, .gitignore effectiveness, branch/merge verification, GitHub Actions check |
| `cost_estimate.md` | Per-resource cost breakdown (Git/GitHub = free) |
| `code/git_workflow_demo.sh` | Shell script — demonstrates full feature branch workflow |
| `.gitignore` | Ignores Terraform state, AWS credentials, Python artifacts |
| `docs/architecture.md` | Workflow diagrams and notes |

## Code

### `code/git_workflow_demo.sh` — Git feature branch workflow

```bash
# Make executable
chmod +x code/git_workflow_demo.sh

# Run with defaults (creates ./demo-repo)
./code/git_workflow_demo.sh

# Run with custom repo path
./code/git_workflow_demo.sh --repo-path /tmp/my-demo-repo
```

What it does:
- Initialises a Git repo with `main` as the default branch
- Creates a `.gitignore` for Python/Node/Terraform
- Creates a feature branch `feature/add-user-auth`
- Makes 3 conventional commits (feat, test, fix)
- Simulates a PR review (diff + log)
- Merges with `--no-ff` and tags a `v1.0.0` release
- Cleans up the merged branch
