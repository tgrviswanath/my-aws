# Steps — Project 9.8 Schema Evolution & Partitioning
# PowerShell (Windows)

---

## Phase 0 — Set Variables

```powershell
cd D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.8_schema_evolution

$REGION   = "us-east-1"
$ACCOUNT  = aws sts get-caller-identity --query Account --output text
$BUCKET   = "handson-data-lake-$ACCOUNT"
$REGISTRY = "handson-registry"
$SCHEMA   = "orders-schema"
$DB_NAME  = "handson_schema_demo"
$TABLE    = "orders_partitioned"
Write-Host "Account: $ACCOUNT | Bucket: $BUCKET"
```

---

## Phase 1 — Run Python Demo (Schema Evolution)

```powershell
pip install boto3 pyarrow pandas s3fs

$env:DATA_LAKE_BUCKET = $BUCKET
python src\schema_evolution_demo.py
# Expected:
# v1 schema: ['order_id', 'customer_id', 'amount', 'order_date']
# v2 schema: ['order_id', 'customer_id', 'amount', 'order_date', 'product', 'discount_pct']
# Merged columns: [...all 6 cols...]
# Total rows: 5  (v1 rows show NaN for product/discount_pct)

aws s3 ls "s3://$BUCKET/schema-demo/" --recursive
# Expected: v1_orders.parquet + v2_orders.parquet
```

---

## Phase 2 — Create Glue Schema Registry

```powershell
aws glue create-registry `
  --registry-name $REGISTRY `
  --description "Schema registry for handson data streams"

aws glue get-registry `
  --registry-id "RegistryName=$REGISTRY" `
  --query "Status"
# Expected: "AVAILABLE"
```

---

## Phase 3 — Register v1 Schema (Avro)

```powershell
$V1 = '{"type":"record","name":"Order","namespace":"handson.orders","fields":[{"name":"order_id","type":"string"},{"name":"customer_id","type":"string"},{"name":"amount","type":"double"},{"name":"order_date","type":"string"}]}'

aws glue create-schema `
  --registry-id "RegistryName=$REGISTRY" `
  --schema-name $SCHEMA --data-format AVRO `
  --compatibility BACKWARD `
  --schema-definition $V1

# Verify
aws glue get-schema `
  --schema-id "RegistryName=$REGISTRY,SchemaName=$SCHEMA" `
  --query "{Version:LatestSchemaVersion,Status:SchemaStatus,Compat:Compatibility}"
# Expected: Version=1, Status=AVAILABLE, Compat=BACKWARD
```

---

## Phase 4 — Register v2 Schema (Backward Compatible)

```powershell
# New fields MUST use ["null","type"] union + "default":null for BACKWARD compat
$V2 = '{"type":"record","name":"Order","namespace":"handson.orders","fields":[{"name":"order_id","type":"string"},{"name":"customer_id","type":"string"},{"name":"amount","type":"double"},{"name":"order_date","type":"string"},{"name":"product","type":["null","string"],"default":null},{"name":"discount_pct","type":["null","double"],"default":null}]}'

aws glue register-schema-version `
  --schema-id "RegistryName=$REGISTRY,SchemaName=$SCHEMA" `
  --schema-definition $V2
# Expected: VersionNumber=2, Status=AVAILABLE

aws glue list-schema-versions `
  --schema-id "RegistryName=$REGISTRY,SchemaName=$SCHEMA" `
  --query "SchemaVersions[*].{V:VersionNumber,S:Status}"
# Expected: [{"V":1,"S":"AVAILABLE"},{"V":2,"S":"AVAILABLE"}]
```

---

## Phase 5 — Create Glue Table with Partition Projection

```powershell
aws glue create-database `
  --database-input "Name=$DB_NAME"

