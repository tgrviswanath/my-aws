# AWS Console UI Steps — Project 0.4: AWS Billing Setup

> **Purpose:** Step-by-step console walkthrough for Billing, Budgets, and CloudWatch alarms  
> **Time:** 20–30 minutes  
> **Cost:** ~$0 (first 2 budget actions free)

---

## Prerequisites Check

Before starting:
- [ ] Logged in to AWS Console (root user or IAM user with billing access enabled)
- [ ] Email address accessible — you will need to confirm an SNS subscription
- [ ] AWS CLI configured (for CLI verification steps at the end)
- [ ] Completed Project 0.1 — you know how to navigate the console

> **Root vs IAM for Billing:** By default, only root can see billing. If using IAM user, root must enable "IAM user and role access to Billing information" first. See Section 3 in GUIDE.md.

---

## Step 1 — Access the Billing Console

### Navigate to Billing

1. Log in to https://console.aws.amazon.com
2. Click your **account name** in the top-right corner (shows your account alias or ID)
3. In the dropdown, click **Billing and Cost Management**

   **Alternative path:** Search bar → type "Billing" → click "Billing and Cost Management"

   **📸 Screenshot:** Capture the account dropdown showing "Billing and Cost Management" option

4. You arrive at the **Billing Dashboard**

### Explore the Billing Dashboard

5. The dashboard shows:
   - **Month-to-date spend:** Likely $0.00 for new accounts
   - **Last month's total**
   - **Service charges:** Breakdown by AWS service
   - **Free Tier usage summary**
   - **Cost Explorer link**

   **📸 Screenshot:** Capture the full Billing Dashboard

### Decision Point 1: AWS Budgets vs CloudWatch Billing Alarm

| Tool | Primary Use | Forecast Alerts | Per-Service Alerts | Cost |
|------|------------|-----------------|-------------------|------|
| ✅ **AWS Budgets** | Monthly cost guardrail | Yes | Yes | First 2 free |
| **CloudWatch Billing Alarm** | Real-time cost spike detection | No | No | Free (≤10 alarms) |

> **Decision: Create an AWS Budget as primary alerting.** Create a CloudWatch alarm as secondary/backup.

### Troubleshooting — Step 1

| Problem | Solution |
|---------|----------|
| "You don't have access to billing" | Root must enable IAM billing access in Account settings |
| Page shows only "Billing" with limited info | Your IAM user lacks billing permissions — use root |
| Dashboard looks different from screenshots | AWS updates the console regularly; layout may vary |

---

## Step 2 — Enable Cost Explorer

### Activate Cost Explorer

1. In the left sidebar, click **Cost Explorer**
2. If not yet enabled, you see a banner:
   > "AWS Cost Explorer helps you visualize and manage your AWS costs and usage over time."
3. Click **Enable Cost Explorer**
4. A confirmation dialog appears — click **Enable Cost Explorer** again

   **📸 Screenshot:** Capture the activation confirmation message

> **Note:** Cost Explorer takes up to 24 hours to populate historical data for the first time. For new accounts with no charges, the charts may show empty or $0.00 data — this is normal.

### Explore the Cost Explorer UI

5. Once enabled, the main Cost Explorer chart appears:
   - X-axis: Time (daily or monthly)
   - Y-axis: Cost (USD)
   - Color-coded by service

6. Try these filters:
   - **Granularity:** Switch between Monthly, Daily
   - **Group by:** Try "Service" to see cost by service
   - **Date range:** Last 3 months, last 6 months

   **📸 Screenshot:** Capture the Cost Explorer chart (even if showing $0.00)

### Decision Point 2: Cost Explorer Data Granularity

| Granularity | Use When |
|-------------|----------|
| **Monthly** | Overview, budget tracking |
| **Daily** | Investigating a spike or unexpected charge |
| **Hourly** | Deep debugging of a specific service (costs more to query) |

---

## Step 3 — Create an AWS Budget

