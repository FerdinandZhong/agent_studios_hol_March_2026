#!/usr/bin/env python3
"""
Load synthetic demo data into customs chatbot Impala tables.

Reads three CSV files from the same directory and inserts rows into:
  - customer_accounts   (from customer_accounts.csv)
  - shipment_tracking   (from shipment_tracking.csv)

Runs post-load verification queries that demonstrate the chatbot's
main query patterns: status lookups, duty balance checks, escalation
triggers, and history lookups.

Usage:
    python load_data_to_impala.py

Update IMPALA_HOST, USERNAME, and PASSWORD before running.
"""

import csv
import sys
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from impala.dbapi import connect

# ---------------------------------------------------------------------------
# Connection parameters — update for your CDP environment
# ---------------------------------------------------------------------------
IMPALA_HOST = 'qzhong-datahub-gateway.qzhong-1.a465-9q4k.cloudera.site'
IMPALA_PORT = 443
USERNAME     = 'qzhong'
PASSWORD     = 'P@ssw0rd.'
DATABASE     = 'customs_chatbot_db'

DATA_DIR = Path(__file__).parent


# ---------------------------------------------------------------------------
# INSERT templates
# ---------------------------------------------------------------------------
CUSTOMER_ACCOUNTS_INSERT = """
INSERT INTO customer_accounts VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
)
"""

SHIPMENT_TRACKING_INSERT = """
INSERT INTO shipment_tracking VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s,
    %s, %s, %s, %s, %s, %s, %s, %s, %s,
    %s, %s, %s, %s, %s, %s
)
"""


# ---------------------------------------------------------------------------
# Row parsers
# ---------------------------------------------------------------------------
def _str_or_none(val: str):
    """Return None for empty/whitespace strings, otherwise stripped string."""
    stripped = val.strip()
    return stripped if stripped else None


def _date_or_none(val: str):
    """Parse YYYY-MM-DD string or return None."""
    stripped = val.strip()
    if not stripped:
        return None
    try:
        return date.fromisoformat(stripped)
    except ValueError:
        return None


def _decimal_or_none(val: str):
    """Parse decimal string or return None."""
    stripped = val.strip()
    if not stripped:
        return None
    try:
        return Decimal(stripped)
    except InvalidOperation:
        return None


def parse_customer_accounts_row(row: dict):
    return (
        _str_or_none(row['customer_id']),
        _str_or_none(row['company_name']),
        _str_or_none(row['contact_name']),
        _str_or_none(row['email']),
        _str_or_none(row['phone']),
        _str_or_none(row['account_type']),
        _date_or_none(row['registration_date']),
        _str_or_none(row['account_status']),
        _str_or_none(row['preferred_language']),
        _str_or_none(row['notes']),
    )


def parse_shipment_tracking_row(row: dict):
    return (
        _str_or_none(row['tracking_id']),
        _str_or_none(row['declaration_id']),
        _str_or_none(row['customer_id']),
        _str_or_none(row['importer_name']),
        _str_or_none(row['hs_code']),
        _str_or_none(row['product_description']),
        _str_or_none(row['country_of_origin']),
        _str_or_none(row['port_of_entry']),
        _str_or_none(row['broker_name']),
        _decimal_or_none(row['quantity']),
        _str_or_none(row['quantity_unit']),
        _decimal_or_none(row['declared_value_usd']),
        _decimal_or_none(row['duty_rate_pct']),
        _decimal_or_none(row['duty_assessed_usd']),
        _decimal_or_none(row['duty_paid_usd']),
        _str_or_none(row['status']),
        _str_or_none(row['location']),
        _date_or_none(row['last_updated']),
        _date_or_none(row['estimated_clearance_date']),
        _date_or_none(row['actual_clearance_date']),
        _str_or_none(row['inspection_type']),
        _str_or_none(row['hold_reason']),
        _str_or_none(row['officer_id']),
        _str_or_none(row['notes']),
    )


