# Databricks notebook source
# MAGIC %md
# MAGIC # COMPASS — Gold Materialization
# MAGIC
# MAGIC Materializes the four gold facts that drive the demo's metric views,
# MAGIC Genie space, and app. Logic mirrors `data/build-gold.py` (the local
# MAGIC reference rollup); any divergence here vs. the local script will show
# MAGIC up as a numbers mismatch in the click-script's $1.62M hero moment.
# MAGIC
# MAGIC | Gold fact                           | Drives                                  |
# MAGIC |-------------------------------------|-----------------------------------------|
# MAGIC | `gold.fact_coop_utilization_daily`  | `metric.forfeiture_risk`, balance views |
# MAGIC | `gold.fact_claim_sla`               | `metric.claim_lifecycle`                |
# MAGIC | `gold.fact_dealer_performance_monthly` | `metric.dealer_performance`          |
# MAGIC | `gold.fact_activity_lift`           | `metric.activity_lift`                  |

# COMMAND ----------

import dlt
from pyspark.sql.functions import (
    col, lit, when, sum as _sum, count as _count,
    current_date, date_trunc, datediff, greatest, expr,
)

NON_TERMINAL_STATUSES = ["Submitted", "Under_Review", "Approved", "Paid"]
APPROVED_STATUSES = ["Approved", "Paid"]

# Lift factor ladder — must match data/build-gold.py LIFT_FACTOR exactly.
# (Map keyed on activity_type_id; default 1.8 for anything not listed.)
LIFT_FACTOR = {
    "ACT-DIG-PROG-DISPLAY": 7.4,
    "ACT-EVT-AD-EVENT":     5.1,
    "ACT-SHO-HYBRID-ZONE":  4.2,
    "ACT-ABM-ENTERPRISE":   3.8,
    "ACT-EVT-NEOCON-REG":   2.9,
}


def _fiscal_period_expr(date_col: str):
    """Steelcase fiscal period P01..P12 (Mar = P01). SQL-only, no UDF."""
    return expr(f"""
        concat('P', lpad(cast(
            CASE
                WHEN {date_col} >= DATE'2026-03-01' THEN (year({date_col}) - 2026) * 12 + month({date_col}) - 3 + 1
                WHEN {date_col} >= DATE'2025-03-01' THEN (year({date_col}) - 2025) * 12 + month({date_col}) - 3 + 1
                WHEN {date_col} >= DATE'2024-03-01' THEN (year({date_col}) - 2024) * 12 + month({date_col}) - 3 + 1
                ELSE                                      (year({date_col}) - 2023) * 12 + month({date_col}) - 3 + 1
            END AS string), 2, '0'))
    """)


# ---------------------------------------------------------------------
# gold.fact_coop_utilization_daily
#
# Daily snapshot per dealer × program with two-band expected_forfeit_usd
# heuristic. Must match data/build-gold.py exactly:
#   expired  (days_to_exp < 0)                                → forfeited_usd
#   HIGH     (days_to_exp < 180 AND paid/allocated < 0.6)     → unused_usd
#   else                                                      → unused × (1-util)² × 0.1
# ---------------------------------------------------------------------
@dlt.table(name="gold_fact_coop_utilization_daily",
           partition_cols=["fiscal_year"],
           comment="Daily co-op utilization snapshot per dealer×program with precomputed expected_forfeit_usd.")
