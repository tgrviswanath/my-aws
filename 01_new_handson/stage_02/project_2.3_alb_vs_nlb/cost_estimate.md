# Cost Estimate — Project 2.3: ALB vs NLB Comparison

## Architecture Summary
Application Load Balancer (L7) with 2 target groups and path-based routing rules + Network Load Balancer (L4) with TCP listener, both in us-east-1 for comparison testing.

---

## ⚠️ Important: No Free Tier for Load Balancers

Unlike Lambda, DynamoDB, and SQS — **Elastic Load Balancing has NO free tier** (the original Classic Load Balancer had a 15-day trial, but ALB/NLB do not). Every hour an ALB or NLB is running incurs charges.

**Recommendation:** Run this lab in a focused session (2–4 hours), then delete load balancers immediately when done.

---

## ALB Pricing

| Component | Rate | Notes |
|---|---|---|
| ALB fixed hourly rate | $0.0225/hour | Regardless of traffic |
| ALB LCU (Load Balancer Capacity Unit) | $0.008/LCU-hour | Billed at highest dimension |
| Monthly ALB fixed cost | ~$16.20/month (24h×30d×$0.0225) | If left running full month |

### LCU Dimensions (billed at whichever is highest)
| Dimension | Per LCU Rate | Typical Lab Value |
|---|---|---|
| New connections | 25 per second | < 25/s in lab |
| Active connections | 3,000 active | < 100 in lab |
| Processed bytes | 1 GB/hour | < 0.01 GB in lab |
| Rule evaluations | 1,000/second | < 100/s in lab |

> For a low-traffic lab, LCU charges are near zero — the $0.0225/hr fixed cost dominates.

---

## NLB Pricing

| Component | Rate | Notes |
|---|---|---|
| NLB fixed hourly rate | $0.006/hour | Per AZ × number of AZs used |
| NLB NLCU (Network Load Balancer Capacity Unit) | $0.006/NLCU-hour | Per AZ |
| 2 AZs fixed cost | $0.006 × 2 = $0.012/hour | If using 2 AZs |
| Monthly NLB (2 AZ, fixed only) | ~$8.64/month | If left running full month |

### NLCU Dimensions for NLB
| Dimension | Per NLCU | Lab Impact |
|---|---|---|
| New TCP flows | 800/second | Minimal in lab |
| Active TCP flows | 100,000 | < 100 in lab |
| Processed bytes | 1 GB/hour | < 0.01 GB in lab |

---

## Lab Session Cost Estimate

| Scenario | Duration | ALB Cost | NLB Cost | Total |
|---|---|---|---|---|
| Quick lab (2 hours) | 2h | 2 × $0.0225 = $0.045 | 2 × $0.012 = $0.024 | **~$0.07** |
| Half-day lab (4 hours) | 4h | 4 × $0.0225 = $0.090 | 4 × $0.012 = $0.048 | **~$0.14** |
| Full day (forgot to delete!) | 24h | 24 × $0.0225 = $0.54 | 24 × $0.012 = $0.29 | **~$0.83** |
| Full month (worst case) | 720h | $16.20 | $8.64 | **~$24.84** |

> 💡 **Key insight:** Delete load balancers immediately after the lab. A 4-hour session costs less than $0.15 total.

---

## Free Tier: None for ALB/NLB

| Service | Free Tier? | Alternative |
|---|---|---|
| Application Load Balancer | ❌ No free tier | Delete promptly after lab |
| Network Load Balancer | ❌ No free tier | Delete promptly after lab |
| Classic Load Balancer | ❌ Deprecated | Don't use |
| EC2 target instances | ✅ t2.micro free 750h/month (12mo) | Keep using t2.micro |
| CloudWatch metrics | ✅ Free basic metrics | No extra cost |

---

## Cost Comparison: ALB vs NLB for Production Workloads

| Traffic Level | ALB Monthly | NLB Monthly | Notes |
|---|---|---|---|
| Low (< 1M requests/month) | ~$16–18 | ~$9–10 | Fixed cost dominates |
| Medium (100M requests/month) | ~$20–25 | ~$12–15 | LCU/NLCU adds modestly |
| High (1B requests/month) | ~$35–50 | ~$20–30 | Capacity units significant |
| Very high (10B+) | Variable | Variable | Custom pricing at this scale |

