#!/bin/bash
# setup.sh — Automates the Linux lab setup inside the container

set -e

echo "=== Updating packages ==="
apt-get update -y

echo "=== Installing tools ==="
apt-get install -y nginx cron curl vim

echo "=== Creating app directory structure ==="
mkdir -p /opt/myapp/{logs,config,data,scripts}

echo "=== Creating app user ==="
useradd -m -s /bin/bash appuser || true
groupadd appgroup || true
usermod -aG appgroup appuser

echo "=== Setting up config file ==="
echo "APP_ENV=development" > /opt/myapp/config/app.conf
chown appuser:appgroup /opt/myapp/config/app.conf
chmod 640 /opt/myapp/config/app.conf

echo "=== Configuring Nginx ==="
cat > /etc/nginx/sites-available/myapp << 'EOF'
server {
    listen 8080;
    server_name localhost;

    access_log /opt/myapp/logs/access.log;
    error_log  /opt/myapp/logs/error.log;

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

ln -sf /etc/nginx/sites-available/myapp /etc/nginx/sites-enabled/myapp
echo "<h1>My App — Linux Lab</h1>" > /opt/myapp/data/index.html

nginx -t
service nginx start

echo "=== Starting cron ==="
service cron start

echo "=== Setup complete ==="
echo "Test Nginx: curl http://localhost:8080"
echo "Test health: curl http://localhost:8080/health"
