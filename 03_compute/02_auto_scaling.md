# Auto Scaling Groups (ASG) — Deep Dive

## What is Auto Scaling?
Auto Scaling automatically adjusts the number of EC2 instances based on demand. It ensures you have the right number of instances to handle load — scaling out when demand increases, scaling in when it drops.

---

## Core Components

```
Auto Scaling Group
├── Launch Template (what to launch)
│   ├── AMI ID
│   ├── Instance type
│   ├── Security groups
│   ├── IAM role
│   └── User data
├── Min / Desired / Max capacity
├── Scaling Policies
├── Health checks
└── Lifecycle hooks
```

---

## Launch Templates vs Launch Configurations

| Feature | Launch Template | Launch Configuration |
|---------|----------------|---------------------|
| Versioning | ✅ Yes | ❌ No |
| Spot + On-Demand mix | ✅ Yes | ❌ No |
| T2/T3 Unlimited | ✅ Yes | ❌ No |
| Recommended | ✅ Yes | ❌ Legacy |

**Always use Launch Templates** — Launch Configurations are deprecated.

```bash
# Create Launch Template
aws ec2 create-launch-template \
  --launch-template-name web-lt \
  --version-description "v1" \
  --launch-template-data '{
    "ImageId": "ami-0c02fb55956c7d316",
    "InstanceType": "t3.micro",
    "SecurityGroupIds": ["sg-12345678"],
    "IamInstanceProfile": {"Name": "WebServerRole"},
    "UserData": "IyEvYmluL2Jhc2gKeXVtIHVwZGF0ZSAteQ=="
  }'
```

---

## Scaling Policies

### 1. Target Tracking (Recommended)
Automatically adjusts to maintain a target metric value.

```bash
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name my-asg \
  --policy-name cpu-target-tracking \
  --policy-type TargetTrackingScaling \
  --target-tracking-configuration '{
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ASGAverageCPUUtilization"
    },
    "TargetValue": 50.0,
    "ScaleInCooldown": 300,
    "ScaleOutCooldown": 60
  }'
```

### 2. Step Scaling
Scale by different amounts based on alarm breach size.

```bash
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name my-asg \
  --policy-name scale-out-steps \
  --policy-type StepScaling \
  --adjustment-type ChangeInCapacity \
  --step-adjustments '[
    {"MetricIntervalLowerBound": 0, "MetricIntervalUpperBound": 20, "ScalingAdjustment": 1},
    {"MetricIntervalLowerBound": 20, "MetricIntervalUpperBound": 40, "ScalingAdjustment": 2},
    {"MetricIntervalLowerBound": 40, "ScalingAdjustment": 4}
  ]'
```

### 3. Scheduled Scaling
Scale at known times (e.g., business hours).

```bash
aws autoscaling put-scheduled-update-group-action \
  --auto-scaling-group-name my-asg \
  --scheduled-action-name scale-up-morning \
  --recurrence "0 8 * * MON-FRI" \
  --min-size 4 --max-size 20 --desired-capacity 8

aws autoscaling put-scheduled-update-group-action \
  --auto-scaling-group-name my-asg \
  --scheduled-action-name scale-down-night \
  --recurrence "0 20 * * MON-FRI" \
  --min-size 1 --max-size 20 --desired-capacity 2
```

### 4. Predictive Scaling
Uses ML to forecast load and scale proactively.

```bash
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name my-asg \
  --policy-name predictive-scaling \
  --policy-type PredictiveScaling \
  --predictive-scaling-configuration '{
    "MetricSpecifications": [{
      "TargetValue": 50,
      "PredefinedMetricPairSpecification": {
        "PredefinedMetricType": "ASGCPUUtilization"
      }
    }],
    "Mode": "ForecastAndScale"
  }'
```

---

## Health Checks

| Type | What it checks | When to use |
|------|---------------|-------------|
| EC2 | Instance status checks | Always (default) |
| ELB | Load balancer health check | When behind ALB/NLB |
| Custom | Your own health endpoint | Complex app health |

```bash
# Set health check type
aws autoscaling update-auto-scaling-group \
  --auto-scaling-group-name my-asg \
  --health-check-type ELB \
  --health-check-grace-period 300
```

**Health check grace period**: Time after launch before health checks start. Set to at least your app startup time.

---

## Lifecycle Hooks

Pause instance launch/termination to run custom actions.

```
Launch: Pending → Pending:Wait → [your action] → Pending:Proceed → InService
Terminate: Terminating → Terminating:Wait → [your action] → Terminating:Proceed → Terminated
```

Use cases:
- **Launch hook**: Install software, register with service discovery, warm up cache
- **Terminate hook**: Drain connections, backup data, deregister from service mesh

```bash
# Create lifecycle hook
aws autoscaling put-lifecycle-hook \
  --auto-scaling-group-name my-asg \
  --lifecycle-hook-name launch-hook \
  --lifecycle-transition autoscaling:EC2_INSTANCE_LAUNCHING \
  --heartbeat-timeout 300 \
  --default-result CONTINUE \
  --notification-target-arn arn:aws:sqs:us-east-1:123456789:my-queue

# Complete lifecycle action (from your script)
aws autoscaling complete-lifecycle-action \
  --auto-scaling-group-name my-asg \
  --lifecycle-hook-name launch-hook \
  --lifecycle-action-result CONTINUE \
  --instance-id i-1234567890abcdef0
```

