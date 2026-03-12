# Customs Call Centre Chatbot — Memory-Enabled Agent Workflow

This document describes a single-agent, 3-task workflow that powers a 24/7 AI-assisted customs call centre chatbot. The agent answers queries about shipment status, duty calculations, import procedures, and restricted goods — maintaining cross-session memory so returning callers never have to repeat themselves.

---

## Workflow Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                  CUSTOMS CHATBOT — SEQUENTIAL WORKFLOW                   │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   User message {input}                                                   │
│          │                                                               │
│          ▼                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────────────────────┐  │
│  │    TASK 1    │───▶│    TASK 2    │───▶│          TASK 3           │  │
│  │ Memory Recall│    │Data Retrieval│    │  A) Compose caller reply  │  │
│  │ & Intent     │    │(SQL or KB)   │    │  B) Store memory note     │  │
│  │ Detection    │    │              │    │     (structured summary,  │  │
│  └──────────────┘    └──────────────┘    │      NOT the reply text)  │  │
│          │                  │            └───────────────────────────┘  │
│    LightMem           iceberg-mcp-server               │                │
│    retrieve_memory    OR                    LightMem                    │
│                       rag_studio_tool       get_timestamp               │
│                                             add_memory                  │
│                                                                          │
│  Single agent: Customs Support Agent                                     │
└──────────────────────────────────────────────────────────────────────────┘
```

**Input placeholder:** `{input}` — the caller's message (text typed or transcribed from voice)

**Query types handled:**

| Intent | Trigger keywords | Data source |
|---|---|---|
| `SHIPMENT_STATUS` | tracking, shipment, where is, arrived, cleared, held | `iceberg-mcp-server` → `shipment_tracking` |
| `DUTY_INQUIRY` | duty, tax, how much, charges, tariff, HS code | `iceberg-mcp-server` → `shipment_tracking` + LLM calculation |
| `PROCEDURE_GUIDANCE` | how do I, what documents, how to import, process, apply | `rag_studio_tool` → Customs Procedures KB |
| `GENERAL` | general customs questions, definitions, timelines | LLM response from context |

---

## Task Definitions

### Task 1: Memory Recall & Intent Detection

**Description:**
Start by calling `retrieve_memory` with the user's message `{input}` as the query and `limit` set to 5. If the workflow runtime provides a caller identifier alongside `{input}` — such as a `session_id`, `phone_number`, or `customer_id` injected by the call centre platform — pass it as a `filters` parameter to scope retrieval to this specific caller. Without a filter, `retrieve_memory` returns the most semantically relevant memories across all callers and may surface another caller's shipment context by mistake. Review the retrieved memories to identify any prior context for this caller: previous shipment references, declared goods, outstanding issues, or preferences stated in earlier sessions.

Then analyse the current message `{input}` to classify its primary intent as one of:
- `SHIPMENT_STATUS` — caller wants to know where their shipment is or whether it has cleared
- `DUTY_INQUIRY` — caller wants to know how much duty is owed or how duty was calculated
- `PROCEDURE_GUIDANCE` — caller wants step-by-step guidance on a customs process or regulation
- `GENERAL` — greetings, definitions, timelines, or questions that can be answered from general knowledge
Extract any structured identifiers from the message: tracking number, declaration ID, HS code, or company name. These will be used as query parameters in Task 2.

If the message spans both a status question and a duty question (e.g. "Where is my shipment and how much duty do I owe?"), classify the intent as `DUTY_INQUIRY` — Task 2 will retrieve the shipment record and compute duty context in one lookup, covering both needs.

**Expected Output:**
```json
{
  "intent": "SHIPMENT_STATUS",
  "extracted_identifiers": {
    "tracking_id": "TRK-2024-08812",
    "declaration_id": null,
    "hs_code": null,
    "company_name": null
  },
  "prior_context_summary": "Caller previously asked about a cotton garment shipment from Bangladesh on 2024-03-10. Shipment was in inspection at that time.",
  "memories_retrieved": 3
}
```

**Success Criteria:**
- `retrieve_memory` called with the user's input as query
- Intent classified into one of the four defined categories
- Structured identifiers extracted where present
- Prior context summarised if relevant memories found

---

### Task 2: Data Retrieval

**Description:**
Task 1's output is already available in your context — do not re-plan or re-classify. Extract the `intent` and `extracted_identifiers` from it now and proceed immediately to the appropriate tool call below. If an identifier is null, skip the corresponding query and move to the next.

**If intent is `SHIPMENT_STATUS` or `DUTY_INQUIRY`:**
**Execute** `iceberg-mcp-server` immediately. Try the following queries in order until a result is found:

1. By tracking ID (if extracted):
   `SELECT * FROM shipment_tracking WHERE tracking_id = '<tracking_id from Task 1>'`

2. By declaration ID (if extracted):
   `SELECT * FROM shipment_tracking WHERE declaration_id = '<declaration_id from Task 1>'`

3. By company name (if extracted):
   `SELECT * FROM shipment_tracking WHERE importer_name LIKE '%<company_name from Task 1>%' ORDER BY last_updated DESC LIMIT 5`

For `DUTY_INQUIRY`, additionally compute duty context: compare `duty_assessed_usd` and `duty_paid_usd`, check if any duty balance is outstanding, and note the applicable HS code and duty rate from the record.

**If intent is `PROCEDURE_GUIDANCE`:**
Use `rag_studio_tool` with `action: "query"` against the **Customs Procedures Knowledge Base**. Formulate the query directly from the caller's message in `{input}`. Retrieve the top 3 chunks and synthesise a clear, step-by-step response. If the question involves prohibited or restricted goods, always include the relevant restriction notice.

**If intent is `GENERAL`:**
No external tool call is required. Proceed directly to Task 3 with a note that the response will be composed from general customs knowledge.

**Expected Output (SHIPMENT_STATUS example):**
```json
{
  "data_source": "iceberg-mcp-server",
  "query_used": "SELECT * FROM shipment_tracking WHERE tracking_id = 'TRK-2024-08812'",
  "result": {
    "tracking_id": "TRK-2024-08812",
    "declaration_id": "INV-2024-00456",
    "importer_name": "ABC Trading UK",
    "hs_code": "6109.10",
    "status": "UNDER_EXAMINATION",
    "location": "Felixstowe — Shed 4, Bay 12",
    "estimated_clearance_date": "2024-03-18",
    "duty_assessed_usd": 1250.00,
    "duty_paid_usd": 0.00,
    "inspection_type": "PHYSICAL",
    "notes": "Physical examination requested by targeting officer. Awaiting examination slot."
  }
}
```

**Success Criteria:**
- Correct tool invoked based on intent
- At least one SQL result or KB chunk retrieved
- For DUTY_INQUIRY: duty balance and HS code noted
- For PROCEDURE_GUIDANCE: at least 2 KB chunks retrieved

---

### Task 3: Response Composition & Memory Storage

This task has **two distinct outputs** that must be kept separate:
1. The **caller response** — the verbose, friendly message sent back to the caller
2. The **memory note** — a compact, structured summary stored in LightMem for future sessions

---

#### Part A — Compose the Caller Response

Using the data retrieved in Task 2 and the prior context from Task 1, compose a clear, empathetic, and actionable response for the caller. Follow these guidelines:

- **Tone:** Professional but approachable. Avoid jargon where possible; explain technical terms when used.
- **Shipment status:** State the current status plainly, give the estimated clearance date, tell the caller what action (if any) is required.
- **Duty inquiry:** State the assessed amount, what has been paid, and any outstanding balance. Explain what triggers the duty (HS code, origin, CIF value) in plain language.
- **Procedure guidance:** Give numbered, actionable steps. Reference the specific document names the caller needs.
- **If data not found:** Acknowledge the limitation, ask for additional identifiers (declaration number, invoice number, company name), and offer to escalate.
- **Escalation trigger:** If the shipment is HELD or SEIZED, or if duty balance exceeds USD 5,000, proactively offer to transfer to a senior officer and provide the case reference.

---

#### Part B — Store a Memory Note (NOT the caller response)

> **Why a separate memory note?** The caller response is verbose and formatted for human conversation. If stored verbatim, future retrieval would return long paragraphs that are hard for the agent to parse. The memory note is designed for machine retrieval — dense, structured, and rich in identifiers.

**Step 1:** Call `get_timestamp` to get the current timestamp.

**Step 2:** Construct the `assistant_reply` as a structured memory note using the following template:

```
CALLER: <company_name or "unknown"> (<customer_id or "unverified">).
QUERY TYPE: <SHIPMENT_STATUS | DUTY_INQUIRY | PROCEDURE_GUIDANCE | GENERAL>.
SHIPMENT: <tracking_id> (<declaration_id>), <product_description> (HS <hs_code>) from <country_of_origin>.
STATUS AT CALL: <status> — <location>. ETA clearance: <estimated_clearance_date>.
DUTY: USD <duty_assessed_usd> assessed, USD <duty_paid_usd> paid. Outstanding: USD <outstanding balance>.
ISSUE: <brief description of the caller's concern or the key finding>.
ACTION TAKEN: <what the agent did>.
ESCALATED: <Yes/No> — <reason if yes>.
SUPERSEDES: <tracking_id> — if this note updates a prior memory for the same shipment (i.e. status or duty changed since the last call). Omit on first contact.
```

For `PROCEDURE_GUIDANCE` or `GENERAL` queries (no shipment), use:
```
CALLER: <company_name or "unknown">.
QUERY TYPE: PROCEDURE_GUIDANCE.
TOPIC: <brief topic, e.g. "GSP/REX documentation for Bangladesh textiles">.
KEY FACTS PROVIDED: <bullet summary of the guidance given>.
FOLLOW-UP EXPECTED: <Yes/No> — <reason if yes>.
SUPERSEDES: <topic or prior call date> — if this note corrects or extends previous guidance on the same topic. Omit otherwise.
```

> **Append-only behaviour:** `add_memory` always inserts a new record — it does not update existing entries. For returning callers, this means multiple notes for the same shipment accumulate over time. Always add the new note (including `SUPERSEDES` when applicable) rather than trying to modify the old one. In Task 1, when `retrieve_memory` returns multiple notes for the same tracking ID, treat the one with the most recent timestamp as authoritative for status and duty figures, and use older notes only for historical context.

**Step 3:** Call `add_memory` with:
- `user_input`: the caller's **original verbatim message** from `{input}`
- `assistant_reply`: the **memory note** constructed in Step 2 (not the caller response)
- `timestamp`: the timestamp from Step 1
- `force_extract`: set to `true` if the intent is `SHIPMENT_STATUS` or `DUTY_INQUIRY`, or if the shipment status is HELD, SEIZED, or UNDER_APPEAL; otherwise omit (defaults to false)

**What gets stored in memory — and why each field matters:**

| Memory field | What to include | Why it matters for future retrieval |
|---|---|---|
| `user_input` | The caller's raw message | Enables semantic search: "find conversations where a caller asked about examination delays" |
| Company / customer ID | Always include if known | Lets future queries filter by "find all memories for ABC Trading UK" |
| Tracking / declaration IDs | Always include if present | Critical for "returning caller" flow — agent infers shipment from memory without caller repeating it |
| Status at call time | Include exact status code + location | Shows how the case evolved over multiple calls |
| Duty figures | Include assessed, paid, outstanding | Tracks duty disputes and payment history across sessions |
| Issue description | One sentence summary of the caller's concern | Powers semantic retrieval for similar future queries |
| Action taken | What the agent said or did | Prevents repeating the same advice on a follow-up call |
| Escalation flag | Yes/No + reason | Ensures human officers have context if the case was escalated |

---

**Expected Output:**

```json
{
  "caller_response": "Your shipment TRK-2024-08812 is currently under physical examination at Felixstowe Port (Shed 4, Bay 12). The examination was requested by our targeting team and an examination slot is being allocated. The estimated clearance date is 18 March 2024, subject to the examination outcome. No duty payment is required until the examination is complete. You do not need to take any action at this time — our officers will contact you or your broker (FastClear Logistics) directly if additional documentation is needed.",
  "memory_note_stored": "CALLER: ABC Trading UK Ltd (CUST-0001). QUERY TYPE: SHIPMENT_STATUS. SHIPMENT: TRK-2024-08812 (INV-2024-00456), cotton T-shirts (HS 6109.10) from Bangladesh. STATUS AT CALL: UNDER_EXAMINATION — Felixstowe Shed 4 Bay 12. ETA clearance: 2024-03-18. DUTY: USD 1020.24 assessed, USD 0.00 paid. Outstanding: USD 1020.24. ISSUE: Caller asked for shipment location and status. Under physical exam, examination slot not yet allocated. ACTION TAKEN: Provided status update and ETA. Advised no action needed from caller. ESCALATED: No.",
  "escalation_recommended": false,
  "memory_stored": true
}
```

**Success Criteria:**
- Caller response is clear, empathetic, and directly answers the query
- `get_timestamp` called before `add_memory`
- `add_memory` stores the **memory note** (not the verbose caller response) as `assistant_reply`
- All key identifiers (tracking ID, status, duty figures) are captured in the memory note
- Escalation offered where status is HELD/SEIZED or duty balance > USD 5,000

---

## Agent Definition

### Customs Support Agent

| Attribute | Value |
|---|---|
| **Name** | Customs Support Agent |
| **Role** | 24/7 AI-Powered Customs Call Centre Assistant |

**Backstory:**
You are a friendly and knowledgeable customs support specialist representing the national customs authority's call centre. You have comprehensive knowledge of import and export procedures, duty calculations, HS code classifications, and customs documentation requirements. You understand that callers are often anxious about delayed or held shipments — costly delays affect businesses and livelihoods — so you communicate clearly, empathetically, and without unnecessary jargon. You remember previous conversations with callers so they never have to repeat their case details. When you cannot resolve an issue yourself, you proactively escalate to the right team rather than leaving callers without a path forward.

**Goal:**
1. Greet the caller and use memory to recall any prior context for this session.
2. Understand what the caller needs — status update, duty question, procedural guidance, or general query.
3. Look up live shipment data or retrieve relevant guidance from the knowledge base as appropriate.
4. Compose a clear, helpful response with specific next steps where applicable.
5. Save the conversation to memory so the next session can pick up seamlessly.
6. Escalate to a human officer when the situation requires it.

**Tools:**
- LightMem MCP: `get_timestamp`, `add_memory`, `retrieve_memory`
- `iceberg-mcp-server` (shipment status and duty lookups)
- `rag_studio_tool` (action: `query`, Knowledge Base: Customs Procedures KB)

**Conversation style examples:**

*Shipment status — clear:*
> "Great news — your shipment [TRK-2024-08812] cleared customs at Felixstowe at 14:32 today. Your goods are now with your freight forwarder for final delivery. Total duty paid: USD 1,250.00. Is there anything else I can help you with?"

*Shipment status — held:*
> "I can see shipment [TRK-2024-08812] has been placed on hold pending a physical examination. I know that's frustrating — I'm going to flag this to a senior officer now so they can prioritise your case. The case reference is HOLD-2024-0441. Can I take your contact number so they can call you back within 2 hours?"

*Procedure guidance:*
> "To import goods under the UK Generalised Scheme of Preferences (UK-GSP) from Bangladesh, you'll need: (1) a completed Form A certificate of origin issued by the Bangladesh Export Promotion Bureau, or (2) a Registered Exporter (REX) statement printed on your commercial invoice. Without one of these, the standard 12% duty rate applies instead of the preferential 0% rate. Would you like me to explain how to apply for REX status?"

---

## Required Tools & MCP Configuration

### LightMem MCP Server

```json
{
  "mcpServers": {
    "lightmem": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/FerdinandZhong/LightMem.git[mcp]", "lightmem-mcp"],
      "env": {
        "OPENAI_API_KEY": "${OPENAI_API_KEY}",
        "LIGHTMEM_DATA_PATH": "/data/shared/customs_chatbot/lightmem/",
        "LIGHTMEM_COLLECTION_NAME": "customs_chatbot_memory"
      }
    }
  }
}
```

> **Important:** `LIGHTMEM_DATA_PATH` must be a **shared, persistent location** accessible across all agent sessions — not a session-specific temp folder. Use `/data/shared/` or a mounted persistent volume.

| LightMem Tool | Used In | Purpose |
|---|---|---|
| `get_timestamp` | Task 3 | Timestamp for memory storage |
| `retrieve_memory` | Task 1 | Recall prior caller context |
| `add_memory` | Task 3 | Store conversation for future sessions |

### `iceberg-mcp-server`
Queries the Cloudera Data Warehouse for live shipment and customer data.
- **Required tables:** `shipment_tracking`, `customer_accounts`

### `rag_studio_tool`
Semantic search over the Customs Procedures Knowledge Base.
- **Action:** `query`
- **Knowledge Base:** Customs Procedures KB (see setup below)
- **Embedding model:** `text-embedding-3-small` (configured in RAG Studio)

---

## Knowledge Base Setup

**Customs Procedures KB** — ingest the following documents from `extra_materials/customs_chatbot_demo_data/procedures_kb/`:

| Document | Covers |
|---|---|
| `customs_import_process.md` | End-to-end import process, key stages, timelines |
| `duty_calculation_guide.md` | How customs value is calculated, duty rates, relief schemes |
| `faq_common_queries.md` | Top 30 most common caller questions and answers |
| `prohibited_restricted_goods.md` | Prohibited goods list, restricted goods licensing requirements |

Chunk size: 512 tokens, overlap: 50 tokens, embedding model: `text-embedding-3-small`.

---

## Required Database Tables (CDW)

| Table | Purpose | Key Columns |
|---|---|---|
| `shipment_tracking` | Live and historical shipment status — the primary lookup table for caller queries | `tracking_id`, `declaration_id`, `importer_name`, `hs_code`, `status`, `location`, `duty_assessed_usd`, `duty_paid_usd` |
| `customer_accounts` | Importer account details for context and personalisation | `customer_id`, `company_name`, `contact_name`, `email`, `phone`, `account_status` |

Synthetic data files and Impala DDL are in `extra_materials/customs_chatbot_demo_data/synthetic_db/`.

---

## Workflow Summary

| Stage | Task | Tools | Input | Output |
|---|---|---|---|---|
| 1 | Memory Recall & Intent Detection | `retrieve_memory` | `{input}` | Intent, extracted IDs, prior context summary |
| 2 | Data Retrieval | `iceberg-mcp-server` OR `rag_studio_tool` | Intent + IDs from Task 1 | Shipment record OR KB guidance chunks |
| 3A | Response Composition | (LLM synthesis) | Task 1 + Task 2 outputs | Verbose, caller-facing reply |
| 3B | Memory Storage | `get_timestamp`, `add_memory` | Key facts from Tasks 1–3A | Structured memory note stored in LightMem |

---

## Sample Conversation Flows

### Flow A — Shipment Status Query (CRITICAL outcome)
```
Caller: "Hi, my shipment TRK-2024-08812 — can you tell me where it is?"
→ Task 1: Intent = SHIPMENT_STATUS, tracking_id = TRK-2024-08812
→ Task 2: SQL lookup → status = UNDER_EXAMINATION, duty_paid = 0
→ Task 3: Response explains examination status, ETA, no action needed from caller
          Memory stored: "Caller asked about TRK-2024-08812 on 2024-03-15"
