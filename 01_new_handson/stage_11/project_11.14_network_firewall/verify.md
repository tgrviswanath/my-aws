# Verification & Validation — Project 11.14 AWS Network Firewall

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| Network Firewall | VPC → Network Firewall → Firewalls | `nfw-11-14`, Status = **READY** |
| Firewall Endpoint | Firewall details → Endpoints | `vpce-xxx` in firewall subnet |
| Firewall Policy | Network Firewall → Policies | `policy-11-14`, attached to `nfw-11-14` |
| Stateless Rule Group | Network Firewall → Rule groups | `stateless-rg-11-14`, capacity used |
| Stateful Rule Group | Network Firewall → Rule groups | `stateful-domain-11-14`, domain list |
| Private RT | Route Tables → Routes | `0.0.0.0/0 → vpce-xxx` (firewall endpoint) |
| IGW RT | Route Tables → Routes | `10.0.3.0/24 → vpce-xxx` (return traffic via firewall) |

📸 Screenshot: Network Firewall showing Status = READY  
📸 Screenshot: Private subnet route table showing `0.0.0.0/0 → vpce-xxx`  
📸 Screenshot: Firewall logs showing ALLOW and DROP records

---

## 2. AWS CLI Verification

```bash
# 2.1 Firewall status
aws network-firewall describe-firewall \
  --firewall-name nfw-11-14 \
  --query "Firewall.{Name:FirewallName,Status:FirewallStatus.Status,Policy:FirewallPolicyArn}"
# Expected: Status=READY

# 2.2 Get firewall endpoint ID
ENDPOINT_ID=$(aws network-firewall describe-firewall \
  --firewall-name nfw-11-14 \
  --query "FirewallStatus.SyncStates.*.Attachment.EndpointId" \
  --output text)
echo "Firewall endpoint: $ENDPOINT_ID"

# 2.3 Verify route tables point to firewall endpoint
aws ec2 describe-route-tables \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query "RouteTables[*].{Name:Tags[?Key=='Name']|[0].Value,Routes:Routes[*].{Dest:DestinationCidrBlock,Target:VpcEndpointId}}"
# Private RT: 0.0.0.0/0 → vpce-xxx
# IGW RT: 10.0.3.0/24 → vpce-xxx

# 2.4 Firewall policy status
aws network-firewall describe-firewall-policy \
  --firewall-policy-name policy-11-14 \
  --query "FirewallPolicyResponse.{Name:FirewallPolicyName,Status:FirewallPolicyStatus}"
# Expected: Status=ACTIVE

# 2.5 Traffic tests from private EC2 (via SSM)
aws ssm start-session --target <INSTANCE_ID>
curl -s --max-time 10 https://aws.amazon.com   # allowed — succeeds
curl -s --max-time 10 https://malware-test.com  # blocked — timeout
```

---

## 3. Terraform State Verification

```bash
cd terraform

terraform state list
# Expected:
# aws_networkfirewall_firewall.main
# aws_networkfirewall_firewall_policy.main
# aws_networkfirewall_rule_group.stateless
# aws_networkfirewall_rule_group.stateful_domain
# aws_cloudwatch_log_group.firewall_flow
# aws_cloudwatch_log_group.firewall_alert

terraform state show aws_networkfirewall_firewall.main
# Shows: id, name, firewall_policy_arn, vpc_id, subnet_mapping

terraform plan
# Expected: No changes.
```

---

## 4. Health Check — Firewall Logs

```bash
# Check firewall flow logs
aws logs describe-log-groups \
  --log-group-name-prefix /aws/network-firewall/nfw-11-14
# Expected: flow and alert log groups exist

# Get recent flow log events
aws logs get-log-events \
  --log-group-name /aws/network-firewall/nfw-11-14/flow \
  --log-stream-name <stream> \
  --limit 10 \
  --query "events[*].message"
# Look for: "action":"allowed" and "action":"dropped" records

# Confirm blocked domain appears in alert logs
aws logs filter-log-events \
  --log-group-name /aws/network-firewall/nfw-11-14/alert \
  --filter-pattern "DROP" \
  --limit 5
```

---

## 5. Expected Successful Outputs

**CLI — firewall status:**
```json
{ "Name": "nfw-11-14", "Status": "READY", "Policy": "arn:aws:network-firewall:..." }
```

**Traffic test results:**
```
curl https://aws.amazon.com    → HTTP 200 ✅ (allowed)
curl https://malware-test.com  → curl: (28) Operation timed out ✅ (blocked by domain list)
```

**Firewall flow log record:**
```json
{ "firewall_name": "nfw-11-14", "availability_zone": "us-east-1a",
  "event": { "src_ip": "10.0.3.x", "dest_ip": "x.x.x.x", "proto": "TCP",
             "dest_port": 443, "action": "allowed" }}
```

---

## 6. Verification Checklist

- [ ] Network Firewall status = READY
- [ ] Firewall endpoint ID obtained
- [ ] Private subnet RT: `0.0.0.0/0 → firewall endpoint`
- [ ] IGW RT: `10.0.3.0/24 → firewall endpoint`
- [ ] Firewall subnet RT: `0.0.0.0/0 → igw`
- [ ] Allowed HTTPS traffic passes through
- [ ] Blocked domain is dropped (connection timeout)
- [ ] Firewall flow logs show ALLOW records
- [ ] Firewall alert logs show DROP records for blocked domains
- [ ] `terraform plan` shows no changes
