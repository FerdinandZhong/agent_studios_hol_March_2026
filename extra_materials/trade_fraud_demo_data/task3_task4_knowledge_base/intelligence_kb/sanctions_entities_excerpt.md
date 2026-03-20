# Sanctions and Restricted Party Screening — Excerpt

**Source:** Consolidated from OFAC SDN List, UN Security Council Consolidated List, EU Restrictive Measures Database, UK OFSI Consolidated List  
**Compilation Date:** 1 January 2024  
**Document Type:** Intelligence Knowledge Base — Sanctions Screening Reference  
**Coverage:** Entities relevant to Bangladesh–UK and South Asia–EU trade corridors  

> **SYNTHETIC DOCUMENT NOTICE:** This document is a synthetic demonstration record created for the CAI Studio Trade Fraud Detection Workflow. All named entities, designations, case references, and financial details are fictional and are provided solely to enable realistic agent testing. Any resemblance to real organisations, individuals, or sanctions records is coincidental.

---

## Section 1: Designated Entities — Trade and Financial Sanctions

The following entities are designated under one or more sanctions regimes. Trade with designated entities (directly or indirectly) may constitute a sanctions violation. Customs officers and compliance teams should apply **fuzzy name matching** to account for transliterations, aliases, and subsidiary companies.

---

### 1.1 Entry: HUSSAIN TRADING NETWORK

**Primary Name:** Hussain Trading Network  
**Designating Authority:** OFAC (US Treasury), Ref: SDN-OFAC-2021-3392; UK OFSI Ref: OFSI-FIN-2022-0441  
**Designation Basis:** Trade-based money laundering; under-invoicing scheme facilitating illicit transfer of value; support for proliferation financing  
**Designation Date:** OFAC: 14 March 2021; OFSI: 22 June 2022  

**Known Aliases and Associated Names:**
- Hussain Trade FZCO (UAE)
- H.T. International Ltd (UK — dissolved 2021)
- KH Global Trade Ltd (UK — dissolved 2022)
- Al-Hussain Export Import Co. (Pakistan)
- Textile House FZCO (UAE — beneficial ownership link)

**Known Addresses:**
- Suite 402, Al Fahidi Tower, Deira, Dubai, UAE
- (Former) 14 Commercial Road, London E1 1LT, UK
- (Former) 22 Adamjee Court, Motijheel, Dhaka, Bangladesh

**Beneficial Owner / Key Individual:**
- HUSSAIN, Muhammad Karim — DOB approx. 1972; dual Bangladeshi/British national; known aliases: M.K. Hussain, Karim Hussain, Mohammad Karim

**Relationship to Demo Shipment:**  
The beneficial ownership of **Textile House Ltd** (Chittagong) has been traced to the same beneficial owner as **Textile House FZCO** (Dubai), which is an alias entity within the **Hussain Trading Network** designated list. The direct entity name "Textile House Ltd" does not appear on the consolidated list, but the beneficial ownership link places this entity within the sanctions-adjacent risk category requiring enhanced due diligence.

*Screening result: MEDIUM-HIGH — beneficial ownership match with designated network; direct entity not listed.*

---

### 1.2 Entry: GLOBAL FABRICS SARL

**Primary Name:** Global Fabrics SARL  
**Designating Authority:** EU Restrictive Measures (Council Regulation EU 2023/1887); UK OFSI (pending — listed as "under review")  
**Designation Basis:** Trade fraud; customs duty evasion; acting as a conduit entity for the Hussain Trading Network  
**Designation Date:** EU: 12 October 2023  

**Known Aliases:**
- Global Fabric Sarl (without terminal 's')
- Global Fabrics International SARL
- GF Textiles SARL
- GF International (short form used in correspondence)

**Registered Address:** 47 Boulevard Zerktouni, Casablanca 20000, Morocco  
**Operational Address (effective):** Dhaka Export Processing Zone, Dhaka, Bangladesh  

**Note:** Global Fabrics SARL has appeared as both shipper and consignee in transactions involving under-invoiced Bangladesh textile exports. The entity maintains a nominal Moroccan registration to create an appearance of EU-proximate operations while conducting actual trade from Bangladesh.

*Screening result: HIGH — entity on EU sanctions list; OFSI review pending.*

---

### 1.3 Entry: AL-NOOR SHIPPING LLC

**Primary Name:** Al-Noor Shipping LLC  
**Designating Authority:** OFAC Ref: SDN-OFAC-2022-7741; UN Security Council Ref: SC/2022/14522  
**Designation Basis:** Providing shipping and logistics services to OFAC-designated entities; sanctions evasion via vessel flag-hopping  
**Designation Date:** OFAC: 3 August 2022; UN: 29 September 2022  

