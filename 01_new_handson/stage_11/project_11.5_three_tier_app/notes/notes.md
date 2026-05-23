# Notes — Project 11.5

## RDS DB Subnet Group
When adding RDS, create a DB subnet group using db-private-a and db-private-b.
RDS requires subnets in at least 2 AZs even for single-AZ deployments.

```bash
aws rds create-db-subnet-group \
  --db-subnet-group-name db-subnet-group-11-5 \
  --db-subnet-group-description "DB subnets for project 11.5" \
  --subnet-ids <db-private-a-id> <db-private-b-id>
```

## Tagging Strategy
Tag every resource with:
- Name: descriptive name
- Project: 11.5
- Tier: web | app | db
- Environment: dev | staging | prod
