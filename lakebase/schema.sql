-- =====================================================================
-- COMPASS Demo — Lakebase (managed Postgres) schema
-- Holds OLTP state for the app: chat memory, approvals, nudge campaigns,
-- saved views, and per-user preferences. Synced (read-only) views from
-- UC gold tables sit alongside.
-- =====================================================================

CREATE SCHEMA IF NOT EXISTS compass;
SET search_path TO compass, public;

-- ---------------------------------------------------------------------
-- app_user
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS app_user (
  user_id              TEXT PRIMARY KEY,            -- OAuth subject (databricks user id)
  email                TEXT NOT NULL UNIQUE,
  display_name         TEXT NOT NULL,
  role                 TEXT NOT NULL                -- 'channel_mgr','rmd','director','finance','dealer'
                       CHECK (role IN ('channel_mgr','rmd','director','finance','dealer')),
  region_id            TEXT,                        -- e.g. RGN-AMER-EAST; null = global
  default_tier_filter  TEXT,                        -- 'Platinum','Gold','Silver','Authorized','All'
  dealer_id            TEXT,                        -- non-null only when role = 'dealer'; scopes the user to one dealer
  created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_login_at        TIMESTAMPTZ,
  CHECK ((role = 'dealer') = (dealer_id IS NOT NULL))
);

-- ---------------------------------------------------------------------
-- chat_session  &  chat_turn
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS chat_session (
  session_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id              TEXT NOT NULL REFERENCES app_user(user_id),
  started_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_active_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  title                TEXT,                        -- auto-summarized
  supervisor_state     JSONB DEFAULT '{}'::jsonb    -- compressed agent memory
);
CREATE INDEX IF NOT EXISTS ix_chat_session_user_active
  ON chat_session(user_id, last_active_at DESC);

