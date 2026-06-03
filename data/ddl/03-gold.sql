-- =====================================================================
-- COMPASS Demo — Gold layer DDL
-- Materialized aggregates and conformed dimensions for Genie + apps.
-- =====================================================================

CREATE SCHEMA IF NOT EXISTS steelcase_demo.gold;

-- ---------------------------------------------------------------------
-- gold.dim_dealer (current-only view of silver SCD-2)
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW steelcase_demo.gold.dim_dealer AS
SELECT
  dealer_id,
  salesforce_account_id,
  dealer_name,
  region_id,
  country,
  tier,
  sales_rep_id
FROM steelcase_demo.silver.dealer
WHERE is_current = TRUE;

CREATE OR REPLACE VIEW steelcase_demo.gold.dim_program AS
SELECT * FROM steelcase_demo.silver.program;

CREATE OR REPLACE VIEW steelcase_demo.gold.dim_activity_type AS
SELECT * FROM steelcase_demo.silver.activity_type;

CREATE OR REPLACE VIEW steelcase_demo.gold.dim_region AS
SELECT * FROM steelcase_demo.silver.region;

CREATE OR REPLACE VIEW steelcase_demo.gold.dim_fiscal_calendar AS
SELECT * FROM steelcase_demo.silver.fiscal_calendar;

-- ---------------------------------------------------------------------
-- gold.fact_coop_utilization_daily
--   one row per dealer × program × fiscal_period × day
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS steelcase_demo.gold.fact_coop_utilization_daily (
  date_key                 DATE NOT NULL,
  dealer_id                STRING NOT NULL,
  program_id               STRING NOT NULL,
  fiscal_year              STRING NOT NULL,
  fiscal_period            STRING NOT NULL,
  allocated_usd            DECIMAL(14,2) NOT NULL,
  committed_usd            DECIMAL(14,2) NOT NULL,
  approved_usd             DECIMAL(14,2) NOT NULL,
  paid_usd                 DECIMAL(14,2) NOT NULL,
  unused_usd               DECIMAL(14,2) NOT NULL,
  forfeited_usd            DECIMAL(14,2) NOT NULL,   -- > 0 only on/after expiration
  expected_forfeit_usd     DECIMAL(14,2) NOT NULL,   -- precomputed heuristic (active programs)
  days_to_expiration       INT
) USING DELTA
PARTITIONED BY (fiscal_year);

-- ---------------------------------------------------------------------
-- gold.fact_claim_sla
--   one row per claim with cycle-time decomposition
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS steelcase_demo.gold.fact_claim_sla (
  claim_id                 STRING NOT NULL,
  dealer_id                STRING NOT NULL,
  region_id                STRING NOT NULL,
  tier                     STRING NOT NULL,
  program_id               STRING NOT NULL,
  activity_type_id         STRING NOT NULL,
  submission_date          DATE NOT NULL,
  decision_date            DATE,
  payment_date             DATE,
  days_submission_to_review INT,
  days_review_to_decision  INT,
  days_decision_to_payment INT,
  total_cycle_days         INT,
  first_pass_approval      BOOLEAN,
  final_status             STRING NOT NULL,
  fiscal_year              STRING NOT NULL
) USING DELTA
PARTITIONED BY (fiscal_year);

-- ---------------------------------------------------------------------
-- gold.fact_dealer_performance_monthly
--   one row per dealer × month
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS steelcase_demo.gold.fact_dealer_performance_monthly (
  month                    DATE NOT NULL,    -- first of month
  dealer_id                STRING NOT NULL,
  region_id                STRING NOT NULL,
  tier                     STRING NOT NULL,
  net_revenue_usd          DECIMAL(14,2) NOT NULL,
  coop_paid_usd            DECIMAL(12,2) NOT NULL,
  attributed_coop_usd_lift DECIMAL(14,2),
  lift_vs_control_pct      DECIMAL(6,3),
  fiscal_year              STRING NOT NULL
) USING DELTA
PARTITIONED BY (fiscal_year);

-- ---------------------------------------------------------------------
-- gold.fact_activity_lift
--   roll-up of dealer performance by activity_type to support the Q5 turn
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS steelcase_demo.gold.fact_activity_lift (
  activity_type_id         STRING NOT NULL,
  region_id                STRING NOT NULL,
  fiscal_year              STRING NOT NULL,
  coop_paid_usd            DECIMAL(14,2) NOT NULL,
  attributed_revenue_usd   DECIMAL(14,2) NOT NULL,
  revenue_per_coop_dollar  DECIMAL(8,2) NOT NULL,
  matched_pairs            INT NOT NULL,
  lift_methodology_version STRING NOT NULL  -- e.g. 'v1.0-matched-tier-region'
) USING DELTA;

-- ---------------------------------------------------------------------
-- Comments on gold tables (used by Genie for hints)
-- ---------------------------------------------------------------------
COMMENT ON TABLE steelcase_demo.gold.fact_coop_utilization_daily IS
  'Daily snapshot of Steelcase co-op program utilization per dealer and program. Use for forfeiture, utilization, and balance questions. Grain: dealer x program x fiscal_period x date_key.';
COMMENT ON TABLE steelcase_demo.gold.fact_claim_sla IS
  'One row per claim with cycle-time decomposition. Use for claim approval SLA, first-pass approval rate, and reviewer load.';
COMMENT ON TABLE steelcase_demo.gold.fact_dealer_performance_monthly IS
  'Monthly dealer sell-through with attributed co-op spend and lift-vs-control. Use for ROI, attribution, and program effectiveness.';
COMMENT ON TABLE steelcase_demo.gold.fact_activity_lift IS
  'Activity-type-level rollup of attributed revenue per co-op dollar. Use for "which activities deliver the best lift?".';
