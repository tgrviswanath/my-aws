# Verification & Validation — Project 0.2 Linux Foundations Lab

---

## 1. Container Running Verification

```bash
# Confirm the linux-lab container is running
docker ps --filter "name=linux-lab"
# Expected: linux-lab container with STATUS = Up

# Exec into it if needed
docker exec -it linux-lab /bin/bash
```

📸 Screenshot: `docker ps` showing linux-lab container running

---

## 2. File System & Permissions Verification

```bash
# Confirm directory structure was created
ls -la /opt/myapp/
# Expected: logs/ config/ data/ scripts/ directories

# Confirm file permissions
ls -la /opt/myapp/config/app.conf
# Expected: -rw-r----- 1 appuser appgroup ... app.conf
# (640 = owner rw, group r, others none)

# Confirm file content
cat /opt/myapp/config/app.conf
# Expected: APP_ENV=development

# Confirm user and group exist
id appuser
# Expected: uid=XXXX(appuser) gid=XXXX(appuser) groups=XXXX(appuser),XXXX(appgroup)

groups appuser
# Expected: appuser : appuser appgroup
```

📸 Screenshot: `ls -la /opt/myapp/config/` showing correct permissions (640)

---

## 3. Nginx Verification

```bash
# Confirm Nginx is running
service nginx status
# Expected: nginx is running

# Default page responds
curl http://localhost
# Expected: <h1>Hello from Linux Lab</h1>

# Custom virtual host on port 8080
curl http://localhost:8080
# Expected: <h1>My App</h1>

# Health endpoint
curl http://localhost:8080/health
# Expected: OK

# Config test passes
nginx -t
# Expected: nginx: configuration file /etc/nginx/nginx.conf test is successful
```

📸 Screenshot: `curl http://localhost:8080/health` returning OK

---

## 4. Process Management Verification

```bash
# Nginx processes visible
ps aux | grep nginx
# Expected: master process + worker process(es)

# System resources
free -h
# Expected: shows memory usage

df -h
# Expected: shows disk usage

# pgrep returns nginx PID
pgrep nginx
# Expected: one or more PIDs
```

---

## 5. Log Analysis Verification

```bash
# Generate traffic first
for i in {1..5}; do curl -s http://localhost > /dev/null; done
curl http://localhost/nonexistent

# Access log has entries
wc -l /var/log/nginx/access.log
# Expected: > 0 lines

# 404 entry exists for /nonexistent
grep "404" /var/log/nginx/access.log
# Expected: at least 1 line with 404

# IP count works
awk '{print $1}' /var/log/nginx/access.log | sort | uniq -c | sort -rn
# Expected: IP addresses with request counts
```

📸 Screenshot: `grep "404"` output showing the nonexistent request

---

## 6. Cron Job Verification

```bash
# Cron service running
service cron status
# Expected: cron is running

# Wait 65 seconds after adding cron entry, then:
cat /opt/myapp/logs/cron.log
# Expected: at least 1 line like:
# Mon Jan  1 12:00:01 UTC 2024: health check OK
```

📸 Screenshot: cron.log showing scheduled entries

---

## 7. SSH Key Authentication Verification

```bash
# Key pair exists
ls -la ~/.ssh/lab_key ~/.ssh/lab_key.pub
# Expected: both files present, lab_key permissions = 600

# SSH connection succeeds (no password prompt)
ssh -i ~/.ssh/lab_key root@<container-ip>
# Expected: logged in without password
```

📸 Screenshot: SSH login success without password prompt

---

## 8. Verification Checklist

- [ ] linux-lab container running
- [ ] `/opt/myapp/{logs,config,data,scripts}` directories created
- [ ] `app.conf` has permissions 640 (owner=appuser, group=appgroup)
- [ ] `appuser` exists and belongs to `appgroup`
- [ ] Nginx running, default page responds on port 80
- [ ] Custom virtual host responds on port 8080
- [ ] `/health` endpoint returns OK
- [ ] `nginx -t` passes
- [ ] Access log has entries after generating traffic
- [ ] 404 entry visible in access log
- [ ] Cron service running
- [ ] Cron log has entries after 1 minute
- [ ] SSH key pair generated
- [ ] SSH login to second container succeeds without password