**Known Aliases:**
- Al Noor Maritime (no hyphen variant)
- Alnoor Logistics LLC
- Al-Noor Freight Services FZCO

**Flag State(s) Used:** Panama, Comoros, Palau (historic), currently unknown  
**IMO Number:** 9421887 (vessel MV AL NOOR STAR — currently under flag of convenience)  

**Relevance to demo case:** No direct link to demo shipment (vessel is MV EVER GIFTED, not Al-Noor). Included for completeness in Bangladesh–Gulf corridor screening.

*Screening result: No match to demo shipment vessel.*

---

### 1.4 Entry: FASTCLEAR LOGISTICS — DIRECTOR INDIVIDUAL SCREENING

**Primary Name:** MORRISON, David Andrew  
**Role:** Director, FastClear Logistics Ltd (UK)  
**Designating Authority:** Not currently designated  
**Status:** Subject of HMRC investigation (Ref: HMRC-TF-2023-1147); named in OLAF Bulletin OLAF-FB-2023-TEX-047 as receiving payments from Hussain Trading Network beneficial ownership  

**Risk Classification:** Not designated; however, subject of live intelligence investigation. High due-diligence flag applies. Any clearance processed by FastClear Logistics under direction of D.A. Morrison should be flagged for supervisory review.

**Known Associates:** James Whitmore (FastClear Logistics customs officer — see customs clearance records; 34 clearances for Textile House Ltd shipments under investigation)

*Screening result: MEDIUM — subject of live investigation; not currently sanctioned.*

---

## Section 2: Restricted Parties — Export Control

### 2.1 Dual-Use Goods — Bangladesh Entities

The following Bangladesh entities are subject to **export licence requirements** for dual-use goods (Council Regulation EU 2021/821; UK Export Control Order 2008):

| Entity | Restriction | Basis |
|---|---|---|
| Dhaka Precision Industries Ltd | Export licence required for all goods classified under Annex I (dual-use) | Diversion risk — prior end-use violation 2019 |
| Bengal Engineering Export Co. | Export licence required for machine tools and electronics | Procurement front for state-linked actor |

*Note: These entities are not relevant to the demo shipment (HS 6109.10 cotton T-shirts are not dual-use goods).*

---

## Section 3: Fuzzy Matching Reference Table

The table below provides known alternative spellings, transliterations, and aliases that should be used when applying fuzzy or semantic name matching:

| Canonical Name | Known Variants | Similarity Score Threshold |
|---|---|---|
| Textile House Ltd | Textilehouse Ltd, Textile Hse Ltd, THL Exports, T.H. Ltd, Textile Houses Ltd | > 0.70 |
| Global Fabrics SARL | Global Fabric Sarl, Global Fabrics Intl, GF Textiles SARL, GF International | > 0.72 |
| Hussain Trading Network | Hussain Trade, Al-Hussain Export, H.T. International, KH Global Trade | > 0.65 |
| ABC Trading UK Ltd | ABC Trade UK, A.B.C. Trading, ABC UK Ltd, ABC Trading United Kingdom | > 0.78 |
| FastClear Logistics | Fast Clear Logistics, FastClear Ltd, FC Logistics, FastClear Freight | > 0.75 |
| Muhammad Karim Hussain | M.K. Hussain, Karim Hussain, Mohammad Karim, M Hussain, Karim M. Hussain | > 0.68 |

---

## Section 4: Screening Decision Matrix

Use the following decision matrix when a sanctions screening query returns results:

| Similarity Score | Direct Match? | Recommended Action |
|---|---|---|
| ≥ 0.90 | Yes | HOLD shipment; escalate to compliance officer immediately; do not release |
| 0.75 – 0.89 | Probable | Enhanced due diligence; request additional documentation; hold pending review |
| 0.60 – 0.74 | Possible | Flag for human review; continue processing with enhanced monitoring |
| < 0.60 | Unlikely | No action required; note in case file |
| Beneficial ownership match | N/A | Treat as 0.75–0.89; apply enhanced due diligence |

---

## References

- OFAC Specially Designated Nationals and Blocked Persons List (SDN): https://sanctionssearch.ofac.treas.gov/
- UK OFSI Consolidated List: https://www.gov.uk/government/publications/financial-sanctions-consolidated-list-of-targets
- UN Security Council Consolidated List: https://www.un.org/securitycouncil/sanctions/information
- EU Restrictive Measures in Force: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:01994R0994-20140730
- Wolfsberg Group Anti-Money Laundering Principles for Correspondent Banking
