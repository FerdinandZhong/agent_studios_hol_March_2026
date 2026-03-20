# Trade Fraud Detection Workflow — Simplified Design

This is a simplified variant of the trade fraud detection workflow. Key differences from the full version:

- **Single input**: `{Attachments}` only — no manual text fields
- **OCR**: PaddleOCR only (`paddle_ocr_tool`) — no RolmOCR
- **Confidence propagation**: Task 1 flags low-confidence fields; Tasks 2–5 note uncertainty rather than failing

## Workflow Overview

The workflow performs 6 sequential tasks:
1. **Document Extraction** — PaddleOCR + LLM field mapping with per-field confidence flags
2. **Price & Anomaly Validation** — Benchmark comparison using fields from Task 1
3. **Compliance Check** — RAG query against Trade Compliance KB using fields from Task 1
4. **Intelligence Correlation** — RAG entity matching against Intelligence KB using fields from Task 1
5. **Network & Collusion Analysis** — SQL pattern analysis using entities from Task 1
6. **Risk Assessment & Report** — Aggregate scores, note low-confidence caveats, generate PDF

## Architecture

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                  TRADE FRAUD DETECTION — SIMPLIFIED WORKFLOW                   │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│   Single input: {Attachments} (invoice image or PDF scan)                     │
│                       │                                                        │
│  ┌────────────┐   ┌───▼──────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐  │
│  │   TASK 1   │   │  TASK 2  │   │  TASK 3  │   │  TASK 4  │   │  TASK 5  │  │
│  │  Document  │──▶│  Price   │──▶│Compliance│──▶│Intellign.│──▶│ Network  │  │
│  │ Extraction │   │  Check   │   │  Check   │   │Correlat. │   │Collusion │  │
│  └─────┬──────┘   └──────────┘   └──────────┘   └──────────┘   └────┬─────┘  │
│        │  extracted_fields JSON + low_confidence_fields[]            │        │
│        │  flows as context into every downstream task                │        │
│        └─────────────────────────────────────────────────────────────┘        │
│                                                                                │
│                                                          ┌──────────┐         │
│                                                          │  TASK 6  │         │
│                                                          │   Risk   │         │
│                                                          │  Report  │         │
│                                                          └──────────┘         │
└────────────────────────────────────────────────────────────────────────────────┘
```

## Confidence Propagation Model

Task 1 produces two outputs that all downstream tasks must respect:

```
extracted_fields: {
  hs_code:           { value: "6109.10",           confidence: 0.97 },
  declared_price:    { value: 0.80,                confidence: 0.91 },
  shipper_name:      { value: "Textile House Ltd", confidence: 0.88 },
  country_of_origin: { value: "Bangladesh",        confidence: 0.94 },
  ...
}
low_confidence_fields: ["broker_name"]   ← fields with confidence < 0.80
```

**Rule for downstream tasks:**
- Use any field regardless of confidence — do not skip or block
- If the field used in a finding appears in `low_confidence_fields`, append `[LOW CONFIDENCE — verify manually]` to that specific finding
- Include `extraction_caveats` in each task's output listing which findings are affected

---

## Task Definitions

### Task 1: Document Extraction

**Description:**
Use `paddle_ocr_tool` with `action: "infer"`, `image_source` set to `{Attachments}`, and `output_mode: "lines"` to extract raw OCR text with per-line confidence scores. The `lines` output returns a JSON array where each entry has `"text"` and `"confidence"` (0–1). Pass the full `lines` array to the LLM with the following instruction: map each OCR line to one of the canonical trade fields — `hs_code`, `product_description`, `declared_unit_price`, `declared_total_value`, `currency`, `country_of_origin`, `port_of_loading`, `port_of_discharge`, `destination_country`, `shipper_name`, `consignee_name`, `broker_name`, `document_type`, `declaration_id`. For each mapped field, record the confidence of the OCR line(s) that support it. If a field is not found in the OCR output, record it as `null` with confidence `0.0`. After mapping, produce a `low_confidence_fields` list containing the names of all fields whose supporting OCR confidence is below **0.80**, or that were inferred by the LLM rather than directly read from the text.

**Expected Output:**
```json
{
  "document_type": "invoice",
  "declaration_id": "INV-2024-00123",
  "extracted_fields": {
    "hs_code":              { "value": "6109.10",           "confidence": 0.97 },
    "product_description":  { "value": "Men's cotton T-shirts", "confidence": 0.95 },
    "declared_unit_price":  { "value": 0.80,                "confidence": 0.91 },
    "declared_total_value": { "value": 8000.00,             "confidence": 0.93 },
    "currency":             { "value": "USD",               "confidence": 0.99 },
    "country_of_origin":    { "value": "Bangladesh",        "confidence": 0.94 },
    "port_of_loading":      { "value": "Chittagong",        "confidence": 0.89 },
    "port_of_discharge":    { "value": "Felixstowe",        "confidence": 0.88 },
    "destination_country":  { "value": "United Kingdom",   "confidence": 0.92 },
    "shipper_name":         { "value": "Textile House Ltd", "confidence": 0.88 },
    "consignee_name":       { "value": "ABC Trading UK Ltd","confidence": 0.87 },
    "broker_name":          { "value": "FastClear Logistics Ltd", "confidence": 0.76 }
  },
  "low_confidence_fields": ["broker_name"],
  "ocr_line_count": 84,
  "overall_extraction_confidence": 0.91
}
```

**Success Criteria:**
- `paddle_ocr_tool` called with `output_mode: "lines"` to capture per-line confidence
- All 12 canonical fields attempted
- `low_confidence_fields` list produced (may be empty)
- Output is valid JSON

---

### Task 2: Price & Anomaly Validation

**Description:**
Task 1's output is already available in your context — do not re-gather or re-plan. Extract the values for `hs_code`, `country_of_origin`, `declared_unit_price`, `shipper_name`, and `consignee_name` from the context now. If any value is null or missing, substitute the string `UNKNOWN` in its place and continue. Note which fields appear in `low_confidence_fields`.

**Execute the following three SQL queries immediately** using `execute_query` (`iceberg-mcp-server`). Do not defer, repeat your planning, or wait — call the tool now with whatever values you have:

1. Benchmark lookup: `SELECT hs_code, avg_unit_price, price_std_dev, min_price, max_price, sample_count FROM trade_price_benchmarks WHERE hs_code = '<hs_code from Task 1>' AND origin_country = '<country_of_origin from Task 1>'`
2. Recent comparable transactions: `SELECT declared_unit_price, declaration_date, country_of_origin FROM trade_declarations WHERE hs_code = '<hs_code>' ORDER BY declaration_date DESC LIMIT 100`
3. Entity baseline: `SELECT COUNT(*) AS shipment_count, AVG(declared_total_value) AS avg_value FROM trade_declarations WHERE shipper_name = '<shipper_name from Task 1>' OR consignee_name = '<consignee_name from Task 1>'`

After all three queries return results, compute price deviation: `(benchmark_avg - declared_price) / benchmark_avg * 100` and z-score: `(declared_price - benchmark_avg) / price_std_dev`. Flag as `UNDER_INVOICING` if z-score < -2.0 or declared price < 30% of benchmark average. Normalise anomaly score: `min(abs(z_score) / 4.0, 1.0)`. Append `[LOW CONFIDENCE — verify manually]` to any `risk_indicators` entry that relies on a field in `low_confidence_fields`. Do not re-execute any query that has already returned a result.

**Expected Output:**
```json
{
  "price_validation": {
    "declared_unit_price": 0.80,
    "benchmark_avg_price": 3.20,
    "benchmark_std_dev": 0.65,
    "price_deviation_pct": 75.0,
    "z_score": -3.69,
    "anomaly_score": 0.92,
    "flag": "UNDER_INVOICING"
  },
  "entity_baseline": {
    "shipment_count": 12,
    "avg_declared_value": 1050.00,
    "volume_anomaly": false
  },
  "risk_indicators": [
    "Declared price USD 0.80 is 75% below benchmark avg USD 3.20 for HS 6109.10 / Bangladesh",
    "Z-score of -3.69 is well below the -2.0 anomaly threshold"
  ],
  "extraction_caveats": []
}
```

**Success Criteria:**
- Benchmark data retrieved via `execute_query`
- Z-score and anomaly score computed
- `extraction_caveats` populated if any field used was low-confidence

---

### Task 3: Compliance Check

**Description:**
Task 1's output is already available in your context — do not re-gather or re-plan. Extract the values for `hs_code`, `country_of_origin`, `destination_country`, `port_of_loading`, `port_of_discharge`, and `product_description` from the context now. If any value is null or missing, substitute the string `UNKNOWN` in its place and continue. Note which of these fields appear in `low_confidence_fields`.

**Execute the following three RAG queries immediately** using `rag_studio_tool` with `action: "query"` against the **Trade Compliance Knowledge Base**. Do not defer, repeat your planning, or wait — call the tool now with whatever values you have:

1. `"HS code <hs_code> import requirements certificate quota restrictions <country_of_origin> to <destination_country>"`
2. `"Rules of Origin <country_of_origin> <hs_code> preferential origin documentary evidence"`
3. `"shipping route <port_of_loading> to <port_of_discharge> transshipment risk origin washing"`

After all three queries return results, use LLM reasoning to: (a) assess whether the product description matches the declared HS code, (b) verify origin plausibility, (c) identify required certificates and flag any that are absent from Task 1's extraction. For findings based on low-confidence fields, append `[LOW CONFIDENCE — verify manually]` to the relevant breach entry. Do not re-execute any query that has already returned a result.

**Expected Output:**
```json
{
  "hs_code_validity": {
    "declared_hs_code": "6109.10",
    "description_match_score": 0.92,
    "potential_misclassification": false,
    "suggested_correct_hs_code": null
  },
  "origin_compliance": {
    "origin_credible": true,
    "rules_of_origin_met": false,
    "origin_washing_risk": false
  },
  "required_certificates": ["Form A (GSP Certificate of Origin)"],
  "missing_certificates": ["Form A (GSP Certificate of Origin)"],
  "breach_list": [
    "Missing Form A required for GSP preferential duty rate on HS 6109.10 from Bangladesh"
  ],
  "compliance_risk_score": 0.70,
  "extraction_caveats": []
}
```

**Success Criteria:**
- Three RAG queries executed against Compliance KB
- HS code consistency assessed by LLM
- `breach_list` is explicit and actionable
- `extraction_caveats` populated if any field used was low-confidence

---

### Task 4: Intelligence Correlation

**Description:**
Task 1's output is already available in your context — do not re-gather or re-plan. Extract the values for `shipper_name`, `consignee_name`, `broker_name`, `country_of_origin`, `destination_country`, and `hs_code` from the context now. If any value is null or missing, substitute the string `UNKNOWN` in its place and continue. Note which of these fields appear in `low_confidence_fields` — entity matches on low-confidence names require manual verification.

**Execute the following four RAG queries immediately** using `rag_studio_tool` with `action: "query"` against the **Intelligence Reports Knowledge Base**. Do not defer, repeat your planning, or wait — call the tool now with whatever values you have:

1. `"fraud risk sanctions <shipper_name> <country_of_origin> textile trade"`
2. `"fraud network import <consignee_name> under-invoicing"`
3. `"customs broker collusion <broker_name>"`
4. `"trade fraud <country_of_origin> to <destination_country> <hs_code> known schemes"`

After all four queries return results, note the similarity score of the top retrieved chunk for each. Pass all results to the LLM to assess alias likelihood, transliteration variants, and subsidiary relationships. For any entity in `low_confidence_fields`, downgrade the match confidence and append `[LOW CONFIDENCE — OCR quality low, verify entity name]` to the match entry. Do not re-execute any query that has already returned a result.

**Expected Output:**
```json
{
  "entity_matches": [
    {
      "entity_name": "Textile House Ltd",
      "entity_role": "shipper",
      "matched_record": "OLAF Bulletin 2023 — South Asian Textile Under-Invoicing Network",
      "similarity_score": 0.87,
      "match_type": "fraud_network",
      "risk_level": "HIGH"
    },
    {
      "entity_name": "FastClear Logistics Ltd",
      "entity_role": "broker",
      "matched_record": null,
      "similarity_score": 0.21,
      "match_type": "no_match",
      "risk_level": "CLEAR",
      "caveat": "[LOW CONFIDENCE — OCR quality low, verify entity name]"
    }
  ],
  "route_intelligence": {
    "known_fraud_schemes": ["Textile under-invoicing Bangladesh-UK corridor"],
    "risk_narrative": "Bangladesh-UK textile corridor flagged in 2023 OLAF bulletin for systematic under-invoicing."
  },
  "overall_intelligence_score": 0.79,
  "extraction_caveats": ["broker_name extracted with confidence 0.76 — match result requires manual verification"]
}
```

**Success Criteria:**
- Four RAG queries executed
- All three entities screened
- `caveat` added to any match result where the entity name was low-confidence
- `extraction_caveats` list populated accordingly

---

### Task 5: Network & Collusion Analysis

**Description:**
Task 1's output is already available in your context — do not re-gather or re-plan. Extract the values for `shipper_name`, `consignee_name`, `broker_name`, and `hs_code` from the context now. If any value is null or missing, substitute the string `UNKNOWN` in its place and continue. Note which of these fields appear in `low_confidence_fields` — results derived from low-confidence names will be flagged as uncertain.

**Execute the following three SQL queries immediately** using `execute_query` (`iceberg-mcp-server`). Do not defer, repeat your planning, or wait — call the tool now with whatever values you have:

1. Inspector-broker co-occurrence: `SELECT officer_id, broker_name, COUNT(*) AS clearance_count, AVG(processing_time_hrs) AS avg_hrs FROM customs_clearances WHERE clearance_date > DATE_ADD(CURRENT_DATE(), -365) GROUP BY officer_id, broker_name HAVING COUNT(*) > 10 ORDER BY clearance_count DESC`
2. Trading network: `SELECT shipper_name, consignee_name, COUNT(*) AS txn_count, AVG(declared_unit_price) AS avg_price FROM trade_declarations WHERE shipper_name = '<shipper_name>' OR consignee_name = '<consignee_name>' GROUP BY shipper_name, consignee_name ORDER BY txn_count DESC`
3. Split shipment detection: `SELECT declaration_date, declared_total_value, quantity FROM trade_declarations WHERE shipper_name = '<shipper_name>' AND consignee_name = '<consignee_name>' AND hs_code = '<hs_code>' AND declaration_date > DATE_ADD(CURRENT_DATE(), -90) ORDER BY declaration_date`

After all three queries return results, pass the result sets to the LLM to synthesise collusion patterns, identify split shipment schemes, and compute `collusion_risk_score`. Append `[LOW CONFIDENCE]` to any finding derived from a low-confidence entity name. Do not re-execute any query that has already returned a result.

**Expected Output:**
```json
{
  "collusion_indicators": {
    "suspicious_officer_broker_pairs": [
      { "officer_id": "OFF-0042", "broker_name": "FastClear Logistics Ltd",
        "clearance_count": 34, "anomaly_score": 0.81 }
    ],
    "highest_risk_pair": "OFF-0042 / FastClear Logistics Ltd (34 clearances)"
  },
  "trading_network": {
    "connected_entities": ["Textile House Ltd", "ABC Trading UK Ltd", "Global Fabrics SARL"],
    "network_avg_price": 0.87,
    "cluster_risk": true
  },
  "split_shipment_analysis": {
    "shipment_count_last_90_days": 7,
    "split_scheme_detected": true,
    "threshold_avoidance_pattern": "7 shipments in 90 days all declared below £1,000 CIF threshold"
  },
  "collusion_risk_score": 0.77,
  "extraction_caveats": ["broker_name low-confidence — inspector-broker pairing requires manual confirmation"]
}
```

**Success Criteria:**
- Three SQL queries executed
- Inspector-broker anomalies identified
- Split shipment pattern assessed
- `extraction_caveats` populated where applicable

---

### Task 6: Risk Assessment & Report

**Description:**
Aggregate all findings from Tasks 2–5. Collect all `extraction_caveats` entries from every task into a single list. Compute composite score: `(price_anomaly_score × 0.25) + (compliance_risk_score × 0.20) + (intelligence_score × 0.30) + (collusion_risk_score × 0.25)`. Classify: 0.0–0.30 = LOW, 0.30–0.60 = MEDIUM, 0.60–0.80 = HIGH, 0.80–1.00 = CRITICAL. If any fields used in HIGH or CRITICAL findings appear in `low_confidence_fields`, add a mandatory human-review note.

Assemble a `markdown_content` string matching the report format shown in **Expected Output** — populated with real values from Tasks 1–5 — then call `write_to_shared_pdf` with `output_file: "fraud_investigation_brief.pdf"` and that `markdown_content`. Do not call the tool until the full markdown is ready.

**Expected Output:**

The agent's final JSON output:
```json
{
  "case_summary": {
    "declaration_id": "INV-2024-00123",
    "shipper_name": "Textile House Ltd",
    "consignee_name": "ABC Trading UK Ltd",
    "hs_code": "6109.10",
    "declared_value": 8000.00
  },
  "score_breakdown": {
    "price_anomaly_score": 0.92,
    "compliance_risk_score": 0.70,
    "intelligence_score": 0.79,
    "collusion_risk_score": 0.0,
    "composite_risk_score": 0.81
  },
  "risk_level": "HIGH",
  "recommended_action": "Hold shipment. Refer to Fraud Investigation Unit. Manual verification required for low-confidence fields before prosecution.",
  "evidence_chain": [
    "Price 75% below HS 6109.10 benchmark — z-score -3.69 (anomaly score 0.92)",
    "Missing Form A GSP certificate",
    "Shipper matches OLAF 2023 fraud network bulletin (similarity 0.87)",
    "No shipments detected in the last 90 days."
  ],
  "extraction_quality": {
    "low_confidence_fields": ["broker_name", "consignee_name"],
    "affected_findings": [
      "Inspector-broker collusion finding (Task 5) — broker_name requires manual OCR verification",
      "Origin compliance finding (Task 3) — consignee_name requires manual OCR verification"
    ],
    "overall_ocr_confidence": 0.91
  },
  "report_path": "/shared/fraud_investigation_brief.pdf"
}
```

The `markdown_content` passed to `write_to_shared_pdf` must render a report in this format, with all values populated from Tasks 1–5 (example shown for the sample case):

```markdown
# TRADE FRAUD INVESTIGATION BRIEF
**Classification:** RESTRICTED — FOR AUTHORIZED USE ONLY
**Generated:** 2024-06-15
**Case Reference:** INV-2024-00123

