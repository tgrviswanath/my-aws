# Project 9.3 — Real-Time Streaming Pipeline
# Console UI Steps (Improved Template Format)
# Region: us-east-1 | Adapt account ID to your setup

---

## 5A. AWS Management Console Implementation

---

### PHASE 0 — Prerequisites Verification

**Prerequisites Check:**
- ✅ Required permissions: `kinesis:CreateStream`, `lambda:CreateFunction`, `dynamodb:CreateTable`, `sqs:CreateQueue`, `iam:CreateRole`
- ✅ Services enabled: Kinesis, Lambda, DynamoDB, SQS — all available in us-east-1
- ✅ Region: us-east-1 selected (top-right of console)
- ✅ Local: `src/consumer_lambda.py` exists, Python + boto3 installed

**Step 0.1: Navigate and Verify Region**

1. Open [AWS Console](https://console.aws.amazon.com)
2. **Expected View:** Top-right region selector showing **N. Virginia** or **us-east-1**
3. **If Different:** Click region selector → choose **US East (N. Virginia) us-east-1**

**📸 Screenshot P0:** AWS Console header showing us-east-1 region

---

### STEP 1 — Create Kinesis Data Stream

**Prerequisites Check:**
- ✅ Required permissions: `kinesis:CreateStream`, `kinesis:DescribeStream`
- ✅ Services enabled: Amazon Kinesis available in us-east-1
- ✅ Region availability: Kinesis Data Streams available in all major regions

**Step 1.1: Navigate and Verify**

1. In the search bar, type **Kinesis** → click **Amazon Kinesis**
2. **Expected View:** Kinesis home page with service cards: Data Streams, Firehose, Analytics
3. Click **Data Streams** in the left navigation
4. **Expected View:** Data Streams list (empty for new accounts)
5. **If Different:** Make sure you're in the Data Streams section, not Delivery Streams (Firehose)

**📸 Screenshot 1a:** Kinesis Data Streams empty list

**Step 1.2: Initiate Stream Creation**

1. Click **Create data stream** (orange button, top-right)
2. **Expected View:** Stream creation form with Name field and Capacity section

**Step 1.3: Configure Stream Name**

| Field | Value | Explanation |
|-------|-------|-------------|
| Data stream name | `handson-events` | Project-consistent naming — matches Terraform |

**Step 1.4: Make Selections — Capacity Mode**

**Decision Point 1:** Capacity mode selection
| Option | Use Case | Cost | For This Project |
|--------|----------|------|-----------------|
| **On-demand** | Auto-scales, unknown throughput | $0.08/GB processed | ❌ More expensive for predictable learning load |
| **Provisioned** | Fixed throughput, known load | $0.015/shard-hour | ✅ Cheapest for learning — 1 shard = $0.015/hr |

1. Select **Provisioned**
2. **Provisioned shards:** enter `1`

**Why 1 shard for this project:**
- 1 shard = 1,000 records/s inbound OR 1 MB/s (whichever first)
- Our producer sends 50 events × ~200 bytes = ~10 KB total
- We use < 1% of shard capacity — adding more shards = wasted money

**📸 Screenshot 1b:** Stream form showing name=`handson-events`, Provisioned, 1 shard

**Step 1.5: Configure Details**

No additional configuration needed for learning. Leave defaults:
- Encryption: Disabled (fine for learning data)
- Tags: (optional) add `Project=handson`

**Step 1.6: Validate Result**

1. Click **Create data stream**
2. **Expected Outcome:** Status shows **Creating** (orange dot) → transitions to **Active** (green dot) within 30–60 seconds
3. **If Stuck on Creating:** Wait up to 2 minutes then refresh. AWS is allocating shard capacity.

**Troubleshooting:**
- `LimitExceededException`: Your account shard quota reached — delete unused streams in this region first
- `AccessDenied`: IAM user missing `kinesis:CreateStream` — add to permissions

**📸 Screenshot 1c:** Stream `handson-events` Status = **Active** with shard count = 1

**Step 1.7: Verify Stream Details**

1. Click on stream name `handson-events`
2. **Expected View:** Details page with tabs: Details, Monitoring, Enhanced fan-out

Confirm these values under **Details** tab:
| Property | Expected |
|----------|----------|
| Status | Active |
| Shard count | 1 |
| Retention period | 24 hours |
| Stream mode | Provisioned |

**📸 Screenshot 1d:** Stream details tab showing retention=24h, Provisioned mode

---

### STEP 2 — Create DynamoDB Table

**Prerequisites Check:**
- ✅ Required permissions: `dynamodb:CreateTable`
- ✅ Region: us-east-1 (same as stream — keep all resources co-located)
- ✅ Understanding: pk=partition key, sk=sort key, enables range queries per product+hour

**Step 2.1: Navigate and Verify**

1. Search bar → **DynamoDB** → click it
2. Left sidebar → **Tables**
3. **Expected View:** Tables list
4. Click **Create table** (orange button)
5. **Expected View:** Table creation form

**📸 Screenshot 2a:** DynamoDB Tables list before creation

**Step 2.2: Make Selections — Key Schema**

**Decision Point 1:** Primary key design
| Design | Example Keys | Query Capability | For This Project |
|--------|-------------|-----------------|-----------------|
| Single partition key only | `pk=PRODUCT#Widget` | Get by product | ❌ Can't filter by time |
| Partition + sort key | `pk=PRODUCT#Widget` + `sk=HOUR#2024-01-15T14` | Get product+hour | ✅ Supports time-range queries |
| GSI (Global Secondary Index) | Complex | Multiple access patterns | ❌ Overkill for learning |

**Step 2.3: Configure Details**

| Field | Value | Explanation |
|-------|-------|-------------|
| Table name | `handson-stream-aggregates` | Matches Terraform |
| Partition key | `pk` (String) | Stores: `PRODUCT#Widget A` |
| Sort key | ✅ Enable | Click **Add sort key** |
| Sort key name | `sk` (String) | Stores: `HOUR#2024-01-15T14:00:00Z` |

**Decision Point 2:** Capacity mode
| Option | Use Case | Cost | For This Project |
|--------|----------|------|-----------------|
| **Provisioned** | Known, predictable load | Fixed RCU/WCU | ❌ Need capacity planning |
| **On-demand** | Variable / learning | Pay per request | ✅ No planning needed — $0.00 at low volume |

1. Select **On-demand** under Table settings

**Step 2.4: Validate Result**

1. Click **Create table**
2. **Expected Outcome:** Status shows **Creating** → **Active** (within 30 seconds)

**Troubleshooting:**
- "Table already exists": Change table name or delete the existing one
- Cannot add sort key: It must be configured during creation — cannot add later

**📸 Screenshot 2b:** DynamoDB table `handson-stream-aggregates` Status = **Active**

---

### STEP 3 — Create IAM Role for Lambda

**Prerequisites Check:**
- ✅ Required permissions: `iam:CreateRole`, `iam:AttachRolePolicy`, `iam:PutRolePolicy`
- ✅ Region availability: IAM is global (not region-specific)
- ✅ Understanding: Lambda needs read access to Kinesis + write to DynamoDB + CloudWatch Logs

**Step 3.1: Navigate and Verify**

1. Search bar → **IAM** → click it
2. Left sidebar → **Roles**
3. **Expected View:** Roles list
4. Click **Create role** (orange button)

**📸 Screenshot 3a:** IAM Roles list before creation

**Step 3.2: Make Selections — Trusted Entity**

**Decision Point 1:** Trusted entity type
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| **AWS service** | AWS service assumes role | ✅ Lambda will assume this role |
| AWS account | Cross-account access | ❌ Not needed |
| Web identity | OIDC/GitHub Actions | ❌ Not needed |

1. Select **AWS service**

**Decision Point 2:** Use case (which service)
| Service | For This Project |
|---------|-----------------|
| **Lambda** | ✅ Our function needs this role |
| EC2 | ❌ Not using EC2 |
| Glue | ❌ Different project |

2. Use case: Select **Lambda** → Click **Next**

**Step 3.3: Configure Permissions**

1. Search for `AWSLambdaBasicExecutionRole` → ✅ check it
   - This grants: `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`
   - Required for Lambda to write execution logs to CloudWatch
2. Click **Next**

**Step 3.4: Configure Role Details**

| Field | Value |
|-------|-------|
| Role name | `handson-kinesis-consumer-role` |
| Description | `Lambda execution role for Kinesis stream processing` |

3. Click **Create role**

**📸 Screenshot 3b:** Role creation confirmation with name `handson-kinesis-consumer-role`

**Step 3.5: Add Inline Policy for Kinesis + DynamoDB**

1. Click on role name `handson-kinesis-consumer-role`
2. Click **Add permissions** → **Create inline policy**
3. Click **JSON** tab (switch from Visual editor)
4. Replace all content with the policy below (replace `YOUR_ACCOUNT_ID`):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "KinesisRead",
      "Effect": "Allow",
      "Action": [
        "kinesis:GetRecords",
        "kinesis:GetShardIterator",
        "kinesis:DescribeStream",
        "kinesis:DescribeStreamSummary",
        "kinesis:ListStreams",
        "kinesis:ListShards"
      ],
      "Resource": "arn:aws:kinesis:us-east-1:YOUR_ACCOUNT_ID:stream/handson-events"
    },
    {
      "Sid": "DynamoDBWrite",
      "Effect": "Allow",
      "Action": [
        "dynamodb:UpdateItem",
        "dynamodb:PutItem",
        "dynamodb:GetItem"
      ],
      "Resource": "arn:aws:dynamodb:us-east-1:YOUR_ACCOUNT_ID:table/handson-stream-aggregates"
    },
    {
      "Sid": "SQSDeadLetter",
      "Effect": "Allow",
      "Action": ["sqs:SendMessage"],
      "Resource": "arn:aws:sqs:us-east-1:YOUR_ACCOUNT_ID:handson-kinesis-dlq"
    }
  ]
}
```

5. Click **Next** → Policy name: `kinesis-dynamo-access` → **Create policy**

**Step 3.6: Validate Result**

**Expected Outcome:** Role shows 2 attached policies:
- `AWSLambdaBasicExecutionRole` (AWS managed)
- `kinesis-dynamo-access` (Customer inline)

**Troubleshooting:**
- "Invalid JSON": Use a JSON validator — check for missing commas or brackets
- Policy save fails: Replace `YOUR_ACCOUNT_ID` with your actual 12-digit account ID

**📸 Screenshot 3c:** IAM role with both `AWSLambdaBasicExecutionRole` and `kinesis-dynamo-access` visible

---

### STEP 4 — Create SQS Dead Letter Queue

**Prerequisites Check:**
- ✅ Required permissions: `sqs:CreateQueue`
- ✅ Understanding: Receives permanently failed Lambda records — prevents silent data loss

**Step 4.1: Navigate and Verify**

1. Search bar → **SQS** → click **Simple Queue Service**
2. **Expected View:** Queues list
3. Click **Create queue**

**Step 4.2: Make Selections — Queue Type**

**Decision Point 1:** Queue type
| Option | Ordering | Duplicates | For This Project |
|--------|----------|-----------|-----------------|
| **Standard** | Best-effort | Possible | ✅ DLQ doesn't need strict ordering |
| FIFO | Strict | Exactly-once | ❌ Overkill for dead letters |

1. Select **Standard**

**Step 4.3: Configure Details**

| Field | Value |
|-------|-------|
| Name | `handson-kinesis-dlq` |

Leave all other settings as defaults (visibility timeout, message retention, etc.)

**Step 4.4: Validate Result**

1. Click **Create queue**
2. **Expected Outcome:** Queue listed with URL `https://sqs.us-east-1.amazonaws.com/ACCOUNT/handson-kinesis-dlq`

