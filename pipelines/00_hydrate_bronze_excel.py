# Databricks notebook source
# MAGIC %md
# MAGIC # COMPASS — Bronze Load: Excel (workspace, batch, idempotent)
# MAGIC
# MAGIC Loads the **4 Excel-sourced fact bronze tables** in
# MAGIC `classic_stable_1zia5t_kp_catalog.compass_bronze`:
# MAGIC
# MAGIC | Source                                              | Bronze target          |
# MAGIC |-----------------------------------------------------|------------------------|
# MAGIC | `compass-source.xlsx` sheet `Allocations`           | `allocation_csv`       |
# MAGIC | `compass-source.xlsx` sheet `ERP_Sales_Orders`      | `erp_sales_order`      |
# MAGIC | `compass-source.xlsx` sheet `Event_Registrations`   | `event_registration`   |
# MAGIC | `compass-source.xlsx` sheet `Portal_Claims`         | `portal_claims`        |
# MAGIC
# MAGIC **Job entry point.** Wired as task `hydrate_bronze_excel` in the
# MAGIC `compass-bronze-load` job. Re-runnable —
# MAGIC `.mode("overwrite").option("overwriteSchema", "false")` replaces contents
# MAGIC without duplication or schema drift.
# MAGIC
# MAGIC Reference/master tables (parquet seeds) are loaded by the sibling task
# MAGIC `hydrate_bronze_parquet` (notebook `00_hydrate_bronze_parquet.py`).
# MAGIC
# MAGIC ## Prerequisites
# MAGIC - **DBR 17.1+** (native Excel reader).
# MAGIC - Workbook at `/Volumes/.../compass_bronze/raw/compass-source/compass-source.xlsx`.
# MAGIC - The 4 target bronze tables exist (DDL applied).
# MAGIC
# MAGIC ## Production framing
# MAGIC In a real Steelcase build these four feeds arrive via Lakeflow Connect
# MAGIC (SFDC/SAP) and Auto Loader (portal/allocations/events). The single-workbook
# MAGIC consolidation is a deliberate demo substitution — see `demo-design.md §5.D`.

# COMMAND ----------

from pyspark.sql.functions import col, current_timestamp, lit
from pyspark.sql.types import StringType

CATALOG = "classic_stable_1zia5t_kp_catalog"
SCHEMA = "compass_bronze"
RAW_VOLUME = f"/Volumes/{CATALOG}/{SCHEMA}/raw"
WORKBOOK_PATH = f"{RAW_VOLUME}/compass-source/compass-source.xlsx"

EXCEL_SHEETS = {
    "allocation_csv":     "Allocations",
    "erp_sales_order":    "ERP_Sales_Orders",
    "event_registration": "Event_Registrations",
    "portal_claims":      "Portal_Claims",
}


def _read_excel_sheet(sheet_name: str):
    return (
        spark.read.format("excel")
             .option("dataAddress", sheet_name)
             .option("headerRows", 1)
             .load(WORKBOOK_PATH)
             .withColumn("_ingest_ts", current_timestamp())
             .withColumn("_source_file", col("_metadata.file_path"))
    )


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
for t in EXCEL_SHEETS:
    fqn = f"{CATALOG}.{SCHEMA}.{t}"
    print(f"  {fqn}: {spark.table(fqn).count():>10,} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Excel sheets → fact-source bronze tables

# COMMAND ----------

_overwrite(_read_excel_sheet("Allocations"),         "allocation_csv")
_overwrite(_read_excel_sheet("ERP_Sales_Orders"),    "erp_sales_order")
_overwrite(_read_excel_sheet("Event_Registrations"), "event_registration")
# portal_claims: native Excel reader drops the original JSON payload; add a
# NULL raw_payload so the bronze schema matches §5.A's production design.
_overwrite(
    _read_excel_sheet("Portal_Claims").withColumn("raw_payload", lit(None).cast(StringType())),
    "portal_claims",
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("After load:")
for t in EXCEL_SHEETS:
    fqn = f"{CATALOG}.{SCHEMA}.{t}"
    print(f"  {fqn:<60} {spark.table(fqn).count():>10,}")

print("\nExpected (Phase 1.5 baseline, as-of 2026-10-13):")
print("  allocation_csv          3,042")
print("  erp_sales_order       625,078")
print("  event_registration      2,546")
print("  portal_claims          10,154")
