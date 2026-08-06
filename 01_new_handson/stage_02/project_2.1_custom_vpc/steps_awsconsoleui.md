# AWS Console UI — Step-by-Step Guide
# Project 2.1: Custom VPC with Public and Private Subnets

> Method: AWS Management Console only (no CLI)
> Region: us-east-1 (N. Virginia)
> Estimated time: 30–45 minutes

---

## Prerequisites Check

Before opening the console, confirm:

- [ ] AWS account is active and you can log in
- [ ] IAM user/role has `VPC:*` and `EC2:*` permissions
- [ ] You know your region (this guide uses **us-east-1**)
- [ ] You have a key pair in us-east-1 (EC2 → Key Pairs)
- [ ] NAT Gateway will incur charges — have billing alerts set up

**Verify your permissions:**
1. Go to **IAM → Users → your user → Permissions**
2. Confirm `AmazonVPCFullAccess` or equivalent policy is attached
3. Go to **EC2 → Key Pairs** — confirm at least one key pair exists

---

## Step 1 — Create VPC

### Decision Point 1: VPC Wizard vs Manual Creation

| Option | Pros | Cons |
|--------|------|------|
| ✅ VPC Wizard ("VPC and more") | Creates subnets, IGW, route tables automatically | Less learning value |
| ✅ Manual (this guide) | Full understanding of each component | More steps |

**We use Manual** to understand each resource independently.

---

### Console Actions

1. Log into **AWS Console** → search for **VPC** in the top search bar
2. Click **Your VPCs** in the left sidebar
3. Click the orange **Create VPC** button (top right)
4. Configure:
   - **Resources to create:** VPC only
   - **Name tag:** `handson-vpc`
   - **IPv4 CIDR block:** `10.0.0.0/16`
   - **IPv6 CIDR block:** No IPv6 CIDR block
   - **Tenancy:** Default
5. Click **Create VPC**

### 📸 Screenshot
> Capture: VPC creation confirmation page showing VPC ID (e.g., `vpc-0abc123`) and CIDR `10.0.0.0/16` with state **Available**

### Expected Outcome
- New VPC appears in Your VPCs list
- State shows **Available**
- CIDR block shows `10.0.0.0/16`
- DNS resolution and DNS hostnames are both enabled (check in Details tab)

### Troubleshooting
| Issue | Cause | Fix |
|-------|-------|-----|
| "CIDR block conflicts" | Another VPC uses overlapping range | Use a different CIDR like `10.1.0.0/16` |
| VPC not appearing | Wrong region selected | Check top-right region selector |
| "Limit exceeded" | Reached max VPCs (default 5 per region) | Delete unused VPCs or request limit increase |

---

## Step 2 — Create Subnets

### Decision Point 2: AZ Selection Strategy

| Strategy | Description | Recommendation |
|----------|-------------|----------------|
| Same AZ for all subnets | Lower latency between subnets | ✅ Dev/learning only |
| Different AZs | High availability if one AZ fails | ✅ Production |

**This guide uses:** public in `us-east-1a`, private in `us-east-1b` — teaching HA concepts without full cost.

---

### Create Public Subnet

1. Go to **VPC → Subnets** in left sidebar
2. Click **Create subnet**
3. Configure:
   - **VPC ID:** select `handson-vpc` from dropdown
   - **Subnet name:** `public-subnet-1a`
   - **Availability Zone:** `us-east-1a`
   - **IPv4 subnet CIDR block:** `10.0.1.0/24`
4. Click **Create subnet**

**Enable auto-assign public IP:**
1. Select `public-subnet-1a` checkbox
2. Click **Actions → Edit subnet settings**
3. Check **Enable auto-assign public IPv4 address**
4. Click **Save**

### Create Private Subnet

1. Click **Create subnet** again
2. Configure:
   - **VPC ID:** select `handson-vpc`
   - **Subnet name:** `private-subnet-1b`
   - **Availability Zone:** `us-east-1b`
   - **IPv4 subnet CIDR block:** `10.0.2.0/24`
