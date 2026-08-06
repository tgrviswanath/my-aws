# Project 2.5 — AWS Failure Simulation and Chaos Engineering

---

## 1. Overview

**Problem Statement**
Most production outages are discovered by customers, not by engineers. Systems that have never been tested under failure conditions contain hidden assumptions: "the database will always be there," "the second AZ will take over instantly," "retry logic will handle transient errors." These assumptions are only visible when they fail — ideally in a controlled lab, not at 2 AM.

**What You'll Learn**
- How ALB health checks detect and route around unhealthy EC2 instances
- How RDS Multi-AZ automatic failover works and how long it takes
- How AWS Fault Injection Simulator (FIS) enables repeatable chaos experiments
- How to measure Recovery Time Objective (RTO) and Recovery Point Objective (RPO)
- How to document resilience properties for your architecture

**Objectives**
1. Verify the multi-AZ setup (ALB + EC2 in 2 AZs, RDS Multi-AZ enabled)
2. Simulate EC2 AZ failure by terminating one instance — observe ALB rerouting
3. Simulate RDS primary failure by forcing a failover — measure switchover time
4. Use AWS FIS to run repeatable, documented chaos experiments
5. Calculate and record actual RTO for each failure scenario

---

## 2. Architecture

```
Normal State:
                    ┌─────────────────────┐
Internet ──────────▶│  ALB (multi-AZ)     │
                    └──────┬──────────────┘
                           │ Routes to healthy targets
              ┌────────────┴────────────┐
              ▼                         ▼
    ┌─────────────────┐       ┌─────────────────┐
    │ EC2 us-east-1a  │       │ EC2 us-east-1b  │ ◀── AZ failure target
    │ app server v1   │       │ app server v2   │
    └────────┬────────┘       └────────┬────────┘
             │                         │
             └───────────┬─────────────┘
                         ▼
              ┌─────────────────────┐
              │  RDS Primary        │ ◀── Failover target
              │  us-east-1a         │
              └─────────────────────┘
                         │ Multi-AZ sync replication
              ┌─────────────────────┐
              │  RDS Standby        │
              │  us-east-1b (hidden)│
              └─────────────────────┘

Failure State (after EC2 us-east-1b terminated):
                    ┌─────────────────────┐
Internet ──────────▶│  ALB detects failure│
                    └──────┬──────────────┘
                           │ ALL traffic routed here
                           ▼
                 ┌─────────────────┐    ✗ EC2 us-east-1b
                 │ EC2 us-east-1a  │      (terminated)
                 └────────┬────────┘
```

---

## 3. Prerequisites

**AWS Account & Permissions**
- IAM permissions: `ec2:TerminateInstances`, `ec2:DescribeInstances`, `elasticloadbalancing:*`, `rds:RebootDBInstance`, `fis:*`
- AWS CLI configured with `us-east-1`

**Infrastructure Requirements (from earlier projects)**
- ALB created from Project 2.3 with at least 2 EC2 targets (one per AZ)
- RDS instance with Multi-AZ enabled (from Project 2.2 or new)
- Both EC2 instances must be running and healthy (green in target group)
- CloudWatch alarms recommended to observe metric changes during failures

**Quick Infrastructure Verification**
```bash
# Verify ALB targets are healthy before starting
TG_ARN="arn:aws:elasticloadbalancing:us-east-1:ACCOUNT:targetgroup/web-tg/xxxx"
aws elbv2 describe-target-health --target-group-arn ${TG_ARN} \
  --query "TargetHealthDescriptions[].{Target:Target.Id,AZ:Target.AvailabilityZone,State:TargetHealth.State}" \
  --output table

# Verify RDS Multi-AZ is enabled
aws rds describe-db-instances \
  --query "DBInstances[?MultiAZ==\`true\`].{ID:DBInstanceIdentifier,Status:DBInstanceStatus,MultiAZ:MultiAZ,SecondaryAZ:SecondaryAvailabilityZone}" \
  --output table
```

---

## 4. Folder Structure

