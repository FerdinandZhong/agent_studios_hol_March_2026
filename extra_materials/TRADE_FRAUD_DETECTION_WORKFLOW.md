# Trade Fraud Detection Workflow - Agent Design

This document describes the sequential task-agent workflow for automated trade fraud detection using CAI's Agent Studio. The workflow applies reliable fraud rules, anomaly detection, and intelligence correlation to identify trade fraud, internal collusion, compliance breaches, and suspicious activity from trade declarations and historical data.

## Workflow Overview

The trade fraud detection workflow performs the following 6 sequential tasks:
1. **Document Extraction** - OCR and extract key fields from trade documents (invoice, bill of lading, origin certificate)
2. **Price & Anomaly Validation** - Detect under-invoicing by comparing declared values against historical price benchmarks
3. **Compliance Check** - Verify the declaration against trade regulations, HS code rules, and sanctions lists
4. **Intelligence Correlation** - Match entities (shippers, consignees, brokers) against known fraud networks and intelligence reports
5. **Network & Collusion Analysis** - Detect unusual relationships between traders, brokers, and customs officers in transaction history
6. **Risk Assessment & Report** - Aggregate findings, compute a composite risk score, and produce an investigation brief

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                           TRADE FRAUD DETECTION SEQUENTIAL WORKFLOW                                  │
├──────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                      │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐           │
│  │  TASK 1  │   │  TASK 2  │   │  TASK 3  │   │  TASK 4  │   │  TASK 5  │   │  TASK 6  │           │
│  │Document  │──▶│ Price &  │──▶│Compliance│──▶│Intellign.│──▶│ Network  │──▶│  Risk    │           │
│  │Extraction│   │ Anomaly  │   │  Check   │   │Correlat. │   │Collusion │   │Assessment│           │
│  └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘           │
│       │              │              │               │              │              │                  │
│       ▼              ▼              ▼               ▼              ▼              ▼                  │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐           │
│  │ AGENT 1  │   │ AGENT 2  │   │ AGENT 3  │   │ AGENT 4  │   │ AGENT 5  │   │ AGENT 6  │           │
│  │ Document │   │  Price   │   │Compliance│   │Intellign.│   │ Network  │   │   Risk   │           │
│  │ Analyst  │   │Validator │   │ Auditor  │   │ Analyst  │   │ Analyst  │   │ Officer  │           │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘           │
│                                                                                                      │
│  Output:        Output:        Output:         Output:         Output:         Output:               │
│  - Extracted    - Price        - Compliance    - Entity        - Collusion     - Composite           │
│    fields         anomaly        breach          match           clusters        risk score          │
│  - HS codes       flags          list            scores          & flags         (0-1)               │
│  - Declared     - Under-       - Regulation    - Sanction      - Repeat        - Investigation      │
│    values         invoicing      violations      hits            patterns        brief (PDF)         │
│  - Entities       score        - Missing cert. - Similarity    - Network       - Report (PDF)       │
│                                                   scores          graph                             │
└──────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Fraud Detection Scope

| Fraud Type | Detected In | Method |
|---|---|---|
| **Under-invoicing** | Task 2 | Price benchmark comparison (z-score via SQL + LLM anomaly assessment) |
| **HS Code Misclassification** | Task 1 + Task 3 | LLM zero-shot classification + compliance rules KB query |
| **False Origin Declaration** | Task 1 + Task 3 | Route vs. declared origin cross-check |
| **Missing/Forged Certificates** | Task 3 | Compliance rules KB query |
| **Known Fraud Networks** | Task 4 | RAG semantic search over intelligence KB |
| **Sanctions Violations** | Task 4 | LLM-assisted fuzzy entity matching against sanctions lists |
| **Broker-Inspector Collusion** | Task 5 | SQL co-occurrence pattern analysis (GROUP BY + HAVING) |
| **Split Shipment Schemes** | Task 5 | Frequency pattern analysis in transaction history |

---

## Task Definitions

### Task 1: Document Extraction

**Description:**
Use the `agentic_kie_tool` with `action: "extract"` and `image_source` set to `{Attachments}` (the uploaded trade document image or PDF page) to perform OCR and structured key information extraction. The tool uses PaddleOCR and RolmOCR in a multi-agent pipeline to extract all relevant fields. Set `open_schema: true` for dynamic field discovery so no predefined field list is required. After the OCR extraction returns raw text and a preliminary field map, pass the full extracted text to the LLM with a structured prompt to: (1) map any unrecognised or ambiguous fields to the canonical trade schema, (2) infer the most likely HS code from the product description if the declared code is absent or partially legible, and (3) assign a confidence score to each field. The resulting canonical fields to extract are: HS code, declared unit price, total declared value, currency, country of origin, shipper name, consignee name, freight forwarder / customs broker name, shipping route (port of loading → port of discharge), and document type (invoice, bill of lading, origin certificate, packing list). If the source document is a PDF, use `pdf_tool` with `action: "readpdf"` first to extract text, then pass relevant sections for structured parsing.

