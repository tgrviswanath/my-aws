#!/bin/bash
# =============================================================================
# setup_nginx.sh — EC2 user-data script to install and configure Nginx
#
# Usage:
#   Paste this script into the EC2 "User data" field when launching an instance,
#   OR run it manually on an Amazon Linux 2 / Ubuntu instance:
#     sudo bash setup_nginx.sh
#
# What this script does:
#   1. System update and Nginx installation
#   2. Create a sample static site with a health-check endpoint
#   3. Configure Nginx as a reverse proxy (port 80 → app on port 3000)
#   4. Enable Gzip compression and security headers
#   5. Harden SSH configuration
#   6. Set up log rotation
#   7. Enable and start Nginx
#
# Tested on: Amazon Linux 2, Amazon Linux 2023, Ubuntu 22.04
# =============================================================================

set -euo pipefail

# ── Detect OS ──────────────────────────────────────────────────────────────────
if [[ -f /etc/os-release ]]; then
    . /etc/os-release
    OS_ID="${ID}"
else
    OS_ID="unknown"
fi

# ── Logging ────────────────────────────────────────────────────────────────────
LOG_FILE="/var/log/setup_nginx.log"
exec > >(tee -a "${LOG_FILE}") 2>&1

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

log "=== Nginx Setup Script Starting ==="
log "OS: ${OS_ID}"

# =============================================================================
# STEP 1 — System update and Nginx install
# =============================================================================
log "Step 1: Updating system and installing Nginx..."

case "${OS_ID}" in
    amzn)
        # Amazon Linux 2 / Amazon Linux 2023
        yum update -y
        amazon-linux-extras install nginx1 -y 2>/dev/null || yum install nginx -y
        ;;
    ubuntu|debian)
        export DEBIAN_FRONTEND=noninteractive
        apt-get update -y
        apt-get install -y nginx curl
        ;;
    *)
        log "WARNING: Unknown OS '${OS_ID}'. Attempting yum install..."
        yum update -y
        yum install nginx -y
        ;;
esac

log "Nginx installed successfully."

# =============================================================================
# STEP 2 — Create sample static site
# =============================================================================
log "Step 2: Creating sample static site..."

WEBROOT="/usr/share/nginx/html"
mkdir -p "${WEBROOT}"

# Get instance metadata (IMDSv2)
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" \
    -H "X-aws-ec2-metadata-token-ttl-seconds: 21600" 2>/dev/null || echo "")

