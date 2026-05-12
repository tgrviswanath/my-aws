# Project 0.2 — Linux Foundations Lab

## What This Does
Practices essential Linux administration skills inside a Docker container. No cloud account needed.

## Skills Covered
- File system navigation
- User and permission management
- Nginx installation and configuration
- Process management
- Log analysis
- Cron job scheduling
- SSH key-based authentication

## How to Run
```bash
docker run -it --name linux-lab ubuntu:22.04 /bin/bash
```

## Folder Structure
```
project_0.2_linux_lab/
├── README.md
├── steps.md
├── docs/
│   └── architecture.md
├── scripts/
│   ├── setup.sh
│   └── nginx.conf
└── cost_estimate.md
```

## Key Commands Reference
| Task | Command |
|------|---------|
| List files with permissions | `ls -la` |
| Change file owner | `chown user:group file` |
| Change permissions | `chmod 640 file` |
| View processes | `ps aux` |
| Tail logs live | `tail -f /var/log/nginx/access.log` |
| Search logs | `grep "404" /var/log/nginx/access.log` |
| Edit crontab | `crontab -e` |

## Lessons Learned
- Linux permissions: owner / group / others (rwx)
- `chmod 640` = owner read+write, group read, others nothing
- Nginx config lives in `/etc/nginx/sites-available/`
- Logs are your best debugging tool — always check them first

## Code

### `scripts/setup.sh` — Linux lab setup script

```bash
chmod +x scripts/setup.sh
sudo bash scripts/setup.sh
```

Covers: Nginx install, user creation, cron job setup, log analysis commands.
