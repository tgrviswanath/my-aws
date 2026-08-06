# Console UI Guide — Project 2.5: AWS Failure Simulation and Chaos Engineering

> Step-by-step console walkthrough for simulating real AWS failures — EC2 AZ outage, RDS Multi-AZ failover, and AWS FIS chaos experiments. Includes decision points, screenshot markers, and timing guidance.

---

## Prerequisites Check

Verify the entire multi-AZ environment is healthy before injecting any failures:

| Component | Where to Check | Required State |
|---|---|---|
| EC2 instances (×2) | EC2 → Instances | Both "running", in different AZs |
| ALB target group | EC2 → Target Groups → Health | Both targets "healthy" (green) |
| RDS Multi-AZ | RDS → Databases → Multi-AZ column | Shows "Yes" |
| RDS status | RDS → Databases → Status | "Available" |
| FIS permissions | IAM → Roles → FISRole | `ec2:TerminateInstances`, `fis:*` |
| CloudWatch alarm (recommended) | CloudWatch → Alarms | Optional: alarm on UnHealthyHostCount > 0 |

**Quick Console Pre-flight Check**
1. Open EC2 → Target Groups → select your target group → Targets tab
2. Confirm both instances show: Health status = **healthy**, Target status = **in-service**
3. Open a second browser tab to EC2 → Instances (you'll watch this during failure)
4. Open a third browser tab to your application URL (continuous manual refresh test)

### 📸 Screenshot
> Take a screenshot of the ALB target group showing both instances as healthy BEFORE any failures.
> Label it: `00_baseline_both_targets_healthy.png`

---

## Step 1 — Verify Multi-AZ Setup

**Verify ALB Spans Multiple AZs**
1. EC2 → Load Balancers → Select your ALB
2. Description tab → Availability Zones section
3. Confirm: 2 AZs listed (e.g., us-east-1a and us-east-1b)
4. Note which instance is in which AZ (you'll terminate the one in us-east-1b)

**Verify RDS Multi-AZ**
1. RDS → Databases → Click your DB instance
2. Configuration tab → Check:
   - Multi-AZ: **Yes**
   - Secondary AZ: shows an AZ (e.g., us-east-1b)
3. If Multi-AZ is "No": Actions → Modify → Enable Multi-AZ → Apply immediately
   - Wait 5–10 minutes for Multi-AZ to be enabled before proceeding

**Verify EC2 AZ Distribution**
1. EC2 → Instances → Add column: Availability Zone
2. Confirm:
   - Instance 1: us-east-1a
   - Instance 2: us-east-1b

### 📸 Screenshot
> Take a screenshot showing:
> - ALB description with both AZs listed
> - RDS configuration showing Multi-AZ: Yes and Secondary AZ
> Label it: `01_multiaz_setup_verified.png`

---

## Step 2 — Simulate EC2 AZ Failure

### Decision Point 1: Terminate vs Stop — What Really Simulates a Failure?

| Action | Console Setting | What It Simulates | ALB Response | Instance Recoverable? |
|---|---|---|---|---|
| ✅ Terminate instance | Actions → Terminate | Real hardware failure / AZ outage | Health check detects within ~30s | ❌ No — permanent |
| Stop instance | Actions → Stop | Graceful shutdown | Same detection time | ✅ Yes — can restart |
| Suspend instance (not AWS) | N/A | Doesn't exist in EC2 | N/A | N/A |
| Reboot instance | Actions → Reboot | OS restart, brief downtime | Detects briefly unhealthy | ✅ Auto-recovery |

> **Terminate = real failure simulation.** Stopping is a graceful shutdown — in real AZ failures, instances don't gracefully stop. Terminate simulates the abrupt loss.

**Preparation: Set Up Monitoring Window**
Before terminating, open these in separate browser tabs:
- Tab 1: EC2 → Target Groups → Your TG → Targets tab (keep refreshing)
- Tab 2: Your application URL (`http://ALB_DNS/` — keep refreshing)
- Tab 3 (optional): CloudWatch → Metrics → ALB → HealthyHostCount

**Execute EC2 AZ Failure**
1. EC2 → Instances
2. Select the instance in **us-east-1b** (the one you want to "fail")
3. Actions → Instance State → **Terminate**
4. Confirm termination dialog → click **Terminate**
5. ⏱️ **Start your timer immediately**

**What to Watch (Immediately After Termination)**
- EC2 Instances: Instance state changes from "running" → "shutting-down" → "terminated"
- Target Group tab: Target state changes from "healthy" → "draining" → (removed)
- Application URL: Continue refreshing — should remain accessible throughout

### 📸 Screenshot
> Take a screenshot of the target group showing:
> - One target marked "unhealthy" or "draining"
> - Other target still "healthy"
> - Timer reading (approximate seconds elapsed)
> Label it: `02_ec2_failure_target_unhealthy_detected.png`

### Expected Outcome
- **Within 0–10s:** Instance state → "shutting-down"
- **Within 10–30s:** Target group shows one target as "unhealthy" or "draining"
- **Within 30–60s:** Target removed from rotation, 100% traffic to surviving instance
- **Application:** Continues serving all requests without user-visible error
- **ALB metric:** `HealthyHostCount` drops from 2 → 1
- **RTO for ALB failover:** 15–45 seconds

### Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Application shows errors during transition | ALB health check interval too long | Reduce health check interval to 10s for sensitive apps |
| Target shows "draining" for a long time | Deregistration delay set high (default 300s) | Reduce deregistration delay in TG attributes for lab |
| Application completely unreachable | Both instances accidentally terminated | Launch a new instance and register it in the target group |
| ALB shows 502 after failover | Surviving instance overloaded | Monitor CPU — resize instance if needed |

---

## Step 3 — Simulate RDS Multi-AZ Failover

### Decision Point 2: Multi-AZ Failover vs Read Replica Promotion

| Method | Automatic? | Failover Time | Data Loss (RPO) | Use Case |
|---|---|---|---|---|
| ✅ Multi-AZ forced failover (this step) | Automatic (after trigger) | 30–90 seconds | ~0 (synchronous) | HA for primary DB |
| Read Replica promotion | Manual only | 5–30 minutes | Some (async) | Regional DR, not HA |
| Aurora failover | Automatic | < 30 seconds | ~0 | Aurora-specific HA |

> **Multi-AZ standby is synchronous — every write to primary is replicated to standby before acknowledging the write.** This means RPO ≈ 0 seconds. The 30–90s cost is RTO, not data loss.

**Check RDS Before Failover**
1. RDS → Databases → Click your instance
2. Note: Availability Zone (e.g., `us-east-1a`) — this is the current primary
3. Events tab → Check for any current events

**Execute Forced Failover**
1. RDS → Databases → Select your Multi-AZ instance
2. Actions → **Reboot**
3. In the reboot dialog: ✅ **Check "Reboot With Failover"**
4. Click **Confirm** (this triggers the Multi-AZ standby to become primary)
5. ⏱️ **Start your timer immediately**

**Watch the Failover in Real Time**
1. RDS → Databases: Status changes `available` → `rebooting` → `available`
2. Events tab (refresh every 10–15s): Look for messages:
   - "Multi-AZ instance failover started"
   - "DB instance restarted"
   - "Multi-AZ instance failover completed"
3. After completion: Availability Zone should show **different AZ** than before

### 📸 Screenshot
> Take a screenshot of the RDS Events tab showing the failover sequence with timestamps.
> Label it: `03_rds_failover_events_timeline.png`

### Expected Outcome
- **0s:** Status → "rebooting", Availability Zone still shows original AZ
- **15–30s:** Failover event appears in Events log
- **30–90s:** Status returns to "available", Availability Zone now shows DIFFERENT AZ
- **Database connections:** Existing connections drop and must reconnect (this is expected)
- **Application:** Connection pool should automatically reconnect within a few seconds
- **RTO for RDS Multi-AZ:** 30–90 seconds (this is the AWS SLA range)

### Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Status stays "rebooting" > 3 minutes | Large pending transaction log draining | Wait — RDS completes pending writes before failover |
| Application can't reconnect after failover | Connection string uses IP, not DNS endpoint | Always use RDS DNS endpoint, never hardcoded IPs |
| AZ shows same as before | "Reboot with Failover" box wasn't checked | Repeat with the checkbox enabled |
| No failover event in Events tab | Not a Multi-AZ instance | Verify Multi-AZ is "Yes" in Configuration tab |

---

## Step 4 — AWS FIS Experiment

### Decision Point 3: FIS vs Manual Termination — When to Use Each

| Approach | Repeatability | Documentation | CI/CD | Learning Value |
|---|---|---|---|---|
| Manual termination (Steps 2–3) | Low (one-off) | Notes only | ❌ No | ✅ High — hands-on |
| ✅ AWS FIS experiment | ✅ High — template reusable | Template = documentation | ✅ Yes via API/CLI | Medium |
| FIS GameDay | Scheduled, organization-wide | Formal runbook | ✅ Automated | ✅ High |

> **Start with manual (Steps 2–3) to learn the behavior. Use FIS to encode and repeat experiments.**

**Create FIS Experiment Template**
1. Navigate to: **AWS Fault Injection Simulator** (search in console)
2. Experiment templates → **Create experiment template**
3. **Description:** `EC2 terminate in us-east-1b - chaos lab 2.5`
4. **IAM role:** Select or create `FISRole`
   - If creating new: needs permissions for `ec2:TerminateInstances`, `iam:PassRole`
5. **Targets** section → Add target:
   - Name: `labEC2s`
   - Resource type: `aws:ec2:instance`
   - Target method: Resource tags
   - Tag: Key=`Environment`, Value=`lab`
   - Selection mode: `COUNT(1)` (terminates exactly 1 instance)
6. **Actions** section → Add action:
   - Name: `terminateOne`
   - Action type: `aws:ec2:terminate-instances`
   - Target: `labEC2s`
7. **Stop conditions** → Add stop condition:
   - Source: `aws:cloudwatch:alarm`
   - Alarm ARN: your "TooManyUnhealthyHosts" alarm (or select "none" for lab)
8. Click **Create experiment template**

### 📸 Screenshot
> Take a screenshot of the completed FIS experiment template showing:
> - Template name/description
> - Actions: aws:ec2:terminate-instances
> - Targets: EC2 instances tagged Environment=lab
> Label it: `04_fis_experiment_template_created.png`

**Run FIS Experiment**
1. Experiment templates → Select your template → **Start experiment**
2. Confirm: type `start` in the confirmation box
3. Experiment status: Running → Completed (typically < 1 minute for terminate action)
4. Experiment detail shows: Actions taken, resources affected, duration

**Monitor Experiment Results**
- EC2 → Instances: confirm one instance was terminated
- Target group: shows unhealthy target detection (same as Step 2)
- FIS → Experiments → Your experiment → shows completion status and actions log

### Expected Outcome
- FIS terminates exactly 1 instance (COUNT(1) selection mode)
- ALB detects and reroutes traffic (same ~30s as manual experiment)
- Experiment detail shows "completed" status with instance ID that was affected
- Template is now reusable — click "Start experiment" any time for the same chaos test

### Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| "Experiment failed to start" | FIS IAM role missing permissions | Attach `AmazonEC2FullAccess` to FISRole (or targeted policy) |
| "No targets found" | No EC2 instances tagged Environment=lab | Tag your EC2 instances: Key=Environment, Value=lab |
| Stop condition triggers immediately | CloudWatch alarm already in ALARM state | Resolve the alarm or set stop condition to "none" |
| COUNT(1) terminates wrong instance | Tag filter not specific enough | Add additional tags to narrow the target selection |

---

## Experiment Results Log (Fill This In)

Use this table to record your actual measurements:

| Experiment | Start Time | Recovery Time | RTO (seconds) | Notes |
|---|---|---|---|---|
| EC2 termination → ALB reroute | | | | |
| RDS Multi-AZ forced failover | | | | |
| FIS EC2 terminate experiment | | | | |

**Key Takeaways to Document**
- Did the application experience any user-visible errors?
- Was the RTO within the expected range?
- What would need to change to reduce RTO further?
- What application-level retry logic would help?

---

## Cleanup Summary

From Console:
1. **FIS** → Experiment templates → Select your templates → **Delete**
2. **EC2** → Launch a replacement instance in us-east-1b (to restore environment)
   - Or: if done with lab, terminate ALL EC2 instances
3. **RDS** → If done with lab: Actions → Delete (uncheck "Create final snapshot" for lab)
4. **CloudWatch** → Alarms → Delete any lab-specific alarms created

Or use CLI cleanup commands — see GUIDE.md Section 10.
