# Databricks notebook source
# MAGIC %md
# MAGIC # COMPASS — Silver Curation
# MAGIC
# MAGIC Cleans the Phase 1.5 bronze tables, applies quality rules, derives fiscal
# MAGIC year, and produces conformed silver tables matching `data/ddl/02-silver.sql`.
# MAGIC
# MAGIC ## Sources
# MAGIC
# MAGIC | Silver table              | Bronze source (this pipeline)        | Phase 1.5 origin              |
# MAGIC |---------------------------|--------------------------------------|-------------------------------|
# MAGIC | `silver.coop_claim`       | `bronze.portal_claims`               | `Portal_Claims` sheet         |
# MAGIC | `silver.coop_allocation`  | `bronze.allocation_csv`              | `Allocations` sheet           |
# MAGIC | `silver.sell_through_order` | `bronze.erp_sales_order`           | `ERP_Sales_Orders` sheet      |
# MAGIC | `silver.marketing_event`  | `bronze.event_registration`          | `Event_Registrations` sheet   |
# MAGIC | `silver.dealer`           | `/Volumes/.../reference/dealer.parquet`        | demo dim seed (see TODO)      |
# MAGIC | `silver.program`          | `/Volumes/.../reference/program.parquet`       | demo dim seed (see TODO)      |
# MAGIC | `silver.activity_type`    | `/Volumes/.../reference/activity_type.parquet` | demo dim seed (see TODO)      |
# MAGIC | `silver.region`           | `/Volumes/.../reference/region.parquet`        | demo dim seed (see TODO)      |
# MAGIC | `silver.fiscal_calendar`  | `/Volumes/.../reference/fiscal_calendar.parquet` | demo dim seed (see TODO)    |
# MAGIC
# MAGIC **Production framing (TODO):** `silver.dealer` would derive from
# MAGIC `bronze.sfdc_account` via SCD-2 merge (Lakeflow Connect — Salesforce);
# MAGIC `silver.program / activity_type / region` from `bronze.ref_*` (Auto Loader
# MAGIC CSV). Both paths are documented in `demo-design.md §5.A`. For the demo we
# MAGIC short-circuit by reading the generator's Parquet dimension files directly
# MAGIC from a UC volume — same data, fewer hops.

# COMMAND ----------

import dlt
from pyspark.sql.functions import col, lit, when, to_date

REFERENCE_BASE = "/Volumes/steelcase_demo/raw/reference"


def _fiscal_year_expr(date_col: str):
    """Steelcase fiscal year (Mar–Feb). Derived from a date column."""
    return (when(col(date_col) >= lit("2026-03-01"), lit("FY26"))
            .when(col(date_col) >= lit("2025-03-01"), lit("FY25"))
            .when(col(date_col) >= lit("2024-03-01"), lit("FY24"))
            .otherwise(lit("FY23")))


# ---------------------------------------------------------------------
# Fact silver — from Phase 1.5 bronze (Excel sheets)
# ---------------------------------------------------------------------
@dlt.table(name="silver_coop_claim",
           comment="Curated co-op claims with typed columns and derived fiscal_year.")
@dlt.expect_or_drop("claim_amount_positive", "requested_amount > 0")
@dlt.expect_or_drop("dealer_present", "dealer_external_id IS NOT NULL")
@dlt.expect_or_drop("status_valid",
    "status IN ('Draft','Submitted','Under_Review','Approved','Rejected','Paid','Expired')")
@dlt.expect_or_drop("paid_le_approved",
    "paid_amount IS NULL OR approved_amount IS NULL OR paid_amount <= approved_amount")
def silver_coop_claim():
    return (
        dlt.read_stream("bronze_portal_claims").select(
            col("claim_id"),
            col("dealer_external_id").alias("dealer_id"),
            col("program_code").alias("program_id"),
            col("activity_code").alias("activity_type_id"),
            col("preapproval_id"),
            to_date("submission_date").alias("submission_date"),
            col("requested_amount").cast("decimal(12,2)").alias("requested_amount_usd"),
            col("approved_amount").cast("decimal(12,2)").alias("approved_amount_usd"),
            col("paid_amount").cast("decimal(12,2)").alias("paid_amount_usd"),
            col("status"),
            col("brand_compliance_score").cast("int"),
            col("reviewer_id"),
            to_date("decision_date").alias("decision_date"),
            to_date("payment_date").alias("payment_date"),
            col("claim_doc_uri"),
            _fiscal_year_expr("submission_date").alias("fiscal_year"),
        )
    )


