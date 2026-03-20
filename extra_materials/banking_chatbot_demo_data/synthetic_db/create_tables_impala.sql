-- =============================================================================
-- Digital Banking Chatbot — Impala DDL & Data Load Script
-- =============================================================================
-- Tables required by the Banking Support Agent via the iceberg-mcp-server tool.
--
-- Run order:
--   1. Create database
--   2. Create tables (in dependency order)
--   3. Load CSVs from HDFS staging path
-- =============================================================================

CREATE DATABASE IF NOT EXISTS banking_chatbot_db
COMMENT 'Digital Banking Chatbot demo data — CAI Studio workflow';

USE banking_chatbot_db;


-- ---------------------------------------------------------------------------
-- 1. customers
--    Core customer identity and KYC registry.
--    Used for caller identification, personalisation, and segment routing.
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS customers;

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
TBLPROPERTIES ('parquet.compression'='SNAPPY', 'transactional'='false');

LOAD DATA INPATH '/user/banking_chatbot/staging/customers.csv'
OVERWRITE INTO TABLE customers;


-- ---------------------------------------------------------------------------
-- 2. accounts
--    All bank accounts linked to customers.
--    Primary table for account status, balance, and lock inquiries.
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS accounts;

CREATE TABLE accounts (
    account_id           STRING         COMMENT 'Unique account identifier (ACC-NNNNNN)',
    customer_id          STRING         COMMENT 'FK → customers.customer_id',
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
TBLPROPERTIES ('parquet.compression'='SNAPPY', 'transactional'='false');

LOAD DATA INPATH '/user/banking_chatbot/staging/accounts.csv'
OVERWRITE INTO TABLE accounts;


-- ---------------------------------------------------------------------------
-- 3. transactions
--    Full transaction history across all accounts.
--    Used for transaction status, failed payment, and dispute inquiries.
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS transactions;

CREATE TABLE transactions (
    transaction_id       STRING         COMMENT 'Unique transaction ID (TXN-YYYY-NNNNNN)',
    account_id           STRING         COMMENT 'FK → accounts.account_id',
    customer_id          STRING         COMMENT 'FK → customers.customer_id (denormalised for fast lookup)',
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
TBLPROPERTIES ('parquet.compression'='SNAPPY', 'transactional'='false');

LOAD DATA INPATH '/user/banking_chatbot/staging/transactions.csv'
OVERWRITE INTO TABLE transactions;


-- ---------------------------------------------------------------------------
-- 4. loans
--    Active and historical loan accounts.
--    Used for balance, payment schedule, and delinquency inquiries.
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS loans;

CREATE TABLE loans (
    loan_id              STRING         COMMENT 'Unique loan identifier (LOAN-YYYY-NNNN)',
    customer_id          STRING         COMMENT 'FK → customers.customer_id',
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
    collateral           STRING         COMMENT 'Collateral description (NULL for unsecured loans)',
    notes                STRING         COMMENT 'Free-text notes on loan status'
)
COMMENT 'Loan accounts — lookup for balance, payment schedule, and default status'
STORED AS PARQUET
TBLPROPERTIES ('parquet.compression'='SNAPPY', 'transactional'='false');

LOAD DATA INPATH '/user/banking_chatbot/staging/loans.csv'
OVERWRITE INTO TABLE loans;


-- ---------------------------------------------------------------------------
-- 5. cards
--    Debit and credit cards linked to accounts.
--    Used for card status, block reason, and credit limit inquiries.
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS cards;

CREATE TABLE cards (
    card_id              STRING         COMMENT 'Unique card identifier (CARD-NNNNNN)',
    account_id           STRING         COMMENT 'FK → accounts.account_id',
    customer_id          STRING         COMMENT 'FK → customers.customer_id (denormalised)',
    card_type            STRING         COMMENT 'DEBIT | CREDIT',
    card_number_masked   STRING         COMMENT 'Last-4 digits masked (****NNNN)',
    status               STRING         COMMENT 'ACTIVE | BLOCKED | EXPIRED | CANCELLED',
    block_reason         STRING         COMMENT 'ACCOUNT_LOCKED | ACCOUNT_FROZEN | LOAN_DEFAULT | FRAUD | LOST | STOLEN | NULL if ACTIVE',
    expiry_date          DATE           COMMENT 'Card expiry date (last day of month)',
    credit_limit         DECIMAL(18,2)  COMMENT 'Credit limit (NULL for debit cards)',
    current_balance      DECIMAL(18,2)  COMMENT 'Current outstanding balance (NULL for debit cards)',
    available_credit     DECIMAL(18,2)  COMMENT 'Available credit = limit minus balance (NULL for debit)',
    issued_date          DATE           COMMENT 'Date card was issued',
    last_used_date       DATE           COMMENT 'Date of last successful transaction on this card',
    notes                STRING         COMMENT 'Free-text notes on card status'
)
COMMENT 'Payment cards — lookup for card status, block reason, and credit inquiries'
STORED AS PARQUET
TBLPROPERTIES ('parquet.compression'='SNAPPY', 'transactional'='false');

LOAD DATA INPATH '/user/banking_chatbot/staging/cards.csv'
OVERWRITE INTO TABLE cards;


-- ---------------------------------------------------------------------------
-- 6. support_cases
--    Open and historical customer support cases.
--    Used for case status lookups and escalation context.
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS support_cases;

CREATE TABLE support_cases (
    case_id              STRING     COMMENT 'Unique case identifier (CASE-YYYY-NNNN)',
    customer_id          STRING     COMMENT 'FK → customers.customer_id',
    case_type            STRING     COMMENT 'FRAUD_REPORT | ACCOUNT_LOCK | TRANSACTION_DISPUTE | TRANSACTION_INQUIRY | LOAN_INQUIRY | LOAN_DEFAULT | COMPLIANCE | GENERAL',
    subject              STRING     COMMENT 'Short description of the issue',
    status               STRING     COMMENT 'OPEN | IN_PROGRESS | RESOLVED | ESCALATED | CLOSED',
    priority             STRING     COMMENT 'LOW | MEDIUM | HIGH | CRITICAL',
    assigned_agent       STRING     COMMENT 'ID of the agent or team handling the case',
    created_at           TIMESTAMP  COMMENT 'Timestamp when the case was opened',
    updated_at           TIMESTAMP  COMMENT 'Timestamp of the last update',
    resolved_at          TIMESTAMP  COMMENT 'Timestamp when the case was resolved (NULL if open)',
    account_id           STRING     COMMENT 'Primary account referenced in this case',
    transaction_id       STRING     COMMENT 'Space-separated transaction IDs related to this case',
    notes                STRING     COMMENT 'Free-text case notes and resolution details'
)
COMMENT 'Support cases — lookup for case status and escalation context'
STORED AS PARQUET
TBLPROPERTIES ('parquet.compression'='SNAPPY', 'transactional'='false');

LOAD DATA INPATH '/user/banking_chatbot/staging/support_cases.csv'
OVERWRITE INTO TABLE support_cases;


-- =============================================================================
-- Chatbot Query Templates — iceberg-mcp-server uses these patterns
-- =============================================================================

-- 1. Account status lookup by customer ID (most common: "Is my account locked?")
SELECT a.account_id, a.account_type, a.account_number_masked, a.currency,
       a.current_balance, a.available_balance, a.status, a.lock_reason,
       a.last_activity_date, a.daily_transfer_limit
FROM accounts a
WHERE a.customer_id = 'CUST-B003'
ORDER BY a.account_type;


-- 2. Account lookup by masked card number (caller says "my card ending in 8844")
SELECT a.account_id, a.account_type, a.current_balance, a.available_balance,
       a.status, a.lock_reason, c.card_type, c.status AS card_status, c.block_reason
FROM accounts a
JOIN cards c ON a.account_id = c.account_id
WHERE c.card_number_masked = '****8844';


-- 3. Recent transaction history for an account
SELECT transaction_id, transaction_type, amount, currency, merchant_name,
       merchant_category, description, status, initiated_at, completed_at,
       channel, failure_reason
FROM transactions
WHERE account_id = 'ACC-100006'
ORDER BY initiated_at DESC
LIMIT 10;


-- 4. Specific transaction lookup by reference number
SELECT transaction_id, account_id, transaction_type, amount, currency,
       merchant_name, description, status, initiated_at, completed_at,
       channel, failure_reason, notes
FROM transactions
WHERE reference_number = 'REF-2026-CC003';


-- 5. Pending transactions for an account
SELECT transaction_id, transaction_type, amount, currency, merchant_name,
       description, initiated_at, channel, reference_number, notes
FROM transactions
WHERE account_id = 'ACC-100019'
  AND status = 'PENDING'
ORDER BY initiated_at DESC;


-- 6. Loan summary for a customer
SELECT loan_id, loan_type, original_amount, outstanding_balance, interest_rate_pct,
       monthly_payment, next_payment_date, next_payment_amount,
       last_payment_date, payments_overdue, status, maturity_date
FROM loans
WHERE customer_id = 'CUST-B001'
ORDER BY origination_date DESC;


-- 7. Delinquent or defaulted loans (triggers escalation)
SELECT l.loan_id, l.loan_type, l.outstanding_balance, l.payments_overdue,
       l.status, l.last_payment_date, l.next_payment_amount,
       c.full_name, c.email, c.phone
FROM loans l
JOIN customers c ON l.customer_id = c.customer_id
WHERE l.status IN ('DELINQUENT', 'DEFAULT')
ORDER BY l.payments_overdue DESC;


-- 8. Card status for a customer (all cards)
SELECT card_id, card_type, card_number_masked, status, block_reason,
       expiry_date, credit_limit, current_balance, available_credit, last_used_date
FROM cards
WHERE customer_id = 'CUST-B003';


-- 9. Open support cases for a customer
SELECT case_id, case_type, subject, status, priority, created_at, updated_at,
       account_id, transaction_id, notes
FROM support_cases
WHERE customer_id = 'CUST-B003'
  AND status NOT IN ('RESOLVED', 'CLOSED')
ORDER BY created_at DESC;


-- 10. Row count verification after load
SELECT 'customers'      AS table_name, COUNT(*) AS row_count FROM customers
UNION ALL
SELECT 'accounts',                      COUNT(*)               FROM accounts
UNION ALL
SELECT 'transactions',                  COUNT(*)               FROM transactions
UNION ALL
SELECT 'loans',                         COUNT(*)               FROM loans
UNION ALL
SELECT 'cards',                         COUNT(*)               FROM cards
UNION ALL
SELECT 'support_cases',                 COUNT(*)               FROM support_cases;


-- =============================================================================
-- END OF SCRIPT
-- =============================================================================
