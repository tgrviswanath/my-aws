# Project 9.1 — AWS Data Lake Foundation
# Console UI Steps
# Region: ap-south-1 (Mumbai) | Account: 495331821583

---

> **Naming convention used throughout this file:**
> - Account ID: `495331821583` — replace with your own where shown
> - Generic placeholders used by Project 9.2: `YOUR_ACCOUNT_ID` → `495331821583`
> - Region: `ap-south-1` — Project 9.2 uses `us-east-1`; adapt region when following 9.2

---

## ⚠️ Project 9.2 Dependency Map — What This Project Must Produce

Project 9.2 (Glue ETL Pipeline) has a **Phase 0 Prerequisites** check that verifies the following resources exist.
Complete every step below **before** starting Project 9.2.

| Resource | Name to create in 9.1 | Verified in 9.2 |
|---|---|---|
| S3 bucket | `handson-data-lake-495331821583` | Step 0.2 |
| S3 folder — raw zone | `raw/orders/year=2024/month=01/day=15/orders.csv` | Step 0.2 |
| S3 folder — temp | `temp/` (required by Spark shuffle) | Step 2.6 |
| S3 folder — scripts | created by 9.2 itself | Step 1.2 |
| IAM role | `handson-glue-role-495331821583` (9.2 calls it `handson-glue-role`) | Step 0.1 |
| IAM policy attached | `AWSGlueServiceRole` + inline S3 policy | Step 0.1 |
| Glue database | `handson_data_lake_495331821583` (9.2 references as `handson_data_lake`) | Step 5 |
| Glue database | `raw_db_495331821583` | Step 5 |
| Sample data crawled | `orders` table in `raw_db_495331821583` | Step 5 |
| Athena workgroup | `handson-data-lake` with result location set | Step 5.3 |

> **Name alignment note:** Project 9.2 job parameters use `--database_name handson_data_lake`.
> The database you create here is `handson_data_lake_495331821583`.
> When entering job parameters in 9.2 Step 2.7, use the full name: `handson_data_lake_495331821583`.

---

## 5A. AWS Management Console Implementation

> Every step follows: Prerequisites Check → Navigate → Decision Points → Configure → Validate

---

### STEP A1 — Create the S3 Data Lake Bucket

**Prerequisites Check:**
- ✅ AWS Account: `495331821583` active
- ✅ Region: Asia Pacific (Mumbai) `ap-south-1` selected
- ✅ Required permissions: `s3:CreateBucket`, `s3:PutBucketPolicy`
- ✅ Services enabled: Amazon S3 (available globally)

**Step A1.1: Navigate to S3 Console**