**Expected Output:**
A JSON object containing extracted trade declaration fields:
- `document_type`: Type of document (invoice/bill_of_lading/origin_certificate/packing_list)
- `declaration_id`: Unique reference number found on the document
- `extracted_fields`: Object containing:
  - `hs_code`: Harmonized System code declared
  - `product_description`: Text description of goods
  - `declared_unit_price`: Numeric value with currency
  - `declared_total_value`: Total declared customs value
  - `currency`: ISO currency code
  - `country_of_origin`: Declared origin country
  - `port_of_loading`: Departure port
  - `port_of_discharge`: Destination port
  - `shipper_name`: Exporting company name
  - `consignee_name`: Importing company name
  - `broker_name`: Customs broker or freight forwarder
  - `quantity`: Declared quantity and unit
- `extraction_confidence`: Overall confidence score (0-1)
- `missing_fields`: List of critical fields not found in the document

**Success Criteria:**
- All critical fields attempted (at least 8 of 12 successfully extracted)
- Confidence score reported for each field
- Document type correctly identified
- Output is valid JSON

---

### Task 2: Price & Anomaly Validation

**Description:**
Use the `execute_query` tool (via `iceberg-mcp-server`) to query the historical price benchmark database. First, retrieve the average market price for the extracted HS code: `SELECT hs_code, avg_unit_price, price_std_dev, min_price, max_price, sample_count FROM trade_price_benchmarks WHERE hs_code = '{hs_code}' AND origin_country = '{country_of_origin}'`. Then retrieve recent comparable transactions: `SELECT declared_unit_price, declaration_date, shipper_country FROM trade_declarations WHERE hs_code = '{hs_code}' ORDER BY declaration_date DESC LIMIT 100`. Compare the declared unit price from Task 1 against these benchmarks. Apply the following rule-based anomaly logic computed arithmetically from the SQL results (no ML library required): calculate the price deviation percentage `(benchmark_avg - declared_price) / benchmark_avg * 100` and the z-score `(declared_price - benchmark_avg) / price_std_dev`; if the z-score is below -2.0, or the declared price is less than 30% of the benchmark average, flag as under-invoicing; normalise the z-score to a 0–1 anomaly score using `min(abs(z_score) / 4.0, 1.0)`. Pass the SQL results and the computed statistics to the LLM to generate a natural-language `risk_indicators` list explaining why the price is anomalous in the context of the specific HS code and origin corridor. Additionally query: `SELECT COUNT(*) as shipment_count, AVG(declared_value) as avg_value FROM trade_declarations WHERE (shipper_name = '{shipper}' OR consignee_name = '{consignee}') AND declaration_date > DATEADD(year, -1, CURRENT_DATE)` to establish the entity's baseline shipping behavior.

**Expected Output:**
A JSON anomaly report containing:
- `price_validation`:
  - `declared_unit_price`: Price from Task 1
  - `benchmark_avg_price`: Historical average for this HS/origin
  - `benchmark_std_dev`: Standard deviation
  - `price_deviation_pct`: Percentage below benchmark
  - `anomaly_score`: Normalized score (0-1, higher = more anomalous)
  - `flag`: `"UNDER_INVOICING"`, `"OVER_INVOICING"`, `"NORMAL"`, or `"INSUFFICIENT_DATA"`
  - `confidence`: Confidence in the assessment
- `entity_baseline`:
  - `shipper_shipment_count`: Historical shipment volume
  - `shipper_avg_declared_value`: Typical declared value
  - `volume_anomaly`: Whether current shipment deviates from entity's own history
- `risk_indicators`: List of specific anomaly strings identified

**Success Criteria:**
- Benchmark data retrieved for the HS code
- Price deviation calculated and anomaly score assigned
- Entity baseline established from historical records
- All flags are one of the defined enum values

---

### Task 3: Compliance Check

**Description:**
Use the `rag_studio_tool` with `action: "query"` to check the **Trade Compliance Knowledge Base** (containing HS code regulations, WTO valuation rules, certificate of origin requirements, quota rules, preferential trade agreement conditions, and dual-use goods restrictions). Execute the following targeted queries in sequence:
1. Query: `"HS code {hs_code} import requirements certificate quota restrictions {country_of_origin} to {destination_country}"` — to identify required documentation and applicable restrictions.
2. Query: `"origin declaration rules {country_of_origin} {hs_code} Rules of Origin"` — to verify that the declared country of origin is credible for the product type.
3. Query: `"shipping route {port_of_loading} to {port_of_discharge} risk flags transshipment"` — to identify if the shipping route passes through known transshipment hubs used for origin-washing.
Cross-reference results against the extracted fields from Task 1 using the LLM: check if declared origin matches expected Rules of Origin for the HS code, verify all required certificates are present (Form A, EUR.1, phytosanitary, etc.), and flag if the declared HS code is inconsistent with the product description by prompting the LLM with the product description and asking it to identify the most appropriate HS heading and assess whether the declared code is plausible.

