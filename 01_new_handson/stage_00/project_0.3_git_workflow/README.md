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

## Lessons Learned
- Never commit `.terraform/`, `*.tfstate`, or `*.pem` files
- One branch per project keeps history clean
- Conventional commits make the log readable at a glance