1. Go to [S3 Console — Mumbai](https://s3.console.aws.amazon.com/s3/home?region=ap-south-1)
2. **Expected View:** S3 dashboard with **"Create bucket"** button in top-right
3. **If Different:** Ensure you're in `ap-south-1` region (check top-right region selector)

**📸 Screenshot A1a:** S3 console showing "Create bucket" button and Mumbai region selected

**Step A1.2: Initiate Bucket Creation**

1. Click the orange **"Create bucket"** button
2. **Expected View:** Bucket creation form with multiple configuration sections

**Step A1.3: Configure Bucket Name and Region**

**Decision Point 1:** Bucket naming strategy
| Naming Option | Use Case | For This Project |
|---------------|----------|-----------------|
| Simple name (e.g., `my-bucket`) | Risk of global name conflicts | ❌ Likely already taken |
| Account-based name | Guaranteed uniqueness | ✅ Use this |
| Random suffix | Harder to remember | ❌ Not needed |

| Field | Value | Explanation |
|-------|-------|-------------|
| Bucket name | `handson-data-lake-495331821583` | Uses your account ID for uniqueness |
| AWS Region | `Asia Pacific (Mumbai) ap-south-1` | Your selected region |

**Decision Point 2:** Object Ownership
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| ACLs enabled | Legacy applications | ❌ Not recommended |
| ACLs disabled (recommended) | Modern security model | ✅ Select this |

**Decision Point 3:** Public Access Settings
| Setting | Value | Explanation |
|---------|-------|-------------|
| Block all public access | ✅ Check all 4 boxes | Data lakes should never be public |
| Block public ACLs | ✅ Checked | Prevents accidental exposure |
| Ignore public ACLs | ✅ Checked | Security best practice |
| Block public bucket policies | ✅ Checked | Prevents policy-based exposure |
| Restrict cross-account access | ✅ Checked | Account-level security |

**Decision Point 4:** Versioning
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| Disable | Simple use cases | ❌ Risk of data loss |
| Enable | Production data protection | ✅ Select this |
| MFA Delete | High-security environments | ❌ Not needed for learning |

**Decision Point 5:** Encryption
| Option | Cost | Security | For This Project |
|--------|------|----------|-----------------|
| Amazon S3 managed keys (SSE-S3) | Free | Good | ✅ Select this |
| AWS KMS keys (SSE-KMS) | $1/month per key | Better | ❌ Unnecessary cost |
| Customer-provided keys | Free | Complex | ❌ Too complex |

**📸 Screenshot A1b:** Bucket configuration form with all settings filled in

**Step A1.4: Create and Validate**

1. Click **"Create bucket"** at the bottom
2. **Expected Outcome:** Green success banner: `"Successfully created bucket handson-data-lake-495331821583"`

**Troubleshooting:**
- `BucketAlreadyExists`: Name is taken — add a random suffix
- `AccessDenied`: Check IAM permissions for `s3:CreateBucket`

**📸 Screenshot A1c:** Success message showing bucket creation confirmed

---

### STEP A2 — Create the Zone Folder Structure

**Prerequisites Check:**
- ✅ S3 bucket created: `handson-data-lake-495331821583`
- ✅ Required permissions: `s3:PutObject`, `s3:ListBucket`
- ✅ Browser: Modern browser with JavaScript enabled

**Step A2.1: Navigate to Bucket**

1. Click on bucket name `handson-data-lake-495331821583`
2. **Expected View:** Empty bucket with **"Create folder"** button
3. **If Different:** Refresh page or check bucket name spelling

**Step A2.2: Plan Folder Structure**

**Decision Point 1:** Folder structure approach
| Approach | Use Case | For This Project |
|----------|----------|-----------------|
| Flat structure | Simple projects | ❌ Not scalable |
| Zone-based structure | Enterprise data lakes | ✅ Use this |
| Department-based | Multi-tenant | ❌ Single project |

| Folder Name | Purpose | Data Types | Required by 9.2 |
|-------------|---------|------------|----------------|
| `raw` | Ingested data as-is | CSV, JSON, logs | ✅ Yes — raw orders CSV |
| `processed` | Cleaned/transformed data | Parquet, optimized formats | ✅ Yes — ETL output target |
| `curated` | Business-ready datasets | Aggregated, joined data | — |
| `archive` | Long-term storage | Compressed historical data | — |
| `athena-results` | Query output storage | Query result files | ✅ Yes — Athena workgroup |
| `temp` | Spark shuffle/temp storage | Intermediate Spark files | ✅ Yes — Glue ETL `--TempDir` |
| `sparkhistory` | Spark UI logs | Job DAG visualisation logs | Optional (9.2 Step 2.6) |

**Step A2.3: Create Each Folder**

For each folder: click **"Create folder"** → enter name → click **"Create folder"**

**Folder 1: `raw`**
1. Click **"Create folder"**
2. Folder name: `raw`
3. Click **"Create folder"**

**Folder 2: `processed`**
1. Click **"Create folder"**
2. Folder name: `processed`
3. Click **"Create folder"**

**Folder 3: `curated`**
1. Click **"Create folder"**
2. Folder name: `curated`
3. Click **"Create folder"**

**Folder 4: `archive`**
1. Click **"Create folder"**
2. Folder name: `archive`
3. Click **"Create folder"**

**Folder 5: `athena-results`**
1. Click **"Create folder"**
2. Folder name: `athena-results`
3. Click **"Create folder"**

**Folder 6: `temp`** *(required by Project 9.2)*
1. Click **"Create folder"**
2. Folder name: `temp`
3. Click **"Create folder"**

> ⚠️ **Project 9.2 dependency:** The Glue ETL job parameter `--TempDir` must point to
> `s3://handson-data-lake-495331821583/temp/`. If this folder does not exist the job will fail.

**Folder 7: `sparkhistory`** *(optional — Spark UI logs)*
1. Click **"Create folder"**
2. Folder name: `sparkhistory`
3. Click **"Create folder"**

**Step A2.4: Validate Structure**

**Expected Outcome:** Bucket shows 7 folders in alphabetical order

**Troubleshooting:**
- If folder creation fails: Check `s3:PutObject` permissions
- If folders not visible: Refresh browser page

**📸 Screenshot A2:** All 7 zone folders visible in bucket (`raw`, `processed`, `curated`, `archive`, `athena-results`, `temp`, `sparkhistory`)

---

### STEP A3 — Configure S3 Lifecycle Policy

**Prerequisites Check:**
- ✅ S3 bucket exists with folder structure created
- ✅ Required permissions: `s3:PutLifecycleConfiguration`
- ✅ Understanding: Lifecycle policies reduce storage costs over time

**Step A3.1: Navigate to Lifecycle Management**

1. Stay in bucket `handson-data-lake-495331821583`
2. Click the **"Management"** tab
3. **Expected View:** Management dashboard with "Lifecycle rules" section
4. **If Different:** Ensure you're in the correct bucket

**📸 Screenshot A3a:** Management tab showing the Lifecycle rules section

**Step A3.2: Create Archive Rule for Raw Data**

1. Click **"Create lifecycle rule"**
2. **Expected View:** Lifecycle rule configuration wizard

**Decision Point 1:** Rule scope strategy
| Scope Type | Use Case | For This Project |
|------------|----------|-----------------|
| Entire bucket | Simple uniform policy | ❌ Different zones need different rules |
| Prefix-based | Zone-specific policies | ✅ Use this |
| Tag-based | Complex metadata scenarios | ❌ Unnecessary complexity |

**Decision Point 2:** Lifecycle actions
| Action Type | Purpose | For This Project |
|-------------|---------|-----------------|
| Transition current versions | Move to cheaper storage | ✅ Enable this |
| Transition noncurrent versions | Handle versioned objects | ❌ Skip for simplicity |
| Expire current versions | Delete old objects | ❌ Keep data for learning |
| Delete incomplete uploads | Cleanup failed uploads | ✅ Good practice |

**Decision Point 3:** Storage class selection
| Storage Class | Retrieval Time | Cost | For This Project |
|---------------|---------------|------|-----------------|
| S3 Standard-IA | Immediate | Medium | ✅ Use if Glacier unavailable |
| S3 One Zone-IA | Immediate | Lower | ❌ Less durable |
| S3 Glacier Flexible Retrieval | 1–5 minutes | Low | ✅ Preferred choice |
| S3 Glacier Deep Archive | 12 hours | Lowest | ❌ Too slow for learning |

**Rule 1 configuration:**

| Field | Value | Explanation |
|-------|-------|-------------|
| Lifecycle rule name | `archive-raw-data` | Descriptive name for raw zone |
| Choose a rule scope | Limit to specific prefixes or tags | Target only raw folder |
| Prefix | `raw/` | Applies to all objects in raw folder |
| Status | Enable | Rule is active |
| Storage class transition | S3 Glacier Flexible Retrieval (or S3 Standard-IA) | Cost-effective archive |
| Days after object creation | `30` | Balance between access and cost |

> If Glacier Flexible Retrieval is not available: use S3 Standard-IA with 30 days instead.

3. Click **"Create rule"**
4. **Expected Outcome:** Rule appears in the lifecycle rules list

**📸 Screenshot A3b:** Lifecycle rule creation form filled out for `archive-raw-data`

**Step A3.3: Create Cleanup Rule for Temporary Files**

1. Click **"Create lifecycle rule"** again

**Rule 2 configuration:**

| Field | Value | Explanation |
|-------|-------|-------------|
| Lifecycle rule name | `expire-temp-data` | Cleanup temporary files |
| Choose a rule scope | Limit to specific prefixes or tags | Target temp folder |
| Prefix | `temp/` | Applies to temporary files |
| Status | Enable | Rule is active |
| Lifecycle action | ✅ Expire current versions of objects | Delete after 7 days |
| Days after object creation | `7` | Delete temp files after 1 week |

2. Click **"Create rule"**

**Step A3.4: Validate Configuration**

**Expected Outcome:** Two lifecycle rules visible:
- `archive-raw-data` (Transition after 30 days)
- `expire-temp-data` (Expire after 7 days)

**Troubleshooting:**
- Rules not appearing: Refresh page
- Permission errors: Check `s3:PutLifecycleConfiguration`
- Invalid prefix: Ensure trailing slash in `raw/` and `temp/`

**📸 Screenshot A3c:** Management tab showing both lifecycle rules active

---

### STEP A4 — Create Glue IAM Role

**Prerequisites Check:**
- ✅ AWS Account: `495331821583` with IAM permissions
- ✅ Required permissions: `iam:CreateRole`, `iam:AttachRolePolicy`
- ✅ Understanding: IAM roles provide secure service-to-service access

**Step A4.1: Navigate to IAM Console**

1. Go to [IAM Console](https://console.aws.amazon.com/iam/)
2. **Expected View:** IAM dashboard with navigation sidebar
3. **If Different:** Check region (IAM is global but console shows regional URL)

**Step A4.2: Initiate Role Creation**

1. Left sidebar → **Roles**
2. Click **"Create role"**
3. **Expected View:** Role creation wizard with trusted entity selection

**📸 Screenshot A4a:** IAM Roles page with "Create role" button visible

**Step A4.3: Configure Trusted Entity**

**Decision Point 1:** Trusted entity type
| Entity Type | Use Case | For This Project |
|-------------|----------|-----------------|
| AWS service | Service assumes role | ✅ Select this |
| AWS account | Cross-account access | ❌ Not needed |
| Web identity | Federated access | ❌ Not needed |
| SAML 2.0 federation | Enterprise SSO | ❌ Not needed |

1. Select: ✅ **AWS service**

**Decision Point 2:** Service selection
| Service | Purpose | For This Project |
|---------|---------|-----------------|
| EC2 | Virtual machines | ❌ Not using EC2 |
| Lambda | Serverless functions | ❌ Not using Lambda |
| Glue | ETL and data catalog | ✅ Select this |
| S3 | Storage service | ❌ Glue will access S3 |

2. Scroll down to find **Glue** → select it
3. Click **"Next"**

**📸 Screenshot A4b:** Glue service selected as trusted entity

**Step A4.4: Attach Permissions Policies**

**Decision Point 3:** Policy selection strategy
| Approach | Security | Complexity | For This Project |
|----------|----------|------------|-----------------|
| AWS managed policies only | Good | Simple | ❌ Insufficient S3 access |
| Managed + Custom policies | Better | Medium | ✅ Use this |
| Custom policies only | Best | Complex | ❌ Unnecessary for learning |

1. Search for: `AWSGlueServiceRole`
2. **Expected View:** Policy with description "Provides access to resources needed by AWS Glue"
3. Check: ✅ `AWSGlueServiceRole`
4. Click **"Next"**

**Step A4.5: Configure Role Details**

| Field | Value | Explanation |
|-------|-------|-------------|
| Role name | `handson-glue-role-495331821583` | Include account ID for uniqueness |
| Description | `Glue service role for data lake project in Mumbai region - Account 495331821583` | Clear purpose description |

> **Project 9.2 dependency:** Project 9.2 refers to this role as `handson-glue-role` in its
> Phase 0 prerequisite check. Your full role name is `handson-glue-role-495331821583`.
> When configuring the Glue ETL job in 9.2 Step 2.4 (IAM Role field), select this exact role.

1. Click **"Create role"**
2. **Expected Outcome:** Success message and redirect to role details

**📸 Screenshot A4c:** Role creation success message

**Step A4.6: Add Custom S3 Inline Policy**

Why a custom policy is needed:
- `AWSGlueServiceRole` provides basic Glue permissions but no specific S3 bucket access
- Need to grant access to your specific bucket following least-privilege principle

1. Click on role name `handson-glue-role-495331821583`
2. **Expected View:** Role details page with Permissions tab
3. Click **"Add permissions"** → **"Create inline policy"**

**Decision Point 4:** Policy creation method
| Method | Ease of Use | Precision | For This Project |
|--------|-------------|-----------|-----------------|
| Visual editor | Easy | Limited | ❌ Complex permissions needed |
| JSON editor | Medium | Precise | ✅ Use this |
| Import from file | Easy | Precise | ❌ No existing file |

4. Click the **"JSON"** tab
5. Replace existing content with:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::handson-data-lake-495331821583",
        "arn:aws:s3:::handson-data-lake-495331821583/*"
      ],
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "ap-south-1"
        }
      }
    }
  ]
}
```

Policy permissions explained:
- `s3:GetObject` — Read files from bucket
- `s3:PutObject` — Write files to bucket
- `s3:DeleteObject` — Remove files (for ETL cleanup)
- `s3:ListBucket` — List bucket contents
- `Condition` — Restricts access to Mumbai region only

6. Click **"Next"**
7. Policy name: `glue-s3-access-495331821583`
8. Click **"Create policy"**

**Step A4.7: Validate Role Configuration**

**Expected Outcome:** Role shows two attached policies:
- `AWSGlueServiceRole` (AWS managed)
- `glue-s3-access-495331821583` (Customer inline)

**Troubleshooting:**
- Policy creation fails: Check JSON syntax (use a JSON validator)
- Permission denied: Verify IAM permissions for your user
- Role not found: Check role name spelling

**📸 Screenshot A4d:** Role detail page showing both policies attached

---

### STEP A5 — Create Glue Data Catalog Databases

**Prerequisites Check:**
- ✅ AWS Glue service available in `ap-south-1`
- ✅ Required permissions: `glue:CreateDatabase`
- ✅ S3 bucket created: `handson-data-lake-495331821583`
- ✅ Understanding: Databases organize tables in the Glue Data Catalog

**Step A5.1: Navigate to Glue Console**

1. Go to [AWS Glue Console — Mumbai](https://console.aws.amazon.com/glue/home?region=ap-south-1)
2. **Expected View:** Glue dashboard with navigation sidebar
3. **If Different:** Ensure `ap-south-1` region is selected (top-right)

**Step A5.2: Access Database Management**

1. Left sidebar → **"Databases"** (under Data Catalog section)
2. **Expected View:** Databases page (likely empty for a new account)
3. Click **"Add database"**

**📸 Screenshot A5a:** Glue Databases page with "Add database" button visible

**Step A5.3: Select Database Type**

**Decision Point 1:** Database type selection
| Database Type | Use Case | For This Project |
|---------------|----------|-----------------|
| Glue Database | Standard database for your own data catalog | ✅ Select this |
| Glue Database Resource Link | Link to database in another AWS account | ❌ Single account project |
| Glue Database in S3 Tables Federated Catalog | S3 Tables preview feature | ❌ Not production ready |

1. Select: ✅ **Glue Database**
2. Click **"Next"**

**📸 Screenshot A5b:** Database type selection showing "Glue Database" selected

**Step A5.4: Create Raw Data Database**

**Database 1 configuration:**

| Field | Value | Explanation |
|-------|-------|-------------|
| Name | `raw_db_495331821583` | Raw zone database (no hyphens allowed) |
| Location | `s3://handson-data-lake-495331821583/raw/` | Points to raw data folder |
| Description | `Raw data zone database - Account 495331821583 - Mumbai region` | Clear purpose |

