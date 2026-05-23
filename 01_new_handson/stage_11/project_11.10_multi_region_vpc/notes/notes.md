# Notes — Project 11.10

## Key Difference from Same-Region Peering
- Must specify `--peer-region` in CLI / `peer_region` in Terraform
- Accepter must be in the other region — `auto_accept` only works same-account same-region
- Use `aws_vpc_peering_connection_accepter` resource in Terraform for cross-region

## Terraform Multi-Region Pattern
Use provider aliases:
```hcl
provider "aws" { alias = "east"; region = "us-east-1" }
provider "aws" { alias = "west"; region = "us-west-2" }
resource "aws_vpc" "east" { provider = aws.east; ... }
resource "aws_vpc" "west" { provider = aws.west; ... }
```

## Common Mistake
Forgetting to accept the peering in the other region.
The peering stays in "pending-acceptance" state until accepted.
