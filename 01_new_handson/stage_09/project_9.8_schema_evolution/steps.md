# Steps — Project 9.8 Schema Evolution & Partitioning

## Phase 1 — Run Schema Evolution Demo

```bash
pip install pyarrow pandas s3fs boto3

export DATA_LAKE_BUCKET=your-data-lake-bucket
python3 src/schema_evolution_demo.py
```

---

## Phase 2 — Register Schema in Glue Schema Registry

```bash
# Create registry
aws glue create-registry --registry-name handson-registry

# Create schema (Avro format)
aws glue create-schema \
  --registry-id RegistryName=handson-registry \
  --schema-name orders-schema \
  --data-format AVRO \
  --compatibility BACKWARD \
  --schema-definition '{
    "type": "record",
    "name": "Order",
    "fields": [
      {"name": "order_id",    "type": "string"},
      {"name": "customer_id", "type": "string"},
      {"name": "amount",      "type": "double"},
      {"name": "order_date",  "type": "string"}
    ]
  }'

# Register v2 schema (adds nullable field — BACKWARD compatible)
aws glue register-schema-version \
  --schema-id SchemaName=orders-schema,RegistryName=handson-registry \
  --schema-definition '{
    "type": "record",
    "name": "Order",
    "fields": [
      {"name": "order_id",    "type": "string"},
      {"name": "customer_id", "type": "string"},
      {"name": "amount",      "type": "double"},
      {"name": "order_date",  "type": "string"},
      {"name": "product",     "type": ["null", "string"], "default": null}
    ]
  }'
```

---

## Phase 3 — Compact Small Files

```bash
# Small files problem: 1000 files × 1 KB = slow queries
# Solution: compact into fewer large files

python3 << 'EOF'
import s3fs
import pyarrow.parquet as pq
import pyarrow as pa

fs = s3fs.S3FileSystem()
bucket = "your-data-lake-bucket"

# Read all small files
dataset = pq.ParquetDataset(f"{bucket}/raw/orders/", filesystem=fs)
table = dataset.read()

print(f"Total rows: {len(table)}")
print(f"Total size: {table.nbytes / 1024 / 1024:.1f} MB")

# Write as single optimized file
pq.write_table(
    table,
    f"{bucket}/processed/orders_compacted/orders.parquet",
    filesystem=fs,
    compression="snappy",
    row_group_size=128 * 1024 * 1024,  # 128 MB row groups
)
print("Compaction complete!")
EOF
```

---

## Screenshots to Take
- [ ] v1 and v2 Parquet files in S3
- [ ] Merged schema showing NaN for v1 rows
- [ ] Glue Schema Registry with versions
- [ ] Athena query with partition filter (fast) vs without (slow)
- [ ] File size before and after compaction
