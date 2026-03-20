#!/usr/bin/env python3
"""
Create digital banking chatbot tables in Impala (Cloudera Data Warehouse).

Creates six tables in the banking_chatbot_db database:
  - customers      : Customer identity and KYC registry
  - accounts       : Bank accounts (checking, savings, money market, CD)
  - transactions   : Full transaction history with status and failure reasons
  - loans          : Active and historical loan accounts
  - cards          : Debit and credit cards linked to accounts
  - support_cases  : Open and historical support cases

Usage:
    python create_impala_tables_banking.py

Update IMPALA_HOST, USERNAME, and PASSWORD before running.
"""

import sys
from impala.dbapi import connect

# ---------------------------------------------------------------------------
# Connection parameters — update for your CDP environment
# ---------------------------------------------------------------------------
IMPALA_HOST = 'your-datahub-gateway.your-env.cloudera.site'
IMPALA_PORT = 443
USERNAME     = 'your_username'
PASSWORD     = 'your_password'
DATABASE     = 'banking_chatbot_db'

# ---------------------------------------------------------------------------
# DDL statements
# ---------------------------------------------------------------------------
CREATE_DATABASE_SQL = f"""
CREATE DATABASE IF NOT EXISTS {DATABASE}
COMMENT 'Digital Banking Chatbot demo data — CAI Studio workflow'
"""

