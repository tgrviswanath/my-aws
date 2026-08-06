# Project 1.2 — EC2 Web Server

**Stage:** 01 | **Level:** Beginner | **Est. Time:** 1–2 hours | **Cost:** ~$8.50/month (free tier: 750 h/month t2.micro)

Launch an EC2 t2.micro instance running Amazon Linux 2023, install Nginx via a user data script at first boot, and expose it on port 80. Covers key pair creation, security group rules (SSH 22, HTTP 80), and Elastic IP assignment for a stable public address.

---

## Services Used

| Tool | Purpose | Cost |
|------|---------|------|
| EC2 (t2.micro) | Virtual server running Amazon Linux 2023 | Free tier: 750 h/month; ~$8.50/month after |
| VPC / Security Groups | Network isolation; stateful firewall rules (port 22, 80) | Free |
| Elastic IP | Static public IP that survives instance stop/start | Free while attached to running instance; ~$0.005/hr if unattached |
| Key Pair | SSH authentication to the instance | Free |

---

## Input / Output

### Input
| Type | Description |
|------|-------------|
| VPC with public subnet | Default VPC is sufficient; subnet must have auto-assign public IP or Elastic IP |
| Key pair | `.pem` file created/downloaded at launch (`my-key.pem`) |
| Security group rules | Inbound: TCP 22 from your IP, TCP 80 from 0.0.0.0/0 |
| User data script | Bash script to install and start Nginx at first boot |

### Output
| Type | Description |
|------|-------------|
| EC2 instance | `i-0abc...` running Amazon Linux 2023, state: running |
| Elastic IP | Static public IP (e.g. `54.210.x.x`) mapped to the instance |
| Nginx default page | `http://54.210.x.x` returns Nginx welcome page on port 80 |
| SSH access | `ssh -i my-key.pem ec2-user@54.210.x.x` connects successfully |

---

## Architecture

```
Internet
  │ HTTP :80  /  SSH :22
  ▼
Security Group (sg-abc123)
  ├── Inbound: TCP 22 from YOUR_IP/32  (SSH)
  ├── Inbound: TCP 80 from 0.0.0.0/0   (HTTP)
  └── Outbound: all traffic allowed
        │
        ▼
EC2 Instance (t2.micro, Amazon Linux 2023)
  ├── Elastic IP: 54.210.x.x  ──  eth0 (private: 10.0.x.x)
  └── Nginx 1.24
        └── listening on 0.0.0.0:80
              └── serves /usr/share/nginx/html/index.html
```

---

## Quick Start

```cmd
REM 1. Create key pair — saves my-key.pem to current directory
aws ec2 create-key-pair --key-name my-key ^
    --query "KeyMaterial" --output text > my-key.pem

REM 2. Create security group
aws ec2 create-security-group --group-name web-sg ^
    --description "HTTP and SSH access" --vpc-id vpc-XXXXX

REM 3. Allow SSH from your IP (replace YOUR_IP)
aws ec2 authorize-security-group-ingress --group-name web-sg ^
    --protocol tcp --port 22 --cidr YOUR_IP/32

REM 4. Allow HTTP from anywhere
aws ec2 authorize-security-group-ingress --group-name web-sg ^
    --protocol tcp --port 80 --cidr 0.0.0.0/0

REM 5. Launch EC2 with user data (installs Nginx on first boot)
aws ec2 run-instances ^
    --image-id ami-0c02fb55956c7d316 ^
    --instance-type t2.micro ^
    --key-name my-key ^
    --security-groups web-sg ^
    --user-data file://code/user_data.sh ^
    --count 1 ^
    --query "Instances[0].InstanceId" ^
    --output text

REM 6. Wait for instance to be running
aws ec2 wait instance-running --instance-ids i-0abc123

REM 7. Allocate and associate Elastic IP
aws ec2 allocate-address --domain vpc
aws ec2 associate-address --instance-id i-0abc123 --allocation-id eipalloc-XXXX

REM 8. Test Nginx
curl http://54.210.x.x
```

---

## Data Flow

```
1. aws ec2 run-instances sends launch request — EC2 scheduler places instance on a host
2. User data script is retrieved and injected by cloud-init at first boot (runs as root)
3. cloud-init executes user_data.sh: dnf install nginx -y && systemctl enable nginx && systemctl start nginx
4. Nginx starts and listens on 0.0.0.0:80
5. Elastic IP is mapped to the instance's primary ENI — incoming traffic on 54.210.x.x hits the instance
6. Security group evaluates inbound rules — TCP 80 from 0.0.0.0/0 is allowed
7. Security groups are stateful: return traffic on the same connection is automatically allowed without a matching outbound rule
8. HTTP request reaches Nginx → returns default welcome page (index.html)
9. SSH connection (port 22) uses the private key for public-key authentication
```

---

## Project Files

| File | Purpose |
|------|---------|
| `README.md` | This file — project overview |
| `GUIDE.md` | Full walkthrough: launch, SSH, Nginx config, Elastic IP |
| `steps.md` | Windows CMD quick-reference for EC2 launch and IP commands |
| `steps_awsconsoleui.md` | Console UI walkthrough: EC2 launch wizard step-by-step |
| `verify.md` | Checklist: Nginx responding, SSH working, Elastic IP assigned |
| `cost_estimate.md` | Cost breakdown (free tier vs on-demand) |
| `code/user_data.sh` | Bootstrap script: installs and enables Nginx on Amazon Linux 2023 |
| `code/` | Security group JSON template, sample Nginx config |
| `docs/` | Instance type comparison (t2 vs t3), security group stateful notes |

---

## Lessons Learned

- Security groups are **stateful** — if you allow inbound TCP 80, the response traffic is automatically allowed outbound without an explicit outbound rule; NACLs are stateless and require both directions
- Elastic IP is free while attached to a **running** instance — if you stop the instance without releasing or re-associating the EIP, AWS charges ~$0.005/hr; always release EIPs you no longer need
- User data runs **as root** at first boot only — `sudo` is not needed inside the script; to re-run it for testing, cloud-init scripts must be cleared first
- EC2 Instance Connect (browser-based SSH in the console) works without downloading a `.pem` file — useful for quick access but requires the security group to allow TCP 22 from AWS IP ranges
- `t2.micro` earns CPU credits at 6 credits/hr and consumes them when CPU usage exceeds the 10% baseline — sustained CPU above baseline drains credits and throttles the instance
- Amazon Linux 2023 uses `dnf` (not `yum`) for package management — user data scripts written for Amazon Linux 2 that use `yum` still work but `dnf` is the preferred tool going forward
- Stopping an instance (not terminating) retains the root EBS volume and Elastic IP association — you only pay for the EBS volume storage while stopped, not the instance hours
