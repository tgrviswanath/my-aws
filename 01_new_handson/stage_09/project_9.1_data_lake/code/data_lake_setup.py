"""
data_lake_setup.py — Set up a data lake: S3 zones, Glue catalog, Lake Formation.

Usage:
    python data_lake_setup.py --bucket my-data-lake-bucket
    python data_lake_setup.py --bucket my-data-lake-bucket --region us-east-1

What this script does:
    1. Creates S3 folder structure: raw/, processed/, curated/, archive/
    2. Creates a Glue database for each zone
    3. Registers S3 locations with AWS Lake Formation
    4. Creates a sample Glue table (orders) in the processed zone
    5. Prints a data lake structure summary

Data lake zones:
    raw/        — Landing zone for raw, unprocessed data (as-is from source)
    processed/  — Cleaned and transformed data (Parquet format)
    curated/    — Business-ready, aggregated data for analytics
    archive/    — Historical data moved from raw after processing

Prerequisites:
    pip install boto3
    AWS credentials with S3, Glue, and Lake Formation permissions
    Lake Formation must be set up in the account (first-time setup may require console)
"""

import argparse
import json

import boto3
from botocore.exceptions import ClientError


# ── AWS clients ───────────────────────────────────────────────────────────────
s3 = boto3.client("s3")
glue = boto3.client("glue")
lakeformation = boto3.client("lakeformation")
sts = boto3.client("sts")


# ── Zone definitions ──────────────────────────────────────────────────────────

# Each zone has: S3 prefix, Glue database name, description
DATA_LAKE_ZONES = [
    {
        "name":        "raw",
        "prefix":      "raw/",
        "database":    "dl_raw",
        "description": "Raw landing zone — unprocessed data as received from sources",
    },
    {
        "name":        "processed",
        "prefix":      "processed/",
        "database":    "dl_processed",
        "description": "Processed zone — cleaned, validated, Parquet-converted data",
    },
    {
        "name":        "curated",
        "prefix":      "curated/",
        "database":    "dl_curated",
        "description": "Curated zone — business-ready aggregated data for analytics",
    },
    {
        "name":        "archive",
        "prefix":      "archive/",
        "database":    "dl_archive",
        "description": "Archive zone — historical raw data after processing",
    },
]

# Sub-folders within each zone (by data domain)
DOMAIN_SUBFOLDERS = ["orders/", "customers/", "products/", "inventory/", "events/"]


# ── Step 1: S3 folder structure ───────────────────────────────────────────────

def create_s3_structure(bucket: str) -> None:
    """
    Create the S3 folder structure for all data lake zones and domains.

    S3 doesn't have real folders — we create zero-byte objects with trailing
    slashes to represent folder structure in the console.

    Args:
        bucket: S3 bucket name
    """
    print("\n  Creating S3 folder structure...")

    # Ensure the bucket exists (create if not)
    try:
        s3.head_bucket(Bucket=bucket)
        print(f"  ✓ Using existing bucket: {bucket}")
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            region = boto3.session.Session().region_name or "us-east-1"
            create_kwargs = {"Bucket": bucket}
            # us-east-1 does not accept a LocationConstraint
            if region != "us-east-1":
                create_kwargs["CreateBucketConfiguration"] = {"LocationConstraint": region}
            s3.create_bucket(**create_kwargs)
            print(f"  ✓ Created bucket: {bucket}")

            # Block all public access on the new bucket
            s3.put_public_access_block(
                Bucket=bucket,
                PublicAccessBlockConfiguration={
                    "BlockPublicAcls": True,
                    "IgnorePublicAcls": True,
                    "BlockPublicPolicy": True,
                    "RestrictPublicBuckets": True,
                },
            )
            print(f"  ✓ Public access blocked on bucket")
        else:
            raise

    # Enable versioning on the bucket (important for data lake integrity)
    s3.put_bucket_versioning(
        Bucket=bucket,
        VersioningConfiguration={"Status": "Enabled"},
    )
    print(f"  ✓ Versioning enabled")

    # Create zone folders and domain sub-folders
    created_keys = []
    for zone in DATA_LAKE_ZONES:
        # Create zone root folder
        zone_key = zone["prefix"]
        s3.put_object(Bucket=bucket, Key=zone_key, Body=b"")
        created_keys.append(zone_key)

        # Create domain sub-folders within each zone
        for domain in DOMAIN_SUBFOLDERS:
            domain_key = zone["prefix"] + domain
            s3.put_object(Bucket=bucket, Key=domain_key, Body=b"")
            created_keys.append(domain_key)

    print(f"  ✓ Created {len(created_keys)} S3 prefixes across {len(DATA_LAKE_ZONES)} zones")


