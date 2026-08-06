# Cost Estimate — Project 2.2: 3-Tier AWS Application Architecture

> Region: us-east-1 | Estimates as of 2024 | All prices in USD
> Assumption: running 24/7 for a full month (730 hours)

---

## Free Tier Eligibility

AWS Free Tier (12 months from account creation) covers:

| Resource | Free Tier Allowance | Monthly Hours | Covered? |
|----------|--------------------|--------------:|---------|
| EC2 t2.micro (web-server) | 750 hrs/month | 730 hrs | ✅ Free |
| EC2 t2.micro (app-server) | 750 hrs/month combined | 730 hrs | ✅ Free (if only 1 instance) |
| RDS db.t3.micro | 750 hrs/month | 730 hrs | ✅ Free |
| RDS storage | 20 GB gp2 | — | ✅ Free |
| RDS backup | 20 GB | — | ✅ Free |
| Data transfer (outbound) | 100 GB/month | — | ✅ Free |

> ⚠️ **Note:** The 750 EC2 free tier hours are shared across ALL t2.micro instances in your account.
> Running both web-server and app-server simultaneously = 1,460 hrs/month — **exceeds the 750 hr limit**.
> The second EC2 will incur charges after the free hours are exhausted.

---

## Non-Free Components

These services are NOT covered by the Free Tier regardless of account age:

| Resource | Unit Price | Monthly Usage | Monthly Cost |
|----------|-----------|:-------------:|-------------:|
| ALB — fixed fee | $0.0225/hr | 730 hrs | $16.43 |
| ALB — LCU charge (est.) | $0.008/LCU-hr | ~100 LCU-hrs | ~$0.80 |
| **ALB Total** | | | **~$17.23** |
| 2nd EC2 t2.micro (after free hours) | $0.0116/hr | 730 hrs | **~$8.47** |
| RDS db.t3.micro (after free tier) | $0.017/hr | 730 hrs | **~$12.41** |
| RDS storage gp2 | $0.115/GB-month | 20 GB | $2.30 |

> ALB pricing note: LCU = Load Capacity Unit. 1 LCU supports 25 new connections/sec, 3,000 active connections, 1 GB/hr processed, 1,000 rule evaluations. Light dev traffic typically uses <1 LCU.

---

## Total Monthly Cost Scenarios

### Scenario A: Within Free Tier (best case)
Conditions: new AWS account (<12 months), running only ONE EC2, RDS in free tier

| Component | Cost |
|-----------|-----:|
| ALB (not free) | $17.23 |
| EC2 web-server (free tier) | $0.00 |
| EC2 app-server (free tier — if 1st instance) | $0.00 |
| RDS db.t3.micro (free tier) | $0.00 |
| RDS storage (free tier 20 GB) | $0.00 |
| Data transfer (within free tier) | $0.00 |
| **Total (Free Tier)** | **~$17–18/month** |

### Scenario B: Partial Free Tier
Conditions: free tier active, but running both EC2 instances simultaneously

| Component | Cost |
|-----------|-----:|
| ALB | $17.23 |
| Web EC2 (first 750 hrs free, rest charged) | ~$0.00 |
| App EC2 (exceeds free hours) | ~$8.47 |
| RDS (free tier) | $0.00 |
| **Total (Partial Free Tier)** | **~$26–28/month** |

### Scenario C: No Free Tier (after 12 months)
Conditions: free tier expired, full pricing applies

| Component | Cost |
|-----------|-----:|
| ALB | $17.23 |
| Web EC2 t2.micro | $8.47 |
| App EC2 t2.micro | $8.47 |
| RDS db.t3.micro | $12.41 |
| RDS storage 20 GB gp2 | $2.30 |
| Data transfer (light usage) | ~$1.00 |
| **Total (No Free Tier)** | **~$49–55/month** |

---

## Cost Optimization Tips

1. **Stop EC2 instances when not in use** — stopped instances don't incur compute charges (only EBS storage)
2. **Snapshot and delete RDS** during downtime — RDS charges even when stopped after 7 days (it auto-restarts)
3. **Delete ALB when not needed** — $17/month fixed cost even with zero traffic
4. **Use t3.micro instead of t2.micro** — better performance at similar or lower cost in some regions
5. **Enable RDS auto-stop** — in RDS settings, enable automatic stop after N days of inactivity
6. **Use Reserved Instances** — 1-year commitment reduces EC2+RDS costs by ~30%

---

## Hourly Cost Breakdown

Useful for estimating a 2-hour lab session:

| Resource | Hourly Rate | 2-Hour Session |
|----------|------------|---------------:|
| ALB | $0.0225 | $0.045 |
| EC2 t2.micro (×2) | $0.0116 × 2 | $0.046 |
| RDS db.t3.micro | $0.017 | $0.034 |
| **Total per 2-hour session** | | **~$0.13** |

> A typical hands-on session costs less than $0.20 if you clean up promptly.

---

## Cleanup

Run these commands immediately after finishing the hands-on exercise:

```bash
# 1. Delete ALB (stops $17/month fixed charge)
aws elbv2 delete-load-balancer --load-balancer-arn $ALB_ARN

# 2. Delete RDS (stops $12/month charge)
aws rds delete-db-instance \
  --db-instance-identifier handson-mysql \
  --skip-final-snapshot

# 3. Terminate EC2 instances (stops compute charges)
aws ec2 terminate-instances --instance-ids $WEB_INSTANCE $APP_INSTANCE

# 4. Verify no running charges remain
aws ec2 describe-instances \
  --filters "Name=instance-state-name,Values=running,pending,stopping" \
  --query 'Reservations[*].Instances[*].{ID:InstanceId,State:State.Name,Type:InstanceType}' \
  --output table

aws elbv2 describe-load-balancers \
  --query 'LoadBalancers[*].{Name:LoadBalancerName,State:State.Code}' \
  --output table

aws rds describe-db-instances \
  --query 'DBInstances[*].{ID:DBInstanceIdentifier,Status:DBInstanceStatus}' \
  --output table
```

**After cleanup, expected output:**
- EC2 instances: `terminated` or empty list
- Load Balancers: empty list
- RDS instances: `deleting` → then empty list

---

## Cost Monitoring Setup (Recommended)

Set up billing alerts before running this project:

1. Go to **AWS Billing → Budgets → Create budget**
2. Budget type: Cost budget
3. Amount: $20/month (covers ALB + one unexpected charge)
4. Alert at: 80% actual + 100% forecasted
5. Email: your email address

```bash
# CLI: create a $20 budget with email alert
aws budgets create-budget \
  --account-id $(aws sts get-caller-identity --query Account --output text) \
  --budget '{
    "BudgetName": "stage02-learning-budget",
    "BudgetLimit": {"Amount": "20", "Unit": "USD"},
    "TimeUnit": "MONTHLY",
    "BudgetType": "COST"
  }' \
  --notifications-with-subscribers '[{
    "Notification": {
      "NotificationType": "ACTUAL",
      "ComparisonOperator": "GREATER_THAN",
      "Threshold": 80,
      "ThresholdType": "PERCENTAGE"
    },
    "Subscribers": [{"SubscriptionType": "EMAIL", "Address": "your@email.com"}]
  }]'
```

---

*Cost estimate for Project 2.2 — Stage 02. Prices are approximate and subject to AWS pricing changes. Always verify current pricing at [aws.amazon.com/pricing](https://aws.amazon.com/pricing).*
