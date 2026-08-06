"""
upload_sample_data.py — Generate and upload partitioned sample data to S3 data lake

Usage:
    python upload_sample_data.py --bucket handson-data-lake-123456789012
    python upload_sample_data.py --bucket handson-data-lake-123456789012 --rows 1000

What it does:
    1. Generates realistic e-commerce orders data
    2. Uploads CSV files partitioned by year/month/day to the raw/ zone
    3. Converts to Parquet and uploads to processed/ zone
    4. Prints a summary of uploaded files
"""

import argparse
import csv
import io
import json
import os
import random
import tempfile
from datetime import datetime, timedelta

import boto3


# ── Sample data generators ────────────────────────────────────────────────────

PRODUCTS = [
    ("Widget A", 29.99),
    ("Widget B", 49.99),
    ("Widget C", 19.99),
    ("Gadget Pro", 99.99),
    ("Gadget Lite", 59.99),
]

STATUSES = ["completed", "completed", "completed", "pending", "cancelled"]


def generate_orders(num_rows: int = 100, start_date: str = "2024-01-01") -> list[dict]:
    """Generate fake e-commerce orders."""
    orders = []
    base_date = datetime.strptime(start_date, "%Y-%m-%d")

    for i in range(1, num_rows + 1):
        product_name, base_price = random.choice(PRODUCTS)
        # Add some price variation
        amount = round(base_price * random.uniform(0.95, 1.05), 2)
        order_date = base_date + timedelta(days=random.randint(0, 30))

        orders.append({
            "order_id": f"ORD-{i:05d}",
            "customer_id": f"CUST-{random.randint(101, 200):03d}",
            "product_name": product_name,
            "amount": amount,
            "order_date": order_date.strftime("%Y-%m-%d"),
            "status": random.choice(STATUSES),
            "year": order_date.year,
            "month": f"{order_date.month:02d}",
            "day": f"{order_date.day:02d}",
        })

    return orders


# ── S3 upload helpers ─────────────────────────────────────────────────────────

def upload_partitioned_csv(s3_client, orders: list[dict], bucket: str) -> list[str]:
    """Group orders by partition key and upload one CSV per partition."""
    # Group by year/month/day
    partitions: dict[tuple, list[dict]] = {}
    for order in orders:
        key = (order["year"], order["month"], order["day"])
        partitions.setdefault(key, []).append(order)

    uploaded = []
    for (year, month, day), partition_orders in partitions.items():
        # Build CSV content
        fieldnames = ["order_id", "customer_id", "product_name", "amount",
                      "order_date", "status"]
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fieldnames,
                                extrasaction="ignore")
        writer.writeheader()
        writer.writerows(partition_orders)

        s3_key = f"raw/orders/year={year}/month={month}/day={day}/orders.csv"
        s3_client.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=buf.getvalue().encode("utf-8"),
            ContentType="text/csv",
        )
        uploaded.append(s3_key)
        print(f"  ✅ Uploaded {len(partition_orders):3d} rows → s3://{bucket}/{s3_key}")

    return uploaded


def upload_parquet(s3_client, orders: list[dict], bucket: str) -> list[str]:
    """Convert orders to Parquet (monthly partitions) and upload to processed/ zone."""
    try:
        import pandas as pd
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError:
        print("  ⚠️  pandas/pyarrow not installed. Skipping Parquet upload.")
        print("     Run: pip install pandas pyarrow")
        return []

    df = pd.DataFrame(orders)
    uploaded = []

    for (year, month), group in df.groupby(["year", "month"]):
        # Drop partition columns from the file itself (they're in the path)
        cols_to_write = [c for c in group.columns
                         if c not in ("year", "month", "day")]
        table = pa.Table.from_pandas(group[cols_to_write])

        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as f:
            pq.write_table(table, f.name, compression="snappy")
            f.flush()

            s3_key = f"processed/orders/year={year}/month={month}/orders.parquet"
            s3_client.upload_file(f.name, bucket, s3_key)
            uploaded.append(s3_key)

            size_kb = os.path.getsize(f.name) / 1024
            print(f"  ✅ Uploaded {len(group):3d} rows ({size_kb:.1f} KB Parquet) "
                  f"→ s3://{bucket}/{s3_key}")

        os.unlink(f.name)

    return uploaded


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Upload sample data to S3 data lake"
    )
    parser.add_argument("--bucket",     required=True, help="S3 bucket name")
    parser.add_argument("--rows",       type=int, default=100, help="Number of orders to generate")
    parser.add_argument("--region",     default="us-east-1")
    parser.add_argument("--profile",    default=None, help="AWS CLI profile")
    parser.add_argument("--start-date", default="2024-01-01", help="Start date YYYY-MM-DD")
    args = parser.parse_args()

    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    s3 = session.client("s3")

    print(f"\n{'='*60}")
    print(f"  Data Lake Sample Upload")
    print(f"  Bucket : {args.bucket}")
    print(f"  Rows   : {args.rows}")
    print(f"{'='*60}\n")

    # Generate data
    print("Generating sample orders...")
    orders = generate_orders(num_rows=args.rows, start_date=args.start_date)
    print(f"Generated {len(orders)} orders\n")

    # Upload CSV to raw zone
    print("Uploading CSV to raw/ zone (partitioned by year/month/day):")
    csv_keys = upload_partitioned_csv(s3, orders, args.bucket)

    # Upload Parquet to processed zone
    print("\nUploading Parquet to processed/ zone (partitioned by year/month):")
    parquet_keys = upload_parquet(s3, orders, args.bucket)

    # Summary
    print(f"\n{'='*60}")
    print(f"  Summary")
    print(f"{'='*60}")
    print(f"  CSV files uploaded:     {len(csv_keys)}")
    print(f"  Parquet files uploaded: {len(parquet_keys)}")
    print(f"\n  Next steps:")
    print(f"  1. Run the Glue crawler to discover schema")
    print(f"     aws glue start-crawler --name handson-raw-crawler")
    print(f"  2. Query with Athena:")
    print(f"     SELECT COUNT(*) FROM orders;")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
