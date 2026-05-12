# Architecture — Project 10.3 Cost Optimization Automation

## Automation Flow

```
EventBridge (daily at 8am UTC)
    │
    ▼
Lambda: handson-cost-optimizer
    │
    ├── Find idle EC2 (CPU < 5% for 7 days)
    │     └── Stop instances → save ~$15/instance/month
    │
    ├── Find unattached EBS volumes
    │     └── Report (manual deletion recommended)
    │
    ├── Find old snapshots (> 30 days)
    │     └── Report (manual deletion recommended)
    │
    └── Publish report to SNS → Email
```

## Cost Optimization Hierarchy

```
1. Right-size (biggest impact, free)
   EC2: use Compute Optimizer recommendations
   RDS: check CPU/memory utilization

2. Savings Plans (30-60% savings)
   Commit to $/hour spend for 1-3 years
   More flexible than Reserved Instances

3. Spot Instances (60-90% savings)
   For fault-tolerant workloads (batch, dev/test)
   ECS Fargate Spot, EMR Spot, EC2 Spot

4. Storage optimization
   S3 Intelligent-Tiering: auto-moves to cheaper tiers
   EBS: gp3 is 20% cheaper than gp2 with better performance
   Delete unattached volumes and old snapshots

5. Architecture optimization
   Lambda instead of EC2 for event-driven workloads
   Fargate instead of EC2 for containers (no idle cost)
   Serverless: pay only for what you use
```

## Cost Tagging Strategy

```
Required tags on ALL resources:
  Project     = handson
  Environment = dev | staging | prod
  Owner       = yourname
  ManagedBy   = terraform | console | cli

Benefits:
  Cost Explorer: filter by tag → see cost per project
  Budget alerts: per-project budget
  Chargeback: bill teams for their usage
```
