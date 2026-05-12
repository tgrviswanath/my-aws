# Project 9.8 — Schema Evolution & Partitioning

## What This Does
Handles real-world data engineering challenges: schemas change over time (new columns, renamed fields), and data must be partitioned efficiently for fast queries.

## Topics Covered
| Topic | Description |
|-------|-------------|
| Glue Schema Registry | Version and validate schemas (Avro/JSON/Protobuf) |
| Schema evolution | Add columns without breaking existing consumers |
| Partition pruning | Query only relevant partitions — 100x faster |
| Parquet optimization | Compression, row groups, column statistics |
| Partition projection | Athena auto-discovers partitions without MSCK REPAIR |
| Compaction | Merge small files into large ones for better performance |

## Partitioning Strategy
```
Good:   s3://bucket/orders/year=2024/month=01/day=15/
Bad:    s3://bucket/orders/2024-01-15/
Worse:  s3://bucket/orders/ (no partitioning)

Rule: partition by columns you filter on most often
```

## How to Run
```bash
python3 src/schema_evolution_demo.py
```

## Lessons Learned
- Parquet supports schema evolution: add nullable columns safely
- Never rename or delete columns — add new ones instead
- Small files problem: thousands of 1 KB files = slow queries — compact to 128 MB+
- Partition cardinality: don't partition by high-cardinality columns (e.g. user_id)
- Glue Schema Registry: enforce schema at producer — reject bad messages early

## Code

### `src/schema_evolution_demo.py` — Glue schema registry demo

```bash
pip install boto3

export GLUE_REGISTRY=handson-registry
export GLUE_SCHEMA=orders-schema

# Register initial schema (v1)
python src/schema_evolution_demo.py register-v1

# Evolve schema (add new optional field — backward compatible)
python src/schema_evolution_demo.py register-v2

# List all schema versions
python src/schema_evolution_demo.py list-versions

# Validate a record against the schema
python src/schema_evolution_demo.py validate
```

Demonstrates: backward-compatible schema evolution (adding optional fields), Glue Schema Registry versioning, Parquet partition pruning.