DDL_STATEMENTS = [
    # -----------------------------------------------------------------------
    # 1. customers
    # -----------------------------------------------------------------------
    ("DROP TABLE IF EXISTS customers", "Dropping customers"),
    ("""
CREATE TABLE customers (
    customer_id          STRING  COMMENT 'Unique customer identifier (CUST-BNNNN)',
    full_name            STRING  COMMENT 'Customer full legal name',
    email                STRING  COMMENT 'Primary email address',
    phone                STRING  COMMENT 'Primary phone number',
    date_of_birth        DATE    COMMENT 'Date of birth for identity verification',
    address              STRING  COMMENT 'Registered home address',
    kyc_status           STRING  COMMENT 'VERIFIED | PENDING | FAILED',
    registration_date    DATE    COMMENT 'Date account relationship opened',
    preferred_language   STRING  COMMENT 'ISO 639-1 language code (EN, ES, FR, JA, DE)',
    customer_segment     STRING  COMMENT 'RETAIL | PREMIUM | BUSINESS',
    notes                STRING  COMMENT 'Free-text notes on the customer relationship'
)
COMMENT 'Customer identity registry — primary lookup for caller identification'
STORED AS PARQUET
TBLPROPERTIES ('parquet.compression'='SNAPPY', 'transactional'='false')
""", "Creating customers"),

    # -----------------------------------------------------------------------
    # 2. accounts
    # -----------------------------------------------------------------------
    ("DROP TABLE IF EXISTS accounts", "Dropping accounts"),
    ("""
CREATE TABLE accounts (
    account_id           STRING         COMMENT 'Unique account identifier (ACC-NNNNNN)',
    customer_id          STRING         COMMENT 'FK -> customers.customer_id',
    account_type         STRING         COMMENT 'CHECKING | SAVINGS | MONEY_MARKET | CD',
    account_number_masked STRING        COMMENT 'Last-4 digits masked (****NNNN)',
    currency             STRING         COMMENT 'ISO 4217 currency code (USD, EUR, GBP)',
    current_balance      DECIMAL(18,2)  COMMENT 'Current ledger balance',
    available_balance    DECIMAL(18,2)  COMMENT 'Available balance (0 if locked or frozen)',
    status               STRING         COMMENT 'ACTIVE | LOCKED | FROZEN | UNDER_REVIEW | DORMANT | CLOSED',
    lock_reason          STRING         COMMENT 'FRAUD_ALERT | SUSPICIOUS_ACTIVITY | LOAN_DEFAULT | LARGE_CASH_DEPOSITS | CUSTOMER_REQUEST | NULL if ACTIVE',
    opened_date          DATE           COMMENT 'Date the account was opened',
    last_activity_date   DATE           COMMENT 'Date of the last transaction',
    interest_rate_pct    DECIMAL(6,3)   COMMENT 'Current annual interest rate percentage',
    overdraft_limit      DECIMAL(18,2)  COMMENT 'Approved overdraft limit (0 if none)',
    daily_transfer_limit DECIMAL(18,2)  COMMENT 'Maximum outbound transfer per day',
    notes                STRING         COMMENT 'Free-text notes on the account status'
)
COMMENT 'Bank accounts — primary lookup for balance, status, and lock inquiries'
STORED AS PARQUET
TBLPROPERTIES ('parquet.compression'='SNAPPY', 'transactional'='false')
""", "Creating accounts"),

    # -----------------------------------------------------------------------
    # 3. transactions
    # -----------------------------------------------------------------------
    ("DROP TABLE IF EXISTS transactions", "Dropping transactions"),
    ("""
CREATE TABLE transactions (
    transaction_id       STRING         COMMENT 'Unique transaction ID (TXN-YYYY-NNNNNN)',
    account_id           STRING         COMMENT 'FK -> accounts.account_id',
    customer_id          STRING         COMMENT 'FK -> customers.customer_id (denormalised)',
    transaction_type     STRING         COMMENT 'DEBIT | CREDIT | TRANSFER | PAYMENT | WITHDRAWAL | DEPOSIT | WIRE | FEE',
    amount               DECIMAL(18,2)  COMMENT 'Transaction amount (always positive)',
    currency             STRING         COMMENT 'ISO 4217 currency code',
    balance_after        DECIMAL(18,2)  COMMENT 'Account balance after this transaction',
    merchant_name        STRING         COMMENT 'Merchant or payee name',
    merchant_category    STRING         COMMENT 'GROCERY | RESTAURANT | RETAIL | UTILITIES | PAYROLL | RENT | ATM | TRANSFER | WIRE | SUBSCRIPTION | GAS | HEALTHCARE | FINANCIAL_SERVICES | TRAVEL',
    description          STRING         COMMENT 'Human-readable transaction description',
    status               STRING         COMMENT 'COMPLETED | PENDING | FAILED | DISPUTED | REVERSED',
    initiated_at         TIMESTAMP      COMMENT 'Timestamp when transaction was initiated',
    completed_at         TIMESTAMP      COMMENT 'Timestamp when transaction completed (NULL if PENDING or FAILED)',
    channel              STRING         COMMENT 'ONLINE | ATM | BRANCH | MOBILE | POS | SYSTEM | ACH | WIRE',
    reference_number     STRING         COMMENT 'Bank reference number for tracing',
    failure_reason       STRING         COMMENT 'INSUFFICIENT_FUNDS | ACCOUNT_LOCKED | ACCOUNT_FROZEN | DAILY_LIMIT_REACHED | CARD_EXPIRED | DECLINED | NULL if not FAILED',
    notes                STRING         COMMENT 'Free-text processing or investigation notes'
)
COMMENT 'Transaction history — lookup for status, failure, and dispute inquiries'
STORED AS PARQUET
TBLPROPERTIES ('parquet.compression'='SNAPPY', 'transactional'='false')
""", "Creating transactions"),

    # -----------------------------------------------------------------------
    # 4. loans
    # -----------------------------------------------------------------------
    ("DROP TABLE IF EXISTS loans", "Dropping loans"),
    ("""
CREATE TABLE loans (
    loan_id              STRING         COMMENT 'Unique loan identifier (LOAN-YYYY-NNNN)',
    customer_id          STRING         COMMENT 'FK -> customers.customer_id',
    loan_type            STRING         COMMENT 'PERSONAL | MORTGAGE | AUTO | STUDENT | BUSINESS | BUSINESS_LINE_OF_CREDIT',
    original_amount      DECIMAL(18,2)  COMMENT 'Original principal amount disbursed',
    outstanding_balance  DECIMAL(18,2)  COMMENT 'Current outstanding balance',
    interest_rate_pct    DECIMAL(6,3)   COMMENT 'Annual interest rate percentage',
    monthly_payment      DECIMAL(18,2)  COMMENT 'Required monthly payment amount',
    next_payment_date    DATE           COMMENT 'Due date of the next scheduled payment',
    next_payment_amount  DECIMAL(18,2)  COMMENT 'Amount due on next payment date',
    last_payment_date    DATE           COMMENT 'Date of the most recent payment received',
    last_payment_amount  DECIMAL(18,2)  COMMENT 'Amount of the most recent payment',
    payments_overdue     INT            COMMENT 'Number of missed payments (0 if current)',
    status               STRING         COMMENT 'ACTIVE | DELINQUENT | DEFAULT | PAID_OFF | IN_REVIEW',
    origination_date     DATE           COMMENT 'Date the loan was funded',
    maturity_date        DATE           COMMENT 'Scheduled loan payoff date',
    collateral           STRING         COMMENT 'Collateral description (NULL for unsecured)',
    notes                STRING         COMMENT 'Free-text notes on loan status'
)
COMMENT 'Loan accounts — lookup for balance, payment schedule, and default status'
STORED AS PARQUET
TBLPROPERTIES ('parquet.compression'='SNAPPY', 'transactional'='false')
""", "Creating loans"),

    # -----------------------------------------------------------------------
    # 5. cards
    # -----------------------------------------------------------------------
    ("DROP TABLE IF EXISTS cards", "Dropping cards"),
    ("""
CREATE TABLE cards (
    card_id              STRING         COMMENT 'Unique card identifier (CARD-NNNNNN)',
    account_id           STRING         COMMENT 'FK -> accounts.account_id',
    customer_id          STRING         COMMENT 'FK -> customers.customer_id (denormalised)',
    card_type            STRING         COMMENT 'DEBIT | CREDIT',
    card_number_masked   STRING         COMMENT 'Last-4 digits masked (****NNNN)',
    status               STRING         COMMENT 'ACTIVE | BLOCKED | EXPIRED | CANCELLED',
    block_reason         STRING         COMMENT 'ACCOUNT_LOCKED | ACCOUNT_FROZEN | LOAN_DEFAULT | FRAUD | LOST | STOLEN | NULL if ACTIVE',
    expiry_date          DATE           COMMENT 'Card expiry date (last day of month)',
    credit_limit         DECIMAL(18,2)  COMMENT 'Credit limit (NULL for debit cards)',
    current_balance      DECIMAL(18,2)  COMMENT 'Outstanding balance (NULL for debit cards)',
    available_credit     DECIMAL(18,2)  COMMENT 'Available credit = limit minus balance',
    issued_date          DATE           COMMENT 'Date card was issued',
    last_used_date       DATE           COMMENT 'Date of last successful transaction',
    notes                STRING         COMMENT 'Free-text notes on card status'
)
COMMENT 'Payment cards — lookup for card status, block reason, and credit inquiries'
STORED AS PARQUET
TBLPROPERTIES ('parquet.compression'='SNAPPY', 'transactional'='false')
""", "Creating cards"),

    # -----------------------------------------------------------------------
    # 6. support_cases
    # -----------------------------------------------------------------------
    ("DROP TABLE IF EXISTS support_cases", "Dropping support_cases"),
    ("""
CREATE TABLE support_cases (
    case_id              STRING     COMMENT 'Unique case identifier (CASE-YYYY-NNNN)',
    customer_id          STRING     COMMENT 'FK -> customers.customer_id',
    case_type            STRING     COMMENT 'FRAUD_REPORT | ACCOUNT_LOCK | TRANSACTION_DISPUTE | TRANSACTION_INQUIRY | LOAN_INQUIRY | LOAN_DEFAULT | COMPLIANCE | GENERAL',
    subject              STRING     COMMENT 'Short description of the issue',
    status               STRING     COMMENT 'OPEN | IN_PROGRESS | RESOLVED | ESCALATED | CLOSED',
    priority             STRING     COMMENT 'LOW | MEDIUM | HIGH | CRITICAL',
    assigned_agent       STRING     COMMENT 'ID of the agent or team handling the case',
    created_at           TIMESTAMP  COMMENT 'Timestamp when the case was opened',
    updated_at           TIMESTAMP  COMMENT 'Timestamp of the last update',
    resolved_at          TIMESTAMP  COMMENT 'Timestamp when resolved (NULL if open)',
    account_id           STRING     COMMENT 'Primary account referenced in this case',
    transaction_id       STRING     COMMENT 'Space-separated transaction IDs for this case',
    notes                STRING     COMMENT 'Free-text case notes and resolution details'
)
COMMENT 'Support cases — lookup for case status and escalation context'
STORED AS PARQUET
TBLPROPERTIES ('parquet.compression'='SNAPPY', 'transactional'='false')
""", "Creating support_cases"),
]

VERIFY_TABLES = [
    "customers",
    "accounts",
    "transactions",
    "loans",
    "cards",
    "support_cases",
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
            'http_path': f'{IMPALA_HOST.split(".")[0]}/cdp-proxy-api/impala',
        },
        {
            'host': IMPALA_HOST, 'port': IMPALA_PORT, 'database': 'default',
            'user': USERNAME, 'password': PASSWORD, 'timeout': 120,
            'use_ssl': True, 'auth_mechanism': 'PLAIN',
            'use_http_transport': True,
            'http_path': f'{IMPALA_HOST.split(".")[0]}/cdp-proxy-api/impala',
        },
        {
            'host': IMPALA_HOST, 'port': IMPALA_PORT, 'database': 'default',
            'user': USERNAME, 'password': PASSWORD, 'timeout': 120,
            'use_ssl': True, 'auth_mechanism': 'LDAP',
            'use_http_transport': True,
            'http_path': f'{IMPALA_HOST.split(".")[0]}/cdp-proxy-api/impala/cliservice',
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
    print("Banking Chatbot DB — Create Tables")
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
        print(f"\nNext step: run  load_data_to_impala_banking.py  to populate the tables.")

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