**📸 Screenshot 4a:** SQS queue `handson-kinesis-dlq` created

---

### STEP 5 — Create Lambda Function

**Prerequisites Check:**
- ✅ IAM role `handson-kinesis-consumer-role` created
- ✅ `src/consumer_lambda.py` exists locally
- ✅ Required permissions: `lambda:CreateFunction`, `iam:PassRole`

**Step 5.1: Navigate and Verify**

1. Search bar → **Lambda** → click it
2. **Expected View:** Lambda functions list
3. Click **Create function** (orange button)

**📸 Screenshot 5a:** Lambda functions list (empty before creation)

**Step 5.2: Make Selections — Creation Method**

**Decision Point 1:** Creation method
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| **Author from scratch** | Write or upload your own code | ✅ We have `consumer_lambda.py` |
| Use a blueprint | Pre-built templates | ❌ Generic code |
| Container image | Docker-based deployment | ❌ Overkill for Python |

1. Select **Author from scratch**

**Step 5.3: Configure Basic Information**

| Field | Value | Explanation |
|-------|-------|-------------|
| Function name | `handson-kinesis-consumer` | Matches Terraform |
| Runtime | **Python 3.11** | Latest stable, matches src/ code |
| Architecture | x86_64 | Standard, widely compatible |

**Decision Point 2:** Execution role
| Option | For This Project |
|--------|-----------------|
| Create a new role with basic Lambda permissions | ❌ Already created custom role |
| **Use an existing role** | ✅ Select `handson-kinesis-consumer-role` |