---

## Mixed Instances Policy (Spot + On-Demand)

```bash
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name mixed-asg \
  --min-size 2 --max-size 20 --desired-capacity 6 \
  --vpc-zone-identifier "subnet-aaa,subnet-bbb,subnet-ccc" \
  --mixed-instances-policy '{
    "LaunchTemplate": {
      "LaunchTemplateSpecification": {
        "LaunchTemplateName": "web-lt",
        "Version": "$Latest"
      },
      "Overrides": [
        {"InstanceType": "t3.medium"},
        {"InstanceType": "t3a.medium"},
        {"InstanceType": "t2.medium"}
      ]
    },
    "InstancesDistribution": {
      "OnDemandBaseCapacity": 2,
      "OnDemandPercentageAboveBaseCapacity": 25,
      "SpotAllocationStrategy": "capacity-optimized"
    }
  }'
```

This keeps 2 On-Demand always, then 25% On-Demand / 75% Spot for the rest.

---

## Warm Pools

Pre-initialize instances to reduce scale-out latency.

```bash
aws autoscaling put-warm-pool \
  --auto-scaling-group-name my-asg \
  --pool-state Stopped \
  --min-size 2
```

Instances in warm pool are pre-launched and stopped (cheaper than running). On scale-out, they start in seconds instead of minutes.

---

## CloudFormation Template

```yaml
AWSTemplateFormatVersion: '2010-09-09'

Resources:
  LaunchTemplate:
    Type: AWS::EC2::LaunchTemplate
    Properties:
      LaunchTemplateName: web-lt
      LaunchTemplateData:
        ImageId: ami-0c02fb55956c7d316
        InstanceType: t3.micro
        SecurityGroupIds:
          - !Ref WebSG
        IamInstanceProfile:
          Name: !Ref InstanceProfile
        UserData:
          Fn::Base64: |
            #!/bin/bash
            yum update -y
            yum install -y httpd
            systemctl start httpd

  AutoScalingGroup:
    Type: AWS::AutoScaling::AutoScalingGroup
    Properties:
      AutoScalingGroupName: web-asg
      MinSize: 2
      MaxSize: 20
      DesiredCapacity: 4
      LaunchTemplate:
        LaunchTemplateId: !Ref LaunchTemplate
        Version: !GetAtt LaunchTemplate.LatestVersionNumber
      VPCZoneIdentifier:
        - !Ref PrivateSubnet1
        - !Ref PrivateSubnet2
      TargetGroupARNs:
        - !Ref ALBTargetGroup
      HealthCheckType: ELB
      HealthCheckGracePeriod: 300
      Tags:
        - Key: Name
          Value: web-server
          PropagateAtLaunch: true

  ScalingPolicy:
    Type: AWS::AutoScaling::ScalingPolicy
    Properties:
      AutoScalingGroupName: !Ref AutoScalingGroup
      PolicyType: TargetTrackingScaling
      TargetTrackingConfiguration:
        PredefinedMetricSpecification:
          PredefinedMetricType: ASGAverageCPUUtilization
        TargetValue: 50.0
```

---

## Common Pitfalls

| Pitfall | Solution |
|---------|---------|
| Grace period too short | Set to app startup time + buffer |
| Scaling too aggressively | Use cooldown periods (300s scale-in) |
| All instances in one AZ | Spread across 3 AZs |
| Not using ELB health checks | Enable when behind load balancer |
| Terminating wrong instances | Use termination policies (OldestInstance, etc.) |
| Scale-in deletes stateful instances | Use lifecycle hooks to drain first |

---

## Interview Q&A

### Q1: What is the difference between horizontal and vertical scaling?
**Horizontal (scale out/in)**: Add/remove instances. Preferred for cloud — no downtime, unlimited scale, fault tolerant. ASG does this automatically.
**Vertical (scale up/down)**: Increase/decrease instance size. Requires downtime, has hardware limits. Use for databases that can't easily scale horizontally.

### Q2: How does Target Tracking scaling work?
You set a target metric value (e.g., 50% CPU). ASG continuously monitors the metric and automatically adds/removes instances to maintain that target. AWS manages the CloudWatch alarms internally. It's the simplest and most recommended policy — no need to define alarm thresholds manually.

### Q3: What is a cooldown period and why is it important?
Cooldown is a pause after a scaling activity before another can start. Prevents thrashing — without it, ASG might launch 10 instances, then immediately terminate 8 because the metric dropped. Scale-out cooldown should be short (60s) to respond quickly. Scale-in cooldown should be longer (300s) to avoid premature termination.

### Q4: How do you handle stateful applications with Auto Scaling?
1. Externalize state: store sessions in ElastiCache, data in RDS/DynamoDB
2. Use lifecycle hooks to drain connections before termination
3. Use ELB connection draining (deregistration delay)
4. Sticky sessions (not recommended for scale) or stateless design
5. Use EFS for shared file storage across instances

### Q5: What is the difference between desired, min, and max capacity?
**Min**: Minimum instances always running (floor). Never scale below this.
**Max**: Maximum instances allowed (ceiling). Never scale above this.
**Desired**: Current target number of instances. ASG maintains this count. Scaling policies change the desired capacity within min/max bounds.
