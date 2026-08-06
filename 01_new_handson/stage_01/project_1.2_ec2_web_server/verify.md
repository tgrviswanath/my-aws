# Verification & Validation — Project 1.2 Linux Web Server on EC2

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| EC2 Instance | EC2 → Instances | `web-server-01`, State = **running** |
| Instance Type | Instance details | `t3.micro` |
| Public IP | Instance details | Public IPv4 address assigned |
| Key Pair | Instance details | `ec2-lab-key` attached |
| Security Group | Instance → Security tab | `web-server-sg` — ports 80, 443, 22 |
| SG Inbound Rules | Security Groups → Inbound | SSH 22 = My IP only (not `0.0.0.0/0`) |
| User Data | Instance → Actions → View user data | Nginx install script present |

📸 Screenshot: EC2 instance showing State = running with public IP  
📸 Screenshot: Security group inbound rules showing SSH restricted to My IP  
📸 Screenshot: Browser showing Nginx page at the public IP

---

## 2. AWS CLI Verification

```bash
# 2.1 Instance running
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=web-server-01" "Name=instance-state-name,Values=running" \
  --query "Reservations[0].Instances[0].{ID:InstanceId,State:State.Name,IP:PublicIpAddress,Type:InstanceType}"
# Expected: State=running, Type=t3.micro, IP not null

# 2.2 Security group rules — SSH must NOT be open to 0.0.0.0/0
aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=web-server-sg" \
  --query "SecurityGroups[0].IpPermissions[?FromPort==\`22\`].IpRanges[*].CidrIp"
# Expected: your IP /32 — NOT 0.0.0.0/0

# 2.3 Nginx responds on port 80
PUBLIC_IP=$(aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=web-server-01" \
  --query "Reservations[0].Instances[0].PublicIpAddress" --output text)
curl -s http://$PUBLIC_IP | grep -i "hello\|nginx\|ec2"
# Expected: HTML response with instance content

# 2.4 Health endpoint
curl -s http://$PUBLIC_IP/health
# Expected: OK or {"status":"healthy"}

# 2.5 SSH connection works
ssh -i ~/Downloads/ec2-lab-key.pem -o ConnectTimeout=5 ec2-user@$PUBLIC_IP "echo SSH_OK"
# Expected: SSH_OK
```

---

## 3. Terraform State Verification

```bash
cd terraform

terraform state list
# Expected:
# aws_instance.web_server
# aws_security_group.web_server
# aws_key_pair.ec2_lab

terraform state show aws_instance.web_server
# Shows: instance_type=t3.micro, ami, public_ip, key_name=ec2-lab-key

terraform output instance_public_ip
# Expected: public IP address

terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

---

## 4. Health Check — From Inside EC2

```bash
ssh -i ~/Downloads/ec2-lab-key.pem ec2-user@$PUBLIC_IP

# Nginx running
systemctl status nginx
# Expected: active (running)

# Nginx config test
sudo nginx -t
# Expected: configuration file test is successful

# Reverse proxy working
curl http://localhost
# Expected: response from backend app

curl http://localhost/health
# Expected: OK

# SSH hardening confirmed
grep "PermitRootLogin" /etc/ssh/sshd_config
# Expected: PermitRootLogin no

grep "PasswordAuthentication" /etc/ssh/sshd_config
# Expected: PasswordAuthentication no
```

---

## 5. Expected Successful Outputs

**CLI — instance state:**
```json
{ "ID": "i-0abc123", "State": "running", "IP": "54.x.x.x", "Type": "t3.micro" }
```

**curl Nginx response:**
```html
<h1>Hello from EC2!</h1>
<p>Instance: ip-10-0-x-x.ec2.internal</p>
```

**curl /health:**
```
OK
```

**SSH hardening:**
```
PermitRootLogin no
PasswordAuthentication no
```

---

## 6. Verification Checklist

- [ ] EC2 instance state = running
- [ ] Instance type = t3.micro (free tier)
- [ ] Public IP assigned
- [ ] Key pair `ec2-lab-key` attached
- [ ] Security group: SSH 22 restricted to My IP only (not `0.0.0.0/0`)
- [ ] Security group: HTTP 80 and HTTPS 443 open to `0.0.0.0/0`
- [ ] `curl http://<PUBLIC_IP>` returns HTML response
- [ ] `curl http://<PUBLIC_IP>/health` returns OK
- [ ] SSH connection succeeds with key pair
- [ ] Nginx status = active (running) inside EC2
- [ ] `PermitRootLogin no` in sshd_config
- [ ] `PasswordAuthentication no` in sshd_config
- [ ] `terraform plan` shows no changes

---

## Section 1: Prerequisites Verified

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 1 | AWS CLI installed | ws --version returns 2.x | Download from aws.amazon.com/cli |
| 2 | Logged in | ws sts get-caller-identity returns JSON | Run ws configure |
| 3 | Correct region | ws configure get region returns us-east-1 | Run ws configure again |

`ash
aws sts get-caller-identity
aws configure list
`

## Section 2: Resources Created

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 4 | Primary resource | Status: Active/Running/Available | Re-run creation command |
| 5 | Configuration applied | Settings match intended values | Check resource details |
| 6 | Service responding | Expected response code/output | Check security groups and logs |

`ash
# Verify resources exist
aws ec2 describe-instances --query 'Reservations[*].Instances[*].{ID:InstanceId,State:State.Name}' --output table
`

## Section 3: Validation Complete

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 7 | End-to-end test | Correct output from service | Check CloudWatch Logs |
| 8 | No errors in logs | Zero error entries | Review CloudWatch Log groups |

## Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| AccessDenied error | Missing IAM permissions | Add required policy to IAM user/role |
| Resource not found | Wrong region or name | Check ws configure get region |
| Timeout connecting | Security group blocking | Add inbound rule for required port |
| Quota exceeded | Service limit reached | Request limit increase or use different region |
| Authentication failure | Expired credentials | Run ws configure with fresh access keys |