# ---------------------------------------------------------------------------
# Master load plan
# ---------------------------------------------------------------------------
LOAD_PLAN = [
    (
        'customer_accounts.csv',
        'customer_accounts',
        CUSTOMER_ACCOUNTS_INSERT,
        parse_customer_accounts_row,
    ),
    (
        'shipment_tracking.csv',
        'shipment_tracking',
        SHIPMENT_TRACKING_INSERT,
        parse_shipment_tracking_row,
    ),
]


# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------
def connect_to_impala():
    configs = [
        {
            'host': IMPALA_HOST, 'port': IMPALA_PORT, 'database': 'default',
            'user': USERNAME, 'password': PASSWORD, 'timeout': 120,
            'use_ssl': True, 'auth_mechanism': 'LDAP',
            'use_http_transport': True,
            'http_path': 'qzhong-datahub/cdp-proxy-api/impala',
        },
        {
            'host': IMPALA_HOST, 'port': IMPALA_PORT, 'database': 'default',
            'user': USERNAME, 'password': PASSWORD, 'timeout': 120,
            'use_ssl': True, 'auth_mechanism': 'PLAIN',
            'use_http_transport': True,
            'http_path': 'qzhong-datahub/cdp-proxy-api/impala',
        },
        {
            'host': IMPALA_HOST, 'port': IMPALA_PORT, 'database': 'default',
            'user': USERNAME, 'password': PASSWORD, 'timeout': 120,
            'use_ssl': True, 'auth_mechanism': 'LDAP',
            'use_http_transport': True,
            'http_path': 'qzhong-datahub/cdp-proxy-api/impala/cliservice',
        },
    ]

    for i, cfg in enumerate(configs, 1):
        try:
            print(f"  Trying config {i} (auth={cfg['auth_mechanism']}, path={cfg['http_path']})...")
            conn = connect(**cfg)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            print(f"  ✓ Connected with config {i}\n")
            return conn, cursor
        except Exception as e:
            print(f"  ✗ Failed: {str(e)[:120]}")

    return None, None


# ---------------------------------------------------------------------------
# CSV loader
# ---------------------------------------------------------------------------
def load_csv(cursor, csv_filename: str, table_name: str, insert_sql: str, parser):
    csv_path = DATA_DIR / csv_filename
    if not csv_path.exists():
        print(f"  ✗ CSV file not found: {csv_path}")
        return 0

    rows_ok = 0
    rows_err = 0
    with open(csv_path, newline='', encoding='utf-8') as fh:
        reader = csv.DictReader(fh)
        for line_no, row in enumerate(reader, 2):
            try:
                params = parser(row)
                cursor.execute(insert_sql.strip(), params)
                rows_ok += 1
            except Exception as e:
                rows_err += 1
                if rows_err <= 3:
                    print(f"  ⚠ Row {line_no} error: {str(e)[:120]}")

    print(f"  Inserted: {rows_ok} rows  |  Errors: {rows_err} rows")
    return rows_ok


