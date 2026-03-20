-- =============================================================================
-- Trade Fraud Detection Workflow — Impala DDL & Data Load Script
-- =============================================================================
-- Tables required by Agent 2 (Price Validator) and Agent 5 (Network Analyst)
-- via the cdw_sql_query tool.
--
-- Run order:
--   1. Create database (if needed)
--   2. Create tables
--   3. Load data from CSV files uploaded to HDFS / S3 / ADLS
--
-- Assumes CSV files have been uploaded to the HDFS path specified in each
-- LOAD DATA statement. Adjust the path to match your CDW environment.
-- =============================================================================


-- ---------------------------------------------------------------------------
-- 0. Database
-- ---------------------------------------------------------------------------
CREATE DATABASE IF NOT EXISTS trade_fraud_db
COMMENT 'Trade fraud detection demo data — CAI Studio workflow'
LOCATION '/user/hive/warehouse/trade_fraud_db.db';

USE trade_fraud_db;


-- ---------------------------------------------------------------------------
-- 1. trade_price_benchmarks
--    Historical average market prices per HS code + origin country.
--    Used by Agent 2 to compute price deviation and anomaly scores.
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS trade_price_benchmarks;

CREATE TABLE trade_price_benchmarks (
    hs_code             STRING        COMMENT 'Harmonized System commodity code (e.g. 6109.10)',
    hs_description      STRING        COMMENT 'Plain-language description of the HS heading',
    origin_country      STRING        COMMENT 'Country of origin as declared (full name)',
    avg_unit_price      DECIMAL(18,4) COMMENT 'Historical average unit price in stated currency',
    price_std_dev       DECIMAL(18,4) COMMENT 'Standard deviation of unit prices in the sample',
    min_price           DECIMAL(18,4) COMMENT 'Minimum observed unit price',
    max_price           DECIMAL(18,4) COMMENT 'Maximum observed unit price',
    sample_count        INT           COMMENT 'Number of transactions used to compute the benchmark',
    currency            STRING        COMMENT 'ISO 4217 currency code (e.g. USD)',
    price_unit          STRING        COMMENT 'Unit of measure for the price (e.g. per piece, per kg)',
    last_updated        DATE          COMMENT 'Date the benchmark was last refreshed'
)
COMMENT 'Price benchmark reference table for under/over-invoicing detection'
STORED AS PARQUET
TBLPROPERTIES (
    'parquet.compression' = 'SNAPPY',
    'transactional'       = 'false'
);

-- Load from CSV (adjust HDFS path as needed)
LOAD DATA INPATH '/user/trade_fraud/staging/trade_price_benchmarks.csv'
OVERWRITE INTO TABLE trade_price_benchmarks;


-- ---------------------------------------------------------------------------
-- 2. trade_declarations
--    Historical trade declaration records.
--    Used by Agent 2 (price benchmarking, entity baseline) and
--    Agent 5 (split shipment detection, trading network mapping).
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS trade_declarations;

CREATE TABLE trade_declarations (
    declaration_id      STRING        COMMENT 'Unique reference ID from the trade document',
    document_type       STRING        COMMENT 'invoice | bill_of_lading | origin_certificate | packing_list',
    hs_code             STRING        COMMENT 'Harmonized System commodity code',
    product_description STRING        COMMENT 'Free-text description of goods',
    declared_unit_price DECIMAL(18,4) COMMENT 'Declared customs unit value',
    declared_total_value DECIMAL(18,2) COMMENT 'Total declared customs value for this line',
    currency            STRING        COMMENT 'ISO 4217 currency code',
    quantity            DECIMAL(18,2) COMMENT 'Declared quantity (numeric)',
    quantity_unit       STRING        COMMENT 'Unit of measure (pcs, kg, units, barrel, etc.)',
    country_of_origin   STRING        COMMENT 'Declared country of origin',
    port_of_loading     STRING        COMMENT 'Port where goods were loaded',
    port_of_discharge   STRING        COMMENT 'Destination port',
    destination_country STRING        COMMENT 'Country of final destination',
    shipper_name        STRING        COMMENT 'Name of the exporting company',
    consignee_name      STRING        COMMENT 'Name of the importing company',
    broker_name         STRING        COMMENT 'Customs broker or freight forwarder',
    declaration_date    DATE          COMMENT 'Date the declaration was lodged',
    incoterms           STRING        COMMENT 'Trade terms (FOB, CIF, EXW, etc.)',
    officer_id          STRING        COMMENT 'ID of the customs officer who handled the declaration',
    status              STRING        COMMENT 'PENDING | CLEARED | HELD | REJECTED'
)
COMMENT 'Historical trade declaration records for price benchmarking and pattern analysis'
STORED AS PARQUET
TBLPROPERTIES (
    'parquet.compression' = 'SNAPPY',
    'transactional'       = 'false'
);

LOAD DATA INPATH '/user/trade_fraud/staging/trade_declarations.csv'
OVERWRITE INTO TABLE trade_declarations;


-- ---------------------------------------------------------------------------
-- 3. customs_clearances
--    Clearance event records linking declarations to officers and brokers.
--    Used by Agent 5 to detect disproportionate officer-broker co-occurrence
--    (potential collusion signal).
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS customs_clearances;

