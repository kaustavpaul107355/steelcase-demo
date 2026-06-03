-- =====================================================================
-- COMPASS Demo — Silver layer DDL
-- Cleansed, typed, conformed. SCD-2 on dim_dealer.
-- =====================================================================

CREATE SCHEMA IF NOT EXISTS steelcase_demo.silver;

-- ---------------------------------------------------------------------
-- silver.dealer (SCD-2)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS steelcase_demo.silver.dealer (
  dealer_id                STRING NOT NULL,
  salesforce_account_id    STRING NOT NULL,
  dealer_name              STRING NOT NULL,
  region_id                STRING NOT NULL,
  country                  STRING NOT NULL,
  tier                     STRING NOT NULL,
  sales_rep_id             STRING,
  effective_from           DATE NOT NULL,
  effective_to             DATE,
  is_current               BOOLEAN NOT NULL,
  CONSTRAINT dealer_tier_valid CHECK (tier IN ('Platinum','Gold','Silver','Authorized'))
) USING DELTA
PARTITIONED BY (is_current);

-- ---------------------------------------------------------------------
-- silver.coop_allocation
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS steelcase_demo.silver.coop_allocation (
  allocation_id            STRING NOT NULL,
  dealer_id                STRING NOT NULL,
  program_id               STRING NOT NULL,
  fiscal_year              STRING NOT NULL,
  allocated_usd            DECIMAL(14,2) NOT NULL,
  allocation_date          DATE NOT NULL,
  expiration_date          DATE NOT NULL,
  allocation_source        STRING NOT NULL,
  CONSTRAINT alloc_amount_positive CHECK (allocated_usd > 0),
  CONSTRAINT alloc_dates_ordered CHECK (expiration_date >= allocation_date)
) USING DELTA
PARTITIONED BY (fiscal_year);

-- ---------------------------------------------------------------------
-- silver.coop_claim
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS steelcase_demo.silver.coop_claim (
  claim_id                 STRING NOT NULL,
  dealer_id                STRING NOT NULL,
  program_id               STRING NOT NULL,
  activity_type_id         STRING NOT NULL,
  preapproval_id           STRING,
  submission_date          DATE NOT NULL,
  requested_amount_usd     DECIMAL(12,2) NOT NULL,
  approved_amount_usd      DECIMAL(12,2),
  paid_amount_usd          DECIMAL(12,2),
  status                   STRING NOT NULL,
  brand_compliance_score   INT,
  reviewer_id              STRING,
  decision_date            DATE,
  payment_date             DATE,
  claim_doc_uri            STRING,
  fiscal_year              STRING NOT NULL,
  CONSTRAINT claim_status_valid CHECK (status IN ('Draft','Submitted','Under_Review','Approved','Rejected','Paid','Expired')),
  CONSTRAINT claim_amount_positive CHECK (requested_amount_usd > 0),
  CONSTRAINT claim_paid_le_approved CHECK (paid_amount_usd IS NULL OR approved_amount_usd IS NULL OR paid_amount_usd <= approved_amount_usd)
) USING DELTA
PARTITIONED BY (fiscal_year);

-- ---------------------------------------------------------------------
-- silver.sell_through_order
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS steelcase_demo.silver.sell_through_order (
  order_line_id            STRING NOT NULL,
  order_id                 STRING NOT NULL,
  dealer_id                STRING NOT NULL,
  product_family           STRING NOT NULL,
  order_date               DATE NOT NULL,
  ship_date                DATE,
  net_revenue_usd          DECIMAL(12,2) NOT NULL,
  fiscal_year              STRING NOT NULL,
  CONSTRAINT order_amount_positive CHECK (net_revenue_usd >= 0)
) USING DELTA
PARTITIONED BY (fiscal_year);

-- ---------------------------------------------------------------------
-- silver.marketing_event
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS steelcase_demo.silver.marketing_event (
  event_id                 STRING NOT NULL,
  dealer_id                STRING NOT NULL,
  activity_type_id         STRING NOT NULL,
  start_date               DATE NOT NULL,
  end_date                 DATE,
  attendees                INT,
  event_cost_usd           DECIMAL(12,2),
  claim_id_nullable        STRING,
  fiscal_year              STRING NOT NULL
) USING DELTA
PARTITIONED BY (fiscal_year);

-- ---------------------------------------------------------------------
-- silver.program / silver.activity_type / silver.region (conformed)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS steelcase_demo.silver.program (
  program_id               STRING NOT NULL,
  program_name             STRING NOT NULL,
  fiscal_year              STRING NOT NULL,
  allocation_method        STRING,
  default_cofund_pct       DECIMAL(5,2),
  program_start            DATE,
  program_end              DATE
) USING DELTA;

CREATE TABLE IF NOT EXISTS steelcase_demo.silver.activity_type (
  activity_type_id         STRING NOT NULL,
  category                 STRING NOT NULL,
  activity_name            STRING NOT NULL,
  default_cofund_pct       DECIMAL(5,2),
  requires_preapproval     BOOLEAN NOT NULL,
  preapproval_threshold_usd DECIMAL(12,2)
) USING DELTA;

CREATE TABLE IF NOT EXISTS steelcase_demo.silver.region (
  region_id                STRING NOT NULL,
  region                   STRING NOT NULL,
  sub_region               STRING,
  default_currency         STRING
) USING DELTA;

-- ---------------------------------------------------------------------
-- silver.fiscal_calendar (Steelcase fiscal year, Mar–Feb)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS steelcase_demo.silver.fiscal_calendar (
  date_key                 DATE NOT NULL,
  fiscal_year              STRING NOT NULL,
  fiscal_period            STRING NOT NULL,    -- P1..P12
  fiscal_week              INT NOT NULL,
  fiscal_quarter           STRING NOT NULL     -- Q1..Q4
) USING DELTA;