def gold_fact_coop_utilization_daily():
    alloc = dlt.read("silver_coop_allocation")
    claims = dlt.read("silver_coop_claim")

    alloc_agg = (alloc
        .groupBy("dealer_id", "program_id", "fiscal_year")
        .agg(
            _sum("allocated_usd").alias("allocated_usd"),
            expr("min(expiration_date)").alias("expiration_date"),
        ))

    committed = (claims.filter(col("status").isin(NON_TERMINAL_STATUSES))
        .groupBy("dealer_id", "program_id")
        .agg(_sum("requested_amount_usd").alias("committed_usd")))

    approved = (claims.filter(col("status").isin(APPROVED_STATUSES))
        .groupBy("dealer_id", "program_id")
        .agg(_sum("approved_amount_usd").alias("approved_usd")))

    paid = (claims.filter(col("status") == "Paid")
        .groupBy("dealer_id", "program_id")
        .agg(_sum("paid_amount_usd").alias("paid_usd")))

    df = (alloc_agg
        .join(committed, ["dealer_id", "program_id"], "left")
        .join(approved,  ["dealer_id", "program_id"], "left")
        .join(paid,      ["dealer_id", "program_id"], "left")
        .na.fill({"committed_usd": 0.0, "approved_usd": 0.0, "paid_usd": 0.0})
        .withColumn("unused_usd",
            greatest(col("allocated_usd") - col("committed_usd"), lit(0.0)))
        .withColumn("days_to_expiration",
            datediff(col("expiration_date"), current_date()))
        .withColumn("forfeited_usd",
            when(col("days_to_expiration") < 0, col("unused_usd")).otherwise(lit(0.0)))
        # Two-band expected_forfeit heuristic — matches build-gold.py
        .withColumn("utilization_ratio",
            col("paid_usd") / greatest(col("allocated_usd"), lit(1.0)))
        .withColumn("expected_forfeit_usd",
            when(col("days_to_expiration") < 0, col("forfeited_usd"))
            .when((col("days_to_expiration") < 180) & (col("utilization_ratio") < 0.6),
                  col("unused_usd"))
            .otherwise(
                col("unused_usd")
                * ((lit(1.0) - col("utilization_ratio")).cast("double"))
                * ((lit(1.0) - col("utilization_ratio")).cast("double"))
                * lit(0.1)
            ))
        .withColumn("date_key", current_date())
        .withColumn("fiscal_period", _fiscal_period_expr("date_key"))
        .select(
            "date_key", "dealer_id", "program_id", "fiscal_year", "fiscal_period",
            col("allocated_usd").cast("decimal(14,2)").alias("allocated_usd"),
            col("committed_usd").cast("decimal(14,2)").alias("committed_usd"),
            col("approved_usd").cast("decimal(14,2)").alias("approved_usd"),
            col("paid_usd").cast("decimal(14,2)").alias("paid_usd"),
            col("unused_usd").cast("decimal(14,2)").alias("unused_usd"),
            col("forfeited_usd").cast("decimal(14,2)").alias("forfeited_usd"),
            col("expected_forfeit_usd").cast("decimal(14,2)").alias("expected_forfeit_usd"),
            col("days_to_expiration").cast("int").alias("days_to_expiration"),
        ))
    return df


# ---------------------------------------------------------------------
# gold.fact_claim_sla
#
# One row per claim with cycle-time decomposition. Mirrors build-gold.py:
# half of submission→decision counts as "review intake", half as decision.
# first_pass_approval = (status in APPROVED) AND (brand_compliance_score >= 70).
# ---------------------------------------------------------------------
@dlt.table(name="gold_fact_claim_sla",
           partition_cols=["fiscal_year"],
           comment="One row per claim with cycle-time decomposition (submission/review/decision/payment).")
def gold_fact_claim_sla():
    claims = dlt.read("silver_coop_claim")
    dealers = dlt.read("silver_dealer").select("dealer_id", "region_id", "tier")

    return (claims.join(dealers, "dealer_id", "left")
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
            col("days_submission_to_review").cast("int"),
            col("days_review_to_decision").cast("int"),
            col("days_decision_to_payment").cast("int"),
            col("total_cycle_days").cast("int"),
            "first_pass_approval", "final_status", "fiscal_year",
        ))


# ---------------------------------------------------------------------
# gold.fact_dealer_performance_monthly
#
# Monthly revenue + co-op paid per dealer with attributed lift. Mirrors
# build-gold.py: attributed_coop_usd_lift = coop_paid_usd × 3.5,
# lift_vs_control_pct = 0.06 (simple heuristic for the demo).
# ---------------------------------------------------------------------
@dlt.table(name="gold_fact_dealer_performance_monthly",
           partition_cols=["fiscal_year"],
           comment="Monthly dealer sell-through with attributed co-op spend and lift-vs-control.")
