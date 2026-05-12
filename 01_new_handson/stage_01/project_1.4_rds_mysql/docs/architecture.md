# Architecture — Project 1.4 RDS MySQL Deployment

## Diagram

```
┌──────────────────────────────────────────────────────┐
│                  AWS Region (us-east-1)               │
│                                                        │
│  ┌──────────────────────┐                             │
│  │  EC2 (bastion/app)   │                             │
│  │  app-sg              │                             │
│  │  MySQL client        │                             │
│  └──────────┬───────────┘                             │
│             │ port 3306 (from app-sg only)             │
│  ┌──────────▼───────────────────────────────────┐    │
│  │           RDS MySQL (db.t3.micro)             │    │
│  │  rds-sg: inbound 3306 from app-sg only        │    │
│  │  Private subnet — NOT publicly accessible     │    │
│  │  Multi-AZ: standby replica in AZ-b            │    │
│  │  Automated backups: 7-day retention           │    │
│  └──────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────┘
```

## Security Model

| Rule | Why |
|------|-----|
| RDS in private subnet | Never expose port 3306 to internet |
| SG allows only app-sg | Only app servers can connect |
| No public access | `publicly_accessible = false` |
| Encrypted storage | AES-256 at rest |
| Automated backups | 7-day retention for point-in-time recovery |

## Multi-AZ vs Read Replica

```
Multi-AZ:
  Primary (AZ-a) ──sync replication──► Standby (AZ-b)
  Automatic failover if primary fails (~60s)
  Use for: high availability

Read Replica:
  Primary ──async replication──► Read Replica
  Manual promotion required
  Use for: read scaling, analytics
```