if [[ -n "${TOKEN}" ]]; then
    INSTANCE_ID=$(curl -s -H "X-aws-ec2-metadata-token: ${TOKEN}" \
        http://169.254.169.254/latest/meta-data/instance-id 2>/dev/null || echo "unknown")
    AZ=$(curl -s -H "X-aws-ec2-metadata-token: ${TOKEN}" \
        http://169.254.169.254/latest/meta-data/placement/availability-zone 2>/dev/null || echo "unknown")
    PUBLIC_IP=$(curl -s -H "X-aws-ec2-metadata-token: ${TOKEN}" \
        http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "unknown")
else
    INSTANCE_ID="unknown"
    AZ="unknown"
    PUBLIC_IP="unknown"
fi

# Main index page
cat > "${WEBROOT}/index.html" << EOF
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EC2 Nginx Server</title>
    <style>
        body { font-family: -apple-system, sans-serif; background: #0d1117; color: #e6edf3;
               display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; }
        .card { background: #161b22; border: 1px solid #30363d; border-radius: 12px;
                padding: 2.5rem; max-width: 480px; width: 90%; text-align: center; }
        h1 { color: #FF9900; font-size: 2rem; margin-bottom: 0.5rem; }
        .badge { display: inline-block; background: rgba(255,153,0,0.15); color: #FF9900;
                 border: 1px solid #FF9900; border-radius: 20px; padding: 3px 12px;
                 font-size: 0.75rem; font-weight: 600; margin-bottom: 1.5rem; }
        .info { background: #0d1117; border-radius: 8px; padding: 1rem; text-align: left; margin-top: 1.5rem; }
        .info p { margin: 0.4rem 0; font-size: 0.9rem; color: #8b949e; }
        .info span { color: #e6edf3; font-weight: 600; }
        .status { color: #3fb950; font-weight: 700; }
    </style>
</head>
<body>
    <div class="card">
        <div class="badge">AWS EC2 + Nginx</div>
        <h1>🚀 Server Online</h1>
        <p>Your EC2 instance is running Nginx successfully.</p>
        <div class="info">
            <p>Instance ID: <span>${INSTANCE_ID}</span></p>
            <p>Availability Zone: <span>${AZ}</span></p>
            <p>Public IP: <span>${PUBLIC_IP}</span></p>
            <p>Status: <span class="status">● Running</span></p>
        </div>
    </div>
</body>
</html>
EOF

# Health check endpoint (returns JSON — used by ALB target groups)
mkdir -p "${WEBROOT}/health"
cat > "${WEBROOT}/health/index.html" << 'EOF'
{"status":"healthy","service":"nginx","version":"1.0"}
EOF

log "Static site created at ${WEBROOT}"

# =============================================================================
# STEP 3 — Nginx configuration (reverse proxy + security headers)
# =============================================================================
log "Step 3: Configuring Nginx..."

NGINX_CONF="/etc/nginx/nginx.conf"

# Backup original config
cp "${NGINX_CONF}" "${NGINX_CONF}.bak"

cat > "${NGINX_CONF}" << 'NGINXCONF'
# /etc/nginx/nginx.conf — Production-hardened Nginx configuration

user nginx;
worker_processes auto;                  # One worker per CPU core
error_log /var/log/nginx/error.log warn;
pid /run/nginx.pid;

events {
    worker_connections 1024;            # Max simultaneous connections per worker
    use epoll;                          # Efficient event model on Linux
    multi_accept on;
}

http {
    # ── MIME types ────────────────────────────────────────────────────────────
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    # ── Logging ───────────────────────────────────────────────────────────────
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';
    access_log /var/log/nginx/access.log main;

    # ── Performance ───────────────────────────────────────────────────────────
    sendfile           on;
    tcp_nopush         on;
    tcp_nodelay        on;
    keepalive_timeout  65;
    types_hash_max_size 4096;

    # ── Gzip compression ──────────────────────────────────────────────────────
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_min_length 256;
    gzip_types
        text/plain text/css text/xml text/javascript
        application/json application/javascript application/xml
        application/rss+xml image/svg+xml;

    # ── Security: hide Nginx version ──────────────────────────────────────────
    server_tokens off;

    # ── Rate limiting ─────────────────────────────────────────────────────────
    limit_req_zone $binary_remote_addr zone=api:10m rate=30r/s;

    # ── Include virtual host configs ──────────────────────────────────────────
    include /etc/nginx/conf.d/*.conf;
}
NGINXCONF

# Virtual host config
cat > /etc/nginx/conf.d/default.conf << 'VHOSTCONF'
# /etc/nginx/conf.d/default.conf — Virtual host configuration

server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    # ── Security headers ──────────────────────────────────────────────────────
    add_header X-Frame-Options           "SAMEORIGIN"           always;
    add_header X-Content-Type-Options    "nosniff"              always;
    add_header X-XSS-Protection          "1; mode=block"        always;
    add_header Referrer-Policy           "strict-origin"        always;
    add_header Permissions-Policy        "geolocation=()"       always;
    add_header Strict-Transport-Security "max-age=31536000"     always;

    # ── Health check endpoint (for ALB target groups) ─────────────────────────
    location /health {
        access_log off;                 # Don't log health checks
        add_header Content-Type application/json;
        return 200 '{"status":"healthy"}';
    }

    # ── Reverse proxy to app on port 3000 ─────────────────────────────────────
    # Uncomment when your app server is running:
    # location /api/ {
    #     limit_req zone=api burst=50 nodelay;
    #     proxy_pass         http://127.0.0.1:3000/;
    #     proxy_http_version 1.1;
    #     proxy_set_header   Upgrade $http_upgrade;
    #     proxy_set_header   Connection "upgrade";
    #     proxy_set_header   Host $host;
    #     proxy_set_header   X-Real-IP $remote_addr;
    #     proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
    #     proxy_set_header   X-Forwarded-Proto $scheme;
    #     proxy_read_timeout 60s;
    # }

    # ── Static files ──────────────────────────────────────────────────────────
    location ~* \.(css|js|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    # ── Main site ─────────────────────────────────────────────────────────────
    location / {
        try_files $uri $uri/ =404;
    }

    # ── Block common attack patterns ──────────────────────────────────────────
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }
}
VHOSTCONF

# Test Nginx config before applying
nginx -t
log "Nginx configuration test passed."

# =============================================================================
# STEP 4 — Harden SSH
# =============================================================================
log "Step 4: Hardening SSH configuration..."

SSHD_CONF="/etc/ssh/sshd_config"
cp "${SSHD_CONF}" "${SSHD_CONF}.bak"

# Apply hardening settings (append to avoid breaking existing config)
cat >> "${SSHD_CONF}" << 'SSHCONF'

# ── Security hardening (added by setup_nginx.sh) ──────────────────────────────
PermitRootLogin no                  # Never allow root SSH login
PasswordAuthentication no           # Key-based auth only
PubkeyAuthentication yes
AuthorizedKeysFile .ssh/authorized_keys
MaxAuthTries 3                      # Lock out after 3 failed attempts
ClientAliveInterval 300             # Disconnect idle sessions after 5 min
ClientAliveCountMax 2
X11Forwarding no
AllowTcpForwarding no
Protocol 2                          # SSHv2 only
SSHCONF

log "SSH hardening applied."

# =============================================================================
# STEP 5 — Enable and start Nginx
# =============================================================================
log "Step 5: Enabling and starting Nginx..."

systemctl enable nginx
systemctl start nginx

# Verify Nginx is running
if systemctl is-active --quiet nginx; then
    log "Nginx is running successfully."
else
    log "ERROR: Nginx failed to start. Check /var/log/nginx/error.log"
    exit 1
fi

# =============================================================================
# STEP 6 — Log rotation (Nginx usually sets this up, but ensure it's correct)
# =============================================================================
log "Step 6: Configuring log rotation..."

cat > /etc/logrotate.d/nginx << 'LOGROTATE'
/var/log/nginx/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 nginx adm
    sharedscripts
    postrotate
        nginx -s reopen
    endscript
}
LOGROTATE

log "Log rotation configured."

# =============================================================================
# Summary
# =============================================================================
log "=== Setup Complete ==="
log "Nginx is serving on port 80"
log "Health check: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo 'localhost')/health"
log "Logs: /var/log/nginx/access.log, /var/log/nginx/error.log"
log "Setup log: ${LOG_FILE}"
