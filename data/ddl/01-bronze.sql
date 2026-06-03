-- =====================================================================
-- COMPASS Demo — Bronze layer DDL
-- Catalog: steelcase_demo  Schema: bronze
-- All bronze tables land raw, append-only, with ingestion metadata.
-- =====================================================================

CREATE CATALOG IF NOT EXISTS steelcase_demo;
CREATE SCHEMA IF NOT EXISTS steelcase_demo.bronze;

-- ---------------------------------------------------------------------
-- Salesforce dealer master (via Lakeflow Connect)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS steelcase_demo.bronze.sfdc_account (
  Id                       STRING,
  Name                     STRING,
  BillingCountry           STRING,
  BillingState             STRING,
  Tier__c                  STRING,
  Region__c                STRING,
  Sales_Rep__c             STRING,
  Dealer_External_Id__c    STRING,    -- custom field; demo's stable dealer_id (D-04711, ...)
  IsDeleted                BOOLEAN,
  LastModifiedDate         TIMESTAMP,
  _ingest_ts               TIMESTAMP,
  _source_file             STRING
) USING DELTA
TBLPROPERTIES (delta.enableChangeDataFeed = true);

-- ---------------------------------------------------------------------
-- ERP sell-through orders (via Lakeflow Connect or batch land)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS steelcase_demo.bronze.erp_sales_order (
  order_id                 STRING,
  order_line_id            STRING,
  dealer_external_id       STRING,
  product_family           STRING,
  order_date               DATE,
  ship_date                DATE,
  net_revenue_usd          DECIMAL(12,2),
  currency                 STRING,
  _ingest_ts               TIMESTAMP,
  _source_file             STRING
) USING DELTA;

-- ---------------------------------------------------------------------
-- Co-op portal claim exports (JSON via Auto Loader)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS steelcase_demo.bronze.portal_claims (
  claim_id                 STRING,
  dealer_external_id       STRING,
  program_code             STRING,
  activity_code            STRING,
  preapproval_id           STRING,
  submission_date          DATE,
  requested_amount         DECIMAL(12,2),
  approved_amount          DECIMAL(12,2),
  paid_amount              DECIMAL(12,2),
  status                   STRING,
  brand_compliance_score   INT,
  reviewer_id              STRING,
  decision_date            DATE,
  payment_date             DATE,
  claim_doc_uri            STRING,
  raw_payload              STRING,    -- full JSON for traceability
  _ingest_ts               TIMESTAMP,
  _source_file             STRING
) USING DELTA;

-- ---------------------------------------------------------------------
-- Allocation CSVs (per region per fiscal year)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS steelcase_demo.bronze.allocation_csv (
  allocation_id            STRING,
  dealer_external_id       STRING,
  program_code             STRING,
  fiscal_year              STRING,
  allocated_usd            DECIMAL(14,2),
  allocation_date          DATE,
  expiration_date          DATE,
  allocation_source        STRING,
  _ingest_ts               TIMESTAMP,
  _source_file             STRING
) USING DELTA;

-- ---------------------------------------------------------------------
-- Marketing event registrations (CSV/JSON via Auto Loader)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS steelcase_demo.bronze.event_registration (
  event_id                 STRING,
  dealer_external_id       STRING,
  activity_code            STRING,
  start_date               DATE,
  end_date                 DATE,
  attendees                INT,
  event_cost_usd           DECIMAL(12,2),
  claim_id                 STRING,
  _ingest_ts               TIMESTAMP,
  _source_file             STRING
) USING DELTA;

-- ---------------------------------------------------------------------
-- Reference data (lookup tables — small)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS steelcase_demo.bronze.ref_program (
  program_code             STRING,
  program_name             STRING,
  fiscal_year              STRING,
  allocation_method        STRING,
  default_cofund_pct       DECIMAL(5,2),
  program_start            DATE,
  program_end              DATE,
  _ingest_ts               TIMESTAMP
) USING DELTA;

CREATE TABLE IF NOT EXISTS steelcase_demo.bronze.ref_activity_type (
  activity_code            STRING,
  category                 STRING,
  activity_name            STRING,
  default_cofund_pct       DECIMAL(5,2),
  requires_preapproval     BOOLEAN,
  preapproval_threshold_usd DECIMAL(12,2),
  _ingest_ts               TIMESTAMP
) USING DELTA;

CREATE TABLE IF NOT EXISTS steelcase_demo.bronze.ref_region (
  region_id                STRING,
  region                   STRING,
  sub_region               STRING,
  default_currency         STRING,
  country_list             STRING,
  _ingest_ts               TIMESTAMP
) USING DELTA;
