# Project 5.2 — Cost Estimate: Multi-Container Local Stack

## Free Tier

This project runs **entirely on your local machine** using Docker Compose. There are no AWS resources created and therefore no AWS costs.

| Component | Cost |
|-----------|------|
| Docker Desktop (personal use) | Free |
| PostgreSQL (Docker image) | Free |
| Redis (Docker image) | Free |
| Node.js (Docker image) | Free |
| Local disk usage (~500MB for images) | Free |
| **Total AWS Cost** | **$0.00** |

---

## Pricing Breakdown

### If Running Locally

| Resource | Cost |
|----------|------|
| Compute (your laptop/desktop CPU) | $0.00 (your electricity bill) |
| Storage (Docker volumes) | $0.00 (local disk) |
| Network | $0.00 (loopback only) |

### If You Later Move to AWS (Reference)

When you graduate this stack to AWS (Project 5.4 covers ECS Fargate):

| AWS Service | Replaces | Approximate Cost |
|-------------|----------|-----------------|
| ECS Fargate (2 tasks) | Docker Compose backend | ~$20-40/month |
| RDS PostgreSQL db.t3.micro | postgres container | ~$15-25/month |
| ElastiCache Redis cache.t3.micro | redis container | ~$12/month |
| ALB | Port forwarding | ~$16/month |
| **Total AWS equivalent** | | **~$65-95/month** |

---

## Total

| Scenario | Monthly Cost |
|----------|-------------|
| Local Docker Compose (this project) | **$0.00** |
| AWS ECS + RDS + ElastiCache equivalent | **~$65-95/month** |

---

## Cleanup

Since everything is local, cleanup means stopping and optionally removing containers and volumes:

```bash
# Stop containers (preserves volumes)
docker compose stop

# Remove containers and network (preserves volumes)
docker compose down

# Full cleanup including all data
docker compose down -v

# Remove images to reclaim disk space
docker rmi project_5.2_multi_container-backend 2>/dev/null || true
docker rmi postgres:16-alpine redis:7-alpine node:20-alpine 2>/dev/null || true

# Prune unused Docker resources
docker system prune -f
```

After cleanup: **$0.00/month** ongoing cost (same as before, since this is all local).

---

## Cost Tips

- Docker Desktop is free for personal and small business use (< $10M revenue or < 250 employees)
- For CI/CD testing of multi-container apps, GitHub Actions provides 2000 free minutes/month
- When moving to production, consider RDS vs self-managed PostgreSQL on EC2 — RDS costs more but reduces operational burden
- ElastiCache is more expensive than self-managed Redis but provides HA, failover, and backups automatically