1. Expand **Permissions** section
2. Select **Use an existing role**
3. Existing role: `handson-kinesis-consumer-role`
4. Click **Create function**

**📸 Screenshot 5b:** Lambda creation form with Python 3.11, existing role selected

**Step 5.4: Upload Lambda Code**

The default code shows Hello World — replace with our ETL consumer.

First, create a ZIP file locally:
```powershell
cd D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.3_kinesis_streaming
Compress-Archive -Path src\consumer_lambda.py -DestinationPath consumer.zip -Force
```

Then in the Lambda console:
1. Click **Code** tab
2. Click **Upload from** → **.zip file**
3. Click **Upload** → navigate to `consumer.zip` → **Open** → **Save**
4. **Expected View:** Code editor shows `consumer_lambda.py` content

**📸 Screenshot 5c:** Lambda code editor showing `consumer_lambda.py` content after upload

**Step 5.5: Configure Environment Variables**

1. Click **Configuration** tab → **Environment variables** → **Edit**
2. Click **Add environment variable**:

| Key | Value |
|-----|-------|
| `TABLE_NAME` | `handson-stream-aggregates` |

3. Click **Save**

**Step 5.6: Configure Timeout**

1. **Configuration** tab → **General configuration** → **Edit**
2. Timeout: **1 min 0 sec** (60 seconds — Kinesis batches process quickly but give buffer)
3. Click **Save**

