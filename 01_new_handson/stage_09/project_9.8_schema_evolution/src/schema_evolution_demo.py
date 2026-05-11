"""
schema_evolution_demo.py — Demonstrates schema evolution with Parquet.
Shows how to safely add columns without breaking existing readers.
"""

import io
import os
import boto3
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

S3_BUCKET = os.environ.get("DATA_LAKE_BUCKET", "handson-data-lake")
s3 = boto3.client("s3")


def write_v1_schema():
    """Write data with original schema (v1)."""
    print("Writing v1 schema data...")

    df_v1 = pd.DataFrame({
        "order_id":   ["ORD-001", "ORD-002", "ORD-003"],
        "customer_id": ["C1", "C2", "C3"],
        "amount":     [29.99, 49.99, 19.99],
        "order_date": pd.to_datetime(["2024-01-15", "2024-01-15", "2024-01-16"]),
    })

    schema_v1 = pa.schema([
        pa.field("order_id",    pa.string()),
        pa.field("customer_id", pa.string()),
        pa.field("amount",      pa.float64()),
        pa.field("order_date",  pa.date32()),
    ])

    table = pa.Table.from_pandas(df_v1, schema=schema_v1)

    buf = io.BytesIO()
    pq.write_table(table, buf, compression="snappy")
    buf.seek(0)

    s3.put_object(
        Bucket=S3_BUCKET,
        Key="schema-demo/year=2024/month=01/v1_orders.parquet",
        Body=buf.getvalue(),
    )
    print(f"  v1 schema: {[f.name for f in schema_v1]}")


def write_v2_schema():
    """Write data with evolved schema (v2) — adds new nullable columns."""
    print("Writing v2 schema data (new columns added)...")

    df_v2 = pd.DataFrame({
        "order_id":    ["ORD-004", "ORD-005"],
        "customer_id": ["C4", "C5"],
        "amount":      [39.99, 59.99],
        "order_date":  pd.to_datetime(["2024-01-17", "2024-01-17"]),
        # New columns — nullable so v1 readers still work
        "product":     ["Widget A", "Widget B"],
        "discount_pct": [0.0, 10.0],
    })

    schema_v2 = pa.schema([
        pa.field("order_id",     pa.string()),
        pa.field("customer_id",  pa.string()),
        pa.field("amount",       pa.float64()),
        pa.field("order_date",   pa.date32()),
        pa.field("product",      pa.string()),      # NEW — nullable
        pa.field("discount_pct", pa.float64()),     # NEW — nullable
    ])

    table = pa.Table.from_pandas(df_v2, schema=schema_v2)

    buf = io.BytesIO()
    pq.write_table(table, buf, compression="snappy")
    buf.seek(0)

    s3.put_object(
        Bucket=S3_BUCKET,
        Key="schema-demo/year=2024/month=01/v2_orders.parquet",
        Body=buf.getvalue(),
    )
    print(f"  v2 schema: {[f.name for f in schema_v2]}")


def read_merged_schema():
    """Read both v1 and v2 files — Parquet merges schemas automatically."""
    print("\nReading merged schema (v1 + v2 files)...")

    import s3fs
    fs = s3fs.S3FileSystem()

    dataset = pq.ParquetDataset(
        f"{S3_BUCKET}/schema-demo/year=2024/month=01/",
        filesystem=fs,
        schema=None,   # auto-merge schemas
    )

    df = dataset.read_pandas().to_pandas()
    print(f"  Merged columns: {list(df.columns)}")
    print(f"  Total rows: {len(df)}")
    print(f"  v1 rows have NaN for new columns:")
    print(df[["order_id", "product", "discount_pct"]].to_string())


def demonstrate_partition_pruning():
    """Show how partition pruning speeds up Athena queries."""
    print("\n=== Partition Pruning Demo ===")
    print("""
Without partitioning:
  SELECT * FROM orders WHERE order_date = '2024-01-15'
  → Scans ALL data (e.g. 1 TB)
  → Cost: $5.00

With year/month/day partitioning:
  SELECT * FROM orders WHERE year=2024 AND month=01 AND day=15
  → Scans only that day's partition (e.g. 100 MB)
  → Cost: $0.0005
  → 10,000x cheaper!

Partition strategy for orders:
  s3://bucket/orders/year=YYYY/month=MM/day=DD/
  
  Good for: daily reports, date-range queries
  Bad for: queries that don't filter by date
    """)


if __name__ == "__main__":
    write_v1_schema()
    write_v2_schema()
    read_merged_schema()
    demonstrate_partition_pruning()
    print("\nDone! Check S3 for the Parquet files.")
