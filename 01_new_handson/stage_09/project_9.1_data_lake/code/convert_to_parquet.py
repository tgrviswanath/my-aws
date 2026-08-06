"""
convert_to_parquet.py — Convert CSV files to Parquet format and upload to S3

Why Parquet?
    CSV:     Row-based, uncompressed → Athena scans ENTIRE file for any query
    Parquet: Column-based, Snappy compressed → Athena only reads requested columns
    Result:  10x cheaper queries, 5x smaller file size, 3x faster query execution

Usage:
    # Convert a local CSV and upload to S3
    python convert_to_parquet.py \
        --input data/sample_orders.csv \
        --bucket handson-data-lake-123456789012 \
        --s3-prefix processed/orders/year=2024/month=01

    # Convert with explicit partitioning
    python convert_to_parquet.py \
        --input data/sample_orders.csv \
        --bucket handson-data-lake-123456789012 \
        --s3-prefix processed/orders \
        --partition-by year month

    # Just compare CSV vs Parquet size (no upload)
    python convert_to_parquet.py --input data/sample_orders.csv --compare-only

Prerequisites:
    pip install boto3 pandas pyarrow
"""

import argparse
import os
import tempfile
from pathlib import Path

import boto3


def convert_csv_to_parquet(
    csv_path: str,
    parquet_path: str,
    partition_cols: list[str] | None = None,
) -> dict:
    """
    Convert a CSV file to Parquet format.

    Args:
        csv_path:       Path to input CSV file
        parquet_path:   Path to write output Parquet file
        partition_cols: Column names to use as partition keys

    Returns:
        dict with csv_size_bytes, parquet_size_bytes, row_count, column_count,
        compression_ratio, columns
    """
    try:
        import pandas as pd
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError:
        raise ImportError(
            "Missing dependencies. Install with:\n"
            "  pip install pandas pyarrow"
        )

    # Read CSV
    print(f"  Reading: {csv_path}")
    df = pd.read_csv(csv_path)
    print(f"  Rows: {len(df):,}  |  Columns: {len(df.columns)}")
    print(f"  Columns: {list(df.columns)}")

    # Type inference — pandas auto-detects types from CSV
    # Parquet preserves these types; CSV treats everything as string
    print(f"\n  Data types detected:")
    for col, dtype in df.dtypes.items():
        print(f"    {col:<20} {str(dtype):<15}")

    # Convert to PyArrow table (intermediate representation)
    table = pa.Table.from_pandas(df, preserve_index=False)

    # Write Parquet with Snappy compression
    pq.write_table(
        table,
        parquet_path,
        compression="snappy",         # Best balance of speed and compression
        use_dictionary=True,          # Dictionary encoding for low-cardinality columns
        write_statistics=True,        # Min/max stats enable Athena predicate pushdown
        row_group_size=128 * 1024,    # 128 KB row groups (good for Athena)
    )

    # Size comparison
    csv_size = os.path.getsize(csv_path)
    parquet_size = os.path.getsize(parquet_path)
    compression_ratio = csv_size / parquet_size if parquet_size > 0 else 1

    return {
        "csv_size_bytes":      csv_size,
        "parquet_size_bytes":  parquet_size,
        "row_count":           len(df),
        "column_count":        len(df.columns),
        "compression_ratio":   compression_ratio,
        "columns":             list(df.columns),
        "schema":              str(table.schema),
    }


def upload_to_s3(
    local_path: str,
    bucket: str,
    s3_key: str,
    s3_client,
) -> str:
    """
    Upload a local file to S3 with correct ContentType for Parquet.

    Args:
        local_path: Local file path
        bucket:     S3 bucket name
        s3_key:     S3 object key (path within bucket)
        s3_client:  boto3 S3 client

    Returns:
        Full S3 URI of the uploaded file
    """
    s3_client.upload_file(
        local_path,
        bucket,
        s3_key,
        ExtraArgs={"ContentType": "application/octet-stream"},
    )
    return f"s3://{bucket}/{s3_key}"