**Step 5.7: Validate Result**

**Expected Outcome:**
- Function state: Active
- Runtime: Python 3.11
- Handler: `consumer_lambda.handler`
- Env var: TABLE_NAME = `handson-stream-aggregates`

**Troubleshooting:**
- "Handler not found": Verify the handler is `consumer_lambda.handler` (filename dot function name)
- "Invalid zip file": Re-create the ZIP ensuring the .py file is at root, not in a subfolder
- "Role not found": Role name typo — go to IAM and copy the exact role name

**📸 Screenshot 5d:** Lambda Configuration showing env var and 60s timeout

---

### STEP 6 — Add Kinesis Trigger to Lambda

**Prerequisites Check:**
- ✅ Kinesis stream `handson-events` Status = Active
- ✅ Lambda `handson-kinesis-consumer` State = Active
- ✅ SQS DLQ `handson-kinesis-dlq` created
- ✅ IAM role has all required Kinesis permissions

**Step 6.1: Navigate and Verify**

1. On the Lambda function page, click **Configuration** tab → **Triggers**
2. **Expected View:** Empty triggers list
3. Click **Add trigger**
4. **Expected View:** Trigger source selection form

**Step 6.2: Make Selections — Trigger Source**

**Decision Point 1:** Event source type
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| **Kinesis** | Stream processing, ordered events | ✅ Our stream source |
| SQS | Queue-based processing | ❌ Different pattern |
| S3 | File-based event triggers | ❌ Not streaming |
| DynamoDB Streams | React to DB changes | ❌ Different use case |

