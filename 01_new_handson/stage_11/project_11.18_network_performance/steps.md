# Steps — Project 11.18 Network Performance Optimization

## Phase 1 — Console

### 1.1 Create VPC and Subnet
- VPC: `vpc-11-18`, CIDR: `10.0.0.0/16`
- Public subnet: `public-11-18`, `10.0.1.0/24`
- IGW + route table

### 1.2 Create Cluster Placement Group
1. **EC2** → **Placement Groups** → **Create**
2. Name: `pg-cluster-11-18`
3. Strategy: **Cluster** (lowest latency, same rack)
4. Create

### 1.3 Launch Two EC2 Instances
- AMI: Amazon Linux 2023
- Instance type: `c5n.large` (network-optimized, ENA enabled)
- Placement group: `pg-cluster-11-18`
- Subnet: `public-11-18`
- Security group: allow SSH (22) + iperf3 (5201) from each other
- Both instances in the same placement group

### 1.4 Verify ENA is Enabled
```bash
# After launch, check ENA attribute
aws ec2 describe-instances --instance-ids <INSTANCE_ID> \
  --query "Reservations[0].Instances[0].EnaSupport"
# Expected: true
```

---

## Phase 2 — Baseline Measurement (Standard MTU 1500)

```bash
# SSH to both instances
ssh -i key.pem ec2-user@<EC2_A_PUBLIC_IP>
ssh -i key.pem ec2-user@<EC2_B_PUBLIC_IP>

# Install iperf3 on both
sudo yum install -y iperf3

# Check current MTU
ip link show eth0 | grep mtu
# Default: mtu 9001 (AWS sets jumbo frames by default within VPC)

# Check ENA driver
ethtool -i eth0 | grep driver
# Expected: driver: ena

# Check network interface stats
ethtool eth0 | grep -i speed
# Expected: Speed: 25000Mb/s (c5n.large)
```

---

## Phase 3 — Performance Tests

```bash
# ── On EC2-A (server): ──
iperf3 -s

# ── On EC2-B (client): ──

# Test 1: Single stream TCP throughput (baseline)
iperf3 -c <EC2_A_PRIVATE_IP> -t 30
# Record: Gbps throughput

# Test 2: Multi-stream TCP (saturate bandwidth)
iperf3 -c <EC2_A_PRIVATE_IP> -t 30 -P 8
# Record: total Gbps with 8 parallel streams

# Test 3: UDP throughput and packet loss
iperf3 -c <EC2_A_PRIVATE_IP> -u -b 10G -t 30
# Record: throughput, jitter, packet loss %

# Test 4: Latency measurement
ping -c 100 -i 0.01 <EC2_A_PRIVATE_IP> | tail -2
# Record: min/avg/max/mdev RTT

# Test 5: Jumbo frames verification
ping -c 5 -M do -s 8972 <EC2_A_PRIVATE_IP>
# -M do = don't fragment, -s 8972 = 9000 byte packet (8972 + 28 headers)
# Expected: success (jumbo frames working within VPC)

# Test 6: Compare with non-placement-group instance
# Launch a third EC2 WITHOUT placement group, repeat iperf3 tests
# Compare latency: placement group should be ~10-20% lower
```

---

## Phase 4 — Terraform

```bash
cd terraform && terraform init && terraform apply
```

---

## Phase 5 — Verify

```bash
# 1. Confirm ENA support on both instances
for ID in <EC2_A_ID> <EC2_B_ID>; do
  echo -n "Instance $ID ENA: "
  aws ec2 describe-instances --instance-ids $ID \
    --query "Reservations[0].Instances[0].EnaSupport" --output text
done
# Expected: True True

# 2. Confirm placement group assignment
aws ec2 describe-instances \
  --filters "Name=placement-group-name,Values=pg-cluster-11-18" \
  --query "Reservations[*].Instances[*].{ID:InstanceId,PG:Placement.GroupName,AZ:Placement.AvailabilityZone}"

# 3. Confirm MTU is 9001 (jumbo frames)
# From EC2:
ip link show eth0 | grep mtu
# Expected: mtu 9001

# 4. Confirm ENA driver
# From EC2:
ethtool -i eth0
# Expected: driver: ena

# 5. Run automated checker
python code/perf_checker.py --instance-a <EC2_A_ID> --instance-b <EC2_B_ID>
```

---

## Phase 6 — Test Results Documentation

```bash
# Record all results in notes/benchmark_results.md:

# Benchmark Results Template:
# Instance type: c5n.large
# Placement group: cluster
# ENA: enabled
# MTU: 9001

# Test 1 - Single stream TCP:
#   Throughput: X Gbps (expected: ~5-10 Gbps for c5n.large)

# Test 2 - Multi-stream TCP (8 parallel):
#   Throughput: X Gbps (expected: ~10-25 Gbps)

# Test 3 - UDP:
#   Throughput: X Gbps, Jitter: X ms, Loss: X%

# Test 4 - Latency (ping):
#   min/avg/max: X/X/X ms (expected: <0.1ms in cluster PG)

# Test 5 - Jumbo frames:
#   8972-byte ping: success/fail

# Test 6 - Without placement group:
#   Latency: X ms (compare with cluster PG)
```

### Verification Checklist
- [ ] Both EC2 instances in cluster placement group
- [ ] ENA support = true on both instances
- [ ] ENA driver (`ena`) confirmed via ethtool
- [ ] MTU = 9001 (jumbo frames) on both instances
- [ ] iperf3 single-stream throughput measured and recorded
- [ ] iperf3 multi-stream throughput measured and recorded
- [ ] Latency measured with ping (< 0.1ms expected in cluster PG)
- [ ] Jumbo frame ping (8972 bytes) succeeds
- [ ] Comparison with non-PG instance shows latency difference

---

## Teardown
```bash
terraform destroy
# c5n.large costs ~$0.108/hr — destroy after benchmarking
```
