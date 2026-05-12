# Architecture — Project 9.8 Schema Evolution & Partitioning

## Schema Evolution Rules

```
BACKWARD compatible (recommended):
  ✅ Add new nullable field with default
  ✅ Remove field with default
  ❌ Rename field
  ❌ Change field type
  ❌ Add required field without default

Example — safe v1 → v2 evolution:
  v1: {order_id, customer_id, amount, order_date}
  v2: {order_id, customer_id, amount, order_date, product=null, discount=null}

  Old consumers reading v2 data: product/discount = null (ignored)
  New consumers reading v1 data: product/discount = null (default)
```

## Partition Projection

```
Without partition projection:
  New partition added to S3
  → Must run: MSCK REPAIR TABLE orders
  → Athena discovers new partition
  → Queries can now use it
  Problem: manual step, easy to forget

With partition projection:
  New partition added to S3
  → Athena automatically knows about it
  → No MSCK REPAIR TABLE needed
  → Queries work immediately

Configuration:
  projection.year.type  = integer
  projection.year.range = 2023,2030
  → Athena generates all year values 2023-2030 automatically
```

## Small Files Problem

```
Problem:
  1000 files × 1 KB = 1 GB total
  Athena opens 1000 files → slow (file open overhead)
  S3 LIST operations → expensive

Solution (compaction):
  1000 files × 1 KB → 1 file × 1 GB
  Athena opens 1 file → fast
  Optimal file size: 128 MB - 1 GB

Compaction with Spark:
  df.coalesce(1).write.parquet("s3://bucket/compacted/")
```