3. Click **Create subnet**
4. Do NOT enable auto-assign public IP for this subnet

### 📸 Screenshot
> Capture: Subnets list filtered by `handson-vpc` showing both subnets with their CIDRs, AZs, and available IP counts (~251 each)

### Expected Outcome
- Two subnets visible in the list
- `public-subnet-1a`: CIDR `10.0.1.0/24`, AZ `us-east-1a`, auto-assign public IP: Yes
- `private-subnet-1b`: CIDR `10.0.2.0/24`, AZ `us-east-1b`, auto-assign public IP: No

### Troubleshooting
| Issue | Cause | Fix |
|-------|-------|-----|
| "CIDR conflicts with existing subnet" | Overlapping CIDR in same VPC | Subnets within same VPC cannot overlap |
| AZ not available | AZ disabled for your account | Try `us-east-1c` or `us-east-1d` |
| Can't find VPC in dropdown | VPC not created yet | Complete Step 1 first |

---

## Step 3 — Create Internet Gateway

### Console Actions

1. Go to **VPC → Internet Gateways** in left sidebar
2. Click **Create internet gateway**
3. Configure:
   - **Name tag:** `handson-igw`
4. Click **Create internet gateway**

**Attach IGW to VPC:**
1. You'll see a green banner: *"Attach to a VPC"* — click it, OR
2. Select `handson-igw` → **Actions → Attach to VPC**
3. Select `handson-vpc` from dropdown
4. Click **Attach internet gateway**

### 📸 Screenshot
> Capture: Internet Gateways list showing `handson-igw` with State **Attached** and VPC ID matching your `handson-vpc`

### Expected Outcome
- IGW state changes from **Detached** to **Attached**
- VPC ID column shows your `handson-vpc`'s ID

### Troubleshooting
| Issue | Cause | Fix |
|-------|-------|-----|
| "Resource already associated" | VPC already has an IGW attached | One VPC can only have one IGW |
| IGW state stays "Detached" | Forgot to attach | Use Actions → Attach to VPC |
| Can't see the attach option | Wrong IAM permissions | Need `ec2:AttachInternetGateway` permission |

---

## Step 4 — Create NAT Gateway

> ⚠️ **COST WARNING:** NAT Gateway costs ~$0.045/hr (~$32/month) plus $0.045/GB data processed.
> Delete it after the hands-on exercise to avoid charges.

### Decision Point 3: NAT Gateway vs NAT Instance

| Option | Management | Cost | Bandwidth | Recommendation |
|--------|-----------|------|-----------|----------------|
| ✅ NAT Gateway | Fully managed by AWS | ~$32/month | Up to 45 Gbps | Production & learning |
| ❌ NAT Instance | You manage (patching, HA) | EC2 cost (~$8/month t2.micro) | Limited by instance type | Legacy only |

**Use NAT Gateway** — NAT Instances are legacy and require manual management.

---

### Console Actions