**Expected Output:**
A JSON compliance report containing:
- `hs_code_validity`:
  - `declared_hs_code`: From Task 1
  - `description_match_score`: How well product description matches HS code (0-1)
  - `potential_misclassification`: Boolean
  - `suggested_correct_hs_code`: If misclassification suspected
- `origin_compliance`:
  - `origin_credible`: Boolean — is origin plausible for this HS code?
  - `rules_of_origin_met`: Boolean
  - `origin_washing_risk`: Boolean — suspicious route via transshipment hub
- `required_certificates`: List of certificates required for this HS/trade lane
- `missing_certificates`: Certificates not found in submitted documents
- `applicable_restrictions`: List of quotas, embargoes, or dual-use restrictions
- `breach_list`: Array of specific compliance breaches identified (empty if none)
- `compliance_risk_score`: Numeric score (0-1)

**Success Criteria:**
- At least 2 RAG queries executed against the compliance KB
- HS code consistency assessed
- Origin plausibility evaluated
- All applicable certificates checked
- Breach list is explicit and actionable

---

### Task 4: Intelligence Correlation

**Description:**
Use the `rag_studio_tool` with `action: "query"` against the **Intelligence Reports Knowledge Base** (containing sanctions lists, known fraud network bulletins, seizure records, and suspicious entity profiles). Execute semantic queries for each key entity extracted in Task 1:
1. Shipper query: `"fraud risk profile {shipper_name} {country_of_origin} trade fraud sanctions"`
2. Consignee query: `"fraud risk profile {consignee_name} import fraud network"`
3. Broker query: `"customs broker fraud {broker_name} collusion"`
4. Combined route query: `"trade fraud {country_of_origin} to {destination_country} {hs_code} known schemes"`
For each query, extract the similarity score of top retrieved chunks. A score above 0.75 against a sanctioned entity profile indicates a high-confidence match. After retrieving KB results, pass the entity names and matched records to the LLM with a structured prompt to assess alias likelihood, detect transliteration variants, and identify subsidiary or shell-company relationships — replacing the need for a dedicated embedding-based fuzzy matcher. Additionally, use the `search_internet` tool to check public sanctions databases (OFAC SDN list, UN consolidated list) for the shipper and consignee names when the intelligence KB returns low results.

**Expected Output:**
A JSON intelligence report containing:
- `entity_matches`: Array of match results, each containing:
  - `entity_name`: Name from declaration
  - `entity_role`: `"shipper"`, `"consignee"`, or `"broker"`
  - `matched_record`: Matching intelligence record title/source (null if no match)
  - `similarity_score`: Vector similarity score (0-1)
  - `match_type`: `"sanctions_list"`, `"fraud_network"`, `"seizure_record"`, `"suspicious_profile"`, or `"no_match"`
  - `risk_level`: `"HIGH"`, `"MEDIUM"`, `"LOW"`, or `"CLEAR"`
- `route_intelligence`:
  - `known_fraud_schemes`: List of known fraud patterns for this trade lane
  - `risk_narrative`: Summary of relevant intelligence findings
- `overall_intelligence_score`: Composite entity risk score (0-1)

**Success Criteria:**
- All 3 key entities (shipper, consignee, broker) queried against intelligence KB
- Similarity scores captured for all queries
- Sanctions database checked for high-risk entities
- Match type categorized for each result

---

### Task 5: Network & Collusion Analysis

**Description:**
Use the `execute_query` tool (via `iceberg-mcp-server`) to analyze historical transaction patterns and detect collusion or coordinated fraud schemes. Execute the following queries:
1. Inspector-Broker pattern: `SELECT officer_id, broker_id, COUNT(*) as clearance_count FROM customs_clearances WHERE declaration_date > DATEADD(year, -1, CURRENT_DATE) GROUP BY officer_id, broker_id HAVING COUNT(*) > 10 ORDER BY clearance_count DESC` — flag officer-broker pairs with disproportionately high co-occurrence (potential collusion signal).
2. Shipper-Consignee network: `SELECT shipper_name, consignee_name, COUNT(*) as txn_count, AVG(declared_unit_price) as avg_price FROM trade_declarations WHERE (shipper_name = '{shipper}' OR consignee_name = '{consignee}') GROUP BY shipper_name, consignee_name` — map the full trading network of identified entities.
3. Split shipment detection: `SELECT declaration_date, declared_total_value, quantity FROM trade_declarations WHERE shipper_name = '{shipper}' AND consignee_name = '{consignee}' AND hs_code = '{hs_code}' AND declaration_date > DATEADD(month, -3, CURRENT_DATE) ORDER BY declaration_date` — detect repeated small shipments designed to stay below duty thresholds.
Pass all three SQL result sets to the LLM together with the benchmark average price for the HS code to identify: suspicious inspector-broker pairs (clearance count > 2x the average, computed from the SQL aggregate), tight trading clusters (same shipper-consignee pair with below-market prices), and split shipment patterns (3+ shipments within 30 days with values just below duty-free thresholds). The LLM synthesises the patterns into the `collusion_risk_score` and `threshold_avoidance_pattern` fields. No graph library is required — all network structure is derived from SQL GROUP BY aggregations.