# ── Step 2: Glue databases ────────────────────────────────────────────────────

def create_glue_databases(bucket: str) -> None:
    """
    Create a Glue Data Catalog database for each data lake zone.

    Args:
        bucket: S3 bucket name (used as the database location)
    """
    print("\n  Creating Glue databases...")

    for zone in DATA_LAKE_ZONES:
        db_name = zone["database"]
        location = f"s3://{bucket}/{zone['prefix']}"

        try:
            glue.create_database(
                DatabaseInput={
                    "Name": db_name,
                    "Description": zone["description"],
                    "LocationUri": location,
                    "Parameters": {
                        "zone": zone["name"],
                        "data_lake_bucket": bucket,
                    },
                }
            )
            print(f"  ✓ Created Glue database: {db_name}  →  {location}")
        except ClientError as e:
            if e.response["Error"]["Code"] == "AlreadyExistsException":
                print(f"  ℹ Glue database already exists: {db_name}")
            else:
                raise


# ── Step 3: Lake Formation registration ──────────────────────────────────────

def register_lake_formation_locations(bucket: str) -> None:
    """
    Register S3 locations with AWS Lake Formation.

    Lake Formation manages fine-grained access control on top of S3 + Glue.
    Each zone is registered as a separate data lake location.

    Args:
        bucket: S3 bucket name
    """
    print("\n  Registering Lake Formation locations...")

    # Get the current IAM role ARN (used as the Lake Formation service role)
    caller_identity = sts.get_caller_identity()
    account_id = caller_identity["Account"]

    # Use the default Lake Formation service role
    # In production, create a dedicated role with appropriate permissions
    role_arn = f"arn:aws:iam::{account_id}:role/AWSGlueServiceRole"

    for zone in DATA_LAKE_ZONES:
        location_uri = f"s3://{bucket}/{zone['prefix']}"
        try:
            lakeformation.register_resource(
                ResourceArn=f"arn:aws:s3:::{bucket}/{zone['prefix']}",
                UseServiceLinkedRole=True,  # Use the Lake Formation service-linked role
            )
            print(f"  ✓ Registered: {location_uri}")
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "AlreadyExistsException":
                print(f"  ℹ Already registered: {location_uri}")
            elif error_code in ("AccessDeniedException", "EntityNotFoundException"):
                # Lake Formation may not be fully set up — log and continue
                print(f"  ⚠ Could not register {location_uri}: {error_code}")
                print(f"    Ensure Lake Formation is enabled and the service role exists")
            else:
                raise


# ── Step 4: Sample Glue table ─────────────────────────────────────────────────

def create_sample_orders_table(bucket: str) -> None:
    """
    Create a sample Glue table for orders data in the processed zone.

    This table represents a typical fact table in the processed zone,
    stored as Parquet files partitioned by year/month/day.

    Schema:
        order_id        STRING
        customer_id     STRING
        order_date      DATE
        product_id      STRING
        quantity        INT
        unit_price      DOUBLE
        total_amount    DOUBLE
        status          STRING
        region          STRING
        year            STRING  (partition key)
        month           STRING  (partition key)
        day             STRING  (partition key)

    Args:
        bucket: S3 bucket name
    """
    print("\n  Creating sample orders table...")

    table_location = f"s3://{bucket}/processed/orders/"

    try:
        glue.create_table(
            DatabaseName="dl_processed",
            TableInput={
                "Name": "orders",
                "Description": "Orders fact table — processed from raw source data",
                "StorageDescriptor": {
                    "Columns": [
                        {"Name": "order_id",     "Type": "string",  "Comment": "Unique order identifier"},
                        {"Name": "customer_id",  "Type": "string",  "Comment": "Customer identifier"},
                        {"Name": "order_date",   "Type": "date",    "Comment": "Date the order was placed"},
                        {"Name": "product_id",   "Type": "string",  "Comment": "Product identifier"},
                        {"Name": "quantity",     "Type": "int",     "Comment": "Number of units ordered"},
                        {"Name": "unit_price",   "Type": "double",  "Comment": "Price per unit in USD"},
                        {"Name": "total_amount", "Type": "double",  "Comment": "Total order value in USD"},
                        {"Name": "status",       "Type": "string",  "Comment": "Order status: pending/shipped/delivered/cancelled"},
                        {"Name": "region",       "Type": "string",  "Comment": "Fulfillment region"},
                    ],
                    "Location": table_location,
                    "InputFormat":  "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat",
                    "OutputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat",
                    "SerdeInfo": {
                        "SerializationLibrary": "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe",
                        "Parameters": {"serialization.format": "1"},
                    },
                    "Compressed": True,
                },
                # Partition keys allow Athena/Glue to prune data efficiently
                "PartitionKeys": [
                    {"Name": "year",  "Type": "string", "Comment": "Partition year  (e.g. 2024)"},
                    {"Name": "month", "Type": "string", "Comment": "Partition month (e.g. 01)"},
                    {"Name": "day",   "Type": "string", "Comment": "Partition day   (e.g. 15)"},
                ],
                "TableType": "EXTERNAL_TABLE",
                "Parameters": {
                    "classification":        "parquet",
                    "compressionType":       "snappy",
                    "typeOfData":            "file",
                    "EXTERNAL":              "TRUE",
                    "parquet.compression":   "SNAPPY",
                },
            },
        )
        print(f"  ✓ Created table: dl_processed.orders  →  {table_location}")
    except ClientError as e:
        if e.response["Error"]["Code"] == "AlreadyExistsException":
            print(f"  ℹ Table already exists: dl_processed.orders")
        else:
            raise


