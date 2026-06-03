-- =====================================================================
-- Certified SQL examples — "Marketing Effectiveness & ROI" Genie Space
-- =====================================================================
-- Catalog: classic_stable_1zia5t_kp_catalog. Semantic queries go through
-- `compass_metric.*` views (never `compass_gold.fact_*` directly).

-- ---------------------------------------------------------------------
-- Q: Top 5 activities by revenue per co-op dollar in AMER East FY26.
-- A: Activity ladder — Programmatic Display leads at $7.40/$1.
-- ---------------------------------------------------------------------
SELECT
  at.activity_name,
  at.category,
  ROUND(MEASURE(revenue_per_coop_dollar_avg), 2) AS revenue_per_coop_dollar,
  ROUND(MEASURE(attributed_revenue_usd_total), 0) AS attributed_revenue_usd,
  ROUND(MEASURE(coop_paid_usd_total), 0)          AS coop_paid_usd
FROM classic_stable_1zia5t_kp_catalog.compass_metric.activity_lift al
JOIN classic_stable_1zia5t_kp_catalog.compass_gold.dim_activity_type at
  ON al.activity_type_id = at.activity_type_id
WHERE al.fiscal_year = 'FY26'
  AND al.region_full = 'AMER East'
GROUP BY at.activity_name, at.category
ORDER BY revenue_per_coop_dollar DESC
LIMIT 5;


-- ---------------------------------------------------------------------
-- Q: Which activity categories deliver the best lift?
-- ---------------------------------------------------------------------
SELECT
  at.category,
  ROUND(MEASURE(revenue_per_coop_dollar_avg), 2)  AS avg_revenue_per_coop_dollar,
  ROUND(MEASURE(attributed_revenue_usd_total), 0) AS attributed_revenue_usd,
  COUNT(DISTINCT al.activity_type_id)              AS distinct_activities
FROM classic_stable_1zia5t_kp_catalog.compass_metric.activity_lift al
JOIN classic_stable_1zia5t_kp_catalog.compass_gold.dim_activity_type at
  ON al.activity_type_id = at.activity_type_id
WHERE al.fiscal_year = 'FY26'
GROUP BY at.category
ORDER BY avg_revenue_per_coop_dollar DESC;


-- ---------------------------------------------------------------------
-- Q: Monthly net revenue for AMER East FY26 dealers by tier.
-- ---------------------------------------------------------------------
SELECT
  DATE_FORMAT(month, 'yyyy-MM')                    AS month,
  tier,
  ROUND(MEASURE(net_revenue_usd_total), 0)         AS net_revenue_usd,
  ROUND(MEASURE(coop_paid_usd_total), 0)           AS coop_paid_usd,
  ROUND(MEASURE(attributed_coop_usd_lift_total),0) AS attributed_lift_usd
FROM classic_stable_1zia5t_kp_catalog.compass_metric.dealer_performance
WHERE fiscal_year = 'FY26'
  AND region_full = 'AMER East'
GROUP BY month, tier
ORDER BY month, tier;


-- ---------------------------------------------------------------------
-- Q: Programmatic Display attributed revenue trend, EMEA, FY24–FY26.
-- ---------------------------------------------------------------------
SELECT
  fiscal_year,
  region_full,
  ROUND(MEASURE(coop_paid_usd_total), 0)          AS coop_paid_usd,
  ROUND(MEASURE(attributed_revenue_usd_total), 0) AS attributed_revenue_usd,
  ROUND(MEASURE(revenue_per_coop_dollar_avg), 2)  AS revenue_per_coop_dollar
FROM classic_stable_1zia5t_kp_catalog.compass_metric.activity_lift
WHERE activity_type_id = 'ACT-DIG-PROG-DISPLAY'
  AND region LIKE 'EMEA%'
GROUP BY fiscal_year, region_full
ORDER BY fiscal_year, region_full;


-- ---------------------------------------------------------------------
-- Q: Average revenue per co-op dollar by region (FY26).
-- ---------------------------------------------------------------------
SELECT
  region,
  ROUND(MEASURE(revenue_per_coop_dollar_avg), 2)  AS avg_revenue_per_coop_dollar,
  ROUND(MEASURE(attributed_revenue_usd_total), 0) AS attributed_revenue_usd
FROM classic_stable_1zia5t_kp_catalog.compass_metric.activity_lift
WHERE fiscal_year = 'FY26'
GROUP BY region
ORDER BY avg_revenue_per_coop_dollar DESC;


-- ---------------------------------------------------------------------
-- Q: Activities with revenue_per_coop_dollar > $5 — category breakdown.
-- ---------------------------------------------------------------------
SELECT
  at.activity_name,
  at.category,
  al.region_full,
  ROUND(MEASURE(revenue_per_coop_dollar_avg), 2)  AS revenue_per_coop_dollar
FROM classic_stable_1zia5t_kp_catalog.compass_metric.activity_lift al
JOIN classic_stable_1zia5t_kp_catalog.compass_gold.dim_activity_type at
  ON al.activity_type_id = at.activity_type_id
WHERE al.fiscal_year = 'FY26'
GROUP BY at.activity_name, at.category, al.region_full
HAVING MEASURE(revenue_per_coop_dollar_avg) > 5
ORDER BY revenue_per_coop_dollar DESC;
