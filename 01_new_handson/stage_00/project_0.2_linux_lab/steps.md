# Steps — Project 0.2 Linux Foundations Lab

## Phase 1 — Start Linux Container

```bash
docker run -it --name linux-lab ubuntu:22.04 /bin/bash

# Update packages first
apt-get update -y
```

---

## Phase 2 — File System Navigation

```bash
# Explore the filesystem
pwd
ls -la /
ls -la /etc
ls -la /var/log

# Create a project directory structure
mkdir -p /opt/myapp/{logs,config,data,scripts}
ls -la /opt/myapp/

# Create files
touch /opt/myapp/config/app.conf
echo "APP_ENV=development" > /opt/myapp/config/app.conf
cat /opt/myapp/config/app.conf
```

---

## Phase 3 — User & Permission Management

```bash
# Create a new user
useradd -m -s /bin/bash appuser
passwd appuser   # set a password

# Create a group
groupadd appgroup

# Add user to group
usermod -aG appgroup appuser

# Verify group membership
groups appuser
id appuser

# Set file ownership
chown appuser:appgroup /opt/myapp/config/app.conf

# Set permissions: owner=rw, group=r, others=none
chmod 640 /opt/myapp/config/app.conf

# Verify
ls -la /opt/myapp/config/

# Test: switch to appuser and try to read
su - appuser
cat /opt/myapp/config/app.conf   # should work (group read)
exit
```

---

## Phase 4 — Install and Configure Nginx

```bash
apt-get install -y nginx

# Start Nginx
service nginx start

# Verify it's running
service nginx status
curl http://localhost

# Replace default page
echo "<h1>Hello from Linux Lab</h1>" > /var/www/html/index.html
curl http://localhost

# View Nginx config
cat /etc/nginx/nginx.conf
ls /etc/nginx/sites-available/
```

Configure a custom virtual host:
```bash
cat > /etc/nginx/sites-available/myapp << 'EOF'
server {
    listen 8080;
    server_name localhost;

    location / {
        root /opt/myapp/data;
        index index.html;
    }

    location /health {
        return 200 'OK';
        add_header Content-Type text/plain;
    }
}
EOF

# Enable the site
ln -s /etc/nginx/sites-available/myapp /etc/nginx/sites-enabled/myapp

# Test config
nginx -t

# Reload
service nginx reload

# Test
echo "<h1>My App</h1>" > /opt/myapp/data/index.html
curl http://localhost:8080
curl http://localhost:8080/health
```

---

## Phase 5 — Process Management

```bash
# View all running processes
ps aux

# Filter for nginx
ps aux | grep nginx

# View system resources
free -h        # memory
df -h          # disk
uptime         # load average

# Find process by name and get PID
pgrep nginx

# Send signal to process
kill -HUP $(pgrep nginx)   # graceful reload
kill -9 <PID>              # force kill (use carefully)

# Background processes
sleep 60 &
jobs
kill %1
```

---

## Phase 6 — Log Analysis

```bash
# Generate some traffic first
for i in {1..10}; do curl -s http://localhost > /dev/null; done
curl http://localhost/nonexistent

# View access logs
cat /var/log/nginx/access.log

# Tail live (open second terminal)
tail -f /var/log/nginx/access.log

# Search for errors
grep "404" /var/log/nginx/access.log
grep "500" /var/log/nginx/error.log

# Count requests
wc -l /var/log/nginx/access.log

# Most common IPs
awk '{print $1}' /var/log/nginx/access.log | sort | uniq -c | sort -rn

# System logs
journalctl -u nginx --no-pager | tail -20
```

---

## Phase 7 — Cron Jobs

```bash
# Install cron
apt-get install -y cron
service cron start

# Edit crontab for root
crontab -e
# Add this line (runs every minute):
# * * * * * echo "$(date): health check OK" >> /opt/myapp/logs/cron.log

# Cron syntax: minute hour day month weekday command
# Examples:
# 0 * * * *     = every hour
# 0 0 * * *     = every day at midnight
# */5 * * * *   = every 5 minutes
# 0 9 * * 1-5   = 9am Monday-Friday

# Wait 1 minute then verify
sleep 65
cat /opt/myapp/logs/cron.log
```

---

## Phase 8 — SSH Key Authentication

```bash
# In a new terminal — start a second container as SSH server
docker run -d --name ssh-server ubuntu:22.04 sleep infinity
docker exec ssh-server apt-get update -y
docker exec ssh-server apt-get install -y openssh-server

# Configure SSH server
docker exec ssh-server mkdir -p /run/sshd
docker exec ssh-server /usr/sbin/sshd

# On your host — generate SSH key pair
ssh-keygen -t rsa -b 4096 -f ~/.ssh/lab_key -N ""
cat ~/.ssh/lab_key.pub

# Copy public key to server container
docker exec ssh-server mkdir -p /root/.ssh
docker exec ssh-server chmod 700 /root/.ssh
docker cp ~/.ssh/lab_key.pub ssh-server:/root/.ssh/authorized_keys
docker exec ssh-server chmod 600 /root/.ssh/authorized_keys

# Get server container IP
docker inspect ssh-server | grep IPAddress

# Connect via SSH
ssh -i ~/.ssh/lab_key root@<container-ip>
```

---

## Screenshots to Take
- [ ] Directory structure with permissions (`ls -la /opt/myapp/`)
- [ ] Nginx running (`curl http://localhost` output)
- [ ] Custom virtual host responding on port 8080
- [ ] Log analysis output (grep results)
- [ ] Cron log showing scheduled entries
- [ ] SSH key-based login success

# AWS CLI Quick Reference

`ash
# Verify setup
aws sts get-caller-identity
aws configure list

# Common commands
aws ec2 describe-instances --output table
aws s3 ls
aws lambda list-functions --output table
`
