-- =====================================================================
-- Certified SQL examples — "Co-op Utilization & Risk" Genie Space
-- =====================================================================
-- These are the patterns we want Genie to learn from. Each one is the
-- "right answer" to a starter question. Genie uses them as in-context
-- exemplars when translating new questions.
--
-- Catalog is `classic_stable_1zia5t_kp_catalog`. All semantic queries go
-- through `compass_metric.*` views (never `compass_gold.fact_*` directly).

-- ---------------------------------------------------------------------
-- Q: What's my Q4 forfeiture risk?
-- A: AMER East FY26 expected_forfeit_usd via metric view. Should produce
--    ~$1,619,574 across 23 dealers.
-- ---------------------------------------------------------------------
SELECT
  MEASURE(expected_forfeit_usd_total) AS expected_forfeit_usd,
  MEASURE(unused_usd_total)           AS unused_usd
FROM classic_stable_1zia5t_kp_catalog.compass_metric.forfeiture_risk
WHERE fiscal_year = 'FY26'
  AND region_full = 'AMER East';


-- ---------------------------------------------------------------------
-- Q: Show me those 23 dealers with their balance, expiration, and YTD utilization.
-- A: Hero list. Top 23 by unused_usd descending, joined to dim_dealer for names.
-- ---------------------------------------------------------------------
SELECT
  d.dealer_name,
  d.tier,
  ROUND(MEASURE(unused_usd_total), 2)           AS unused_usd,
  ROUND(MEASURE(paid_usd_total), 2)             AS paid_usd,
  ROUND(MEASURE(utilization_rate_ytd) * 100, 1) AS utilization_pct,
  MIN(expiration_date)                          AS expiration_date
FROM classic_stable_1zia5t_kp_catalog.compass_metric.forfeiture_risk f
JOIN classic_stable_1zia5t_kp_catalog.compass_gold.dim_dealer d
  ON f.dealer_id = d.dealer_id
WHERE f.fiscal_year = 'FY26'
  AND f.region_full = 'AMER East'
GROUP BY d.dealer_name, d.tier
ORDER BY unused_usd DESC
LIMIT 23;


-- ---------------------------------------------------------------------
-- Q: How many claims are stuck in Under_Review for AMER East?
-- ---------------------------------------------------------------------
SELECT
  region_full,
  MEASURE(claims_under_review_count) AS claims_under_review
FROM classic_stable_1zia5t_kp_catalog.compass_metric.claim_lifecycle
WHERE fiscal_year = 'FY26'
  AND region_full = 'AMER East';


-- ---------------------------------------------------------------------
-- Q: Total allocated vs. paid for FY26 main co-op program by region.
-- ---------------------------------------------------------------------
SELECT
  region_full,
  ROUND(MEASURE(allocated_usd_total), 0) AS allocated_usd,
  ROUND(MEASURE(paid_usd_total), 0)      AS paid_usd,
  ROUND(MEASURE(unused_usd_total), 0)    AS unused_usd
FROM classic_stable_1zia5t_kp_catalog.compass_metric.coop_program_metrics
WHERE fiscal_year = 'FY26'
  AND program_id = 'PRG-FY26-COOP-MAIN'
GROUP BY region_full
ORDER BY paid_usd DESC;


-- ---------------------------------------------------------------------
-- Q: Average claim cycle time for Tier-Silver dealers in AMER East.
-- ---------------------------------------------------------------------
SELECT
  tier,
  ROUND(MEASURE(avg_total_cycle_days), 1)              AS avg_total_cycle_days,
  ROUND(MEASURE(avg_days_submission_to_decision), 1)   AS avg_submit_to_decision,
  ROUND(MEASURE(avg_days_decision_to_payment), 1)      AS avg_decision_to_pay
FROM classic_stable_1zia5t_kp_catalog.compass_metric.claim_lifecycle
WHERE fiscal_year = 'FY26'
  AND region_full = 'AMER East'
  AND tier = 'Silver'
GROUP BY tier;


-- ---------------------------------------------------------------------
-- Q: Dealers with allocation expiring within 60 days (FY26 AMER East).
-- ---------------------------------------------------------------------
SELECT
  d.dealer_name,
  d.tier,
  ROUND(MEASURE(unused_usd_total), 0) AS unused_usd,
  MIN(f.expiration_date)              AS expiration_date,
  MIN(f.days_to_expiration)           AS days_to_expiration
FROM classic_stable_1zia5t_kp_catalog.compass_metric.forfeiture_risk f
JOIN classic_stable_1zia5t_kp_catalog.compass_gold.dim_dealer d
  ON f.dealer_id = d.dealer_id
WHERE f.fiscal_year = 'FY26'
  AND f.region_full = 'AMER East'
  AND f.days_to_expiration BETWEEN 0 AND 60
GROUP BY d.dealer_name, d.tier
ORDER BY days_to_expiration ASC;