```

### Flow B — Procedure Guidance Query
```
Caller: "What documents do I need to import electronics from China?"
→ Task 1: Intent = PROCEDURE_GUIDANCE, hs_code context: electronics (~8471/8517)
→ Task 2: RAG KB query → returns import process doc + restricted goods doc (dual-use check)
→ Task 3: Response lists required docs + flags potential dual-use licence requirement
          Memory stored for next session
```

### Flow C — Returning Caller (memory in action)
```
Caller: "Any update on my shipment?"
→ Task 1: retrieve_memory → finds previous context: "TRK-2024-08812 was under examination"
          Intent = SHIPMENT_STATUS, tracking_id inferred from memory = TRK-2024-08812
→ Task 2: SQL lookup → status now CLEARED, duty_paid = 1250.00
→ Task 3: "Great news since your last call — TRK-2024-08812 has now cleared!"
          Updates memory with resolution
```

---

## Sample Inputs — Synthetic Data Walkthrough

The following scenarios are drawn from `synthetic_db/customer_accounts.csv` and `synthetic_db/shipment_tracking.csv`. Each shows a first-time query and a follow-up two days later, along with the memory note that bridges the two sessions.

---

### Scenario 1 — ABC Trading UK (CUST-0001): Shipment Under Examination

**DB record:** TRK-2024-08812 · `UNDER_EXAMINATION` · Felixstowe Shed 4 Bay 12 · duty assessed USD 1,020.24 · duty paid USD 0.00 · ETA 2024-03-18 · broker: FastClear Logistics

**Day 1 — First contact (2024-03-15):**
> Hi, this is James Carter from ABC Trading UK. Our shipment tracking TRK-2024-08812 arrived at Felixstowe a couple of days ago and we still haven't heard anything from our broker. Can you tell me what's happening and when it might clear?

| Task | What happens |
|---|---|
| Task 1 | Intent = `SHIPMENT_STATUS` · `tracking_id` = TRK-2024-08812 · no prior memories |
| Task 2 | `SELECT * FROM shipment_tracking WHERE tracking_id = 'TRK-2024-08812'` → UNDER_EXAMINATION, Shed 4 Bay 12, ETA 2024-03-18 |
| Task 3A | Explains physical examination by targeting team, ETA 18 March, no action needed |
| Task 3B | `force_extract: true` (SHIPMENT_STATUS intent). Memory note stored: |

```
CALLER: ABC Trading UK Ltd (CUST-0001).
QUERY TYPE: SHIPMENT_STATUS.
SHIPMENT: TRK-2024-08812 (INV-2024-00456), Men's cotton T-shirts (HS 6109.10) from Bangladesh.
STATUS AT CALL: UNDER_EXAMINATION — Felixstowe Shed 4 Bay 12. ETA clearance: 2024-03-18.
DUTY: USD 1020.24 assessed, USD 0.00 paid. Outstanding: USD 1020.24.
ISSUE: Caller asked for status and ETA after no update from broker post-arrival.
ACTION TAKEN: Confirmed UNDER_EXAMINATION. Physical exam by targeting team. ETA 18 March. Advised no action needed from caller.
ESCALATED: No.
```

**Day 3 — Follow-up (2024-03-17):**
> Hi, it's James again from ABC Trading. I called a couple of days ago about our shipment — yesterday was the estimated clearance date. Has the examination started? Any chance of a delay?

| Task | What happens |
|---|---|
| Task 1 | Intent = `SHIPMENT_STATUS` · `tracking_id` **not stated** — inferred from memory (TRK-2024-08812) · 1 prior memory retrieved |
| Task 2 | SQL lookup on TRK-2024-08812 → status still `UNDER_EXAMINATION` (examination slot not yet allocated per notes) |
| Task 3A | "Since we last spoke on 15 March, the examination slot has not yet been allocated — the ETA of 18 March may shift. FastClear Logistics will contact you once the slot is booked." |
| Task 3B | New note with `SUPERSEDES: TRK-2024-08812 — prior note dated 2024-03-15 showing UNDER_EXAMINATION, no slot yet.` |

---

### Scenario 2 — Denim Discount UK (CUST-0003): Held Shipment → Reclassification & Appeal

**DB records:**
- TRK-2024-08734 · `HELD` · Felixstowe Bay 7 · HS 6113.00 declared, 6203.42 suspected · hold_reason: HS misclassification · duty gap if reclassified: USD 1,578.08
- TRK-2024-08244 · `UNDER_APPEAL` · reclassified to 6203.42 · duty assessed USD 3,360.00 · paid USD 1,820.00 · outstanding USD 1,540.00

**Day 1 — First contact (2024-03-10):**
> Hello, Barry Nolan from Denim Discount UK. Our shipment has been held at Felixstowe since early February — the declaration reference is SUSP-2024-CLASS-001. We declared it as industrial workwear but nobody has told us why it's stuck. Can you find out?

| Task | What happens |
|---|---|
| Task 1 | Intent = `SHIPMENT_STATUS` · `declaration_id` = SUSP-2024-CLASS-001 · no prior memories |
| Task 2 | `SELECT * FROM shipment_tracking WHERE declaration_id = 'SUSP-2024-CLASS-001'` → TRK-2024-08734, HELD, HS misclassification suspected, potential reclassification to 6203.42 |
| Task 3A | Hold reason explained: HS code under investigation, possible reclassification to fashion jeans (12% vs 6.5% duty), additional duty exposure ~USD 1,578. **Escalation triggered** (HELD) — offers transfer to senior officer. |
| Task 3B | `force_extract: true` (HELD status). Memory note stored: |

```
CALLER: Denim Discount UK Ltd (CUST-0003).
QUERY TYPE: SHIPMENT_STATUS.
SHIPMENT: TRK-2024-08734 (SUSP-2024-CLASS-001), industrial workwear trousers declared (HS 6113.00) from Bangladesh.
STATUS AT CALL: HELD — Felixstowe Examination Bay 7. ETA clearance: pending examination outcome.
DUTY: USD 1862.64 assessed at 6.5%. USD 0.00 paid. Potential additional USD 1578.08 if reclassified to 6203.42 at 12%.
ISSUE: Shipment held since early February. Officer suspects HS misclassification — goods may be fashion jeans, not industrial workwear.
ACTION TAKEN: Informed caller of hold reason and duty gap exposure. Offered escalation to senior officer.
ESCALATED: Yes — HELD status.
```

**Day 3 — Follow-up (2024-03-12):**
> Hi, Barry Nolan again from Denim Discount. We've now received a formal reclassification notice moving us to HS 6203.42 with a higher duty rate. We want to appeal. How do we do that, and do we have to pay the extra duty while the appeal is in progress?

| Task | What happens |
|---|---|
| Task 1 | Intent spans `DUTY_INQUIRY` (extra duty, must we pay?) + `PROCEDURE_GUIDANCE` (how to appeal). Neither matches the SHIPMENT_STATUS + DUTY_INQUIRY tie-break rule. Agent classifies as `DUTY_INQUIRY` — duty payment obligation is the blocking question. `retrieve_memory` → prior note on TRK-2024-08734 (HELD, misclassification). Also retrieves TRK-2024-08244 (UNDER_APPEAL) if it already exists. |
| Task 2 | SQL lookup → TRK-2024-08244: UNDER_APPEAL, duty USD 3,360.00, paid USD 1,820.00, outstanding USD 1,540.00. Additionally queries `rag_studio_tool` for HS reclassification appeal process (C285 form, 30-day window, duty deferral during appeal). |
| Task 3A | Explains outstanding duty (USD 1,540); appeal window is 30 days from reclassification date; C285 form if appeal succeeds and overpayment must be claimed back; duty still technically due during appeal unless deferral is granted. Advises trader to apply for appeal immediately. |
| Task 3B | `SUPERSEDES: TRK-2024-08734 — prior note dated 2024-03-10, situation evolved to formal reclassification and appeal stage.` |

---

### Scenario 3 — UK Gadgets Distribution (CUST-0015): Seized Shipment → FIS Investigation

**DB record:** TRK-2024-07355 · `SEIZED` · Heathrow Hold Room 3 · goods declared as laptop parts (duty-free, HS parts) but physical exam confirmed complete assembled laptops (8471.30) · referred to HMRC Fraud Investigation Service

**Day 1 — First contact (2024-03-10):**
> Hi, my name is Martin Fowler from UK Gadgets Distribution. Our shipment TRK-2024-07355 was seized at Heathrow back in December. We haven't heard anything since. What is the current status and what do we need to do?

| Task | What happens |
|---|---|
| Task 1 | Intent = `SHIPMENT_STATUS` · `tracking_id` = TRK-2024-07355 · no prior memories |
| Task 2 | SQL → SEIZED, Heathrow Hold Room 3, seizure reason: misdescription (assembled laptops declared as parts), HMRC FIS referral |
| Task 3A | Confirms SEIZED and FIS referral. **Escalation triggered** (SEIZED). Advises legal representation. Provides case reference. Explains no release until FIS investigation concludes. |
| Task 3B | `force_extract: true` (SEIZED). Memory note stored: |

```
CALLER: UK Gadgets Distribution (CUST-0015).
QUERY TYPE: SHIPMENT_STATUS.
SHIPMENT: TRK-2024-07355 (SUSP-2023-9003), laptop computers (HS 8471.30) from China — declared as parts (duty-free).
STATUS AT CALL: SEIZED — Heathrow Hold Room 3.
DUTY: USD 0.00 assessed / USD 0.00 paid (no duty gap — misdescription fraud case, not an under-invoicing case).
ISSUE: Goods declared as laptop parts but found to be complete assembled laptops on examination. Criminal misdescription. Case referred to HMRC Fraud Investigation Service.
ACTION TAKEN: Confirmed SEIZED and FIS referral. Advised legal representation. Explained no release pending FIS outcome.
ESCALATED: Yes — SEIZED status. HMRC FIS case.
```

**Day 3 — Follow-up (2024-03-12):**
> Hi, Martin Fowler from UK Gadgets again. We've now engaged a solicitor. Can you explain what contesting a seizure involves, and what the HMRC FIS investigation process typically looks like?

| Task | What happens |
|---|---|
| Task 1 | Intent = `PROCEDURE_GUIDANCE` (seizure challenge process, FIS investigation). `retrieve_memory` → prior note: SEIZED, FIS referral, solicitor now engaged. |
| Task 2 | `rag_studio_tool` query: "how to contest a seizure / condemned goods / HMRC FIS investigation process" → KB chunks on seizure challenge, restoration request, condemnation notice timeline. |
| Task 3A | Explains: condemnation notice → 30-day window to issue a legal challenge (Notice of Claim); restoration request possible but rarely granted in fraud cases; FIS investigation is a parallel criminal process distinct from seizure challenge; solicitor engagement is the correct step. |
| Task 3B | `SUPERSEDES: TRK-2024-07355 — prior note dated 2024-03-10. Caller now has legal representation. Query shifted to procedure guidance.` |

---

## Memory Schema

This section defines precisely what LightMem stores and retrieves, and why.

### How LightMem Stores Information

Each call to `add_memory` stores a `(user_input, assistant_reply)` pair. LightMem embeds both fields and indexes them for semantic similarity search. When `retrieve_memory` is called, it returns the pairs whose embeddings are closest to the query.

**The key design choice:** `assistant_reply` is a **structured memory note**, not the caller-facing response. This ensures future retrievals return dense, parseable information rather than verbose conversation text.

---

### Memory Note Templates

#### Template 1 — Shipment Status / Duty Inquiry
```
CALLER: <company_name> (<customer_id>).
QUERY TYPE: <SHIPMENT_STATUS | DUTY_INQUIRY>.
SHIPMENT: <tracking_id> (<declaration_id>), <product_description> (HS <hs_code>) from <country_of_origin>.
STATUS AT CALL: <status> — <location>. ETA clearance: <estimated_clearance_date>.
DUTY: USD <duty_assessed_usd> assessed, USD <duty_paid_usd> paid. Outstanding: USD <outstanding>.
ISSUE: <one-sentence summary of caller concern>.
ACTION TAKEN: <what the agent said or did>.
ESCALATED: <Yes/No> — <reason if yes>.
SUPERSEDES: <tracking_id> — omit on first contact.
```

**Example (first contact):**
```
CALLER: ABC Trading UK Ltd (CUST-0001).
QUERY TYPE: SHIPMENT_STATUS.
SHIPMENT: TRK-2024-08812 (INV-2024-00456), cotton T-shirts (HS 6109.10) from Bangladesh.
STATUS AT CALL: UNDER_EXAMINATION — Felixstowe Shed 4 Bay 12. ETA clearance: 2024-03-18.
DUTY: USD 1020.24 assessed, USD 0.00 paid. Outstanding: USD 1020.24.
ISSUE: Caller asked for shipment location. Under physical exam, examination slot pending.
ACTION TAKEN: Provided status update and ETA. Advised no action needed from caller.
ESCALATED: No.
```

**Example (returning caller — status resolved):**
```
CALLER: ABC Trading UK Ltd (CUST-0001).
QUERY TYPE: SHIPMENT_STATUS.
SHIPMENT: TRK-2024-08812 (INV-2024-00456), cotton T-shirts (HS 6109.10) from Bangladesh.
STATUS AT CALL: CLEARED — Felixstowe. ETA clearance: N/A (cleared 2024-03-19).
DUTY: USD 1020.24 assessed, USD 1020.24 paid. Outstanding: USD 0.00.
ISSUE: Caller checking if shipment cleared after examination. Confirmed CLEARED same day.
ACTION TAKEN: Confirmed clearance and duty payment. Caller satisfied.
ESCALATED: No.
SUPERSEDES: TRK-2024-08812 — prior note dated 2024-03-15 showing UNDER_EXAMINATION status.
```

---

#### Template 2 — Procedure Guidance / General
```
CALLER: <company_name or "unknown">.
QUERY TYPE: <PROCEDURE_GUIDANCE | GENERAL>.
TOPIC: <brief topic, e.g. "GSP/REX documentation for Bangladesh textiles">.
KEY FACTS PROVIDED: <bullet list of the main points covered>.
FOLLOW-UP EXPECTED: <Yes/No> — <reason if yes, e.g. "Caller will call back with Form A serial number">.
```

**Example:**
```
CALLER: Denim Discount UK Ltd (CUST-0003).
QUERY TYPE: PROCEDURE_GUIDANCE.
TOPIC: How to appeal HS code reclassification from 6113 to 6203.42.
KEY FACTS PROVIDED:
  - 30-day appeal window from reclassification date
  - Need ATR ruling or trade publication evidence supporting original code
  - C285 form for duty overpayment claim if appeal succeeds
  - Civil penalty of 30% of shortfall may be waived if voluntary disclosure
