# Cost Estimate — Project 0.2: Linux Lab (WSL2 + CloudShell)

> **Total Estimated Cost: $0.00**  
> **AWS Free Tier Eligible: Yes (100%)**

---

## Service Cost Breakdown

| Service | Resource Used | Quantity | Unit Cost | Monthly Cost |
|---------|--------------|----------|-----------|--------------|
| AWS CloudShell | Compute environment | Free | Free | $0.00 |
| AWS CloudShell | Storage (1 GB included) | 1 GB | Free | $0.00 |
| AWS STS | `get-caller-identity` calls | ~10 calls | Free | $0.00 |
| AWS IAM | `list-users` API calls | ~5 calls | Free | $0.00 |
| WSL2 | Local software | 1 install | Free | $0.00 |
| Ubuntu (WSL2) | Local software | 1 install | Free | $0.00 |
| **Total** | | | | **$0.00** |

---

## Free Tier Details

### AWS CloudShell — Always Free
- CloudShell compute time is **always free** — no hourly charges
- **1 GB of persistent storage per region** is included at no cost
- Storage beyond 1 GB is not possible (hard limit, not a billing limit)
- CloudShell is not listed as a "Free Tier" service because it has no cost tier — it is simply free
- Sessions that are idle terminate automatically; no background charges

### AWS STS — Always Free
- `sts:GetCallerIdentity` has no charge
- All STS API calls are free

### AWS IAM — Always Free
- All IAM API calls (`list-users`, `get-user`, etc.) are free
- IAM has no cost model whatsoever

### WSL2 — Free Software
- WSL2 is a free feature of Windows 10/11
- Ubuntu from the Microsoft Store is free
- No subscription or license required

---

## CloudShell Storage Notes

CloudShell gives you **1 GB of persistent storage** in your home directory (`/home/cloudshell-user`). Files stored here persist between sessions. This is not a cost consideration — there is no charge regardless of how much of the 1 GB you use.

If you fill the 1 GB:
- CloudShell warns you when storage is near full
- You can delete files to free space
- You cannot pay for more storage — it's a hard limit
- Use S3 for larger file storage needs

---

## What Could Cost Money (But Doesn't in This Project)

| If You Had Done This | Potential Cost |
|---------------------|---------------|
| Launched an EC2 instance to use as Linux server | $0.0116/hour (t2.micro, outside free tier) |
| Used AWS Systems Manager Session Manager to access EC2 | Free, but the EC2 instance itself costs |
| Stored CloudShell output in S3 | $0.023/GB/month (after 5 GB free tier) |
| Used AWS Cloud9 IDE instead of CloudShell | EC2 charges for the underlying instance |

> This project uses only CloudShell (free) and WSL2 (local, free). No billable resources.

---

## Cleanup

### CloudShell Cleanup (Optional)
There is nothing to clean up in the traditional sense — CloudShell leaves no running resources. However:

```bash
# Delete practice files from CloudShell (optional)
rm -rf ~/linux-lab/
rm ~/*.txt ~/*.sh 2>/dev/null

# If you want to completely reset CloudShell storage:
# In Console: CloudShell → Actions → Delete AWS CloudShell home directory
```

### WSL2 Cleanup (Optional)
```powershell
# Remove Ubuntu distribution (all data will be lost)
wsl --unregister Ubuntu

# Remove WSL feature entirely
dism.exe /online /disable-feature /featurename:Microsoft-Windows-Subsystem-Linux
```

> **Recommendation:** Keep WSL2 and Ubuntu installed — you will use them in every subsequent project.

---

## Monthly Running Cost Summary

```
AWS CloudShell:         $0.00/month
CloudShell storage:     $0.00/month (1 GB included)
AWS API calls:          $0.00/month
WSL2 / Ubuntu:          $0.00/month
─────────────────────────────────────
Total:                  $0.00/month
Annual projection:      $0.00/year
```

**This is a zero-cost foundational project.**

---

*End of cost_estimate.md — Project 0.2*
