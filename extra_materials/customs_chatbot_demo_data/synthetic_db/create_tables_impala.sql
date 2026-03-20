-- =============================================================================
-- Customs Chatbot — Impala DDL & Data Load Script
-- =============================================================================
-- Tables required by the Customs Support Agent via the cdw_sql_query tool.
--
-- Run order:
--   1. Create database
--   2. Create tables
--   3. Load CSVs from HDFS staging path
-- =============================================================================

CREATE DATABASE IF NOT EXISTS customs_chatbot_db
COMMENT 'Customs Call Centre Chatbot demo data — CAI Studio workflow';

USE customs_chatbot_db;

-- ---------------------------------------------------------------------------
-- 1. customer_accounts
--    Importer and broker account registry.
--    Used for caller identification and personalisation context.
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS customer_accounts;

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
TBLPROPERTIES ('parquet.compression'='SNAPPY', 'transactional'='false');

LOAD DATA INPATH '/user/customs_chatbot/staging/customer_accounts.csv'
OVERWRITE INTO TABLE customer_accounts;


-- ---------------------------------------------------------------------------
-- 2. shipment_tracking
--    Live and historical shipment status records.
--    The primary table queried by the chatbot for status and duty inquiries.
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS shipment_tracking;

CREATE TABLE shipment_tracking (
    tracking_id               STRING         COMMENT 'Unique shipment tracking ID (TRK-YYYY-NNNNN)',
    declaration_id            STRING         COMMENT 'Customs declaration reference number',
    customer_id               STRING         COMMENT 'FK → customer_accounts.customer_id',
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
TBLPROPERTIES ('parquet.compression'='SNAPPY', 'transactional'='false');

LOAD DATA INPATH '/user/customs_chatbot/staging/shipment_tracking.csv'
OVERWRITE INTO TABLE shipment_tracking;


-- =============================================================================
-- Chatbot Query Templates — the cdw_sql_query tool uses these patterns
-- =============================================================================

-- 1. Status lookup by tracking ID (most common caller query)
SELECT tracking_id, declaration_id, importer_name, product_description, hs_code,
       status, `location`, last_updated, estimated_clearance_date, actual_clearance_date,
       duty_assessed_usd, duty_paid_usd, inspection_type, hold_reason, notes
FROM shipment_tracking
WHERE tracking_id = 'TRK-2024-08812';


-- 2. Status lookup by declaration ID
SELECT tracking_id, declaration_id, importer_name, product_description, hs_code,
       status, `location`, estimated_clearance_date,
       duty_assessed_usd, duty_paid_usd, hold_reason, notes
FROM shipment_tracking
WHERE declaration_id = 'INV-2024-00456';


-- 3. All active shipments for an importer (by name, partial match)
SELECT tracking_id, declaration_id, hs_code, product_description, status,
       port_of_entry, last_updated, estimated_clearance_date,
       duty_assessed_usd, duty_paid_usd
FROM shipment_tracking
WHERE importer_name LIKE '%ABC Trading%'
ORDER BY last_updated DESC
LIMIT 10;


-- 4. Outstanding duty balance check (duty assessed but not fully paid)
SELECT tracking_id, declaration_id, importer_name, status,
       duty_assessed_usd, duty_paid_usd,
       (duty_assessed_usd - duty_paid_usd) AS duty_outstanding_usd
FROM shipment_tracking
WHERE importer_name LIKE '%ABC Trading%'
  AND duty_assessed_usd > duty_paid_usd
ORDER BY last_updated DESC;


-- 5. Held/seized shipments — triggers escalation in Task 3
SELECT tracking_id, declaration_id, importer_name, status,
       `location`, hold_reason, officer_id, notes
FROM shipment_tracking
WHERE status IN ('HELD', 'SEIZED', 'UNDER_APPEAL')
  AND importer_name LIKE '%Denim Discount%';


-- 6. Row count verification after load
SELECT 'customer_accounts'  AS table_name, COUNT(*) AS row_count FROM customer_accounts
UNION ALL
SELECT 'shipment_tracking',                COUNT(*)               FROM shipment_tracking;


-- =============================================================================
-- END OF SCRIPT
-- =============================================================================