CREATE TABLE customs_clearances (
    clearance_id            STRING        COMMENT 'Unique clearance event ID',
    declaration_id          STRING        COMMENT 'FK → trade_declarations.declaration_id',
    officer_id              STRING        COMMENT 'Customs officer identifier',
    officer_name            STRING        COMMENT 'Full name of customs officer',
    broker_id               STRING        COMMENT 'Customs broker identifier',
    broker_name             STRING        COMMENT 'Trading name of customs broker / freight forwarder',
    clearance_date          DATE          COMMENT 'Date the clearance decision was made',
    processing_time_hrs     DECIMAL(6,2)  COMMENT 'Hours from lodgement to clearance decision',
    declared_value_usd      DECIMAL(18,2) COMMENT 'Declared value in USD at time of clearance',
    duty_assessed_usd       DECIMAL(18,2) COMMENT 'Duty assessed by customs',
    duty_paid_usd           DECIMAL(18,2) COMMENT 'Duty actually paid (may differ if dispute)',
    outcome                 STRING        COMMENT 'CLEARED | HELD | REJECTED | PENDING',
    inspection_type         STRING        COMMENT 'NONE | DOC_CHECK | X_RAY | PHYSICAL | SEIZURE',
    anomaly_flag            STRING        COMMENT 'NONE | LOW | MEDIUM | HIGH — pre-computed risk flag'
)
COMMENT 'Customs clearance event log for officer-broker collusion detection'
STORED AS PARQUET
TBLPROPERTIES (
    'parquet.compression' = 'SNAPPY',
    'transactional'       = 'false'
);

LOAD DATA INPATH '/user/trade_fraud/staging/customs_clearances.csv'
OVERWRITE INTO TABLE customs_clearances;


-- =============================================================================
-- Validation Queries — run after load to verify data is accessible
-- =============================================================================

-- 1. Confirm row counts
SELECT 'trade_price_benchmarks' AS table_name, COUNT(*) AS row_count FROM trade_price_benchmarks
UNION ALL
SELECT 'trade_declarations',                    COUNT(*)               FROM trade_declarations
UNION ALL
SELECT 'customs_clearances',                    COUNT(*)               FROM customs_clearances;


-- 2. Check benchmark for the demo case: HS 6109.10 from Bangladesh
--    Expected: avg_unit_price ≈ 3.20, std_dev ≈ 0.65
SELECT hs_code, origin_country, avg_unit_price, price_std_dev, min_price, max_price, sample_count
FROM trade_price_benchmarks
WHERE hs_code = '6109.10'
AND   origin_country = 'Bangladesh';


-- 3. Task 2 Query A — price benchmark lookup (as called by Agent 2)
SELECT hs_code, avg_unit_price, price_std_dev, min_price, max_price, sample_count
FROM trade_price_benchmarks
WHERE hs_code = '6109.10'
AND   origin_country = 'Bangladesh';


-- 4. Task 2 Query B — recent comparable transactions (as called by Agent 2)
SELECT declared_unit_price, declaration_date, country_of_origin AS shipper_country
FROM trade_declarations
WHERE hs_code = '6109.10'
ORDER BY declaration_date DESC
LIMIT 100;


-- 5. Task 2 Query C — entity baseline for Textile House Ltd (as called by Agent 2)
SELECT
    COUNT(*)             AS shipment_count,
    AVG(declared_total_value) AS avg_value
FROM trade_declarations
WHERE (shipper_name = 'Textile House Ltd' OR consignee_name = 'ABC Trading UK')
AND   declaration_date > DATE_ADD(CURRENT_DATE(), -365);


-- 6. Task 5 Query A — officer-broker co-occurrence analysis (as called by Agent 5)
--    The query that should surface the OFF-0042 / FastClear Logistics anomaly
SELECT
    officer_id,
    broker_name,
    COUNT(*)              AS clearance_count,
    AVG(processing_time_hrs) AS avg_processing_hrs
FROM customs_clearances
WHERE clearance_date > DATE_ADD(CURRENT_DATE(), -365)
GROUP BY officer_id, broker_name
HAVING COUNT(*) > 10
ORDER BY clearance_count DESC;


-- 7. Task 5 Query B — trading network map for Textile House Ltd / ABC Trading UK
SELECT
    shipper_name,
    consignee_name,
    COUNT(*)                   AS txn_count,
    AVG(declared_unit_price)   AS avg_price
FROM trade_declarations
WHERE (shipper_name = 'Textile House Ltd' OR consignee_name = 'ABC Trading UK')
GROUP BY shipper_name, consignee_name
ORDER BY txn_count DESC;


-- 8. Task 5 Query C — split shipment detection (last 90 days)
SELECT
    declaration_date,
    declared_total_value,
    quantity,
    broker_name
FROM trade_declarations
WHERE shipper_name   = 'Textile House Ltd'
AND   consignee_name = 'ABC Trading UK'
AND   hs_code        = '6109.10'
AND   declaration_date > DATE_ADD(CURRENT_DATE(), -90)
ORDER BY declaration_date;


-- =============================================================================
-- END OF SCRIPT
-- =============================================================================
