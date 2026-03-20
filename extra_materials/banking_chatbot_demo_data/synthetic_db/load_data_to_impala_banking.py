#!/usr/bin/env python3
"""
Load synthetic demo data into banking chatbot Impala tables.

Reads six CSV files from the same directory and inserts rows into:
  - customers      (from customers.csv)
  - accounts       (from accounts.csv)
  - transactions   (from transactions.csv)
  - loans          (from loans.csv)
  - cards          (from cards.csv)
  - support_cases  (from support_cases.csv)

Runs post-load verification queries that demonstrate the chatbot's
main query patterns: account status, transaction history, loan balances,
card status, and open support cases.

Usage:
    python load_data_to_impala_banking.py

Update IMPALA_HOST, USERNAME, and PASSWORD before running.
"""

import csv
import sys
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from impala.dbapi import connect

# ---------------------------------------------------------------------------
# Connection parameters — update for your CDP environment
# ---------------------------------------------------------------------------
IMPALA_HOST = 'your-datahub-gateway.your-env.cloudera.site'
IMPALA_PORT = 443
USERNAME     = 'your_username'
PASSWORD     = 'your_password'
DATABASE     = 'banking_chatbot_db'

DATA_DIR = Path(__file__).parent


# ---------------------------------------------------------------------------
# INSERT templates
# ---------------------------------------------------------------------------
CUSTOMERS_INSERT = """
INSERT INTO customers VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
)
"""

ACCOUNTS_INSERT = """
INSERT INTO accounts VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
)
"""

TRANSACTIONS_INSERT = """
INSERT INTO transactions VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
)
"""

LOANS_INSERT = """
INSERT INTO loans VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
)
"""

CARDS_INSERT = """
INSERT INTO cards VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
)
"""

SUPPORT_CASES_INSERT = """
INSERT INTO support_cases VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
)
"""


# ---------------------------------------------------------------------------
# Type conversion helpers
# ---------------------------------------------------------------------------
def to_date(s):
    """Convert YYYY-MM-DD string to date, or None if empty."""
    if not s or s.strip() == '':
        return None
    return datetime.strptime(s.strip(), '%Y-%m-%d').date()


def to_timestamp(s):
    """Convert YYYY-MM-DD HH:MM:SS string to datetime, or None if empty."""
    if not s or s.strip() == '':
        return None
    try:
        return datetime.strptime(s.strip(), '%Y-%m-%d %H:%M:%S')
    except ValueError:
        return datetime.strptime(s.strip(), '%Y-%m-%d').replace(
            hour=0, minute=0, second=0
        )


def to_decimal(s):
    """Convert string to Decimal, or None if empty."""
    if not s or s.strip() == '':
        return None
    try:
        return Decimal(s.strip())
    except InvalidOperation:
        return None


def to_int(s):
    """Convert string to int, or None if empty."""
    if not s or s.strip() == '':
        return None
    try:
        return int(s.strip())
    except ValueError:
        return None


def to_str(s):
    """Return stripped string or None if empty."""
    if not s or s.strip() == '':
        return None
    return s.strip()


# ---------------------------------------------------------------------------
# CSV loaders
# ---------------------------------------------------------------------------
def load_customers(cursor, csv_path):
    print(f"\nLoading customers from {csv_path.name}...")
    rows_loaded = 0
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            values = (
                to_str(row['customer_id']),
                to_str(row['full_name']),
                to_str(row['email']),
                to_str(row['phone']),
                to_date(row['date_of_birth']),
                to_str(row['address']),
                to_str(row['kyc_status']),
                to_date(row['registration_date']),
                to_str(row['preferred_language']),
                to_str(row['customer_segment']),
                to_str(row['notes']),
            )
            cursor.execute(CUSTOMERS_INSERT, values)
            rows_loaded += 1
    print(f"  ✓ {rows_loaded} customers loaded")
    return rows_loaded


def load_accounts(cursor, csv_path):
    print(f"\nLoading accounts from {csv_path.name}...")
    rows_loaded = 0
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            values = (
                to_str(row['account_id']),
                to_str(row['customer_id']),
                to_str(row['account_type']),
                to_str(row['account_number_masked']),
                to_str(row['currency']),
                to_decimal(row['current_balance']),
                to_decimal(row['available_balance']),
                to_str(row['status']),
                to_str(row['lock_reason']),
                to_date(row['opened_date']),
                to_date(row['last_activity_date']),
                to_decimal(row['interest_rate_pct']),
                to_decimal(row['overdraft_limit']),
                to_decimal(row['daily_transfer_limit']),
                to_str(row['notes']),
            )
            cursor.execute(ACCOUNTS_INSERT, values)
            rows_loaded += 1
    print(f"  ✓ {rows_loaded} accounts loaded")
    return rows_loaded