FOLLOW-UP EXPECTED: Yes — Caller will obtain ATR ruling and call back for appeal submission guidance.
```

---

### What Each Memory Field Enables

| Field stored | Enables in future sessions |
|---|---|
| `user_input` (caller's raw message) | Semantic search: "find calls where a caller asked about examination delays at Felixstowe" |
| `CALLER: {company} ({id})` | Caller identification without asking: returning caller says "any update?" and agent retrieves their case |
| Tracking / declaration IDs | Implicit shipment reference: agent knows TRK-2024-08812 without caller repeating it |
| `STATUS AT CALL: {status}` | Case evolution tracking: agent can tell caller "since your last call, status changed from UNDER_EXAMINATION to CLEARED" |
| Duty figures | Duty dispute continuity: agent knows what was assessed and paid at last contact |
| `ACTION TAKEN` | Avoids redundancy: agent does not repeat the same advice on a follow-up call |
| `ESCALATED: Yes` | Human officer context: if call is routed to a human, full case history is available |
| `SUPERSEDES: <id>` | Temporal ordering: when multiple notes exist for the same shipment, agent knows which is the latest authoritative record |

---

### When to Use `force_extract: true`

Pass `force_extract: true` in the `add_memory` call when the conversation contains many named entities (company names, officer IDs, tracking numbers, HS codes). LightMem will perform additional entity extraction to improve future retrieval precision.

**Use `force_extract: true` for:**
- Shipment status calls with multiple shipment references
- Duty dispute calls with specific assessment amounts and HS codes
- Any call involving a HELD, SEIZED, or UNDER_APPEAL shipment

**Skip `force_extract` (default False) for:**
- General procedure guidance with no specific shipment context
- Simple FAQ-style queries

---

## Usage Notes

1. **Session Identity:** If the caller's session ID or phone number is available as a filter, pass it as a `filters` parameter to `retrieve_memory` to scope memory retrieval to this specific caller. Without a filter, the agent retrieves the most semantically relevant memories across all callers.

2. **Escalation Threshold:** The escalation trigger (HELD/SEIZED status or duty balance > USD 5,000) is a configurable starting point. Adjust based on call centre capacity and risk policy.

3. **Memory Freshness:** Call `offline_update` periodically to consolidate and deduplicate stored memories. Because `add_memory` is append-only, returning-caller records accumulate across sessions — `offline_update` merges entries flagged with `SUPERSEDES` and removes stale notes, keeping the vector index compact and retrieval relevant. Recommended schedule: nightly, triggered as a **CML Job** in the same project as the chatbot agent. Set the job command to invoke the LightMem MCP server's `offline_update` action and configure it to run at 02:00 local time to avoid overlap with peak call centre hours. Run manually after any bulk data migration or if retrieval quality degrades.

4. **Handoff to Human:** When the agent recommends escalation, log the full conversation context (Task 1–3 outputs) into the case management system before handoff so the human officer has full context without the caller needing to repeat themselves.

5. **Multilingual:** The LLM and LightMem embeddings support multilingual input. Callers can write in their native language and the agent will respond in the same language.