**Expected Output:**
A JSON network analysis report containing:
- `collusion_indicators`:
  - `suspicious_officer_broker_pairs`: List of pairs with `officer_id`, `broker_id`, `clearance_count`, `anomaly_score`
  - `highest_risk_pair`: The most suspicious pairing found
- `trading_network`:
  - `connected_entities`: List of entities linked to the shipper or consignee
  - `network_avg_price`: Average declared price across the network (compare to benchmark)
  - `cluster_risk`: Whether the trading cluster shows consistent under-declaration
- `split_shipment_analysis`:
  - `shipment_count_last_90_days`: Number of shipments
  - `split_scheme_detected`: Boolean
  - `threshold_avoidance_pattern`: Description of the pattern if detected
- `collusion_risk_score`: Composite collusion risk (0-1)

**Success Criteria:**
- Inspector-broker co-occurrence analyzed
- Trading network mapped for both shipper and consignee
- Split shipment history checked for last 90 days
- Risk scores calculated for each collusion dimension

---

### Task 6: Risk Assessment & Report

**Description:**
Aggregate all findings from Tasks 1-5 and compute a composite fraud risk score. Apply the following weighted formula: `composite_score = (price_anomaly_score × 0.25) + (compliance_risk_score × 0.20) + (intelligence_score × 0.30) + (collusion_risk_score × 0.25)`. Classify the composite score: 0.0-0.3 = LOW, 0.3-0.6 = MEDIUM, 0.6-0.8 = HIGH, 0.8-1.0 = CRITICAL. Based on the classification, determine the recommended action: LOW → auto-release, MEDIUM → enhanced documentation check, HIGH → physical inspection + supervisor review, CRITICAL → hold shipment + refer to fraud unit. Use the `write_to_shared_pdf` tool with `output_file: "fraud_investigation_brief.pdf"` to generate a structured investigation report containing the full evidence chain from all agents.

**Expected Output:**
A JSON risk assessment containing:
- `case_summary`:
  - `declaration_id`: From Task 1
  - `shipper_name`: From Task 1
  - `consignee_name`: From Task 1
  - `hs_code`: From Task 1
  - `declared_value`: From Task 1
- `score_breakdown`:
  - `price_anomaly_score`: From Task 2
  - `compliance_risk_score`: From Task 3
  - `intelligence_score`: From Task 4
  - `collusion_risk_score`: From Task 5
  - `composite_risk_score`: Weighted aggregate (0-1)
- `risk_level`: `"LOW"`, `"MEDIUM"`, `"HIGH"`, or `"CRITICAL"`
- `recommended_action`: String describing the disposition
- `evidence_chain`: Array of specific findings from each task that contributed to the score
- `report_path`: Path to the generated PDF investigation brief

**Success Criteria:**
- All 4 component scores present and valid
- Composite score correctly computed
- Risk level matches score range
- PDF investigation brief successfully generated

---

## Agent Definitions

### Agent 1: Document Analyst

| Attribute | Value |
|---|---|
| **Name** | Document Analyst |
| **Role** | Trade Document OCR and Key Information Extractor |

**Backstory:**
You are a specialist in processing trade and customs documentation. You have deep expertise in the structure of international trade documents — commercial invoices, bills of lading, certificates of origin, and packing lists. You understand Harmonized System (HS) codes, Incoterms, and the critical fields that customs authorities rely on to assess duties and verify compliance. You leverage advanced OCR technology (PaddleOCR and RolmOCR) to extract raw text from document images with high accuracy, then use your language understanding capabilities to map ambiguous or partially extracted fields to the canonical trade schema, infer HS codes from product descriptions, and flag any fields that are missing, illegible, or inconsistent. Your extractions form the foundation for all downstream fraud checks.

**Goal:**
1. Accept a trade document image or PDF page as input (`{Attachments}`).
2. Apply OCR extraction using `agentic_kie_tool` in open-schema mode to discover all fields dynamically.
3. Map discovered fields to the canonical trade schema: HS code, declared price, quantity, origin, shipper, consignee, broker, route.
4. Flag any critical fields that are absent or have low confidence.
5. Output a clean, structured JSON that downstream agents can consume directly.

**Tools:** `agentic_kie_tool` (action: `extract`), `pdf_tool` (action: `readpdf`)

**Output Format:**
```json
{
  "document_type": "invoice",
  "declaration_id": "INV-2024-00123",
  "extracted_fields": {
    "hs_code": "6109.10",
    "product_description": "Men's cotton T-shirts",
    "declared_unit_price": 0.80,
    "declared_total_value": 8000.00,
    "currency": "USD",
    "country_of_origin": "Bangladesh",
    "port_of_loading": "Chittagong",
    "port_of_discharge": "Felixstowe",
    "shipper_name": "Textile House Ltd",
    "consignee_name": "ABC Trading UK",
    "broker_name": "FastClear Logistics",
    "quantity": "10000 units"
  },
  "extraction_confidence": 0.91,
  "missing_fields": []
}
```

