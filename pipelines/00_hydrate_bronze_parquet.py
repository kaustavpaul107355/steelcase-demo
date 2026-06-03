# Databricks notebook source
# MAGIC %md
# MAGIC # COMPASS — Bronze Load: Parquet seeds (workspace, batch, idempotent)
# MAGIC
# MAGIC Loads the **4 parquet-sourced reference/master bronze tables** in
# MAGIC `classic_stable_1zia5t_kp_catalog.compass_bronze`:
# MAGIC
# MAGIC | Source                            | Bronze target          |
# MAGIC |-----------------------------------|------------------------|
# MAGIC | `seed/dealer.parquet`             | `sfdc_account`         |
# MAGIC | `seed/program.parquet`            | `ref_program`          |
# MAGIC | `seed/activity_type.parquet`      | `ref_activity_type`    |
# MAGIC | `seed/region.parquet`             | `ref_region`           |
# MAGIC
# MAGIC **Job entry point.** Wired as task `hydrate_bronze_parquet` in the
# MAGIC `compass-bronze-load` job. Re-runnable —
# MAGIC `.mode("overwrite").option("overwriteSchema", "false")` replaces contents
# MAGIC without duplication or schema drift.
# MAGIC
# MAGIC Fact tables (Excel-sourced) are loaded by the sibling task
# MAGIC `hydrate_bronze_excel` (notebook `00_hydrate_bronze_excel.py`).
# MAGIC
# MAGIC ## Prerequisites
# MAGIC - Parquet seeds at `/Volumes/.../compass_bronze/raw/seed/`.
# MAGIC - The 4 target bronze tables exist (DDL applied).
# MAGIC
# MAGIC ## Production framing
# MAGIC In a real Steelcase build, these reference/master tables would arrive via:
# MAGIC - `sfdc_account` ← Lakeflow Connect — Salesforce (SCD-2 via CDC)
# MAGIC - `ref_program` / `ref_activity_type` / `ref_region` ← Auto Loader CSV
# MAGIC
# MAGIC See `demo-design.md §5.A`. For the demo, we hydrate them from the same
# MAGIC generator output as the silver dims so bronze is fully populated.

# COMMAND ----------

from pyspark.sql.functions import col, current_timestamp, lit
from pyspark.sql.types import StringType, BooleanType

CATALOG = "classic_stable_1zia5t_kp_catalog"
SCHEMA = "compass_bronze"
RAW_VOLUME = f"/Volumes/{CATALOG}/{SCHEMA}/raw"
SEED_DIR = f"{RAW_VOLUME}/seed"

REF_TABLES = ["sfdc_account", "ref_program", "ref_activity_type", "ref_region"]


def _coerce_to_target(df, table_fqn: str):
    """Cast each source column to the matching target table column's type."""
    target_schema = spark.table(table_fqn).schema
    src_cols = set(df.columns)
    for f in target_schema.fields:
        if f.name in src_cols:
            df = df.withColumn(f.name, col(f.name).cast(f.dataType))
    return df


def _overwrite(df, table: str):
    fqn = f"{CATALOG}.{SCHEMA}.{table}"
    df = _coerce_to_target(df, fqn).select(*spark.table(fqn).columns)
    df.write.mode("overwrite").option("overwriteSchema", "false").saveAsTable(fqn)
    print(f"  {fqn}: {spark.table(fqn).count():>10,} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Pre-flight: row counts before load

# COMMAND ----------

print("Before load:")
for t in REF_TABLES:
    fqn = f"{CATALOG}.{SCHEMA}.{t}"
    print(f"  {fqn}: {spark.table(fqn).count():>10,} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Parquet seeds → reference/master bronze tables
# MAGIC
# MAGIC Column renames match the bronze DDL exactly:
# MAGIC - `dealer.parquet` → SFDC-shaped columns; the generator's `dealer_id` lands in custom field `Dealer_External_Id__c`.
# MAGIC - `program.parquet` → `program_id` becomes `program_code`.
# MAGIC - `activity_type.parquet` → `activity_type_id` becomes `activity_code`.
# MAGIC - `region.parquet` → direct passthrough; `country_list` not present in seed (set NULL).

# COMMAND ----------

# bronze.sfdc_account ← dealer.parquet
dealer = spark.read.parquet(f"{SEED_DIR}/dealer.parquet")
sfdc = (dealer
    .select(
        col("salesforce_account_id").alias("Id"),
        col("dealer_name").alias("Name"),
        col("country").alias("BillingCountry"),
        lit(None).cast(StringType()).alias("BillingState"),
        col("tier").alias("Tier__c"),
        col("region_id").alias("Region__c"),
        col("sales_rep_id").alias("Sales_Rep__c"),
        col("dealer_id").alias("Dealer_External_Id__c"),
        lit(False).cast(BooleanType()).alias("IsDeleted"),
        current_timestamp().alias("LastModifiedDate"),
    )
    .withColumn("_ingest_ts", current_timestamp())
    .withColumn("_source_file", lit(f"{SEED_DIR}/dealer.parquet"))
)
_overwrite(sfdc, "sfdc_account")

# COMMAND ----------

# bronze.ref_program ← program.parquet
program = spark.read.parquet(f"{SEED_DIR}/program.parquet")
ref_program = (program
    .select(
        col("program_id").alias("program_code"),
        col("program_name"),
        col("fiscal_year"),
        col("allocation_method"),
        col("default_cofund_pct"),
        col("program_start"),
        col("program_end"),
    )
    .withColumn("_ingest_ts", current_timestamp())
)
_overwrite(ref_program, "ref_program")

# COMMAND ----------

# bronze.ref_activity_type ← activity_type.parquet
activity = spark.read.parquet(f"{SEED_DIR}/activity_type.parquet")
ref_activity = (activity
    .select(
        col("activity_type_id").alias("activity_code"),
        col("category"),
        col("activity_name"),
        col("default_cofund_pct"),
        col("requires_preapproval"),
        col("preapproval_threshold_usd"),
    )
    .withColumn("_ingest_ts", current_timestamp())
)
_overwrite(ref_activity, "ref_activity_type")

# COMMAND ----------

# bronze.ref_region ← region.parquet (country_list NULL — not in generator output)
region = spark.read.parquet(f"{SEED_DIR}/region.parquet")
ref_region = (region
    .select(
        col("region_id"),
        col("region"),
        col("sub_region"),
        col("default_currency"),
        lit(None).cast(StringType()).alias("country_list"),
    )
    .withColumn("_ingest_ts", current_timestamp())
)
_overwrite(ref_region, "ref_region")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("After load:")
for t in REF_TABLES:
    fqn = f"{CATALOG}.{SCHEMA}.{t}"
    print(f"  {fqn:<60} {spark.table(fqn).count():>10,}")

print("\nExpected (Phase 1.5 baseline, as-of 2026-10-13):")
print("  sfdc_account              843")
print("  ref_program                10")
print("  ref_activity_type          22")
print("  ref_region                  8")