### Start Budget Creation

1. In the left sidebar, click **Budgets**
2. If first time, you see the Budgets overview page
3. Click **Create budget**

### Choose Budget Type

4. You see four budget types:
   - ✅ **Cost budget** — Alert on monthly cost
   - Usage budget — Alert on specific service usage
   - Savings Plans budget — Track Savings Plans
   - Reservation budget — Track Reserved Instances

5. Select **Cost budget — Recommended**
6. Click **Next**

### Configure the Budget

7. Fill in budget details:

   | Field | Value |
   |-------|-------|
   | Budget name | `monthly-learning-budget` |
   | Period | Monthly |
   | Budget renewal type | Recurring budget |
   | Start month | Current month |
   | Budgeted amount | `5.00` |

8. Leave the rest as defaults (you can add service filters in advanced mode)
9. Click **Next**

   **📸 Screenshot:** Capture the budget configuration form before clicking Next

### Configure Alert Thresholds

10. Click **Add alert threshold** (you start with one; add a second)

    **First Alert (80% warning):**
    | Field | Value |
    |-------|-------|
    | Threshold | `80` |
    | Threshold type | % of budgeted amount |
    | Trigger | Actual (not forecasted) |
    | Email recipients | `your-email@example.com` |

11. Click **Add alert threshold** again

    **Second Alert (100% exceeded):**
    | Field | Value |
    |-------|-------|
    | Threshold | `100` |
    | Threshold type | % of budgeted amount |
    | Trigger | Actual |
    | Email recipients | `your-email@example.com` |

12. Click **Next**

### Review and Create

13. Review the budget summary:
    ```
    Name:           monthly-learning-budget
    Amount:         $5.00 (USD)
    Period:         Monthly (Recurring)
    Alert 1:        80% actual ($4.00) → email
    Alert 2:        100% actual ($5.00) → email
    ```
14. Click **Create budget**

    **📸 Screenshot:** Capture the success page showing the new budget in the Budgets list

### Expected Outcome — Step 3

The Budgets list shows:
```
monthly-learning-budget    $0.00 / $5.00    0%    No alerts triggered
```

### Troubleshooting — Step 3

| Problem | Solution |
|---------|----------|
| "Budget limit exceeded immediately" | Your account has charges from current month |
| Email not received | Check spam folder; confirm SNS if prompted |
| Can't add second alert | Each budget supports up to 5 alert thresholds |
| "Budget actions" option visible but not used | Budget Actions trigger automated responses (stop EC2, etc.) — skip for now |

---

## Step 4 — Create a CloudWatch Billing Alarm

### Switch Region to us-east-1

> **Critical:** Billing metrics in CloudWatch only exist in us-east-1 (US East N. Virginia).

1. Click the region dropdown (top-right, next to your account name)
2. Select **US East (N. Virginia) — us-east-1**

### Navigate to CloudWatch

3. Search bar → type `CloudWatch` → click **CloudWatch**
4. In the left sidebar, click **Alarms** → **All alarms**
5. Click **Create alarm**

### Select the Billing Metric