---

### Agent 2: Price Validator

| Attribute | Value |
|---|---|
| **Name** | Price Validator |
| **Role** | Trade Price Anomaly Detection Specialist |

**Backstory:**
You are an expert in trade valuation and customs fraud, with years of experience in detecting under-invoicing and over-invoicing schemes. You have an encyclopaedic knowledge of commodity price ranges across different HS codes and trade corridors. You know that fraudsters exploit the complexity of customs valuation rules by declaring prices far below market value to minimise duties, or far above market value for money laundering or export subsidy abuse. You use statistical benchmarks and anomaly detection techniques to surface declarations where the declared price is implausible given the product type, origin, and historical data.

**Goal:**
1. Receive the extracted fields from Agent 1 (HS code, declared unit price, origin, shipper, consignee).
2. Query the historical price benchmark database via `execute_query` (`iceberg-mcp-server`) for the relevant HS code and origin.
3. Calculate the deviation of the declared price from the benchmark.
4. Query the entity's own historical declaration history to establish a personal baseline.
5. Output a price anomaly report with an anomaly score and specific flag categories.

**Tools:** `iceberg-mcp-server` (`execute_query`, `get_schema`), `csv_reader` (for supplementary price reference data)

**Output Format:**
```json
{
  "price_validation": {
    "declared_unit_price": 0.80,
    "benchmark_avg_price": 3.20,
    "benchmark_std_dev": 0.65,
    "price_deviation_pct": 75.0,
    "anomaly_score": 0.94,
    "flag": "UNDER_INVOICING",
    "confidence": 0.91
  },
  "entity_baseline": {
    "shipper_shipment_count": 47,
    "shipper_avg_declared_value": 1.10,
    "volume_anomaly": false
  },
  "risk_indicators": [
    "Declared price 75% below HS 6109.10 benchmark for Bangladesh origin",
    "Price below minimum observed in 100 comparable transactions"
  ]
}
```

---

### Agent 3: Compliance Auditor

| Attribute | Value |
|---|---|
| **Name** | Compliance Auditor |
| **Role** | Trade Compliance and Regulatory Breach Specialist |

**Backstory:**
You are a senior customs compliance officer with expertise in international trade regulations, preferential trade agreements, Rules of Origin, and dual-use goods controls. You know that trade fraud often involves misclassifying goods under a lower-duty HS code, falsely declaring the origin to claim preferential tariff treatment, or omitting required certificates (such as Form A for GSP, EUR.1 for EU preferences, or phytosanitary certificates for agricultural goods). You methodically cross-reference every declaration against the applicable regulations and flag every breach with a clear legal reference.

**Goal:**
1. Receive the extracted fields from Agent 1 (HS code, product description, origin, route, document set).
2. Query the Trade Compliance Knowledge Base via `rag_studio_tool` for applicable rules and requirements.
3. Assess HS code consistency — does the product description match the declared code?
4. Evaluate origin plausibility — is the declared origin credible for this product under Rules of Origin?
5. Check the shipping route for transshipment hub risk (origin-washing).
6. Identify all required certificates and flag any that are missing from the submitted documents.
7. Output a structured compliance breach list.

**Tools:** `rag_studio_tool` (action: `query`, Knowledge Base: Trade Compliance KB)

**Output Format:**
```json
{
  "hs_code_validity": {
    "declared_hs_code": "6109.10",
    "description_match_score": 0.88,
    "potential_misclassification": false,
    "suggested_correct_hs_code": null
  },
  "origin_compliance": {
    "origin_credible": true,
    "rules_of_origin_met": false,
    "origin_washing_risk": false
  },
  "required_certificates": ["Form A (GSP Certificate of Origin)", "Export licence"],
  "missing_certificates": ["Form A (GSP Certificate of Origin)"],
  "applicable_restrictions": ["Subject to UK textile quota TRQ-2024-011"],
  "breach_list": [
    "Missing Form A certificate required for GSP preferential duty rate",
    "Declaration does not confirm Rules of Origin local value-added threshold"
  ],
  "compliance_risk_score": 0.72
}
```

---

### Agent 4: Intelligence Analyst

| Attribute | Value |
|---|---|
| **Name** | Intelligence Analyst |
| **Role** | Trade Intelligence and Sanctions Screening Specialist |

**Backstory:**
You are an intelligence professional specialising in trade-based financial crime and sanctions evasion. You have access to a curated intelligence knowledge base containing sanctions lists (OFAC SDN, UN Consolidated, EU Restrictive Measures), known fraud network bulletins, historical seizure records, and suspicious entity profiles. Your primary challenge is that fraudsters use aliases, subsidiary companies, and transliterated names to evade exact-match screening. You use semantic similarity search and fuzzy matching to surface high-confidence entity matches even when names are not identical. You also understand trade corridors known for specific fraud schemes and can contextualise individual declarations against regional fraud intelligence.