CREATE TABLE IF NOT EXISTS chat_turn (
  turn_id              BIGSERIAL PRIMARY KEY,
  session_id           UUID NOT NULL REFERENCES chat_session(session_id) ON DELETE CASCADE,
  turn_index           INT NOT NULL,
  role                 TEXT NOT NULL                -- 'user','assistant','tool'
                       CHECK (role IN ('user','assistant','tool')),
  content              TEXT NOT NULL,
  tool_name            TEXT,                        -- nullable; populated for tool turns
  tool_payload_json    JSONB,
  trace_id             TEXT,                        -- MLflow trace id
  latency_ms           INT,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_chat_turn_session_idx
  ON chat_turn(session_id, turn_index);
CREATE INDEX IF NOT EXISTS ix_chat_turn_trace
  ON chat_turn(trace_id);

-- ---------------------------------------------------------------------
-- claim_review (the approval workflow store)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS claim_review (
  claim_id             TEXT PRIMARY KEY,            -- mirrors UC.silver.coop_claim.claim_id
  dealer_id            TEXT NOT NULL,
  status               TEXT NOT NULL                -- 'Pending','Approved','Rejected','PaidStaged'
                       CHECK (status IN ('Pending','Approved','Rejected','PaidStaged')),
  reviewer_user_id     TEXT REFERENCES app_user(user_id),
  decision_at          TIMESTAMPTZ,
  reviewer_note        TEXT,
  rejection_code       TEXT,                        -- one of: MISSING_PREAPPROVAL, TIER_INELIGIBLE, OFF_BRAND, OUT_OF_REGION, DOC_INCOMPLETE, DOUBLE_DIP, OTHER
  brand_check_json     JSONB,                       -- creative-pod scoring breakdown
  created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_claim_review_status
  ON claim_review(status, decision_at);
CREATE INDEX IF NOT EXISTS ix_claim_review_reviewer
  ON claim_review(reviewer_user_id, decision_at);

-- ---------------------------------------------------------------------
-- nudge_campaign  &  nudge_recipient
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS nudge_campaign (
  campaign_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_code        TEXT UNIQUE,                  -- human-readable, e.g. nudge-2026-Q4-AE-001
  created_by           TEXT NOT NULL REFERENCES app_user(user_id),
  created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
  template_id          TEXT NOT NULL,                -- 'Q4-Fast-Track-Digital','Mid-Year-Check-In', etc.
  dealer_filter_json   JSONB NOT NULL,               -- the filter that resolved to the recipient list
  deadline             DATE,
  status               TEXT NOT NULL                 -- 'Draft','Queued','Sent','Cancelled'
                       CHECK (status IN ('Draft','Queued','Sent','Cancelled')),
  notes                TEXT
);

CREATE TABLE IF NOT EXISTS nudge_recipient (
  campaign_id          UUID NOT NULL REFERENCES nudge_campaign(campaign_id) ON DELETE CASCADE,
  dealer_id            TEXT NOT NULL,
  dealer_email         TEXT NOT NULL,
  personalization_json JSONB,                        -- {"unused_balance_usd": 47100.0, "expiration_date":"2027-02-28", ...}
  email_status         TEXT NOT NULL DEFAULT 'Pending'
                       CHECK (email_status IN ('Pending','Queued','Sent','Opened','Clicked','Bounced','Failed')),
  sent_at              TIMESTAMPTZ,
  opened_at            TIMESTAMPTZ,
  PRIMARY KEY (campaign_id, dealer_id)
);
CREATE INDEX IF NOT EXISTS ix_nudge_recipient_campaign_status
  ON nudge_recipient(campaign_id, email_status);

-- ---------------------------------------------------------------------
-- saved_view
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS saved_view (
  view_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id              TEXT NOT NULL REFERENCES app_user(user_id),
  name                 TEXT NOT NULL,
  description          TEXT,
  filter_payload       JSONB NOT NULL,                -- {metric_view, filters, group_by, ...}
  pinned               BOOLEAN NOT NULL DEFAULT FALSE,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_used_at         TIMESTAMPTZ,
  UNIQUE (user_id, name)
);
CREATE INDEX IF NOT EXISTS ix_saved_view_user_pinned
  ON saved_view(user_id, pinned, last_used_at DESC);

-- ---------------------------------------------------------------------
-- user_preference (kv)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_preference (
  user_id              TEXT NOT NULL REFERENCES app_user(user_id),
  pref_key             TEXT NOT NULL,
  pref_value_json      JSONB NOT NULL,
  updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, pref_key)
);

-- ---------------------------------------------------------------------
-- audit_log (write-side actions taken via agent tools)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_log (
  audit_id             BIGSERIAL PRIMARY KEY,
  occurred_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  user_id              TEXT REFERENCES app_user(user_id),
  session_id           UUID REFERENCES chat_session(session_id),
  action               TEXT NOT NULL,               -- 'create_nudge_campaign','advance_claim','save_view',...
  target_type          TEXT,                        -- 'nudge_campaign','claim','saved_view'
  target_id            TEXT,
  payload_json         JSONB,
  trace_id             TEXT
);
CREATE INDEX IF NOT EXISTS ix_audit_log_user_time
  ON audit_log(user_id, occurred_at DESC);

-- ---------------------------------------------------------------------
-- SYNCED VIEWS from UC (created via reverse-ETL / synced tables)
-- The actual sync mechanism is configured in DAB; the table shapes
-- below are what the app reads.
-- ---------------------------------------------------------------------

-- v_dealer  <-  steelcase_demo.gold.dim_dealer
CREATE TABLE IF NOT EXISTS v_dealer (
  dealer_id              TEXT PRIMARY KEY,
  dealer_name            TEXT NOT NULL,
  salesforce_account_id  TEXT,
  region_id              TEXT NOT NULL,
  country                TEXT NOT NULL,
  tier                   TEXT NOT NULL,
  sales_rep_id           TEXT,
  synced_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_v_dealer_region ON v_dealer(region_id);

-- v_coop_utilization_today  <-  latest snapshot of fact_coop_utilization_daily
CREATE TABLE IF NOT EXISTS v_coop_utilization_today (
  dealer_id              TEXT NOT NULL,
  program_id             TEXT NOT NULL,
  fiscal_year            TEXT NOT NULL,
  fiscal_period          TEXT NOT NULL,
  date_key               DATE NOT NULL,
  allocated_usd          NUMERIC(14,2) NOT NULL,
  committed_usd          NUMERIC(14,2) NOT NULL,
  approved_usd           NUMERIC(14,2) NOT NULL,
  paid_usd               NUMERIC(14,2) NOT NULL,
  unused_usd             NUMERIC(14,2) NOT NULL,
  days_to_expiration     INT,
  synced_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (dealer_id, program_id, fiscal_year)
);
CREATE INDEX IF NOT EXISTS ix_v_util_unused
  ON v_coop_utilization_today (unused_usd DESC);

-- ---------------------------------------------------------------------
-- Permissions (rough — refine for production)
-- ---------------------------------------------------------------------
-- App service principal gets full DML on the compass schema.
-- Read-only role (`compass_reader`) for ad-hoc queries.
-- Synced tables are written by the sync process and read by the app.
-- ---------------------------------------------------------------------
