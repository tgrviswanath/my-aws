# Verification & Validation — Project 11.3 Security Groups Deep Dive

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| ALB SG | EC2 → Security Groups | `alb-sg-11-3`, Inbound: 80+443 from `0.0.0.0/0` |
| Web SG | EC2 → Security Groups | `web-sg-11-3`, Inbound: 80 from `alb-sg-11-3` (SG reference, not CIDR) |
| App SG | EC2 → Security Groups | `app-sg-11-3`, Inbound: 8080 from `web-sg-11-3` |
| DB SG | EC2 → Security Groups | `db-sg-11-3`, Inbound: 3306 from `app-sg-11-3` only |
| Web EC2 | EC2 → Instances | Public subnet, `web-sg-11-3` attached |
| App EC2 | EC2 → Instances | Private subnet, `app-sg-11-3` attached |
| DB EC2 | EC2 → Instances | Private subnet, `db-sg-11-3` attached |

📸 Screenshot: DB SG inbound rules showing source = `app-sg-11-3` (not a CIDR)  
📸 Screenshot: Web SG inbound rules showing source = `alb-sg-11-3`

---

## 2. AWS CLI Verification

```bash
VPC_ID=<your-vpc-id>

# 2.1 List all 4 SGs
aws ec2 describe-security-groups \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query "SecurityGroups[*].{Name:GroupName,ID:GroupId}"

# 2.2 Inspect DB SG — must only allow from App SG, not from CIDR
aws ec2 describe-security-groups --group-ids $DB_SG \
  --query "SecurityGroups[0].IpPermissions[*].{Port:FromPort,Source:UserIdGroupPairs[0].GroupId,CIDR:IpRanges}"
# Expected: Source=app-sg-id, CIDR=null (no CIDR-based rules)

# 2.3 Inspect Web SG — must allow HTTP only from ALB SG
aws ec2 describe-security-groups --group-ids $WEB_SG \
  --query "SecurityGroups[0].IpPermissions[?FromPort==\`80\`].UserIdGroupPairs[0].GroupId"
# Expected: alb-sg-id

# 2.4 Connectivity test — from Web EC2
ssh -i key.pem ec2-user@<WEB_PUBLIC_IP>
curl http://<APP_PRIVATE_IP>:8080    # succeeds (web → app allowed)
nc -zv <DB_PRIVATE_IP> 3306          # fails (web → db blocked)

# 2.5 Connectivity test — from App EC2 (hop from web)
ssh -i key.pem ec2-user@<APP_PRIVATE_IP>
nc -zv <DB_PRIVATE_IP> 3306          # succeeds (app → db allowed)
nc -zv <WEB_PRIVATE_IP> 80           # fails (app → web blocked)
```

---

## 3. Terraform State Verification

```bash
cd terraform

terraform state list
# Expected:
# aws_security_group.alb
# aws_security_group.web
# aws_security_group.app
# aws_security_group.db
# aws_security_group_rule.web_from_alb
# aws_security_group_rule.app_from_web
# aws_security_group_rule.db_from_app

terraform state show aws_security_group.db
# Shows: ingress rules referencing app SG id, not a CIDR

terraform plan
# Expected: No changes.
```

---

## 4. Health Check

```bash
# Verify SG chaining is enforced — these must FAIL:
# From web EC2:
nc -zv <DB_PRIVATE_IP> 3306   # timeout — web cannot reach DB directly

# From internet:
nc -zv <APP_PRIVATE_IP> 8080  # timeout — app has no public access
nc -zv <DB_PRIVATE_IP> 3306   # timeout — DB has no public access
```

---

## 5. Expected Successful Outputs

**CLI — DB SG inbound rules:**
```json
[{ "Port": 3306, "Source": "sg-app-id", "CIDR": null }]
```

**Connectivity matrix:**
```
ALB → Web (80):   ✅ allowed
Web → App (8080): ✅ allowed
App → DB (3306):  ✅ allowed
Web → DB (3306):  ❌ blocked
Internet → App:   ❌ blocked
Internet → DB:    ❌ blocked
```

---

## 6. Verification Checklist

- [ ] 4 SGs created: alb, web, app, db
- [ ] Web SG allows HTTP only from ALB SG (SG reference, not `0.0.0.0/0`)
- [ ] App SG allows 8080 only from Web SG
- [ ] DB SG allows 3306 only from App SG
- [ ] Web EC2 can reach App EC2 on 8080
- [ ] Web EC2 cannot reach DB EC2 on 3306
- [ ] App EC2 can reach DB EC2 on 3306
- [ ] No direct internet access to App or DB EC2
- [ ] `terraform plan` shows no changes