**First, allocate an Elastic IP:**
1. Go to **EC2 → Elastic IPs** (under Network & Security)
2. Click **Allocate Elastic IP address**
3. Leave defaults (Amazon's pool)
4. Click **Allocate**
5. Note the Allocation ID (e.g., `eipalloc-0abc123`) — you'll need it

**Create NAT Gateway:**
1. Go to **VPC → NAT Gateways**
2. Click **Create NAT gateway**
3. Configure:
   - **Name:** `handson-nat-gw`
   - **Subnet:** `public-subnet-1a` ← MUST be the public subnet
   - **Connectivity type:** Public
   - **Elastic IP allocation ID:** select the EIP you just created
4. Click **Create NAT gateway**
5. Wait ~2 minutes — refresh until state shows **Available**

### 📸 Screenshot
> Capture: NAT Gateways list showing `handson-nat-gw` in **Available** state, with Elastic IP shown, placed in `public-subnet-1a`

### Expected Outcome
- NAT Gateway state: **Available**
- Subnet: `public-subnet-1a`
- Elastic IP is assigned and visible

### Troubleshooting
| Issue | Cause | Fix |
|-------|-------|-----|
| NAT GW stuck "Pending" | Normal — takes up to 3 minutes | Wait and refresh |
| "No Elastic IPs available" | Need to allocate first | EC2 → Elastic IPs → Allocate |
| Private EC2 can't reach internet | NAT GW in wrong subnet | NAT GW must be in public subnet (has IGW route) |
| NAT GW created in private subnet | Common mistake | Delete and recreate in public subnet |

---

## Step 5 — Configure Route Tables

### Console Actions

**Create Public Route Table:**
1. Go to **VPC → Route Tables**
2. Click **Create route table**
3. Configure:
   - **Name:** `public-rt`
   - **VPC:** `handson-vpc`
4. Click **Create route table**

**Add route to IGW:**
1. Select `public-rt`
2. Click **Routes** tab → **Edit routes**
3. Click **Add route**
4. Destination: `0.0.0.0/0`
5. Target: **Internet Gateway** → select `handson-igw`
6. Click **Save changes**

**Associate with public subnet:**
1. Click **Subnet associations** tab → **Edit subnet associations**
2. Check `public-subnet-1a`
3. Click **Save associations**

---

**Create Private Route Table:**
1. Click **Create route table** again
2. Configure:
   - **Name:** `private-rt`
   - **VPC:** `handson-vpc`
3. Click **Create route table**

**Add route to NAT Gateway:**
1. Select `private-rt`
2. Click **Routes** tab → **Edit routes**
3. Click **Add route**
4. Destination: `0.0.0.0/0`
5. Target: **NAT Gateway** → select `handson-nat-gw`
6. Click **Save changes**

**Associate with private subnet:**
1. Click **Subnet associations** tab → **Edit subnet associations**
2. Check `private-subnet-1b`
3. Click **Save associations**

### 📸 Screenshot
> Capture 1: `public-rt` Routes tab showing two entries: `10.0.0.0/16 → local` and `0.0.0.0/0 → igw-xxxx`
> Capture 2: `private-rt` Routes tab showing: `10.0.0.0/16 → local` and `0.0.0.0/0 → nat-xxxx`
> Capture 3: Subnet associations confirming each route table is linked to the correct subnet

### Expected Outcome
- `public-rt` has default route to IGW, associated with `public-subnet-1a`
- `private-rt` has default route to NAT GW, associated with `private-subnet-1b`
- Both route tables show the local route `10.0.0.0/16 → local` (auto-added)

### Troubleshooting
| Issue | Cause | Fix |
|-------|-------|-----|
| Route saved but traffic not flowing | Subnet not associated | Check Subnet associations tab |
| Cannot select NAT GW as target | NAT GW not yet Available | Wait for NAT GW state = Available |
| Route table already has conflicting route | Duplicate destination CIDR | Remove the old route first |
| Both subnets using main route table | Custom RT not associated | Edit subnet associations on your custom RT |

---

## Summary Checklist

After completing all 5 steps, verify:

- [ ] VPC `handson-vpc` exists with CIDR `10.0.0.0/16`
- [ ] `public-subnet-1a` in us-east-1a, auto-assign public IP enabled
- [ ] `private-subnet-1b` in us-east-1b, auto-assign public IP disabled
- [ ] `handson-igw` attached to `handson-vpc`
- [ ] `handson-nat-gw` in Available state in `public-subnet-1a`
- [ ] `public-rt` has `0.0.0.0/0 → IGW` and is associated with `public-subnet-1a`
- [ ] `private-rt` has `0.0.0.0/0 → NAT GW` and is associated with `private-subnet-1b`

---

## Next Steps
- Deploy EC2 bastion in `public-subnet-1a` (see GUIDE.md § 5A)
- Deploy app EC2 in `private-subnet-1b`
- Test SSH through bastion and outbound internet from private subnet
- **Remember to clean up NAT Gateway** when done (see GUIDE.md § 10)

---

*Console UI guide for Project 2.1 — Stage 02 AWS Networking Hands-on*