def gold_fact_dealer_performance_monthly():
    orders = dlt.read("silver_sell_through_order")
    claims = dlt.read("silver_coop_claim")
    dealers = dlt.read("silver_dealer").select("dealer_id", "region_id", "tier")

    monthly_rev = (orders
        .withColumn("month", date_trunc("month", col("order_date")).cast("date"))
        .groupBy("dealer_id", "month", "fiscal_year")
        .agg(_sum("net_revenue_usd").alias("net_revenue_usd")))

    monthly_coop = (claims.filter(col("status") == "Paid")
        .withColumn("month", date_trunc("month", col("payment_date")).cast("date"))
        .groupBy("dealer_id", "month")
        .agg(_sum("paid_amount_usd").alias("coop_paid_usd")))

    return (monthly_rev
        .join(monthly_coop, ["dealer_id", "month"], "left")
        .join(dealers, "dealer_id", "left")
        .na.fill({"coop_paid_usd": 0.0})
        .withColumn("attributed_coop_usd_lift",
            (col("coop_paid_usd") * lit(3.5)).cast("decimal(14,2)"))
        .withColumn("lift_vs_control_pct", lit(0.06).cast("decimal(6,3)"))
        .select(
            "month", "dealer_id", "region_id", "tier",
            col("net_revenue_usd").cast("decimal(14,2)").alias("net_revenue_usd"),
            col("coop_paid_usd").cast("decimal(12,2)").alias("coop_paid_usd"),
            "attributed_coop_usd_lift", "lift_vs_control_pct", "fiscal_year",
        ))


# ---------------------------------------------------------------------
# gold.fact_activity_lift
#
# Activity-type × region × FY rollup. Encodes the v1.0-matched-tier-region
# methodology with the same LIFT_FACTOR ladder as build-gold.py — drives
# the Act 6 "top-5 activities" turn (Programmatic Display leads at $7.40/$1).
# ---------------------------------------------------------------------
@dlt.table(name="gold_fact_activity_lift",
           comment="Activity-type-level rollup of attributed revenue per co-op dollar.")
def gold_fact_activity_lift():
    claims = dlt.read("silver_coop_claim")
    dealers = dlt.read("silver_dealer").select("dealer_id", "region_id")

    base = (claims.filter(col("status") == "Paid")
        .join(dealers, "dealer_id", "left")
        .groupBy("activity_type_id", "region_id", "fiscal_year")
        .agg(
            _sum("paid_amount_usd").alias("coop_paid_usd"),
            _count(lit(1)).alias("matched_pairs"),
        ))

    # CASE expression matching LIFT_FACTOR; default 1.8.
    lift_case = when(lit(False), lit(1.8))
    for activity_id, factor in LIFT_FACTOR.items():
        lift_case = lift_case.when(col("activity_type_id") == lit(activity_id), lit(factor))
    lift_case = lift_case.otherwise(lit(1.8))

    return (base
        .withColumn("lift_factor", lift_case)
        .withColumn("attributed_revenue_usd",
            (col("coop_paid_usd") * col("lift_factor")).cast("decimal(14,2)"))
        .withColumn("revenue_per_coop_dollar",
            (col("attributed_revenue_usd") / greatest(col("coop_paid_usd"), lit(1.0)))
              .cast("decimal(8,2)"))
        .withColumn("lift_methodology_version", lit("v1.0-matched-tier-region"))
        .select(
            "activity_type_id", "region_id", "fiscal_year",
            col("coop_paid_usd").cast("decimal(14,2)").alias("coop_paid_usd"),
            "attributed_revenue_usd",
            "revenue_per_coop_dollar",
            col("matched_pairs").cast("int").alias("matched_pairs"),
            "lift_methodology_version",
        ))
