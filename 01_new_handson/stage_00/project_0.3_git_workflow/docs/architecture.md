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

## Input / Output

### Input
| Type | Description | Example |
|------|-------------|---------|
| AWS Account | Active subscription | IAM user with required permissions |
| Configuration | Service settings | CIDR blocks, instance types, regions |
| Source Data | Application or data files | Docker images, SQL scripts, CSV files |

### Output
| Type | Description | Access |
|------|-------------|--------|
| AWS Resources | Deployed infrastructure | AWS Console or CLI |
| Service Endpoints | HTTP/HTTPS URLs, connection strings | Resource overview |
| CloudWatch Logs | Execution and audit trail | CloudWatch Log groups |
| Metrics | Performance data | CloudWatch Metrics |

## Key Concepts
| Concept | Explanation |
|---------|-------------|
| IAM Role | AWS identity for services â€” no static credentials |
| Security Group | Virtual firewall for EC2/RDS â€” stateful |
| VPC | Isolated network â€” your private AWS cloud |
| Region | Geographic AWS datacenter location |
| Availability Zone | Isolated datacenters within a region |
| CloudWatch | AWS monitoring and logging service |
| Free Tier | AWS free usage limits per service per month |
