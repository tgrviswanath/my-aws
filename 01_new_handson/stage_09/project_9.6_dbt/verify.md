# Verification & Validation — Project 9.6 dbt Transformation Pipeline

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| Athena / Redshift | Athena Query Editor or Redshift | `stg_orders`, `fct_daily_revenue` tables/views exist |
| S3 dbt artifacts | S3 → data lake bucket → dbt/ | `manifest.json`, `catalog.json` present (after `dbt docs generate`) |
| Glue Tables | Glue → Tables → processed_db | dbt model tables listed |

📸 Screenshot: `dbt run` output showing all models pass  
📸 Screenshot: `dbt test` output showing all tests pass  
📸 Screenshot: `dbt docs serve` lineage graph  
📸 Screenshot: Athena query on `fct_daily_revenue` returning results

---

## 2. CLI Verification

```bash
cd dbt_project

# 2.1 Test dbt connection
dbt debug
# Expected: All checks passed

# 2.2 Install dependencies
dbt deps
# Expected: packages installed (if packages.yml exists)

# 2.3 Run all models
dbt run
# Expected output:
# 1 of 3 START sql view model processed_db.stg_orders ............. [RUN]
# 1 of 3 OK created sql view model processed_db.stg_orders ........ [OK in 2.34s]
# 2 of 3 START sql table model processed_db.int_orders_enriched ... [RUN]
# 2 of 3 OK created sql table model processed_db.int_orders_enriched [OK in 5.12s]
# 3 of 3 START sql table model processed_db.fct_daily_revenue ...... [RUN]
# 3 of 3 OK created sql table model processed_db.fct_daily_revenue . [OK in 3.45s]
# Finished running 3 models in 0:00:12

# 2.4 Run all tests
dbt test
# Expected:
# 1 of 4 START test not_null_stg_orders_order_id ................... [RUN]
# 1 of 4 PASS not_null_stg_orders_order_id ......................... [PASS in 1.23s]
# 2 of 4 PASS unique_stg_orders_order_id ........................... [PASS in 1.45s]
# 3 of 4 PASS not_null_fct_daily_revenue_order_date ................ [PASS in 1.12s]
# 4 of 4 PASS accepted_values_stg_orders_status .................... [PASS in 1.34s]
# All 4 tests passed

# 2.5 Generate documentation
dbt docs generate
# Expected: catalog.json and manifest.json created

# 2.6 Query a dbt model via Athena CLI
BUCKET=$(aws s3 ls | grep handson-data-lake | awk '{print $3}')
QUERY_ID=$(aws athena start-query-execution \
  --query-string "SELECT order_date, total_orders, total_revenue FROM processed_db.fct_daily_revenue ORDER BY order_date DESC LIMIT 5;" \
  --query-execution-context Database=processed_db \
  --result-configuration OutputLocation=s3://$BUCKET/athena-results/ \
  --query "QueryExecutionId" --output text)
aws athena wait query-execution-complete --query-execution-id $QUERY_ID
aws athena get-query-results --query-execution-id $QUERY_ID \
  --query "ResultSet.Rows[*].Data[*].VarCharValue" --output table
# Expected: daily revenue rows returned

# 2.7 Check model freshness (if sources configured)
dbt source freshness
# Expected: sources within freshness threshold
```

---

## 3. dbt Artifacts Verification

```bash
cd dbt_project

# 3.1 Confirm manifest.json exists after run
ls -la target/manifest.json target/catalog.json 2>/dev/null
# Expected: both files exist

# 3.2 Check model count in manifest
python3 -c "
import json
with open('target/manifest.json') as f:
    m = json.load(f)
nodes = [k for k in m['nodes'] if m['nodes'][k]['resource_type'] == 'model']
print(f'Models in manifest: {len(nodes)}')
for n in nodes:
    print(' -', m['nodes'][n]['name'])
"
# Expected: stg_orders, int_orders_enriched, fct_daily_revenue listed

# 3.3 Check test results
python3 -c "
import json
with open('target/run_results.json') as f:
    r = json.load(f)
results = r.get('results', [])
passed = sum(1 for x in results if x['status'] == 'pass')
failed = sum(1 for x in results if x['status'] == 'fail')
print(f'Tests: {passed} passed, {failed} failed')
"
# Expected: all passed, 0 failed
```

---

## 4. Health Check — Incremental Model Test

```bash
cd dbt_project

# Run incremental model (only processes new rows)
dbt run --select fct_daily_revenue --full-refresh
# Expected: full refresh completes

# Add new data and run incrementally
dbt run --select fct_daily_revenue
# Expected: only new rows processed (faster than full refresh)

# Verify row count increased
BUCKET=$(aws s3 ls | grep handson-data-lake | awk '{print $3}')
QUERY_ID=$(aws athena start-query-execution \
  --query-string "SELECT COUNT(*) FROM processed_db.fct_daily_revenue;" \
  --query-execution-context Database=processed_db \
  --result-configuration OutputLocation=s3://$BUCKET/athena-results/ \
  --query "QueryExecutionId" --output text)
aws athena wait query-execution-complete --query-execution-id $QUERY_ID
aws athena get-query-results --query-execution-id $QUERY_ID \
  --query "ResultSet.Rows[1].Data[0].VarCharValue"
# Expected: row count > 0
```

---

## 5. Expected Successful Outputs

**dbt run:**
```
Finished running 3 models in 0:00:12.
3 of 3 OK
```

**dbt test:**
```
Finished running 4 tests in 0:00:06.
4 passed, 0 failed, 0 errors, 0 skipped
```

**Athena fct_daily_revenue:**
```
| order_date | total_orders | total_revenue |
|------------|--------------|---------------|
| 2024-01-15 | 42           | 1234.56       |
| 2024-01-14 | 38           | 1102.34       |
```

---

## 6. Verification Checklist

- [ ] `dbt debug` — all checks passed
- [ ] `dbt run` — all 3 models OK (stg_orders, int_orders_enriched, fct_daily_revenue)
- [ ] `dbt test` — all tests passed (not_null, unique, accepted_values)
- [ ] `dbt docs generate` — manifest.json and catalog.json created
- [ ] `stg_orders` view exists in Athena/Redshift
- [ ] `fct_daily_revenue` table exists and returns rows
- [ ] Incremental model run processes only new rows
- [ ] `dbt source freshness` passes (if sources configured)
