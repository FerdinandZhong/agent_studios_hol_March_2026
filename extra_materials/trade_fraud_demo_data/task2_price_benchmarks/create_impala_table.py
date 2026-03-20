#!/usr/bin/env python3
"""
Create trade fraud detection tables in Impala (Cloudera Data Warehouse).

Creates three tables in the trade_fraud_db database:
  - trade_price_benchmarks   : HS code price reference data (used by Agent 2)
  - trade_declarations       : Historical declaration records (used by Agents 2 & 5)
  - customs_clearances       : Clearance event log (used by Agent 5)

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
DATABASE     = 'trade_fraud_db'

# ---------------------------------------------------------------------------
# DDL statements
# ---------------------------------------------------------------------------
CREATE_DATABASE_SQL = f"""
CREATE DATABASE IF NOT EXISTS {DATABASE}
COMMENT 'Trade fraud detection demo data — CAI Studio workflow'
"""

DDL_STATEMENTS = [
    # -----------------------------------------------------------------------
    # 1. trade_price_benchmarks
    # -----------------------------------------------------------------------
    ("DROP TABLE IF EXISTS trade_price_benchmarks", "Dropping trade_price_benchmarks"),
    ("""
CREATE TABLE trade_price_benchmarks (
    hs_code          STRING        COMMENT 'Harmonized System commodity code (e.g. 6109.10)',
    hs_description   STRING        COMMENT 'Plain-language description of the HS heading',
    origin_country   STRING        COMMENT 'Country of origin as declared (full name)',
    avg_unit_price   DECIMAL(18,4) COMMENT 'Historical average unit price in stated currency',
    price_std_dev    DECIMAL(18,4) COMMENT 'Standard deviation of unit prices in the sample',
    min_price        DECIMAL(18,4) COMMENT 'Minimum observed unit price',
    max_price        DECIMAL(18,4) COMMENT 'Maximum observed unit price',
    sample_count     INT           COMMENT 'Number of transactions used to compute the benchmark',
    currency         STRING        COMMENT 'ISO 4217 currency code (e.g. USD)',
    price_unit       STRING        COMMENT 'Unit of measure for the price (e.g. per piece, per kg)',
    last_updated     DATE          COMMENT 'Date the benchmark was last refreshed'
)
COMMENT 'Price benchmark reference table for under/over-invoicing detection'
STORED AS PARQUET
TBLPROPERTIES ('parquet.compression'='SNAPPY', 'transactional'='false')
""", "Creating trade_price_benchmarks"),

    # -----------------------------------------------------------------------
    # 2. trade_declarations
    # -----------------------------------------------------------------------
    ("DROP TABLE IF EXISTS trade_declarations", "Dropping trade_declarations"),
    ("""
CREATE TABLE trade_declarations (
    declaration_id       STRING        COMMENT 'Unique reference ID from the trade document',
    document_type        STRING        COMMENT 'invoice | bill_of_lading | origin_certificate | packing_list',
    hs_code              STRING        COMMENT 'Harmonized System commodity code',
    product_description  STRING        COMMENT 'Free-text description of goods',
    declared_unit_price  DECIMAL(18,4) COMMENT 'Declared customs unit value',
    declared_total_value DECIMAL(18,2) COMMENT 'Total declared customs value for this line',
    currency             STRING        COMMENT 'ISO 4217 currency code',
    quantity             DECIMAL(18,2) COMMENT 'Declared quantity (numeric)',
    quantity_unit        STRING        COMMENT 'Unit of measure (pcs, kg, units, barrel, etc.)',
    country_of_origin    STRING        COMMENT 'Declared country of origin',
    port_of_loading      STRING        COMMENT 'Port where goods were loaded',
    port_of_discharge    STRING        COMMENT 'Destination port',
    destination_country  STRING        COMMENT 'Country of final destination',
    shipper_name         STRING        COMMENT 'Name of the exporting company',
    consignee_name       STRING        COMMENT 'Name of the importing company',
    broker_name          STRING        COMMENT 'Customs broker or freight forwarder',
    declaration_date     DATE          COMMENT 'Date the declaration was lodged',
    incoterms            STRING        COMMENT 'Trade terms (FOB, CIF, EXW, etc.)',
    officer_id           STRING        COMMENT 'ID of the customs officer who handled the declaration',
    status               STRING        COMMENT 'PENDING | CLEARED | HELD | REJECTED'
)
COMMENT 'Historical trade declaration records for price benchmarking and pattern analysis'
STORED AS PARQUET
TBLPROPERTIES ('parquet.compression'='SNAPPY', 'transactional'='false')
""", "Creating trade_declarations"),

    # -----------------------------------------------------------------------
    # 3. customs_clearances
    # -----------------------------------------------------------------------
    ("DROP TABLE IF EXISTS customs_clearances", "Dropping customs_clearances"),
    ("""
CREATE TABLE customs_clearances (
    clearance_id         STRING        COMMENT 'Unique clearance event ID',
    declaration_id       STRING        COMMENT 'FK to trade_declarations.declaration_id',
    officer_id           STRING        COMMENT 'Customs officer identifier',
    officer_name         STRING        COMMENT 'Full name of customs officer',
    broker_id            STRING        COMMENT 'Customs broker identifier',
    broker_name          STRING        COMMENT 'Trading name of customs broker / freight forwarder',
    clearance_date       DATE          COMMENT 'Date the clearance decision was made',
    processing_time_hrs  DECIMAL(6,2)  COMMENT 'Hours from lodgement to clearance decision',
    declared_value_usd   DECIMAL(18,2) COMMENT 'Declared value in USD at time of clearance',
    duty_assessed_usd    DECIMAL(18,2) COMMENT 'Duty assessed by customs',
    duty_paid_usd        DECIMAL(18,2) COMMENT 'Duty actually paid',
    outcome              STRING        COMMENT 'CLEARED | HELD | REJECTED | PENDING',
    inspection_type      STRING        COMMENT 'NONE | DOC_CHECK | X_RAY | PHYSICAL | SEIZURE',
    anomaly_flag         STRING        COMMENT 'NONE | LOW | MEDIUM | HIGH'
)
COMMENT 'Customs clearance event log for officer-broker collusion detection'
STORED AS PARQUET
TBLPROPERTIES ('parquet.compression'='SNAPPY', 'transactional'='false')
""", "Creating customs_clearances"),
]

VERIFY_TABLES = [
    "trade_price_benchmarks",
    "trade_declarations",
    "customs_clearances",
]


# ---------------------------------------------------------------------------
# Connection helper
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
            cursor.execute("SELECT 1")   # smoke-test
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
    print("Trade Fraud DB — Create Tables")
    print("=" * 70)
    print(f"Host    : {IMPALA_HOST}:{IMPALA_PORT}")
    print(f"User    : {USERNAME}")
    print(f"Database: {DATABASE}\n")

    conn, cursor = connect_to_impala()
    if not conn:
        print("\n✗ All connection attempts failed. Check host/credentials.")
        sys.exit(1)

    try:
        # Create and select database
        print(f"Creating database '{DATABASE}' if not exists...")
        cursor.execute(CREATE_DATABASE_SQL)
        cursor.execute(f"USE {DATABASE}")
        print(f"✓ Using database: {DATABASE}\n")

        # Run DDL statements
        for sql, description in DDL_STATEMENTS:
            print(f"{description}...")
            cursor.execute(sql.strip())
            print(f"  ✓ Done\n")

        # Verify all three tables exist and show their schemas
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
                print(f"  {name:<25} {dtype:<16} {comment}")
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
