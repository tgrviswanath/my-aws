# Cost Estimate — Project 3.2 Terraform AWS Infrastructure

| Resource | Monthly Cost |
|----------|-------------|
| NAT Gateway | ~$32.40 |
| ALB | ~$16–18 |
| EC2 t3.micro x2 | $0 (free tier) or ~$15 |
| RDS db.t3.micro | $0 (free tier) or ~$13 |
| EBS 20 GB | $0 (free tier) |
| **Total** | **~$50–80/month** |

## ⚠️ Always Destroy After Learning
```bash
terraform destroy -var-file="terraform.tfvars" -var="db_password=yourpassword"
```
NAT Gateway alone costs ~$1/day. Destroy after each session.
