# Project 2.5 — Chaos Engineering & Failure Simulation

**Stage:** 02 | **Level:** Advanced | **Est. Time:** 3–4 hours | **Cost:** ~$10–20/session

Use AWS Fault Injection Simulator (FIS) to deliberately break the infrastructure built in Projects 2.2 and 2.4 and measure how fast it recovers. Three failure scenarios are scripted: terminate EC2 instances behind an ALB and watch health-check-based failover, reboot the RDS MySQL instance and measure downtime, and block AZ-level traffic to observe Route 53 health check redirection. Recovery times (RTO) are measured for each scenario and compared against the theoretical minimums. CloudWatch dashboards track 5XX error rates and `TargetResponseTime` spikes during each experiment.

## Services Used

| Tool | Purpose | Cost |
|---|---|---|
| AWS FIS | Fault injection orchestration — runs experiments | Free |
| ALB | Observability target — 5XX rate and health check state | ~$16/month |
| EC2 (×2) | Failure target — instance termination and stop actions | ~$8/month each |
| RDS MySQL | Failure target — reboot with and without Multi-AZ | ~$15/month |
| Route 53 Health Checks | DNS failover trigger after AZ disruption | $0.50/health check |
| CloudWatch | Metrics, alarms, and dashboards during experiments | ~$3/month |
| IAM Role | FIS execution role with EC2/RDS terminate permissions | Free |

## Input / Output

### Input

| Parameter | Value |
|---|---|
| ALB + EC2 setup | Running infrastructure from Project 2.2 |
| RDS instance | `project22-mysql` from Project 2.2 |
| Route 53 health check | Associated with EC2 EIP from Project 2.4 |
| FIS experiment: EC2 | Action: `aws:ec2:terminate-instances`, 1 target |
| FIS experiment: RDS | Action: `aws:rds:reboot-db-instances`, no failover |
| FIS experiment: AZ | Action: `aws:ec2:stop-instances`, filter by AZ tag |
| CloudWatch alarm | `HTTPCode_Target_5XX_Count > 5` for 1 minute |

### Output

| Failure Scenario | Measured RTO |
|---|---|
| EC2 termination (ALB health check default 30s + threshold 2) | ~60–90 seconds |
| EC2 termination (ALB health check fast 10s + threshold 2) | ~20–30 seconds |
| RDS reboot, single-AZ | 60–120 seconds full outage |
| RDS reboot, Multi-AZ enabled | 60–120 seconds automatic failover to standby |
| AZ failure + Route 53 health check (TTL 60s) | 60–120 seconds DNS propagation |

## Architecture

```
  [FIS Experiment Template]
  IAM Role: fis-execution-role
         │
         ├─── Action 1: terminate EC2 web-tier-1a
         │         │
         │    [ALB health check detects unhealthy target]
         │    [ALB removes target from rotation]
         │    [CloudWatch: 5XX spike then drops to 0]
         │
         ├─── Action 2: reboot RDS project22-mysql
         │         │
         │    [RDS unavailable 60–120s]
         │    [App tier returns DB connection errors]
         │    [CloudWatch: TargetResponseTime spike]
         │
         └─── Action 3: stop all EC2 in us-east-1a
                   │
              [Route 53 health check fails for 1a endpoint]
              [DNS stops returning 1a IP after TTL expires]
              [Traffic shifts to us-east-1b endpoint]
```

## Quick Start

```cmd
REM Step 1: Create IAM role for FIS
aws iam create-role ^
  --role-name fis-execution-role ^
  --assume-role-policy-document "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":{\"Service\":\"fis.amazonaws.com\"},\"Action\":\"sts:AssumeRole\"}]}"

aws iam attach-role-policy ^
  --role-name fis-execution-role ^
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonFISServiceRolePolicy

REM Step 2: Set up CloudWatch alarm to watch 5XX errors during experiments
aws cloudwatch put-metric-alarm ^
  --alarm-name fis-5xx-alarm ^
  --metric-name HTTPCode_Target_5XX_Count ^
  --namespace AWS/ApplicationELB ^
  --dimensions Name=LoadBalancer,Value=<ALB_FULL_NAME> ^
  --statistic Sum ^
  --period 60 ^
  --threshold 5 ^
  --comparison-operator GreaterThanThreshold ^
  --evaluation-periods 1 ^
  --alarm-actions <SNS_TOPIC_ARN>

REM Step 3: Create FIS experiment template — EC2 termination
aws fis create-experiment-template ^
  --description "Terminate one web-tier EC2 behind ALB" ^
  --targets "{\"webInstances\":{\"resourceType\":\"aws:ec2:instance\",\"resourceTags\":{\"Name\":\"web-tier-1a\"},\"selectionMode\":\"COUNT(1)\"}}" ^
  --actions "{\"terminateWeb\":{\"actionId\":\"aws:ec2:terminate-instances\",\"targets\":{\"Instances\":\"webInstances\"}}}" ^
  --stop-conditions "[{\"source\":\"aws:cloudwatch:alarm\",\"value\":\"<ALARM_ARN>\"}]" ^
  --role-arn arn:aws:iam::<ACCOUNT_ID>:role/fis-execution-role

REM Step 4: Start EC2 termination experiment; poll target health every 10s
aws fis start-experiment --experiment-template-id <TEMPLATE_ID_EC2>
aws elbv2 describe-target-health --target-group-arn <WEB_TG_ARN>

REM Step 5: Create FIS template for RDS reboot
aws fis create-experiment-template ^
  --description "Reboot RDS to measure downtime" ^
  --targets "{\"rdsTarget\":{\"resourceType\":\"aws:rds:db\",\"resourceArns\":[\"arn:aws:rds:us-east-1:<ACCOUNT_ID>:db:project22-mysql\"],\"selectionMode\":\"ALL\"}}" ^
  --actions "{\"rebootRds\":{\"actionId\":\"aws:rds:reboot-db-instances\",\"targets\":{\"DBInstances\":\"rdsTarget\"}}}" ^
  --stop-conditions "[{\"source\":\"none\"}]" ^
  --role-arn arn:aws:iam::<ACCOUNT_ID>:role/fis-execution-role

REM Step 6: Start RDS reboot experiment; poll until Available
aws fis start-experiment --experiment-template-id <TEMPLATE_ID_RDS>

aws rds describe-db-instances ^
  --db-instance-identifier project22-mysql ^
  --query "DBInstances[0].DBInstanceStatus"

REM Step 7: Create CloudWatch dashboard for experiment visibility
aws cloudwatch put-dashboard --dashboard-name FIS-Experiments ^
  --dashboard-body "{\"widgets\":[{\"type\":\"metric\",\"properties\":{\"metrics\":[[\"AWS/ApplicationELB\",\"HTTPCode_Target_5XX_Count\"],[\"AWS/ApplicationELB\",\"TargetResponseTime\"]],\"period\":10,\"title\":\"ALB During FIS Experiments\"}}]}"
```

