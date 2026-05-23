# Architecture Notes — Project 11.16

## DR Strategies Compared
```
Pilot Light:
  DR region: only DB replica running
  On failover: start EC2, configure ALB (~30-60 min RTO)
  Cost: ~$5/month

Warm Standby (this project):
  DR region: minimal EC2 + ALB always running
  On failover: scale up EC2, DNS switches (~1-5 min RTO)
  Cost: ~$64/month

Active-Active:
  Both regions serve traffic simultaneously
  Route 53 weighted or latency routing
  On failure: remove failed region from DNS (~seconds RTO)
  Cost: ~$128/month
```

## Route 53 Failover Flow
```
Normal:
  DNS query → Route 53 → PRIMARY record (health check = healthy) → Primary ALB

Failure:
  Health check fails 3 times (30s) → PRIMARY marked unhealthy
  DNS query → Route 53 → SECONDARY record (no health check) → DR ALB
  TTL expires (60s) → clients get DR IP

Recovery:
  Health check passes 1 time → PRIMARY marked healthy
  DNS query → Route 53 → PRIMARY record again
```

## RTO/RPO for This Architecture
| Metric | Value | Notes |
|--------|-------|-------|
| RTO | ~2 min | Health check (30s) + DNS TTL (60s) + client retry |
| RPO | ~5 min | RDS replication lag |
