# Architecture — Project 10.4 Kubernetes on EKS

## EKS Cluster Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    EKS Cluster: handson-eks-cluster               │
│                                                                    │
│  Control Plane (AWS managed — $0.10/hr)                           │
│  ├── API Server                                                    │
│  ├── etcd (cluster state)                                         │
│  ├── Scheduler                                                     │
│  └── Controller Manager                                           │
│                                                                    │
│  Worker Nodes (EC2 t3.medium × 2)                                 │
│  ├── Node 1 (AZ-a)                                                │
│  │   ├── Pod: flask-api-xxx (0.1 vCPU, 128 MB)                   │
│  │   └── Pod: flask-api-yyy (0.1 vCPU, 128 MB)                   │
│  └── Node 2 (AZ-b)                                                │
│      └── Pod: flask-api-zzz (0.1 vCPU, 128 MB)                   │
│                                                                    │
│  Namespaces:                                                       │
│  ├── production  ← app workloads                                  │
│  ├── monitoring  ← Prometheus, Grafana                            │
│  └── kube-system ← system components                              │
└──────────────────────────────────────────────────────────────────┘
```

## HPA Scaling Flow

```
Metrics Server collects CPU/memory from pods
    │
    ▼
HPA controller checks every 15 seconds:
  current CPU utilization = 85%
  target CPU utilization  = 70%
  desired replicas = ceil(3 × 85/70) = 4
    │
    ▼
HPA scales Deployment from 3 → 4 replicas
    │
    ▼
Scheduler places new pod on least-loaded node
    │
    ▼
Pod starts, passes readiness probe
    │
    ▼
Service routes traffic to new pod
```

## RBAC Model

```
ClusterRole: cluster-admin (full access)
    └── ClusterRoleBinding → admin users

Role: developer-read (namespace: production)
    └── RoleBinding → developer users
    └── Permissions: get, list, watch pods/services/deployments

Role: deployer (namespace: production)
    └── RoleBinding → CI/CD service account
    └── Permissions: update deployments, create pods
```

## Input / Output

### Input
| Type | Description | Example |
|------|-------------|---------|
| AWS Account | Active subscription | IAM user with required permissions |
| Configuration | Service settings | CIDR blocks, instance types, regions |
| Source Data | Application or data files | Docker images, SQL scripts, CSV files |

### Output
| Type | Description | Access |
|------|-------------|--------|
| AWS Resources | Deployed infrastructure | AWS Console or CLI |
| Service Endpoints | HTTP/HTTPS URLs, connection strings | Resource overview |
| CloudWatch Logs | Execution and audit trail | CloudWatch Log groups |
| Metrics | Performance data | CloudWatch Metrics |

## Key Concepts
| Concept | Explanation |
|---------|-------------|
| IAM Role | AWS identity for services â€” no static credentials |
| Security Group | Virtual firewall for EC2/RDS â€” stateful |
| VPC | Isolated network â€” your private AWS cloud |
| Region | Geographic AWS datacenter location |
| Availability Zone | Isolated datacenters within a region |
| CloudWatch | AWS monitoring and logging service |
| Free Tier | AWS free usage limits per service per month |
