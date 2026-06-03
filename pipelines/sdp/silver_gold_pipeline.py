# COMPASS — Silver + Gold (Lakeflow Declarative Pipeline)
#
# Reads from the 8 bronze tables in `compass_bronze.*` (loaded by the
# `compass-bronze-load` job) and materializes:
#   - 9 silver tables   (5 dim, 4 fact)
#   - 4 gold facts      (utilization, claim_sla, dealer_performance, activity_lift)
#
# Gold dim views are SQL CREATE OR REPLACE VIEW objects in `data/ddl/03-gold.sql`
# and are NOT managed by this pipeline (they reference silver directly).
#
# Uses the modern `pyspark.pipelines` API. All targets are materialized views
# (full-table recompute on each pipeline refresh) — fits the demo's batch-overwrite
# bronze pattern. Multi-schema via fully qualified names.
#
# Parameters supplied by the pipeline's `configuration` block (see databricks.yml):
#   compass.catalog        — UC catalog (e.g. classic_stable_1zia5t_kp_catalog)
#   compass.bronze_schema  — bronze schema name
#   compass.silver_schema  — silver schema name
#   compass.gold_schema    — gold schema name
#   compass.as_of          — snapshot date for fact_coop_utilization_daily (e.g. 2026-10-13)

from pyspark import pipelines as dp
from pyspark.sql.functions import (
    col, lit, when, sum as _sum, count as _count,
    date_trunc, datediff, greatest, expr,
)

CATALOG = spark.conf.get("compass.catalog")
BRONZE  = spark.conf.get("compass.bronze_schema")
SILVER  = spark.conf.get("compass.silver_schema")
GOLD    = spark.conf.get("compass.gold_schema")
AS_OF   = spark.conf.get("compass.as_of")

NON_TERMINAL_STATUSES = ["Submitted", "Under_Review", "Approved", "Paid"]
APPROVED_STATUSES     = ["Approved", "Paid"]

# Lift factor ladder — must match data/build-gold.py LIFT_FACTOR exactly.
LIFT_FACTOR = {
    "ACT-DIG-PROG-DISPLAY": 7.4,
    "ACT-EVT-AD-EVENT":     5.1,
    "ACT-SHO-HYBRID-ZONE":  4.2,
    "ACT-ABM-ENTERPRISE":   3.8,
    "ACT-EVT-NEOCON-REG":   2.9,
}


def _fy(d):
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


# =====================================================================
# Silver — dimensions (from bronze reference/master tables)
# =====================================================================
@dp.materialized_view(name=f"{CATALOG}.{SILVER}.dealer",
                      comment="Dealer dimension — current rows derived from bronze.sfdc_account.")
@dp.expect_or_drop("tier_valid", "tier IN ('Platinum','Gold','Silver','Authorized')")
def silver_dealer():
    return (spark.read.table(f"{CATALOG}.{BRONZE}.sfdc_account")
        .filter(~col("IsDeleted"))
        .select(
            col("Dealer_External_Id__c").alias("dealer_id"),
            col("Id").alias("salesforce_account_id"),
            col("Name").alias("dealer_name"),
            col("Region__c").alias("region_id"),
            col("BillingCountry").alias("country"),
            col("Tier__c").alias("tier"),
            col("Sales_Rep__c").alias("sales_rep_id"),
            lit("2023-01-01").cast("date").alias("effective_from"),
            lit(None).cast("date").alias("effective_to"),
            lit(True).alias("is_current"),
        ))


@dp.materialized_view(name=f"{CATALOG}.{SILVER}.program",
                      comment="Program dimension — from bronze.ref_program.")
def silver_program():
    return (spark.read.table(f"{CATALOG}.{BRONZE}.ref_program")
        .select(
            col("program_code").alias("program_id"),
            col("program_name"),
            col("fiscal_year"),
            col("allocation_method"),
            col("default_cofund_pct"),
            col("program_start"),
            col("program_end"),
        ))


@dp.materialized_view(name=f"{CATALOG}.{SILVER}.activity_type",
                      comment="Activity-type dimension — from bronze.ref_activity_type.")