def print_comparison(stats: dict, csv_path: str, parquet_path: str) -> None:
    """
    Print a side-by-side comparison of CSV vs Parquet.

    Args:
        stats:        Output from convert_csv_to_parquet()
        csv_path:     Path to original CSV
        parquet_path: Path to Parquet file
    """
    csv_kb     = stats["csv_size_bytes"] / 1024
    parquet_kb = stats["parquet_size_bytes"] / 1024
    ratio      = stats["compression_ratio"]

    # Athena cost comparison (at $5/TB scanned)
    csv_cost     = (stats["csv_size_bytes"] / (1024 ** 4)) * 5
    parquet_cost = (stats["parquet_size_bytes"] / (1024 ** 4)) * 5

    print(f"\n  {'='*55}")
    print(f"  FORMAT COMPARISON")
    print(f"  {'='*55}")
    print(f"  {'Metric':<30} {'CSV':>10} {'Parquet':>12}")
    print(f"  {'-'*55}")
    print(f"  {'File size':<30} {csv_kb:>8.1f} KB {parquet_kb:>8.1f} KB")
    print(f"  {'Rows':<30} {stats['row_count']:>10,} {stats['row_count']:>12,}")
    print(f"  {'Columns':<30} {stats['column_count']:>10} {stats['column_count']:>12}")
    print(f"  {'Compression ratio':<30} {'1x':>10} {ratio:>10.1f}x")
    print(f"  {'Athena scan cost (per query)':<30} ${csv_cost:.8f} ${parquet_cost:.8f}")
    print(f"  {'='*55}")
    print(f"\n  Parquet is {ratio:.1f}x smaller than CSV.")
    print(f"  For 1 TB of data: CSV query costs $5.00, Parquet costs ${5/ratio:.2f}")
    print(f"  Savings: {(1 - 1/ratio)*100:.0f}% on Athena query costs\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Convert CSV files to Parquet and upload to S3"
    )
    parser.add_argument("--input",        required=True, help="Input CSV file path")
    parser.add_argument("--bucket",       default=None, help="S3 bucket name (required unless --compare-only)")
    parser.add_argument("--s3-prefix",    default="processed", help="S3 key prefix (no trailing slash)")
    parser.add_argument("--partition-by", nargs="*", help="Column names to partition by (e.g. year month)")
    parser.add_argument("--compare-only", action="store_true", help="Only show CSV vs Parquet comparison, no S3 upload")
    parser.add_argument("--region",       default="us-east-1")
    parser.add_argument("--profile",      default=None)
    args = parser.parse_args()

    if not args.compare_only and not args.bucket:
        parser.error("--bucket is required unless --compare-only is set")

    input_path = args.input
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    filename_stem = Path(input_path).stem

    print(f"\n{'='*60}")
    print(f"  CSV → Parquet Converter")
    print(f"  Input: {input_path}")
    print(f"{'='*60}")

    # Convert to a temp Parquet file
    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
        tmp_parquet = tmp.name

    try:
        stats = convert_csv_to_parquet(
            csv_path=input_path,
            parquet_path=tmp_parquet,
            partition_cols=args.partition_by,
        )

        # Show comparison
        print_comparison(stats, input_path, tmp_parquet)

        if not args.compare_only:
            # Build S3 key
            s3_key = f"{args.s3_prefix}/{filename_stem}.parquet"

            print(f"  Uploading to S3...")
            session = boto3.Session(profile_name=args.profile, region_name=args.region)
            s3_client = session.client("s3")

            s3_uri = upload_to_s3(tmp_parquet, args.bucket, s3_key, s3_client)

            print(f"  ✅ Uploaded: {s3_uri}")
            print(f"\n  You can now query this file in Athena:")
            print(f"  SELECT * FROM processed_{filename_stem} LIMIT 10;")
            print(f"\n  Or create a table pointing to it:")
            print(f"  CREATE EXTERNAL TABLE processed_{filename_stem}")
            print(f"  STORED AS PARQUET")
            print(f"  LOCATION 's3://{args.bucket}/{args.s3_prefix}/';")

    finally:
        os.unlink(tmp_parquet)


if __name__ == "__main__":
    main()
