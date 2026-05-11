"""
etl_job.py — AWS Glue ETL job
Transforms raw order data from CSV to partitioned Parquet.

Run with:
  aws glue start-job-run --job-name handson-etl-job
"""

import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, IntegerType

# ─── Initialize Glue context ──────────────────────────────────────────────────

args = getResolvedOptions(sys.argv, [
    "JOB_NAME",
    "source_bucket",
    "target_bucket",
    "database_name",
])

sc          = SparkContext()
glueContext = GlueContext(sc)
spark       = glueContext.spark_session
job         = Job(glueContext)
job.init(args["JOB_NAME"], args)

SOURCE_BUCKET = args["source_bucket"]
TARGET_BUCKET = args["target_bucket"]
DATABASE      = args["database_name"]

# ─── Extract: Read raw data from S3 ──────────────────────────────────────────

print("Reading raw orders data...")

# Use DynamicFrame for schema flexibility
raw_dyf = glueContext.create_dynamic_frame.from_options(
    connection_type="s3",
    connection_options={
        "paths": [f"s3://{SOURCE_BUCKET}/raw/orders/"],
        "recurse": True,
    },
    format="csv",
    format_options={"withHeader": True, "separator": ","},
    transformation_ctx="raw_orders",
)

print(f"Raw record count: {raw_dyf.count()}")
raw_dyf.printSchema()

# Convert to Spark DataFrame for richer transformations
df = raw_dyf.toDF()

# ─── Transform: Clean and enrich ─────────────────────────────────────────────

print("Transforming data...")

df_clean = (
    df
    # Drop rows with null order_id or amount
    .dropna(subset=["order_id", "amount"])

    # Fix data types
    .withColumn("amount", F.col("amount").cast(DoubleType()))
    .withColumn("order_date", F.to_date("order_date", "yyyy-MM-dd"))

    # Add derived columns
    .withColumn("year",  F.year("order_date"))
    .withColumn("month", F.month("order_date"))
    .withColumn("day",   F.dayofmonth("order_date"))

    # Standardize text
    .withColumn("product", F.upper(F.trim("product")))
    .withColumn("customer_id", F.trim("customer_id"))

    # Add processing metadata
    .withColumn("processed_at", F.current_timestamp())
    .withColumn("etl_job", F.lit(args["JOB_NAME"]))

    # Remove duplicates
    .dropDuplicates(["order_id"])
)

print(f"Clean record count: {df_clean.count()}")

# ─── Aggregate: Daily order summaries ────────────────────────────────────────

df_daily = (
    df_clean
    .groupBy("year", "month", "day", "product")
    .agg(
        F.count("order_id").alias("order_count"),
        F.sum("amount").alias("total_revenue"),
        F.avg("amount").alias("avg_order_value"),
        F.countDistinct("customer_id").alias("unique_customers"),
    )
    .withColumn("total_revenue", F.round("total_revenue", 2))
    .withColumn("avg_order_value", F.round("avg_order_value", 2))
)

# ─── Load: Write to S3 as Parquet ─────────────────────────────────────────────

print("Writing processed data to S3...")

# Write individual orders (partitioned by year/month)
(
    df_clean
    .write
    .mode("overwrite")
    .partitionBy("year", "month")
    .parquet(f"s3://{TARGET_BUCKET}/processed/orders/")
)

# Write daily aggregates
(
    df_daily
    .write
    .mode("overwrite")
    .partitionBy("year", "month")
    .parquet(f"s3://{TARGET_BUCKET}/processed/orders_daily/")
)

print("ETL job complete!")
print(f"  Orders written to: s3://{TARGET_BUCKET}/processed/orders/")
print(f"  Daily aggregates:  s3://{TARGET_BUCKET}/processed/orders_daily/")

job.commit()
