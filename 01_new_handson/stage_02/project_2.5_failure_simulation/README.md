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

## Lessons Learned
- Always enable VPC Flow Logs — they show exactly what traffic is being blocked
- Systems Manager Session Manager is your lifeline when SSH is locked out
- CloudTrail shows every API call — essential for IAM debugging
- The most common real-world issues: wrong security group, wrong subnet, missing IAM permission
- Chaos engineering mindset: if you haven't broken it, you don't understand it