**Goal:**
1. Receive entity names (shipper, consignee, broker) and trade route details from Agent 1.
2. Execute semantic searches against the Intelligence Reports Knowledge Base via `rag_studio_tool`.
3. Apply fuzzy matching logic to detect aliases and transliterations.
4. Search public sanctions databases via `search_internet` for entities with no KB matches.
5. Contextualise the trade route against known regional fraud schemes.
6. Output a structured intelligence report with similarity scores and match classifications.

**Tools:** `rag_studio_tool` (action: `query`, Knowledge Base: Intelligence Reports KB), `search_internet`

**Output Format:**
```json
{
  "entity_matches": [
    {
      "entity_name": "Textile House Ltd",
      "entity_role": "shipper",
      "matched_record": "2023 OLAF Bulletin: South Asian Textile Under-Invoicing Network",
      "similarity_score": 0.87,
      "match_type": "fraud_network",
      "risk_level": "HIGH"
    },
    {
      "entity_name": "FastClear Logistics",
      "entity_role": "broker",
      "matched_record": null,
      "similarity_score": 0.21,
      "match_type": "no_match",
      "risk_level": "CLEAR"
    }
  ],
  "route_intelligence": {
    "known_fraud_schemes": ["Textile under-invoicing via Bangladesh corridor", "GSP certificate fraud"],
    "risk_narrative": "Bangladesh-to-UK textile corridor is a known high-risk lane for under-invoicing and GSP fraud per 2023 HMRC intelligence bulletin."
  },
  "overall_intelligence_score": 0.79
}
```

---

### Agent 5: Network Analyst

| Attribute | Value |
|---|---|
| **Name** | Network Analyst |
| **Role** | Collusion Detection and Trading Network Specialist |

**Backstory:**
You are an expert in detecting internal fraud and collusion in customs and trade operations. You understand that the most damaging fraud often involves insiders — a customs officer who consistently clears shipments for a particular broker without adequate scrutiny, or a network of related companies that systematically under-declare values to share duty savings. You use SQL-based co-occurrence analysis and statistical pattern recognition to identify these relationships in transaction history data, and you reason over the results using your language capabilities to synthesise findings into clear collusion risk scores and narratives. You know that a single anomalous transaction is rarely sufficient evidence, but repeated patterns across multiple shipments reveal the systematic nature of organised fraud.

**Goal:**
1. Receive the entity identifiers (shipper, consignee, broker) and HS code from Agent 1.
2. Query the transaction history database via `execute_query` (`iceberg-mcp-server`) for inspector-broker co-occurrence patterns.
3. Map the full trading network of the identified entities.
4. Detect split shipment patterns designed to avoid duty thresholds.
5. Identify any inspector-broker pairs with statistically anomalous co-occurrence rates.
6. Output a network risk assessment with specific collusion indicators.

**Tools:** `iceberg-mcp-server` (`execute_query`, `get_schema`)

**Output Format:**
```json
{
  "collusion_indicators": {
    "suspicious_officer_broker_pairs": [
      {
        "officer_id": "OFF-0042",
        "broker_id": "FastClear Logistics",
        "clearance_count": 34,
        "anomaly_score": 0.81
      }
    ],
    "highest_risk_pair": "OFF-0042 / FastClear Logistics (34 clearances, score: 0.81)"
  },
  "trading_network": {
    "connected_entities": ["Textile House Ltd", "Global Fabrics SARL", "ABC Trading UK"],
    "network_avg_price": 0.85,
    "cluster_risk": true
  },
  "split_shipment_analysis": {
    "shipment_count_last_90_days": 7,
    "split_scheme_detected": true,
    "threshold_avoidance_pattern": "7 shipments in 90 days, all declared below £1,000 CIF threshold"
  },
  "collusion_risk_score": 0.77
}
```

---

### Agent 6: Risk Officer

| Attribute | Value |
|---|---|
| **Name** | Risk Officer |
| **Role** | Fraud Risk Aggregator and Investigation Brief Author |

**Backstory:**
You are a senior fraud risk officer responsible for synthesising intelligence from multiple specialist agents into a clear, actionable investigation brief. You understand that fraud decisions must be defensible — every flag must be traced back to a specific piece of evidence, and the recommended action must be proportionate to the risk level. You communicate clearly with investigators, compliance managers, and legal teams. You know that false positives waste enforcement resources, so you weigh evidence carefully before escalating. Your reports are used as the basis for physical inspections, holds, prosecutions, and audit trails.

**Goal:**
1. Receive all findings from Agents 2-5 (price anomaly, compliance breaches, intelligence matches, network risk).
2. Apply the weighted composite scoring formula to compute the overall risk level.
3. Determine the appropriate disposition (auto-release / enhanced check / inspection / hold).
4. Compile a full evidence chain with specific findings from each agent.
5. Generate a structured PDF investigation brief using `write_to_shared_pdf`.

