# Verification & Validation — Project 10.5 Production-grade Microservices Platform

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| ECS Services | ECS → Clusters → handson-cluster | Order Service, User Service running (desired = running) |
| API Gateway | API Gateway → APIs | `handson-platform-api` deployed |
| CloudFront | CloudFront → Distributions | Distribution Status = **Deployed** |
| WAF | WAF → Web ACLs | Associated with CloudFront distribution |
| Kinesis Stream | Kinesis → Data Streams | `handson-platform-events` Active |
| ElastiCache | ElastiCache → Clusters | Redis cluster Available |
| RDS (Orders) | RDS → Databases | `handson-orders-db` Available |
| RDS (Users) | RDS → Databases | `handson-users-db` Available |
| GuardDuty | GuardDuty → Summary | Enabled |
| X-Ray | X-Ray → Service Map | All services visible |

📸 Screenshot: ECS cluster with all services running  
📸 Screenshot: X-Ray Service Map showing full platform topology  
📸 Screenshot: `platform_health.py` output showing ALL SYSTEMS HEALTHY

---

## 2. AWS CLI Verification

```bash
# 2.1 Check all ECS services are healthy
aws ecs describe-services \
  --cluster handson-cluster \
  --services order-service user-service \
  --query "services[*].{Name:serviceName,Desired:desiredCount,Running:runningCount,Status:status}"
# Expected: all services Running == Desired

# 2.2 Check API Gateway deployment
aws apigateway get-rest-apis \
  --query "items[?name=='handson-platform-api'].{Name:name,Id:id}"
# Expected: API listed

API_ID=$(aws apigateway get-rest-apis \
  --query "items[?name=='handson-platform-api'].id" --output text)
aws apigateway get-stages \
  --rest-api-id $API_ID \
  --query "item[*].{Stage:stageName,Deployed:deploymentId}"
# Expected: prod stage deployed

# 2.3 Check CloudFront distribution
aws cloudfront list-distributions \
  --query "DistributionList.Items[*].{Domain:DomainName,Status:Status,Origins:Origins.Items[0].DomainName}"
# Expected: Status=Deployed

# 2.4 Check ElastiCache Redis
aws elasticache describe-cache-clusters \
  --query "CacheClusters[?contains(CacheClusterId,'handson')].{Id:CacheClusterId,Status:CacheClusterStatus,Engine:Engine}"
# Expected: Status=available, Engine=redis

# 2.5 Check Kinesis stream
aws kinesis describe-stream-summary \
  --stream-name handson-platform-events \
  --query "StreamDescriptionSummary.{Status:StreamStatus,Shards:OpenShardCount}"
# Expected: Status=ACTIVE

# 2.6 Check both RDS instances
for DB in handson-orders-db handson-users-db; do
  STATUS=$(aws rds describe-db-instances \
    --db-instance-identifier $DB \
    --query "DBInstances[0].DBInstanceStatus" --output text 2>/dev/null)
  echo "$DB: $STATUS"
done
# Expected: both available

# 2.7 Test API Gateway endpoint
CF_DOMAIN=$(aws cloudfront list-distributions \
  --query "DistributionList.Items[0].DomainName" --output text)
curl -s -o /dev/null -w "%{http_code}" https://$CF_DOMAIN/api/health
# Expected: 200

# 2.8 Run platform health check
python code/platform_health.py
# Expected: ALL SYSTEMS HEALTHY
```

---

## 3. Terraform State Verification

```bash
cd terraform

terraform state list | wc -l
# Expected: large number of resources (50+)

# Key resources to spot-check
terraform state show aws_ecs_service.order_service
# Shows: desired_count, task_definition, load_balancer

terraform state show aws_elasticache_cluster.redis
# Shows: cluster_id, engine=redis, node_type

terraform output api_gateway_url
# Expected: https://xxx.execute-api.us-east-1.amazonaws.com/prod

terraform output cloudfront_domain
# Expected: xxx.cloudfront.net

terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

---

## 4. Health Check — Full Platform Validation

```bash
# Run comprehensive platform health check
python code/platform_health.py

# Expected output:
# === Platform Health Dashboard ===
# ECS Services:
#   ✅ order-service:  2/2 tasks running
#   ✅ user-service:   2/2 tasks running
#
# Databases:
#   ✅ handson-orders-db: available
#   ✅ handson-users-db:  available
#
# Cache:
#   ✅ handson-redis: available
#
# Streaming:
#   ✅ handson-platform-events: ACTIVE (1 shard)
#
# API Gateway:
#   ✅ handson-platform-api: 5xx rate = 0.0%
#
# Security:
#   ✅ GuardDuty: ENABLED
#   ✅ WAF: associated with CloudFront
#
# Overall: ALL SYSTEMS HEALTHY ✅

# Test end-to-end request flow
CF_DOMAIN=$(aws cloudfront list-distributions \
  --query "DistributionList.Items[0].DomainName" --output text)

# Health check
curl -s https://$CF_DOMAIN/api/health
# Expected: {"status": "healthy"}

# Create an order (tests order-service + RDS + Redis + Kinesis)
curl -s -X POST https://$CF_DOMAIN/api/orders \
  -H "Content-Type: application/json" \
  -d '{"product_id": "PROD-001", "quantity": 1, "customer_id": "CUST-001"}'
# Expected: {"order_id": "ORD-xxx", "status": "created"}
```

---

## 5. Expected Successful Outputs

**CLI — describe-services:**
```json
[
  { "Name": "order-service", "Desired": 2, "Running": 2, "Status": "ACTIVE" },
  { "Name": "user-service",  "Desired": 2, "Running": 2, "Status": "ACTIVE" }
]
```

**platform_health.py:**
```
Overall: ALL SYSTEMS HEALTHY ✅
ECS: 4/4 tasks running
RDS: 2/2 databases available
Cache: available
Kinesis: ACTIVE
API 5xx rate: 0.0%
```

**terraform output:**
```
api_gateway_url   = "https://xxx.execute-api.us-east-1.amazonaws.com/prod"
cloudfront_domain = "xxx.cloudfront.net"
```

---

## 6. Verification Checklist

- [ ] All ECS services: Running == Desired (order-service, user-service)
- [ ] API Gateway `handson-platform-api` deployed to prod stage
- [ ] CloudFront distribution Status = Deployed
- [ ] WAF associated with CloudFront
- [ ] ElastiCache Redis Status = available
- [ ] Kinesis stream `handson-platform-events` Status = ACTIVE
- [ ] RDS `handson-orders-db` Status = available
- [ ] RDS `handson-users-db` Status = available
- [ ] GuardDuty enabled
- [ ] X-Ray Service Map shows all services
- [ ] `curl https://<CF_DOMAIN>/api/health` returns 200
- [ ] `platform_health.py` prints ALL SYSTEMS HEALTHY
- [ ] `terraform plan` shows no changes
