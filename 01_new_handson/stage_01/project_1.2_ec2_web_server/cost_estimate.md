# Cost Estimate — EC2 Web Server with Nginx

> **Region:** us-east-1 (US East - N. Virginia)
> **Scenario:** Single t2.micro instance running 24/7 with Elastic IP and 8 GB EBS

---

## Free Tier

AWS Free Tier for new accounts (first 12 months):

| Resource | Free Tier Allowance | Notes |
|----------|--------------------|----|
| EC2 t2.micro | 750 hours/month | Enough for 1 instance running 24/7 |
| EBS gp2/gp3 | 30 GB/month | Covers the 8 GB root volume |
| EBS I/O | 2,000,000 I/Os | Standard web traffic |
| Elastic IP | Free | When attached to a running instance |
| Data transfer out | 1 GB/month | To the internet |
| EC2 public IPv4 | 750 hours/month | Free tier applies to 1 address |

**Result during Free Tier:** ~$0.00/month if you stay within limits.

---

## Detailed Cost Breakdown

### EC2 Instance — t2.micro

| Period | Cost | Notes |
|--------|------|-------|
| Free Tier (months 1–12) | $0.00/month | 750 hrs/month free |
| After Free Tier | $0.0116/hour | On-demand, us-east-1 |
| After Free Tier (24/7) | **~$8.50/month** | 730 hrs × $0.0116 |

**Tip:** Use Savings Plans or Reserved Instances to reduce cost:
- 1-year Reserved Instance (t2.micro): ~$5.11/month (40% savings)
- Spot Instance (t2.micro): ~$0.003–0.005/hour (variable, can be interrupted)

---

### EBS Storage — 8 GB gp3

| Period | Cost | Notes |
|--------|------|-------|
| Free Tier (months 1–12) | $0.00/month | 30 GB gp2 free |
| After Free Tier (gp3) | $0.08/GB/month | 8 GB × $0.08 = **$0.64/month** |

---

### Elastic IP Address

| State | Cost |
|-------|------|
| Attached to a **running** instance | $0.00 |
| Attached to a **stopped** instance | $0.005/hour (~$3.60/month) |
| Not attached (unattached/idle) | $0.005/hour (~$3.60/month) |
| Additional IPs (beyond 1 per instance) | $0.005/hour each |

> ⚠️ **Important:** If you stop your instance and forget the Elastic IP, you'll be charged $0.005/hr. Always release the Elastic IP before stopping long-term.

---

### Data Transfer

| Transfer Type | Cost |
|---------------|------|
| Data IN to EC2 | Free |
| Data OUT to internet (first 1 GB/month) | Free (all tiers) |
| Data OUT to internet (next 9.999 TB) | $0.09/GB |
| Data between AWS services (same region) | Free |

**For a basic personal web server:** Data transfer cost is typically < $1/month.

---

### Public IPv4 Address (New Pricing — Feb 2024)

AWS now charges for all public IPv4 addresses, even if attached to running instances:

| Resource | Cost |
|----------|------|
| EC2 public IPv4 (free tier) | 750 hours/month free |
| EC2 public IPv4 (after free tier) | $0.005/hour (~$3.60/month) |
| Elastic IP on running instance | $0.005/hour (~$3.60/month) |

> After free tier, expect an additional ~$3.60/month for the public IPv4 address.

---

## Total Cost Summary

### During Free Tier (Months 1–12)

| Resource | Monthly Cost |
|----------|-------------|
| EC2 t2.micro | $0.00 |
| EBS 8 GB gp3 | $0.00 |
| Elastic IP (running) | $0.00 |
| Data transfer (< 1 GB out) | $0.00 |
| **Total** | **$0.00/month** |

### After Free Tier (Month 13+)

| Resource | Monthly Cost |
|----------|-------------|
| EC2 t2.micro (24/7) | $8.50 |
| EBS 8 GB gp3 | $0.64 |
| Elastic IP (running) | $3.60 |
| Data transfer (~5 GB out) | $0.36 |
| **Total** | **~$13.10/month** |

---

## Cost Optimization Tips

1. **Stop the instance when not in use** — EC2 charges stop when instance is stopped (EBS storage charges continue)
2. **Use Savings Plans** — commit to 1 year → ~40% discount
3. **Use Spot Instances** — up to 90% cheaper but can be interrupted; good for non-critical workloads
4. **Upgrade to t3.micro** — same cost, 10% better performance vs t2.micro
5. **Monitor with Cost Explorer** — AWS Console → Billing → Cost Explorer → set budget alerts

---

## Cleanup

When you're done with this project, delete all resources to stop charges:

### CLI Cleanup

```bash
# 1. Terminate the EC2 instance (stops per-hour charge)
aws ec2 terminate-instances --instance-ids <INSTANCE_ID>
aws ec2 wait instance-terminated --instance-ids <INSTANCE_ID>

# 2. Release the Elastic IP (stops IPv4 charge)
aws ec2 release-address --allocation-id <ALLOCATION_ID>

# 3. Delete the security group
aws ec2 delete-security-group --group-id <SG_ID>

# 4. Delete the key pair (optional — no cost)
aws ec2 delete-key-pair --key-name ec2-web-server-key
```

### Console Cleanup

1. EC2 → Instances → select `web-server-01` → Instance state → Terminate instance
2. EC2 → Elastic IPs → select your IP → Actions → Release Elastic IP address
3. EC2 → Security Groups → select `web-server-sg` → Actions → Delete security groups
4. EC2 → Key Pairs → select `ec2-web-server-key` → Actions → Delete

### Verify No Charges Remain

```bash
# Check no instances running
aws ec2 describe-instances \
  --filters "Name=instance-state-name,Values=running" \
  --query 'Reservations[].Instances[].InstanceId' \
  --output text

# Check no Elastic IPs allocated
aws ec2 describe-addresses --query 'Addresses[*].PublicIp' --output text
```

After cleanup, no further charges will accrue for this project.
