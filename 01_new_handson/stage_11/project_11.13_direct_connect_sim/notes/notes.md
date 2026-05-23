# Notes — Project 11.13

## Bird BGP Quick Reference
```bash
# Check BGP session status
sudo birdc show protocols

# Show all BGP routes
sudo birdc show route

# Show routes from specific peer
sudo birdc show route protocol aws_tunnel1

# Force BGP session reset
sudo birdc disable aws_tunnel1
sudo birdc enable aws_tunnel1

# Reload config without restart
sudo birdc configure
```

## Tunnel Inside IPs
AWS assigns /30 CIDRs for the BGP session inside the tunnel:
- AWS side: 169.254.x.x/30
- Customer side: 169.254.x.x/30 (adjacent IP)
These are used as BGP neighbor IPs in Bird config.

## Key Difference from Project 11.12
Project 11.12 uses static routing — you manually specify routes.
Project 11.13 uses BGP — routes are exchanged dynamically.
BGP is what Direct Connect uses in production.
