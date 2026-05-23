# Architecture Notes — Project 11.17

## awsvpc Network Mode
```
Traditional EC2 networking:
  Host EC2 → shared ENI → all containers share host IP
  SGs applied at host level

awsvpc mode (Fargate):
  Each task → own ENI → own VPC IP (10.0.x.x)
  SGs applied per-task
  Task is a first-class VPC citizen
```

## Cloud Map Service Discovery Flow
```
Task starts → registers with Cloud Map → DNS record created
  web.local → [10.0.3.5, 10.0.4.7]  (2 web tasks)
  api.local → [10.0.3.8, 10.0.4.12] (2 api tasks)

Task stops → deregisters → DNS record removed
  web.local → [10.0.4.7]  (1 remaining)
```

## Subnet IP Planning for Containers
Each Fargate task consumes 1 VPC IP.
A /24 subnet = 251 usable IPs = max 251 tasks per subnet.
For large clusters, use /22 or /21 subnets for private task subnets.

## EKS VPC CNI (for reference)
Same concept as awsvpc — each pod gets a VPC IP.
EKS uses the VPC CNI plugin which allocates ENIs and secondary IPs.
Max pods per node = (ENIs per instance × IPs per ENI) - 1