def load_transactions(cursor, csv_path):
    print(f"\nLoading transactions from {csv_path.name}...")
    rows_loaded = 0
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            values = (
                to_str(row['transaction_id']),
                to_str(row['account_id']),
                to_str(row['customer_id']),
                to_str(row['transaction_type']),
                to_decimal(row['amount']),
                to_str(row['currency']),
                to_decimal(row['balance_after']),
                to_str(row['merchant_name']),
                to_str(row['merchant_category']),
                to_str(row['description']),
                to_str(row['status']),
                to_timestamp(row['initiated_at']),
                to_timestamp(row['completed_at']),
                to_str(row['channel']),
                to_str(row['reference_number']),
                to_str(row['failure_reason']),
                to_str(row['notes']),
            )
            cursor.execute(TRANSACTIONS_INSERT, values)
            rows_loaded += 1
    print(f"  ✓ {rows_loaded} transactions loaded")
    return rows_loaded


def load_loans(cursor, csv_path):
    print(f"\nLoading loans from {csv_path.name}...")
    rows_loaded = 0
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            values = (
                to_str(row['loan_id']),
                to_str(row['customer_id']),
                to_str(row['loan_type']),
                to_decimal(row['original_amount']),
                to_decimal(row['outstanding_balance']),
                to_decimal(row['interest_rate_pct']),
                to_decimal(row['monthly_payment']),
                to_date(row['next_payment_date']),
                to_decimal(row['next_payment_amount']),
                to_date(row['last_payment_date']),
                to_decimal(row['last_payment_amount']),
                to_int(row['payments_overdue']),
                to_str(row['status']),
                to_date(row['origination_date']),
                to_date(row['maturity_date']),
                to_str(row['collateral']),
                to_str(row['notes']),
            )
            cursor.execute(LOANS_INSERT, values)
            rows_loaded += 1
    print(f"  ✓ {rows_loaded} loans loaded")
    return rows_loaded


def load_cards(cursor, csv_path):
    print(f"\nLoading cards from {csv_path.name}...")
    rows_loaded = 0
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            values = (
                to_str(row['card_id']),
                to_str(row['account_id']),
                to_str(row['customer_id']),
                to_str(row['card_type']),
                to_str(row['card_number_masked']),
                to_str(row['status']),
                to_str(row['block_reason']),
                to_date(row['expiry_date']),
                to_decimal(row['credit_limit']),
                to_decimal(row['current_balance']),
                to_decimal(row['available_credit']),
                to_date(row['issued_date']),
                to_date(row['last_used_date']),
                to_str(row['notes']),
            )
            cursor.execute(CARDS_INSERT, values)
            rows_loaded += 1
    print(f"  ✓ {rows_loaded} cards loaded")
    return rows_loaded


def load_support_cases(cursor, csv_path):
    print(f"\nLoading support_cases from {csv_path.name}...")
    rows_loaded = 0
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            values = (
                to_str(row['case_id']),
                to_str(row['customer_id']),
                to_str(row['case_type']),
                to_str(row['subject']),
                to_str(row['status']),
                to_str(row['priority']),
                to_str(row['assigned_agent']),
                to_timestamp(row['created_at']),
                to_timestamp(row['updated_at']),
                to_timestamp(row['resolved_at']),
                to_str(row['account_id']),
                to_str(row['transaction_id']),
                to_str(row['notes']),
            )
            cursor.execute(SUPPORT_CASES_INSERT, values)
            rows_loaded += 1
    print(f"  ✓ {rows_loaded} support cases loaded")
    return rows_loaded


# ---------------------------------------------------------------------------
# Post-load verification queries
# ---------------------------------------------------------------------------
VERIFICATION_QUERIES = [
    # Row counts
    (
        "Row counts per table",
        """
        SELECT 'customers'     AS tbl, COUNT(*) AS n FROM customers
        UNION ALL SELECT 'accounts',     COUNT(*) FROM accounts
        UNION ALL SELECT 'transactions', COUNT(*) FROM transactions
        UNION ALL SELECT 'loans',        COUNT(*) FROM loans
        UNION ALL SELECT 'cards',        COUNT(*) FROM cards
        UNION ALL SELECT 'support_cases',COUNT(*) FROM support_cases
        """,
        ["table", "row_count"],
    ),
    # Locked / frozen accounts
    (
        "Non-active accounts (locked / frozen / under review)",
        """
        SELECT a.account_id, c.full_name, a.account_type, a.status,
               a.lock_reason, a.current_balance, a.available_balance
        FROM accounts a
        JOIN customers c ON a.customer_id = c.customer_id
        WHERE a.status != 'ACTIVE'
        ORDER BY a.status
        """,
        ["account_id", "customer", "type", "status", "lock_reason", "balance", "available"],
    ),
    # Pending transactions
    (
        "Pending transactions",
        """
        SELECT t.transaction_id, c.full_name, t.transaction_type,
               t.amount, t.currency, t.description, t.initiated_at, t.channel
        FROM transactions t
        JOIN customers c ON t.customer_id = c.customer_id
        WHERE t.status = 'PENDING'
        ORDER BY t.initiated_at DESC
        """,
        ["txn_id", "customer", "type", "amount", "currency", "description", "initiated", "channel"],
    ),
    # Failed transactions
    (
        "Failed transactions",
        """
        SELECT t.transaction_id, c.full_name, t.amount, t.description,
               t.failure_reason, t.initiated_at
        FROM transactions t
        JOIN customers c ON t.customer_id = c.customer_id
        WHERE t.status = 'FAILED'
        ORDER BY t.initiated_at DESC
        """,
        ["txn_id", "customer", "amount", "description", "failure_reason", "initiated"],
    ),
    # Delinquent / default loans
    (
        "Delinquent and defaulted loans",
        """
        SELECT l.loan_id, c.full_name, l.loan_type, l.outstanding_balance,
               l.payments_overdue, l.status, l.last_payment_date
        FROM loans l
        JOIN customers c ON l.customer_id = c.customer_id
        WHERE l.status IN ('DELINQUENT', 'DEFAULT')
        ORDER BY l.payments_overdue DESC
        """,
        ["loan_id", "customer", "type", "outstanding", "overdue_payments", "status", "last_payment"],
    ),
    # Open support cases
    (
        "Open and in-progress support cases",
        """
        SELECT sc.case_id, c.full_name, sc.case_type, sc.subject,
               sc.status, sc.priority, sc.created_at
        FROM support_cases sc
        JOIN customers c ON sc.customer_id = c.customer_id
        WHERE sc.status NOT IN ('RESOLVED', 'CLOSED')
        ORDER BY
            CASE sc.priority WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2
                             WHEN 'MEDIUM' THEN 3 ELSE 4 END,
            sc.created_at DESC
        """,
        ["case_id", "customer", "type", "subject", "status", "priority", "opened"],
    ),
]


