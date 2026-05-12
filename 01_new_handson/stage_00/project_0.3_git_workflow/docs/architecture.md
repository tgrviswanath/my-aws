# Architecture — Project 0.3 Git & GitHub Workflow

## Repository Structure

```
aws-handson-projects/
├── .github/
│   ├── workflows/
│   │   └── terraform-validate.yml
│   └── pull_request_template.md
├── .gitignore
├── README.md
├── stage_00/
│   ├── project_0.1_local_dev_setup/
│   ├── project_0.2_linux_lab/
│   └── ...
├── stage_01/ ... stage_10/
```

## Branch Strategy

```
main (protected — always deployable)
  └── feature/project-X.X-name
        └── PR → review → merge to main
```

## Commit Convention

```
feat:     new project or feature
fix:      bug fix
docs:     documentation only
chore:    maintenance, cleanup
refactor: restructure, no behavior change
```

## GitHub Actions Validation Flow

```
Pull Request opened
    │
    ▼
.github/workflows/terraform-validate.yml
    │
    ├── terraform fmt -check    ← fail if not formatted
    ├── terraform init          ← download providers
    └── terraform validate      ← check syntax
    │
    ▼
PR checks pass → reviewer approves → merge to main
```
