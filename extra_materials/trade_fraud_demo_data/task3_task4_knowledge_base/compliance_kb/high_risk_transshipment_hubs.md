# High-Risk Transshipment Hubs — Origin-Washing and Route Risk Reference

**Source:** WCO CELBET (Container and Land Border Expert Team) Intelligence Compendium 2023; HMRC Compliance Intelligence Unit; OLAF Trade Fraud Bulletin 2023-Q3  
**Document Type:** Trade Compliance Knowledge Base — Route Risk Reference  
**Last Updated:** Q4 2023  

---

## Purpose

This document lists seaports, airports, and free trade zones that are known to be used in **origin-washing schemes** — the fraudulent practice of routing goods through an intermediate location to falsely re-attribute country of origin and claim preferential duty rates or evade trade restrictions (sanctions, quotas, antidumping duties).

The presence of a known transshipment hub in a shipment's routing is a **risk factor** that should trigger enhanced document scrutiny and, where other fraud indicators are present, physical inspection.

**Routing through a hub alone is not evidence of fraud.** Transshipment is a legitimate and common commercial practice. However, in combination with other indicators (under-invoicing, missing Form A, entity intelligence hits), it materially increases the probability of fraudulent origin declaration.

---

## Risk Tier Classification

| Risk Tier | Definition |
|---|---|
| **Tier 1 — Critical** | Hub with documented seizure history specifically for origin-washing of the commodity type in transit; active intelligence cases |
| **Tier 2 — High** | Hub with documented general origin-washing cases; free zone infrastructure that facilitates certificate manipulation |
| **Tier 3 — Medium** | Hub with structural conditions for origin-washing (free zone, minimal processing rules) but limited documented cases |

---

## Tier 1 — Critical Risk Hubs (Textiles and General Merchandise)

### Port Klang (Malaysia) — Westport & Northport

**Risk profile:** Tier 1 — Critical  
**Primary fraud type:** China → Malaysia origin-washing for textiles, steel, aluminium, electronics  
**Volume:** Approximately 2.3 million TEUs transshipped annually; limited MAS (Malaysian) customs inspection capacity in FTZ  

**Known schemes:**
- Goods manufactured in China shipped to Port Klang Free Zone (PKFZ); relabelled with "Made in Malaysia" certificates; re-exported as Malaysian origin to claim preferential access to US, EU, and UK markets
- Certificate of origin fraud: Malaysian Form D (ASEAN preferential) or ATIGA certificates issued for Chinese goods
- Primary commodity sectors: Steel products (HS 7207-7217), aluminium (HS 7604), solar panels (HS 8541), textiles/garments (HS 50-63)

**Detection signals specific to Port Klang transshipment:**
- Bill of lading shows Shenzhen/Guangzhou/Shanghai → Port Klang → destination port
- Short Port Klang dwell time (< 5 days) inconsistent with value-adding processing
- Certificate of Origin issuing body is a Malaysian FTZ operator rather than MITI (Ministry of International Trade and Industry)
- PKFZ company address on commercial documents

---

### Colombo (Sri Lanka)

**Risk profile:** Tier 1 — Critical (Bangladesh corridor specific)  
**Primary fraud type:** Bangladesh → Sri Lanka — used specifically to obtain Sri Lankan Form A certificates for goods manufactured in Bangladesh but claiming Sri Lankan origin; Bangladesh goods transhipped to claim UK-DCTS Sri Lanka tier rate  

**Known schemes:**
- Bangladesh garments with under-invoiced value shipped to Colombo; repackaged and issued new Sri Lankan certificates of origin
- Exploits the geographic proximity of Chittagong → Colombo (regular feeder service, 3-day transit)
- Used when UK import quota for Bangladesh has been reached or when shipment-specific compliance issues make direct Bangladesh import risky

**Detection signals:**
- Bill of lading shows Chittagong → Colombo → Felixstowe/Southampton/Tilbury
- Declared origin: Sri Lanka, but shipper address or email domain suggests Bangladesh operation
- Colombo dwell time < 7 days (insufficient for value-adding processing)
- Form A issued by Sri Lanka Export Development Board for goods with Bangladesh-origin materials

---

### Jebel Ali Free Zone (JAFZ) — Dubai, UAE

**Risk profile:** Tier 1 — Critical  
**Primary fraud type:** Multi-purpose origin-washing and sanctions evasion; used for goods from Iran, Russia, China, and North Korea being re-routed to Western markets  

**Known schemes:**
- Goods subject to UK/EU/US sanctions (Russia, Iran, Belarus) shipped to JAFZ, repackaged and re-documented as "UAE origin" or "UAE re-export"
- Dual-use goods and controlled technology exported to JAFZ and then re-exported without end-user documentation to sanctioned states
- Chinese steel, aluminium and textile goods routed through JAFZ to obscure origin and avoid EU/UK antidumping duties

