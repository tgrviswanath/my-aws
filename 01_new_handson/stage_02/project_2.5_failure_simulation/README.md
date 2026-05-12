# Project 2.5 — Failure Simulation Lab

## What This Does
Deliberately breaks things in your AWS environment to learn how to diagnose, troubleshoot, and recover from real-world failures. This is one of the most valuable projects in the roadmap.

## Failures Simulated

| Scenario | What Breaks | What You Learn |
|----------|------------|----------------|
| EC2 crash | Instance stops responding | ASG recovery, health checks |
| Security group lockout | Can't SSH or reach app | SG debugging, Systems Manager |
| Wrong route table | Private subnet loses internet | Route table troubleshooting |
| RDS connection failure | App can't reach database | Connection string, SG, subnet |
| Full disk on EC2 | Instance becomes unresponsive | Disk monitoring, EBS expansion |
| IAM permission denied | App can't access S3 | IAM debugging, CloudTrail |
| NAT Gateway deleted | Private instances lose internet | Routing, NAT recovery |

## Tools Used for Diagnosis
- CloudWatch Logs and Metrics
- VPC Flow Logs
- EC2 Systems Manager Session Manager
- AWS CloudTrail
- `ping`, `curl`, `telnet`, `traceroute` from EC2

## How to Run
```bash
# Deploy test environment first
cd terraform && terraform init && terraform apply -auto-approve

# Run chaos simulations (non-production only!)
pip install boto3
python code/chaos_simulator.py --action stop-ec2 --asg-name handson-asg
python code/chaos_simulator.py --action restore --rollback-file rollback_*.json
```

## Lessons Learned
- Always enable VPC Flow Logs — they show exactly what traffic is being blocked
- Systems Manager Session Manager is your lifeline when SSH is locked out
- CloudTrail shows every API call — essential for IAM debugging
- The most common real-world issues: wrong security group, wrong subnet, missing IAM permission
- Chaos engineering mindset: if you haven't broken it, you don't understand it

## Code

### `code/chaos_simulator.py` — Simulate failures to test resilience

> ⚠️ **WARNING: Only run in non-production environments!**

```bash
pip install boto3

# Simulate EC2 instance failure (stops a random instance in an ASG)
python code/chaos_simulator.py --action stop-ec2 --asg-name my-asg-name

# Simulate security group misconfiguration (removes all inbound rules)
python code/chaos_simulator.py --action block-sg --sg-id sg-0abc123def

# Simulate database failure (reboots RDS, triggers Multi-AZ failover if enabled)
python code/chaos_simulator.py --action simulate-db-fail --rds-id my-db-instance

# Restore all changes using the rollback file (auto-created by each action)
python code/chaos_simulator.py --action restore --rollback-file rollback_20240101_120000.json

# Skip confirmation prompt (for scripted use)
python code/chaos_simulator.py --action stop-ec2 --asg-name my-asg --yes
```

Safety features:
- Requires typing `yes` to confirm before any destructive action
- Automatically writes a `rollback_YYYYMMDD_HHMMSS.json` file after each action
- `--action restore` reads the rollback file and undoes all changes in reverse order