---

## RISK VERDICT

| Field | Value |
|---|---|
| **Risk Level** | HIGH |
| **Composite Score** | 0.81 / 1.00 |
| **Recommended Action** | Hold shipment. Refer to Fraud Investigation Unit. Manual verification required for low-confidence fields before prosecution. |

---

## CASE SUMMARY

| Field | Value |
|---|---|
| Declaration ID | INV-2024-00123 |
| Shipper | Textile House Ltd |
| Consignee | ABC Trading UK Ltd |
| HS Code | 6109.10 |
| Declared Value | USD 8000.00 |
| Country of Origin | Bangladesh |
| Route | Chittagong → Felixstowe |

---

## SCORE BREAKDOWN

| Module | Score | Weight | Contribution |
|---|---|---|---|
| Price Anomaly (Task 2) | 0.92 | 25% | 0.23 |
| Compliance (Task 3) | 0.70 | 20% | 0.14 |
| Intelligence (Task 4) | 0.79 | 30% | 0.24 |
| Network / Collusion (Task 5) | 0.00 | 25% | 0.00 |
| **Composite** | **0.81** | 100% | — |

---

## EVIDENCE CHAIN

1. Price 75% below HS 6109.10 benchmark — z-score -3.69 (anomaly score 0.92)
2. Missing Form A GSP certificate
3. Shipper matches OLAF 2023 fraud network bulletin (similarity 0.87)
4. No shipments detected in the last 90 days.

