# Steps — Project 1.2 Linux Web Server on EC2

## Phase 1 — Console

### 1.1 Create Key Pair
1. Go to **EC2** → **Key Pairs** → **Create key pair**
2. Name: `ec2-lab-key`
3. Type: RSA, Format: `.pem`
4. Download and save securely — you cannot download it again

```bash
# Set correct permissions on your key
chmod 400 ~/Downloads/ec2-lab-key.pem
```

### 1.2 Create Security Group
1. Go to **EC2** → **Security Groups** → **Create security group**
2. Name: `web-server-sg`
3. Inbound rules:
   - HTTP: port 80, source `0.0.0.0/0`
   - HTTPS: port 443, source `0.0.0.0/0`
   - SSH: port 22, source **Your IP only** (use "My IP")
4. Outbound: allow all (default)

### 1.3 Launch EC2 Instance
1. Go to **EC2** → **Launch instance**
2. Name: `web-server-01`
3. AMI: **Amazon Linux 2023** (free tier eligible)
4. Instance type: `t3.micro` (free tier eligible)
5. Key pair: `ec2-lab-key`
6. Security group: `web-server-sg`
7. Storage: 8 GB gp3 (default)
8. Advanced → User data (paste the setup script below)
9. Launch

User data script:
```bash
#!/bin/bash
yum update -y
yum install -y nginx
systemctl start nginx
systemctl enable nginx
echo "<h1>Hello from EC2!</h1><p>Instance: $(hostname)</p>" > /usr/share/nginx/html/index.html
```

---

## Phase 2 — Connect via SSH

```bash
# Get the public IP from EC2 console
ssh -i ~/Downloads/ec2-lab-key.pem ec2-user@YOUR_PUBLIC_IP

# Verify Nginx is running
systemctl status nginx
curl http://localhost
```

---

## Phase 3 — Configure Nginx as Reverse Proxy

```bash
# SSH into the instance first
ssh -i ~/Downloads/ec2-lab-key.pem ec2-user@YOUR_PUBLIC_IP

# Create a simple app to proxy to
cat > /tmp/app.py << 'EOF'
from http.server import HTTPServer, BaseHTTPRequestHandler

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Hello from the backend app!")

HTTPServer(("127.0.0.1", 8080), Handler).serve_forever()
EOF

# Run app in background
python3 /tmp/app.py &

# Configure Nginx reverse proxy
sudo tee /etc/nginx/conf.d/app.conf << 'EOF'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /health {
        return 200 'OK';
        add_header Content-Type text/plain;
    }
}
EOF

sudo nginx -t
sudo systemctl reload nginx

# Test
curl http://localhost
curl http://YOUR_PUBLIC_IP
```

---

## Phase 4 — Secure SSH Access

```bash
# On the instance — harden SSH config
sudo vi /etc/ssh/sshd_config

# Ensure these settings:
# PermitRootLogin no
# PasswordAuthentication no
# PubkeyAuthentication yes

sudo systemctl restart sshd
```

---

## Phase 5 — AWS CLI

```bash
# Launch instance via CLI
aws ec2 run-instances \
  --image-id ami-0c02fb55956c7d316 \
  --instance-type t3.micro \
  --key-name ec2-lab-key \
  --security-group-ids sg-XXXXXXXXXX \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=web-server-01},{Key=Project,Value=handson}]' \
  --user-data file://userdata.sh

# Get instance public IP
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=web-server-01" \
  --query "Reservations[0].Instances[0].PublicIpAddress" \
  --output text

# Stop instance when done (saves free tier hours)
aws ec2 stop-instances --instance-ids i-XXXXXXXXXX

# Terminate when completely done
aws ec2 terminate-instances --instance-ids i-XXXXXXXXXX
```

---

## Phase 6 — Terraform

```bash
cd terraform
terraform init
terraform plan -var-file="terraform.tfvars"
terraform apply -var-file="terraform.tfvars"

# Get outputs
terraform output instance_public_ip

# Destroy when done
terraform destroy -var-file="terraform.tfvars"
```

---

## Screenshots to Take
- [ ] EC2 instance running in console (green "Running" status)
- [ ] SSH connection successful in terminal
- [ ] Nginx serving page at public IP in browser
- [ ] Reverse proxy working (curl output)
- [ ] Security group rules showing correct ports
- [ ] `terraform apply` success output
