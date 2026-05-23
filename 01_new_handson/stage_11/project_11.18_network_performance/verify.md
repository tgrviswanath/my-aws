# Verification & Validation — Project 11.18 Network Performance Optimization

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| Placement Group | EC2 → Placement Groups | `pg-cluster-11-18`, Strategy = Cluster |
| EC2-A | EC2 → Instances | `c5n.large`, Placement group = `pg-cluster-11-18` |
| EC2-B | EC2 → Instances | `c5n.large`, Placement group = `pg-cluster-11-18` |
| ENA Support | Instance details | ENA support = **enabled** |
| Network Interface | EC2 → Network Interfaces | ENI attached, ENA driver |

📸 Screenshot: Both instances showing placement group = `pg-cluster-11-18`  
📸 Screenshot: iperf3 multi-stream output showing throughput in Gbps  
📸 Screenshot: ping output showing sub-millisecond latency

---

## 2. AWS CLI Verification

```bash
# 2.1 Confirm ENA support on both instances
for ID in <EC2_A_ID> <EC2_B_ID>; do
  echo -n "Instance $ID ENA: "
  aws ec2 describe-instances --instance-ids $ID \
    --query "Reservations[0].Instances[0].EnaSupport" --output text
done
# Expected: True True

# 2.2 Confirm placement group assignment
aws ec2 describe-instances \
  --filters "Name=placement-group-name,Values=pg-cluster-11-18" \
  --query "Reservations[*].Instances[*].{ID:InstanceId,Type:InstanceType,PG:Placement.GroupName,AZ:Placement.AvailabilityZone}"
# Expected: 2 instances, both in pg-cluster-11-18, same AZ

# 2.3 Confirm placement group strategy
aws ec2 describe-placement-groups \
  --filters "Name=group-name,Values=pg-cluster-11-18" \
  --query "PlacementGroups[*].{Name:GroupName,Strategy:Strategy,State:State}"
# Expected: Strategy=cluster, State=available

# 2.4 From EC2 — confirm MTU and ENA driver
ssh -i key.pem ec2-user@<EC2_A_PUBLIC_IP>
ip link show eth0 | grep mtu
# Expected: mtu 9001 (jumbo frames)

ethtool -i eth0 | grep driver
# Expected: driver: ena

ethtool eth0 | grep Speed
# Expected: Speed: 25000Mb/s (c5n.large)
```

---

## 3. Terraform State Verification

```bash
cd terraform

terraform state list
# Expected:
# aws_placement_group.cluster
# aws_instance.ec2_a
# aws_instance.ec2_b
# aws_security_group.perf_test

terraform state show aws_placement_group.cluster
# Shows: name=pg-cluster-11-18, strategy=cluster

terraform state show aws_instance.ec2_a
# Shows: instance_type=c5n.large, placement_group=pg-cluster-11-18, ena_support=true

terraform plan
# Expected: No changes.
```

---

## 4. Performance Benchmark Results

Run all tests and record in `notes/benchmark_results.md`:

```bash
# On EC2-A (server):
iperf3 -s

# On EC2-B (client):

# Test 1: Single-stream TCP
iperf3 -c <EC2_A_PRIVATE_IP> -t 30
# Record: Gbps (expected: 5-10 Gbps for c5n.large)

# Test 2: Multi-stream TCP (8 parallel)
iperf3 -c <EC2_A_PRIVATE_IP> -t 30 -P 8
# Record: total Gbps (expected: 10-25 Gbps)

# Test 3: Latency
ping -c 100 -i 0.01 <EC2_A_PRIVATE_IP> | tail -1
# Record: min/avg/max ms (expected: < 0.1ms in cluster PG)

# Test 4: Jumbo frames
ping -c 5 -M do -s 8972 <EC2_A_PRIVATE_IP>
# Expected: success (9000-byte packets work within VPC)
```

---

## 5. Expected Successful Outputs

**ENA and MTU:**
```
driver: ena
mtu 9001
Speed: 25000Mb/s
```

**iperf3 single-stream:**
```
[ ID] Interval     Transfer     Bitrate
[  5] 0.00-30.00s  18.6 GBytes  5.33 Gbits/sec  sender
```

**iperf3 multi-stream (8 parallel):**
```
[SUM] 0.00-30.00s  75.2 GBytes  21.6 Gbits/sec  sender
```

**Latency (cluster placement group):**
```
round-trip min/avg/max/mdev = 0.048/0.062/0.089/0.008 ms
```

**Jumbo frame ping:**
```
64 bytes from 10.0.1.x: icmp_seq=1 ttl=64 time=0.07 ms
5 packets transmitted, 5 received, 0% packet loss
```

---

## 6. Verification Checklist

- [ ] Both EC2 instances in cluster placement group
- [ ] ENA support = true on both instances
- [ ] ENA driver (`ena`) confirmed via ethtool
- [ ] MTU = 9001 (jumbo frames) on both instances
- [ ] Instance speed = 25000Mb/s (c5n.large)
- [ ] iperf3 single-stream throughput measured and recorded
- [ ] iperf3 multi-stream throughput measured and recorded
- [ ] Latency < 0.1ms (cluster placement group)
- [ ] Jumbo frame ping (8972 bytes) succeeds
- [ ] Results saved to `notes/benchmark_results.md`
- [ ] `terraform plan` shows no changes
