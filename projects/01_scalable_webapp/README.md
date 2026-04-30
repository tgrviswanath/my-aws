# Project 01: Scalable Web Application

## Architecture

```
Internet
    ↓
Route 53 (DNS)
    ↓
CloudFront (CDN + WAF)
    ↓
ALB (Application Load Balancer)
    ↓
EC2 Auto Scaling Group (private subnets, 3 AZs)
    ↓
ElastiCache Redis (session store + query cache)
    ↓
RDS Aurora PostgreSQL (Multi-AZ)
    ↓
S3 (static assets, user uploads)
```

## Components

| Component | Service | Config |
|-----------|---------|--------|
| DNS | Route 53 | Latency routing + health checks |
| CDN | CloudFront | S3 origin + ALB origin |
| Load Balancer | ALB | HTTPS, HTTP→HTTPS redirect |
| Compute | EC2 t3.medium | ASG: min 2, max 20 |
| Cache | ElastiCache Redis r6g.large | 2 replicas |
| Database | Aurora PostgreSQL 15 | 1 writer + 2 readers |
| Storage | S3 | Static assets + uploads |
| Secrets | Secrets Manager | DB credentials |
| Monitoring | CloudWatch + X-Ray | Dashboards + tracing |

## Deployment

```bash
# 1. Deploy infrastructure
cd infrastructure/
terraform init
terraform plan -var-file=production.tfvars
terraform apply -var-file=production.tfvars

# 2. Deploy application
cd ../app/
docker build -t webapp:latest .
aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_REPO
docker tag webapp:latest $ECR_REPO/webapp:latest
docker push $ECR_REPO/webapp:latest

# 3. Update ECS service (or ASG with new AMI)
aws ecs update-service \
  --cluster production \
  --service webapp \
  --force-new-deployment
```

## Scaling Strategy

- **Horizontal**: ASG target tracking at 60% CPU
- **Database reads**: Aurora read replicas + ElastiCache
- **Static content**: CloudFront caches globally
- **Sessions**: Redis (not sticky sessions)

## Security

- WAF on CloudFront (OWASP Top 10 rules)
- ALB in public subnets, EC2 in private subnets
- RDS in isolated DB subnets
- Security groups chained: ALB → App → DB
- All data encrypted at rest (KMS) and in transit (TLS)
- Secrets Manager for credentials
- IMDSv2 enforced on EC2

## Cost Optimization

- Reserved Instances for EC2 and RDS (1-year)
- S3 Intelligent-Tiering for uploads
- CloudFront reduces origin data transfer
- Auto Scaling scales down during off-peak

## Estimated Monthly Cost (Production)

| Service | Cost |
|---------|------|
| EC2 (2x t3.medium, Reserved) | ~$50 |
| Aurora PostgreSQL (db.r6g.large Multi-AZ) | ~$200 |
| ElastiCache (cache.r6g.large) | ~$100 |
| ALB | ~$20 |
| CloudFront (1TB) | ~$85 |
| S3 (100GB) | ~$3 |
| NAT Gateway | ~$35 |
| **Total** | **~$493/month** |
