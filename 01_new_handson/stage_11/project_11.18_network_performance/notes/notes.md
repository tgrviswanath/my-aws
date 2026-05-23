# Notes — Project 11.18

## Quick Commands Reference
```bash
# Check ENA driver
ethtool -i eth0 | grep driver
# Expected: driver: ena

# Check MTU
ip link show eth0 | grep mtu
# Expected: mtu 9001

# Check interface speed
ethtool eth0 | grep Speed
# Expected: Speed: 25000Mb/s (c5n.large)

# Check network stats (packets/bytes)
ethtool -S eth0 | grep -E "tx_bytes|rx_bytes|tx_packets|rx_packets"

# iperf3 server
iperf3 -s

# iperf3 client — single stream
iperf3 -c <SERVER_IP> -t 30

# iperf3 client — multi-stream
iperf3 -c <SERVER_IP> -t 30 -P 8

# iperf3 UDP
iperf3 -c <SERVER_IP> -u -b 10G -t 30

# Jumbo frame test
ping -c 5 -M do -s 8972 <SERVER_IP>
```

## Why Single Stream < Multi-Stream
TCP single stream is limited by the congestion window and RTT.
Multiple parallel streams bypass this limitation and saturate the link.
For benchmarking max throughput, always use -P 8 or higher.

## Instance Type Selection for Network Performance
| Need | Instance |
|------|----------|
| General purpose | m5.xlarge (up to 10 Gbps) |
| Network intensive | c5n.xlarge (up to 25 Gbps) |
| Maximum throughput | c5n.18xlarge (100 Gbps) |
| HPC / MPI | hpc6a.48xlarge (100 Gbps EFA) |