def silver_activity_type():
    return (spark.read.table(f"{CATALOG}.{BRONZE}.ref_activity_type")
        .select(
            col("activity_code").alias("activity_type_id"),
            col("category"),
            col("activity_name"),
            col("default_cofund_pct"),
            col("requires_preapproval"),
            col("preapproval_threshold_usd"),
        ))


@dp.materialized_view(name=f"{CATALOG}.{SILVER}.region",
                      comment="Region dimension — from bronze.ref_region.")
def silver_region():
    return (spark.read.table(f"{CATALOG}.{BRONZE}.ref_region")
        .select("region_id", "region", "sub_region", "default_currency"))


@dp.materialized_view(name=f"{CATALOG}.{SILVER}.fiscal_calendar",
                      comment="Steelcase fiscal calendar — daily rows FY23..FY26 (computed).")
def silver_fiscal_calendar():
    return spark.sql("""
        WITH days AS (
          SELECT explode(sequence(DATE'2023-03-01', DATE'2027-02-28', INTERVAL 1 DAY)) AS date_key
        )
        SELECT
          date_key,
          CASE
            WHEN date_key >= DATE'2026-03-01' THEN 'FY26'
            WHEN date_key >= DATE'2025-03-01' THEN 'FY25'
            WHEN date_key >= DATE'2024-03-01' THEN 'FY24'
            ELSE 'FY23'
          END AS fiscal_year,
          concat('P', lpad(cast(
            CASE
              WHEN date_key >= DATE'2026-03-01' THEN (year(date_key) - 2026) * 12 + month(date_key) - 3 + 1
              WHEN date_key >= DATE'2025-03-01' THEN (year(date_key) - 2025) * 12 + month(date_key) - 3 + 1
              WHEN date_key >= DATE'2024-03-01' THEN (year(date_key) - 2024) * 12 + month(date_key) - 3 + 1
              ELSE                                    (year(date_key) - 2023) * 12 + month(date_key) - 3 + 1
            END AS string), 2, '0')) AS fiscal_period,
          cast(
            datediff(date_key, CASE
                WHEN date_key >= DATE'2026-03-01' THEN DATE'2026-03-01'
                WHEN date_key >= DATE'2025-03-01' THEN DATE'2025-03-01'
                WHEN date_key >= DATE'2024-03-01' THEN DATE'2024-03-01'
                ELSE                                    DATE'2023-03-01'
              END) DIV 7 + 1
          AS INT) AS fiscal_week,
          CASE
            WHEN month(date_key) IN (3,4,5)  THEN 'Q1'
            WHEN month(date_key) IN (6,7,8)  THEN 'Q2'
            WHEN month(date_key) IN (9,10,11) THEN 'Q3'
            ELSE 'Q4'
          END AS fiscal_quarter
        FROM days
    """)


# =====================================================================
# Silver — facts (from Phase 1.5 bronze)
# =====================================================================
@dp.materialized_view(name=f"{CATALOG}.{SILVER}.coop_allocation",
                      comment="Curated allocation roster — from bronze.allocation_csv.")
