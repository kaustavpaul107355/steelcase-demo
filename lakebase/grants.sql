-- =====================================================================
-- COMPASS Demo — Lakebase grants
-- Apply AFTER the Databricks App is created (so the app's service principal
-- exists and can be GRANTed to). Idempotent; safe to re-run.
--
-- Usage:
--   psql ... -v app_sp_id=<service-principal-uuid> -f lakebase/grants.sql
--
-- :app_sp_id is the App's service principal id. The Postgres role name
-- Databricks creates for an App SP is the SP id verbatim, e.g.
-- 'aec5be3d-de3c-404c-8e60-feed0f265fd3'.
-- =====================================================================

\set ON_ERROR_STOP on
SET search_path TO compass, public;

-- ---------------------------------------------------------------------
-- Roles
-- ---------------------------------------------------------------------
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'compass_app') THEN
    CREATE ROLE compass_app NOLOGIN;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'compass_reader') THEN
    CREATE ROLE compass_reader NOLOGIN;
  END IF;
END $$;

-- ---------------------------------------------------------------------
-- compass_app: full DML on the compass schema (app SP runs the BFF)
-- ---------------------------------------------------------------------
GRANT USAGE ON SCHEMA compass TO compass_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA compass TO compass_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA compass TO compass_app;

ALTER DEFAULT PRIVILEGES IN SCHEMA compass
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO compass_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA compass
  GRANT USAGE, SELECT ON SEQUENCES TO compass_app;

-- ---------------------------------------------------------------------
-- compass_reader: read-only ad-hoc queries (humans + audit jobs)
-- ---------------------------------------------------------------------
GRANT USAGE ON SCHEMA compass TO compass_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA compass TO compass_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA compass
  GRANT SELECT ON TABLES TO compass_reader;

-- ---------------------------------------------------------------------
-- Bind the App SP to compass_app.
-- Run with `-v app_sp_id=<uuid>` once the Databricks App exists.
-- psql does NOT substitute :variables inside $$ ... $$ dollar-quoting, so
-- the SP id is shuttled into the DO block via a session GUC.
-- ---------------------------------------------------------------------
SELECT set_config('compass.app_sp_id', :'app_sp_id', false);

DO $$
DECLARE
  app_sp text := NULLIF(current_setting('compass.app_sp_id', true), '');
BEGIN
  IF app_sp IS NULL THEN
    RAISE NOTICE 'app_sp_id not provided; skipping App SP role grant.';
  ELSE
    -- The role for a Databricks App SP is auto-created by Lakebase when
    -- the SP first authenticates. Create a placeholder so the GRANT can
    -- land idempotently even before the SP has connected once.
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = app_sp) THEN
      EXECUTE format('CREATE ROLE %I LOGIN', app_sp);
    END IF;
    EXECUTE format('GRANT compass_app TO %I', app_sp);
    RAISE NOTICE 'Granted compass_app to %', app_sp;
  END IF;
END $$;

-- ---------------------------------------------------------------------
-- RLS note
-- ---------------------------------------------------------------------
-- The COMPASS BFF enforces region/tier/user scoping in its SQL queries
-- (WHERE clauses join compass.app_user on the OAuth subject). True Postgres
-- RLS (`ENABLE ROW LEVEL SECURITY` + per-table policies) is intentionally
-- not turned on for the demo because:
--   1. The app already speaks a single SP identity, so per-user RLS would
--      require SET LOCAL session vars on every checkout — extra surface.
--   2. The same scoping logic must run in `lite` mode (no Lakebase), so
--      keeping it in the BFF is the single source of truth.
-- Revisit if a future production iteration wants defense-in-depth.

-- ---------------------------------------------------------------------
-- Verify
-- ---------------------------------------------------------------------
\echo Roles after apply:
SELECT rolname, rolcanlogin
FROM pg_roles
WHERE rolname IN ('compass_app','compass_reader')
   OR rolname = :'app_sp_id'
ORDER BY rolname;

\echo Grants on compass schema:
SELECT grantee, privilege_type
FROM information_schema.table_privileges
WHERE table_schema = 'compass'
  AND grantee IN ('compass_app','compass_reader')
GROUP BY grantee, privilege_type
ORDER BY grantee, privilege_type;
