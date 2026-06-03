"""Hydrate compass.v_dealer + compass.v_coop_utilization_today by pulling from UC.

This is a one-shot hydrate (not continuous sync). For the demo's static FY26 data
this is sufficient; a future iteration can replace this with managed synced tables
once the UC catalog binding for the autoscale Lakebase project is set up.
"""
import os
from databricks.sdk import WorkspaceClient
import psycopg

os.environ["DATABRICKS_CONFIG_PROFILE"] = "fe-vm-classic-stable-1zia5t-kp"
HOST = "ep-raspy-credit-d2yhs2ud.database.us-east-1.cloud.databricks.com"
USER = "kaustav.paul@databricks.com"
DB = "databricks_postgres"
INSTANCE = "compass-lakebase-prov"

import uuid
w = WorkspaceClient()
cred = w.database.generate_database_credential(
    request_id=str(uuid.uuid4()),
    instance_names=[INSTANCE],
)

# Pull data from UC via SQL warehouse
WH = "e6dc9b218651c48a"  # KP SQL DWH

DEALER_SQL = """
SELECT dealer_id, dealer_name, salesforce_account_id, region_id, country, tier, sales_rep_id
FROM classic_stable_1zia5t_kp_catalog.compass_gold.dim_dealer
"""

UTIL_SQL = """
SELECT dealer_id, program_id, fiscal_year, fiscal_period, date_key,
       CAST(allocated_usd AS decimal(14,2)) AS allocated_usd,
       CAST(committed_usd AS decimal(14,2)) AS committed_usd,
       CAST(approved_usd  AS decimal(14,2)) AS approved_usd,
       CAST(paid_usd      AS decimal(14,2)) AS paid_usd,
       CAST(unused_usd    AS decimal(14,2)) AS unused_usd,
       days_to_expiration
FROM classic_stable_1zia5t_kp_catalog.compass_gold.fact_coop_utilization_daily
WHERE date_key = (SELECT max(date_key) FROM classic_stable_1zia5t_kp_catalog.compass_gold.fact_coop_utilization_daily)
"""

def fetch(sql):
    r = w.statement_execution.execute_statement(
        warehouse_id=WH, statement=sql, wait_timeout="50s"
    )
    sid = r.statement_id
    # poll
    while r.status.state.value in ("PENDING", "RUNNING"):
        r = w.statement_execution.get_statement(sid)
    if r.status.state.value != "SUCCEEDED":
        raise RuntimeError(f"SQL failed: {r.status.error}")
    cols = [c.name for c in r.manifest.schema.columns]
    data = list(r.result.data_array or [])
    # if chunked, fetch remaining chunks
    chunk_idx = (r.result.next_chunk_index if r.result else None)
    while chunk_idx is not None:
        chunk = w.statement_execution.get_statement_result_chunk_n(sid, chunk_idx)
        data += list(chunk.data_array or [])
        chunk_idx = chunk.next_chunk_index
    return cols, data

print("[hydrate] pulling dim_dealer from UC...")
dcols, ddata = fetch(DEALER_SQL)
print(f"  {len(ddata)} rows, cols={dcols}")

print("[hydrate] pulling fact_coop_utilization_daily (latest snapshot)...")
ucols, udata = fetch(UTIL_SQL)
print(f"  {len(udata)} rows, cols={ucols}")

conn_str = f"host={HOST} dbname={DB} user={USER} password={cred.token} sslmode=require"
with psycopg.connect(conn_str) as conn:
    conn.autocommit = False
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS compass.v_dealer (
              dealer_id              TEXT PRIMARY KEY,
              dealer_name            TEXT NOT NULL,
              salesforce_account_id  TEXT,
              region_id              TEXT NOT NULL,
              country                TEXT NOT NULL,
              tier                   TEXT NOT NULL,
              sales_rep_id           TEXT,
              synced_at              TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            CREATE INDEX IF NOT EXISTS ix_v_dealer_region ON compass.v_dealer(region_id);

            CREATE TABLE IF NOT EXISTS compass.v_coop_utilization_today (
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
            CREATE INDEX IF NOT EXISTS ix_v_util_unused ON compass.v_coop_utilization_today (unused_usd DESC);
        """)
        cur.execute("TRUNCATE compass.v_dealer, compass.v_coop_utilization_today")
        # Insert dealer rows
        with cur.copy("COPY compass.v_dealer (dealer_id, dealer_name, salesforce_account_id, region_id, country, tier, sales_rep_id) FROM STDIN") as copy:
            for row in ddata:
                copy.write_row(row)
        # Insert util rows
        with cur.copy("COPY compass.v_coop_utilization_today (dealer_id, program_id, fiscal_year, fiscal_period, date_key, allocated_usd, committed_usd, approved_usd, paid_usd, unused_usd, days_to_expiration) FROM STDIN") as copy:
            for row in udata:
                copy.write_row(row)
    conn.commit()
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM compass.v_dealer")
        print("[verify] compass.v_dealer rows:", cur.fetchone()[0])
        cur.execute("SELECT count(*) FROM compass.v_coop_utilization_today")
        print("[verify] compass.v_coop_utilization_today rows:", cur.fetchone()[0])
        cur.execute("SELECT max(date_key) FROM compass.v_coop_utilization_today")
        print("[verify] util latest date_key:", cur.fetchone()[0])
        cur.execute("""
            SELECT d.dealer_id, d.dealer_name, ROUND(u.unused_usd, 2) AS unused
            FROM compass.v_coop_utilization_today u
            JOIN compass.v_dealer d USING (dealer_id)
            WHERE d.region_id = 'RGN-AMER-EAST' AND u.fiscal_year = 'FY26'
            ORDER BY u.unused_usd DESC LIMIT 3
        """)
        print("[verify] top 3 unused (AMER East FY26):")
        for r in cur.fetchall():
            print(f"  {r[0]}  {r[1][:40]:40s}  ${r[2]:,}")
