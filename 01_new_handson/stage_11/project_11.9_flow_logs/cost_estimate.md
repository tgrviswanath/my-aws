# Cost Estimate — Project 11.9 VPC Flow Logs

| Resource | Usage | Monthly Cost |
|----------|-------|-------------|
| Flow Logs ingestion (CW) | ~100 MB | ~$0.05 |
| CloudWatch Log storage | ~100 MB | ~$0.03 |
| S3 storage | ~100 MB | ~$0.002 |
| EC2 t3.micro | ~2 hrs | ~$0.02 |
| **Total** | | **~$0.10** |

## Notes
- Flow logs charge per GB of log data published (~$0.50/GB to CloudWatch)
- For high-traffic VPCs, flow logs can be expensive — use subnet or ENI level instead of VPC level
- S3 storage is much cheaper than CloudWatch for long-term retention
- Use Parquet format for S3 — reduces storage and Athena query costs

## Teardown
```bash
terraform destroy
# Also delete S3 bucket contents and CloudWatch log group
```
