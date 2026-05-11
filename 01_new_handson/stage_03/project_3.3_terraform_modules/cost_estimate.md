# Cost Estimate — Project 3.3 Terraform Modules & Environments

## Dev Environment
| Resource | Monthly Cost |
|----------|-------------|
| NAT Gateway | ~$32 |
| RDS db.t3.micro (no Multi-AZ) | $0 (free tier) |
| **Dev Total** | **~$32/month** |

## Prod Environment (if deployed)
| Resource | Monthly Cost |
|----------|-------------|
| NAT Gateway | ~$32 |
| RDS db.t3.small (Multi-AZ) | ~$50 |
| **Prod Total** | **~$82/month** |

## Notes
- Only deploy prod environment briefly to observe the difference
- Destroy both environments after the learning session
- The key learning here is the module pattern — not running both long-term
