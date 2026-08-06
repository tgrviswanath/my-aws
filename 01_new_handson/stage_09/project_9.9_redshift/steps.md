# Steps — Project 9.9 Redshift Data Warehouse
# PowerShell (Windows)

---

## Phase 0 — Set Variables

```powershell
cd D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.9_redshift

$REGION     = "us-east-1"
$ACCOUNT    = aws sts get-caller-identity --query Account --output text
$BUCKET     = "handson-data-lake-$ACCOUNT"
$NS_NAME    = "handson-namespace"
$WG_NAME    = "handson-workgroup"
$ROLE_NAME  = "handson-redshift-role"
$DB         = "analytics"
$ADMIN_USER = "admin"
$ADMIN_PASS = "Admin@1234!"   # CHANGE THIS

$VPC_ID     = aws ec2 describe-vpcs --query "Vpcs[?IsDefault==\`true\`].VpcId" --output text
$SUBNET_IDS = (aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" `
               --query "Subnets[0:2].SubnetId" --output text) -split "`t"
Write-Host "Account: $ACCOUNT | VPC: $VPC_ID"
```

---

## Phase 1 — Create IAM Role

```powershell
@'
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"redshift.amazonaws.com"},"Action":"sts:AssumeRole"}]}
'@ | Out-File "$env:TEMP\rs-trust.json" -Encoding utf8

aws iam create-role --role-name $ROLE_NAME `
  --assume-role-policy-document "file://$env:TEMP\rs-trust.json"
aws iam attach-role-policy --role-name $ROLE_NAME `
  --policy-arn "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
aws iam attach-role-policy --role-name $ROLE_NAME `
  --policy-arn "arn:aws:iam::aws:policy/AWSGlueConsoleFullAccess"

$ROLE_ARN = aws iam get-role --role-name $ROLE_NAME --query "Role.Arn" --output text
Write-Host "Role ARN: $ROLE_ARN"
```

---

## Phase 2 — Create Security Group

```powershell
$SG_ID = aws ec2 create-security-group `
  --group-name "handson-redshift-sg" `
  --description "Redshift port 5439" `
  --vpc-id $VPC_ID --query "GroupId" --output text

$VPC_CIDR = aws ec2 describe-vpcs --vpc-ids $VPC_ID `
  --query "Vpcs[0].CidrBlock" --output text
aws ec2 authorize-security-group-ingress `
  --group-id $SG_ID --protocol tcp --port 5439 --cidr $VPC_CIDR
Write-Host "SG: $SG_ID allows port 5439 from $VPC_CIDR"
```

---

## Phase 3 — Create Namespace + Workgroup

```powershell
# Namespace
aws redshift-serverless create-namespace `
  --namespace-name $NS_NAME --admin-username $ADMIN_USER `
  --admin-user-password $ADMIN_PASS --db-name $DB `
  --iam-roles $ROLE_ARN --tags "Key=Project,Value=handson"

# Wait for AVAILABLE
for ($i=0; $i -lt 20; $i++) {
  $ST = aws redshift-serverless get-namespace `
    --namespace-name $NS_NAME --query "namespace.status" --output text
  if ($ST -eq "AVAILABLE") { break }
  Write-Host "Namespace: $ST"; Start-Sleep -Seconds 15
}

# Workgroup
aws redshift-serverless create-workgroup `
  --namespace-name $NS_NAME --workgroup-name $WG_NAME `
  --base-capacity 8 --subnet-ids $SUBNET_IDS `
  --security-group-ids $SG_ID --publicly-accessible false `
  --tags "Key=Project,Value=handson"

# Wait for AVAILABLE (5-10 min)
Write-Host "Waiting for workgroup (5-10 min)..."
for ($i=0; $i -lt 40; $i++) {
  $ST = aws redshift-serverless get-workgroup `
    --workgroup-name $WG_NAME --query "workgroup.status" --output text
  Write-Host "[$i] $ST"
  if ($ST -eq "AVAILABLE") { break }
  Start-Sleep -Seconds 15
}

$ENDPOINT = aws redshift-serverless get-workgroup `
  --workgroup-name $WG_NAME --query "workgroup.endpoint.address" --output text
Write-Host "Endpoint: $ENDPOINT"
```

---

## Phase 4 — Setup Tables + Load Data

```powershell
pip install psycopg2-binary boto3

$env:REDSHIFT_HOST     = $ENDPOINT
$env:REDSHIFT_USER     = $ADMIN_USER
$env:REDSHIFT_PASSWORD = $ADMIN_PASS
$env:REDSHIFT_DB       = $DB
$env:S3_BUCKET         = $BUCKET
$env:IAM_ROLE_ARN      = $ROLE_ARN

python code\redshift_operations.py setup
# Expected: ✓ Schema ready, ✓ fact_orders, ✓ dim_date, ✓ populated

python code\redshift_operations.py load
# Expected: ✓ Load complete — N rows in fact_orders

python code\redshift_operations.py report
# Expected: 4 formatted analytics tables
```

---

## Phase 5 — Query via Data API

```powershell
$QID = aws redshift-data execute-statement `
  --workgroup-name $WG_NAME --database $DB `
  --sql "SELECT product_id,COUNT(*) orders,SUM(total_amount) revenue FROM analytics.fact_orders GROUP BY 1 ORDER BY 3 DESC LIMIT 5;" `
  --query "Id" --output text
Start-Sleep -Seconds 5
aws redshift-data get-statement-result --id $QID `
  --query "Records[*][0:3][*].stringValue"
```

---

## Phase 6 — Cleanup

```powershell
aws redshift-serverless delete-workgroup --workgroup-name $WG_NAME
Start-Sleep -Seconds 120  # wait for workgroup deletion
aws redshift-serverless delete-namespace --namespace-name $NS_NAME
aws ec2 delete-security-group --group-id $SG_ID
aws iam detach-role-policy --role-name $ROLE_NAME --policy-arn "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
aws iam detach-role-policy --role-name $ROLE_NAME --policy-arn "arn:aws:iam::aws:policy/AWSGlueConsoleFullAccess"
aws iam delete-role --role-name $ROLE_NAME
Write-Host "✅ Cleanup complete"
```

---

## Screenshots to Take

- [ ] IAM role `handson-redshift-role` with 2 policies attached
- [ ] Workgroup `handson-workgroup` Status = Available
- [ ] Workgroup details showing endpoint URL
- [ ] Terminal: `setup` output — all ✓
- [ ] Terminal: `load` — COPY complete + row count
- [ ] Terminal: `report` — formatted analytics tables
- [ ] Redshift Query Editor v2 — query result + execution time
- [ ] CLI: Data API result for top products
