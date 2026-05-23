# Verification & Validation — Project 9.9 Redshift Data Warehouse

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| Redshift Serverless | Redshift → Serverless dashboard | Namespace + Workgroup listed, Status = **Available** |
| Workgroup | Redshift Serverless → Workgroups | `handson-workgroup` Status = **Available** |
| Query Editor | Redshift → Query Editor v2 | Can connect and run queries |
| Tables | Query Editor → Schema browser | `fact_orders`, `dim_customers`, `dim_products` tables visible |
| S3 IAM Role | IAM → Roles | Redshift role with S3 read access |

📸 Screenshot: Redshift Serverless workgroup Available  
📸 Screenshot: Query Editor showing tables in analytics schema  
📸 Screenshot: `redshift_operations.py report` output with analytics results

---

## 2. AWS CLI Verification

```bash
# 2.1 Confirm Redshift Serverless workgroup is available
aws redshift-serverless get-workgroup \
  --workgroup-name handson-workgroup \
  --query "workgroup.{Status:status,Endpoint:endpoint.address,Port:endpoint.port}"
# Expected: status=AVAILABLE, endpoint populated

# 2.2 Confirm namespace exists
aws redshift-serverless get-namespace \
  --namespace-name handson-namespace \
  --query "namespace.{Status:status,DBName:dbName,AdminUser:adminUsername}"
# Expected: status=AVAILABLE

# 2.3 Set connection env vars
export REDSHIFT_HOST=$(aws redshift-serverless get-workgroup \
  --workgroup-name handson-workgroup \
  --query "workgroup.endpoint.address" --output text)
export REDSHIFT_USER=admin
export REDSHIFT_DB=analytics

# 2.4 Create tables
python code/redshift_operations.py setup
# Expected: Tables created: fact_orders, dim_customers, dim_products

# 2.5 Load data from S3
BUCKET=$(aws s3 ls | grep handson-data-lake | awk '{print $3}')
python code/redshift_operations.py load \
  --bucket $BUCKET \
  --prefix processed/orders/
# Expected: COPY command completed, N rows loaded

# 2.6 Run analytical queries
python code/redshift_operations.py query
# Expected: query results printed

# 2.7 Print full analytics report
python code/redshift_operations.py report
# Expected: daily revenue, top products, customer LTV printed

# 2.8 Verify via Redshift Data API
QUERY_ID=$(aws redshift-data execute-statement \
  --workgroup-name handson-workgroup \
  --database analytics \
  --sql "SELECT COUNT(*) as total_orders, SUM(amount) as total_revenue FROM fact_orders;" \
  --query "Id" --output text)
sleep 5
aws redshift-data get-statement-result \
  --id $QUERY_ID \
  --query "Records[0][*].longValue"
# Expected: total_orders and total_revenue values
```

---

## 3. Terraform State Verification

```bash
cd terraform

terraform state list
# Expected:
# aws_redshiftserverless_namespace.main
# aws_redshiftserverless_workgroup.main
# aws_iam_role.redshift
# aws_iam_role_policy_attachment.redshift_s3
# aws_security_group.redshift
# aws_vpc_endpoint.redshift (if private access)

terraform state show aws_redshiftserverless_workgroup.main
# Shows: workgroup_name, namespace_name, base_capacity (RPU)

terraform output redshift_endpoint
# Expected: handson-workgroup.xxx.us-east-1.redshift-serverless.amazonaws.com

terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

---

## 4. Health Check — Analytics Queries

```bash
# Run all analytical queries via Redshift Data API
QUERIES=(
  "SELECT COUNT(*) FROM fact_orders;"
  "SELECT product_name, SUM(amount) as revenue FROM fact_orders JOIN dim_products USING(product_id) GROUP BY product_name ORDER BY revenue DESC LIMIT 5;"
  "SELECT DATE_TRUNC('day', order_date) as day, SUM(amount) as daily_revenue FROM fact_orders GROUP BY 1 ORDER BY 1 DESC LIMIT 7;"
)

for SQL in "${QUERIES[@]}"; do
  QUERY_ID=$(aws redshift-data execute-statement \
    --workgroup-name handson-workgroup \
    --database analytics \
    --sql "$SQL" \
    --query "Id" --output text)
  sleep 3
  STATE=$(aws redshift-data describe-statement \
    --id $QUERY_ID \
    --query "Status" --output text)
  echo "Query: $SQL"
  echo "Status: $STATE"
  [ "$STATE" = "FINISHED" ] && echo "✅ Query succeeded" || echo "❌ Query failed"
  echo "---"
done
```

---

## 5. Expected Successful Outputs

**CLI — get-workgroup:**
```json
{ "status": "AVAILABLE", "Endpoint": "handson-workgroup.xxx.us-east-1.redshift-serverless.amazonaws.com", "Port": 5439 }
```

**redshift_operations.py report:**
```
=== Analytics Report ===
Total Orders: 1,000
Total Revenue: $49,823.50

Top 5 Products by Revenue:
  1. Widget A    $12,450.00
  2. Widget B    $9,823.50
  3. Widget C    $8,234.00

Daily Revenue (last 7 days):
  2024-01-15: $1,234.56
  2024-01-14: $1,102.34
  ...

Customer LTV (top 5):
  CUST-001: $892.50 (12 orders)
  CUST-002: $756.00 (9 orders)
```

**terraform output:**
```
redshift_endpoint = "handson-workgroup.xxx.us-east-1.redshift-serverless.amazonaws.com"
redshift_port     = "5439"
```

---

## 6. Verification Checklist

- [ ] Redshift Serverless namespace Status = AVAILABLE
- [ ] Redshift Serverless workgroup `handson-workgroup` Status = AVAILABLE
- [ ] Redshift endpoint accessible (port 5439)
- [ ] IAM role has S3 read access for COPY command
- [ ] `redshift_operations.py setup` creates tables without error
- [ ] `redshift_operations.py load` COPY command succeeds, rows loaded > 0
- [ ] `redshift_operations.py query` returns analytical results
- [ ] `redshift_operations.py report` prints daily revenue, top products, LTV
- [ ] Redshift Data API query returns results
- [ ] `terraform plan` shows no changes
