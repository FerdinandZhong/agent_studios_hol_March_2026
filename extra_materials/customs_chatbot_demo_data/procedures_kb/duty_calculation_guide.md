# Customs Duty Calculation Guide

**Source:** HM Revenue & Customs (HMRC) — Tariff and Duty Reference  
**Applies to:** Goods imported into Great Britain  
**Last reviewed:** January 2024

---

## How Customs Duty Is Calculated

Customs duty is calculated using a straightforward formula:

```
Customs Duty = Customs Value (CIF) × Duty Rate (%)
```

However, determining the **customs value** and the correct **duty rate** each involve several steps.

---

## Step 1: Establish the Customs Value

The customs value is the taxable base for duty calculations. The UK uses the **WTO Customs Valuation Agreement**, which defines six methods of valuation. The default (and most common) method is:

### Method 1: Transaction Value
The transaction value is the **price actually paid or payable** for the goods when sold for export to the UK, adjusted to a CIF (Cost + Insurance + Freight) basis.

**CIF Adjustment:**  
If your trade terms are **FOB** (Free On Board), you must **add** the cost of freight and insurance from the port of loading to the UK port of entry to arrive at the CIF customs value.

| Trade Terms | Adjustment Required |
|---|---|
| **EXW** (Ex Works) | Add transport + insurance to UK port |
| **FOB** (Free On Board) | Add freight + insurance UK port |
| **CIF** (Cost + Insurance + Freight) | No adjustment — use invoice value directly |
| **DDP** (Delivered Duty Paid) | Deduct duties and charges from invoice price |

**Example:**
- Invoice value (FOB Bangladesh): USD 32,000
- Sea freight Chittagong → Felixstowe: USD 1,800
- Insurance: USD 120
- **CIF Customs Value: USD 33,920**

### Method 2–6 (Fallback Methods)
If the transaction value cannot be used (e.g., buyer and seller are related and the relationship affected the price), HMRC may use:
- Identical or similar goods values (Methods 2 & 3)
- Deductive value from UK resale price (Method 4)
- Computed value from production costs (Method 5)
- Fallback / reasonable means (Method 6)

---

## Step 2: Determine the Duty Rate

The duty rate is determined by the commodity code (HS code) under the **UK Global Tariff**. Three different rates may apply:

### 2.1 MFN (Most Favoured Nation) Rate
The standard rate applied to imports from countries without a preferential trade agreement. All WTO members are entitled to this rate.

**Example MFN rates for common textile HS codes:**
| HS Code | Description | MFN Rate |
|---|---|---|
| 6109.10 | T-shirts, cotton | 12.0% |
| 6110.20 | Jerseys, pullovers, cotton | 12.0% |
| 6203.42 | Men's cotton trousers | 12.0% |
| 6204.62 | Women's cotton trousers | 12.0% |
| 6113.00 | Garments from knitted/crocheted fabrics | 12.0% |
| 6211.42 | Track suits, cotton | 12.0% |
| 8471.30 | Portable data-processing machines (laptops) | 0.0% |
| 8517.12 | Telephones for cellular networks | 0.0% |
| 9403.60 | Wooden furniture | 5.0% |

### 2.2 UK-DCTS Preferential Rate (Developing Countries)
The **UK Developing Countries Trading Scheme (UK-DCTS)** provides duty reductions or exemptions for goods originating in least developed and developing countries.

**Enhanced Preferences (effectively 0% for most textiles):**

| Country | Status | Textile Duty Rate | Evidence Required |
|---|---|---|---|
| Bangladesh | Least Developed Country (LDC) | 0% | Form A or REX statement |
| Cambodia | LDC | 0% | Form A or REX statement |
| Myanmar | LDC | 0% | Form A or REX statement |
| Sri Lanka | Developing Country | 9.6% (20% reduction) | Form A or REX statement |
| Pakistan | Developing Country | 9.6% (20% reduction) | Form A or REX statement |
| India | Not DCTS eligible for most textiles | 12% (MFN applies) | N/A |

### 2.3 UK FTA Preferential Rates
The UK has bilateral Free Trade Agreements with several countries. Goods originating in FTA partner countries may benefit from reduced or zero duty.

**Key FTA partners:**
| Country | Agreement | Typical Textile Rate |
|---|---|---|
| Japan | UK-Japan Comprehensive Economic Partnership | 0% with origin evidence |
| South Korea | UK-Korea FTA | 0% with origin evidence |
| Turkey | UK-Turkey FTA | 0% with origin evidence |
| Australia | UK-Australia FTA (2023) | 0% immediately (textiles) |

---

## Step 3: Apply the Preference Code

To claim a preferential rate, the importer must declare the correct **preference code** on the customs declaration:

| Preference Code | Meaning |
|---|---|
| 100 | No preference claimed — MFN rate applies |
| 200 | GSP / UK-DCTS preference — Form A presented |
| 300 | GSP / UK-DCTS preference — REX statement on invoice |
| 400 | Bilateral FTA preference |

