# Steps — Project 11.14 AWS Network Firewall

## Phase 1 — Console

### 1.1 Create VPC with 3 Subnets
- VPC: `vpc-11-14`, CIDR: `10.0.0.0/16`
- Public subnet: `public-11-14`, `10.0.1.0/24` (for IGW traffic)
- Firewall subnet: `firewall-11-14`, `10.0.2.0/24` (firewall endpoint lives here)
- Private subnet: `private-11-14`, `10.0.3.0/24` (EC2 instances)
- IGW: `igw-11-14`

### 1.2 Create Firewall Rule Groups

**Stateless Rule Group** (`stateless-rg-11-14`):
1. **VPC** → **Network Firewall** → **Network Firewall rule groups** → **Create**
2. Type: Stateless
3. Capacity: 100
4. Rules:
   - Priority 1: Allow TCP 443 from 10.0.3.0/24 to any → Forward to stateful
   - Priority 2: Allow TCP 80 from 10.0.3.0/24 to any → Forward to stateful
   - Default: Drop

**Stateful Rule Group** (`stateful-domain-11-14`):
1. Type: Stateful, Domain list
2. Domain list type: Deny list
3. Domains: `*.malware-test.com`, `*.blocked-site.com`
4. Protocol: HTTP, HTTPS

### 1.3 Create Firewall Policy
1. Name: `policy-11-14`
2. Add stateless rule group: `stateless-rg-11-14`
3. Add stateful rule group: `stateful-domain-11-14`
4. Default stateless action: Drop

### 1.4 Create Network Firewall
1. **VPC** → **Network Firewall** → **Network firewalls** → **Create**
2. Name: `nfw-11-14`
3. VPC: `vpc-11-14`
4. Subnet: `firewall-11-14`
5. Policy: `policy-11-14`
6. Create (takes ~5 minutes)
7. Note the **Firewall endpoint ID** (vpce-xxx) after creation

### 1.5 Configure Route Tables

**IGW Route Table** (new — attach to IGW):
- Route: `10.0.3.0/24 → <firewall-endpoint-id>`

**Firewall Subnet Route Table**:
- Route: `0.0.0.0/0 → igw-11-14`

**Private Subnet Route Table**:
- Route: `0.0.0.0/0 → <firewall-endpoint-id>`

---

## Phase 2 — AWS CLI

```bash
VPC_ID=<vpc-id>
FIREWALL_SUBNET=<firewall-subnet-id>

# Create stateless rule group
aws network-firewall create-rule-group \
  --rule-group-name stateless-rg-11-14 \
  --type STATELESS \
  --capacity 100 \
  --rule-group '{
    "RulesSource": {
      "StatelessRulesAndCustomActions": {
        "StatelessRules": [{
          "Priority": 1,
          "RuleDefinition": {
            "MatchAttributes": {
              "Sources": [{"AddressDefinition": "10.0.3.0/24"}],
              "Protocols": [6],
              "DestinationPorts": [{"FromPort": 443, "ToPort": 443}]
            },
            "Actions": ["aws:forward_to_sfe"]
          }
        }]
      }
    }
  }'

# Create firewall policy
POLICY_ARN=$(aws network-firewall create-firewall-policy \
  --firewall-policy-name policy-11-14 \
  --firewall-policy '{
    "StatelessDefaultActions": ["aws:drop"],
    "StatelessFragmentDefaultActions": ["aws:drop"]
  }' \
  --query "FirewallPolicyResponse.FirewallPolicyArn" --output text)

# Create firewall
aws network-firewall create-firewall \
  --firewall-name nfw-11-14 \
  --firewall-policy-arn $POLICY_ARN \
  --vpc-id $VPC_ID \
  --subnet-mappings SubnetId=$FIREWALL_SUBNET
```

---

## Phase 3 — Terraform

```bash
cd terraform && terraform init && terraform apply
```

---

## Phase 4 — Verify

```bash
# 1. Check firewall status
aws network-firewall describe-firewall \
  --firewall-name nfw-11-14 \
  --query "Firewall.{Name:FirewallName,Status:FirewallStatus.Status}"
# Expected: READY

# 2. Get firewall endpoint ID
ENDPOINT_ID=$(aws network-firewall describe-firewall \
  --firewall-name nfw-11-14 \
  --query "FirewallStatus.SyncStates.*.Attachment.EndpointId" \
  --output text)
echo "Firewall endpoint: $ENDPOINT_ID"

# 3. Verify route tables point to firewall endpoint
aws ec2 describe-route-tables \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query "RouteTables[*].{Name:Tags[?Key=='Name']|[0].Value,Routes:Routes[*].{Dest:DestinationCidrBlock,Target:VpcEndpointId}}"

# 4. Check firewall policy is attached
aws network-firewall describe-firewall-policy \
  --firewall-policy-name policy-11-14 \
  --query "FirewallPolicyResponse.{Name:FirewallPolicyName,Status:FirewallPolicyStatus}"
```

---

## Phase 5 — Test

```bash
# SSH to private EC2 (via SSM or bastion)

# Test 1: Allowed traffic — HTTPS to a permitted site
curl -s --max-time 10 https://aws.amazon.com
# Expected: success (not in block list)

# Test 2: Blocked domain — should be dropped
curl -s --max-time 10 https://malware-test.com
# Expected: connection timeout (firewall drops it)

# Test 3: HTTP traffic
curl -s --max-time 10 http://example.com
# Expected: success (if HTTP allowed in rules)

# Test 4: Check firewall logs
aws logs get-log-events \
  --log-group-name /aws/network-firewall/nfw-11-14/flow \
  --log-stream-name <stream> \
  --limit 20
# Look for ALLOW and DROP records

# Test 5: Add a Suricata rule to block specific content
# In firewall policy, add stateful rule:
# alert http any any -> any any (msg:"Block test"; content:"blocked-keyword"; sid:1001;)
# Then: curl http://example.com/blocked-keyword
# Expected: connection dropped, alert in logs

# Test 6: Verify traffic path (traceroute)
traceroute 8.8.8.8
# Should show firewall endpoint as a hop

# Run automated checker
python code/nfw_checker.py --firewall-name nfw-11-14
```

### Verification Checklist
- [ ] Network Firewall status = READY
- [ ] Firewall endpoint ID obtained
- [ ] Private subnet route table: `0.0.0.0/0 → firewall endpoint`
- [ ] IGW route table: `10.0.3.0/24 → firewall endpoint`
- [ ] Firewall subnet route table: `0.0.0.0/0 → igw`
- [ ] Allowed HTTPS traffic passes through
- [ ] Blocked domain is dropped (connection timeout)
- [ ] Firewall logs show ALLOW and DROP records
- [ ] Suricata rule triggers alert for matching content

---

## Teardown
```bash
terraform destroy
# Network Firewall costs ~$0.395/hr — destroy immediately after lab
```