**Specific to textiles/garments:**
- Bangladesh/Pakistani garments shipped to JAFZ under-invoiced; new commercial documents issued at higher prices for money laundering or illicit value transfer
- UAE-origin Form A issued for goods manufactured in Bangladesh, exploiting UAE-UK free trade negotiations

**Detection signals:**
- Bill of lading shows origin country → Jebel Ali (DP World terminal) → European destination
- Declaring party is a UAE free zone entity with no manufacturing capacity
- JAFZ "warehouse receipt" rather than factory production documents
- Container number continuity — same physical container arrives JAFZ and departs without devanning

---

## Tier 2 — High Risk Hubs

### Singapore (PSA Port)

**Risk profile:** Tier 2 — High  
**Primary fraud type:** Electronics, semiconductors, and controlled goods; some textile origin-washing  
**Notes:** Singapore itself has strong customs controls; risk is primarily through third-party logistics operators misusing Singapore's free port infrastructure. Risk lower than Tier 1 hubs but non-negligible for high-value electronics and dual-use goods.

---

### Salalah Free Zone (Oman)

**Risk profile:** Tier 2 — High  
**Primary fraud type:** Gulf region origin-washing; Russia/CIS → Oman → EU/UK re-routing post-2022 sanctions  
**Notes:** Significant increase in Oman-transshipped goods since 2022 Russia sanctions. Steel, machinery, electronics.

---

### Tangier Med (Morocco)

**Risk profile:** Tier 2 — High  
**Primary fraud type:** China → Morocco → EU route. Chinese textiles and electronics transshipped to claim EU-Morocco Association Agreement preferential access.  
**Notes:** Active OLAF investigation ongoing as of Q3 2023.

---

### Istanbul (Turkey) — Ambarlı Port

**Risk profile:** Tier 2 — High  
**Primary fraud type:** Iran sanctions evasion; Russia re-routing post-2022. Also some textile origin-washing (Turkish preference vs. Chinese goods).  

---

## Tier 3 — Medium Risk Hubs

| Hub | Country | Primary Concern |
|---|---|---|
| Port Said / Ain Sokhna | Egypt | Suez Canal transshipment; some Africa-origin certificate fraud |
| Piraeus | Greece | Mediterranean hub; Chinese investment; some antidumping circumvention |
| Klang Valley Free Zone | Malaysia | Overflow from PKFZ; electronics |
| Hamad Port | Qatar | Gulf transshipment; post-2022 Russia re-routing |
| Hai Phong | Vietnam | Chinese goods transshipped as Vietnamese to exploit US-Vietnam trade differential |
| Laem Chabang | Thailand | Chinese goods transshipped to claim ASEAN FTA rates |

---

## Route Risk Assessment Matrix

Use this matrix when evaluating a shipment's declared route against the transshipment hub list:

| Route Pattern | Risk Level | Recommended Action |
|---|---|---|
| Origin country → Direct to discharge port | Baseline | Standard risk assessment |
| Origin country → Tier 3 hub → Discharge | Low-Medium | Note in file; verify if other indicators present |
| Origin country → Tier 2 hub → Discharge | Medium-High | Request original B/L showing full routing; verify hub dwell time |
| Origin country → Tier 1 hub → Discharge | High | Enhanced document scrutiny; verify Certificate of Origin with issuing authority; consider physical inspection |
| Origin country → Multiple hubs → Discharge | Very High | Strong origin-washing indicator; physical inspection recommended; refer to intelligence unit |
| Bill of lading routing inconsistent with declared transit time | High | Document fraud indicator; obtain vessel tracking records |

---

## Specific Route Assessment: Chittagong → Felixstowe

The declared route for shipment **INV-2024-00123** is:
- **Port of Loading:** Chittagong, Bangladesh
- **Port of Discharge:** Felixstowe, United Kingdom
- **Vessel:** MV EVER GIFTED, Voyage 0142E

**Route Assessment:** DIRECT — No Tier 1/2/3 hub in declared route.

The direct Chittagong–Felixstowe route is a high-volume legitimate trade lane operated by Evergreen Marine Corporation and other major carriers. The declared routing itself does not add transshipment risk for this specific shipment. Risk for this case derives from price anomaly and intelligence indicators rather than route risk.

**However:** Historical pattern analysis shows that other shipments from Textile House Ltd and related entities (Global Fabrics SARL) have previously been routed via Colombo (detected in 2023 shipments not in the current declaration). This prior route history warrants a supplementary check with carrier records.

---

## References

- WCO CELBET Intelligence Compendium 2023
- OLAF Trade Fraud Bulletin 2023-Q2/Q3 (Restricted circulation — synthesised for KB)
- HMRC Compliance Intelligence Unit — Origin Fraud Typologies 2023
- US CBP CSMS #55741649 — Transshipment of Chinese-Origin Merchandise (2022)
- EU Regulation 952/2013 — Union Customs Code, Article 60 (Non-preferential origin rules)