# ── Step 5: Summary ───────────────────────────────────────────────────────────

def print_summary(bucket: str) -> None:
    """
    Print a summary of the data lake structure.

    Args:
        bucket: S3 bucket name
    """
    region = boto3.session.Session().region_name or "us-east-1"

    print("\n" + "=" * 70)
    print("  DATA LAKE STRUCTURE SUMMARY")
    print("=" * 70)
    print(f"\n  S3 Bucket: s3://{bucket}/")
    print()

    for zone in DATA_LAKE_ZONES:
        print(f"  ├── {zone['prefix']:<15}  [{zone['database']}]  {zone['description']}")
        for domain in DOMAIN_SUBFOLDERS:
            print(f"  │   └── {domain}")

    print()
    print("  Glue Databases:")
    for zone in DATA_LAKE_ZONES:
        print(f"    • {zone['database']:<20}  s3://{bucket}/{zone['prefix']}")

    print()
    print("  Sample Tables:")
    print(f"    • dl_processed.orders  (Parquet, partitioned by year/month/day)")

    print()
    print("  Console Links:")
    print(f"    S3:              https://s3.console.aws.amazon.com/s3/buckets/{bucket}")
    print(f"    Glue Catalog:    https://{region}.console.aws.amazon.com/glue/home#/catalog/databases")
    print(f"    Lake Formation:  https://{region}.console.aws.amazon.com/lakeformation/home")
    print(f"    Athena:          https://{region}.console.aws.amazon.com/athena/home")
    print()
    print("  Sample Athena Query:")
    print("    SELECT year, month, SUM(total_amount) AS revenue")
    print("    FROM dl_processed.orders")
    print("    WHERE year = '2024'")
    print("    GROUP BY year, month")
    print("    ORDER BY month;")
    print("=" * 70 + "\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Set up a data lake: S3 zones, Glue catalog, Lake Formation"
    )
    parser.add_argument(
        "--bucket", required=True,
        help="S3 bucket name for the data lake (will be created if it doesn't exist)"
    )
    parser.add_argument(
        "--region", default=None,
        help="AWS region (default: from AWS config/env)"
    )
    parser.add_argument(
        "--skip-lakeformation", action="store_true",
        help="Skip Lake Formation registration (use if LF is not set up)"
    )
    args = parser.parse_args()

    global s3, glue, lakeformation, sts
    if args.region:
        s3 = boto3.client("s3", region_name=args.region)
        glue = boto3.client("glue", region_name=args.region)
        lakeformation = boto3.client("lakeformation", region_name=args.region)
        sts = boto3.client("sts", region_name=args.region)

    print(f"\n=== Data Lake Setup ===")
    print(f"  Bucket: {args.bucket}")

    # Step 1 — S3 structure
    create_s3_structure(args.bucket)

    # Step 2 — Glue databases
    create_glue_databases(args.bucket)

    # Step 3 — Lake Formation (optional)
    if not args.skip_lakeformation:
        register_lake_formation_locations(args.bucket)
    else:
        print("\n  Skipping Lake Formation registration (--skip-lakeformation)")

    # Step 4 — Sample table
    create_sample_orders_table(args.bucket)

    # Step 5 — Summary
    print_summary(args.bucket)


if __name__ == "__main__":
    main()
