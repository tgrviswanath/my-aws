# AWS Console UI Steps — EC2 Web Server with Nginx

> **Method:** AWS Management Console (browser-based)
> **Estimated time:** 25–35 minutes
> **Difficulty:** Beginner

---

## Prerequisites Check

Before opening the AWS Console, confirm:

- [ ] Logged into [AWS Console](https://console.aws.amazon.com) with EC2 permissions
- [ ] Your public IP address is known — visit [whatismyip.com](https://whatismyip.com) and note it (e.g., `203.0.113.42`)
- [ ] You know which region to use (recommend: **us-east-1** for free tier resources)
- [ ] SSH client available: Terminal (macOS/Linux) or Windows Terminal / PuTTY (Windows)
- [ ] A folder ready to save the `.pem` key file after download

**Quick permission check:**
- IAM → Users → your user → Permissions tab
- Confirm `AmazonEC2FullAccess` or custom policy including `ec2:RunInstances`, `ec2:AllocateAddress`

---

## Step 1: Launch EC2 Instance

### 1.1 — Navigate to EC2

1. AWS Console search bar → type **EC2**
2. Click **EC2** under Services
3. Click **Launch instance** (orange button, top right)

### 1.2 — Name the Instance

- **Name:** `web-server-01`

### 1.3 — Choose an Amazon Machine Image (AMI)

Scroll to **Application and OS Images (Amazon Machine Image)**

### Decision Point 1: Amazon Linux vs Ubuntu

| Choice | Notes |
|--------|-------|
| ✅ **Amazon Linux 2023** | AWS-optimized, `dnf`/`yum`, SSH user: `ec2-user`, recommended for AWS learning |
| Ubuntu 22.04 LTS | Familiar Debian/apt ecosystem, SSH user: `ubuntu` |

**Select:** Amazon Linux 2023 AMI (64-bit x86)
- Confirm the badge says **"Free tier eligible"**

📸 **Screenshot checkpoint:** AMI selection panel showing Amazon Linux 2023 highlighted with "Free tier eligible" badge.

### 1.4 — Choose Instance Type

- **Instance type:** `t2.micro`
- Confirm it shows **"Free tier eligible"** (1 vCPU, 1 GiB Memory)

### 1.5 — Configure Key Pair

**Why you need a key pair:** SSH authentication requires a private key (.pem file). AWS keeps the public key; you keep the private key. Without it you cannot SSH into the instance.

1. Click **Create new key pair**
2. **Key pair name:** `ec2-web-server-key`
3. **Key pair type:** RSA
4. **Private key file format:**
   - `.pem` — for OpenSSH (macOS, Linux, Windows Terminal)
   - `.ppk` — for PuTTY (Windows only)
5. Click **Create key pair** → the `.pem` file downloads automatically

> ⚠️ Save this file in a secure location. If you lose it, you cannot SSH into this instance. You would need to create a new instance with a new key pair.

📸 **Screenshot checkpoint:** Key pair creation dialog showing the key pair name before clicking Create.

### 1.6 — Configure Network Settings (Security Group)

1. Click **Edit** next to Network settings
2. **VPC:** leave as default VPC
3. **Auto-assign public IP:** Enable (or leave as "Enable" — default)
4. **Firewall (security groups):** Select **Create security group**
5. **Security group name:** `web-server-sg`
6. **Description:** `Allow HTTP, HTTPS, SSH for web server`

**Configure inbound rules:**

Default rule (keep it):
| Type | Protocol | Port | Source | Notes |
|------|----------|------|--------|-------|
| SSH | TCP | 22 | **My IP** (auto-filled) | ✅ Restricted to your IP |

Add rule → HTTP:
| Type | Protocol | Port | Source |
|------|----------|------|--------|
| HTTP | TCP | 80 | Anywhere (0.0.0.0/0) |

Add rule → HTTPS:
| Type | Protocol | Port | Source |
|------|----------|------|--------|
| HTTPS | TCP | 443 | Anywhere (0.0.0.0/0) |

📸 **Screenshot checkpoint:** Security group configuration showing all 3 rules (SSH/My IP, HTTP/Anywhere, HTTPS/Anywhere).

### 1.7 — Configure Storage

- **Root volume:** 8 GB gp3 (free tier: up to 30 GB)
- Leave encryption and other settings as default

### 1.8 — Advanced Details (User Data)

Expand **Advanced details** → scroll to the bottom → **User data** text box

Paste this script to automatically install Nginx when the instance first boots:

```bash
#!/bin/bash
yum update -y
yum install nginx -y
systemctl start nginx
systemctl enable nginx
echo "<h1>Hello from EC2 + Nginx!</h1><p>Instance: $(hostname -f)</p>" \
  > /usr/share/nginx/html/index.html
```

> This script runs once at first boot. It updates the OS, installs Nginx, starts it, enables it to start on reboot, and writes a custom homepage.

### 1.9 — Review and Launch

**Summary panel (right side) should show:**
- AMI: Amazon Linux 2023
- Instance type: t2.micro (Free tier)
- Key pair: ec2-web-server-key
- Security group: web-server-sg
- Storage: 8 GiB gp3

Click **Launch instance**

**Expected result:** Green success banner with instance ID link (e.g., `i-0abc1234def56789`).

Click the instance ID link to go to the Instances view.

📸 **Screenshot checkpoint:** EC2 Instances list showing `web-server-01` with **Instance state: Running** (green dot).

---

### Troubleshooting — Step 1

**Error: "You have requested more instances than your current instance limit"**
- New accounts have a limit of 1–5 on-demand instances. Request a limit increase in Service Quotas.

**Error: "InvalidKeyPair.NotFound"**
- The key pair didn't save. Create a new one from EC2 → Key Pairs → Create key pair.

**Instance stays in "Pending" state**
- Normal for 1–2 minutes. The state changes to "Running" automatically.

**Instance launched but port 80 not accessible**
- Nginx user data may still be running. Wait 2–3 minutes after instance is in "Running" state.
- Check the instance's system log: Actions → Monitor and troubleshoot → Get system log

---

## Step 2: Verify Instance is Running

### 2.1 — Find Your Instance

1. EC2 → Instances → Instances
2. Find `web-server-01` in the list
3. Click on the instance ID to open details

### 2.2 — Note the Public IP Address

In the instance summary panel:
- **Public IPv4 address:** e.g., `54.123.45.67` (this changes on every stop/start — we'll fix this with Elastic IP)
- **Public IPv4 DNS:** e.g., `ec2-54-123-45-67.compute-1.amazonaws.com`

### 2.3 — Test Nginx (Initial Check)

Open a new browser tab and visit:
`http://54.123.45.67` (replace with your instance's public IP)

**Expected result:** Nginx welcome page or your custom "Hello from EC2" page.

> If you see "This site can't be reached" after waiting 2 minutes, check:
> 1. Is the instance status "Running"? (not "Pending")
> 2. Did the security group allow port 80?
> 3. Did the user data script run? (check system log)

📸 **Screenshot checkpoint:** Browser showing Nginx page at `http://<public-ip>`.

---

## Step 3: Allocate and Associate an Elastic IP

**Why?** The current public IP changes every time you stop and start the instance. An Elastic IP is a static IP that stays with your account.

### 3.1 — Allocate an Elastic IP

1. EC2 left sidebar → **Network & Security** → **Elastic IPs**
2. Click **Allocate Elastic IP address**
3. **Network Border Group:** leave as your region (e.g., `us-east-1`)
4. **Public IPv4 address pool:** Amazon's pool of IPv4 addresses
5. Click **Allocate**

**Expected result:** New Elastic IP appears in the list (e.g., `54.200.100.50`)

📸 **Screenshot checkpoint:** Elastic IPs page showing the newly allocated IP address.

### 3.2 — Associate Elastic IP with Your Instance

1. Check the checkbox next to your new Elastic IP
2. Click **Actions** → **Associate Elastic IP address**
3. **Resource type:** Instance
4. **Instance:** Start typing `web-server-01` or the instance ID → select it
5. **Private IP address:** leave as auto-selected
6. Click **Associate**

**Expected result:** The Elastic IP row now shows your instance ID in the "Associated instance ID" column.

📸 **Screenshot checkpoint:** Elastic IPs page showing the IP associated with your instance ID.

### 3.3 — Test with Elastic IP

Open a browser and visit: `http://<your-elastic-ip>`

The Nginx page should still appear, now using the static Elastic IP.

---

### Troubleshooting — Step 3

**Error: "This address is already associated"**
- Disassociate the IP first: Actions → Disassociate → then re-associate.

**Elastic IP shows as "Not associated" in the list**
- The association didn't complete. Repeat the association steps.

**Elastic IP not showing up in instance details**
- Refresh the EC2 Instances page. Association can take 10–30 seconds to reflect.

---

## Step 4: Connect via SSH

### 4.1 — Find the SSH Connection Command

1. EC2 → Instances → click your instance
2. Click **Connect** (top right)
3. Click the **SSH client** tab
4. Copy the example command shown (e.g., `ssh -i "ec2-web-server-key.pem" ec2-user@54.200.100.50`)

### 4.2 — Connect from Terminal

```bash
# Adjust the path to where you saved your .pem file
chmod 400 ~/Downloads/ec2-web-server-key.pem

ssh -i ~/Downloads/ec2-web-server-key.pem ec2-user@<YOUR-ELASTIC-IP>
```

📸 **Screenshot checkpoint:** SSH terminal session connected to the EC2 instance showing the Amazon Linux 2023 welcome banner.

### 4.3 — Verify Nginx Inside the Instance

```bash
sudo systemctl status nginx
# Expected: active (running) in green

curl localhost
# Expected: your custom HTML or Nginx default page

sudo cat /var/log/nginx/access.log
# Expected: HTTP access log entries from your browser tests
```

**Expected Outcome after Step 4:**
- [ ] SSH connection working with your `.pem` key
- [ ] Nginx status shows `active (running)`
- [ ] `curl localhost` returns HTML content
- [ ] Browser at `http://<elastic-ip>` shows the Nginx page

---

### Troubleshooting — Step 4

**Error: "Permission denied (publickey)"**
- Wrong key file. Use the exact `.pem` you downloaded for this instance.
- Wrong user. Amazon Linux uses `ec2-user`, not `root` or `ubuntu`.
- Key file permissions too open: `chmod 400 your-key.pem`

**SSH connection times out**
- Security group may not allow port 22 from your IP
- Your IP may have changed since launch. Update the security group SSH rule with your current IP.

**Nginx not running after SSH**
- Check if User Data ran: `sudo cat /var/log/cloud-init-output.log`
- Manually install: `sudo yum install nginx -y && sudo systemctl start nginx`

---

## Final Expected Outcome

After completing all 4 steps:

- [ ] EC2 instance `web-server-01` is in "Running" state
- [ ] Security group allows ports 22 (your IP), 80 (all), 443 (all)
- [ ] Elastic IP is allocated and associated with the instance
- [ ] `http://<elastic-ip>` shows the Nginx web page in a browser
- [ ] SSH works: `ssh -i key.pem ec2-user@<elastic-ip>` connects successfully
- [ ] Nginx is enabled to auto-start on reboot (`systemctl is-enabled nginx` returns `enabled`)

**Your EC2 web server is now:**
- Running Nginx serving HTTP on port 80
- Accessible globally via a stable Elastic IP
- Secured with SSH key authentication
- Ready for deploying a Node.js, Python, or PHP application