# Write table JSON to temp file
@"
{"Name":"$TABLE","TableType":"EXTERNAL_TABLE","Parameters":{"EXTERNAL":"TRUE","projection.enabled":"true","projection.year.type":"integer","projection.year.range":"2023,2030","projection.month.type":"integer","projection.month.range":"1,12","projection.month.digits":"2","projection.day.type":"integer","projection.day.range":"1,31","projection.day.digits":"2","storage.location.template":"s3://$BUCKET/processed/orders/year=\${year}/month=\${month}/day=\${day}"},"PartitionKeys":[{"Name":"year","Type":"int"},{"Name":"month","Type":"int"},{"Name":"day","Type":"int"}],"StorageDescriptor":{"Location":"s3://$BUCKET/processed/orders/","InputFormat":"org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat","OutputFormat":"org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat","SerdeInfo":{"SerializationLibrary":"org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe","Parameters":{"serialization.format":"1"}},"Columns":[{"Name":"order_id","Type":"string"},{"Name":"customer_id","Type":"string"},{"Name":"amount","Type":"double"},{"Name":"order_date","Type":"date"},{"Name":"product","Type":"string"}]}}
"@ | Out-File "$env:TEMP\table.json" -Encoding utf8

aws glue create-table --database-name $DB_NAME `
  --table-input "file://$env:TEMP\table.json"

# Verify partition projection
aws glue get-table --database-name $DB_NAME --name $TABLE `
  --query "Table.Parameters.'projection.enabled'"
# Expected: "true"
```

---

## Phase 6 — Test Partition Pruning (Athena)

```powershell
# With partition filter (fast)
$Q1 = aws athena start-query-execution `
  --query-string "SELECT COUNT(*) FROM ${DB_NAME}.${TABLE} WHERE year=2024 AND month=1" `
  --query-execution-context "Database=$DB_NAME" `
  --result-configuration "OutputLocation=s3://$BUCKET/athena-results/" `
  --query "QueryExecutionId" --output text
aws athena wait query-execution-complete --query-execution-id $Q1
$SCAN1 = aws athena get-query-execution --query-execution-id $Q1 `
  --query "QueryExecution.Statistics.DataScannedInBytes" --output text
Write-Host "With filter: $([math]::Round($SCAN1/1024,1)) KB scanned"

# Without filter (scans all data)
$Q2 = aws athena start-query-execution `
  --query-string "SELECT COUNT(*) FROM ${DB_NAME}.${TABLE}" `
  --query-execution-context "Database=$DB_NAME" `
  --result-configuration "OutputLocation=s3://$BUCKET/athena-results/" `
  --query "QueryExecutionId" --output text
aws athena wait query-execution-complete --query-execution-id $Q2
$SCAN2 = aws athena get-query-execution --query-execution-id $Q2 `
  --query "QueryExecution.Statistics.DataScannedInBytes" --output text
Write-Host "Without filter: $([math]::Round($SCAN2/1024,1)) KB scanned"
Write-Host "Savings: $([math]::Round((1-$SCAN1/$SCAN2)*100,1))%"
```

---

## Phase 7 — Cleanup

```powershell
aws glue delete-table --database-name $DB_NAME --name $TABLE
aws glue delete-database --name $DB_NAME
aws glue delete-schema `
  --schema-id "RegistryName=$REGISTRY,SchemaName=$SCHEMA"
aws glue delete-registry --registry-id "RegistryName=$REGISTRY"
aws s3 rm "s3://$BUCKET/schema-demo/" --recursive
Write-Host "✅ Cleanup complete"
```

---

## Screenshots to Take

- [ ] Glue Schema Registry showing `handson-registry` Available
- [ ] Schema `orders-schema` with v1 + v2 both Available
- [ ] Terminal: merged Parquet read showing NaN for v1 rows
- [ ] S3: `schema-demo/year=2024/month=01/` with v1 and v2 Parquet files
- [ ] Glue table `orders_partitioned` partition projection properties
- [ ] Athena: WITH filter — low DataScanned value
- [ ] Athena: WITHOUT filter — higher DataScanned value
