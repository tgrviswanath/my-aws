# Benchmark Results — Project 11.18

## Environment
- Instance type: c5n.large
- Placement group: cluster
- ENA: enabled
- MTU: 9001
- Region: us-east-1
- Date: ___________

## Results

### Test 1 — Single Stream TCP
```
iperf3 -c <EC2-A-IP> -t 30
Throughput: _______ Gbps
```

### Test 2 — Multi-Stream TCP (8 parallel)
```
iperf3 -c <EC2-A-IP> -t 30 -P 8
Throughput: _______ Gbps
```

### Test 3 — UDP
```
iperf3 -c <EC2-A-IP> -u -b 10G -t 30
Throughput: _______ Gbps
Jitter:     _______ ms
Loss:       _______ %
```

### Test 4 — Latency (ping 100 packets)
```
ping -c 100 -i 0.01 <EC2-A-IP>
min/avg/max/mdev: ___ / ___ / ___ / ___ ms
```

### Test 5 — Jumbo Frames
```
ping -c 5 -M do -s 8972 <EC2-A-IP>
Result: success / fail
```

### Test 6 — Without Placement Group (comparison)
```
Latency: _______ ms
Throughput: _______ Gbps
```

## Observations
_Write your observations here after running the tests._
