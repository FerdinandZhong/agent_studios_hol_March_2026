#!/usr/bin/env python3
"""
Create customs chatbot tables in Impala (Cloudera Data Warehouse).

Creates two tables in the customs_chatbot_db database:
  - customer_accounts  : Importer / broker account registry
  - shipment_tracking  : Live and historical shipment status records

Usage:
    python create_impala_table.py

Update IMPALA_HOST, USERNAME, and PASSWORD before running.
"""

import sys
from impala.dbapi import connect

# ---------------------------------------------------------------------------
# Connection parameters — update for your CDP environment
# ---------------------------------------------------------------------------
IMPALA_HOST = 'qzhong-datahub-gateway.qzhong-1.a465-9q4k.cloudera.site'
IMPALA_PORT = 443
USERNAME     = 'qzhong'
PASSWORD     = 'P@ssw0rd.'
DATABASE     = 'customs_chatbot_db'

# ---------------------------------------------------------------------------
# DDL statements
# ---------------------------------------------------------------------------
CREATE_DATABASE_SQL = f"""
CREATE DATABASE IF NOT EXISTS {DATABASE}
COMMENT 'Customs Call Centre Chatbot demo data — CAI Studio workflow'
"""

DDL_STATEMENTS = [
    # -----------------------------------------------------------------------
    # 1. customer_accounts
    # -----------------------------------------------------------------------
    ("DROP TABLE IF EXISTS customer_accounts", "Dropping customer_accounts"),
    ("""
CREATE TABLE customer_accounts (
    customer_id          STRING  COMMENT 'Unique customer identifier (CUST-NNNN)',
    company_name         STRING  COMMENT 'Registered company name',
    contact_name         STRING  COMMENT 'Primary contact person',
    email                STRING  COMMENT 'Contact email address',
    phone                STRING  COMMENT 'Contact phone number',
    account_type         STRING  COMMENT 'IMPORTER | BROKER | EXPORTER',
    registration_date    DATE    COMMENT 'Date the account was registered',
    account_status       STRING  COMMENT 'ACTIVE | SUSPENDED | UNDER_REVIEW | CLOSED',
    preferred_language   STRING  COMMENT 'ISO 639-1 language code (EN, FR, DE, NL, etc.)',
    notes                STRING  COMMENT 'Free-text notes on the account'
)
COMMENT 'Importer and broker account registry for caller identification'
STORED AS PARQUET
TBLPROPERTIES ('parquet.compression'='SNAPPY', 'transactional'='false')
""", "Creating customer_accounts"),

    # -----------------------------------------------------------------------
    # 2. shipment_tracking
    # -----------------------------------------------------------------------
    ("DROP TABLE IF EXISTS shipment_tracking", "Dropping shipment_tracking"),
    ("""
CREATE TABLE shipment_tracking (
    tracking_id               STRING         COMMENT 'Unique shipment tracking ID (TRK-YYYY-NNNNN)',
    declaration_id            STRING         COMMENT 'Customs declaration reference number',
    customer_id               STRING         COMMENT 'FK -> customer_accounts.customer_id',
    importer_name             STRING         COMMENT 'Name of the importing company',
    hs_code                   STRING         COMMENT 'Harmonized System commodity code',
    product_description       STRING         COMMENT 'Plain-language description of goods',
    country_of_origin         STRING         COMMENT 'Declared country of origin',
    port_of_entry             STRING         COMMENT 'Port where goods entered (or are entering)',
    broker_name               STRING         COMMENT 'Customs broker or freight forwarder',
    quantity                  DECIMAL(18,2)  COMMENT 'Declared quantity',
    quantity_unit             STRING         COMMENT 'Unit of measure (pcs, kg, units, etc.)',
    declared_value_usd        DECIMAL(18,2)  COMMENT 'Declared customs value in USD',
    duty_rate_pct             DECIMAL(6,2)   COMMENT 'Applicable duty rate percentage',
    duty_assessed_usd         DECIMAL(18,2)  COMMENT 'Total duty assessed by customs',
    duty_paid_usd             DECIMAL(18,2)  COMMENT 'Duty amount already paid',
    status                    STRING         COMMENT 'PENDING | IN_TRANSIT | UNDER_EXAMINATION | HELD | CLEARED | SEIZED | UNDER_APPEAL',
    `location`                STRING         COMMENT 'Current physical location of the shipment',
    last_updated              DATE           COMMENT 'Date the status was last updated',
    estimated_clearance_date  DATE           COMMENT 'Estimated date of customs clearance',
    actual_clearance_date     DATE           COMMENT 'Actual clearance date (NULL if not yet cleared)',
    inspection_type           STRING         COMMENT 'NONE | DOC_CHECK | X_RAY | PHYSICAL | SEIZURE',
    hold_reason               STRING         COMMENT 'Reason for hold (NULL if not held)',
    officer_id                STRING         COMMENT 'Assigned customs officer identifier',
    notes                     STRING         COMMENT 'Free-text processing notes'
)
COMMENT 'Live and historical shipment tracking — primary chatbot lookup table'
STORED AS PARQUET
TBLPROPERTIES ('parquet.compression'='SNAPPY', 'transactional'='false')
""", "Creating shipment_tracking"),
]

VERIFY_TABLES = [
    "customer_accounts",
    "shipment_tracking",
]


# ---------------------------------------------------------------------------
# Connection helper (CDP Knox gateway with retry configs)
# ---------------------------------------------------------------------------
def connect_to_impala():
    """Attempt connection using the standard CDP Knox gateway configurations."""
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
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 70)
    print("Customs Chatbot DB — Create Tables")
    print("=" * 70)
    print(f"Host    : {IMPALA_HOST}:{IMPALA_PORT}")
    print(f"User    : {USERNAME}")
    print(f"Database: {DATABASE}\n")

    conn, cursor = connect_to_impala()
    if not conn:
        print("\n✗ All connection attempts failed. Check host/credentials.")
        sys.exit(1)

    try:
        print(f"Creating database '{DATABASE}' if not exists...")
        cursor.execute(CREATE_DATABASE_SQL)
        cursor.execute(f"USE {DATABASE}")
        print(f"✓ Using database: {DATABASE}\n")

        for sql, description in DDL_STATEMENTS:
            print(f"{description}...")
            cursor.execute(sql.strip())
            print(f"  ✓ Done\n")

        print("=" * 70)
        print("Table verification")
        print("=" * 70)
        for table in VERIFY_TABLES:
            cursor.execute(f"DESCRIBE {table}")
            columns = cursor.fetchall()
            print(f"\n{table}")
            print("-" * 60)
            for col in columns:
                name    = col[0]
                dtype   = col[1]
                comment = col[2] if len(col) > 2 else ''
                print(f"  {name:<28} {dtype:<16} {comment}")
            print(f"  ({len(columns)} columns)")

        print("\n✓ All tables created successfully.")
        print(f"\nNext step: run  load_data_to_impala.py  to populate the tables.")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
