# EBS, EFS & Glacier — Block and File Storage Deep Dive

## EBS — Elastic Block Store

EBS provides persistent block storage volumes for EC2. Think of it as a network-attached hard drive.

### Volume Types

| Type | IOPS | Throughput | Use Case |
|------|------|-----------|---------|
| gp3 | 3,000–16,000 | 125–1,000 MB/s | General purpose, OS, dev/test |
| gp2 | 3 IOPS/GB, up to 16,000 | 250 MB/s | Legacy general purpose |
| io2 Block Express | Up to 256,000 | 4,000 MB/s | Critical databases (Oracle, SAP) |
| io1/io2 | Up to 64,000 | 1,000 MB/s | I/O-intensive databases |
| st1 | 500 | 500 MB/s | Big data, Kafka, log processing |
| sc1 | 250 | 250 MB/s | Cold data, infrequent access |

**gp3 vs gp2**: gp3 is cheaper and lets you independently configure IOPS and throughput. Always prefer gp3.

### EBS Operations

```bash
# Create volume
aws ec2 create-volume \
  --availability-zone us-east-1a \
  --volume-type gp3 \
  --size 100 \
  --iops 6000 \
  --throughput 500 \
  --encrypted \
  --kms-key-id arn:aws:kms:us-east-1:123456789:key/abc-123

# Attach to instance
aws ec2 attach-volume \
  --volume-id vol-12345678 \
  --instance-id i-1234567890abcdef0 \
  --device /dev/xvdf

# From inside EC2 — format and mount
sudo mkfs -t xfs /dev/xvdf
sudo mkdir /data
sudo mount /dev/xvdf /data

# Persist mount across reboots
echo "/dev/xvdf /data xfs defaults,nofail 0 2" | sudo tee -a /etc/fstab

# Modify volume (online, no downtime for gp3)
aws ec2 modify-volume \
  --volume-id vol-12345678 \
  --volume-type gp3 \
  --size 200 \
  --iops 10000

# Extend filesystem after resize
sudo xfs_growfs /data
```

### EBS Snapshots

```bash
# Create snapshot
aws ec2 create-snapshot \
  --volume-id vol-12345678 \
  --description "Daily backup $(date +%Y-%m-%d)" \
  --tag-specifications 'ResourceType=snapshot,Tags=[{Key=Name,Value=daily-backup}]'

# Copy snapshot to another region
aws ec2 copy-snapshot \
  --source-region us-east-1 \
  --source-snapshot-id snap-12345678 \
  --region eu-west-1 \
  --description "DR copy"

# Create volume from snapshot
aws ec2 create-volume \
  --snapshot-id snap-12345678 \
  --availability-zone us-east-1b \
  --volume-type gp3

# Automate with Data Lifecycle Manager
aws dlm create-lifecycle-policy \
  --description "Daily EBS snapshots" \
  --state ENABLED \
  --execution-role-arn arn:aws:iam::123456789:role/AWSDataLifecycleManagerDefaultRole \
  --policy-details '{
    "PolicyType": "EBS_SNAPSHOT_MANAGEMENT",
    "ResourceTypes": ["VOLUME"],
    "TargetTags": [{"Key": "Backup", "Value": "true"}],
    "Schedules": [{
      "Name": "Daily",
      "CreateRule": {"Interval": 24, "IntervalUnit": "HOURS", "Times": ["03:00"]},
      "RetainRule": {"Count": 7},
      "CopyTags": true
    }]
  }'
```

### EBS Multi-Attach

io1/io2 volumes can be attached to up to 16 instances in the same AZ simultaneously. Requires cluster-aware filesystem (not ext4/xfs).

```bash
aws ec2 attach-volume \
  --volume-id vol-12345678 \
  --instance-id i-second-instance \
  --device /dev/xvdf
```

---

## EFS — Elastic File System

EFS is a managed NFS (Network File System) that can be mounted on multiple EC2 instances simultaneously across AZs.

```
EFS File System
├── Mount Targets (one per AZ)
│   ├── us-east-1a: 10.0.1.100
│   ├── us-east-1b: 10.0.2.100
│   └── us-east-1c: 10.0.3.100
└── Access Points (application-specific entry points)
```

### EFS vs EBS

| Feature | EFS | EBS |
|---------|-----|-----|
| Type | File (NFS) | Block |
| Multi-instance | ✅ Thousands | ❌ Single (io2 multi-attach: 16) |
| Cross-AZ | ✅ Yes | ❌ Single AZ |
| Scaling | Automatic | Manual |
| Performance | Scales with size | Configurable |
| Cost | ~$0.30/GB | ~$0.08/GB (gp3) |
| Use case | Shared content, CMS, home dirs | OS, databases |

### EFS Setup

