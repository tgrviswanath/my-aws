"""
spark_job.py — PySpark job for EMR.
Processes large order datasets with distributed computing.

Submit to EMR:
  aws emr add-steps \
    --cluster-id j-XXXXXXXXXX \
    --steps Type=Spark,Name="Order Analysis",ActionOnFailure=CONTINUE,\
            Args=[--deploy-mode,cluster,--master,yarn,\
                  s3://BUCKET/scripts/spark_job.py,\
                  --input,s3://BUCKET/raw/orders/,\
                  --output,s3://BUCKET/processed/spark/]
"""

import sys
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window

def main(input_path: str, output_path: str) -> None:
    spark = SparkSession.builder \
        .appName("OrderAnalysis") \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
        .getOrCreate()

    spark.sparkContext.setLogLevel("WARN")
    print(f"Spark version: {spark.version}")
    print(f"Reading from: {input_path}")

    # ─── Read data ────────────────────────────────────────────────────────────
    df = spark.read \
        .option("header", "true") \
        .option("inferSchema", "true") \
        .csv(input_path)

    print(f"Total records: {df.count()}")
    df.printSchema()

    # ─── Transform ────────────────────────────────────────────────────────────

    # Clean and enrich
    df_clean = df \
        .dropna(subset=["order_id", "amount"]) \
        .withColumn("order_date", F.to_date("order_date")) \
        .withColumn("year",  F.year("order_date")) \
        .withColumn("month", F.month("order_date")) \
        .withColumn("amount", F.col("amount").cast("double")) \
        .dropDuplicates(["order_id"])

    # Revenue by product and month
    df_product_monthly = df_clean \
        .groupBy("year", "month", "product") \
        .agg(
            F.count("order_id").alias("order_count"),
            F.sum("amount").alias("total_revenue"),
            F.avg("amount").alias("avg_order_value"),
            F.countDistinct("customer_id").alias("unique_customers"),
        ) \
        .withColumn("total_revenue", F.round("total_revenue", 2))

    # Customer lifetime value (CLV)
    df_clv = df_clean \
        .groupBy("customer_id") \
        .agg(
            F.count("order_id").alias("total_orders"),
            F.sum("amount").alias("lifetime_value"),
            F.min("order_date").alias("first_order"),
            F.max("order_date").alias("last_order"),
        ) \
        .withColumn("lifetime_value", F.round("lifetime_value", 2))

    # Running total per customer (window function)
    window = Window.partitionBy("customer_id").orderBy("order_date")
    df_running = df_clean \
        .withColumn("running_total", F.sum("amount").over(window))

    # ─── Write output ─────────────────────────────────────────────────────────

    df_product_monthly \
        .write.mode("overwrite") \
        .partitionBy("year", "month") \
        .parquet(f"{output_path}/product_monthly/")

    df_clv \
        .write.mode("overwrite") \
        .parquet(f"{output_path}/customer_clv/")

    print(f"Output written to: {output_path}")
    print(f"Product monthly records: {df_product_monthly.count()}")
    print(f"Customer CLV records: {df_clv.count()}")

    spark.stop()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",  required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    main(args.input, args.output)
