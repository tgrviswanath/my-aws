# Steps — Project 9.6 dbt Transformation Pipeline

## Phase 1 — Install dbt

```bash
# Install dbt with Athena adapter
pip install dbt-athena-community

# Verify
dbt --version
```

---

## Phase 2 — Configure dbt Profile

```bash
mkdir -p ~/.dbt

cat > ~/.dbt/profiles.yml << 'EOF'
handson:
  target: dev
  outputs:
    dev:
      type: athena
      s3_staging_dir: s3://handson-athena-results-ACCOUNTID/dbt/
      region_name: us-east-1
      database: awsdatacatalog
      schema: handson_data_lake
      work_group: handson-data-lake
EOF
```

---

## Phase 3 — Initialize and Run

```bash
cd dbt_project

# Test connection
dbt debug

# Run all models
dbt run

# Run only staging models
dbt run --select staging

# Run only marts
dbt run --select marts

# Run with full refresh (rebuild from scratch)
dbt run --full-refresh
```

---

## Phase 4 — Run Tests

```bash
# Run all tests
dbt test

# Run tests for specific model
dbt test --select fct_orders

# Expected output:
# PASS not_null_fct_orders_order_id
# PASS unique_fct_orders_order_id
# PASS accepted_values_fct_orders_order_status
```

---

## Phase 5 — Generate and View Documentation

```bash
# Generate docs
dbt docs generate

# Serve docs locally
dbt docs serve --port 8080
# Open: http://localhost:8080
# See: lineage graph, model descriptions, test results
```

---

## Phase 6 — Query dbt Models in Athena

```bash
# After dbt run, query the mart tables
aws athena start-query-execution \
  --query-string "SELECT order_tier, COUNT(*) as orders, SUM(order_amount_usd) as revenue FROM fct_orders GROUP BY order_tier" \
  --work-group handson-data-lake \
  --query-execution-context Database=handson_data_lake \
  --query "QueryExecutionId" --output text
```

---

## Screenshots to Take
- [ ] `dbt run` output showing models built
- [ ] `dbt test` output showing all tests passing
- [ ] dbt docs lineage graph in browser
- [ ] Athena showing dbt-created tables
- [ ] Incremental model only processing new rows