## Data Flow

1. FIS reads the experiment template, assumes `fis-execution-role`, and calls the target AWS APIs to inject the fault.
2. EC2 termination experiment: FIS calls `ec2:TerminateInstances` on `web-tier-1a`. The instance enters `shutting-down` state.
3. ALB health check next fires against the terminated instance — connection refused — and marks the target `unhealthy` after 2 consecutive failures.
4. ALB stops sending new requests to the unhealthy target; all traffic shifts to remaining healthy targets. Existing in-flight connections on the terminated instance drop immediately.
5. CloudWatch `HTTPCode_Target_5XX_Count` spikes during the health check detection window, then returns to zero once traffic is fully rerouted.
6. RDS reboot experiment: FIS calls `rds:RebootDBInstance`. The DB becomes unavailable; app-tier EC2 logs `Communications link failure` errors.
7. RDS comes back online after 60–120 seconds. If Multi-AZ is enabled, AWS promotes the standby replica before the primary fully restarts — actual downtime is shorter.
8. Route 53 health check experiment: stopping AZ instances causes HTTP health check failures. After `FailureThreshold` (3×) consecutive failures, Route 53 excludes that record. Clients with cached TTL see no change until TTL expires and they re-query.

## Project Files

| File | Description |
|---|---|
| `README.md` | This document |
| `fis-iam-setup.sh` | Creates the FIS IAM execution role |
| `ec2-termination-template.json` | FIS experiment template for EC2 termination |
| `rds-reboot-template.json` | FIS experiment template for RDS reboot |
| `az-stop-template.json` | FIS experiment template for AZ-level EC2 stop |
| `cloudwatch-dashboard.json` | Dashboard showing 5XX count and TargetResponseTime |
| `measure-rto.sh` | Polls health status every 5 seconds and timestamps recovery |
| `results.md` | Recorded RTOs for all three failure scenarios |

## Lessons Learned

- **ALB failure detection time = interval × unhealthy threshold:** Default settings (30s interval, threshold 2) mean 60 seconds before a dead target stops receiving traffic. Switching to fast health checks (10s interval, threshold 2) cuts detection to 20 seconds — worth the extra cost for latency-sensitive apps.
- **RDS reboot only triggers failover if Multi-AZ is enabled:** A single-AZ RDS reboot causes a real outage. With Multi-AZ, AWS automatically promotes the synchronous standby replica — the endpoint DNS stays the same, but the underlying host changes. Applications must reconnect (connection pool refresh).
- **FIS experiment templates require an IAM role with inject permissions:** FIS does not use your CLI credentials to perform the fault actions — it assumes a dedicated IAM role. Attach `AmazonFISServiceRolePolicy` or write a custom policy scoped to only the resources you want to target.
- **CloudWatch metrics during failure show a sharp 5XX spike, then zero:** The spike represents requests hitting the unhealthy target before ALB removes it. After removal, the ALB only routes to healthy targets so 5XX drops. If 5XX persists after the spike, the underlying app — not the infrastructure — is the problem.
- **Chaos engineering principle: define steady state before you inject a fault:** Before running any FIS experiment, establish what "normal" looks like (baseline 5XX rate, p99 latency, RDS connection count). Without a steady-state baseline, you cannot tell whether what you observe during the experiment is the failure or a pre-existing condition.
- **FIS stop conditions act as safety brakes:** A stop condition linked to a CloudWatch alarm automatically halts the experiment if impact exceeds a threshold. Always configure a stop condition — it prevents a lab experiment from cascading into a prolonged outage.
- **Route 53 TTL is the irreducible floor for DNS failover speed:** Even with 10-second health check intervals, a client that cached the DNS response 5 seconds ago will continue using the unhealthy IP for up to TTL seconds. Low TTL (60s) on health-check-associated records is essential for fast DNS-level failover.
