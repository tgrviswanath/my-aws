# Steps — Project 9.1 Data Lake Architecture

## Phase 1 — Deploy

```bash
cd terraform
terraform init && terraform apply -auto-approve
BUCKET=$(terraform output -raw data_lake_bucket)
```

---

## Phase 2 — Upload Sample Data

```bash
# Create sample CSV data
cat > /tmp/orders.csv << 'EOF'
order_id,customer_id,product,amount,order_date
ORD-001,CUST-101,Widget A,29.99,2024-01-15
ORD-002,CUST-102,Widget B,49.99,2024-01-15
ORD-003,CUST-101,Widget C,19.99,2024-01-16
ORD-004,CUST-103,Widget A,29.99,2024-01-16
EOF

# Upload to raw zone (partitioned by date)
aws s3 cp /tmp/orders.csv \
  s3://$BUCKET/raw/orders/year=2024/month=01/day=15/orders.csv

# Convert to Parquet using Python
python3 << 'EOF'
import pandas as pd
df = pd.read_csv('/tmp/orders.csv')
df['year'] = pd.to_datetime(df['order_date']).dt.year
df['month'] = pd.to_datetime(df['order_date']).dt.month
df.to_parquet('/tmp/orders.parquet', index=False)
print(df)
EOF

# Upload Parquet to processed zone
aws s3 cp /tmp/orders.parquet \
  s3://$BUCKET/processed/orders/year=2024/month=01/orders.parquet
```

---

## Phase 3 — Run Glue Crawler

```bash
# Start crawler manually (don't wait for schedule)
aws glue start-crawler --name handson-raw-crawler

# Wait for completion
aws glue get-crawler --name handson-raw-crawler \
  --query "Crawler.State" --output text
# Wait until: READY

# Check discovered tables
aws glue get-tables \
  --database-name handson_data_lake \
  --query "TableList[*].{Name:Name,Location:StorageDescriptor.Location}"
```

---

## Phase 4 — Query with Athena

```bash
WORKGROUP=$(terraform output -raw athena_workgroup)
DATABASE=$(terraform output -raw glue_database)

# Run query
QUERY_ID=$(aws athena start-query-execution \
  --query-string "SELECT * FROM orders LIMIT 10" \
  --work-group $WORKGROUP \
  --query-execution-context Database=$DATABASE \
  --query "QueryExecutionId" --output text)

aws athena wait query-execution-complete --query-execution-id $QUERY_ID

aws athena get-query-results --query-execution-id $QUERY_ID \
  --query "ResultSet.Rows[*].Data[*].VarCharValue" --output table
```

---

## Screenshots to Take
- [ ] S3 bucket with raw/processed/curated zones
- [ ] Glue Crawler discovering schema
- [ ] Glue Data Catalog showing tables
- [ ] Athena query returning results
- [ ] Parquet vs CSV size comparison
- [ ] Partition pruning in Athena (WHERE year=2024)
