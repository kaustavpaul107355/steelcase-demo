# Databricks notebook source
# MAGIC %md
# MAGIC # COMPASS — Bronze Landing (Phase 1.5)
# MAGIC
# MAGIC Hydrates four `bronze.*` raw tables from a **single source workbook** —
# MAGIC `compass-source.xlsx` — using the native Databricks Excel reader
# MAGIC (DBR 17.1+) via Auto Loader. Each sheet maps 1:1 to one bronze table.
# MAGIC
# MAGIC | Bronze target              | Source sheet           |
# MAGIC |---------------------------|------------------------|
# MAGIC | `bronze.allocation_csv`    | `Allocations`          |
# MAGIC | `bronze.erp_sales_order`   | `ERP_Sales_Orders`     |
# MAGIC | `bronze.event_registration`| `Event_Registrations`  |
# MAGIC | `bronze.portal_claims`     | `Portal_Claims`        |
# MAGIC
# MAGIC ### Production framing
# MAGIC In a real Steelcase build these four feeds arrive via different mechanisms
# MAGIC (Salesforce/SAP via **Lakeflow Connect**, portal exports + allocation CSVs
# MAGIC + event registrations via **Auto Loader** — see `demo-design.md §5.A`).
# MAGIC For the demo we collapse them into one workbook to showcase the native
# MAGIC multi-sheet Excel reader: no JAR, no Python lib, schema-evolved-off,
# MAGIC `dataAddress` selects the sheet. The bronze table names + DDL are
# MAGIC unchanged so silver/gold downstream are untouched.
# MAGIC
# MAGIC ### Requirements
# MAGIC - DBR 17.1+ (native Excel reader)
# MAGIC - Workbook dropped into `/Volumes/steelcase_demo/raw/compass-source/`

# COMMAND ----------

import dlt
from pyspark.sql.functions import current_timestamp, input_file_name, lit

VOLUME_BASE = "/Volumes/steelcase_demo/raw"
SOURCE_WORKBOOK_DIR = f"{VOLUME_BASE}/compass-source/"


def _excel_sheet(sheet_name: str, schema_dir: str):
    """Auto Loader reader pinned to one sheet of the source workbook."""
    return (
        spark.readStream.format("cloudFiles")
             .option("cloudFiles.format", "excel")
             .option("cloudFiles.schemaEvolutionMode", "none")
             .option("cloudFiles.schemaLocation", f"{VOLUME_BASE}/_schemas/{schema_dir}")
             .option("dataAddress", sheet_name)
             .option("headerRows", 1)
             .load(SOURCE_WORKBOOK_DIR)
             .withColumn("_ingest_ts", current_timestamp())
             .withColumn("_source_file", input_file_name())
             .withColumn("_source_sheet", lit(sheet_name))
    )


# ---------------------------------------------------------------------
# Bronze tables — one per sheet
# ---------------------------------------------------------------------
@dlt.table(
    name="bronze_allocation_csv",
    comment="Per-FY allocation roster — Phase 1.5 source: Allocations sheet of compass-source.xlsx.",
)
def bronze_allocation_csv():
    return _excel_sheet("Allocations", "allocation_csv")


@dlt.table(
    name="bronze_erp_sales_order",
    comment="Sell-through order lines — Phase 1.5 source: ERP_Sales_Orders sheet of compass-source.xlsx.",
)
def bronze_erp_sales_order():
    return _excel_sheet("ERP_Sales_Orders", "erp_sales_order")


@dlt.table(
    name="bronze_event_registration",
    comment="Marketing event registrations — Phase 1.5 source: Event_Registrations sheet of compass-source.xlsx.",
)
def bronze_event_registration():
    return _excel_sheet("Event_Registrations", "event_registration")


@dlt.table(
    name="bronze_portal_claims",
    comment="Co-op portal claim records — Phase 1.5 source: Portal_Claims sheet of compass-source.xlsx.",
)
def bronze_portal_claims():
    return _excel_sheet("Portal_Claims", "portal_claims")