> Glue database naming rules:
> - ✅ Allowed: Letters, numbers, underscores
> - ❌ Not allowed: Hyphens, spaces, special characters
> - Use lowercase for consistency

1. Fill in the form with values above
2. Click **"Create database"**
3. **Expected Outcome:** Success message, returned to databases list

**📸 Screenshot A5c:** Database creation form filled out for `raw_db_495331821583`

**Step A5.5: Create Processed Data Database**

1. Click **"Add database"** again
2. Select: ✅ **Glue Database** → **"Next"**

**Database 2 configuration:**

| Field | Value | Explanation |
|-------|-------|-------------|
| Name | `handson_data_lake_495331821583` | Main processed database |
| Location | `s3://handson-data-lake-495331821583/processed/` | Points to processed folder |
| Description | `Main database for handson data lake - Account 495331821583 - Mumbai` | Primary analytics database |

> **Project 9.2 dependency:** This is the primary database used by the ETL job in Project 9.2.
> Set the job parameter `--database_name` to `handson_data_lake_495331821583`.
> Athena queries in 9.2 Step 5 also target this database.

3. Click **"Create database"**

**Step A5.6: Create Curated Data Database**

1. Click **"Add database"** again
2. Select: ✅ **Glue Database** → **"Next"**

**Database 3 configuration:**

| Field | Value | Explanation |
|-------|-------|-------------|
| Name | `curated_db_495331821583` | Business-ready data |
| Location | `s3://handson-data-lake-495331821583/curated/` | Points to curated folder |
| Description | `Curated data zone database - Account 495331821583 - Mumbai` | Final analytics layer |

3. Click **"Create database"**

**Step A5.7: Validate Database Creation**

**Expected Outcome:** Databases page shows 3 databases:
- `curated_db_495331821583`
- `handson_data_lake_495331821583`
- `raw_db_495331821583`

**Troubleshooting:**
- Database creation fails: Check naming rules (no hyphens)
- Permission denied: Verify `glue:CreateDatabase` permission
- S3 location error: Ensure bucket exists and is accessible

**📸 Screenshot A5d:** Databases page showing all 3 created databases

---

### STEP A6 — Upload Sample Data to S3

**Prerequisites Check:**
- ✅ S3 bucket with folder structure created
- ✅ Text editor or Excel available for CSV creation
- ✅ Required permissions: `s3:PutObject`
- ✅ Understanding: Partitioned data structure for analytics

**Step A6.1: Create the Sample CSV File**

**Decision Point 1:** Data format selection
| Format | Pros | Cons | For This Project |
|--------|------|------|-----------------|
| CSV | Human readable, simple | Larger file size | ✅ Use for learning |
| JSON | Flexible schema | Complex parsing | ❌ Unnecessary complexity |
| Parquet | Optimized for analytics | Binary format | ❌ Save for processed zone |

1. Open a text editor (Notepad, VS Code, etc.)
2. Create a file with this content:

```
order_id,customer_id,product_name,amount,order_date
ORD-001,CUST-101,Widget A,29.99,2024-01-15
ORD-002,CUST-102,Widget B,49.99,2024-01-15
ORD-003,CUST-101,Widget C,19.99,2024-01-16
ORD-004,CUST-103,Widget A,29.99,2024-01-16
ORD-005,CUST-104,Widget B,49.99,2024-01-17
ORD-006,CUST-105,Widget A,29.99,2024-01-17
ORD-007,CUST-106,Widget C,19.99,2024-01-18
ORD-008,CUST-107,Widget B,49.99,2024-01-18
ORD-009,CUST-108,Widget A,29.99,2024-01-19
ORD-010,CUST-109,Widget C,19.99,2024-01-20
```

3. Save as `orders.csv` on your desktop

**📸 Screenshot A6a:** CSV file content open in text editor

**Step A6.2: Create the Partition Folder Structure**

**Decision Point 2:** Partitioning strategy
| Strategy | Query Performance | Storage Organization | For This Project |
|----------|-----------------|---------------------|-----------------|
| No partitions | Poor for large data | Simple | ❌ Not scalable |
| Date-based (year/month/day) | Excellent for time queries | Organized | ✅ Use this |
| Product-based | Good for product queries | Complex | ❌ Unnecessary |

Why partitioning matters:
- Athena only scans relevant partitions (reduces cost and query time)
- Organizes data logically by date
- Glue auto-detects Hive-style `key=value` folder naming

**Step A6.3: Navigate to Upload Location**

