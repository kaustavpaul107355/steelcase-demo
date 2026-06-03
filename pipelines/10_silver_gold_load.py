# Databricks notebook source
# MAGIC %md
# MAGIC # COMPASS — Silver + Gold Load (workspace, batch, idempotent)
# MAGIC
# MAGIC Refreshes the full silver + gold layer in `classic_stable_1zia5t_kp_catalog`.
# MAGIC
# MAGIC **Job entry point.** Designed to be triggered by the
# MAGIC `compass-silver-gold-load` job. Re-runnable — uses `.mode("overwrite")`
# MAGIC on every Delta target so re-runs replace contents without duplication.
# MAGIC
# MAGIC ## Sources
# MAGIC
# MAGIC | Layer | Tables | Source |
# MAGIC |---|---|---|
# MAGIC | silver dim | `dealer`, `program`, `activity_type`, `region`, `fiscal_calendar` | `/Volumes/.../compass_bronze/raw/seed/*.parquet` |
# MAGIC | silver fact | `coop_allocation`, `coop_claim`, `sell_through_order`, `marketing_event` | Phase 1.5 hydrated `compass_bronze.*` |
# MAGIC | gold fact | `fact_coop_utilization_daily`, `fact_claim_sla`, `fact_dealer_performance_monthly`, `fact_activity_lift` | computed from silver, mirroring `data/build-gold.py` |
# MAGIC
# MAGIC ## Prerequisites
# MAGIC - **DBR 17.1+** (matches the bronze load notebook; required for parity).
# MAGIC - Phase 1.5 bronze tables populated. The pre-flight cell fails fast if not.
# MAGIC - Dim parquet files present at `/Volumes/.../compass_bronze/raw/seed/`.
# MAGIC - Silver and gold tables exist (DDL applied). All metric views in `compass_metric.*` reference these gold tables and will reflect new data automatically.

# COMMAND ----------

from datetime import date
from pyspark.sql.functions import (
    col, lit, when, sum as _sum, count as _count,
    date_trunc, datediff, greatest, expr,
)

CATALOG = "classic_stable_1zia5t_kp_catalog"
BRONZE = f"{CATALOG}.compass_bronze"
SILVER = f"{CATALOG}.compass_silver"
GOLD = f"{CATALOG}.compass_gold"
SEED_VOLUME = f"/Volumes/{CATALOG}/compass_bronze/raw/seed"

# Snapshot as-of for fact_coop_utilization_daily. Matches data/build-gold.py
# default — keeps the demo's $1.62M hero math stable across runs.
AS_OF = "2026-10-13"

NON_TERMINAL_STATUSES = ["Submitted", "Under_Review", "Approved", "Paid"]
APPROVED_STATUSES = ["Approved", "Paid"]

# Lift factor ladder — must match data/build-gold.py LIFT_FACTOR exactly.
LIFT_FACTOR = {
    "ACT-DIG-PROG-DISPLAY": 7.4,
    "ACT-EVT-AD-EVENT":     5.1,
    "ACT-SHO-HYBRID-ZONE":  4.2,
    "ACT-ABM-ENTERPRISE":   3.8,
    "ACT-EVT-NEOCON-REG":   2.9,
}


def _fy(d):
    """Fiscal-year derivation expression for a date column."""
    return (when(col(d) >= lit("2026-03-01"), lit("FY26"))
            .when(col(d) >= lit("2025-03-01"), lit("FY25"))
            .when(col(d) >= lit("2024-03-01"), lit("FY24"))
            .otherwise(lit("FY23")))


def _fiscal_period(date_col: str):
    return expr(f"""
        concat('P', lpad(cast(
            CASE
                WHEN {date_col} >= DATE'2026-03-01' THEN (year({date_col}) - 2026) * 12 + month({date_col}) - 3 + 1
                WHEN {date_col} >= DATE'2025-03-01' THEN (year({date_col}) - 2025) * 12 + month({date_col}) - 3 + 1
                WHEN {date_col} >= DATE'2024-03-01' THEN (year({date_col}) - 2024) * 12 + month({date_col}) - 3 + 1
                ELSE                                      (year({date_col}) - 2023) * 12 + month({date_col}) - 3 + 1
            END AS string), 2, '0'))
    """)


def _coerce_to_target(df, table_fqn: str):
    """Cast each source column to match target Delta schema."""
    target_schema = spark.table(table_fqn).schema
    src_cols = set(df.columns)
    for f in target_schema.fields:
        if f.name in src_cols:
            df = df.withColumn(f.name, col(f.name).cast(f.dataType))
    return df