@dlt.table(name="silver_coop_allocation",
           comment="Per-FY allocation roster, typed and validated.")
@dlt.expect_or_drop("alloc_amount_positive", "allocated_usd > 0")
@dlt.expect_or_drop("alloc_dates_ordered", "expiration_date >= allocation_date")
def silver_coop_allocation():
    return (
        dlt.read_stream("bronze_allocation_csv").select(
            col("allocation_id"),
            col("dealer_external_id").alias("dealer_id"),
            col("program_code").alias("program_id"),
            col("fiscal_year"),
            col("allocated_usd").cast("decimal(14,2)").alias("allocated_usd"),
            to_date("allocation_date").alias("allocation_date"),
            to_date("expiration_date").alias("expiration_date"),
            col("allocation_source"),
        )
    )


@dlt.table(name="silver_sell_through_order",
           comment="ERP sell-through order lines, typed; FY derived from order_date.")
@dlt.expect_or_drop("order_amount_nonneg", "net_revenue_usd >= 0")
def silver_sell_through_order():
    return (
        dlt.read_stream("bronze_erp_sales_order").select(
            col("order_line_id"),
            col("order_id"),
            col("dealer_external_id").alias("dealer_id"),
            col("product_family"),
            to_date("order_date").alias("order_date"),
            to_date("ship_date").alias("ship_date"),
            col("net_revenue_usd").cast("decimal(12,2)").alias("net_revenue_usd"),
            _fiscal_year_expr("order_date").alias("fiscal_year"),
        )
    )


@dlt.table(name="silver_marketing_event",
           comment="Marketing event registrations, typed; FY derived from start_date.")
def silver_marketing_event():
    return (
        dlt.read_stream("bronze_event_registration").select(
            col("event_id"),
            col("dealer_external_id").alias("dealer_id"),
            col("activity_code").alias("activity_type_id"),
            to_date("start_date").alias("start_date"),
            to_date("end_date").alias("end_date"),
            col("attendees").cast("int"),
            col("event_cost_usd").cast("decimal(12,2)").alias("event_cost_usd"),
            col("claim_id").alias("claim_id_nullable"),
            _fiscal_year_expr("start_date").alias("fiscal_year"),
        )
    )


# ---------------------------------------------------------------------
# Dimension silver — demo shortcut, reads generator Parquet from volume.
#
# Production design (see demo-design.md §5.A):
#   silver.dealer        ← bronze.sfdc_account (SCD-2 via Lakeflow Connect)
#   silver.program       ← bronze.ref_program  (Auto Loader CSV)
#   silver.activity_type ← bronze.ref_activity_type
#   silver.region        ← bronze.ref_region
#   silver.fiscal_calendar ← bronze.ref_fiscal_calendar (or computed)
#
# The four dim parquet files must be uploaded to:
#   /Volumes/steelcase_demo/raw/reference/
# alongside compass-source.xlsx. They come straight out of the local
# generator's seed directory (dealer.parquet, program.parquet, ...).
# ---------------------------------------------------------------------
@dlt.table(name="silver_dealer",
           comment="Dealer dimension (current rows only for the demo; SCD-2 in production).")
def silver_dealer():
    return spark.read.parquet(f"{REFERENCE_BASE}/dealer.parquet")


@dlt.table(name="silver_program", comment="Program dimension.")
def silver_program():
    return spark.read.parquet(f"{REFERENCE_BASE}/program.parquet")


@dlt.table(name="silver_activity_type", comment="Activity-type dimension.")
def silver_activity_type():
    return spark.read.parquet(f"{REFERENCE_BASE}/activity_type.parquet")


@dlt.table(name="silver_region", comment="Region dimension.")
def silver_region():
    return spark.read.parquet(f"{REFERENCE_BASE}/region.parquet")


@dlt.table(name="silver_fiscal_calendar", comment="Steelcase fiscal calendar (Mar–Feb).")
def silver_fiscal_calendar():
    return spark.read.parquet(f"{REFERENCE_BASE}/fiscal_calendar.parquet")
