# EC2 — Elastic Compute Cloud Deep Dive

## What is EC2?
EC2 provides resizable virtual machines (instances) in the cloud. You choose the OS, CPU, memory, storage, and networking. EC2 is the backbone of most AWS architectures.

---

## Instance Types

| Family | Purpose | Examples |
|--------|---------|---------|
| General Purpose | Balanced CPU/memory | t3, t4g, m5, m6i |
| Compute Optimized | High CPU | c5, c6i, c6g |
| Memory Optimized | High RAM | r5, r6i, x1e, z1d |
| Storage Optimized | High I/O | i3, i4i, d3 |
| Accelerated | GPU/FPGA | p4, g5, inf2, f1 |
| HPC | High-performance compute | hpc6a |

### Naming Convention
```
m  5  .  x  large
│  │     │  └── Size: nano/micro/small/medium/large/xlarge/2xlarge...
│  │     └── (optional) attribute: a=AMD, g=Graviton, n=network-optimized
│  └── Generation: higher = newer
└── Family: m=general, c=compute, r=memory, i=storage, p=GPU
```

### T-series Burstable Instances
- Earn CPU credits when idle, spend when busy
- `t3.micro` baseline: 10% CPU, can burst to 100%
- `T3 Unlimited`: pay for extra credits beyond baseline
- Best for: dev/test, low-traffic web servers, microservices

---

## AMI (Amazon Machine Image)

An AMI is a template containing OS, application server, and applications.

```
AMI contains:
├── Root volume snapshot (OS + software)
├── Launch permissions (who can use it)
└── Block device mapping (EBS volumes to attach)
```

### AMI Types
| Type | Description |
|------|-------------|
| AWS-provided | Amazon Linux 2, Ubuntu, Windows Server |
| AWS Marketplace | Pre-configured vendor images (Nginx, Splunk) |
| Community | Public AMIs from other users |
| Custom | Your own AMIs (golden images) |

### Creating a Custom AMI (Golden Image)
```bash
# 1. Launch base instance, configure it
# 2. Create AMI
aws ec2 create-image \
  --instance-id i-1234567890abcdef0 \
  --name "MyApp-v1.0-$(date +%Y%m%d)" \
  --description "Production golden image" \
  --no-reboot

# 3. Copy AMI to another region
aws ec2 copy-image \
  --source-image-id ami-0abc123 \
  --source-region us-east-1 \
  --region eu-west-1 \
  --name "MyApp-v1.0-eu"
```

---

## Storage Options for EC2

| Type | Use Case | Performance |
|------|---------|-------------|
| EBS gp3 | General purpose OS/data | 3000 IOPS baseline, up to 16000 |
| EBS io2 | Databases, high IOPS | Up to 64000 IOPS |
| EBS st1 | Throughput-heavy (Kafka, logs) | Up to 500 MB/s |
| EBS sc1 | Cold data, infrequent access | Up to 250 MB/s |
| Instance Store | Temp storage, cache, buffers | Highest IOPS, ephemeral |

**Key rule**: Instance store data is lost when instance stops/terminates. EBS persists.

---

## EC2 Lifecycle

```
Pending → Running → Stopping → Stopped → Terminated
                 ↘ Shutting-down → Terminated
```

- **Stop/Start**: New public IP assigned (unless Elastic IP)
- **Reboot**: Same public IP retained
- **Hibernate**: RAM saved to EBS, faster resume (must enable at launch)
- **Terminate**: Instance deleted, root EBS deleted by default

---

## Placement Groups

| Type | Behavior | Use Case |
|------|---------|---------|
| Cluster | Same rack, same AZ | Low latency HPC, 10Gbps between instances |
| Spread | Different racks | Critical instances, max 7 per AZ |
| Partition | Different partitions (racks) | Hadoop, Kafka, Cassandra |

```bash
# Create placement group
aws ec2 create-placement-group \
  --group-name my-cluster \
  --strategy cluster

# Launch into placement group
aws ec2 run-instances \
  --placement "GroupName=my-cluster" \
  --instance-type c5n.18xlarge \
  --image-id ami-0abc123
```

---

## User Data & Metadata

### User Data (bootstrap script)
```bash
#!/bin/bash
# Runs once at first launch as root
yum update -y
yum install -y httpd
systemctl start httpd
systemctl enable httpd
echo "<h1>Hello from $(hostname)</h1>" > /var/www/html/index.html
```

```bash
# Pass user data at launch
aws ec2 run-instances \
  --user-data file://bootstrap.sh \
  --image-id ami-0abc123 \
  --instance-type t3.micro
```

### Instance Metadata Service (IMDS)
```bash
# From inside the instance
# IMDSv1 (legacy, less secure)
curl http://169.254.169.254/latest/meta-data/instance-id
curl http://169.254.169.254/latest/meta-data/public-ipv4

# IMDSv2 (recommended — token-based)
TOKEN=$(curl -X PUT "http://169.254.169.254/latest/api/token" \
  -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
curl -H "X-aws-ec2-metadata-token: $TOKEN" \
  http://169.254.169.254/latest/meta-data/instance-id
```

**Best practice**: Enforce IMDSv2 only — prevents SSRF attacks from stealing credentials.

---

## Security Groups

- Stateful firewall at the instance level
- Default: deny all inbound, allow all outbound
- Rules are allow-only (no explicit deny)

```bash
# Create security group
aws ec2 create-security-group \
  --group-name web-sg \
  --description "Web server security group" \
  --vpc-id vpc-12345678

# Add inbound rules
aws ec2 authorize-security-group-ingress \
  --group-id sg-12345678 \
  --protocol tcp --port 80 --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
  --group-id sg-12345678 \
  --protocol tcp --port 443 --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
  --group-id sg-12345678 \
  --protocol tcp --port 22 --cidr 10.0.0.0/8
```