```bash
# Create EFS file system
aws efs create-file-system \
  --performance-mode generalPurpose \
  --throughput-mode elastic \
  --encrypted \
  --tags Key=Name,Value=shared-storage

# Create mount targets (one per AZ)
aws efs create-mount-target \
  --file-system-id fs-12345678 \
  --subnet-id subnet-aaa \
  --security-groups sg-efs-12345678

# Mount on EC2
sudo yum install -y amazon-efs-utils
sudo mkdir /shared
sudo mount -t efs -o tls fs-12345678:/ /shared

# Persist in /etc/fstab
echo "fs-12345678:/ /shared efs _netdev,tls 0 0" | sudo tee -a /etc/fstab
```

### EFS Storage Classes

```bash
# Enable Intelligent Tiering (auto-moves infrequent files to EFS-IA)
aws efs put-lifecycle-configuration \
  --file-system-id fs-12345678 \
  --lifecycle-policies \
    TransitionToIA=AFTER_30_DAYS \
    TransitionToPrimaryStorageClass=AFTER_1_ACCESS
```

### EFS Access Points

```bash
# Create access point (enforces user/group, root directory)
aws efs create-access-point \
  --file-system-id fs-12345678 \
  --posix-user Uid=1000,Gid=1000 \
  --root-directory '{
    "Path": "/app-data",
    "CreationInfo": {
      "OwnerUid": 1000,
      "OwnerGid": 1000,
      "Permissions": "755"
    }
  }'
```

---

## S3 Glacier — Archival Storage

Glacier is for long-term archival storage where retrieval time is acceptable.

### Glacier Retrieval Options

| Option | Time | Cost |
|--------|------|------|
| Expedited | 1-5 minutes | $0.03/GB + $0.01/1000 req |
| Standard | 3-5 hours | $0.01/GB + $0.0025/1000 req |
| Bulk | 5-12 hours | $0.0025/GB + $0.00025/1000 req |

### Glacier via S3 Lifecycle (Recommended)

```bash
# Move to Glacier via S3 lifecycle (see S3 module)
# Direct Glacier API (legacy Glacier Vaults)
aws glacier create-vault \
  --account-id - \
  --vault-name my-archive

aws glacier upload-archive \
  --account-id - \
  --vault-name my-archive \
  --body archive.tar.gz

# Initiate retrieval job
aws glacier initiate-job \
  --account-id - \
  --vault-name my-archive \
  --job-parameters '{
    "Type": "archive-retrieval",
    "ArchiveId": "archive-id-here",
    "Tier": "Standard",
    "SNSTopic": "arn:aws:sns:us-east-1:123456789:glacier-notifications"
  }'
```

---

## Storage Decision Guide

```
Need to store files/objects?
├── Frequently accessed → S3 Standard
├── Infrequently accessed → S3 Standard-IA
├── Archive (instant retrieval) → S3 Glacier Instant
├── Archive (hours OK) → S3 Glacier Flexible
└── Long-term compliance → S3 Glacier Deep Archive

Need block storage for EC2?
├── OS/general → EBS gp3
├── High IOPS database → EBS io2
├── Big data/streaming → EBS st1
└── Cold data → EBS sc1

Need shared file storage?
├── Multiple EC2 instances → EFS
├── Windows file shares → FSx for Windows
├── High-performance HPC → FSx for Lustre
└── NetApp ONTAP → FSx for NetApp ONTAP
```

---

## Interview Q&A

### Q1: What is the difference between EBS and EFS?
**EBS**: Block storage, attached to a single EC2 instance (except io2 multi-attach), single AZ, like a hard drive. Best for OS, databases, applications needing low-latency block I/O.
**EFS**: Network file system (NFS), mounted by thousands of instances simultaneously, spans multiple AZs, automatically scales. Best for shared content, CMS, home directories, container storage.

### Q2: What happens to EBS data when an EC2 instance is terminated?
Root EBS volume: deleted by default (`DeleteOnTermination=true`). Additional EBS volumes: persist by default (`DeleteOnTermination=false`). You can change this behavior at launch or while running. Instance store volumes: always deleted on termination (ephemeral).

### Q3: How do EBS snapshots work?
Snapshots are incremental backups stored in S3 (managed by AWS). First snapshot copies all data. Subsequent snapshots only copy changed blocks. Restoring creates a new volume from the snapshot. Snapshots can be copied across regions for DR. Use Data Lifecycle Manager to automate snapshot schedules and retention.

### Q4: When would you use EFS over S3?
EFS when: you need a POSIX-compliant filesystem, applications use file system APIs (open/read/write/seek), you need shared access from multiple EC2 instances simultaneously, you're running containers needing persistent shared storage.
S3 when: storing objects/files accessed via HTTP API, static website hosting, data lake, backups, CDN origin.

### Q5: What is EBS-optimized and why does it matter?
EBS-optimized instances have dedicated network bandwidth between EC2 and EBS, preventing EBS I/O from competing with regular network traffic. Most modern instance types are EBS-optimized by default. Critical for I/O-intensive workloads (databases) — without it, network contention can cause unpredictable EBS performance.
