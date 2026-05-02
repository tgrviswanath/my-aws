# High Availability, Fault Tolerance & Disaster Recovery

## Key Concepts

| Term | Definition | Target |
|------|-----------|--------|
| Availability | % time system is operational | 99.9% = 8.7hr/yr downtime |
| Fault Tolerance | Continue operating despite failures | Zero downtime |
| RPO (Recovery Point Objective) | Max acceptable data loss | Minutes to hours |
| RTO (Recovery Time Objective) | Max acceptable downtime | Minutes to hours |
| MTTR | Mean Time To Recovery | How fast you recover |
| MTBF | Mean Time Between Failures | How reliable the system is |

### Availability Nines

| Availability | Downtime/Year | Downtime/Month |
|-------------|--------------|----------------|
| 99% | 87.6 hours | 7.3 hours |
| 99.9% | 8.76 hours | 43.8 minutes |
| 99.95% | 4.38 hours | 21.9 minutes |
| 99.99% | 52.6 minutes | 4.4 minutes |
| 99.999% | 5.26 minutes | 26.3 seconds |

---

## Multi-AZ Architecture

```
Region: us-east-1
├── AZ-a (us-east-1a)
│   ├── EC2 instances (ASG)
│   ├── RDS Primary
│   ├── ElastiCache Primary
│   └── NAT Gateway
├── AZ-b (us-east-1b)
│   ├── EC2 instances (ASG)
│   ├── RDS Standby (Multi-AZ)
│   ├── ElastiCache Replica
│   └── NAT Gateway
└── AZ-c (us-east-1c)
    └── EC2 instances (ASG)

ALB spans all AZs → distributes traffic
Route 53 → ALB (single endpoint)
```

### Design Principles for HA

1. **Eliminate single points of failure** — every component in 2+ AZs
2. **Detect failures** — health checks, CloudWatch alarms
3. **Recover automatically** — ASG replaces failed instances, RDS Multi-AZ failover
4. **Decouple components** — SQS between services, async processing
5. **Design for failure** — assume any component can fail at any time

---

## Disaster Recovery Strategies

### 1. Backup & Restore (RPO: hours, RTO: hours)

```
Cost: $
Complexity: Low

Primary Region → S3 backups → Restore in DR region when needed
```

```bash
# Automated backup strategy
# RDS: automated backups + cross-region snapshot copy
aws rds copy-db-snapshot \
  --source-db-snapshot-identifier arn:aws:rds:us-east-1:123456789:snapshot:prod-daily \
  --target-db-snapshot-identifier prod-daily-dr \
  --region eu-west-1

# S3: Cross-Region Replication
# EBS: Copy snapshots to DR region
# AMIs: Copy to DR region
```

### 2. Pilot Light (RPO: minutes, RTO: 10-30 min)

```
Cost: $$
Complexity: Medium

Primary: Full production
DR:      Core services running (DB), compute off
         → Scale up compute when needed
```

```bash
# Keep RDS running in DR region (minimal instance)
# Keep AMIs current in DR region
# Pre-configure ASG with 0 desired capacity
# On disaster: update desired capacity, update DNS
aws autoscaling update-auto-scaling-group \
  --auto-scaling-group-name dr-asg \
  --desired-capacity 4 \
  --region eu-west-1

aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890 \
  --change-batch file://failover-to-dr.json
```

### 3. Warm Standby (RPO: seconds, RTO: minutes)

```
Cost: $$$
Complexity: High

Primary: Full production scale
DR:      Scaled-down but running version of production
         → Scale up quickly when needed
```

### 4. Multi-Site Active-Active (RPO: ~0, RTO: ~0)

```
Cost: $$$$
Complexity: Very High

Both regions serve traffic simultaneously
Route 53 latency routing or weighted routing
Aurora Global Database for data sync
```

```
Route 53 (latency routing)
├── us-east-1: ALB → ECS → Aurora Primary
└── eu-west-1: ALB → ECS → Aurora Secondary (read)

On us-east-1 failure:
→ Route 53 health check fails
→ All traffic routes to eu-west-1
→ Promote Aurora secondary to primary
```

---

## Multi-Region Architecture

```yaml
# Route 53 failover configuration
Primary:
  Region: us-east-1
  Record: app.example.com
  Type: A (Alias to ALB)
  Routing: Failover PRIMARY
  HealthCheck: ALB health endpoint

Secondary:
  Region: eu-west-1
  Record: app.example.com
  Type: A (Alias to ALB)
  Routing: Failover SECONDARY
  HealthCheck: ALB health endpoint
```

### Data Replication Strategies

```
S3:          Cross-Region Replication (CRR) — async, near real-time
RDS:         Cross-region read replica → promote on failover
Aurora:      Global Database — ~1s RPO, <1min RTO
DynamoDB:    Global Tables — multi-active, ~1s replication
ElastiCache: Manual backup/restore or Global Datastore (Redis)
```