---

## MODULE FINDINGS

### Price & Anomaly Validation
- Declared unit price: USD 0.80
- Benchmark average: USD 3.20 (std dev: 0.65)
- Price deviation: 75% below benchmark
- Z-score: -3.69 | Anomaly score: 0.92
- Flag: **UNDER_INVOICING**

### Compliance Check
- HS code validity: 6109.10 — description match score 0.92
- Potential misclassification: false
- Origin credible: true | Rules of Origin met: false
- Required certificates: Form A (GSP Certificate of Origin)
- **Missing certificates: Form A (GSP Certificate of Origin)**
- Compliance risk score: 0.70

**Breaches:**
- Missing Form A required for GSP preferential duty rate on HS 6109.10 from Bangladesh

> ⚠ Extraction caveats: consignee_name extracted with confidence 0.76 — compliance finding requires manual verification

### Intelligence Correlation
- **Textile House Ltd** (shipper): HIGH — OLAF Bulletin 2023 South Asian Textile Under-Invoicing Network (similarity 0.87)
- **FastClear Logistics Ltd** (broker): CLEAR — no match (similarity 0.21) [LOW CONFIDENCE — OCR quality low, verify entity name]
- Known fraud schemes: Textile under-invoicing Bangladesh-UK corridor
- Route intelligence: Bangladesh-UK textile corridor flagged in 2023 OLAF bulletin for systematic under-invoicing.
- Overall intelligence score: 0.79