If a preference is claimed but the origin evidence is invalid, HMRC will demand the difference between the preferential and MFN rate, plus 10% late payment interest and potentially a penalty.

---

## Worked Examples

### Example 1: Bangladesh T-shirts — GSP Preference Claimed

| Item | Value |
|---|---|
| FOB invoice value | USD 32,000 |
| Freight (Chittagong → Felixstowe) | USD 1,800 |
| Insurance | USD 120 |
| **CIF Customs Value** | **USD 33,920** |
| HS Code | 6109.10 (cotton T-shirts) |
| MFN Duty Rate | 12.0% |
| Preferential Rate (Bangladesh GSP) | 0.0% |
| Preference Code | 300 (REX statement on invoice) |
| **Duty Payable (with preference)** | **USD 0.00** |
| Duty payable if preference rejected | USD 4,070.40 |

**Saving from correct GSP claim: USD 4,070.40**

---

### Example 2: China Furniture — MFN Rate

| Item | Value |
|---|---|
| CIF invoice value | USD 92,000 |
| HS Code | 9403.60 (wooden furniture) |
| MFN Duty Rate | 5.0% |
| Preference available | None — China not in UK-DCTS or UK FTA |
| **Duty Payable** | **USD 4,600.00** |

---

### Example 3: Misclassification — Impact on Duty

A shipment of men's fashion denim jeans is declared under HS 6113.00 (industrial workwear garments, 6.5% duty) instead of the correct HS 6203.42 (men's cotton trousers, 12.0% duty).

| Item | Incorrect Declaration | Correct Classification |
|---|---|---|
| Declared HS code | 6113.00 | 6203.42 |
| Declared duty rate | 6.5% | 12.0% |
| CIF customs value | USD 28,656 | USD 28,656 |
| Duty assessed | USD 1,862.64 | USD 3,438.72 |
| **Duty shortfall** | | **USD 1,576.08** |

After reclassification, HMRC issues a revised demand for USD 1,576.08 plus 10% interest and may issue a misdeclaration penalty of 30% of the shortfall (USD 472.82), bringing the total additional liability to approximately USD 2,206.91.

---

## VAT on Imports

In addition to customs duty, **Import VAT** is payable at the standard UK rate (currently 20%) on most goods. Import VAT is calculated on:

```
Import VAT = (Customs Value + Customs Duty) × 20%
```

**Example (continuing Example 2):**
- Customs Value: USD 92,000
- Customs Duty: USD 4,600
- **Import VAT base: USD 96,600**
- **Import VAT: USD 19,320**

Most VAT-registered businesses can reclaim Import VAT as input tax on their VAT return. The **Postponed VAT Accounting (PVA)** scheme allows VAT-registered importers to account for import VAT on their VAT return rather than paying it at the border.

---

## Duty Relief Schemes

### Inward Processing Relief (IPR)
Allows goods to be imported, processed or repaired, and re-exported without paying customs duty on the import. Requires prior HMRC authorisation.

### Temporary Admission (TA)
Goods temporarily imported for a specific purpose (e.g., trade shows, repairs) can be imported duty-free if re-exported within a specified period. An ATA Carnet is the simplest mechanism.

### Customs Warehousing
Goods can be stored in an HMRC-authorised customs warehouse without duty payment until they are released into free circulation or re-exported. No time limit, but warehouse must be licensed.

### End Use Relief
Duty reduction for goods used for specific industrial purposes (e.g., components incorporated into aircraft or ships).

---

## Common Questions About Duty Calculations

**Q: I've already paid duty but think the amount was wrong. Can I get a refund?**  
A: Yes. Submit a C285 (Post-Clearance Amendment) form within 3 years of the date your declaration was accepted. Include the correct HS code and supporting evidence. HMRC will review and refund any overpayment plus interest.

**Q: My duty rate was 12% but my supplier said it should be 0% for Bangladesh goods.**  
A: Your supplier is likely referring to the UK-DCTS GSP preference rate. To claim 0% duty on Bangladesh goods, you need to present either a Form A certificate of origin issued by the Bangladesh EPB, or a REX statement printed on the commercial invoice by a registered exporter. If you didn't have this at import, you can submit a late preference claim within 3 years — but you'll need to obtain the origin evidence retrospectively from your supplier.

**Q: How do I know what duty rate applies to my product?**  
A: Use the UK Trade Tariff tool on GOV.UK. Enter your commodity description and the tool will suggest the correct HS code and show the applicable MFN and preferential rates. For complex classifications, HMRC offers a free Advance Tariff Ruling (ATR) service.

**Q: Do I pay duty on the freight costs as well?**  
A: Yes — if your terms are FOB, you add the freight and insurance costs to arrive at the CIF customs value, and duty is calculated on that total. However, any freight costs incurred after the goods arrive in the UK are excluded from the customs value.
