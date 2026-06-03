-- =====================================================================
-- COMPASS Demo — Lakebase seed data
-- Minimal rows to make the app demo'able the moment it boots.
-- =====================================================================

SET search_path TO compass, public;

-- ---------------------------------------------------------------------
-- Users
-- ---------------------------------------------------------------------
INSERT INTO app_user (user_id, email, display_name, role, region_id, default_tier_filter, dealer_id, last_login_at)
VALUES
  ('U-MAYA-001',  'maya.demo@steelcase-demo.invalid',   'Maya Chen',     'channel_mgr', 'RGN-AMER-EAST', 'All', NULL,      now()),
  ('U-ELIOT-001', 'eliot.demo@steelcase-demo.invalid',  'Eliot Vargas',  'director',    NULL,            'All', NULL,      now()),
  ('U-PRIYA-001', 'priya.demo@pivot-workplace.invalid', 'Priya Shah',    'dealer',      'RGN-AMER-EAST', NULL,  'D-04711', now()),
  ('U-FIN-001',   'jordan.demo@steelcase-demo.invalid', 'Jordan Patel',  'finance',     NULL,            'All', NULL,      now()),
  ('U-RMD-EM-001','renske.demo@steelcase-demo.invalid', 'Renske de Boer','rmd',         'RGN-EMEA-NORTH','All', NULL,      now()),
  ('U-KAUSTAV-001','kaustav.paul@databricks.com',       'Kaustav Paul',  'channel_mgr', 'RGN-AMER-EAST', 'All', NULL,      now())
ON CONFLICT (user_id) DO NOTHING;

-- ---------------------------------------------------------------------
-- Pre-warm chat session for Maya (so the app opens "warm")
-- ---------------------------------------------------------------------
INSERT INTO chat_session (session_id, user_id, started_at, last_active_at, title)
VALUES
  ('11111111-1111-1111-1111-111111111111', 'U-MAYA-001',
   now() - INTERVAL '2 days', now() - INTERVAL '2 days',
   'Q3 mid-cycle review')
ON CONFLICT (session_id) DO NOTHING;

-- ---------------------------------------------------------------------
-- Saved views for Maya
-- ---------------------------------------------------------------------
INSERT INTO saved_view (view_id, user_id, name, description, filter_payload, pinned, last_used_at)
VALUES
  ('a1111111-aaaa-1111-aaaa-111111111111', 'U-MAYA-001',
   'Q3 — Top 20 dealers by utilization',
   'Mid-quarter check on the top utilizers; used in monthly RMD readout.',
   '{"metric_view":"coop_program_metrics","dimensions":["dealer_name","tier"],"measures":["utilization_rate","paid_usd"],"filters":{"region":"AMER","sub_region":"East","fiscal_year":"FY26","fiscal_quarter":"Q3"},"sort":[{"measure":"utilization_rate","direction":"desc","limit":20}]}'::jsonb,
   TRUE, now() - INTERVAL '40 days'),

  ('a2222222-aaaa-2222-aaaa-222222222222', 'U-MAYA-001',
   'YTD claim approval cycle time',
   'Pulled for the QBR; track p50/p90 cycle time YTD.',
   '{"metric_view":"claim_lifecycle","dimensions":["activity_category"],"measures":["cycle_time_days_p50","cycle_time_days_p90","first_pass_approval_rate"],"filters":{"region":"AMER","sub_region":"East","fiscal_year":"FY26"}}'::jsonb,
   TRUE, now() - INTERVAL '12 days'),

  ('a3333333-aaaa-3333-aaaa-333333333333', 'U-MAYA-001',
   'High-balance Silver dealers',
   'Silver dealers with balance > $20K and < 120 days to expiration.',
   '{"metric_view":"forfeiture_risk","dimensions":["dealer_name","tier","days_to_expiration"],"measures":["unused_balance_usd","expected_forfeit_usd"],"filters":{"region":"AMER","sub_region":"East","tier":"Silver","unused_balance_usd_gt":20000,"days_to_expiration_lt":120}}'::jsonb,
   FALSE, now() - INTERVAL '90 days')
ON CONFLICT (user_id, name) DO NOTHING;

-- ---------------------------------------------------------------------
-- Pending claims in approval queue (5 — matches the click-script header)
-- ---------------------------------------------------------------------
-- Four of these are hero-cohort dealers (D-04711..) so the click-script
-- "are any at-risk dealers also in the approval queue?" turn returns 4.
INSERT INTO claim_review (claim_id, dealer_id, status, brand_check_json, created_at, updated_at)
VALUES
  ('CL-FY26-009842', 'D-04711', 'Pending', '{"score":78,"logo":18,"color":17,"typography":12,"photo":15,"voice":16}'::jsonb, now() - INTERVAL '2 days', now() - INTERVAL '2 days'),
  ('CL-FY26-009851', 'D-04713', 'Pending', '{"score":82,"logo":19,"color":17,"typography":13,"photo":17,"voice":16}'::jsonb, now() - INTERVAL '3 days', now() - INTERVAL '3 days'),
  ('CL-FY26-009862', 'D-04718', 'Pending', '{"score":71,"logo":16,"color":15,"typography":12,"photo":14,"voice":14}'::jsonb, now() - INTERVAL '1 days', now() - INTERVAL '1 days'),
  ('CL-FY26-009873', 'D-04725', 'Pending', '{"score":88,"logo":20,"color":18,"typography":14,"photo":18,"voice":18}'::jsonb, now() - INTERVAL '4 days', now() - INTERVAL '4 days'),
  ('CL-FY26-009884', 'D-01100', 'Pending', '{"score":65,"logo":15,"color":13,"typography":11,"photo":13,"voice":13}'::jsonb, now() - INTERVAL '5 days', now() - INTERVAL '5 days')
ON CONFLICT (claim_id) DO NOTHING;

-- ---------------------------------------------------------------------
-- Default user preferences
-- ---------------------------------------------------------------------
INSERT INTO user_preference (user_id, pref_key, pref_value_json)
VALUES
  ('U-MAYA-001', 'home_layout', '{"left":"chat","right":"approval_queue","sidebar":["saved_views","nudge_campaigns"]}'::jsonb),
  ('U-MAYA-001', 'date_format', '"YYYY-MM-DD"'::jsonb),
  ('U-MAYA-001', 'currency_display', '"USD"'::jsonb),
  ('U-ELIOT-001','home_layout', '{"left":"chat","right":"saved_views","sidebar":["pinned_metrics"]}'::jsonb)
ON CONFLICT (user_id, pref_key) DO NOTHING;