# ---------------------------------------------------------------------------
# Post-load verification queries
# ---------------------------------------------------------------------------
VERIFICATION_QUERIES = [
    # --- Row counts ---
    (
        "Row counts",
        """
        SELECT 'customer_accounts' AS tbl, COUNT(*) AS cnt FROM customer_accounts
        UNION ALL
        SELECT 'shipment_tracking', COUNT(*) FROM shipment_tracking
        """,
    ),

    # --- Chatbot Query Pattern 1: Status lookup by tracking ID ---
    (
        "Chatbot Pattern 1 — Status lookup by tracking ID (TRK-2024-08812)",
        """
        SELECT tracking_id, declaration_id, importer_name, status,
               `location`, estimated_clearance_date,
               duty_assessed_usd, duty_paid_usd, hold_reason
        FROM shipment_tracking
        WHERE tracking_id = 'TRK-2024-08812'
        """,
    ),

    # --- Chatbot Query Pattern 2: Held / Seized shipments (escalation trigger) ---
    (
        "Chatbot Pattern 2 — Held and Seized shipments (escalation triggers)",
        """
        SELECT tracking_id, importer_name, status, hold_reason,
               (duty_assessed_usd - duty_paid_usd) AS duty_outstanding_usd
        FROM shipment_tracking
        WHERE status IN ('HELD', 'SEIZED', 'UNDER_APPEAL')
        ORDER BY last_updated DESC
        """,
    ),

    # --- Chatbot Query Pattern 3: Outstanding duty balance for a caller ---
    (
        "Chatbot Pattern 3 — Outstanding duty balances (duty inquiry)",
        """
        SELECT tracking_id, declaration_id, importer_name,
               duty_assessed_usd, duty_paid_usd,
               (duty_assessed_usd - duty_paid_usd) AS duty_outstanding_usd,
               status
        FROM shipment_tracking
        WHERE duty_assessed_usd > duty_paid_usd
          AND status != 'CLEARED'
        ORDER BY duty_outstanding_usd DESC
        """,
    ),

    # --- Chatbot Query Pattern 4: In-transit shipments (status inquiries) ---
    (
        "Chatbot Pattern 4 — Shipments currently in transit",
        """
        SELECT tracking_id, importer_name, port_of_entry, country_of_origin,
               product_description, estimated_clearance_date, `location`
        FROM shipment_tracking
        WHERE status = 'IN_TRANSIT'
        ORDER BY estimated_clearance_date
        """,
    ),

    # --- Chatbot Query Pattern 5: Shipment history for a company ---
    (
        "Chatbot Pattern 5 — Full shipment history for ABC Trading UK Ltd",
        """
        SELECT tracking_id, declaration_id, product_description, status,
               last_updated, duty_assessed_usd, duty_paid_usd
        FROM shipment_tracking
        WHERE importer_name LIKE '%ABC Trading%'
        ORDER BY last_updated DESC
        LIMIT 10
        """,
    ),

    # --- Chatbot Query Pattern 6: Broker performance (for caller context) ---
    (
        "Chatbot Pattern 6 — Shipment count by broker and status",
        """
        SELECT broker_name,
               COUNT(*) AS total_shipments,
               SUM(CASE WHEN status = 'CLEARED' THEN 1 ELSE 0 END) AS cleared,
               SUM(CASE WHEN status IN ('HELD','SEIZED','UNDER_EXAMINATION') THEN 1 ELSE 0 END) AS problem_shipments
        FROM shipment_tracking
        GROUP BY broker_name
        ORDER BY problem_shipments DESC
        """,
    ),
]


def run_verifications(cursor):
    print("\n" + "=" * 70)
    print("Post-Load Verification Queries")
    print("=" * 70)

    for title, sql in VERIFICATION_QUERIES:
        print(f"\n--- {title} ---")
        try:
            cursor.execute(sql.strip())
            rows = cursor.fetchall()
            cols = [desc[0] for desc in cursor.description] if cursor.description else []
            if cols:
                header = " | ".join(f"{c:<30}" for c in cols)
                print("  " + header)
                print("  " + "-" * len(header))
            for row in rows:
                print("  " + " | ".join(f"{str(v):<30}" for v in row))
            if not rows:
                print("  (no rows returned)")
        except Exception as e:
            print(f"  ✗ Query failed: {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 70)
    print("Customs Chatbot DB — Load Data")
    print("=" * 70)
    print(f"Host    : {IMPALA_HOST}:{IMPALA_PORT}")
    print(f"User    : {USERNAME}")
    print(f"Database: {DATABASE}")
    print(f"Data dir: {DATA_DIR}\n")

    conn, cursor = connect_to_impala()
    if not conn:
        print("\n✗ All connection attempts failed. Check host/credentials.")
        sys.exit(1)

    try:
        cursor.execute(f"USE {DATABASE}")
        print(f"✓ Using database: {DATABASE}\n")

        for csv_filename, table_name, insert_sql, parser in LOAD_PLAN:
            print(f"Loading {csv_filename} → {table_name} ...")
            load_csv(cursor, csv_filename, table_name, insert_sql, parser)
            print()

        run_verifications(cursor)
        print("\n✓ Data load complete.")

    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