**Tools:** `write_to_shared_pdf`

**Scoring Formula:**
```
composite_score = (price_anomaly_score × 0.25)
                + (compliance_risk_score × 0.20)
                + (intelligence_score    × 0.30)
                + (collusion_risk_score  × 0.25)

LOW      → 0.0 – 0.30  → Auto-release
MEDIUM   → 0.30 – 0.60 → Enhanced documentation check
HIGH     → 0.60 – 0.80 → Physical inspection + supervisor review
CRITICAL → 0.80 – 1.00 → Hold shipment + refer to fraud unit
```

**Output Format:**
```json
{
  "case_summary": {
    "declaration_id": "INV-2024-00123",
    "shipper_name": "Textile House Ltd",
    "consignee_name": "ABC Trading UK",
    "hs_code": "6109.10",
    "declared_value": 8000.00
  },
  "score_breakdown": {
    "price_anomaly_score": 0.94,
    "compliance_risk_score": 0.72,
    "intelligence_score": 0.79,
    "collusion_risk_score": 0.77,
    "composite_risk_score": 0.81
  },
  "risk_level": "CRITICAL",
  "recommended_action": "Hold shipment immediately and refer to Fraud Investigation Unit. Do not release without senior officer authorisation.",
  "evidence_chain": [
    "Price 75% below HS 6109.10 benchmark (anomaly score: 0.94)",
    "Missing Form A GSP certificate — duty relief not entitled",
    "Shipper matches 2023 OLAF fraud network bulletin (similarity: 0.87)",
    "7 split shipments in 90 days below £1,000 threshold",
    "Inspector OFF-0042 / FastClear Logistics: 34 co-clearances (collusion score: 0.81)"
  ],
  "report_path": "/shared/fraud_investigation_brief.pdf",
  "alert_sent": true
}
```

---

## Workflow Summary

| Stage | Task | Agent | Tools | Input | Output |
|---|---|---|---|---|---|
| 1 | Document Extraction | Document Analyst | `agentic_kie_tool`, `pdf_tool` | Trade document image/PDF | Structured extracted fields JSON |
| 2 | Price & Anomaly Validation | Price Validator | `iceberg-mcp-server` (`execute_query`, `get_schema`), `csv_reader` | HS code, declared price, entities | Price anomaly score + flags |
| 3 | Compliance Check | Compliance Auditor | `rag_studio_tool` (Compliance KB) | HS code, origin, route, doc set | Compliance breach list + score |
| 4 | Intelligence Correlation | Intelligence Analyst | `rag_studio_tool` (Intel KB), `search_internet` | Shipper, consignee, broker, route | Entity match scores + intelligence |
| 5 | Network & Collusion Analysis | Network Analyst | `iceberg-mcp-server` (`execute_query`, `get_schema`) | Shipper, consignee, broker | Collusion indicators + network risk |
| 6 | Risk Assessment & Report | Risk Officer | `write_to_shared_pdf` | All agent outputs | PDF investigation brief |

---

## Required Agent Studio Tools

### 1. `agentic_kie_tool`
Multi-agent OCR pipeline (PaddleOCR + RolmOCR) for structured extraction from trade document images.
- **Action:** `extract`
- **Key Parameters:** `image_source`, `open_schema: true`, `output_mode: "deterministic"`

### 2. `pdf_tool`
PDF text extraction for text-based trade documents.
- **Action:** `readpdf`
- **Key Parameters:** `pdf` (file path or attachment reference)

### 3. `iceberg-mcp-server` (MCP)
SQL queries against the Cloudera Data Warehouse (Iceberg tables) for historical trade data, price benchmarks, and transaction history.

| Tool | Description | Key Parameters |
|---|---|---|
| `execute_query` | Execute a SQL query on the Impala database and return results as JSON | `sql_query` |
| `get_schema` | Retrieve the list of table names in the current Impala database | — |

- **Required Tables:** `trade_price_benchmarks`, `trade_declarations`, `customs_clearances`
- **Usage pattern:** Call `get_schema` once at the start of a SQL-heavy task to confirm table availability, then use `execute_query` for all data retrieval.

### 4. `rag_studio_tool`
Semantic search over pre-loaded knowledge bases.
- **Action:** `query`
- **Knowledge Bases Required:**
  - **Trade Compliance KB:** HS taxonomy, WTO valuation rules, Rules of Origin, certificate requirements
  - **Intelligence Reports KB:** Sanctions lists (OFAC, UN, EU), fraud network bulletins, seizure records

### 5. `search_internet`
Public web search for sanctions database lookups when intelligence KB has insufficient coverage.

### 6. `write_to_shared_pdf`
Generate PDF investigation briefs from structured markdown content.
- **Key Parameters:** `output_file: "fraud_investigation_brief.pdf"`, `markdown_content`

---

## Models and APIs Required

