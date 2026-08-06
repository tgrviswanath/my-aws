# AWS Console UI Steps — Python Automation with boto3

> **Method:** AWS Management Console (browser-based) + local terminal
> **Estimated time:** 25–35 minutes
> **Difficulty:** Beginner–Intermediate

---

## Prerequisites Check

Before starting, confirm these are ready in your terminal:

```bash
# Python 3.8+
python3 --version

# pip
pip --version

# AWS CLI
aws --version

# boto3 (install if missing)
python3 -c "import boto3; print('boto3', boto3.__version__)" 2>/dev/null \
  || pip install boto3
```

- [ ] Python 3.8 or newer installed
- [ ] AWS CLI v2 installed and `aws configure` has been run (or you have IAM role on EC2)
- [ ] boto3 installed: `pip install boto3`
- [ ] Logged into [AWS Console](https://console.aws.amazon.com) with IAM permissions

---

## Step 1: Create an IAM Role/User for boto3

boto3 needs AWS credentials. The right credential source depends on where your script runs.

### Decision Point 1: IAM Role vs IAM Access Key

| Scenario | Recommended Method |
|----------|------------------|
| Script runs on your local machine | IAM user + access key (`aws configure`) ✅ |
| Script runs on an EC2 instance | IAM Instance Profile (role attached to EC2) ✅ |
| Script runs in Lambda | IAM Execution Role ✅ |
| Script runs in GitHub Actions CI/CD | OIDC federation (no long-term keys) ✅ |

**For this project:** We'll create an IAM user with an access key for local use, AND a role for EC2 use.

---

### 1A: Create IAM User (for local scripts)

1. AWS Console search → **IAM**
2. Left sidebar → **Users** → **Create user**
3. **User name:** `boto3-local-user`
4. Do NOT check "Provide user access to the AWS Management Console" (programmatic only)
5. Click **Next**

**Attach permissions:**
- Click **Attach policies directly**
- Search and select:
  - `AmazonEC2ReadOnlyAccess` ✅
  - `AmazonS3FullAccess` ✅
  - `AmazonRDSReadOnlyAccess` ✅

Click **Next** → **Create user**

📸 **Screenshot checkpoint:** User `boto3-local-user` created with the three policies attached.

### 1B: Create Access Key

1. Click on `boto3-local-user` to open the user
2. Click **Security credentials** tab
3. Scroll to **Access keys** → click **Create access key**
4. **Use case:** Select **Command Line Interface (CLI)**
5. Check the confirmation checkbox
6. Click **Next** → **Create access key**
7. **IMPORTANT:** Copy and save both:
   - **Access key ID** (e.g., `YOUR_ACCESS_KEY_ID`)
   - **Secret access key** (visible only once!)
8. Click **Download .csv file** → save it securely
9. Click **Done**

📸 **Screenshot checkpoint:** Access key creation page showing the Access key ID and the secret access key visible (before closing).

> ⚠️ The secret access key is shown only once. If you close this page without saving it, you must create a new access key.

---

### 1C: Create IAM Role (for EC2 Instance Profile)

1. IAM → Left sidebar → **Roles** → **Create role**
2. **Trusted entity type:** AWS service
3. **Service:** EC2 → click **Next**
4. Attach policies (same as above):
   - `AmazonEC2ReadOnlyAccess`
   - `AmazonS3FullAccess`
   - `AmazonRDSReadOnlyAccess`
5. **Role name:** `boto3-ec2-automation-role`
6. **Description:** `Role for boto3 automation scripts running on EC2`
7. Click **Create role**

📸 **Screenshot checkpoint:** Role `boto3-ec2-automation-role` created with the three policies listed in the Permissions tab.

### 1D: Attach Role to an EC2 Instance (if running on EC2)

1. EC2 → Instances → select your instance
2. **Actions** → **Security** → **Modify IAM role**
3. Select `boto3-ec2-automation-role`
4. Click **Update IAM role**

📸 **Screenshot checkpoint:** EC2 instance detail showing the IAM role `boto3-ec2-automation-role` in the Security tab.

---

### Troubleshooting — Step 1

**Can't create an access key**
- You may need permission from an admin to create access keys
- Some organizations restrict programmatic access keys — check your org's policy

**"This action is not allowed" when attaching policies**
- Your current IAM user lacks `iam:AttachUserPolicy`
- Ask your AWS admin to attach the policies for you

---

## Step 2: Configure AWS CLI with the Access Key

This step is for **local machine use** (skip if you're on EC2 with an instance profile).

### 2.1 — Run aws configure

Open your terminal:

```bash
aws configure
```

Enter the values from the `.csv` file you downloaded:

```
AWS Access Key ID [None]: YOUR_ACCESS_KEY_ID
AWS Secret Access Key [None]: YOUR_SECRET_ACCESS_KEY
Default region name [None]: us-east-1
Default output format [None]: json
```

### 2.2 — Verify Configuration

```bash
# Check stored credentials (shows key ID, not secret)
aws configure list

# Test with a real API call
aws sts get-caller-identity
```

**Expected output:**
```json
{
    "UserId": "AIDAIOSFODNN7EXAMPLE",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/boto3-local-user"
}
```

📸 **Screenshot checkpoint:** Terminal showing `aws configure list` with the profile name, access key (obfuscated), and region visible.

---

### Troubleshooting — Step 2

**Error: "Unable to locate credentials"**
- `aws configure` wasn't run, or you're in a different profile
- Check: `cat ~/.aws/credentials` (Linux/macOS) or `type %USERPROFILE%\.aws\credentials` (Windows)

**Error: "InvalidClientTokenId"**
- Access key ID is incorrect or the key has been deactivated
- Create a new access key in IAM console

**Error: "SignatureDoesNotMatch"**
- Secret access key is incorrect
- Delete and recreate the access key

---

## Step 3: Install boto3 and Test

### 3.1 — Set Up a Virtual Environment (Recommended)

```bash
# Create project folder
mkdir my-boto3-scripts && cd my-boto3-scripts

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate       # Linux/macOS
# venv\Scripts\activate.bat    # Windows CMD
# venv\Scripts\Activate.ps1    # Windows PowerShell

# Install boto3
pip install boto3

# Verify
python3 -c "import boto3; print('boto3 version:', boto3.__version__)"
```

### 3.2 — Run First boto3 Script

Create and run a simple test:

```bash
# Create a test script
cat > test_boto3.py << 'EOF'
import boto3

# Test EC2 - list regions
ec2 = boto3.client('ec2', region_name='us-east-1')
regions = ec2.describe_regions()
print(f"EC2 accessible. Found {len(regions['Regions'])} regions.")

# Test S3 - list buckets
s3 = boto3.client('s3')
buckets = s3.list_buckets()
print(f"S3 accessible. Found {len(buckets['Buckets'])} buckets.")

# Test RDS - list instances
rds = boto3.client('rds', region_name='us-east-1')
dbs = rds.describe_db_instances()
print(f"RDS accessible. Found {len(dbs['DBInstances'])} DB instances.")

print("\n✅ boto3 is working correctly with your AWS credentials!")
EOF

python3 test_boto3.py
```

📸 **Screenshot checkpoint:** Terminal showing the test script output confirming EC2, S3, and RDS are all accessible.

---

### Troubleshooting — Step 3

**Error: "botocore.exceptions.NoCredentialsError"**
- `aws configure` wasn't run, or the virtual environment is using a different Python than expected
- Run `aws configure` again from the same terminal session

**Error: "botocore.exceptions.ClientError: An error occurred (AccessDenied)"**
- The IAM user lacks permissions for that service
- In IAM Console, check attached policies for `boto3-local-user`

**Error: "ModuleNotFoundError: No module named 'boto3'"**
- boto3 not installed in the current Python environment
- Run: `pip install boto3` and retry

---

## Step 4: Run the Automation Scripts

### 4.1 — Run EC2 Inventory Script

```bash
# List all EC2 instances
python3 ec2/list_instances.py
```

**Expected output (if instances exist):**
```
ID                   State        Type           Name                      Public IP
------------------------------------------------------------------------------------------
i-0abc123def456789   running      t2.micro       web-server-01             54.123.45.67
i-0def456abc789012   stopped      t3.small       dev-machine               N/A
```

If no instances exist, the output will be empty (just the header line) — that's fine.

📸 **Screenshot checkpoint:** Terminal showing the EC2 list output with instance details.

### 4.2 — Run S3 File Operations

```bash
# Create a test file
echo "<h1>Hello from boto3!</h1>" > test_upload.html

# Upload to S3 (replace with your bucket name)
python3 -c "
import boto3
s3 = boto3.client('s3')

# Create a test bucket first
import random, string
bucket_name = 'boto3-test-' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
s3.create_bucket(Bucket=bucket_name)
print(f'Created bucket: {bucket_name}')

# Upload
s3.upload_file('test_upload.html', bucket_name, 'index.html')
print('Uploaded index.html')

# List
response = s3.list_objects_v2(Bucket=bucket_name)
for obj in response.get('Contents', []):
    print(f'  s3://{bucket_name}/{obj[\"Key\"]} ({obj[\"Size\"]} bytes)')

# Download
s3.download_file(bucket_name, 'index.html', '/tmp/downloaded.html')
print('Downloaded to /tmp/downloaded.html')

# Cleanup test bucket
s3.delete_object(Bucket=bucket_name, Key='index.html')
s3.delete_bucket(Bucket=bucket_name)
print(f'Cleaned up bucket: {bucket_name}')
"
```

📸 **Screenshot checkpoint:** Terminal showing bucket creation, upload, list, download, and cleanup — all succeeding.

### 4.3 — Run Inventory Report

```bash
python3 utils/inventory_report.py
```

**Expected output:**
```json
{
  "generated_at": "2024-01-15T10:30:00.000000",
  "region": "us-east-1",
  "ec2": {
    "instances": [...]
  },
  "s3": {
    "buckets": [...]
  },
  "rds": {
    "instances": [...]
  }
}

Summary:
  EC2: 2 instances
  S3:  3 buckets
  RDS: 1 instances
```

---

## Step 5: Verify IAM Permissions in Console

After running the scripts, verify what was accessed in IAM:

1. IAM → Users → `boto3-local-user` → **Access Advisor** tab
2. You'll see which services were accessed and when
3. Services not accessed can have their permissions removed (least privilege)

📸 **Screenshot checkpoint:** IAM Access Advisor showing S3, EC2, and RDS as recently accessed services.

---

## Final Expected Outcome

After completing all 5 steps:

- [ ] IAM user `boto3-local-user` created with EC2/S3/RDS read/write policies
- [ ] Access key downloaded and saved securely
- [ ] `aws configure` completed with the access key
- [ ] `aws sts get-caller-identity` returns your account info
- [ ] `python3 -c "import boto3"` works without errors
- [ ] EC2 list script runs and shows instances (or empty list if no instances)
- [ ] S3 operations (create, upload, list, download, delete) all succeed
- [ ] Inventory report generates valid JSON output
- [ ] IAM Access Advisor shows S3, EC2, RDS were accessed

**Your boto3 setup is now:**
- Authenticated via IAM credentials
- Able to automate EC2, S3, and RDS operations programmatically
- Ready for building automation scripts, scheduled jobs (cron), or Lambda functions
- A foundation for infrastructure-as-code and DevOps automation
