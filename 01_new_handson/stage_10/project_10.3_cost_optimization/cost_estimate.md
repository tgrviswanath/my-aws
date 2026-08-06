# Cost Estimate — Project 10.3: Cost Optimization Tools

## Pricing for the Optimization Tools Themselves

| Tool | Cost | Notes |
|------|------|-------|
| Trusted Advisor (basic) | Free | 7 checks only |
| Trusted Advisor (full) | Included with Business/Enterprise support | $100/month min for Business |
| Compute Optimizer | **Free** | No charge for the service |
| Cost Explorer | Free basic | $0.01/record for hourly+resource-level data |
| Savings Plans | 0 overhead | Pay normal rates, just discounted |
| Spot instances | 60-90% less than On-Demand | Depends on instance type + AZ |
| AWS Budgets | Free (first 2 budgets) | $0.02/budget/day after |

---

## Free Tier

- **Compute Optimizer**: Always free
- **Cost Explorer**: Basic monthly view free; $0.01/record for hourly granularity
- **Budgets**: First 2 budgets free; then $0.02/budget/day (~$0.60/month)
- **Trusted Advisor**: Free 7 core checks (no Business/Enterprise needed)

---

## Potential Savings from Each Tool

### Trusted Advisor Typical Findings
| Finding | Typical Waste | Action |
|---------|--------------|--------|
| Idle EC2 (< 2% CPU) | $15-100/instance/month | Stop or terminate |
| Idle RDS (0 connections) | $25-200/instance/month | Stop or downsize |
| Unattached EBS volumes | $5-50/volume/month | Delete |
| Unused Elastic IPs | $3.65/IP/month | Release |
| Over-provisioned EC2 | 20-60% of instance cost | Right-size |

### Compute Optimizer Savings
| Resource | Average Savings |
|---------|----------------|
| Over-provisioned EC2 | 20-40% per instance |
| Lambda memory | 10-30% per function |
| ECS task CPU/memory | 15-25% per service |

### Spot Instance Savings
| Instance Use Case | Savings |
|-----------------|---------|
| Dev/test servers | 60-80% vs On-Demand |
| Batch processing | 70-90% |
| CI/CD workers | 65-80% |

### Savings Plans Savings
| Plan Type | Savings | Flexibility |
|-----------|---------|-------------|
| Compute Savings Plans | 66% | EC2, Fargate, Lambda — any region, type |
| EC2 Instance Savings Plans | 72% | Same family + region only |
| RDS Reserved Instances | 30-60% | Same class + engine + region |

---

## ROI Calculation Example

**Starting costs (before optimization): $1,000/month**

| Optimization | Monthly Savings | Action |
|-------------|----------------|--------|
| Stop 3 idle EC2 instances | $150 | Trusted Advisor finding |
| Right-size 5 instances (Compute Optimizer) | $200 | Downsize m5.2xlarge → m5.large |
| Delete 20 unattached EBS volumes | $50 | Trusted Advisor finding |
| Spot for dev workloads (10 instances) | $300 | 70% discount on dev fleet |
| 1-year Compute Savings Plan | $200 | 66% on committed usage |
| Auto-stop (saves 14 hrs/day on dev) | $100 | Lambda + EventBridge |
| **Total Savings** | **$1,000** | **100% cost reduction!** |

**Net result: $0/month** (in this optimistic example — real savings typically 30-60%)

---

## Tool-Specific Costs for This Project

| Item | One-Time | Monthly |
|------|---------|---------|
| Lambda (auto-stop, runs 4× per hour) | $0 | $0.01 |
| EventBridge rule | $0 | $0 (within free tier) |
| Cost Anomaly Detection | $0 | $0 |
| Compute Optimizer | $0 | $0 |
| Budget alerts | $0 | $0 (within 2 free budgets) |
| **Total for optimization tools** | **$0** | **~$0.01** |

---

## Total

| Phase | Cost |
|-------|------|
| Tools setup | **~$0** |
| Ongoing monitoring tools | **~$0.01/month** |
| Savings generated | **$200-1,000+/month** (varies) |

**ROI: Essentially infinite — tools are free, savings are real.**

---

## Cleanup

```bash
# Delete auto-stop Lambda
aws events remove-targets --rule "auto-stop-idle-ec2-schedule" --ids "1"
aws events delete-rule --name "auto-stop-idle-ec2-schedule"
aws lambda delete-function --function-name auto-stop-idle-ec2

# Delete cost anomaly monitor
MONITOR_ARN=$(aws ce list-cost-allocation-tags \
  --query '...' --output text)  # Get your monitor ARN
aws ce delete-anomaly-monitor --monitor-arn $MONITOR_ARN

# Cancel Spot Fleet (terminate running instances)
aws ec2 cancel-spot-fleet-requests \
  --spot-fleet-request-ids $FLEET_ID \
  --terminate-instances

# Delete SNS topics
aws sns delete-topic --topic-arn $SNS_ARN

# Delete Budgets
BUDGET_NAME="monthly-spend-limit"
aws budgets delete-budget \
  --account-id $ACCOUNT_ID \
  --budget-name $BUDGET_NAME

echo "Cleanup complete"
echo "WARNING: Cannot cancel existing Savings Plans — they run until expiry"
echo "Compute Optimizer and Cost Explorer data retained for 90 days (free)"
```

**Note on Savings Plans:** Once purchased, they cannot be cancelled. The commitment runs until the end of the term (1 or 3 years). They will continue to provide savings even without active management.