1. Source: **Kinesis**

**Step 6.3: Configure Trigger Details**

| Field | Value | Explanation |
|-------|-------|-------------|
| Kinesis stream | `handson-events` | Select from dropdown |
| Consumer | No consumer (classic polling) | Standard mode |
| Batch size | `100` | Max records per Lambda invocation |
| Starting position | **Latest** | Process only new records |
| Batch window | `0` seconds | Trigger immediately, don't wait |

**Decision Point 2:** Starting position
| Option | Behavior | For This Project |
|--------|----------|-----------------|
| **Latest** | Only process records after trigger created | ✅ Normal production use |
| Trim horizon | Replay ALL 24h of history | ❌ Would process old test data |
| At timestamp | Custom start point | ❌ Advanced use case |

**Step 6.4: Configure Error Handling**

Expand **Additional settings**:

| Setting | Value | Why |
|---------|-------|-----|
| Bisect batch on function error | ✅ Enable | Isolates bad records without blocking stream |
| Retry attempts | `3` | Retry failed batch 3 times before sending to DLQ |
| Destination on failure | **SQS queue** → `handson-kinesis-dlq` | Capture permanently failed records |
| Maximum record age | `-1` (no limit) | Process all records regardless of age |

**📸 Screenshot 6a:** Trigger config showing batch=100, LATEST, bisect enabled, DLQ selected

**Step 6.5: Validate Result**

1. Click **Add**
2. **Expected Outcome:** Trigger listed with:
   - Source: `handson-events`
   - State: **Enabled**
   - Batch size: 100

**Troubleshooting:**
- Trigger shows **Disabled**: IAM role missing Kinesis read permissions — check inline policy
- "The provided execution role does not have permissions": Role missing `kinesis:GetRecords` — update role policy
- Trigger stuck in Creating: Wait 30 seconds, refresh page

**📸 Screenshot 6b:** Lambda Triggers tab showing Kinesis trigger State = **Enabled**

---

### STEP 7 — Test End-to-End Pipeline

**Prerequisites Check:**
- ✅ All 5 resources created and Active/Enabled
- ✅ Python + boto3 installed locally
- ✅ AWS CLI configured with your credentials

**Step 7.1: Navigate and Verify Pre-test State**

1. Open DynamoDB → Tables → `handson-stream-aggregates` → **Explore table items**
2. **Expected View:** Empty table (0 items)

**📸 Screenshot 7a:** Empty DynamoDB table before running producer

**Step 7.2: Send Test Events**

Run in terminal:
```powershell
cd D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.3_kinesis_streaming
python src/producer.py
```

**Expected View in terminal:**
```
Sending 50 events to stream: handson-events
  [1/50] Sent ORDER_PLACED | Shard: shardId-000000000000 | Seq: 49537014...
  ...
  [50/50] Sent ORDER_PLACED | Shard: shardId-000000000000 | Seq: 49537063...
Done. Sent 50 events.
```

**📸 Screenshot 7b:** Terminal showing producer sending 50 events with Shard IDs