---

## Chaos Engineering

Test your HA by intentionally introducing failures.

```bash
# AWS Fault Injection Simulator (FIS)
aws fis create-experiment-template \
  --description "Terminate random EC2 instance in ASG" \
  --targets '{
    "Instances": {
      "resourceType": "aws:ec2:instance",
      "resourceTags": {"aws:autoscaling:groupName": "prod-asg"},
      "selectionMode": "PERCENT(25)"
    }
  }' \
  --actions '{
    "TerminateInstances": {
      "actionId": "aws:ec2:terminate-instances",
      "targets": {"Instances": "Instances"}
    }
  }' \
  --stop-conditions '[{
    "source": "aws:cloudwatch:alarm",
    "value": "arn:aws:cloudwatch:us-east-1:123456789:alarm:high-error-rate"
  }]' \
  --role-arn arn:aws:iam::123456789:role/FISRole

# Run experiment
aws fis start-experiment \
  --experiment-template-id EXT123456789
```

---

## Health Check Design

```python
# Comprehensive health check endpoint
from flask import Flask, jsonify
import boto3
import redis
import psycopg2

app = Flask(__name__)

@app.route('/health')
def health():
    checks = {}
    status = 200
    
    # Database check
    try:
        conn = get_db_connection()
        conn.execute('SELECT 1')
        checks['database'] = 'healthy'
    except Exception as e:
        checks['database'] = f'unhealthy: {str(e)}'
        status = 503
    
    # Cache check
    try:
        r = get_redis_connection()
        r.ping()
        checks['cache'] = 'healthy'
    except Exception as e:
        checks['cache'] = f'unhealthy: {str(e)}'
        # Cache failure might not be critical
    
    # Downstream service check
    try:
        response = requests.get('http://payment-service/health', timeout=2)
        checks['payment_service'] = 'healthy' if response.ok else 'degraded'
    except Exception:
        checks['payment_service'] = 'unreachable'
    
    return jsonify({
        'status': 'healthy' if status == 200 else 'unhealthy',
        'checks': checks,
        'version': os.environ.get('APP_VERSION', 'unknown')
    }), status

@app.route('/ready')
def ready():
    # Readiness: is this instance ready to serve traffic?
    # Used by ALB/ECS health checks
    return jsonify({'status': 'ready'}), 200
```

---

## Interview Q&A

### Q1: What is the difference between High Availability and Fault Tolerance?
**High Availability**: System remains operational with minimal downtime. Achieved through redundancy and automatic failover. Some brief interruption may occur (seconds to minutes). Example: RDS Multi-AZ with ~1-2 min failover.
**Fault Tolerance**: System continues operating without interruption despite failures. No downtime. More expensive — requires full redundancy. Example: Multi-AZ ALB with multiple healthy instances — one fails, others continue serving traffic immediately.

### Q2: What is the difference between RPO and RTO?
**RPO (Recovery Point Objective)**: Maximum acceptable data loss measured in time. "How much data can we afford to lose?" RPO=1hr means you can lose up to 1 hour of data. Drives backup frequency.
**RTO (Recovery Time Objective)**: Maximum acceptable downtime. "How long can we be down?" RTO=30min means you must be back online within 30 minutes. Drives DR strategy choice.

### Q3: How would you design a system for 99.99% availability?
1. Multi-AZ deployment for all components (EC2 ASG, RDS Multi-AZ, ElastiCache Multi-AZ)
2. ALB across 3 AZs with health checks
3. Auto Scaling to replace failed instances
4. RDS Multi-AZ with automatic failover
5. Route 53 health checks with failover routing
6. CloudWatch alarms + automated remediation (Lambda)
7. Eliminate all single points of failure
8. Regular DR drills and chaos engineering
9. Circuit breakers for downstream dependencies

### Q4: What is the difference between the four DR strategies?
**Backup & Restore**: Cheapest, slowest. Hours of RTO/RPO. Good for non-critical systems.
**Pilot Light**: Core services (DB) always running in DR. Compute off. 10-30 min RTO. Good for important but not critical systems.
**Warm Standby**: Scaled-down production running in DR. Minutes RTO. Good for business-critical systems.
**Multi-Site Active-Active**: Both regions serve traffic. Near-zero RTO/RPO. Most expensive. Good for mission-critical systems.

### Q5: How does Aurora Global Database help with DR?
Aurora Global Database replicates data from primary region to up to 5 secondary regions with ~1 second lag (RPO ~1s). On primary region failure: promote a secondary region to primary in under 1 minute (RTO <1min). Secondary regions can serve reads, reducing latency for global users. Much better than RDS cross-region replicas which have higher replication lag and longer promotion time.
