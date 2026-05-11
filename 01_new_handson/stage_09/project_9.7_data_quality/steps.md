# Steps — Project 9.7 Data Quality Validation

## Phase 1 — Install Dependencies

```bash
pip install great-expectations pyarrow s3fs pandas
```

---

## Phase 2 — Run Validation Against Sample Data

```bash
# Create sample data with intentional quality issues
python3 << 'EOF'
import pandas as pd

df = pd.DataFrame({
    "order_id":   ["ORD-001", "ORD-002", None, "ORD-001"],  # null + duplicate
    "customer_id": ["C1", "C2", "C3", "C4"],
    "product":    ["Widget A", "Widget B", "Unknown Product", "Widget C"],
    "amount":     [29.99, -5.00, 49.99, 19.99],  # negative amount
    "order_date": ["2024-01-15", "2024-01-15", "2024-01-16", "2024-01-16"],
})

df.to_parquet("/tmp/test_orders.parquet", index=False)
print("Sample data created with quality issues")
EOF

# Run validation
python3 src/validate_orders.py
# Expected: FAILED — shows which checks failed
```

---

## Phase 3 — Fix Data and Re-validate

```bash
python3 << 'EOF'
import pandas as pd

# Clean data
df = pd.DataFrame({
    "order_id":   ["ORD-001", "ORD-002", "ORD-003"],
    "customer_id": ["C1", "C2", "C3"],
    "product":    ["Widget A", "Widget B", "Widget C"],
    "amount":     [29.99, 49.99, 19.99],
    "order_date": ["2024-01-15", "2024-01-15", "2024-01-16"],
})

df.to_parquet("/tmp/clean_orders.parquet", index=False)
print("Clean data created")
EOF

python3 src/validate_orders.py
# Expected: PASSED — all checks green
```

---

## Phase 4 — Integrate with Airflow Pipeline

```python
# In your Airflow DAG, add after ETL step:
validate_task = PythonOperator(
    task_id="validate_data_quality",
    python_callable=lambda: subprocess.run(
        ["python3", "src/validate_orders.py"],
        check=True  # raises exception if validation fails
    ),
)

# Pipeline stops if validation fails — bad data never reaches analytics
run_glue_etl >> validate_task >> run_dbt_task
```

---

## Screenshots to Take
- [ ] Validation FAILED output showing specific failed checks
- [ ] Validation PASSED output after fixing data
- [ ] Great Expectations data docs HTML report
- [ ] Airflow pipeline stopping on validation failure