**Step 7.3: View Lambda Logs**

1. Lambda → `handson-kinesis-consumer` → **Monitor** tab
2. Click **View CloudWatch logs**
3. Click the most recent log stream
4. **Expected View:**
```
Processing batch of 50 records
  Processed: ORDER_PLACED | Product: Widget A | Amount: $45.23
  ...
Batch complete: 50 records, 0 errors
```

**Troubleshooting:**
- "No log streams": Lambda hasn't invoked yet — wait 10 seconds and refresh
- "Error decoding record": Base64 decode issue — check consumer_lambda.py code
- "Table not found": TABLE_NAME env var missing or wrong — check Lambda configuration

**📸 Screenshot 7c:** CloudWatch logs showing `Batch complete: 50 records, 0 errors`

**Step 7.4: Verify DynamoDB Aggregates**

1. DynamoDB → Tables → `handson-stream-aggregates` → **Explore table items**
2. **Expected View:** Items like:

| pk | sk | order_count | total_revenue |
|----|----|----|---|
| PRODUCT#Widget A | HOUR#2024-01-15T14:00:00Z | 15 | 45300 |
| PRODUCT#Gadget X | HOUR#2024-01-15T14:00:00Z | 8 | 48800 |

Note: `total_revenue` is in **cents** — divide by 100 for dollars

**📸 Screenshot 7d:** DynamoDB showing product aggregates with order counts

**Step 7.5: Validate CloudWatch Metrics**

1. Kinesis console → `handson-events` → **Monitoring** tab
2. **Expected graphs:**
   - `PutRecords.Records`: spike to 50 when producer ran
   - `GetRecords.IteratorAgeMilliseconds`: briefly high → drops to 0 (Lambda caught up)

**📸 Screenshot 7e:** Kinesis monitoring showing IncomingRecords spike and IteratorAge near 0

---

### Console UI Summary

| Resource | Name | Location |
|----------|------|----------|
| Kinesis Stream | `handson-events` | Kinesis → Data Streams |
| DynamoDB Table | `handson-stream-aggregates` | DynamoDB → Tables |
| IAM Role | `handson-kinesis-consumer-role` | IAM → Roles |
| SQS DLQ | `handson-kinesis-dlq` | SQS → Queues |
| Lambda Function | `handson-kinesis-consumer` | Lambda → Functions |
| Lambda Trigger | Kinesis: `handson-events` | Lambda → Configuration → Triggers |

### Screenshot Summary (Console Method)
| # | Description | Step |
|---|-------------|------|
| P0 | Console with us-east-1 selected | Phase 0 |
| 1a | Kinesis Data Streams empty list | Step 1.1 |
| 1b | Stream form: Provisioned, 1 shard | Step 1.4 |
| 1c | Stream Active (green) | Step 1.6 |
| 1d | Stream Details tab | Step 1.7 |
| 2a | DynamoDB empty list | Step 2.1 |
| 2b | Table Active | Step 2.4 |
| 3a | IAM Roles list | Step 3.1 |
| 3b | Role creation confirmation | Step 3.4 |
| 3c | Role with both policies | Step 3.6 |
| 4a | SQS DLQ created | Step 4.4 |
| 5a | Lambda empty list | Step 5.1 |
| 5b | Lambda creation form | Step 5.3 |
| 5c | Lambda code showing consumer_lambda.py | Step 5.4 |
| 5d | Lambda config: env var + timeout | Step 5.6 |
| 6a | Trigger config form | Step 6.3 |
| 6b | Trigger Enabled | Step 6.5 |
| 7a | Empty DynamoDB before test | Step 7.1 |
| 7b | Producer terminal output | Step 7.2 |
| 7c | CloudWatch logs: batch complete | Step 7.3 |
| 7d | DynamoDB aggregates table | Step 7.4 |
| 7e | Kinesis monitoring metrics | Step 7.5 |

**Total: 22 screenshots for complete documentation**