```
project_2.5_failure_simulation/
├── GUIDE.md                           # This file
├── steps_awsconsoleui.md              # Console walkthrough with screenshots
├── cost_estimate.md                   # FIS and EC2 replacement cost
├── scripts/
│   ├── verify_setup.sh                # Pre-flight checks before experiments
│   ├── simulate_ec2_failure.sh        # Terminate one EC2, monitor health
│   ├── simulate_rds_failover.sh       # Force RDS failover, measure time
│   ├── create_fis_template.sh         # Create FIS experiment template
│   ├── run_fis_experiment.sh          # Start FIS experiment and monitor
│   └── restore_environment.sh        # Launch replacement EC2, verify
├── fis_templates/
│   ├── ec2_terminate_experiment.json  # FIS template: terminate EC2
│   └── rds_failover_experiment.json   # FIS template: RDS failover
└── runbook/
    └── incident_response.md           # Runbook for each failure scenario
```

---

## 5. Implementation

### 5A. Console Walkthrough

#### Prerequisites Check
- [ ] EC2 → Instances: 2 running instances in different AZs, both healthy
- [ ] EC2 → Load Balancers → Your ALB → Target Groups → All targets show "healthy"
- [ ] RDS → Databases → Multi-AZ column shows "Yes" for your instance
- [ ] CloudWatch → Alarms → Consider creating alarm on `UnHealthyHostCount > 0`
- [ ] FIS console accessible (confirm IAM role with `fis:*` permissions)

#### Decision Point 1: Manual Termination vs AWS FIS

| Approach | Best For | Repeatability | CI/CD Integration |
|---|---|---|---|
| ✅ Manual EC2 termination | Learning, one-time experiments | Low | No |
| ✅ AWS FIS experiment | Repeatable chaos, GameDay testing | High | ✅ Yes via CLI |
| EC2 stop (not terminate) | Graceful shutdown simulation | Medium | No |
| Network ACL block | Network partition simulation | Medium | No |

> **Use manual termination first** to understand the behavior, then encode it as an FIS experiment for future repeatability.

**Simulate EC2 Failure via Console**
1. Open EC2 → Instances in two browser tabs (one for actions, one to monitor)
2. EC2 → Load Balancers → Target Groups → Monitor target health in real time
3. Select one EC2 instance (in us-east-1b) → Actions → Instance State → Terminate
4. Immediately switch to the Target Groups tab and watch the health change
5. Start a timer — record how long until ALB stops sending traffic to terminated instance

**Expected Outcome**
- Within ~10-30 seconds: Target state changes from "healthy" → "draining" → "unused"
- ALB routes 100% of traffic to the surviving instance within ~30 seconds
- Your application continues serving requests (verify with `curl` loop in terminal)

**Simulate RDS Failover via Console**
1. RDS → Databases → Select your Multi-AZ instance
2. Actions → Reboot → Check "Reboot with Failover" → Confirm
3. Start timer immediately
4. Watch RDS Events tab (refresh every 10s): Primary → Rebooting → Availability failover
5. Record time from reboot initiation to "database available" event

**Expected RTO**: 30–60 seconds for RDS Multi-AZ automatic failover.

**AWS FIS Experiment via Console**
1. Navigate to AWS Fault Injection Simulator → Experiment templates → Create template
2. Description: "Terminate EC2 in AZ failure simulation"
3. Add action: `aws:ec2:terminate-instances`
4. Target: EC2 instances tagged with `Environment=lab`
5. Stop condition: CloudWatch alarm (UnHealthyHostCount > 1 for 5 minutes)
6. IAM role: create `FISRole` with permission to terminate EC2
7. Click Create template → Start experiment

**Troubleshooting**
- ALB not rerouting after termination: Check health check interval (default 30s) — may take 2-3 intervals
- RDS failover took longer than 60s: Check if there were pending transactions draining; this is normal
- FIS experiment won't start: IAM role missing `ec2:TerminateInstances` or target filter returns 0 resources
- Application errors during failover: Connection pool needs retry logic — expected behavior during ~30s transition

---

### 5B. CLI Implementation

