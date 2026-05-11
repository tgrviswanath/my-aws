"""
validate_orders.py — Data quality validation using Great Expectations.
Run after each ETL job to validate the output data.
"""

import json
import os
import sys
from datetime import datetime

import boto3
import pandas as pd
import great_expectations as gx
from great_expectations.core.batch import RuntimeBatchRequest

S3_BUCKET   = os.environ.get("DATA_LAKE_BUCKET", "handson-data-lake")
REPORT_PATH = f"s3://{S3_BUCKET}/data-quality/reports/"


def load_data_from_s3(bucket: str, prefix: str) -> pd.DataFrame:
    """Load Parquet files from S3 into a DataFrame."""
    import pyarrow.parquet as pq
    import s3fs

    fs = s3fs.S3FileSystem()
    dataset = pq.ParquetDataset(f"{bucket}/{prefix}", filesystem=fs)
    return dataset.read_pandas().to_pandas()


def validate_orders(df: pd.DataFrame) -> dict:
    """Run Great Expectations suite on orders DataFrame."""

    context = gx.get_context()

    # Create a datasource
    datasource = context.sources.add_pandas("orders_datasource")
    asset = datasource.add_dataframe_asset("orders")
    batch_request = asset.build_batch_request(dataframe=df)

    # Define expectations
    suite_name = "orders_suite"
    suite = context.add_or_update_expectation_suite(suite_name)

    validator = context.get_validator(
        batch_request=batch_request,
        expectation_suite_name=suite_name,
    )

    # ─── Completeness checks ──────────────────────────────────────────────────
    validator.expect_table_row_count_to_be_between(min_value=1)
    validator.expect_column_values_to_not_be_null("order_id")
    validator.expect_column_values_to_not_be_null("customer_id")
    validator.expect_column_values_to_not_be_null("amount")
    validator.expect_column_values_to_not_be_null("order_date")

    # ─── Uniqueness checks ────────────────────────────────────────────────────
    validator.expect_column_values_to_be_unique("order_id")

    # ─── Validity checks ──────────────────────────────────────────────────────
    validator.expect_column_values_to_be_between(
        "amount", min_value=0.01, max_value=10000.0
    )
    validator.expect_column_values_to_be_in_set(
        "product",
        value_set=["Widget A", "Widget B", "Widget C", "Gadget X", "Gadget Y"],
        mostly=0.99,   # allow 1% unknown products
    )
    validator.expect_column_values_to_match_strftime_format(
        "order_date", strftime_format="%Y-%m-%d"
    )

    # ─── Statistical checks ───────────────────────────────────────────────────
    validator.expect_column_mean_to_be_between(
        "amount", min_value=10.0, max_value=200.0
    )

    # Run validation
    results = validator.validate()

    # Summary
    passed = results["statistics"]["successful_expectations"]
    total  = results["statistics"]["evaluated_expectations"]
    success = results["success"]

    print(f"\n{'='*50}")
    print(f"Data Quality Report — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")
    print(f"Status:  {'✅ PASSED' if success else '❌ FAILED'}")
    print(f"Checks:  {passed}/{total} passed")
    print(f"Rows:    {len(df):,}")

    if not success:
        print("\nFailed checks:")
        for result in results["results"]:
            if not result["success"]:
                print(f"  ❌ {result['expectation_config']['expectation_type']}: "
                      f"{result['expectation_config']['kwargs']}")

    return {
        "success": success,
        "passed": passed,
        "total": total,
        "row_count": len(df),
        "timestamp": datetime.now().isoformat(),
    }


def main():
    print("Loading orders data from S3...")
    df = load_data_from_s3(S3_BUCKET, "processed/orders/")
    print(f"Loaded {len(df):,} rows")

    results = validate_orders(df)

    # Exit with error code if validation failed (for CI/CD pipelines)
    if not results["success"]:
        print("\n❌ Data quality validation FAILED — pipeline should not proceed")
        sys.exit(1)
    else:
        print("\n✅ Data quality validation PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
