# Notes — Project 11.16

## DNS TTL is Critical
Set TTL to 60s on failover records. High TTL (e.g. 300s) means clients cache
the old IP for 5 minutes after failover — increasing effective RTO.

## Health Check Regions
Route 53 health checks are performed from multiple AWS regions globally.
The endpoint must be reachable from the internet (not behind a private ALB).

## Testing Failover Without Breaking Production
Use a separate subdomain for testing: `test.yourdomain.com`
Point it at the same ALB. Test failover on `test.` without affecting `app.`.

## Runbook Template
```
DR Activation Runbook:
1. Confirm primary is down (check health check status)
2. Scale up DR EC2 fleet (if warm standby)
3. Promote RDS read replica to primary in DR region
4. Update application config to point to DR RDS
5. Verify DR ALB health checks pass
6. Confirm DNS has switched (nslookup app.yourdomain.com)
7. Notify stakeholders
8. Monitor DR region metrics
```

## Common Mistake
Not testing DR regularly. DR that has never been tested will fail when needed.
Schedule quarterly DR drills — actually fail over and verify everything works.