def run_verifications(cursor):
    print("\n" + "=" * 70)
    print("Post-load verification queries")
    print("=" * 70)

    for title, sql, columns in VERIFICATION_QUERIES:
        print(f"\n{title}")
        print("-" * 60)
        try:
            cursor.execute(sql.strip())
            rows = cursor.fetchall()
            if rows:
                col_width = 18
                header = "  ".join(f"{c[:col_width]:<{col_width}}" for c in columns)
                print(f"  {header}")
                print("  " + "-" * (col_width * len(columns) + 2 * (len(columns) - 1)))
                for row in rows:
                    line = "  ".join(
                        f"{str(v)[:col_width]:<{col_width}}" for v in row
                    )
                    print(f"  {line}")
                print(f"  ({len(rows)} row{'s' if len(rows) != 1 else ''})")
            else:
                print("  (no rows)")
        except Exception as e:
            print(f"  ✗ Query failed: {e}")


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
            'http_path': f'{IMPALA_HOST.split(".")[0]}/cdp-proxy-api/impala',
        },
        {
            'host': IMPALA_HOST, 'port': IMPALA_PORT, 'database': 'default',
            'user': USERNAME, 'password': PASSWORD, 'timeout': 120,
            'use_ssl': True, 'auth_mechanism': 'PLAIN',
            'use_http_transport': True,
            'http_path': f'{IMPALA_HOST.split(".")[0]}/cdp-proxy-api/impala',
        },
    ]
    for i, cfg in enumerate(configs, 1):
        try:
            print(f"  Trying config {i}...")
            conn = connect(**cfg)
            cur = conn.cursor()
            cur.execute("SELECT 1")
            print(f"  ✓ Connected with config {i}\n")
            return conn, cur
        except Exception as e:
            print(f"  ✗ Failed: {str(e)[:120]}")
    return None, None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 70)
    print("Banking Chatbot DB — Load Synthetic Data")
    print("=" * 70)
    print(f"Host    : {IMPALA_HOST}:{IMPALA_PORT}")
    print(f"User    : {USERNAME}")
    print(f"Database: {DATABASE}")
    print(f"Data dir: {DATA_DIR}\n")

    # Verify CSV files exist
    files = {
        'customers':      DATA_DIR / 'customers.csv',
        'accounts':       DATA_DIR / 'accounts.csv',
        'transactions':   DATA_DIR / 'transactions.csv',
        'loans':          DATA_DIR / 'loans.csv',
        'cards':          DATA_DIR / 'cards.csv',
        'support_cases':  DATA_DIR / 'support_cases.csv',
    }
    for name, path in files.items():
        if not path.exists():
            print(f"✗ Missing file: {path}")
            sys.exit(1)
    print("✓ All CSV files found\n")

    conn, cursor = connect_to_impala()
    if not conn:
        print("\n✗ All connection attempts failed. Check host/credentials.")
        sys.exit(1)

    try:
        cursor.execute(f"USE {DATABASE}")
        print(f"✓ Using database: {DATABASE}\n")

        total = 0
        total += load_customers(cursor,     files['customers'])
        total += load_accounts(cursor,      files['accounts'])
        total += load_transactions(cursor,  files['transactions'])
        total += load_loans(cursor,         files['loans'])
        total += load_cards(cursor,         files['cards'])
        total += load_support_cases(cursor, files['support_cases'])

        print(f"\n{'=' * 70}")
        print(f"✓ Total rows inserted: {total}")

        run_verifications(cursor)

        print("\n✓ Data load complete. Banking chatbot database is ready.")

    except Exception as e:
        print(f"\n✗ Error during load: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