| Model / API | Use | Agent | Notes |
|---|---|---|---|
| **PaddleOCR** (bundled in `agentic_kie_tool`) | Document OCR — raw text extraction from images | Agent 1 | Bundled; no separate deployment needed |
| **RolmOCR** (`reducto/RolmOCR`, bundled in `agentic_kie_tool`) | Structured layout OCR for complex document formats | Agent 1 | Bundled; no separate deployment needed |
| **OpenAI API** (`gpt-4o` or `gpt-4o-mini`) | Field mapping + HS code inference after OCR (Agent 1); anomaly narrative generation (Agent 2); HS code misclassification assessment (Agent 3); alias / fuzzy entity matching (Agent 4); collusion pattern synthesis (Agent 5); investigation brief drafting (Agent 6) | All agents | Single API key; configure in Agent Studio LLM settings |
| **OpenAI Embeddings API** (`text-embedding-3-small`) | Document embeddings for RAG Studio knowledge bases (Compliance KB + Intelligence KB) | Agents 3 & 4 | Configure as the embedding model in RAG Studio KB settings |

---

## Knowledge Base Setup

Both knowledge bases must be created in RAG Studio with **embedding model: `text-embedding-3-small` (OpenAI)**. Set chunk size to 512 tokens with 50-token overlap.

### Trade Compliance KB
Documents to ingest into RAG Studio before running the workflow (sample files available under `extra_materials/trade_fraud_demo_data/task3_task4_knowledge_base/compliance_kb/`):
- HS code taxonomy and classification notes (WCO) — `hs_chapter_61_textile_rules.md`
- Rules of Origin for applicable preferential trade agreements — `rules_of_origin_bangladesh_uk.md`
- Required certificate types per HS chapter (Form A, EUR.1, phytosanitary, etc.) — `gsp_form_a_requirements.md`
- Known high-risk transshipment hub list — `high_risk_transshipment_hubs.md`
- WTO Customs Valuation Agreement guidance (source from WTO website)

### Intelligence Reports KB
Documents to ingest and keep updated (sample files available under `extra_materials/trade_fraud_demo_data/task3_task4_knowledge_base/intelligence_kb/`):
- Agency fraud bulletins (OLAF, HMRC, CBP, WCO CEN bulletins) — `olaf_bulletin_2023_textile_under_invoicing.md`
- Seizure and prosecution records (anonymised) — `seizure_records_2022_2024.md`
- Sanctions and restricted party excerpts — `sanctions_entities_excerpt.md`
- OFAC Specially Designated Nationals (SDN) list (download monthly from treasury.gov)
- UN Consolidated Sanctions List (download monthly from un.org)
- EU Restrictive Measures database (download monthly from eur-lex.europa.eu)

---

## Required Database Tables (CDW)

| Table | Purpose | Key Columns |
|---|---|---|
| `trade_price_benchmarks` | Price reference by HS code + origin | `hs_code`, `origin_country`, `avg_unit_price`, `price_std_dev`, `min_price`, `max_price` |
| `trade_declarations` | Historical declaration records | `declaration_id`, `hs_code`, `shipper_name`, `consignee_name`, `declared_unit_price`, `declaration_date` |
| `customs_clearances` | Clearance records with officer and broker | `declaration_id`, `officer_id`, `broker_id`, `clearance_date`, `outcome` |

---

## Usage Notes

1. **Input Format:** The workflow accepts a trade declaration package — typically a scanned invoice image or PDF. Multiple documents (invoice + bill of lading + origin certificate) can be processed by running Agent 1 multiple times and merging the extracted fields.

2. **Knowledge Base Freshness:** The Intelligence Reports KB should be updated at least monthly with new sanctions list snapshots and agency bulletins to ensure relevant matches.

3. **Scoring Calibration:** The composite score weights (0.25 / 0.20 / 0.30 / 0.25) are a starting baseline. They should be reviewed after 3-6 months of production use and adjusted based on which fraud types are most prevalent in the specific customs context.

4. **Interpreting Risk Scores:**
   - High price anomaly + Low intelligence score → Likely opportunistic under-invoicing by a new entity
   - Low price anomaly + High intelligence score → Known bad actor using market-price camouflage — prioritise for investigation
   - High collusion score + Moderate other scores → Internal integrity issue — escalate to internal affairs
   - High on all dimensions → Organised fraud network — refer to specialist unit

5. **Human-in-the-Loop:** LOW risk cases can be auto-released. All MEDIUM and above cases should be reviewed by a human officer before final disposition. Agent outputs are advisory — final release/hold decisions rest with authorised officers.

6. **Audit Trail:** Every agent output is persisted as part of the workflow run history in Agent Studio, providing a complete audit trail for compliance reporting and legal proceedings.

7. **Multilingual Support:** The `agentic_kie_tool` (PaddleOCR + RolmOCR) supports multilingual document OCR. The OpenAI `gpt-4o` model and `text-embedding-3-small` embeddings natively handle multilingual text, so trade documents in Chinese, Arabic, Spanish, French, and other major trade languages can be processed without additional configuration.
