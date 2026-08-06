# Steps — Project 9.6 dbt Transformation Pipeline
# PowerShell (Windows)

---

## Phase 0 — Set Variables

```powershell
cd D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.6_dbt

$REGION    = "us-east-1"
$ACCOUNT   = aws sts get-caller-identity --query Account --output text
$DATA_BUCKET    = "handson-data-lake-$ACCOUNT"
$STAGING_BUCKET = "handson-dbt-staging-$ACCOUNT"
$DBT_DIR   = "D:\1.projects\AI\my-aws\01_new_handson\stage_09\project_9.6_dbt\dbt_project"
Write-Host "Account: $ACCOUNT"
```

---

## Phase 1 — Install dbt + Create S3 Staging Bucket

```powershell
pip install dbt-athena-community==1.7.1
dbt --version

aws s3api create-bucket --bucket $STAGING_BUCKET --region $REGION
aws s3api put-public-access-block --bucket $STAGING_BUCKET `
  --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
```

---

## Phase 2 — Configure profiles.yml

```powershell
New-Item -ItemType Directory -Path "$env:USERPROFILE\.dbt" -Force

@"
handson:
  target: dev
  outputs:
    dev:
      type: athena
      s3_staging_dir: s3://$STAGING_BUCKET/dbt/
      region_name: $REGION
      database: awsdatacatalog
      schema: handson_data_lake
      work_group: handson-dbt
      threads: 4
"@ | Out-File "$env:USERPROFILE\.dbt\profiles.yml" -Encoding utf8
```

---

## Phase 3 — Create Project Config Files

```powershell
Set-Location $DBT_DIR

# dbt_project.yml
@'
name: 'handson'
version: '1.0.0'
config-version: 2
profile: 'handson'
model-paths: ["models"]
models:
  handson:
    staging:
      +materialized: view
    marts:
      +materialized: table
'@ | Out-File "dbt_project.yml" -Encoding utf8

# Source definition
@'
version: 2
sources:
  - name: raw
    database: awsdatacatalog
    schema: handson_data_lake
    tables:
      - name: orders
'@ | Out-File "models\staging\schema.yml" -Encoding utf8

# packages.yml
@'
packages:
  - package: dbt-labs/dbt_utils
    version: 1.1.1
'@ | Out-File "packages.yml" -Encoding utf8
```

---

## Phase 4 — Test Connection

```powershell
dbt deps    # install dbt-utils
dbt debug   # test Athena connection
# Expected: All checks passed
```

---

## Phase 5 — Run Models

```powershell
dbt run                              # all models
dbt run --select staging             # staging only
dbt run --select fct_orders          # single model
dbt run --full-refresh               # ignore incremental filter
```

---

## Phase 6 — Run Tests

```powershell
dbt test                             # all tests
dbt test --select fct_orders         # single model
# Expected: PASS=7 WARN=0 ERROR=0 FAIL=0
```

---

## Phase 7 — Documentation

```powershell
dbt docs generate
dbt docs serve --port 8080
# Open: http://localhost:8080  (Ctrl+C to stop)
```

---

## Phase 8 — Query in Athena

```powershell
$QID = aws athena start-query-execution `
  --query-string "SELECT order_tier,COUNT(*) as n,SUM(order_amount_usd) as rev FROM handson_data_lake.fct_orders GROUP BY 1 ORDER BY rev DESC" `
  --work-group "handson-dbt" `
  --result-configuration "OutputLocation=s3://$STAGING_BUCKET/dbt/results/" `
  --query "QueryExecutionId" --output text
aws athena wait query-execution-complete --query-execution-id $QID
aws athena get-query-results --query-execution-id $QID `
  --query "ResultSet.Rows[*].Data[*].VarCharValue" --output table
```

---

## Phase 9 — Cleanup

```powershell
# Drop dbt tables
aws athena start-query-execution `
  --query-string "DROP VIEW IF EXISTS handson_data_lake.stg_orders" `
  --result-configuration "OutputLocation=s3://$STAGING_BUCKET/dbt/cleanup/" | Out-Null

aws athena start-query-execution `
  --query-string "DROP TABLE IF EXISTS handson_data_lake.fct_orders" `
  --result-configuration "OutputLocation=s3://$STAGING_BUCKET/dbt/cleanup/" | Out-Null

# Delete S3 + workgroup
aws s3 rm "s3://$STAGING_BUCKET" --recursive
aws s3api delete-bucket --bucket $STAGING_BUCKET
aws athena delete-work-group --work-group "handson-dbt" --recursive-delete-option
Write-Host "✅ Cleanup complete"
```

---

## Screenshots to Take

- [ ] `dbt debug` — all checks passed
- [ ] `dbt run` first run — PASS=2 TOTAL=2
- [ ] `dbt run` second run — faster (incremental only new rows)
- [ ] `dbt test` — all 7 tests PASS
- [ ] `dbt docs serve` lineage graph in browser
- [ ] Athena table list showing stg_orders + fct_orders
- [ ] Athena fct_orders query returning order_tier results