1. Go to [Your S3 Bucket](https://s3.console.aws.amazon.com/s3/buckets/handson-data-lake-495331821583)
2. Click on the `raw/` folder
3. **Expected View:** Empty raw folder

**Step A6.4: Create Partition Folders**

Create folders in this sequence — navigate into each one before creating the next:

1. Create `orders/` → click into it
2. Create `year=2024/` → click into it
3. Create `month=01/` → click into it
4. Create `day=15/` → click into it

> Partition naming format: `key=value` (e.g., `year=2024`) — this is Hive-style partitioning. Glue crawlers automatically recognize this pattern.

**📸 Screenshot A6b:** Complete folder path visible: `raw/orders/year=2024/month=01/day=15/`

**Step A6.5: Upload the CSV File**

1. Navigate into the `day=15/` folder
2. Click **"Upload"**
3. **Expected View:** Upload interface

**Decision Point 3:** Upload method
| Method | Ease | Speed | For This Project |
|--------|------|-------|-----------------|
| Drag and drop | Easy | Fast | ✅ Use this |
| Add files button | Easy | Fast | ✅ Alternative |
| AWS CLI | Complex | Very fast | ❌ Unnecessary |

4. Drag `orders.csv` from desktop into the upload area
5. **Expected View:** File appears in upload list
6. Click **"Upload"**
7. **Expected Outcome:** Upload success message

**Step A6.6: Validate Upload**

Final S3 path: `s3://handson-data-lake-495331821583/raw/orders/year=2024/month=01/day=15/orders.csv`

> **Project 9.2 dependency:** Project 9.2 Phase 0 Step 0.2 verifies this exact path exists.
> Do not rename folders or the file — `orders.csv` at this partition path is what 9.2 checks.

**Expected folder tree:**
```
handson-data-lake-495331821583/
└── raw/
    └── orders/
        └── year=2024/
            └── month=01/
                └── day=15/
                    └── orders.csv
```

**Troubleshooting:**
- Upload fails: Check `s3:PutObject` permissions
- File not visible: Refresh browser page
- Wrong location: Verify folder path matches partition structure

**📸 Screenshot A6c:** `orders.csv` visible inside the partition structure

---

### STEP A7 — Create and Run Glue Crawler

**Prerequisites Check:**
- ✅ Glue databases created
- ✅ IAM role `handson-glue-role-495331821583` exists
- ✅ Sample data uploaded to S3
- ✅ Required permissions: `glue:CreateCrawler`, `glue:StartCrawler`

**Step A7.1: Navigate to Crawler Management**

1. Go to [AWS Glue Console — Mumbai](https://console.aws.amazon.com/glue/home?region=ap-south-1)
2. Left sidebar → **"Crawlers"** (under Data Catalog section)
3. **Expected View:** Crawlers page (likely empty for a new account)
4. Click **"Create crawler"**

**📸 Screenshot A7a:** Crawlers page with "Create crawler" button visible

**Step A7.2: Configure Crawler Properties**

**Decision Point 1:** Crawler naming strategy
| Naming Approach | Clarity | Scalability | For This Project |
|-----------------|---------|-------------|-----------------|
| Simple name | Low | Poor | ❌ Not descriptive |
| Descriptive with account ID | High | Good | ✅ Use this |
| Environment-based | Medium | Good | ❌ Single environment |

| Field | Value | Explanation |
|-------|-------|-------------|
| Name | `handson-raw-crawler-495331821583` | Descriptive name with account ID |
| Description | `Discovers schema from raw S3 data for account 495331821583 in Mumbai region` | Clear purpose |

1. Fill in the form
2. Click **"Next"**

**📸 Screenshot A7b:** Crawler properties configuration filled in

**Step A7.3: Configure Data Sources**

**Decision Point 2:** Data source type
| Source Type | Use Case | For This Project |
|-------------|----------|-----------------|
| S3 | Object storage | ✅ Select this |
| JDBC | Relational databases | ❌ Not using RDS |
| DynamoDB | NoSQL database | ❌ Not using DynamoDB |
| Kafka | Streaming data | ❌ Not using streaming |

**Decision Point 3:** Crawling scope
| Scope Option | Coverage | Performance | For This Project |
|-------------|----------|-------------|-----------------|
| Crawl all sub-folders | Complete | Slower | ✅ Use this — needed for partitions |
| Crawl only specified folder | Limited | Faster | ❌ Would miss partitions |

1. Data source type: Select **S3**
2. S3 path: `s3://handson-data-lake-495331821583/raw/`
3. Subsequent crawler runs: Select **"Crawl all sub-folders"**
4. Click **"Add an S3 data source"**
5. Click **"Next"**

**📸 Screenshot A7c:** Data source configuration showing S3 path

**Step A7.4: Configure Security Settings**

**Decision Point 4:** IAM role selection
| Role Option | Security | Complexity | For This Project |
|-------------|----------|------------|-----------------|
| Existing role | Good | Simple | ✅ Use this |
| Create new role | Good | Medium | ❌ Already created in Step A4 |

1. IAM role: Select `handson-glue-role-495331821583`
2. **Expected View:** Role appears in dropdown
3. **If Role Missing:** Return to Step A4 and verify role creation
4. Click **"Next"**

**Step A7.5: Set Output and Scheduling**

**Decision Point 5:** Target database
| Database | Expected Content | For This Step |
|----------|-----------------|--------------|
| `raw_db_495331821583` | Orders table from crawler | ✅ Select this |
| `handson_data_lake_495331821583` | Processed data | ❌ Wrong zone |
| `curated_db_495331821583` | Business data | ❌ Wrong zone |

**Decision Point 6:** Crawler schedule
| Schedule Type | Use Case | For This Project |
|---------------|----------|-----------------|
| On demand | Manual control | ✅ Use for learning |
| Hourly | Frequent updates | ❌ Unnecessary cost |
| Daily | Regular batch processing | ❌ No regular updates |

| Field | Value | Explanation |
|-------|-------|-------------|
| Target database | `raw_db_495331821583` | Database for raw data tables |
| Table name prefix | (leave empty) | No prefix needed |
| Crawler schedule | On demand | Manual trigger |

1. Click **"Next"**

**Step A7.6: Review and Create**

**Validation checklist before clicking Create:**
- ✅ Name: `handson-raw-crawler-495331821583`
- ✅ Data source: `s3://handson-data-lake-495331821583/raw/`
- ✅ IAM role: `handson-glue-role-495331821583`
- ✅ Target database: `raw_db_495331821583`
- ✅ Schedule: On demand

1. Click **"Create crawler"**
2. **Expected Outcome:** Success message and redirect to crawler details

**📸 Screenshot A7d:** Crawler review page before creation — all settings confirmed

**Step A7.7: Run the Crawler**

1. **Expected View:** Crawler details page with **"Run crawler"** button
2. Click **"Run crawler"**

**Status progression — what you'll see:**
| Status | Duration | What's happening |
|--------|----------|-----------------|
| `Starting` | 0–30 seconds | Launching managed Spark job |
| `Running` | 30 sec–2 min | Reading S3, inferring schema, detecting partitions |
| `Ready` | Final | Table created in Data Catalog |

**Step A7.8: Monitor Crawler Execution**

**Success indicators:**
- Status: `Ready`
- Tables added: `1`
- Last run: Recent timestamp

**Troubleshooting:**
- Status stuck on `Starting`: Check IAM role permissions
- Status shows `Failed`: Check CloudWatch logs for details
- No tables added: Verify S3 data exists and is accessible

**📸 Screenshot A7e:** Crawler status showing "Ready" with "Tables added: 1"

---

### STEP A8 — Verify Table in Glue Data Catalog

**Prerequisites Check:**
- ✅ Crawler completed successfully with "Tables added: 1"
- ✅ Status shows `Ready`
- ✅ Required permissions: `glue:GetTable`, `glue:GetDatabase`

**Step A8.1: Navigate to Tables**

1. In Glue Console, left sidebar → **"Tables"** (under Data Catalog)
2. **Expected View:** Tables page with database selector
3. **If Different:** Refresh page if tables are not immediately visible

**Step A8.2: Select Target Database**

**Decision Point 1:** Database selection
| Database | Expected Content | For This Step |
|----------|-----------------|--------------|
| `raw_db_495331821583` | Orders table from crawler | ✅ Select this |
| `handson_data_lake_495331821583` | Empty (no crawler run yet) | ❌ Wrong database |
| `curated_db_495331821583` | Empty (no crawler run yet) | ❌ Wrong database |

1. Database dropdown: Select `raw_db_495331821583`
2. **Expected View:** One table named `orders` should appear

**📸 Screenshot A8a:** Tables page showing `orders` table in `raw_db_495331821583`

**Step A8.3: Validate Schema**

1. Click on table name `orders`
2. **Expected View:** Table details page with multiple tabs

**Column schema validation:**
| Column Name | Data Type | Expected |
|-------------|-----------|---------|
| `order_id` | string | ✅ Text identifier |
| `customer_id` | string | ✅ Text identifier |
| `product_name` | string | ✅ Text description |
| `amount` | double | ✅ Numeric value |
| `order_date` | string | ✅ Date as text |

**Storage details validation:**
| Field | Expected Value | Significance |
|-------|---------------|-------------|
| Location | `s3://handson-data-lake-495331821583/raw/orders/` | S3 path |
| Input format | `org.apache.hadoop.mapred.TextInputFormat` | CSV format |
| SerDe | `org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe` | CSV serializer |

**📸 Screenshot A8b:** Table schema showing all columns and data types

**Step A8.4: Validate Partition Information**

1. Click the **"Partitions"** tab
2. **Expected View:** Partition keys and values

**Partition keys validation:**
| Partition Key | Data Type | Expected |
|---------------|-----------|---------|
| `year` | string | ✅ From folder structure |
| `month` | string | ✅ From folder structure |
| `day` | string | ✅ From folder structure |

**Partition values should show:**
- `year=2024 / month=01 / day=15`
- Location: `s3://handson-data-lake-495331821583/raw/orders/year=2024/month=01/day=15/`

**Troubleshooting:**
- Table not found: Check crawler completed successfully
- Wrong schema: Verify CSV file format and headers
- Missing partitions: Ensure folder structure follows `key=value` pattern
- Permission errors: Check Glue IAM role permissions

**📸 Screenshot A8c:** Partitions tab showing partition keys and values

---

### STEP A9 — Query Data with Athena

**Prerequisites Check:**
- ✅ Glue table created and validated
- ✅ S3 data accessible
- ✅ Required permissions: `athena:StartQueryExecution`, `s3:GetObject`
- ✅ Understanding: Athena charges $5 per TB of data scanned

**Step A9.1: Navigate to Athena Console**

1. Go to [Amazon Athena Console — Mumbai](https://console.aws.amazon.com/athena/home?region=ap-south-1)
2. **Expected View:** Athena query editor interface
3. **If First Time:** You may see a setup wizard

**Step A9.2: Configure Workgroup and Query Result Location**

> **Project 9.2 dependency:** Project 9.2 Step 5.1 expects an Athena workgroup named
> `handson-data-lake` to already exist with the query result location pre-configured.
> Complete **both** sub-steps below before running any queries.

**Sub-step A9.2a — Create workgroup `handson-data-lake`**

**Decision Point 1:** Workgroup strategy
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| `primary` (default) | Quick start, no isolation | ❌ Not referenced by 9.2 |
| Named workgroup | Isolated result location, referenced by 9.2 | ✅ Create this |

1. In Athena console, click **"Workgroups"** (left sidebar)
2. Click **"Create workgroup"**
3. Fill in the form:

| Field | Value | Explanation |
|-------|-------|-------------|
| Workgroup name | `handson-data-lake` | Exact name — 9.2 references this |
| Description | `Workgroup for data lake project — account 495331821583` | Self-documenting |
| Query result location | `s3://handson-data-lake-495331821583/athena-results/` | Dedicated results folder |
| Encrypt query results | SSE-S3 (default) | Consistent with bucket encryption |

4. Click **"Create workgroup"**
5. **Expected Outcome:** Workgroup `handson-data-lake` appears in workgroup list
6. Click on `handson-data-lake` to make it the **active workgroup**

**📸 Screenshot A9a-wg:** Athena workgroups list showing `handson-data-lake` *(required by Project 9.2)*

**Sub-step A9.2b — Verify result location in Settings**

**Decision Point 2:** Result storage strategy
| Storage Location | Cost | Organization | For This Project |
|-----------------|------|-------------|-----------------|
| Dedicated results folder | Low | Clean | ✅ Use this |
| Default Athena bucket | Low | Mixed | ❌ Less organized |
| Separate bucket | Higher | Isolated | ❌ Unnecessary complexity |

1. With `handson-data-lake` workgroup selected, click **"Settings"** → **"Manage"**
2. Confirm Query result location: `s3://handson-data-lake-495331821583/athena-results/`
3. Click **"Save"** if changes were made

**📸 Screenshot A9a:** Athena settings showing query result location in the `handson-data-lake` workgroup

**Step A9.3: Verify Database Connection**

1. Database dropdown: Select `raw_db_495331821583`
2. **Expected View:** Tables section should show `orders` table
3. **If Not Visible:** Refresh page or check Glue table exists

**📸 Screenshot A9b:** Athena interface showing database and table selection

**Step A9.4: Execute Basic Data Query**

1. Copy query into the query editor:

```sql
-- Query 1: See all data from your Mumbai account
SELECT * FROM raw_db_495331821583.orders LIMIT 10;
```

2. Click **"Run"** (or Ctrl+Enter)
3. **Expected Execution Time:** 5–15 seconds
4. **Expected Cost:** ~$0.000001 (very small file)

**Expected results:**
| order_id | customer_id | product_name | amount | order_date | year | month | day |
|----------|-------------|-------------|--------|------------|------|-------|-----|
| ORD-001 | CUST-101 | Widget A | 29.99 | 2024-01-15 | 2024 | 01 | 15 |
| ORD-002 | CUST-102 | Widget B | 49.99 | 2024-01-15 | 2024 | 01 | 15 |
| ... | ... | ... | ... | ... | ... | ... | ... |

**📸 Screenshot A9c:** Query 1 results showing data with partition columns

**Step A9.5: Execute Aggregation Query**

```sql
-- Query 2: Product performance analysis for account 495331821583
SELECT
    product_name,
    COUNT(*) AS order_count,
    SUM(amount) AS total_revenue,
    AVG(amount) AS avg_order_value,
    MIN(amount) AS min_order,
    MAX(amount) AS max_order
FROM raw_db_495331821583.orders
WHERE year = '2024' AND month = '01'
GROUP BY product_name
ORDER BY total_revenue DESC;
```

**Expected results:**
| product_name | order_count | total_revenue | avg_order_value | min_order | max_order |
|-------------|-------------|--------------|----------------|----------|----------|
| Widget B | 3 | 149.97 | 49.99 | 49.99 | 49.99 |
| Widget A | 4 | 119.96 | 29.99 | 29.99 | 29.99 |
| Widget C | 3 | 59.97 | 19.99 | 19.99 | 19.99 |

**📸 Screenshot A9d:** Query 2 results showing aggregated analytics

**Step A9.6: Execute Partition-Pruned Query**

```sql
-- Query 3: Partition-pruned query (cost-efficient) for Mumbai data
SELECT
    order_id,
    customer_id,
    product_name,
    amount,
    order_date
FROM raw_db_495331821583.orders
WHERE year = '2024' AND month = '01' AND day = '15'
ORDER BY amount DESC;
```

Why this query is efficient:
- Uses partition columns in `WHERE` clause — Athena only scans relevant partition
- Reduces both cost and query time significantly at scale

**📸 Screenshot A9e:** Query 3 results — partition-pruned execution with small data scanned

**Step A9.7: Validate Query Performance**

**Performance metrics to check** (shown below the results):
- Execution time: should be under 30 seconds
- Data scanned: should show KB range
- Query cost: should be minimal ($0.000001 range)

**Troubleshooting:**
- Query fails: Check table exists and permissions
- No results: Verify data was uploaded correctly
- Slow performance: Check partition pruning is applied (`WHERE year=... AND month=...`)
- Permission errors: Verify Athena and S3 access

**📸 Screenshot A9f:** Query execution details showing performance metrics and data scanned

---

### STEP A10 — Register with Lake Formation

**Prerequisites Check:**
- ✅ S3 bucket and Glue catalog configured
- ✅ Required permissions: `lakeformation:RegisterResource`, `lakeformation:GrantPermissions`
- ✅ Understanding: Lake Formation uses opt-in security — permissions must be explicitly granted

**Step A10.1: Navigate to Lake Formation**

1. Go to [AWS Lake Formation Console — Mumbai](https://console.aws.amazon.com/lakeformation/home?region=ap-south-1)
2. **Expected View:** Lake Formation dashboard or welcome screen
3. **If you see a Welcome/Get Started screen:** Click **"Get started"** to proceed to the main console

**📸 Screenshot A10a:** Lake Formation welcome screen or dashboard

**Step A10.2: Register Your S3 Data Location**

Why this step is needed:
- Lake Formation must know which S3 locations it manages
- Required before granting any database permissions

1. Left sidebar → **"Data lake locations"** (under Administration)
2. **Expected View:** Registered S3 locations page (probably empty)
3. Click **"Register location"**

**📸 Screenshot A10b:** Data lake locations page before registration

**Step A10.3: Fill Registration Form**

| Field | Value | Explanation |
|-------|-------|-------------|
| Amazon S3 path | `s3://handson-data-lake-495331821583/` | Your entire bucket path |
| IAM role | `handson-glue-role-495331821583` | The role created in Step A4 |

1. Amazon S3 path field: type `s3://handson-data-lake-495331821583/` (include `s3://` prefix and trailing `/`)
2. IAM role field: click dropdown → select `handson-glue-role-495331821583`
3. Click **"Register location"**
4. **Expected Result:** Success message — location registered

**📸 Screenshot A10c:** Registration form filled out before submitting

**Step A10.4: Grant Database Permissions**

Why this step is needed:
- Lake Formation uses an opt-in security model — nobody has access by default
- You must explicitly grant yourself permission to query the database

1. Left sidebar → **"Data lake permissions"** (under Permissions)
2. **Expected View:** Current permissions page (probably empty)
3. Click **"Grant"**

**📸 Screenshot A10d:** Data lake permissions page before granting access

**Step A10.5: Fill Permission Grant Form**

**Section 1 — Principals (who gets access):**
1. IAM users and roles → click **"Add"**
2. Select your current IAM user from the list

**Section 2 — LF-Tags or catalog resources:**
1. Select **"Named data catalog resources"** (default)

**Section 3 — Databases:**
1. Databases dropdown → select `raw_db_495331821583`

**Section 4 — Database permissions:**
1. Check: ✅ **Describe**
2. Check: ✅ **Select** (allows querying)

**Section 5 — Grantable permissions:** leave unchecked

1. Click **"Grant"**
2. **Expected Result:** Success message — permissions granted

**📸 Screenshot A10e:** Permission grant form filled out

**Step A10.6: Validate Lake Formation Setup**

1. Go to [Athena Console](https://console.aws.amazon.com/athena/home?region=ap-south-1)
2. Run this verification query:

```sql
SELECT * FROM raw_db_495331821583.orders LIMIT 5;
```

3. **Expected Result:** Query runs successfully and returns sample data without permission errors

**Troubleshooting:**
- Registration fails: Check IAM role permissions
- Permission denied in Athena: Return to Lake Formation → verify permissions were granted for the correct database and user
- Query fails after grant: Check that you selected `Select` permission, not just `Describe`

**📸 Screenshot A10f:** Successful Athena query after Lake Formation setup confirmed

---

### STEP A11 — Create ETL Job

**Prerequisites Check:**
- ✅ Glue databases and tables created
- ✅ IAM role `handson-glue-role-495331821583` with appropriate permissions
- ✅ Understanding: ETL transforms raw data into analytics-ready format

**Step A11.1: Navigate to ETL Jobs**

1. Go to [AWS Glue Console — Mumbai](https://console.aws.amazon.com/glue/home?region=ap-south-1)
2. Left sidebar → **"ETL jobs"** (under Data Integration and ETL)
3. Click **"Create job"**

**📸 Screenshot A11a:** ETL Jobs page with "Create job" button visible

**Step A11.2: Select Job Type**

**Decision Point 1:** Job creation method
| Method | Ease | Flexibility | For This Project |
|--------|------|-------------|-----------------|
| Visual ETL | Medium | High | ✅ Use for learning |
| Spark script editor | Hard | Highest | ❌ Too complex for initial setup |
| Python shell script editor | Hard | High | ❌ No Spark distribution |
| Ray script editor | Hard | Medium | ❌ Not an ML workload |

1. Select **"Visual ETL"**
2. **Expected View:** Job configuration form

**📸 Screenshot A11b:** Job type selection screen showing Visual ETL selected

**Step A11.3: Configure Job Properties**

| Field | Value | Explanation |
|-------|-------|-------------|
| Name | `raw-to-processed-etl-495331821583` | Descriptive job name |
| IAM Role | `handson-glue-role-495331821583` | Service role for execution |
| Glue version | `4.0` | Latest stable version |
| Language | `Python 3` | Programming language |
| Worker type | `G.1X` | Standard worker (4 vCPU, 16GB) |
| Number of workers | `2` | Minimum for learning |
| Job timeout | `60` | Kill job if stuck — cost protection |
| Job bookmark | Disable | Simple for initial run |

**📸 Screenshot A11c:** Job configuration form filled out

**Step A11.4: Design Visual ETL Pipeline**

After creating the job, you see the Visual ETL canvas:
- Left panel: Available nodes (Sources, Transforms, Targets)
- Main canvas: Drag-and-drop area

**Add Source node:**
1. Left panel → **Sources** → drag **"AWS Glue Data Catalog"** to canvas
2. Configure:
   - Node name: `ReadRawOrders`
   - Database: `raw_db_495331821583`
   - Table: `orders`

**Add Transform node:**
1. Left panel → **Transforms** → drag **"ApplyMapping"** to canvas
2. Draw a line from `ReadRawOrders` → `ApplyMapping`
3. Configure:
   - Node name: `TransformOrders`
   - Mapping: keep all existing columns

**Add Target node:**
1. Left panel → **Targets** → drag **"Amazon S3"** to canvas
2. Draw a line from `TransformOrders` → S3 target
3. Configure:
   - Node name: `WriteProcessedData`
   - Format: `Parquet`
   - S3 Target Location: `s3://handson-data-lake-495331821583/processed/orders/`
   - Partition Keys: `year`, `month`, `day`

**📸 Screenshot A11d:** Complete visual ETL pipeline on canvas

**Step A11.5: Save and Run Job**

1. Click **"Save"** (top-right corner)
2. **Expected Result:** Job saved successfully
3. Click **"Run"**
4. **Expected Execution Time:** 2–5 minutes

**Status progression:**
| Status | Duration | What's happening |
|--------|----------|-----------------|
| `Starting` | 0–30 sec | AWS allocating workers |
| `Running` | 1–5 min | Spark reading raw CSV, writing Parquet |
| `Succeeded` | Final | Parquet files written to S3 |

**Step A11.6: Verify ETL Output**

1. Go to [S3 Console](https://s3.console.aws.amazon.com/s3/buckets/handson-data-lake-495331821583)
2. Navigate to `processed/orders/`
3. **Expected structure:**
```
processed/
└── orders/
    └── year=2024/
        └── month=01/
            └── day=15/
                └── part-00000.parquet
```

4. Verify in Athena:
```sql
-- Create external table for processed data
CREATE EXTERNAL TABLE handson_data_lake_495331821583.processed_orders (
  order_id          string,
  customer_id       string,
  product_name      string,
  amount            double,
  order_date        string,
  revenue_category  string,
  account_id        string,
  region            string
)
PARTITIONED BY (year string, month string, day string)
STORED AS PARQUET
LOCATION 's3://handson-data-lake-495331821583/processed/orders/';

-- Register partitions
MSCK REPAIR TABLE handson_data_lake_495331821583.processed_orders;

-- Query processed data
SELECT * FROM handson_data_lake_495331821583.processed_orders LIMIT 10;
```

**📸 Screenshot A11e:** Athena query results showing processed Parquet data

---

### STEP A12 — Set Up CloudWatch Monitoring

**Prerequisites Check:**
- ✅ AWS services deployed and running
- ✅ Required permissions: `cloudwatch:CreateDashboard`, `cloudwatch:PutMetricAlarm`

**Step A12.1: Navigate to CloudWatch**

1. Go to [CloudWatch Console — Mumbai](https://console.aws.amazon.com/cloudwatch/home?region=ap-south-1)
2. **Expected View:** CloudWatch dashboard homepage

**Step A12.2: Create Custom Dashboard**

1. Left sidebar → **"Dashboards"**
2. Click **"Create dashboard"**
3. Dashboard name: `DataLake-Dashboard-495331821583-Mumbai`
4. Click **"Create dashboard"**

**Step A12.3: Add S3 Metrics Widget**

1. Click **"Add widget"** → Widget type: **Line**
2. Data source: **CloudWatch**
3. Metrics:
   - Namespace: `AWS/S3`
   - Metric: `BucketSizeBytes`
   - Bucket: `handson-data-lake-495331821583`
   - Storage Type: `StandardStorage`
4. Click **"Create widget"**

**Step A12.4: Add Glue Job Metrics Widget**

1. Click **"Add widget"** again
2. Metrics:
   - Namespace: `AWS/Glue`
   - Metric: `glue.driver.aggregate.numCompletedTasks`
   - Job: `raw-to-processed-etl-495331821583`
3. Click **"Create widget"**

**Step A12.5: Create Cost Alert**

1. Left sidebar → **"Alarms"** → **"All alarms"**
2. Click **"Create alarm"**

| Field | Value | Explanation |
|-------|-------|-------------|
| Metric | `AWS/Billing EstimatedCharges` | Total account charges |
| Statistic | Maximum | Highest value |
| Period | 6 hours | Check frequency |
| Threshold | Static > 10 | Alert if over $10 |
| Alarm name | `DataLake-Cost-Alert-495331821583` | Descriptive name |

**📸 Screenshot A12a:** CloudWatch dashboard with S3 and Glue metric widgets

---

### STEP A13 — Configure Data Quality Rules

**Prerequisites Check:**
- ✅ Glue tables exist with data
- ✅ Understanding: Data quality ensures reliable analytics

**Step A13.1: Navigate to Data Quality**

1. In Glue Console → left sidebar → **"Data Quality"**
2. Click **"Create ruleset"**

**Step A13.2: Configure Quality Ruleset**

| Field | Value |
|-------|-------|
| Name | `orders-quality-rules-495331821583-mumbai` |
| Target table | `raw_db_495331821583.orders` |

**Data quality rules:**

```
Rules = [
    ColumnCount = 5,
    IsComplete "order_id",
    IsUnique "order_id",
    ColumnValues "amount" > 0,
    ColumnDataType "order_date" = "string",
    ColumnValues "customer_id" matches "CUST-[0-9]{3}",
    RowCount between 1 and 1000000,
    ColumnValues "product_name" in ["Widget A", "Widget B", "Widget C"]
]
```

**📸 Screenshot A13a:** Data quality rules configuration filled in

---

### STEP A14 — Set Up Cost Monitoring

**Prerequisites Check:**
- ✅ AWS Cost Explorer enabled
- ✅ Understanding: Cost monitoring prevents bill surprises

**Step A14.1: Navigate to Cost Management**

1. Go to [AWS Budgets](https://console.aws.amazon.com/billing/home#/budgets)
2. Click **"Create budget"**

**Step A14.2: Configure Budget**

| Field | Value |
|-------|-------|
| Budget type | Cost budget |
| Budget name | `DataLake-Budget-495331821583-Mumbai` |
| Period | Monthly |
| Budget amount | `$20` |
| Budget scope | Filtered |

**Filters:**
- Service: S3, Glue, Athena, Lake Formation
- Region: Asia Pacific (Mumbai)

**Alert configuration:**
- Alert threshold: 80% of budgeted amount
- Email recipients: your email address

**📸 Screenshot A14a:** Budget configuration with Mumbai region filter applied

---

### STEP A15 — Security Hardening

**Prerequisites Check:**
- ✅ All services deployed
- ✅ Understanding: Security is ongoing, not one-time setup

**Step A15.1: Update IAM Role with Least Privilege**

1. Go to IAM → **Roles** → `handson-glue-role-495331821583`
2. Edit the inline policy `glue-s3-access-495331821583`
3. Replace with this enhanced least-privilege policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": [
        "arn:aws:s3:::handson-data-lake-495331821583/raw/*",
        "arn:aws:s3:::handson-data-lake-495331821583/processed/*"
      ],
      "Condition": {
        "StringEquals": {"aws:RequestedRegion": "ap-south-1"}
      }
    },
    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::handson-data-lake-495331821583",
      "Condition": {
        "StringLike": {"s3:prefix": ["raw/*", "processed/*"]},
        "StringEquals": {"aws:RequestedRegion": "ap-south-1"}
      }
    }
  ]
}
```

**Step A15.2: Enable S3 Access Logging**

1. Go to S3 → `handson-data-lake-495331821583` → **"Properties"** tab
2. **Server access logging** → **"Edit"** → **"Enable"**

| Field | Value |
|-------|-------|
| Target bucket | `handson-data-lake-495331821583` |
| Target prefix | `access-logs/` |

3. Click **"Save changes"**

**📸 Screenshot A15a:** S3 access logging configuration enabled

---

---

### Console UI Summary — Resources Created

| Resource | Name | Location in Console |
|----------|------|-------------------|
| S3 bucket | `handson-data-lake-495331821583` | S3 → Buckets |
| S3 folders | `raw/`, `processed/`, `curated/`, `archive/`, `athena-results/`, `temp/`, `sparkhistory/` | S3 → bucket root |
| Lifecycle rules | `archive-raw-data`, `expire-temp-data` | S3 → bucket → Management tab |
| IAM role | `handson-glue-role-495331821583` | IAM → Roles |
| Inline policy | `glue-s3-access-495331821583` | IAM → Roles → role detail |
| Glue databases | `raw_db_495331821583`, `handson_data_lake_495331821583`, `curated_db_495331821583` | Glue → Data Catalog → Databases |
| Glue crawler | `handson-raw-crawler-495331821583` | Glue → Data Catalog → Crawlers |
| Glue table | `orders` in `raw_db_495331821583` | Glue → Data Catalog → Tables |
| ETL job | `raw-to-processed-etl-495331821583` | Glue → ETL Jobs |
| Athena workgroup | `handson-data-lake` | Athena → Workgroups |
| CloudWatch dashboard | `DataLake-Dashboard-495331821583-Mumbai` | CloudWatch → Dashboards |
| Cost budget | `DataLake-Budget-495331821583-Mumbai` | AWS Budgets |

---

### ✅ Project 9.2 Readiness Check

All 7 boxes must be checked before starting Project 9.2:

- ☐ S3 bucket exists: `handson-data-lake-495331821583`
- ☐ `temp/` folder exists in bucket
- ☐ Raw data at: `raw/orders/year=2024/month=01/day=15/orders.csv`
- ☐ IAM role exists: `handson-glue-role-495331821583` with `AWSGlueServiceRole` attached
- ☐ Glue database exists: `handson_data_lake_495331821583`
- ☐ Glue database exists: `raw_db_495331821583`
- ☐ Athena workgroup exists: `handson-data-lake` with result location set

All 7 checked? ✅ You are ready to start Project 9.2.

---

### Screenshot Summary (Complete List for Project 9.1)

| # | What to Capture | When |
|---|----------------|------|
| A1a | S3 console showing "Create bucket" button and Mumbai region | Start of Step A1 |
| A1b | Bucket configuration form with all settings filled | During Step A1 |
| A1c | Success message — bucket created | After Step A1 |
| A2 | All 7 zone folders visible in bucket | After Step A2 |
| A3a | Management tab — Lifecycle rules section | Start of Step A3 |
| A3b | Lifecycle rule form for `archive-raw-data` | During Step A3 |
| A3c | Management tab showing both lifecycle rules | After Step A3 |
| A4a | IAM Roles page with "Create role" button | Start of Step A4 |
| A4b | Glue service selected as trusted entity | During Step A4 |
| A4c | Role creation success message | During Step A4 |
| A4d | Role detail showing both policies attached | After Step A4 |
| A5a | Glue Databases page with "Add database" button | Start of Step A5 |
| A5b | Database type selection — "Glue Database" chosen | During Step A5 |
| A5c | Database creation form for `raw_db_495331821583` | During Step A5 |
| A5d | Databases page showing all 3 databases | After Step A5 |
| A6a | CSV file content in text editor | During Step A6 |
| A6b | Complete partition folder path in S3 | During Step A6 |
| A6c | `orders.csv` visible inside partition structure | After Step A6 |
| A7a | Crawlers page with "Create crawler" button | Start of Step A7 |
| A7b | Crawler properties form filled | During Step A7 |
| A7c | Data source configuration — S3 path | During Step A7 |
| A7d | Crawler review page — all settings confirmed | During Step A7 |
| A7e | Crawler status "Ready" with "Tables added: 1" | After Step A7 |
| A8a | Tables page showing `orders` in `raw_db_495331821583` | During Step A8 |
| A8b | Table schema — all columns and data types | During Step A8 |
| A8c | Partitions tab — partition keys and values | During Step A8 |
| A9a-wg | Athena workgroups list showing `handson-data-lake` | Start of Step A9 *(required by 9.2)* |
| A9a | Athena settings — query result location in workgroup | During Step A9 |
| A9b | Athena interface — database and table selected | During Step A9 |
| A9c | Query 1 results with partition columns | During Step A9 |
| A9d | Query 2 aggregated analytics results | During Step A9 |
| A9e | Query 3 partition-pruned results | During Step A9 |
| A9f | Query execution details — data scanned metrics | During Step A9 |
| A10a | Lake Formation dashboard | Start of Step A10 |
| A10b | Data lake locations page | During Step A10 |
| A10c | S3 registration form filled | During Step A10 |
| A10d | Data lake permissions page | During Step A10 |
| A10e | Permission grant form filled | During Step A10 |
| A10f | Successful Athena query after Lake Formation setup | After Step A10 |
| A11a | ETL Jobs page with "Create job" button | Start of Step A11 |
| A11b | Visual ETL job type selected | During Step A11 |
| A11c | Job configuration form | During Step A11 |
| A11d | Complete visual pipeline on canvas | During Step A11 |
| A11e | Athena results showing processed Parquet data | After Step A11 |
| A12a | CloudWatch dashboard with metric widgets | After Step A12 |
| A13a | Data quality rules configuration | After Step A13 |
| A14a | Budget configuration with Mumbai filter | After Step A14 |
| A15a | S3 access logging enabled | After Step A15 |

**Total: 49 screenshots** — capture all to build a complete hands-on portfolio.

---

### Estimated Monthly Cost — Mumbai Region (ap-south-1)

| Service | Monthly Usage | Cost (USD) | Notes |
|---------|--------------|-----------|-------|
| S3 Standard Storage | 5 GB | $0.125 | 8% higher than us-east-1 |
| S3 Requests | 10,000 PUT/GET | $0.05 | Same as global |
| Glue Crawler | 4 runs | $0.88 | Same as global |
| Glue ETL Jobs | 4 DPU-hours | $1.76 | Same as global |
| Athena Queries | 5 GB scanned | $0.025 | Same as global |
| Lake Formation | Basic usage | $0.00 | Free tier |
| CloudWatch | Basic monitoring | $0.30 | Same as global |
| Data Transfer | Within ap-south-1 | $0.00 | No intra-region charges |
| **Total** | | **~$3.18/month** | Excellent for learning |