6. Click **Select metric**
7. In the "Browse" tab, scroll to find **Billing** (it's a standalone category)
8. Click **Billing**
9. Click **Total Estimated Charge**
10. You see a single metric: `EstimatedCharges` with `Currency: USD`
11. Check the checkbox next to it
12. Click **Select metric**

   **📸 Screenshot:** Capture the metric selection screen showing EstimatedCharges

### Configure the Alarm

13. On the "Specify metric and conditions" page:

    | Setting | Value |
    |---------|-------|
    | Statistic | Maximum |
    | Period | 6 hours |
    | Threshold type | Static |
    | Alarm condition | Greater than |
    | Threshold value | `5` |

14. Click **Next**

### Configure Notification

15. **Alarm state trigger:** In alarm
16. Click **Create new SNS topic**
17. Topic name: `billing-alerts`
18. Email endpoints: `your-email@example.com`
19. Click **Create topic**

    **📸 Screenshot:** Capture the SNS topic creation in the notification step

20. Click **Next**

### Name the Alarm

21. Alarm name: `billing-over-5-dollars`
22. Description: `Alert when estimated monthly charges exceed $5 USD`
23. Click **Next** → Review → **Create alarm**

### Confirm the SNS Subscription

24. Check your email inbox — you should receive:
    ```
    Subject: AWS Notification - Subscription Confirmation
    From: no-reply@sns.amazonaws.com
    ```
25. Open the email and click the **Confirm subscription** link
26. A browser page confirms: "Subscription confirmed!"

    **📸 Screenshot:** Capture the CloudWatch alarm in "OK" state (green dot)

### Expected Outcome — Step 4

CloudWatch Alarms list shows:
```
billing-over-5-dollars    OK    In-alarm when EstimatedCharges > 5
```

### Troubleshooting — Step 4

| Problem | Solution |
|---------|----------|
| "Billing" not visible in CloudWatch metrics | Must be in us-east-1 region; also, billing metrics need 6–24 hrs to appear |
| Alarm immediately in "INSUFFICIENT_DATA" state | Normal for new accounts — no data yet; it will show OK once metric appears |
| Confirmation email not received | Check spam; re-subscribe via SNS console if needed |
| "Create new SNS topic" option missing | Select "Use existing SNS topic" and choose `billing-alerts` if it already exists |

---

## Step 5 — Review Free Tier Usage

### Navigate to Free Tier

1. In Billing console → left sidebar → click **Free Tier**
2. The Free Tier dashboard shows:

   | Column | Meaning |
   |--------|---------|
   | Service | AWS service name |
   | Type | Always free / 12 months free / Trial |
   | Monthly usage limit | The free tier cap |
   | Current usage | What you've used this month |
   | Forecasted usage | Expected usage by end of month |

   **📸 Screenshot:** Capture the Free Tier usage table

3. All rows should show 0 or very low usage for a new account

### Enable Free Tier Email Alerts

4. In left sidebar → **Billing preferences**
5. Under "Alert preferences":
   - Check: ✅ **Receive AWS Free Tier Usage Alerts**
   - Email: `your-email@example.com`
6. Under "Invoice delivery preferences":
   - Check: ✅ **PDF invoices delivered by email**
7. Click **Update**

   **📸 Screenshot:** Capture the Billing Preferences page with alerts enabled

---

## Step 6 — Verify Everything in the Console

### Budget Verification

1. Billing → Budgets — confirm `monthly-learning-budget` exists with $0.00/$5.00
2. Click the budget name → see "Budget history" tab
3. Verify both alerts (80% and 100%) are listed in "Alert history"

### CloudWatch Alarm Verification

1. CloudWatch → Alarms → All alarms (region: us-east-1)
2. Confirm `billing-over-5-dollars` is in **OK** state
3. Click the alarm name → see the metric graph (flat line at $0.00)

### Billing Dashboard Cross-Check

1. Billing → Dashboard
2. Confirm "Budgets" widget shows your active budget
3. Confirm "Free Tier" section shows 0% usage

---

## Console Navigation Quick Reference

| Task | Path |
|------|------|
| Billing Dashboard | Account menu → Billing and Cost Management |
| Cost Explorer | Billing → Cost Explorer |
| Create Budget | Billing → Budgets → Create budget |
| Edit Budget | Billing → Budgets → [budget name] → Edit |
| Delete Budget | Billing → Budgets → [budget name] → Delete |
| CloudWatch Alarms | CloudWatch (us-east-1) → Alarms → All alarms |
| Free Tier Usage | Billing → Free Tier |
| Billing Preferences | Billing → Billing preferences |
| Cost Allocation Tags | Billing → Cost allocation tags |
| View Current Invoice | Billing → Bills |

---

*End of steps_awsconsoleui.md — Project 0.4*
