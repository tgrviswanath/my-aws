# Architecture Notes — Project 11.18

## ENA (Enhanced Networking) Stack
```
Application
    ↓
OS Network Stack
    ↓
ENA Driver (SR-IOV — bypasses hypervisor)
    ↓
Physical NIC on host
    ↓
AWS Network Fabric
```
Without ENA: traffic goes through hypervisor → adds latency.
With ENA: traffic bypasses hypervisor → lower latency, higher PPS.

## Placement Group Strategies
| Strategy | Use Case | Benefit |
|----------|----------|---------|
| Cluster | HPC, low latency | Same rack, <0.1ms RTT |
| Spread | HA, fault isolation | Different racks/AZs |
| Partition | Hadoop, Kafka | Groups on separate racks |

## Jumbo Frames (MTU 9001)
```
Standard frame: [14B header][1500B payload][4B FCS] = 1518B total
Jumbo frame:    [14B header][9000B payload][4B FCS] = 9018B total

Benefit: 6x larger payload per frame → fewer frames → less overhead
         Especially useful for large file transfers, databases

Limitation: Only within VPC. Internet traffic is capped at MTU 1500.
```

## Expected Benchmark Results (c5n.large)
| Test | Expected |
|------|----------|
| Single-stream TCP | 4-6 Gbps |
| Multi-stream TCP (8P) | 10-25 Gbps |
| Latency (cluster PG) | < 0.1 ms |
| Latency (no PG) | 0.1-0.5 ms |