def _write_overwrite(df, fqn: str):
    """Coerce + overwrite a Delta target while preserving its schema."""
    df = _coerce_to_target(df, fqn).select(*spark.table(fqn).columns)
    df.write.mode("overwrite").option("overwriteSchema", "false").saveAsTable(fqn)
    print(f"  {fqn}: {spark.table(fqn).count():>10,} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Pre-flight: bronze populated, dim parquets present

# COMMAND ----------

bronze_facts = ["allocation_csv", "erp_sales_order", "event_registration", "portal_claims"]
empty_bronze = [t for t in bronze_facts if spark.table(f"{BRONZE}.{t}").count() == 0]
if empty_bronze:
    raise RuntimeError(
        f"Bronze fact tables empty: {empty_bronze}. "
        f"Run the `compass-bronze-load` job first."
    )
print(f"  bronze fact tables: all populated ✓")
for f in ["dealer", "program", "activity_type", "region", "fiscal_calendar"]:
    n = spark.read.parquet(f"{SEED_VOLUME}/{f}.parquet").count()
    print(f"  seed/{f}.parquet: {n:>6,} rows ✓")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Silver: dimensions (from `compass_bronze.raw/seed/*.parquet`)

# COMMAND ----------

_write_overwrite(spark.read.parquet(f"{SEED_VOLUME}/dealer.parquet"),           f"{SILVER}.dealer")
_write_overwrite(spark.read.parquet(f"{SEED_VOLUME}/program.parquet"),          f"{SILVER}.program")
_write_overwrite(spark.read.parquet(f"{SEED_VOLUME}/activity_type.parquet"),    f"{SILVER}.activity_type")
_write_overwrite(spark.read.parquet(f"{SEED_VOLUME}/region.parquet"),           f"{SILVER}.region")
_write_overwrite(spark.read.parquet(f"{SEED_VOLUME}/fiscal_calendar.parquet"),  f"{SILVER}.fiscal_calendar")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Silver: facts (from Phase 1.5 hydrated bronze)

# COMMAND ----------

# silver.coop_allocation ← bronze.allocation_csv
df = (spark.table(f"{BRONZE}.allocation_csv")
      .select(
          col("allocation_id"),
          col("dealer_external_id").alias("dealer_id"),
          col("program_code").alias("program_id"),
          col("fiscal_year"),
          col("allocated_usd"),
          col("allocation_date"),
          col("expiration_date"),
          col("allocation_source"),
      ))
_write_overwrite(df, f"{SILVER}.coop_allocation")

# silver.coop_claim ← bronze.portal_claims
df = (spark.table(f"{BRONZE}.portal_claims")
      .select(
          col("claim_id"),
          col("dealer_external_id").alias("dealer_id"),
          col("program_code").alias("program_id"),
          col("activity_code").alias("activity_type_id"),
          col("preapproval_id"),
          col("submission_date"),
          col("requested_amount").alias("requested_amount_usd"),
          col("approved_amount").alias("approved_amount_usd"),
          col("paid_amount").alias("paid_amount_usd"),
          col("status"),
          col("brand_compliance_score"),
          col("reviewer_id"),
          col("decision_date"),
          col("payment_date"),
          col("claim_doc_uri"),
          _fy("submission_date").alias("fiscal_year"),
      ))
_write_overwrite(df, f"{SILVER}.coop_claim")

# silver.sell_through_order ← bronze.erp_sales_order
df = (spark.table(f"{BRONZE}.erp_sales_order")
      .select(
          col("order_line_id"),
          col("order_id"),
          col("dealer_external_id").alias("dealer_id"),
          col("product_family"),
          col("order_date"),
          col("ship_date"),
          col("net_revenue_usd"),
          _fy("order_date").alias("fiscal_year"),
      ))
_write_overwrite(df, f"{SILVER}.sell_through_order")

# silver.marketing_event ← bronze.event_registration
df = (spark.table(f"{BRONZE}.event_registration")
      .select(
          col("event_id"),
          col("dealer_external_id").alias("dealer_id"),
          col("activity_code").alias("activity_type_id"),
          col("start_date"),
          col("end_date"),
          col("attendees"),
          col("event_cost_usd"),
          col("claim_id").alias("claim_id_nullable"),
          _fy("start_date").alias("fiscal_year"),
      ))
_write_overwrite(df, f"{SILVER}.marketing_event")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold: `fact_coop_utilization_daily`
# MAGIC
# MAGIC Snapshot at `AS_OF = 2026-10-13`. Two-band `expected_forfeit_usd` matches `data/build-gold.py`.

# COMMAND ----------

alloc = spark.table(f"{SILVER}.coop_allocation")
claims = spark.table(f"{SILVER}.coop_claim")

alloc_agg = (alloc
    .groupBy("dealer_id", "program_id", "fiscal_year")
    .agg(_sum("allocated_usd").alias("allocated_usd"),
         expr("min(expiration_date)").alias("expiration_date")))

committed = (claims.filter(col("status").isin(NON_TERMINAL_STATUSES))
    .groupBy("dealer_id", "program_id")
    .agg(_sum("requested_amount_usd").alias("committed_usd")))

approved = (claims.filter(col("status").isin(APPROVED_STATUSES))
    .groupBy("dealer_id", "program_id")
    .agg(_sum("approved_amount_usd").alias("approved_usd")))

paid = (claims.filter(col("status") == "Paid")
    .groupBy("dealer_id", "program_id")
    .agg(_sum("paid_amount_usd").alias("paid_usd")))

util = (alloc_agg
    .join(committed, ["dealer_id", "program_id"], "left")
    .join(approved,  ["dealer_id", "program_id"], "left")
    .join(paid,      ["dealer_id", "program_id"], "left")
    .na.fill({"committed_usd": 0.0, "approved_usd": 0.0, "paid_usd": 0.0})
    .withColumn("unused_usd", greatest(col("allocated_usd") - col("committed_usd"), lit(0.0)))
    .withColumn("days_to_expiration", datediff(col("expiration_date"), lit(AS_OF).cast("date")))
    .withColumn("forfeited_usd",
        when(col("days_to_expiration") < 0, col("unused_usd")).otherwise(lit(0.0)))
    .withColumn("utilization_ratio",
        col("paid_usd") / greatest(col("allocated_usd"), lit(1.0)))
    .withColumn("expected_forfeit_usd",
        when(col("days_to_expiration") < 0, col("forfeited_usd"))
        .when((col("days_to_expiration") < 180) & (col("utilization_ratio") < 0.6),
              col("unused_usd"))
        .otherwise(col("unused_usd")
                   * (lit(1.0) - col("utilization_ratio")).cast("double")
                   * (lit(1.0) - col("utilization_ratio")).cast("double")
                   * lit(0.1)))
    .withColumn("date_key", lit(AS_OF).cast("date"))
    .withColumn("fiscal_period", _fiscal_period("date_key"))
    .select(
        "date_key", "dealer_id", "program_id", "fiscal_year", "fiscal_period",
        "allocated_usd", "committed_usd", "approved_usd", "paid_usd",
        "unused_usd", "forfeited_usd", "expected_forfeit_usd",
        "days_to_expiration",
    ))
_write_overwrite(util, f"{GOLD}.fact_coop_utilization_daily")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold: `fact_claim_sla`

# COMMAND ----------

claims = spark.table(f"{SILVER}.coop_claim")
dealers = spark.table(f"{SILVER}.dealer").select("dealer_id", "region_id", "tier")

sla = (claims.join(dealers, "dealer_id", "left")
    .withColumn("days_submission_to_decision",
        datediff(col("decision_date"), col("submission_date")))
    .withColumn("days_decision_to_payment",
        datediff(col("payment_date"), col("decision_date")))
    .withColumn("days_submission_to_review",
        (col("days_submission_to_decision") / 2).cast("int"))
    .withColumn("days_review_to_decision",
        (col("days_submission_to_decision") / 2).cast("int"))
    .withColumn("total_cycle_days",
        datediff(col("payment_date"), col("submission_date")))
    .withColumn("first_pass_approval",
        col("status").isin(APPROVED_STATUSES) & (col("brand_compliance_score") >= 70))
    .withColumn("final_status", col("status"))
    .select(
        "claim_id", "dealer_id", "region_id", "tier",
        "program_id", "activity_type_id",
        "submission_date", "decision_date", "payment_date",
        "days_submission_to_review", "days_review_to_decision",
        "days_decision_to_payment", "total_cycle_days",
        "first_pass_approval", "final_status", "fiscal_year",
    ))
_write_overwrite(sla, f"{GOLD}.fact_claim_sla")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold: `fact_dealer_performance_monthly`

# COMMAND ----------

orders = spark.table(f"{SILVER}.sell_through_order")
claims = spark.table(f"{SILVER}.coop_claim")
dealers = spark.table(f"{SILVER}.dealer").select("dealer_id", "region_id", "tier")

monthly_rev = (orders
    .withColumn("month", date_trunc("month", col("order_date")).cast("date"))
    .groupBy("dealer_id", "month", "fiscal_year")
    .agg(_sum("net_revenue_usd").alias("net_revenue_usd")))

monthly_coop = (claims.filter(col("status") == "Paid")
    .withColumn("month", date_trunc("month", col("payment_date")).cast("date"))
    .groupBy("dealer_id", "month")
    .agg(_sum("paid_amount_usd").alias("coop_paid_usd")))

perf = (monthly_rev
    .join(monthly_coop, ["dealer_id", "month"], "left")
    .join(dealers, "dealer_id", "left")
    .na.fill({"coop_paid_usd": 0.0})
    .withColumn("attributed_coop_usd_lift", col("coop_paid_usd") * lit(3.5))
    .withColumn("lift_vs_control_pct", lit(0.06))
    .select(
        "month", "dealer_id", "region_id", "tier",
        "net_revenue_usd", "coop_paid_usd",
        "attributed_coop_usd_lift", "lift_vs_control_pct", "fiscal_year",
    ))
_write_overwrite(perf, f"{GOLD}.fact_dealer_performance_monthly")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold: `fact_activity_lift`

# COMMAND ----------

claims = spark.table(f"{SILVER}.coop_claim")
dealers = spark.table(f"{SILVER}.dealer").select("dealer_id", "region_id")

base = (claims.filter(col("status") == "Paid")
    .join(dealers, "dealer_id", "left")
    .groupBy("activity_type_id", "region_id", "fiscal_year")
    .agg(_sum("paid_amount_usd").alias("coop_paid_usd"),
         _count(lit(1)).alias("matched_pairs")))

lift_case = when(lit(False), lit(1.8))
for activity_id, factor in LIFT_FACTOR.items():
    lift_case = lift_case.when(col("activity_type_id") == lit(activity_id), lit(factor))
lift_case = lift_case.otherwise(lit(1.8))

activity_lift = (base
    .withColumn("lift_factor", lift_case)
    .withColumn("attributed_revenue_usd", col("coop_paid_usd") * col("lift_factor"))
    .withColumn("revenue_per_coop_dollar",
        (col("attributed_revenue_usd") / greatest(col("coop_paid_usd"), lit(1.0)))
          .cast("decimal(8,2)"))
    .withColumn("lift_methodology_version", lit("v1.0-matched-tier-region"))
    .select(
        "activity_type_id", "region_id", "fiscal_year",
        "coop_paid_usd", "attributed_revenue_usd",
        "revenue_per_coop_dollar", "matched_pairs",
        "lift_methodology_version",
    ))
_write_overwrite(activity_lift, f"{GOLD}.fact_activity_lift")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Hero sanity check
# MAGIC
# MAGIC AMER East FY26 expected_forfeit should hit ~$1.62M and top 3 should be Pivot / Halcyon / Northpoint.

# COMMAND ----------

result = spark.sql(f"""
    SELECT
        ROUND(SUM(util.expected_forfeit_usd), 2) AS amer_east_fy26_expected_forfeit,
        COUNT(DISTINCT util.dealer_id)            AS dealers
    FROM {GOLD}.fact_coop_utilization_daily util
    JOIN {SILVER}.dealer d ON util.dealer_id = d.dealer_id
    WHERE util.fiscal_year = 'FY26'
      AND d.region_id = 'RGN-AMER-EAST'
""").collect()[0]
print(f"  AMER East FY26 expected_forfeit_usd: ${result.amer_east_fy26_expected_forfeit:,.2f}")
print(f"  Dealers covered:                     {result.dealers}")

top3 = spark.sql(f"""
    SELECT d.dealer_name, d.tier, ROUND(util.unused_usd, 0) AS unused_usd
    FROM {GOLD}.fact_coop_utilization_daily util
    JOIN {SILVER}.dealer d ON util.dealer_id = d.dealer_id
    WHERE util.fiscal_year = 'FY26' AND d.region_id = 'RGN-AMER-EAST'
    ORDER BY util.unused_usd DESC
    LIMIT 3
""").collect()
print("  Top 3 at-risk (FY26 AMER East):")
for r in top3:
    print(f"    {r.dealer_name:<40} {r.tier:<12} ${r.unused_usd:>10,.0f}")
