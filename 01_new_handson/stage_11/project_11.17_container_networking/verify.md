# Verification & Validation — Project 11.17 Container Networking (ECS/EKS)

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| ECS Cluster | ECS → Clusters | `cluster-11-17`, Status = **ACTIVE** |
| Web Service | ECS → Clusters → Services | `svc-web-11-17`, Running = Desired (2/2) |
| API Service | ECS → Clusters → Services | `svc-api-11-17`, Running = Desired (2/2) |
| Task ENIs | ECS → Tasks → Networking tab | Each task has a VPC IP (awsvpc mode) |
| ALB Target Group | EC2 → Target Groups | `tg-web-11-17`, all targets = healthy |
| Cloud Map | Cloud Map → Services | `web.local` and `api.local` with task IPs registered |

📸 Screenshot: ECS cluster showing both services with running count = desired count  
📸 Screenshot: Task networking tab showing private VPC IP (awsvpc mode)  
📸 Screenshot: Cloud Map service instances showing task IPs

---

## 2. AWS CLI Verification

```bash
CLUSTER=cluster-11-17

# 2.1 Cluster status
aws ecs describe-clusters --clusters $CLUSTER \
  --query "clusters[*].{Name:clusterName,Status:status,ActiveServices:activeServicesCount,RunningTasks:runningTasksCount}"
# Expected: Status=ACTIVE, ActiveServices=2

# 2.2 Services running count = desired count
aws ecs describe-services \
  --cluster $CLUSTER \
  --services svc-web-11-17 svc-api-11-17 \
  --query "services[*].{Name:serviceName,Status:status,Running:runningCount,Desired:desiredCount}"
# Expected: Running=Desired for both services

# 2.3 Tasks have VPC IPs (awsvpc mode)
TASK_ARN=$(aws ecs list-tasks --cluster $CLUSTER \
  --service-name svc-web-11-17 --query "taskArns[0]" --output text)
aws ecs describe-tasks --cluster $CLUSTER --tasks $TASK_ARN \
  --query "tasks[0].attachments[?type=='ElasticNetworkInterface'].details[?name=='privateIPv4Address'].value"
# Expected: IP in 10.0.x.x range

# 2.4 Cloud Map service discovery
aws servicediscovery discover-instances \
  --namespace-name local \
  --service-name web \
  --query "Instances[*].Attributes.AWS_INSTANCE_IPV4"
# Expected: 2 IPs (one per web task)

# 2.5 ALB target health
TG_ARN=$(aws elbv2 describe-target-groups --names tg-web-11-17 \
  --query "TargetGroups[0].TargetGroupArn" --output text)
aws elbv2 describe-target-health --target-group-arn $TG_ARN \
  --query "TargetHealthDescriptions[*].{IP:Target.Id,Health:TargetHealth.State}"
# Expected: all healthy

# 2.6 ALB responds
ALB_DNS=$(aws elbv2 describe-load-balancers --names alb-11-17 \
  --query "LoadBalancers[0].DNSName" --output text)
curl http://$ALB_DNS
# Expected: nginx response
```

---

## 3. Terraform State Verification

```bash
cd terraform

terraform state list
# Expected:
# aws_ecs_cluster.main
# aws_ecs_task_definition.web
# aws_ecs_task_definition.api
# aws_ecs_service.web
# aws_ecs_service.api
# aws_service_discovery_private_dns_namespace.local
# aws_service_discovery_service.web
# aws_service_discovery_service.api
# aws_lb.main
# aws_lb_target_group.web

terraform state show aws_ecs_service.web
# Shows: network_configuration.assign_public_ip=DISABLED, launch_type=FARGATE

terraform plan
# Expected: No changes.
```

---

## 4. Health Check — Service Discovery

```bash
# Exec into a running web task and test service discovery
TASK_ARN=$(aws ecs list-tasks --cluster $CLUSTER \
  --service-name svc-web-11-17 --query "taskArns[0]" --output text)

aws ecs execute-command \
  --cluster $CLUSTER \
  --task $TASK_ARN \
  --container web \
  --interactive \
  --command "/bin/sh"

# Inside container:
nslookup api.local          # resolves to api task IPs
curl http://api.local:8080  # succeeds
nc -zv <api-task-ip> 80     # fails (SG blocks port 80 from web to api)
```

---

## 5. Expected Successful Outputs

**ECS services:**
```json
[
  { "Name": "svc-web-11-17", "Status": "ACTIVE", "Running": 2, "Desired": 2 },
  { "Name": "svc-api-11-17", "Status": "ACTIVE", "Running": 2, "Desired": 2 }
]
```

**Cloud Map instances:**
```json
["10.0.3.x", "10.0.4.x"]   ← task IPs registered automatically
```

**Service discovery from inside container:**
```
nslookup api.local → 10.0.3.x, 10.0.4.x
curl http://api.local:8080 → nginx response ✅
nc -zv <api-ip> 80 → Connection refused ✅ (SG enforced)
```

---

## 6. Verification Checklist

- [ ] ECS cluster status = ACTIVE
- [ ] Web service: 2 running tasks, running = desired
- [ ] API service: 2 running tasks, running = desired
- [ ] Each task has a VPC IP (awsvpc mode confirmed)
- [ ] Cloud Map shows task IPs for `web.local` and `api.local`
- [ ] ALB target group: all targets healthy
- [ ] `curl http://<ALB_DNS>` returns nginx response
- [ ] `nslookup api.local` from web task returns api task IPs
- [ ] `curl http://api.local:8080` from web task succeeds
- [ ] Tasks have no public IPs (private subnet confirmed)
- [ ] SG enforcement: web cannot reach api on port 80
- [ ] `terraform plan` shows no changes