---

## Elastic IPs

```bash
# Allocate Elastic IP
aws ec2 allocate-address --domain vpc

# Associate with instance
aws ec2 associate-address \
  --instance-id i-1234567890abcdef0 \
  --allocation-id eipalloc-12345678

# Release (stop paying)
aws ec2 release-address --allocation-id eipalloc-12345678
```

**Cost**: Free when associated with running instance. $0.005/hr when unassociated.

---

## CloudFormation — EC2 Template

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: EC2 instance with security group

Parameters:
  InstanceType:
    Type: String
    Default: t3.micro
    AllowedValues: [t3.micro, t3.small, t3.medium]
  KeyName:
    Type: AWS::EC2::KeyPair::KeyName

Resources:
  WebServerSG:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: Web server security group
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 80
          ToPort: 80
          CidrIp: 0.0.0.0/0
        - IpProtocol: tcp
          FromPort: 443
          ToPort: 443
          CidrIp: 0.0.0.0/0

  WebServer:
    Type: AWS::EC2::Instance
    Properties:
      InstanceType: !Ref InstanceType
      ImageId: ami-0c02fb55956c7d316
      KeyName: !Ref KeyName
      SecurityGroupIds:
        - !Ref WebServerSG
      UserData:
        Fn::Base64: |
          #!/bin/bash
          yum update -y
          yum install -y httpd
          systemctl start httpd
          systemctl enable httpd
      Tags:
        - Key: Name
          Value: WebServer

Outputs:
  PublicIP:
    Value: !GetAtt WebServer.PublicIp
```

---

## Performance & Scalability

- **Enhanced Networking**: Use ENA (Elastic Network Adapter) for up to 100 Gbps
- **EBS-Optimized**: Dedicated bandwidth between EC2 and EBS
- **SR-IOV**: Hardware-level network virtualization for lower latency
- **Nitro System**: AWS hypervisor — near bare-metal performance

### Right-sizing
```bash
# Use Compute Optimizer
aws compute-optimizer get-ec2-instance-recommendations \
  --account-ids 123456789012

# Check CloudWatch metrics for right-sizing
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=i-1234567890abcdef0 \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-31T00:00:00Z \
  --period 86400 \
  --statistics Average
```

---

## Security Best Practices

1. **Never use root account** — create IAM users/roles
2. **Use IAM Instance Profiles** — never store credentials on EC2
3. **Enforce IMDSv2** — prevent SSRF credential theft
4. **Disable SSH password auth** — use key pairs only
5. **Use Systems Manager Session Manager** — no SSH port needed
6. **Enable VPC Flow Logs** — audit network traffic
7. **Patch regularly** — use Systems Manager Patch Manager

```bash
# Connect via SSM (no SSH needed)
aws ssm start-session --target i-1234567890abcdef0

# Enforce IMDSv2 on existing instance
aws ec2 modify-instance-metadata-options \
  --instance-id i-1234567890abcdef0 \
  --http-tokens required \
  --http-endpoint enabled
```

---

## Common Pitfalls

| Pitfall | Solution |
|---------|---------|
| Instance store data lost on stop | Use EBS for persistent data |
| Public IP changes on restart | Use Elastic IP or Route 53 |
| Security group too permissive (0.0.0.0/0 SSH) | Restrict to known IPs or use SSM |
| Storing credentials in user data | Use IAM Instance Profile |
| Not using IMDSv2 | Enforce via instance metadata options |
| Over-provisioned instances | Use Compute Optimizer + Auto Scaling |

---

## Interview Q&A

### Q1: What is the difference between stopping and terminating an EC2 instance?
**Stop**: Instance shuts down, EBS root volume persists, you stop paying for compute (still pay for EBS). Can restart later. Gets new public IP on restart.
**Terminate**: Instance is permanently deleted. Root EBS volume deleted by default (unless `DeleteOnTermination=false`). Cannot recover.

### Q2: What is an AMI and how do you create a golden image strategy?
AMI = snapshot of an EC2 instance (OS + software + config). Golden image strategy: maintain a base AMI with all security patches, monitoring agents, and standard software pre-installed. Bake new AMIs on each release. Use AWS Image Builder to automate. Benefits: faster launch, consistent config, no configuration drift.

### Q3: How does EC2 instance metadata work and what are the security implications?
IMDS runs at 169.254.169.254. Provides instance ID, IAM credentials, user data, etc. IMDSv1 is vulnerable to SSRF — attacker can steal IAM credentials via a web app that fetches arbitrary URLs. IMDSv2 requires a PUT request to get a token first, preventing SSRF exploitation. Always enforce IMDSv2.

### Q4: What is the difference between a Security Group and a NACL?
Security Group: stateful, instance-level, allow rules only, evaluated as a whole.
NACL: stateless (must allow both inbound and outbound), subnet-level, allow and deny rules, evaluated in order by rule number.

### Q5: When would you use a Spot instance vs Reserved instance?
**Spot**: Fault-tolerant batch jobs, big data processing, CI/CD workers, stateless web servers with Auto Scaling. Up to 90% savings but can be interrupted with 2-min notice.
**Reserved**: Steady-state production databases, application servers with predictable load. 1-3 year commitment, up to 72% savings, no interruption risk.

### Q6: What is EC2 Hibernate and when would you use it?
Hibernate saves RAM contents to EBS, then stops the instance. On restart, RAM is restored — much faster than a cold boot. Use for: long-running processes that take time to warm up (in-memory caches, ML model loading). Requirements: EBS root volume must be encrypted, instance RAM ≤ 150GB.
