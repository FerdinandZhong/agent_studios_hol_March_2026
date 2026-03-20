#!/usr/bin/env python3
"""
Load trade fraud demo CSV data into Impala (Cloudera Data Warehouse).

Loads three CSV files into the corresponding tables in trade_fraud_db:
  CSV file                       →  Impala table
  trade_price_benchmarks.csv     →  trade_price_benchmarks
  trade_declarations.csv         →  trade_declarations
  customs_clearances.csv         →  customs_clearances

Expects the CSV files to be in the same directory as this script.
Run create_impala_table.py first to create the tables.

Usage:
    python load_data_to_impala.py
"""

import csv
import os
import sys
from decimal import Decimal, InvalidOperation
from impala.dbapi import connect

# ---------------------------------------------------------------------------
# Connection parameters — update for your CDP environment
# ---------------------------------------------------------------------------
IMPALA_HOST = 'qzhong-datahub-gateway.qzhong-1.a465-9q4k.cloudera.site'
IMPALA_PORT = 443
USERNAME     = 'qzhong'
PASSWORD     = 'P@ssw0rd.'
DATABASE     = 'trade_fraud_db'

# Directory containing the CSV files (defaults to same folder as this script)
DATA_DIR = os.path.dirname(os.path.abspath(__file__))

BATCH_SIZE = 50   # rows per INSERT batch

# ---------------------------------------------------------------------------
# Per-table configuration: CSV filename, INSERT template, row parser
# ---------------------------------------------------------------------------

def _str(v):
    """Return None for empty strings so Impala stores NULL."""
    v = v.strip()
    return v if v and v != '' else None

def _dec(v):
    """Parse a decimal/float string; return None on empty or error."""
    v = v.strip()
    if not v:
        return None
    try:
        return float(Decimal(v))
    except InvalidOperation:
        return None

def _int(v):
    """Parse an integer string; return None on empty or error."""
    v = v.strip()
    if not v:
        return None
    try:
        return int(v)
    except ValueError:
        return None


def parse_price_benchmarks_row(row):
    return (
        _str(row['hs_code']),
        _str(row['hs_description']),
        _str(row['origin_country']),
        _dec(row['avg_unit_price']),
        _dec(row['price_std_dev']),
        _dec(row['min_price']),
        _dec(row['max_price']),
        _int(row['sample_count']),
        _str(row['currency']),
        _str(row['price_unit']),
        _str(row['last_updated']),
    )

PRICE_BENCHMARKS_INSERT = """
INSERT INTO trade_price_benchmarks VALUES (?,?,?,?,?,?,?,?,?,?,?)
"""


def parse_declarations_row(row):
    return (
        _str(row['declaration_id']),
        _str(row['document_type']),
        _str(row['hs_code']),
        _str(row['product_description']),
        _dec(row['declared_unit_price']),
        _dec(row['declared_total_value']),
        _str(row['currency']),
        _dec(row['quantity']),
        _str(row['quantity_unit']),
        _str(row['country_of_origin']),
        _str(row['port_of_loading']),
        _str(row['port_of_discharge']),
        _str(row['destination_country']),
        _str(row['shipper_name']),
        _str(row['consignee_name']),
        _str(row['broker_name']),
        _str(row['declaration_date']),
        _str(row['incoterms']),
        _str(row['officer_id']),
        _str(row['status']),
    )

DECLARATIONS_INSERT = """
INSERT INTO trade_declarations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
"""


def parse_clearances_row(row):
    return (
        _str(row['clearance_id']),
        _str(row['declaration_id']),
        _str(row['officer_id']),
        _str(row['officer_name']),
        _str(row['broker_id']),
        _str(row['broker_name']),
        _str(row['clearance_date']),
        _dec(row['processing_time_hrs']),
        _dec(row['declared_value_usd']),
        _dec(row['duty_assessed_usd']),
        _dec(row['duty_paid_usd']),
        _str(row['outcome']),
        _str(row['inspection_type']),
        _str(row['anomaly_flag']),
    )

