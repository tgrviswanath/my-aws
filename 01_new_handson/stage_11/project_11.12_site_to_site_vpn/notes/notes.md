# Notes — Project 11.12

## Getting Tunnel Parameters
After creating the VPN connection, download the config:
Console → VPN Connection → Download Configuration → Generic/Generic/Vendor Agnostic
This gives you: Tunnel IPs, Pre-shared keys, IKE/ESP parameters.

## strongSwan Troubleshooting
```bash
# Check tunnel status
sudo strongswan status

# View IKE logs
sudo journalctl -u strongswan -f

# Restart tunnel
sudo strongswan restart

# Check if ESP traffic is flowing
sudo tcpdump -i eth0 esp -n
```

## Common Issues
- Tunnel stays DOWN: check security group allows UDP 500 and 4500 from AWS tunnel IPs
- Traffic doesn't flow: check IP forwarding is enabled (`sysctl net.ipv4.ip_forward`)
- Tunnel flaps: check DPD settings and keepalive traffic