```bash
# --- Variables ---
ALB_TG_ARN="arn:aws:elasticloadbalancing:us-east-1:ACCT:targetgroup/web-tg/xxxx"
INSTANCE_TO_TERMINATE="i-xxxxxxxxx"    # EC2 in the AZ you want to simulate failing
RDS_INSTANCE_ID="myapp-db"
FIS_ROLE_ARN="arn:aws:iam::ACCT:role/FISRole"
REGION="us-east-1"

# === EXPERIMENT 1: EC2 AZ Failure ===

# Step 1: Record baseline — both targets healthy
echo "=== BASELINE: Target Health ===" && date
aws elbv2 describe-target-health --target-group-arn ${ALB_TG_ARN} \
  --query "TargetHealthDescriptions[].{Target:Target.Id,AZ:Target.AvailabilityZone,State:TargetHealth.State}" \
  --output table

# Step 2: Terminate the instance (simulates AZ failure)
echo "=== INJECTING FAILURE: Terminating ${INSTANCE_TO_TERMINATE} ===" && date
aws ec2 terminate-instances --instance-ids ${INSTANCE_TO_TERMINATE}
FAILURE_START=$(date +%s)

# Step 3: Poll target health until failover complete
echo "=== MONITORING: Watching for ALB to reroute traffic ==="
while true; do
  HEALTH=$(aws elbv2 describe-target-health --target-group-arn ${ALB_TG_ARN} \
    --query "TargetHealthDescriptions[?TargetHealth.State!='healthy'].{Target:Target.Id,State:TargetHealth.State,Reason:TargetHealth.Reason}" \
    --output text)
  
  CURRENT=$(date +%s)
  ELAPSED=$((CURRENT - FAILURE_START))
  echo "[${ELAPSED}s elapsed] Unhealthy targets: ${HEALTH}"
  
  UNHEALTHY_COUNT=$(aws elbv2 describe-target-health --target-group-arn ${ALB_TG_ARN} \
    --query "length(TargetHealthDescriptions[?TargetHealth.State=='unhealthy'])" --output text)
  
  if [ "${UNHEALTHY_COUNT}" == "0" ]; then
    echo "=== RECOVERY COMPLETE at ${ELAPSED} seconds ==="
    break
  fi
  sleep 5
done

# === EXPERIMENT 2: RDS Multi-AZ Failover ===

echo "=== RDS BASELINE: Primary AZ ===" && date
aws rds describe-db-instances \
  --db-instance-identifier ${RDS_INSTANCE_ID} \
  --query "DBInstances[0].{AZ:AvailabilityZone,Status:DBInstanceStatus,MultiAZ:MultiAZ}" \
  --output table

# Force failover (reboot with failover)
echo "=== INJECTING FAILURE: RDS forced failover ===" && date
RDS_FAILOVER_START=$(date +%s)
aws rds reboot-db-instance \
  --db-instance-identifier ${RDS_INSTANCE_ID} \
  --force-failover

# Poll until available again
echo "=== MONITORING: Waiting for RDS to become available ==="
while true; do
  STATUS=$(aws rds describe-db-instances \
    --db-instance-identifier ${RDS_INSTANCE_ID} \
    --query "DBInstances[0].DBInstanceStatus" --output text)
  
  CURRENT=$(date +%s)
  ELAPSED=$((CURRENT - RDS_FAILOVER_START))
  echo "[${ELAPSED}s elapsed] RDS Status: ${STATUS}"
  
  if [ "${STATUS}" == "available" ]; then
    NEW_AZ=$(aws rds describe-db-instances \
      --db-instance-identifier ${RDS_INSTANCE_ID} \
      --query "DBInstances[0].AvailabilityZone" --output text)
    echo "=== RDS FAILOVER COMPLETE at ${ELAPSED}s | New primary AZ: ${NEW_AZ} ==="
    break
  fi
  sleep 10
done

# === EXPERIMENT 3: AWS FIS Experiment ===

# Create FIS experiment template
FIS_TEMPLATE=$(aws fis create-experiment-template \
  --description "EC2 AZ failure simulation for lab 2.5" \
  --stop-conditions '[{"source":"none"}]' \
  --targets '{
    "labInstances": {
      "resourceType": "aws:ec2:instance",
      "resourceTags": {"Environment": "lab"},
      "selectionMode": "COUNT(1)"
    }
  }' \
  --actions '{
    "terminateInstances": {
      "actionId": "aws:ec2:terminate-instances",
      "targets": {"Instances": "labInstances"}
    }
  }' \
  --role-arn ${FIS_ROLE_ARN} \
  --query "experimentTemplate.id" --output text)

echo "FIS Template ID: ${FIS_TEMPLATE}"

# Start FIS experiment
EXPERIMENT_ID=$(aws fis start-experiment \
  --experiment-template-id ${FIS_TEMPLATE} \
  --query "experiment.id" --output text)

echo "FIS Experiment ID: ${EXPERIMENT_ID}"

# Monitor experiment
aws fis get-experiment --id ${EXPERIMENT_ID} \
  --query "experiment.{Status:state.status,CreationTime:creationTime}" \
  --output table
```

