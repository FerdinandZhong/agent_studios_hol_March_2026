# OLAF Fraud Bulletin — South Asian Textile Under-Invoicing Network (2023)

**Bulletin Reference:** OLAF-FB-2023-TEX-047  
**Issuing Authority:** European Anti-Fraud Office (OLAF) — Trade Fraud Unit (TFU)  
**Classification:** RESTRICTED — For Law Enforcement and Customs Intelligence Use Only  
**Date Issued:** 15 September 2023  
**Distribution:** EU Member State Customs Authorities; HMRC (UK — post-Brexit intelligence sharing MoU); WCO CEN; INTERPOL Financial Crime Unit  

> **SYNTHETIC DOCUMENT NOTICE:** This document is a synthetic demonstration record created for the CAI Studio Trade Fraud Detection Workflow. All named entities, case references, and specific intelligence details are fictional and are provided solely to enable realistic agent testing. Any resemblance to real organisations, individuals, or events is coincidental.

---

## Executive Summary

OLAF's Trade Fraud Unit has identified a systematic **textile under-invoicing network** operating across the Bangladesh–EU and Bangladesh–UK trade corridors. The network involves a cluster of interrelated exporters, freight forwarders, and import-side distributors that have coordinated to suppress declared customs values for knitted cotton garments (primarily HS 6109.10) at between 20% and 30% of market benchmark prices.

The scale of duty evasion is estimated at **EUR 4.2 million per year** across identified network members in the EU, with an additional estimated **GBP 1.8 million per year** in the UK (communicated to HMRC).

This bulletin updates OLAF-FB-2022-TEX-031 and reflects new entities identified through cross-border financial investigation conducted jointly with the Danish Tax Agency, HMRC, and the Bangladesh National Bureau of Revenue (NBR).

---

## Network Structure

### Core Export Entities (Bangladesh Origin)

| Entity | Registration | Role | Risk Level |
|---|---|---|---|
| **Textile House Ltd** | CEPZ, Chittagong, Bangladesh; ETIN 123456789012 | Primary exporter; declared low-value shipments to UK and EU | **HIGH** |
| **Global Fabrics SARL** | Registered: Casablanca, Morocco (shell); Operational: Dhaka, Bangladesh | Secondary exporter; used when Textile House Ltd is under scrutiny | **HIGH** |
| **BD Fashion Exports** | Dhaka Export Processing Zone, Bangladesh | Third-tier exporter used for split shipments | **MEDIUM** |
| **Bengal Cloth Trading** | Narayanganj, Bangladesh (registered); actual control from Dhaka | Used for overflow shipments when TEU capacity is needed | **MEDIUM** |

### Core Import/Distribution Entities (Destination Side)

| Entity | Registration | Role | Risk Level |
|---|---|---|---|
| **ABC Trading UK Ltd** | Felixstowe, UK; Company No. 09876543 | Primary UK consignee for Textile House Ltd shipments | **HIGH** |
| **Global Fabrics SARL** | Also appears as consignee in some EU shipments | Dual-role entity | **HIGH** |
| **EuroCloth Ltd** | Rotterdam, Netherlands | EU consignee for low-value textile shipments from BD Fashion Exports | **MEDIUM** |

### Logistics Facilitators

| Entity | Role | Risk Level |
|---|---|---|
| **FastClear Logistics Ltd** | UK customs broker; HMRC Agent No. GB-CA-20190042. Consistently clears under-invoiced shipments without raising compliance queries. Co-occurrence with specific customs officer (reported separately to HMRC). | **HIGH** |
| **QuickImport UK** | Secondary UK customs broker; used by BD Fashion Exports and Bengal Cloth Trading | **MEDIUM** |

---

## Modus Operandi

### Stage 1: Invoice Preparation
The exporter prepares **two sets of commercial documents**:
- A **customs invoice** with artificially suppressed unit prices (USD 0.75–0.85 per piece for HS 6109.10, compared to the market rate of USD 3.00–3.50)
- A **true invoice** at market rates used for the inter-party settlement via informal value transfer (hawala) or through an intermediary billing entity in a third country (typically a Dubai or Hong Kong registered entity)

### Stage 2: Customs Clearance
The suppressed-price invoice is presented to customs for duty assessment. Using the GSP-origin claim (Bangladesh → EU/UK, 0% duty for Enhanced Preferences), the declared customs value is minimised. Where GSP cannot be claimed (missing Form A), duty is assessed at 12% of the artificially low CIF value — still significantly less than duty on the true value.

Example duty saving per shipment:
- True CIF value: USD 32,000 (10,000 pcs × USD 3.20)
- Declared CIF value: USD 8,000 (10,000 pcs × USD 0.80)
- MFN duty at 12%: USD 3,840 (true) vs. USD 960 (declared)
- **Per-shipment duty evasion: USD 2,880**

