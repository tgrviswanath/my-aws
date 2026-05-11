# Cost Estimate — Project 9.3 Real-time Streaming Pipeline

| Resource | Monthly Cost |
|----------|-------------|
| Kinesis Data Stream (1 shard) | ~$10.80 |
| Lambda consumer | $0 (free tier) |
| DynamoDB aggregates | $0 (free tier) |
| SQS DLQ | $0 (free tier) |
| **Total** | **~$10.80/month** |

## Notes
- Kinesis: $0.015/shard-hour = $10.80/month for 1 shard — always running
- Delete stream when not using: `terraform destroy`
- For learning: use Kinesis for a few hours, then destroy
- Alternative: use SQS for simpler use cases (cheaper, no shard management)