---

## Cost Optimization Tips

1. **Multi-AZ strategy:** ALB is charged per-region (not per-AZ). NLB is charged per-AZ — using 2 AZs doubles the base cost.
2. **Consolidate listeners:** Multiple host/path rules share one ALB and one hourly charge.
3. **Use ALB access logs selectively:** S3 storage costs $0.023/GB — disable if not needed.
4. **Target group reuse:** One target group can be shared across multiple listeners/rules at no extra cost.

---

## Cleanup Commands

### Delete ALB and Associated Resources

```bash
# Get Load Balancer ARNs
ALB_ARN=$(aws elbv2 describe-load-balancers --names alb-lab-23 \
  --query "LoadBalancers[0].LoadBalancerArn" --output text)
NLB_ARN=$(aws elbv2 describe-load-balancers --names nlb-lab-23 \
  --query "LoadBalancers[0].LoadBalancerArn" --output text)

echo "ALB ARN: ${ALB_ARN}"
echo "NLB ARN: ${NLB_ARN}"

# Get and delete all listeners (ALB)
LISTENER_ARNS=$(aws elbv2 describe-listeners --load-balancer-arn ${ALB_ARN} \
  --query "Listeners[].ListenerArn" --output text)

for LISTENER in ${LISTENER_ARNS}; do
  # Delete non-default rules first
  RULES=$(aws elbv2 describe-rules --listener-arn ${LISTENER} \
    --query "Rules[?Priority!='default'].RuleArn" --output text)
  for RULE in ${RULES}; do
    aws elbv2 delete-rule --rule-arn ${RULE}
    echo "Deleted rule: ${RULE}"
  done
  # Delete listener
  aws elbv2 delete-listener --listener-arn ${LISTENER}
  echo "Deleted listener: ${LISTENER}"
done

# Delete NLB listeners
NLB_LISTENERS=$(aws elbv2 describe-listeners --load-balancer-arn ${NLB_ARN} \
  --query "Listeners[].ListenerArn" --output text)
for LISTENER in ${NLB_LISTENERS}; do
  aws elbv2 delete-listener --listener-arn ${LISTENER}
done

# Delete Load Balancers
aws elbv2 delete-load-balancer --load-balancer-arn ${ALB_ARN}
aws elbv2 delete-load-balancer --load-balancer-arn ${NLB_ARN}
echo "Load balancers deleted — billing stops immediately"

# Wait for deletion before deleting target groups
aws elbv2 wait load-balancers-deleted --load-balancer-arns ${ALB_ARN} ${NLB_ARN}

# Delete Target Groups
for TG_NAME in web-tg api-tg nlb-tcp-tg; do
  TG_ARN=$(aws elbv2 describe-target-groups --names ${TG_NAME} \
    --query "TargetGroups[0].TargetGroupArn" --output text 2>/dev/null)
  if [ "${TG_ARN}" != "None" ] && [ -n "${TG_ARN}" ]; then
    aws elbv2 delete-target-group --target-group-arn ${TG_ARN}
    echo "Deleted target group: ${TG_NAME}"
  fi
done

echo "=== Cleanup Complete ==="
```

### Verify Cleanup (No More Charges)
```bash
echo "=== Remaining Load Balancers (should be empty) ==="
aws elbv2 describe-load-balancers \
  --query "LoadBalancers[?contains(LoadBalancerName, 'lab-23')].{Name:LoadBalancerName,State:State.Code}" \
  --output text

echo "=== Remaining Target Groups (should be empty) ==="
aws elbv2 describe-target-groups \
  --query "TargetGroups[?contains(TargetGroupName, 'tg')].TargetGroupName" \
  --output text

echo "If both outputs empty, no more load balancer charges will accrue."
```

---

*Region: us-east-1 | Prices as of 2024 — verify at https://aws.amazon.com/elasticloadbalancing/pricing/*