### Stage 3: Settlement and Profit Extraction
The difference between the true invoice value and the customs invoice value is transferred through one of:
- **Hawala networks** operating in Chittagong, Dhaka, and London
- **Over-invoicing on reverse shipments** (UK to Bangladesh) to balance transfer value
- **Dubai-based shell company invoicing** — a Dubai LLC invoices Textile House Ltd for "consulting services" at the value equivalent to the suppressed customs value, creating a paper trail that moves money back to the UK buyer's principals

---

## Financial Investigation Findings

Bank account analysis conducted by the Danish Tax Agency and shared under the EU Mutual Assistance framework identified:

- Textile House Ltd maintains accounts at **Pubali Bank, Chittagong** (account 3412-0011-228876) and a parallel account at **Standard Chartered, Dubai** in the name of **Textile House FZCO** (a UAE free zone entity linked to the same beneficial owners)
- ABC Trading UK Ltd has made 47 wire transfers to the Standard Chartered Dubai account totalling **GBP 892,000** over 24 months — amounts inconsistent with the declared transaction values but consistent with true-invoice settlement
- **FastClear Logistics Ltd** director has received personal payments totalling **GBP 34,000** from a third party linked to Textile House Ltd's beneficial ownership structure

---

## Identified Aliases and Associated Entities

The beneficial ownership of Textile House Ltd has been traced (via UK Companies House and Bangladesh NBR) to **Mr. Karim Hussain** (DOB: 1972, Bangladeshi and British national). Mr. Hussain also controls or has controlled:

| Entity Name | Jurisdiction | Relationship |
|---|---|---|
| Textile House Ltd | Bangladesh | Primary exporter |
| Textile House FZCO | Dubai, UAE | Financial conduit |
| KH Garments Ltd | UK | Previously dissolved — prior import vehicle |
| Global Fabrics SARL | Morocco (registered), Bangladesh (operated) | Active network member |
| Apex Knitwear Ltd | Bangladesh | Recently registered — suspected successor entity |

Fuzzy matching note: Documents may show name variations including "Textilehouse Ltd", "Textile Hse Ltd", "THL Exports", "Global Fabric Sarl" (without the 'S'), "Global Fabrics S.A.R.L.", "Global Fabrics International SARL".

---

## Recommended Enforcement Actions

1. **Flag all shipments** from Textile House Ltd, Global Fabrics SARL, BD Fashion Exports, and Bengal Cloth Trading for enhanced examination at the port of discharge.
2. **Require Form A originals** (not copies) for all Bangladesh-origin textile shipments from these entities before GSP preference can be granted.
3. **Refer FastClear Logistics Ltd** to HMRC Customs Brokers Compliance Team for audit of all clearances in the past 24 months.
4. **Request financial intelligence** from NCA (UK National Crime Agency) on ABC Trading UK Ltd.
5. **Issue post-clearance demand notices** for underpaid duty on cleared shipments — estimated recovery: GBP 135,000 for identified shipments (2022–2023).

---

## Intelligence Sharing

This bulletin has been shared with:
- HMRC Intelligence — Trade Fraud Team (Ref: HMRC-TF-2023-1147)
- UK Border Force — National Targeting Centre
- WCO CEN Bulletin Ref: CEN-2023-TEX-0089
- Europol EMPACT — Customs OA Ref: EMPACT-2023-CUST-7

Any new intelligence on entities named in this bulletin should be directed to: **olaf-trade@ec.europa.eu** (OLAF) and **hmrc.tradeintelligence@hmrc.gov.uk** (HMRC).

---

## Annex A: Seizure Summary Table

| Date | Port | Shipper | HS Code | Declared Value | True Value (est.) | Duty Evaded |
|---|---|---|---|---|---|---|
| 14 Jan 2023 | Rotterdam | Global Fabrics SARL | 6109.10 | USD 7,500 | USD 32,000 | EUR 2,920 |
| 03 Mar 2023 | Felixstowe | Textile House Ltd | 6109.10 | USD 8,000 | USD 32,500 | GBP 2,925 |
| 22 Apr 2023 | Hamburg | BD Fashion Exports | 6109.10 | USD 6,800 | USD 31,000 | EUR 2,944 |
| 11 Jun 2023 | Antwerp | Textile House Ltd | 6203.42 | USD 12,000 | USD 65,000 | EUR 6,380 |
| 29 Aug 2023 | Felixstowe | Bengal Cloth Trading | 6110.20 | USD 4,500 | USD 55,000 | GBP 6,075 |

---

*This bulletin expires 12 months from issue date unless renewed. Intelligence should be validated against current sources before enforcement action.*