### Network & Collusion Analysis
- Suspicious officer-broker pairs: None detected
- Connected trading entities: Textile House Ltd, ABC Trading UK Ltd
- Split shipments (last 90 days): 0
- Split scheme detected: false
- Collusion risk score: 0.00

---

## EXTRACTION QUALITY

| Field | Confidence | Status |
|---|---|---|
| hs_code | 0.97 | OK |
| product_description | 0.95 | OK |
| declared_unit_price | 0.91 | OK |
| declared_total_value | 0.93 | OK |
| currency | 0.99 | OK |
| country_of_origin | 0.94 | OK |
| port_of_loading | 0.89 | OK |
| port_of_discharge | 0.88 | OK |
| destination_country | 0.92 | OK |
| shipper_name | 0.88 | OK |
| consignee_name | 0.76 | LOW CONFIDENCE |
| broker_name | 0.76 | LOW CONFIDENCE |

**Overall OCR confidence:** 0.91

**Affected findings:**
- Inspector-broker collusion finding (Task 5) — broker_name requires manual OCR verification
- Origin compliance finding (Task 3) — consignee_name requires manual OCR verification

> ⚠ **MANDATORY HUMAN REVIEW:** The above HIGH findings rely on low-confidence OCR fields and must be manually verified before enforcement action is taken.

