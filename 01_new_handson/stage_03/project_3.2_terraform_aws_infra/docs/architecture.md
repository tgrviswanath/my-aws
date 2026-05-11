# Architecture — Project 3.2 Terraform AWS Infrastructure

## File Structure

```
terraform/
├── versions.tf   ← required_providers, required_version
├── variables.tf  ← all variable declarations
├── locals.tf     ← name_prefix, common_tags
├── vpc.tf        ← VPC, subnets, IGW, NAT, route tables
├── ec2.tf        ← security groups, ALB, launch template, ASG
├── rds.tf        ← DB subnet group, RDS instance
├── outputs.tf    ← all outputs
└── terraform.tfvars ← variable values (gitignored for passwords)
```

## Resource Dependency Graph

```
aws_vpc.main
  ├── aws_subnet.public[0,1]
  │     └── aws_internet_gateway.main
  │           └── aws_eip.nat
  │                 └── aws_nat_gateway.main
  │                       └── aws_route_table.private
  │                             └── aws_route_table_association.private_app[0,1]
  │                             └── aws_route_table_association.private_db[0,1]
  │
  ├── aws_security_group.alb
  │     └── aws_lb.app
  │           └── aws_lb_target_group.app
  │                 └── aws_lb_listener.http
  │
  ├── aws_security_group.app
  │     └── aws_launch_template.app
  │           └── aws_autoscaling_group.app ──► aws_lb_target_group.app
  │
  └── aws_security_group.rds
        └── aws_db_subnet_group.main
              └── aws_db_instance.mysql
```

## Terraform State

```
After apply, terraform.tfstate contains:
- 20+ resources tracked
- All IDs, ARNs, endpoints stored
- Used for future plan/apply/destroy operations

Never delete terraform.tfstate manually.
Use remote state (Project 3.4) for team environments.
```
