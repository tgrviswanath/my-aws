# Cost Estimate — Project 9.7 Data Quality Validation

> **Great Expectations Core is 100% free and open source.**
> AWS costs are near-zero at learning scale.

---

## Tool Costs

| Tool | Cost | Notes |
|------|------|-------|
| Great Expectations Core | **$0** | Open source, local/Lambda |
| Great Expectations Cloud | $200+/month | Managed platform — skip for learning |

---

## AWS Resource Costs

| Resource | Free Tier | Cost After Free Tier | This Project |
|----------|-----------|---------------------|-------------|
| Lambda | ✅ 1M invocations/month | $0.20/M after | ~1 invoke/day = **$0** |
| Lambda compute | ✅ 400K GB-sec/month | $0.0000166/GB-s | 512MB×300s×30runs = 4,608 GB-s = **$0** (within free tier) |
| SNS publishes | ✅ 1M/month | $0.50/M after | ~30/month = **$0** |
| SNS email delivery | ✅ 1,000/month | $2/100K after | ~30/month = **$0** |
| EventBridge custom events | ✅ 5M/month | $1/M after | ~30/month = **$0** |
| S3 (reports + quarantine) | ✅ 5 GB/month | $0.023/GB | < 1 MB/month = **~$0.00** |
| CloudWatch Logs (5 GB) | ✅ 5 GB/month | $0.50/GB after | < 1 MB/month = **$0** |

**Total: ~$0.01/month** (S3 storage only)

---

## Scale Estimates

| Scenario | Runs/Month | Lambda GB-sec | Monthly Cost |
|----------|-----------|--------------|-------------|
| Learning (1/day) | 30 | 4,608 | **$0** (free tier) |
| Small team (10/day) | 300 | 46,080 | **$0** (free tier) |
| Production (100/day) | 3,000 | 460,800 | **~$1.00** |
| Heavy (1,000/day) | 30,000 | 4,608,000 | **~$68** |

---

## Alternatives Comparison

| Option | Cost | Effort | Use When |
|--------|------|--------|---------|
| Great Expectations (this project) | ~$0 | Low | Python pipelines, rich reports |
| dbt tests | ~$0 | Very low | Already using dbt |
| AWS Deequ (EMR) | ~$0.07/run | Medium | EMR/Glue at petabyte scale |
| Monte Carlo (SaaS) | $1,000+/month | Low | Enterprise data observability |

---

## Cleanup to Stop All Costs

```powershell
aws lambda delete-function --function-name handson-data-quality-check
aws sns delete-topic --topic-arn $TOPIC_ARN
aws events delete-rule --name handson-glue-job-success
aws s3 rm s3://BUCKET/data-quality/ --recursive
aws s3 rm s3://BUCKET/quarantine/ --recursive
```

After cleanup: **$0.00/month**.