---

## APPROVAL

| Role | Name | Signature | Date |
|---|---|---|---|
| Reviewing Officer | | | |
| Senior Supervisor | | | |
| Fraud Unit Referral | | | |

*This brief was generated automatically by the Trade Fraud Detection System. All findings must be reviewed by a qualified officer before enforcement action is taken.*
```

**Success Criteria:**
- Composite score correctly computed from Tasks 2–5
- `markdown_content` fully populated before `write_to_shared_pdf` is called
- Mandatory human-review block present when `risk_level` is HIGH or CRITICAL and `low_confidence_fields` is non-empty
- `report_path` returned in JSON output

---

## Agent Definitions

### Agent 1: Document Analyst

| Attribute | Value |
|---|---|
| **Name** | Document Analyst |
| **Role** | Trade Document OCR Extraction and Confidence Assessment Specialist |

**Backstory:**
You are a specialist in processing trade and customs documentation using PaddleOCR. You understand Harmonized System codes, Incoterms, and the critical fields customs authorities rely on. You use PaddleOCR to extract raw text with per-line confidence scores, then map those lines to the canonical trade schema. Crucially, you are honest about uncertainty — any field whose OCR support is below your confidence threshold is explicitly flagged so downstream agents can qualify their findings rather than act blindly on unreliable data.

**Goal:**
1. Call `paddle_ocr_tool` with `output_mode: "lines"` to obtain text + confidence per line.
2. Map OCR lines to the 12 canonical trade fields using LLM reasoning.
3. Record the OCR confidence for each mapped field.
4. Produce `low_confidence_fields` list for all fields with confidence < 0.80 or inferred rather than directly read.
5. Output structured JSON consumed by all downstream agents.

**Tools:** `paddle_ocr_tool` (action: `infer`, output_mode: `lines`)

---

### Agent 2: Price Validator

| Attribute | Value |
|---|---|
| **Name** | Price Validator |
| **Role** | Trade Price Anomaly Detection Specialist |

**Backstory:**
You detect under-invoicing and over-invoicing by comparing declared prices against historical benchmarks. You use SQL to query price benchmarks and entity history. When the declared price is implausible, you compute a z-score and flag the anomaly. You are aware that OCR extraction may be imperfect and qualify your findings accordingly.

**Goal:**
1. Read `hs_code`, `declared_unit_price`, `country_of_origin`, `shipper_name`, `consignee_name` from Task 1.
2. Query price benchmarks and entity baseline via `execute_query`.
3. Compute z-score and anomaly score.
4. Append `[LOW CONFIDENCE]` qualifier to findings derived from low-confidence fields.

**Tools:** `iceberg-mcp-server` (`execute_query`, `get_schema`)

---

### Agent 3: Compliance Auditor

| Attribute | Value |
|---|---|
| **Name** | Compliance Auditor |
| **Role** | Trade Compliance and Regulatory Breach Specialist |

**Backstory:**
You are a senior customs compliance officer expert in Rules of Origin, preferential trade agreements, and certificate requirements. You query a compliance knowledge base and use LLM reasoning to cross-reference declaration fields against applicable regulations. You qualify any compliance finding that relies on a low-confidence extracted field.

**Goal:**
1. Read key fields from Task 1 (hs_code, origin, route, product description).
2. Execute three targeted RAG queries against the Trade Compliance KB.
3. Assess HS code consistency, origin plausibility, and certificate completeness.
4. Flag breaches; qualify any finding based on a low-confidence field.

**Tools:** `rag_studio_tool` (action: `query`, KB: Trade Compliance KB)

---

### Agent 4: Intelligence Analyst

| Attribute | Value |
|---|---|
| **Name** | Intelligence Analyst |
| **Role** | Trade Intelligence and Entity Screening Specialist |

**Backstory:**
You screen trade entities against intelligence reports, fraud bulletins, and sanctions records using semantic search. You understand that OCR name extraction can produce minor errors — you use LLM reasoning to assess whether near-matches are aliases, transliterations, or coincidences. For entity names with low OCR confidence, you explicitly downgrade match certainty and flag for manual review.

**Goal:**
1. Read entity names and route from Task 1.
2. Execute four RAG queries against the Intelligence Reports KB.
3. Assess alias/transliteration likelihood via LLM.
4. Downgrade and caveat any match result based on a low-confidence entity name.

**Tools:** `rag_studio_tool` (action: `query`, KB: Intelligence Reports KB)

---

### Agent 5: Network Analyst

| Attribute | Value |
|---|---|
| **Name** | Network Analyst |
| **Role** | Collusion Detection and Trading Network Specialist |

**Backstory:**
You detect broker-inspector collusion and split shipment schemes using SQL co-occurrence analysis. You synthesise patterns across three queries to identify systematic fraud. When entity names are low-confidence, you flag the resulting collusion findings for manual verification.

**Goal:**
1. Read entity identifiers from Task 1.
2. Execute three SQL queries (co-occurrence, network, split shipments).
3. Synthesise patterns into `collusion_risk_score`.
4. Append `[LOW CONFIDENCE]` to any finding using a low-confidence entity name.

**Tools:** `iceberg-mcp-server` (`execute_query`, `get_schema`)

---

### Agent 6: Risk Officer

| Attribute | Value |
|---|---|
| **Name** | Risk Officer |
| **Role** | Fraud Risk Aggregator and Investigation Brief Author |

**Backstory:**
You synthesise findings from all specialist agents into a defensible investigation brief. You understand that OCR quality affects evidentiary strength — your report explicitly separates high-confidence findings from those requiring manual field verification, ensuring investigators know exactly which parts of the case are solid and which need further confirmation before enforcement action.

**Goal:**
1. Aggregate all task outputs and `extraction_caveats`.
2. Compute composite risk score and classify risk level.
3. Assemble the full markdown report using the template in Task 6 — populate every section (case summary, score breakdown table, evidence chain, per-module findings, per-field extraction quality table, mandatory human-review block if applicable, approval table).
4. Call `write_to_shared_pdf` once with the completed `markdown_content` to produce the PDF.

**Tools:** `write_to_shared_pdf`

---

## Workflow Summary

| Stage | Task | Agent | Tools | Input | Output |
|---|---|---|---|---|---|
| 1 | Document Extraction | Document Analyst | `paddle_ocr_tool` | `{Attachments}` | Extracted fields JSON + `low_confidence_fields` |
| 2 | Price Validation | Price Validator | `iceberg-mcp-server` | Task 1 output | Price anomaly score + caveats |
| 3 | Compliance Check | Compliance Auditor | `rag_studio_tool` (Compliance KB) | Task 1 output | Breach list + caveats |
| 4 | Intelligence Correlation | Intelligence Analyst | `rag_studio_tool` (Intel KB) | Task 1 output | Entity matches + caveats |
| 5 | Network & Collusion | Network Analyst | `iceberg-mcp-server` | Task 1 output | Collusion indicators + caveats |
| 6 | Risk Report | Risk Officer | `write_to_shared_pdf` | Tasks 2–5 outputs | Investigation brief PDF |

---

## Required Tools

| Tool | Agent | Key Parameters |
|---|---|---|
| `paddle_ocr_tool` | Agent 1 | `action: "infer"`, `image_source: {Attachments}`, `output_mode: "lines"` |
| `iceberg-mcp-server` → `execute_query` | Agents 2 & 5 | `sql_query` |
| `iceberg-mcp-server` → `get_schema` | Agents 2 & 5 | — |
| `rag_studio_tool` | Agents 3 & 4 | `action: "query"` |
| `write_to_shared_pdf` | Agent 6 | `output_file`, `markdown_content` |

---

## Confidence Threshold Reference

| Threshold | Meaning |
|---|---|
| ≥ 0.90 | High confidence — use without caveat |
| 0.80 – 0.89 | Acceptable — use, no caveat needed |
| < 0.80 | Low confidence — use but append `[LOW CONFIDENCE — verify manually]` |
| 0.00 (null) | Field not found — note as missing; downstream task skips checks requiring this field |
