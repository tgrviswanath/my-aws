# Project 10.3 — Cost Optimization: Console UI Steps
## Visual Walkthrough for AWS Management Console

---

## Prerequisites Check

- [ ] AWS Support: Business or Enterprise for full Trusted Advisor
- [ ] At least 30+ hours of EC2/Lambda/Fargate usage for Compute Optimizer
- [ ] IAM permissions: `ce:*`, `compute-optimizer:*`, `trustedadvisor:*`
- [ ] Region: Cost Explorer and Trusted Advisor are global

---

## Step 1 — Trusted Advisor Cost Checks

1. Search for **Trusted Advisor** in the console
2. Click **Trusted Advisor**
3. If on Basic support: you see 7 checks (limited)
4. Click **Cost Optimization** tab
5. Key checks to review:
   - **Low Utilization Amazon EC2 Instances** (< 10% CPU, 0 network I/O)
   - **Idle RDS DB Instances** (0 connections for 7 days)
   - **Underutilized Amazon EBS Volumes** (< 1 IOPS/day)
   - **Unassociated Elastic IP Addresses** ($3.65/month each)
   - **Amazon EC2 Reserved Instance Optimization**
6. Click on any check to see flagged resources + estimated savings

📸 Screenshot: Trusted Advisor Cost Optimization tab with multiple flagged checks

---

## Step 2 — Enable Compute Optimizer

1. Search for **Compute Optimizer** in the console
2. Click **AWS Compute Optimizer**
3. Click **Opt in to Compute Optimizer**
4. Select: **Opt in account** (or **opt in organization** if using Organizations)
5. Click **Opt in**
6. Wait 24-48 hours for initial analysis
7. Return to see recommendations populated

📸 Screenshot: Compute Optimizer opt-in page with organization option

---

## Step 3 — View EC2 Resize Recommendations

1. In **Compute Optimizer** → **EC2 instances**
2. For each instance:
   - **Current type**: What you're running
   - **Finding**: Over-provisioned, Under-provisioned, Optimized
   - **Recommended type**: What CO suggests (usually smaller = cheaper)
   - **Estimated monthly savings**: Dollar amount
3. Click on an instance to see:
   - CPU and memory utilization graphs
   - Multiple recommendation options with confidence scores
4. Apply recommendation: Go to EC2 → Instances → select instance → **Actions** → **Instance settings** → **Change instance type**

📸 Screenshot: EC2 recommendation showing current vs recommended type with savings estimate

**Decision Point: When to follow Compute Optimizer?**
- Confidence score > 90%: Strongly consider
- "Over-provisioned" with < 40% CPU: Clear action
- Production databases: Test during maintenance window

---

## Step 4 — Launch Spot Instances for Dev

1. Navigate to **EC2** → **Spot Requests**
2. Click **Request Spot Instances**
3. Configure:
   - **AMI**: Amazon Linux 2023
   - **Instance type**: t3.medium (or let EC2 select)
   - **Fleet type**: Maintain target capacity
   - **Target capacity**: 2 instances
   - **Allocation strategy**: Capacity-optimized (reduces interruptions)
4. Under **Additional launch parameters**:
   - **Interruption behavior**: Stop (can resume later)
5. **Diversification**: Add multiple instance types (t3.medium, t3a.medium, m5.large)
6. Click **Launch**

📸 Screenshot: Spot request configuration with multiple instance types for diversification

---

## Step 5 — View Savings Plans Recommendations

1. Navigate to **AWS Cost Management** → **Savings Plans**
2. Click **Recommendations** tab
3. Compute Savings Plan recommendations show:
   - **Recommended hourly commitment**: $X/hour
   - **Estimated monthly savings**: $Y
   - **Coverage after purchase**: Z%
4. Review for **1-year** and **3-year** terms
5. Review payment options: No Upfront, Partial Upfront, All Upfront

📸 Screenshot: Savings Plans recommendation with hourly commitment and estimated savings

---

## Step 6 — Purchase a Savings Plan

1. From the Recommendations page, click **Add to cart** on a recommended plan
2. Review in cart:
   - Type: Compute Savings Plans (most flexible)
   - Commitment: $X/hour
   - Term: 1 year
   - Payment: No Upfront
3. Click **Review and purchase**
4. Confirm the commitment (cannot cancel after purchase)
5. Savings apply immediately to eligible usage

📸 Screenshot: Savings Plans purchase confirmation page