CLEARANCES_INSERT = """
INSERT INTO customs_clearances VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
"""

# Master load plan: (csv_filename, table_name, insert_sql, row_parser)
LOAD_PLAN = [
    (
        'trade_price_benchmarks.csv',
        'trade_price_benchmarks',
        PRICE_BENCHMARKS_INSERT,
        parse_price_benchmarks_row,
    ),
    (
        'trade_declarations.csv',
        'trade_declarations',
        DECLARATIONS_INSERT,
        parse_declarations_row,
    ),
    (
        'customs_clearances.csv',
        'customs_clearances',
        CLEARANCES_INSERT,
        parse_clearances_row,
    ),
]


# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------
def connect_to_impala():
    configs = [
        {
            'host': IMPALA_HOST, 'port': IMPALA_PORT, 'database': DATABASE,
            'user': USERNAME, 'password': PASSWORD, 'timeout': 120,
            'use_ssl': True, 'auth_mechanism': 'LDAP',
            'use_http_transport': True,
            'http_path': 'qzhong-datahub/cdp-proxy-api/impala',
        },
        {
            'host': IMPALA_HOST, 'port': IMPALA_PORT, 'database': DATABASE,
            'user': USERNAME, 'password': PASSWORD, 'timeout': 120,
            'use_ssl': True, 'auth_mechanism': 'PLAIN',
            'use_http_transport': True,
            'http_path': 'qzhong-datahub/cdp-proxy-api/impala',
        },
        {
            'host': IMPALA_HOST, 'port': IMPALA_PORT, 'database': DATABASE,
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
# Load helper
# ---------------------------------------------------------------------------
def load_csv(cursor, csv_filename, table_name, insert_sql, row_parser):
    csv_path = os.path.join(DATA_DIR, csv_filename)
    if not os.path.exists(csv_path):
        print(f"  ✗ CSV file not found: {csv_path}")
        return 0

    # Parse rows
    rows = []
    skipped = 0
    with open(csv_path, newline='', encoding='utf-8') as fh:
        reader = csv.DictReader(fh)
        for line_num, row in enumerate(reader, start=2):  # start=2: row 1 is header
            try:
                rows.append(row_parser(row))
            except Exception as e:
                print(f"    ! Skipping line {line_num}: {e}")
                skipped += 1

    print(f"  Parsed {len(rows)} rows ({skipped} skipped)\n"
          f"  Inserting into {DATABASE}.{table_name} in batches of {BATCH_SIZE}...")

    inserted = 0
    errors   = 0
    for start in range(0, len(rows), BATCH_SIZE):
        batch = rows[start : start + BATCH_SIZE]
        try:
            cursor.executemany(insert_sql.strip(), batch)
            inserted += len(batch)
        except Exception as batch_err:
            print(f"    ! Batch error: {batch_err} — retrying row by row...")
            for row_tuple in batch:
                try:
                    cursor.execute(insert_sql.strip(), row_tuple)
                    inserted += 1
                except Exception as row_err:
                    print(f"    ! Row error: {row_err}")
                    errors += 1
        print(f"    {inserted}/{len(rows)} rows inserted...", end='\r')

    print()
    if errors:
        print(f"  ✗ {errors} rows failed to insert")
    print(f"  ✓ {inserted} rows loaded into {table_name}")
    return inserted


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------
def verify_all(cursor):
    print("\n" + "=" * 70)
    print("Post-load verification")
    print("=" * 70)

    # Row counts
    print("\nRow counts:")
    for _, table, _, _ in LOAD_PLAN:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  {table:<35} {count:>6} rows")

    # Demo case benchmark — should show avg_unit_price ≈ 3.20
    print("\nBenchmark check — HS 6109.10, Bangladesh (expected avg ≈ 3.20 USD/pc):")
    cursor.execute("""
        SELECT hs_code, origin_country,
               avg_unit_price, price_std_dev, min_price, max_price, sample_count
        FROM trade_price_benchmarks
        WHERE hs_code = '6109.10' AND origin_country = 'Bangladesh'
    """)
    for row in cursor.fetchall():
        print(f"  HS={row[0]}  Origin={row[1]}  avg={row[2]}  std={row[3]}"
              f"  min={row[4]}  max={row[5]}  n={row[6]}")

    # Price anomaly check — declared price vs benchmark for demo shipment
    print("\nPrice anomaly — INV-2024-00123 declared vs benchmark:")
    cursor.execute("""
        SELECT declaration_id, declared_unit_price, shipper_name, consignee_name
        FROM trade_declarations
        WHERE declaration_id = 'INV-2024-00123'
    """)
    for row in cursor.fetchall():
        declared = float(row[1])
        benchmark_avg = 3.20
        deviation_pct = (benchmark_avg - declared) / benchmark_avg * 100
        z_score = (declared - benchmark_avg) / 0.65
        anomaly_score = min(abs(z_score) / 4.0, 1.0)
        print(f"  {row[0]}  declared={declared}  benchmark_avg={benchmark_avg}"
              f"  deviation={deviation_pct:.1f}%  z={z_score:.2f}  anomaly_score={anomaly_score:.2f}")

    # Collusion check — officer-broker co-occurrence (OFF-0042 should be top)
    print("\nOfficer-broker co-occurrence (top 5, last 365 days):")
    cursor.execute("""
        SELECT officer_id, broker_name,
               COUNT(*) AS clearance_count,
               ROUND(AVG(processing_time_hrs), 2) AS avg_hrs
        FROM customs_clearances
        WHERE clearance_date > DATE_ADD(CURRENT_DATE(), -365)
        GROUP BY officer_id, broker_name
        HAVING COUNT(*) > 5
        ORDER BY clearance_count DESC
        LIMIT 5
    """)
    for row in cursor.fetchall():
        print(f"  {row[0]}  /  {row[1]:<35}  {row[2]:>3} clearances  {row[3]} avg hrs")

    # Split shipment check
    print("\nSplit shipment pattern — Textile House Ltd → ABC Trading UK (last 90 days):")
    cursor.execute("""
        SELECT declaration_date, declared_total_value, quantity, broker_name
        FROM trade_declarations
        WHERE shipper_name   = 'Textile House Ltd'
          AND consignee_name = 'ABC Trading UK'
          AND hs_code        = '6109.10'
          AND declaration_date > DATE_ADD(CURRENT_DATE(), -90)
        ORDER BY declaration_date
    """)
    rows = cursor.fetchall()
    for row in rows:
        print(f"  {row[0]}  USD {row[1]:<10}  qty={row[2]}  broker={row[3]}")
    print(f"  → {len(rows)} shipments in 90 days")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 70)
    print("Trade Fraud DB — Load CSV Data into Impala")
    print("=" * 70)
    print(f"Host     : {IMPALA_HOST}:{IMPALA_PORT}")
    print(f"User     : {USERNAME}")
    print(f"Database : {DATABASE}")
    print(f"Data dir : {DATA_DIR}\n")

    conn, cursor = connect_to_impala()
    if not conn:
        print("\n✗ All connection attempts failed. Check host/credentials.")
        sys.exit(1)

    try:
        cursor.execute(f"USE {DATABASE}")

        for csv_filename, table_name, insert_sql, row_parser in LOAD_PLAN:
            print("-" * 70)
            print(f"Loading {csv_filename}  →  {table_name}")
            print("-" * 70)
            # Truncate existing rows before reload
            cursor.execute(f"TRUNCATE TABLE IF EXISTS {table_name}")
            load_csv(cursor, csv_filename, table_name, insert_sql, row_parser)
            print()

        verify_all(cursor)

        print("\n" + "=" * 70)
        print("✓ All tables loaded successfully.")
        print("=" * 70)

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