---

## 6. Code Deep Dive

### FIS Action Types Available
```
aws:ec2:terminate-instances     — Terminate EC2 instances
aws:ec2:stop-instances          — Stop EC2 instances (graceful)
aws:ec2:send-spot-instance-interruptions — Simulate Spot interruption
aws:rds:failover-db-cluster     — RDS Multi-AZ or Aurora failover
aws:fis:inject-api-internal-error — Simulate API errors
aws:ssm:send-command            — Run SSM command (CPU stress, network latency)
```

### FIS Stop Condition (safety switch)
```json
{
  "source": "aws:cloudwatch:alarm",
  "value": "arn:aws:cloudwatch:us-east-1:ACCT:alarm/TooManyUnhealthyHosts"
}
```

---

## 7. Verification

```bash
# After EC2 termination: confirm ALB routes to surviving instance only
aws elbv2 describe-target-health --target-group-arn ${ALB_TG_ARN} --output table

# After RDS failover: confirm new primary AZ is different from original
aws rds describe-db-instances \
  --db-instance-identifier ${RDS_INSTANCE_ID} \
  --query "DBInstances[0].{NewAZ:AvailabilityZone,Status:DBInstanceStatus}" \
  --output table

# Check RDS events for failover record
aws rds describe-events \
  --source-identifier ${RDS_INSTANCE_ID} \
  --source-type db-instance \
  --duration 60 \
  --query "Events[].{Time:Date,Message:Message}" \
  --output table
```

---

## 8. Observations

| Experiment | Expected RTO | Typical Actual | Notes |
|---|---|---|---|
| EC2 termination → ALB reroute | 30s | 15–45s | Depends on health check interval |
| RDS Multi-AZ failover | 60s | 30–90s | Longer if transactions pending |
| FIS spot interruption | 2 min | 1–3 min | Per AWS SLA |
| AZ network partition (manual NACL) | Immediate route | 15–30s | ALB detects via health check |

---

## 9. Screenshots

1. Both EC2 instances showing "healthy" in target group before experiment
2. Target group during failover showing one "draining" target
3. RDS Events tab showing "Multi-AZ instance failover started" and "completed" timestamps
4. FIS Experiment detail showing actions taken and completion status
5. Terminal showing continuous curl loop with no errors during ALB failover
6. CloudWatch metric `HealthyHostCount` graph dipping and recovering

---

## 10. Cleanup

```bash
# Step 1: Delete FIS experiment templates
aws fis list-experiment-templates \
  --query "experimentTemplates[?description=='EC2 AZ failure simulation for lab 2.5'].id" \
  --output text | xargs -I{} aws fis delete-experiment-template --id {}

# Step 2: Launch replacement EC2 (restore environment)
NEW_INSTANCE=$(aws ec2 run-instances \
  --image-id ami-0c02fb55956c7d316 \
  --instance-type t2.micro \
  --key-name your-key-pair \
  --subnet-id ${SUBNET_1B} \
  --security-group-ids ${SG_ID} \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=web-server-1b},{Key=Environment,Value=lab}]' \
  --user-data file://userdata/web_server.sh \
  --query "Instances[0].InstanceId" --output text)

echo "Replacement EC2: ${NEW_INSTANCE}"

# Register replacement in target group
aws elbv2 register-targets \
  --target-group-arn ${ALB_TG_ARN} \
  --targets Id=${NEW_INSTANCE},Port=80

# Step 3: Verify environment restored
aws elbv2 describe-target-health --target-group-arn ${ALB_TG_ARN} --output table

# Step 4: If done with entire lab — terminate all EC2s and delete RDS
# aws ec2 terminate-instances --instance-ids ${ALL_INSTANCE_IDS}
# aws rds delete-db-instance --db-instance-identifier ${RDS_INSTANCE_ID} --skip-final-snapshot

echo "Environment restored and verified"
```