**Decision Point: No Upfront vs All Upfront?**
- **No Upfront**: No cash required, 20-30% savings, pay monthly
- **Partial Upfront**: Pay half now, slightly higher savings
- **All Upfront**: Maximum savings (66%), pay full year now
- Recommendation: No Upfront if cash flow matters; All Upfront if you have the capital

---

## Step 7 — Set Up Auto-Stop with EventBridge

1. Navigate to **AWS Lambda** → **Create function**
2. **Author from scratch**:
   - Name: `auto-stop-idle-ec2`
   - Runtime: Python 3.11
3. Paste the Lambda code from GUIDE.md section 6
4. **Configuration** → **Environment variables**:
   - `CPU_THRESHOLD`: `5.0`
   - `IDLE_MINUTES`: `30`
   - `TAG_KEY`: `AutoStop`
   - `TAG_VALUE`: `true`
5. Save and deploy

**Add EventBridge trigger:**
1. Lambda → **+ Add trigger**
2. **EventBridge (CloudWatch Events)**
3. **Create a new rule**:
   - Rule name: `auto-stop-idle-ec2-schedule`
   - Rule type: Schedule expression
   - Expression: `rate(15 minutes)`
4. Click **Add**

📸 Screenshot: Lambda function with EventBridge trigger added showing rate(15 minutes)

---

## Step 8 — Cost Explorer Analysis

1. Navigate to **AWS Cost Management** → **Cost Explorer**
2. **Enable Cost Explorer** if first time
3. Default view shows monthly costs by service
4. Useful filters and groupings:
   - Group by: **Service** → see which services cost most
   - Group by: **Instance type** → see EC2 type distribution
   - Group by: **Tag** → see per-project costs
5. **Hourly and Resource Level Data**: Enable for more granular analysis
6. Save report as CSV or schedule email delivery

📸 Screenshot: Cost Explorer with service breakdown bar chart showing top spending services

---

## Step 9 — Create Budget and Cost Anomaly Alert

1. Navigate to **AWS Budgets** → **Create budget**
2. Select **Cost budget**
3. Configure:
   - **Budget name**: `monthly-spend-limit`
   - **Period**: Monthly
   - **Budget amount**: $200
4. **Configure alerts**:
   - **Alert threshold**: 80% of budget ($160)
   - **Email**: your-email@example.com
   - **SNS**: optional
5. Click **Create budget**

**Cost Anomaly Detection:**
1. Navigate to **Cost Management** → **Cost Anomaly Detection**
2. Click **Create monitor** → Monitor type: AWS services
3. Create subscription:
   - Alert frequency: Daily
   - Threshold: 20% above baseline
   - Notification: Email

📸 Screenshot: Budget creation form with 80% alert threshold

---

## Step 10 — Review Savings Summary Dashboard

1. Navigate to **Savings Plans** → **Inventory**
2. See applied Savings Plans and coverage percentage
3. Navigate to **Compute Optimizer** → **Dashboard**
4. Summary shows:
   - Total estimated monthly savings available
   - % of resources optimized
5. Navigate to **Trusted Advisor** → **Estimated Monthly Savings**
6. Review total potential savings across all checks

📸 Screenshot: Compute Optimizer dashboard showing total estimated savings across all resource types

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Trusted Advisor full checks locked | Basic support plan | Upgrade to Business/Enterprise support |
| Compute Optimizer shows no data | Just opted in | Wait 24-48 hours for ML analysis |
| Auto-stop not working | Lambda missing EC2 permissions | Add `ec2:StopInstances`, `cloudwatch:GetMetricStatistics` to role |
| Savings Plans recommendation is $0 | Too little usage | Need steady On-Demand spend to generate recommendation |
| Spot interruption causing service disruption | Single instance type | Use multiple types + diversified subnets |

---

## Console Navigation Quick Reference

```
AWS Console
├── Trusted Advisor
│   └── Cost Optimization tab → Idle/underutilized resources
├── Compute Optimizer
│   ├── EC2 instances         → Right-size recommendations
│   ├── Lambda functions      → Memory optimization
│   └── ECS services          → CPU/memory recommendations
├── Cost Management
│   ├── Cost Explorer         → Spend analysis and trends
│   ├── Budgets               → Spend alerts
│   ├── Savings Plans         → Purchase commitments
│   └── Cost Anomaly Detection → Unusual spending alerts
└── EC2
    ├── Spot Requests         → Launch spot instances
    └── Fleet Requests        → Manage spot fleets
```