@dp.expect_or_drop("alloc_amount_positive", "allocated_usd > 0")
@dp.expect_or_drop("alloc_dates_ordered", "expiration_date >= allocation_date")
def silver_coop_allocation():
    return (spark.read.table(f"{CATALOG}.{BRONZE}.allocation_csv")
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


@dp.materialized_view(name=f"{CATALOG}.{SILVER}.coop_claim",
                      comment="Curated co-op claims — from bronze.portal_claims.")
@dp.expect_or_drop("claim_amount_positive", "requested_amount_usd > 0")
@dp.expect_or_drop("status_valid",
    "status IN ('Draft','Submitted','Under_Review','Approved','Rejected','Paid','Expired')")
@dp.expect_or_drop("paid_le_approved",
    "paid_amount_usd IS NULL OR approved_amount_usd IS NULL OR paid_amount_usd <= approved_amount_usd")
def silver_coop_claim():
    return (spark.read.table(f"{CATALOG}.{BRONZE}.portal_claims")
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


@dp.materialized_view(name=f"{CATALOG}.{SILVER}.sell_through_order",
                      comment="ERP sell-through orders — from bronze.erp_sales_order.")
@dp.expect_or_drop("order_amount_nonneg", "net_revenue_usd >= 0")
def silver_sell_through_order():
    return (spark.read.table(f"{CATALOG}.{BRONZE}.erp_sales_order")
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


@dp.materialized_view(name=f"{CATALOG}.{SILVER}.marketing_event",
                      comment="Marketing event registrations — from bronze.event_registration.")
def silver_marketing_event():
    return (spark.read.table(f"{CATALOG}.{BRONZE}.event_registration")
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


# =====================================================================
# Gold — facts (materialized views from silver)
# =====================================================================
@dp.materialized_view(name=f"{CATALOG}.{GOLD}.fact_coop_utilization_daily",
                      comment="Daily co-op utilization snapshot with two-band expected_forfeit_usd heuristic.")
def gold_fact_coop_utilization_daily():
    alloc = spark.read.table(f"{CATALOG}.{SILVER}.coop_allocation")
    claims = spark.read.table(f"{CATALOG}.{SILVER}.coop_claim")

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

    return (alloc_agg
        .join(committed, ["dealer_id", "program_id"], "left")
        .join(approved,  ["dealer_id", "program_id"], "left")
        .join(paid,      ["dealer_id", "program_id"], "left")
        .na.fill({"committed_usd": 0.0, "approved_usd": 0.0, "paid_usd": 0.0})
        .withColumn("unused_usd",
            greatest(col("allocated_usd") - col("committed_usd"), lit(0.0)))
        .withColumn("days_to_expiration",
            datediff(col("expiration_date"), lit(AS_OF).cast("date")))
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


@dp.materialized_view(name=f"{CATALOG}.{GOLD}.fact_claim_sla",
                      comment="One row per claim with cycle-time decomposition.")
def gold_fact_claim_sla():
    claims = spark.read.table(f"{CATALOG}.{SILVER}.coop_claim")
    dealers = spark.read.table(f"{CATALOG}.{SILVER}.dealer").select("dealer_id", "region_id", "tier")

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
            "days_submission_to_review", "days_review_to_decision",
            "days_decision_to_payment", "total_cycle_days",
            "first_pass_approval", "final_status", "fiscal_year",
        ))


@dp.materialized_view(name=f"{CATALOG}.{GOLD}.fact_dealer_performance_monthly",
                      comment="Monthly dealer sell-through with attributed co-op lift.")
def gold_fact_dealer_performance_monthly():
    orders = spark.read.table(f"{CATALOG}.{SILVER}.sell_through_order")
    claims = spark.read.table(f"{CATALOG}.{SILVER}.coop_claim")
    dealers = spark.read.table(f"{CATALOG}.{SILVER}.dealer").select("dealer_id", "region_id", "tier")

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
        .withColumn("attributed_coop_usd_lift", col("coop_paid_usd") * lit(3.5))
        .withColumn("lift_vs_control_pct", lit(0.06))
        .select(
            "month", "dealer_id", "region_id", "tier",
            "net_revenue_usd", "coop_paid_usd",
            "attributed_coop_usd_lift", "lift_vs_control_pct", "fiscal_year",
        ))


@dp.materialized_view(name=f"{CATALOG}.{GOLD}.fact_activity_lift",
                      comment="Activity-type-level attributed revenue per co-op dollar; drives Act 6.")
def gold_fact_activity_lift():
    claims = spark.read.table(f"{CATALOG}.{SILVER}.coop_claim")
    dealers = spark.read.table(f"{CATALOG}.{SILVER}.dealer").select("dealer_id", "region_id")

    base = (claims.filter(col("status") == "Paid")
        .join(dealers, "dealer_id", "left")
        .groupBy("activity_type_id", "region_id", "fiscal_year")
        .agg(_sum("paid_amount_usd").alias("coop_paid_usd"),
             _count(lit(1)).alias("matched_pairs")))

    lift_case = when(lit(False), lit(1.8))
    for activity_id, factor in LIFT_FACTOR.items():
        lift_case = lift_case.when(col("activity_type_id") == lit(activity_id), lit(factor))
    lift_case = lift_case.otherwise(lit(1.8))

    return (base
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
