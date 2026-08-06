# Cost Estimate — Project 0.4: AWS Billing Setup

> **Total Estimated Cost: ~$0.00**  
> **AWS Free Tier Eligible: Mostly yes — see notes below**

---

## Service Cost Breakdown

| Service | Resource | Quantity | Unit Cost | Monthly Cost |
|---------|----------|----------|-----------|--------------|
| AWS Budgets | Budget (first 2 free) | 1–2 budgets | Free | $0.00 |
| AWS Budgets | Budget actions | 0 actions | $0.10/action/day | $0.00 |
| Amazon CloudWatch | Billing alarm | 1 alarm | Free (≤10) | $0.00 |
| Amazon SNS | Email notifications | ~5 emails | Free (≤1,000/month) | $0.00 |
| AWS Cost Explorer | Enabled (no API queries) | 0 queries | Free | $0.00 |
| AWS Cost Explorer | API queries (CLI) | ~10 queries | $0.01/request | ~$0.10 |
| IAM | Git credentials, policies | Included | Free | $0.00 |
| **Total** | | | | **~$0.00–$0.10** |

---

## Free Tier Details

### AWS Budgets

**Free tier:**
- **First 2 budget actions are free** each month
- Beyond 2 actions: **$0.10 per budget action per day**

**What counts as a "budget action":**
A budget action is an automated response to a threshold breach — for example, automatically stopping EC2 instances or applying an IAM policy when cost exceeds your budget. Simply receiving an email alert does **NOT** count as a budget action.

For this project, we only configure email alerts (not automated actions), so the cost is **$0.00**.

| Budget Feature | Cost |
|---------------|------|
| Creating a budget | Free |
| Email alert notification | Free |
| SNS notification | Free |
| Budget action (automated response) | $0.10/action/day after first 2 free |

### Amazon CloudWatch — Free Tier

- **10 alarms free** per month (includes billing alarms)
- Since we create 1 alarm, the cost is **$0.00**
- After 10 alarms: $0.10/alarm/month

### Amazon SNS — Free Tier

- **1,000 email notifications free** per month
- We will send maybe 5–10 emails in a month (if thresholds are triggered)
- Cost: **$0.00**

### AWS Cost Explorer

- **Enabling Cost Explorer:** Free
- **Using the console UI:** Free
- **API queries via CLI:** $0.01 per `GetCostAndUsage` request
- For ~10 test queries in this project: **~$0.10** (negligible)
- After learning phase: skip CLI queries unless needed

---

## Potential Cost After Free Tier Exhaustion

This only applies if you scale beyond the learning setup:

| Scenario | Service | Monthly Cost |
|----------|---------|-------------|
| 11+ CloudWatch alarms | CloudWatch | $0.10/alarm/month per alarm above 10 |
| 3+ budget actions | Budgets | $0.10/action/day |
| 1,001+ SNS emails | SNS | $2.00 per 100k emails |
| Many Cost Explorer API calls | Cost Explorer | $0.01 per request |

For solo learning: none of these thresholds will be reached.

---

## Important Note: The Budget Monitors YOUR Costs — It Is Not a Cost Itself

The purpose of this project is to set up billing alerts that protect you from unexpected charges in future projects. The monitoring infrastructure itself costs virtually nothing. Without it, a single forgotten EC2 instance could cost $8–$50/month.

**Cost-benefit calculation:**
```
Cost of this project's monitoring setup:  ~$0.00/month
Cost of one forgotten EC2 t2.micro:       ~$8.00/month (outside free tier)
Cost of one forgotten NAT Gateway:        ~$32.00/month
Cost of one forgotten RDS db.t3.micro:    ~$25.00/month

Setting up billing alerts:  PRICELESS (saves you from surprise bills)
```

---

## Cleanup

### Cleanup Cost Impact
All resources in this project are either free or cost negligible amounts. Cleaning up will save at most $0.10/month.

**Recommendation: Keep the budget and alarm running.** They protect you during all future projects.

### If You Want to Clean Up

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Delete budget
aws budgets delete-budget \
    --account-id $ACCOUNT_ID \
    --budget-name "monthly-learning-budget"

# Delete CloudWatch alarm (must be in us-east-1)
aws cloudwatch delete-alarms \
    --alarm-names "billing-over-5-dollars" \
    --region us-east-1

# Delete SNS topic
aws sns delete-topic \
    --topic-arn "arn:aws:sns:us-east-1:$ACCOUNT_ID:billing-alerts" \
    --region us-east-1
```

After cleanup:
```
AWS Budgets:     $0.00/month
CloudWatch:      $0.00/month
SNS:             $0.00/month
Cost Explorer:   $0.00/month
─────────────────────────────
Total:           $0.00/month
```

---

## Monthly Running Cost Summary

```
AWS Budgets (email alerts only):   $0.00/month
CloudWatch billing alarm (1):      $0.00/month
SNS email notifications:           $0.00/month
Cost Explorer (console use):       $0.00/month
Cost Explorer (CLI, ~10 queries):  ~$0.10 one-time
─────────────────────────────────────────────────
Total monthly:                     $0.00/month
One-time setup CLI cost:           ~$0.10
Annual projection:                 ~$0.00/year
```

**This is effectively a zero-cost foundational project.**

---

## What This Project Helps You Avoid

By setting up billing alerts now, you protect yourself from these common learning mistakes:

| Accidental Resource | Hourly Rate | Monthly if Forgotten |
|--------------------|-------------|---------------------|
| EC2 t2.micro (outside free tier) | $0.0116/hr | ~$8.50 |
| EC2 t3.small | $0.0208/hr | ~$15.00 |
| NAT Gateway (running) | $0.045/hr | ~$32.00 |
| RDS db.t3.micro | $0.017/hr | ~$12.50 |
| Elastic IP (unattached) | $0.005/hr | ~$3.60 |
| Application Load Balancer | $0.008/hr | ~$5.80 |

**The $5 budget alert catches all of these within the first few days.**

---

*End of cost_estimate.md — Project 0.4*
