# Digital Banking Chatbot — Memory-Enabled Agent Workflow

This document describes a single-agent, 3-task workflow that powers a 24/7 AI-assisted digital banking chatbot. The agent answers queries about account locks, transaction status, loan payments, card issues, and suspected fraud — maintaining cross-session memory so returning customers never have to repeat themselves.

---

## Workflow Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                  BANKING CHATBOT — SEQUENTIAL WORKFLOW                   │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   User message {input}                                                   │
│          │                                                               │
│          ▼                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────────────────────┐  │
│  │    TASK 1    │───▶│    TASK 2    │───▶│          TASK 3           │  │
│  │ Memory Recall│    │Data Retrieval│    │  A) Compose customer reply│  │
│  │ & Intent     │    │(SQL or KB)   │    │  B) Store memory note     │  │
│  │ Detection    │    │              │    │     (structured summary,  │  │
│  └──────────────┘    └──────────────┘    │      NOT the reply text)  │  │
│          │                  │            └───────────────────────────┘  │
│    LightMem           iceberg-mcp-server               │                │
│    retrieve_memory    OR                    LightMem                    │
│                       rag_studio_tool       get_timestamp               │
│                                             add_memory                  │
│                                                                          │
│  Single agent: Banking Support Agent                                     │
└──────────────────────────────────────────────────────────────────────────┘
```

**Input placeholder:** `{input}` — the customer's message (text typed or transcribed from voice)

**Query types handled:**

| Intent | Trigger keywords | Data source |
|---|---|---|
| `ACCOUNT_STATUS` | locked, frozen, balance, account, can't access, available, why is my account | `iceberg-mcp-server` → `accounts`, `customers`, `support_cases` |
| `TRANSACTION_INQUIRY` | transaction, payment, transfer, pending, failed, declined, wire, charge, where is my | `iceberg-mcp-server` → `transactions`, `accounts` |
| `LOAN_INQUIRY` | loan, mortgage, auto loan, payment due, balance, how much do I owe, overdue | `iceberg-mcp-server` → `loans`, `customers` |
| `CARD_INQUIRY` | card, blocked, declined, credit limit, card not working, debit card, expiry | `iceberg-mcp-server` → `cards`, `accounts` |
| `FRAUD_REPORT` | fraud, unauthorized, didn't make this, suspicious, stolen, I didn't do this | `iceberg-mcp-server` → `transactions`, `support_cases` |
| `GENERAL` | how do I, what is, procedures, interest rate, general banking questions | `rag_studio_tool` → Banking Procedures KB |

---

## Task Definitions

### Task 1: Memory Recall & Intent Detection

**Description:**
Start by calling `retrieve_memory` with the user's message `{input}` as the query and `limit` set to 5. If the workflow runtime provides a caller identifier alongside `{input}` — such as a `session_id`, `phone_number`, or `customer_id` injected by the digital banking platform — pass it as a `filters` parameter to scope retrieval to this specific customer. Without a filter, `retrieve_memory` returns the most semantically relevant memories across all customers and risks surfacing another customer's account details. Review the retrieved memories to identify any prior context: previous account issues, open support cases, reported fraud, loan concerns, or stated preferences from earlier sessions.

Then analyse the current message `{input}` to classify its primary intent as one of:
- `ACCOUNT_STATUS` — customer wants to know why their account is locked or frozen, check their balance, or understand account restrictions
- `TRANSACTION_INQUIRY` — customer wants to know the status of a specific payment, transfer, or charge; why a transaction failed; or when a pending amount will post
- `LOAN_INQUIRY` — customer wants their current loan balance, next payment date, payment amount, or the status of a delinquent loan
- `CARD_INQUIRY` — customer wants to know why their card is blocked, check their credit limit or available credit, or report a card issue
- `FRAUD_REPORT` — customer is reporting an unauthorized transaction or suspicious account activity
- `GENERAL` — general banking procedures, product questions, interest rates, or questions answerable from general knowledge

Extract any structured identifiers from the message: account number (last 4 digits), transaction reference number, transaction ID, loan ID, card number (last 4 digits), or full name. These will be used as query parameters in Task 2.

**Intent tie-break rules:**
- If the message mentions both an account lock and an unauthorized transaction (e.g. "my account is locked because of a charge I didn't make"), classify as `FRAUD_REPORT` — this takes priority and triggers the full fraud lookup and escalation path.
- If the message mentions both a failed transaction and a card block, classify as `CARD_INQUIRY` — the card status is likely the root cause.
- If the message mentions both a loan payment and an account lock, classify as `ACCOUNT_STATUS` — the lock details will reveal if it is loan-related.

**Expected Output:**
```json
{
  "intent": "ACCOUNT_STATUS",
  "extracted_identifiers": {
    "customer_id": "CUST-B003",
    "account_number_last4": "8844",
    "transaction_id": null,
    "transaction_ref": null,
    "loan_id": null,
    "card_number_last4": null,
    "full_name": "Maria Garcia"
  },
  "prior_context_summary": "Customer previously contacted on 2026-03-12 about checking account lock due to fraud. Case CASE-2026-0001 open. Fraud investigation ongoing.",
  "memories_retrieved": 2
}
```

**Success Criteria:**
- `retrieve_memory` called with the user's input as query
- Intent classified into one of the six defined categories
- Structured identifiers extracted where present in the message
- Prior context summarised if relevant memories found; explicitly noted if no prior memories exist

---

### Task 2: Data Retrieval

**Description:**
Task 1's output is already available in your context — do not re-plan or re-classify. Extract the `intent` and `extracted_identifiers` from it now and proceed immediately to the appropriate tool calls below. If an identifier is null, attempt resolution through the customer's session identity or prior memory context before skipping.

---

**If intent is `ACCOUNT_STATUS`:**

Execute `iceberg-mcp-server`. Try the following queries in order:

1. Retrieve all accounts for the customer (primary lookup):
   ```sql
   SELECT a.account_id, a.account_type, a.account_number_masked, a.currency,
          a.current_balance, a.available_balance, a.status, a.lock_reason,
          a.last_activity_date, a.daily_transfer_limit, a.notes
   FROM accounts a
   WHERE a.customer_id = '<customer_id from Task 1>'
   ORDER BY a.account_type
   ```

2. If only last-4 digits provided, resolve to full account:
   ```sql
   SELECT a.account_id, a.account_type, a.current_balance, a.available_balance,
          a.status, a.lock_reason, a.notes
   FROM accounts a
   WHERE a.customer_id = '<customer_id>'
     AND a.account_number_masked = '****<last4>'
   ```

3. Check for any open support cases (context for lock reason or ongoing investigation):
   ```sql
   SELECT case_id, case_type, subject, status, priority, created_at, notes
   FROM support_cases
   WHERE customer_id = '<customer_id>'
     AND status NOT IN ('RESOLVED', 'CLOSED')
   ORDER BY created_at DESC
   ```

For locked or frozen accounts: identify the `lock_reason` field — it maps directly to the escalation and resolution path:
- `FRAUD_ALERT` → fraud investigation in progress; escalate to fraud team
- `SUSPICIOUS_ACTIVITY` → security hold; identity verification required before unfreeze
- `LOAN_DEFAULT` → account locked by collections; escalate to collections team
- `LARGE_CASH_DEPOSITS` → AML/compliance review; restricted but not fully locked
- `CUSTOMER_REQUEST` → customer-initiated lock; can be reversed with identity verification

---

**If intent is `TRANSACTION_INQUIRY`:**

Execute `iceberg-mcp-server`. Try the following queries in order until the specific transaction is found:

1. By transaction ID (if extracted):
   ```sql
   SELECT transaction_id, account_id, transaction_type, amount, currency,
          merchant_name, description, status, initiated_at, completed_at,
          channel, reference_number, failure_reason, notes
   FROM transactions
   WHERE transaction_id = '<transaction_id from Task 1>'
   ```

2. By bank reference number (if extracted):
   ```sql
   SELECT transaction_id, transaction_type, amount, currency,
          merchant_name, description, status, initiated_at, completed_at,
          channel, failure_reason, notes
   FROM transactions
   WHERE reference_number = '<reference_number from Task 1>'
   ```

3. If no specific identifier — retrieve recent transactions for the account to let the customer identify which one:
   ```sql
   SELECT transaction_id, transaction_type, amount, currency, merchant_name,
          description, status, initiated_at, completed_at, channel,
          reference_number, failure_reason
   FROM transactions
   WHERE account_id = '<account_id>'
   ORDER BY initiated_at DESC
   LIMIT 10
   ```

4. If customer asks specifically about pending items:
   ```sql
   SELECT transaction_id, transaction_type, amount, currency, merchant_name,
          description, initiated_at, channel, reference_number, notes
   FROM transactions
   WHERE account_id = '<account_id>'
     AND status = 'PENDING'
   ORDER BY initiated_at DESC
   ```

For `FAILED` transactions: always retrieve the `failure_reason` field and explain it in plain language in Task 3 (e.g. `INSUFFICIENT_FUNDS` → "The payment was declined because your available balance was too low"; `DAILY_LIMIT_REACHED` → "Your daily transfer limit was already reached earlier that day").

For `DISPUTED` transactions: also query `support_cases` for an existing dispute case before advising the customer to open a new one.

---

**If intent is `LOAN_INQUIRY`:**

Execute `iceberg-mcp-server`:

1. All active loans for the customer:
   ```sql
   SELECT loan_id, loan_type, original_amount, outstanding_balance,
          interest_rate_pct, monthly_payment, next_payment_date,
          next_payment_amount, last_payment_date, last_payment_amount,
          payments_overdue, status, maturity_date, collateral, notes
   FROM loans
   WHERE customer_id = '<customer_id>'
   ORDER BY origination_date DESC
   ```

2. If a specific loan ID is mentioned:
   ```sql
   SELECT *
   FROM loans
   WHERE loan_id = '<loan_id from Task 1>'
   ```

For delinquent or defaulted loans: note `payments_overdue` count and compute total arrears as `monthly_payment × payments_overdue`. If `status = 'DEFAULT'`, escalation is mandatory. If `status = 'DELINQUENT'` (1–2 payments overdue), offer a payment arrangement before escalating.

---

**If intent is `CARD_INQUIRY`:**

Execute `iceberg-mcp-server`:

1. All cards for the customer:
   ```sql
   SELECT card_id, card_type, card_number_masked, status, block_reason,
          expiry_date, credit_limit, current_balance, available_credit,
          last_used_date, notes
   FROM cards
   WHERE customer_id = '<customer_id>'
   ```

2. If only last-4 digits provided:
   ```sql
   SELECT c.card_id, c.card_type, c.card_number_masked, c.status,
          c.block_reason, c.expiry_date, c.credit_limit, c.current_balance,
          c.available_credit, a.status AS account_status, a.lock_reason
   FROM cards c
   JOIN accounts a ON c.account_id = a.account_id
   WHERE c.customer_id = '<customer_id>'
     AND c.card_number_masked = '****<last4>'
   ```

For blocked cards: the `block_reason` field determines the resolution path. A block caused by `ACCOUNT_LOCKED` or `ACCOUNT_FROZEN` cannot be lifted by reissuing the card alone — the underlying account issue must be resolved first. An `EXPIRED` card requires a replacement request. A `FRAUD` block requires fraud team verification before a new card is issued.

---

**If intent is `FRAUD_REPORT`:**

Execute `iceberg-mcp-server` immediately. This intent always triggers escalation in Task 3.

1. Retrieve recent transactions to identify the suspicious ones alongside the customer's report:
   ```sql
   SELECT transaction_id, transaction_type, amount, currency, merchant_name,
          merchant_category, description, status, initiated_at, completed_at,
          channel, reference_number, notes
   FROM transactions
   WHERE account_id = '<account_id>'
   ORDER BY initiated_at DESC
   LIMIT 20
   ```

2. Check whether a fraud case is already open (avoid opening a duplicate):
   ```sql
   SELECT case_id, subject, status, priority, created_at, updated_at, notes
   FROM support_cases
   WHERE customer_id = '<customer_id>'
     AND case_type = 'FRAUD_REPORT'
     AND status NOT IN ('RESOLVED', 'CLOSED')
   ORDER BY created_at DESC
   ```

3. Check the account status — it may already be locked due to the same fraud event:
   ```sql
   SELECT account_id, account_type, account_number_masked, status, lock_reason, notes
   FROM accounts
   WHERE customer_id = '<customer_id>'
   ```

Cross-reference the transactions the customer describes with what appears in the database. Identify any transactions with suspicious indicators in the `notes` field (geolocation mismatch, unusual hours, foreign merchant). Summarise which transactions appear unauthorized and which appear legitimate.

---

**If intent is `GENERAL`:**

Use `rag_studio_tool` with `action: "query"` against the **Banking Procedures Knowledge Base**. Formulate the query directly from the customer's message in `{input}`. Retrieve the top 3 chunks and synthesise a clear, step-by-step response. If the question involves account security or fraud prevention, always include the relevant security notice.

**Expected Output (`ACCOUNT_STATUS` example):**
```json
{
  "data_source": "iceberg-mcp-server",
  "queries_executed": [
    "SELECT ... FROM accounts WHERE customer_id = 'CUST-B003'",
    "SELECT ... FROM support_cases WHERE customer_id = 'CUST-B003' AND status NOT IN ('RESOLVED','CLOSED')"
  ],
  "result": {
    "accounts": [
      {
        "account_id": "ACC-100006",
        "account_type": "CHECKING",
        "account_number_masked": "****8844",
        "current_balance": 1234.56,
        "available_balance": 0.00,
        "status": "LOCKED",
        "lock_reason": "FRAUD_ALERT",
        "last_activity_date": "2026-03-12",
        "notes": "Locked on 2026-03-12 after two unauthorized international transactions detected."
      }
    ],
    "open_cases": [
      {
        "case_id": "CASE-2026-0001",
        "case_type": "FRAUD_REPORT",
        "status": "OPEN",
        "priority": "HIGH"
      }
    ]
  }
}
```

**Success Criteria:**
- Correct queries executed for the detected intent
- At least one result row retrieved, or absence of result explicitly noted
- For `ACCOUNT_STATUS`: lock reason and open cases both retrieved
- For `TRANSACTION_INQUIRY`: `failure_reason` retrieved for FAILED transactions; existing dispute case checked for DISPUTED transactions
- For `LOAN_INQUIRY`: `payments_overdue` and `status` retrieved for delinquency assessment
- For `FRAUD_REPORT`: recent 20 transactions and existing fraud cases both retrieved

---

### Task 3: Response Composition & Memory Storage

This task has **two distinct outputs** that must be kept separate:
1. The **customer response** — the verbose, empathetic message sent back to the customer
2. The **memory note** — a compact, structured summary stored in LightMem for future sessions

---

#### Part A — Compose the Customer Response

Using the data retrieved in Task 2 and the prior context from Task 1, compose a clear, empathetic, and actionable response. Follow these guidelines:

- **Tone:** Warm, reassuring, and jargon-free. Customers contacting support are often anxious — about locked funds, missing payments, or suspected fraud. Acknowledge the inconvenience before explaining the situation.
- **Account lock/freeze:** State the specific reason in plain language, explain what the customer needs to do to resolve it, and give a realistic timeframe.
- **Transaction inquiry:** Confirm the transaction details (amount, date, merchant), state the current status plainly, and explain what happens next. For pending items, give an expected posting timeframe. For failed items, explain the root cause and exactly how to fix it.
- **Loan inquiry:** State the outstanding balance, next payment date and amount, and whether any payments are overdue. If delinquent, explain the consequences and options (payment arrangement, hardship programme) before escalating.
- **Card inquiry:** State the card status and root cause. Distinguish between a card-level block (can sometimes be resolved by reissue) and an account-level lock (card block will persist until the account is unlocked).
- **Fraud report:** Acknowledge the report immediately, confirm which transactions appear unauthorized, explain what the bank is doing (lock, investigation, provisional credit timeline), and provide a case reference number. Never ask the customer to "wait and see."
- **If data not found:** Acknowledge the limitation, ask for additional identifiers (account number, reference number, date of transaction, loan ID), and offer to escalate.

**Escalation triggers — always proactively offer transfer to a specialist:**

| Trigger condition | Escalation type |
|---|---|
| Account `status = 'LOCKED'` and `lock_reason = 'FRAUD_ALERT'` | Fraud specialist team |
| Account `status = 'FROZEN'` pending identity verification | Security/identity verification team |
| Any `FRAUD_REPORT` intent regardless of account status | Fraud specialist team |
| Loan `status = 'DEFAULT'` | Collections / loan resolution team |
| Loan `payments_overdue >= 3` | Collections team |
| Disputed transaction amount > USD 500 | Disputes resolution team |
| AML / `LARGE_CASH_DEPOSITS` lock | Compliance team |

---

#### Part B — Store a Memory Note (NOT the customer response)

> **Why a separate memory note?** The customer response is verbose and formatted for human conversation. If stored verbatim, future retrieval would return long paragraphs that are difficult for the agent to parse. The memory note is designed for machine retrieval — dense, structured, and rich in identifiers.

**Step 1:** Call `get_timestamp` to get the current timestamp.

**Step 2:** Construct the `assistant_reply` as a structured memory note using the following template:

```
CUSTOMER: <full_name> (<customer_id>).
QUERY TYPE: <ACCOUNT_STATUS | TRANSACTION_INQUIRY | LOAN_INQUIRY | CARD_INQUIRY | FRAUD_REPORT | GENERAL>.
ACCOUNT: <account_id> (<account_type>, <account_number_masked>). STATUS: <status>. LOCK REASON: <lock_reason or "none">.
BALANCE: <current_balance> total / <available_balance> available.
TRANSACTION: <transaction_id> — <description>, <amount> <currency>, <status>. [Omit if not relevant.]
LOAN: <loan_id> — <loan_type>, <outstanding_balance> outstanding, <payments_overdue> payment(s) overdue, <status>. [Omit if not relevant.]
CARD: <card_id> — <card_type>, <card_number_masked>, <status>. BLOCK REASON: <block_reason or "none">. [Omit if not relevant.]
ISSUE: <one-sentence summary of the customer's concern>.
ACTION TAKEN: <what the agent said or did>.
ESCALATED: <Yes/No> — <reason and team if yes>.
CASE REF: <case_id if a support case was referenced or opened, else omit>.
SUPERSEDES: <reference> — if this note updates a prior memory for the same account or issue. Omit on first contact.
```

For `GENERAL` queries (no account data retrieved), use:
```
CUSTOMER: <full_name or "unknown">.
QUERY TYPE: GENERAL.
TOPIC: <brief topic, e.g. "how to dispute a transaction" or "international wire transfer fees">.
KEY FACTS PROVIDED: <bullet summary of the main points covered>.
FOLLOW-UP EXPECTED: <Yes/No> — <reason if yes>.
```

> **Append-only behaviour:** `add_memory` always inserts a new record — it does not update existing entries. For returning customers, multiple notes for the same issue accumulate over time. Always add the new note (including `SUPERSEDES` when applicable) rather than trying to modify the old one. In Task 1, when `retrieve_memory` returns multiple notes for the same account, treat the one with the most recent timestamp as authoritative for current status, and use older notes for historical context only.

**Step 3:** Call `add_memory` with:
- `user_input`: the customer's **original verbatim message** from `{input}`
- `assistant_reply`: the **memory note** constructed in Step 2 (not the customer response)
- `timestamp`: the timestamp from Step 1
- `force_extract`: set to `true` if the intent is `FRAUD_REPORT`, `ACCOUNT_STATUS` with a non-ACTIVE account, or `LOAN_INQUIRY` with a delinquent/defaulted loan; otherwise omit (defaults to false)

**What gets stored in memory — and why each field matters:**

| Memory field | What to include | Why it matters for future retrieval |
|---|---|---|
| `user_input` | Customer's raw message | Enables semantic search: "find sessions where a customer asked about a pending international wire" |
| Customer name / ID | Always include if known | Lets future queries filter by "find all memories for Maria Garcia" |
| Account ID, type, last-4 | Always include if account was retrieved | Allows agent to identify the account on a follow-up without customer repeating it |
| Account status + lock reason | Include exact status code | Shows how the case evolved: LOCKED → UNLOCKED across sessions |
| Transaction ID and status | Include if a specific transaction was discussed | Tracks whether a pending item posted or a failed payment was resolved |
| Loan ID, balance, overdue count | Include if loan discussed | Tracks payment history and delinquency progression across sessions |
| Card status + block reason | Include if card discussed | Prevents asking same questions on a follow-up |
| Issue description | One sentence summary | Powers semantic retrieval for similar future queries |
| Action taken | What the agent said or did | Prevents repeating the same advice on a follow-up call |
| Escalation flag | Yes/No + team | Ensures specialists have context if the case was referred |
| Case reference | Case ID if applicable | Links memory to active support case for continuity |

---

**Expected Output:**

```json
{
  "customer_response": "Hi Maria — I can see your checking account ending in 8844 is currently locked. This was triggered automatically on 12 March after our fraud detection system identified two transactions that didn't match your usual spending pattern: a $450.00 purchase from an unknown merchant in Russia at 10:34 PM, and a $1,200.00 charge at an international electronics retailer at 3:17 AM. These have been flagged as potentially unauthorized and case CASE-2026-0001 has been opened for investigation. Your available balance is currently $0 while the lock is in place to protect your funds — your actual balance of $1,234.56 is safe. I'm going to connect you with our fraud specialist team now so they can walk you through the next steps, including verifying these charges and arranging a replacement card if needed. Your case reference is CASE-2026-0001. Is that okay?",
  "memory_note_stored": "CUSTOMER: Maria Garcia (CUST-B003). QUERY TYPE: ACCOUNT_STATUS. ACCOUNT: ACC-100006 (CHECKING, ****8844). STATUS: LOCKED. LOCK REASON: FRAUD_ALERT. BALANCE: $1,234.56 total / $0.00 available. TRANSACTION: TXN-2026-000012 — $450.00 Unknown Merchant RU, COMPLETED (suspicious). TXN-2026-000013 — $1,200.00 TechStore International, COMPLETED (suspicious). ISSUE: Customer asked why account is locked. Two unauthorized international transactions on 2026-03-12. ACTION TAKEN: Explained lock reason and two suspicious transactions. Offered transfer to fraud team. Provided case reference. ESCALATED: Yes — FRAUD_ALERT lock. Fraud specialist team. CASE REF: CASE-2026-0001.",
  "escalation_recommended": true,
  "memory_stored": true
}
```

**Success Criteria:**
- Customer response is clear, empathetic, and directly answers the query
- `get_timestamp` called before `add_memory`
- `add_memory` stores the **memory note** (not the verbose customer response) as `assistant_reply`
- All key identifiers (account ID, status, transaction IDs, case reference) captured in memory note
- Escalation offered where required by the escalation trigger table

---

## Agent Definition

### Banking Support Agent

| Attribute | Value |
|---|---|
| **Name** | Banking Support Agent |
| **Role** | 24/7 AI-Powered Digital Banking Support Assistant |

**Backstory:**
You are a knowledgeable and empathetic banking support specialist for a digital bank. You have comprehensive knowledge of account management, payment processing, loan servicing, card operations, and fraud procedures. You understand that customers reaching out about locked accounts, failed payments, or unauthorized transactions are often stressed — these issues affect their daily lives and finances — so you communicate clearly, calmly, and with genuine care. You remember previous conversations so customers never have to repeat their situation. You proactively escalate to the right specialist team when an issue requires human intervention, and you always give the customer a case reference number and a clear next step before ending the conversation.

**Goal:**
1. Greet the customer and use memory to recall any prior context for this session.
2. Understand what the customer needs — account status, transaction inquiry, loan question, card issue, fraud report, or general guidance.
3. Look up live account, transaction, loan, or card data from the banking database.
4. Compose a clear, reassuring response with specific next steps and realistic timeframes.
5. Save the conversation to memory so the next session can pick up seamlessly.
6. Escalate to the appropriate specialist team when the situation requires it.

**Tools:**
- LightMem MCP: `get_timestamp`, `add_memory`, `retrieve_memory`
- `iceberg-mcp-server` (account, transaction, loan, card, and case lookups)
- `rag_studio_tool` (action: `query`, Knowledge Base: Banking Procedures KB)

**Conversation style examples:**

*Account lock — fraud:*
> "I can see your account has been locked as a precaution because we detected some unusual activity. I know that's worrying — let me explain exactly what happened and what we'll do to fix it. I'm going to connect you with our fraud team right now who can resolve this quickly."

*Pending transaction:*
> "Your transfer of $800.00 is still processing — ACH transfers typically take 1 business day, so it should appear in the recipient's account by tomorrow morning. Your reference number is REF-2026-KK004 if you need to follow up."

*Loan delinquency:*
> "I can see your personal loan has one missed payment from last month. The good news is it hasn't gone to default yet. I'd recommend making the overdue payment today to avoid late fees — I can walk you through how to do that, or I can connect you with our loan team to discuss a payment arrangement if you need more flexibility."

*Fraud report:*
> "I'm really sorry to hear that — let's get this sorted straight away. I can see the transaction you're describing. I'm flagging this as unauthorized right now, locking your card, and opening a fraud case. You'll receive provisional credit within 5 business days while we investigate. Your case number is CASE-2026-0009."

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
        "LIGHTMEM_DATA_PATH": "/data/shared/banking_chatbot/lightmem/",
        "LIGHTMEM_COLLECTION_NAME": "banking_chatbot_memory"
      }
    }
  }
}
```

> **Important:** `LIGHTMEM_DATA_PATH` must be a **shared, persistent location** accessible across all agent sessions — not a session-specific temp folder. Use `/data/shared/` or a mounted persistent volume.

| LightMem Tool | Used In | Purpose |
|---|---|---|
| `get_timestamp` | Task 3 | Timestamp for memory storage |
| `retrieve_memory` | Task 1 | Recall prior customer context |
| `add_memory` | Task 3 | Store conversation for future sessions |

### `iceberg-mcp-server`
Queries the Cloudera Data Warehouse for live account and transaction data.

**Required tables:** `customers`, `accounts`, `transactions`, `loans`, `cards`, `support_cases`

### `rag_studio_tool`
Semantic search over the Banking Procedures Knowledge Base.
- **Action:** `query`
- **Knowledge Base:** Banking Procedures KB (see setup below)
- **Embedding model:** `text-embedding-3-small` (configured in RAG Studio)

---

## Knowledge Base Setup

**Banking Procedures KB** — ingest the following documents from `extra_materials/banking_chatbot_demo_data/procedures_kb/`:

| Document | Covers |
|---|---|
| `account_management_guide.md` | Account types, lock and freeze policies, dormancy, closure procedures, identity verification requirements |
| `fraud_prevention_guide.md` | Fraud detection triggers, dispute process, provisional credit policy, chargeback timelines, card replacement |
| `loan_procedures_guide.md` | Loan payment methods, delinquency process, default consequences, hardship programmes, loan modification options |
| `faq_banking_common_queries.md` | Top 30 most common digital banking questions and answers |

Chunk size: 512 tokens, overlap: 50 tokens, embedding model: `text-embedding-3-small`.

---

## Required Database Tables (CDW)

| Table | Purpose | Key Columns |
|---|---|---|
| `customers` | Customer identity and KYC — used for caller identification and personalisation | `customer_id`, `full_name`, `email`, `phone`, `kyc_status`, `customer_segment` |
| `accounts` | Bank accounts — primary lookup for balance, status, and lock inquiries | `account_id`, `customer_id`, `account_type`, `account_number_masked`, `current_balance`, `available_balance`, `status`, `lock_reason` |
| `transactions` | Full transaction history — lookup for status, failure reason, and dispute inquiries | `transaction_id`, `account_id`, `customer_id`, `amount`, `status`, `initiated_at`, `failure_reason`, `reference_number` |
| `loans` | Loan accounts — lookup for balance, payment schedule, and default status | `loan_id`, `customer_id`, `loan_type`, `outstanding_balance`, `monthly_payment`, `next_payment_date`, `payments_overdue`, `status` |
| `cards` | Payment cards — lookup for card status, block reason, and credit inquiries | `card_id`, `account_id`, `customer_id`, `card_type`, `card_number_masked`, `status`, `block_reason`, `credit_limit`, `available_credit` |
| `support_cases` | Open and historical support cases — context for escalation and duplicate case prevention | `case_id`, `customer_id`, `case_type`, `status`, `priority`, `account_id`, `transaction_id` |

Synthetic data files and Impala DDL are in `extra_materials/banking_chatbot_demo_data/synthetic_db/`.

---

## Workflow Summary

| Stage | Task | Tools | Input | Output |
|---|---|---|---|---|
| 1 | Memory Recall & Intent Detection | `retrieve_memory` | `{input}` | Intent, extracted identifiers, prior context summary |
| 2 | Data Retrieval | `iceberg-mcp-server` OR `rag_studio_tool` | Intent + identifiers from Task 1 | Account/transaction/loan/card records OR KB guidance chunks |
| 3A | Response Composition | (LLM synthesis) | Task 1 + Task 2 outputs | Verbose, customer-facing reply |
| 3B | Memory Storage | `get_timestamp`, `add_memory` | Key facts from Tasks 1–3A | Structured memory note stored in LightMem |

---

## Sample Conversation Flows

### Flow A — Account Lock Query (FRAUD_ALERT)
```
Customer: "My card is suddenly not working and I can't log into my account properly"
→ Task 1: Intent = ACCOUNT_STATUS, customer_id = CUST-B003
→ Task 2: accounts query → ACC-100006 LOCKED / FRAUD_ALERT. Support cases → CASE-2026-0001 OPEN HIGH
→ Task 3: Explains fraud lock, names the two suspicious transactions, provides case ref
          Escalation triggered (FRAUD_ALERT). Memory stored.
```

### Flow B — Pending Transaction Inquiry
```
Customer: "I sent an $800 transfer two days ago and it still hasn't arrived"
→ Task 1: Intent = TRANSACTION_INQUIRY, customer_id = CUST-B011
→ Task 2: transactions query → TXN-2026-000041, PENDING, ACH, initiated 2026-03-16
→ Task 3: Confirms transfer is processing, gives reference number and expected posting date
          Memory stored (no escalation needed).
```

### Flow C — Returning Customer (memory in action)
```
Customer: "Hi, it's Maria again — any update on my account?"
→ Task 1: retrieve_memory → finds prior context: "ACC-100006 LOCKED / FRAUD_ALERT.
          CASE-2026-0001 OPEN. Customer was connected to fraud team."
          Intent = ACCOUNT_STATUS, account inferred from memory (no identifiers in message)
→ Task 2: SQL lookup → ACC-100006 still LOCKED. CASE-2026-0001 still OPEN.
→ Task 3: "Since we last spoke, the fraud investigation is still in progress.
          Your case CASE-2026-0001 is being handled by our fraud team..."
          Updates memory with SUPERSEDES note.
```

### Flow D — Loan Default Escalation
```
Customer: "I keep getting letters about my loan — what's going on?"
→ Task 1: Intent = LOAN_INQUIRY, customer_id = CUST-B015
→ Task 2: loans query → LOAN-2024-0003 DEFAULT, 5 payments overdue. accounts → ACC-100024 LOCKED/LOAN_DEFAULT
→ Task 3: Explains loan default and account lock. Escalation triggered (DEFAULT + 5 overdue payments).
          Offers collections team transfer for payment arrangement.
          Memory stored with force_extract: true.
```

---

## Sample Inputs — Synthetic Data Walkthrough

The following scenarios are drawn from `synthetic_db/customers.csv`, `synthetic_db/accounts.csv`, and `synthetic_db/transactions.csv`. Each shows a first-time query and a follow-up, along with the memory note that bridges the two sessions.

---

### Scenario 1 — Maria Garcia (CUST-B003): Fraud Lock on Checking Account

**DB records:** ACC-100006 · `LOCKED` / `FRAUD_ALERT` · balance $1,234.56 / available $0.00 · TXN-2026-000012 ($450 Russia, COMPLETED, suspicious) · TXN-2026-000013 ($1,200 Eastern Europe, COMPLETED, suspicious) · CASE-2026-0001 OPEN HIGH

**Day 1 — First contact (2026-03-12):**
> Hi, I'm Maria Garcia. My debit card just got declined at the supermarket and I can't see my checking account balance in the app. What's happening?

| Task | What happens |
|---|---|
| Task 1 | Intent = `ACCOUNT_STATUS` · `full_name` = Maria Garcia · resolved `customer_id` = CUST-B003 · no prior memories |
| Task 2 | `accounts` query → ACC-100006 LOCKED / FRAUD_ALERT. `support_cases` → CASE-2026-0001 OPEN HIGH |
| Task 3A | Explains that account was locked automatically after two suspicious international transactions at 10:34 PM and 3:17 AM. Names the transactions. Provides case reference CASE-2026-0001. Escalates to fraud team. |
| Task 3B | `force_extract: true` (FRAUD_ALERT lock). Memory note stored: |

```
CUSTOMER: Maria Garcia (CUST-B003).
QUERY TYPE: ACCOUNT_STATUS.
ACCOUNT: ACC-100006 (CHECKING, ****8844). STATUS: LOCKED. LOCK REASON: FRAUD_ALERT.
BALANCE: $1,234.56 total / $0.00 available.
TRANSACTION: TXN-2026-000012 — $450.00 Unknown Merchant RU, COMPLETED (flagged suspicious).
             TXN-2026-000013 — $1,200.00 TechStore International, COMPLETED (flagged suspicious).
ISSUE: Customer's card declined and app showing no balance — account locked due to fraud alert triggered by two international transactions on 2026-03-12.
ACTION TAKEN: Explained fraud lock and two suspicious transactions. Provided case reference CASE-2026-0001. Connected customer to fraud specialist team.
ESCALATED: Yes — FRAUD_ALERT lock. Fraud specialist team.
CASE REF: CASE-2026-0001.
```

**Day 6 — Follow-up (2026-03-18):**
> Hi, it's Maria again. It's been almost a week and my account is still locked. I need access to my money. Has anyone looked at my case?

| Task | What happens |
|---|---|
| Task 1 | Intent = `ACCOUNT_STATUS` · customer identified by name · `retrieve_memory` → prior note: ACC-100006 LOCKED / FRAUD_ALERT, CASE-2026-0001 OPEN, fraud team escalation |
| Task 2 | `accounts` query → ACC-100006 still LOCKED / FRAUD_ALERT (no change). `support_cases` → CASE-2026-0001 status IN_PROGRESS, updated 2026-03-16 |
| Task 3A | Acknowledges frustration. Reports case status: IN_PROGRESS, last updated 2026-03-16. Advises customer that fraud investigations typically take 5–10 business days. Escalates again to fraud team with updated urgency given customer's need for funds access. |
| Task 3B | New note with `SUPERSEDES: ACC-100006 — prior note dated 2026-03-12, account still locked, fraud investigation ongoing.` |

---

### Scenario 2 — Kevin Murphy (CUST-B015): Loan Default & Account Lock

**DB records:** LOAN-2024-0003 · `DEFAULT` · 5 payments overdue · total arrears $1,730.75 · ACC-100024 · `LOCKED` / `LOAN_DEFAULT` · balance $567.00 / available $0.00

**Day 1 — First contact (2026-03-18):**
> I've been getting letters saying I owe money on a loan. I also tried to use my card today and it was declined. What's going on with my account?

| Task | What happens |
|---|---|
| Task 1 | Intent = `ACCOUNT_STATUS` (card declined + account access issue; no fraud keywords) · `customer_id` = CUST-B015 · no prior memories |
| Task 2 | `accounts` → ACC-100024 LOCKED / LOAN_DEFAULT, available $0.00. `loans` → LOAN-2024-0003 DEFAULT, 5 payments overdue, total arrears $1,730.75. `support_cases` → CASE-2026-0004 ESCALATED CRITICAL |
| Task 3A | Explains account was locked because personal loan LOAN-2024-0003 has been in default since November 2025 (5 missed payments totalling $1,730.75). Card is blocked for the same reason. Presents two options: (1) pay the full arrears to immediately unlock the account, (2) call the collections team to arrange a payment plan. **Escalation triggered** (DEFAULT + 5 overdue payments). |
| Task 3B | `force_extract: true` (LOAN DEFAULT). Memory note stored: |

```
CUSTOMER: Kevin Murphy (CUST-B015).
QUERY TYPE: ACCOUNT_STATUS.
ACCOUNT: ACC-100024 (CHECKING, ****6655). STATUS: LOCKED. LOCK REASON: LOAN_DEFAULT.
BALANCE: $567.00 total / $0.00 available.
LOAN: LOAN-2024-0003 — PERSONAL, $9,800.00 outstanding, 5 payment(s) overdue, DEFAULT. Total arrears: $1,730.75.
CARD: CARD-000014 — DEBIT, ****6655, BLOCKED. BLOCK REASON: LOAN_DEFAULT.
ISSUE: Customer's card declined. Account locked due to 5 missed loan payments (Nov 2025–Mar 2026). Collections in progress.
ACTION TAKEN: Explained loan default and account/card lock. Presented payment-in-full vs payment-arrangement options. Connected customer to collections team.
ESCALATED: Yes — LOAN DEFAULT (5 payments overdue). Collections team.
CASE REF: CASE-2026-0004.
```

---

### Scenario 3 — Yuki Tanaka (CUST-B013): Pending International Wire (Memory in Action)

**DB records:** ACC-100021 · ACTIVE · TXN-2026-000048 · `PENDING` · $5,000.00 wire to Japan · initiated 2026-03-14

**Day 1 — First contact (2026-03-14):**
> Hi, I just sent a wire transfer of $5,000 to Japan for my family. The reference is REF-2026-MM003. How long will it take to arrive?

| Task | What happens |
|---|---|
| Task 1 | Intent = `TRANSACTION_INQUIRY` · `transaction_ref` = REF-2026-MM003 · no prior memories |
| Task 2 | `transactions` → TXN-2026-000048 PENDING, WIRE, $5,000, initiated 2026-03-14 11:00, compliance review for international wire |
| Task 3A | Confirms wire is in progress and under standard compliance review. Gives estimated delivery: 2–3 business days (by 2026-03-17 or 2026-03-18). Provides reference REF-2026-MM003 and case CASE-2026-0007. |
| Task 3B | Memory note stored (no escalation): |

```
CUSTOMER: Yuki Tanaka (CUST-B013).
QUERY TYPE: TRANSACTION_INQUIRY.
ACCOUNT: ACC-100021 (CHECKING, ****7788). STATUS: ACTIVE.
TRANSACTION: TXN-2026-000048 — WIRE, $5,000.00 to Japan (Tanaka Family), PENDING. Initiated 2026-03-14 11:00. Ref: REF-2026-MM003.
ISSUE: Customer asked for wire transfer delivery estimate. Transfer in standard international compliance review.
ACTION TAKEN: Confirmed PENDING status. Advised 2–3 business day delivery window (by 2026-03-17/18). Provided reference number.
ESCALATED: No.
CASE REF: CASE-2026-0007.
```

**Day 4 — Follow-up (2026-03-18):**
> Hi, it's Yuki. I sent a wire to Japan on Saturday — my family still hasn't received it. It should have been there by now.

| Task | What happens |
|---|---|
| Task 1 | Intent = `TRANSACTION_INQUIRY` · customer identified by name · `retrieve_memory` → prior note: TXN-2026-000048 PENDING, $5,000 wire to Japan, initiated 2026-03-14, expected 2026-03-17/18 |
| Task 2 | `transactions` → TXN-2026-000048 still PENDING (now 4 days). `support_cases` → CASE-2026-0007 IN_PROGRESS, last updated 2026-03-16 |
| Task 3A | "Since your call on 14 March, the wire is still showing as pending — this is now past the original 2–3 day estimate. I'm escalating this to our wire transfer team to investigate the delay and get an urgent update. Your reference is still REF-2026-MM003." Escalates to wire transfer specialist team. |
| Task 3B | `SUPERSEDES: TXN-2026-000048 — prior note dated 2026-03-14, wire still PENDING beyond expected delivery window. Escalated to wire team.` |

---

### Scenario 4 — Priya Sharma (CUST-B011): Pending ACH + Expired Card (Two Intents)

**DB records:** ACC-100019 · ACTIVE · TXN-2026-000041 PENDING ACH $800 · TXN-2026-000042 FAILED insurance $75 / `CARD_EXPIRED` · CARD-000019 EXPIRED

**Day 1 — First contact (2026-03-16):**
> I made a transfer of $800 on Monday and it hasn't shown up yet. Also my insurance payment failed — I'm not sure why.

| Task | What happens |
|---|---|
| Task 1 | Intent spans `TRANSACTION_INQUIRY` (both a pending transfer and a failed payment). Classified as `TRANSACTION_INQUIRY` — the message mentions two specific transactions. `customer_id` = CUST-B011. No prior memories. |
| Task 2 | `transactions` → TXN-2026-000041 PENDING ACH $800 (initiated 2026-03-16, expected 2026-03-17). TXN-2026-000042 FAILED $75 / `CARD_EXPIRED`. `cards` → CARD-000019 EXPIRED (expired Dec 2025) |
| Task 3A | Addresses both: (1) $800 ACH transfer is processing normally, expected tomorrow. (2) Insurance payment failed because the debit card on file (****5544) expired in December 2025. Advises customer to request a card replacement and update their payment method with the insurer. |
| Task 3B | Memory note stored (no escalation): |

```
CUSTOMER: Priya Sharma (CUST-B011).
QUERY TYPE: TRANSACTION_INQUIRY.
ACCOUNT: ACC-100019 (CHECKING, ****5544). STATUS: ACTIVE.
TRANSACTION: TXN-2026-000041 — TRANSFER, $800.00 ACH to savings, PENDING. Initiated 2026-03-16. Expected 2026-03-17.
             TXN-2026-000042 — PAYMENT, $75.00 insurance premium, FAILED. Reason: CARD_EXPIRED. Card ****5544 (CARD-000019) expired 2025-12-31.
CARD: CARD-000019 — DEBIT, ****5544, EXPIRED. Expiry: 2025-12-31.
ISSUE: Customer asked about pending ACH transfer and failed insurance payment. ACH is processing normally. Insurance failed due to expired card.
ACTION TAKEN: Confirmed ACH pending — advised expected posting 2026-03-17. Explained card expiry as failure cause. Advised customer to request replacement card and update insurer payment method.
ESCALATED: No.
FOLLOW-UP EXPECTED: Yes — customer needs to request card replacement and confirm ACH posts.
```

---

## Memory Schema

### How LightMem Stores Information

Each call to `add_memory` stores a `(user_input, assistant_reply)` pair. LightMem embeds both fields and indexes them for semantic similarity search. When `retrieve_memory` is called, it returns the pairs whose embeddings are closest to the query.

**The key design choice:** `assistant_reply` is a **structured memory note**, not the customer-facing response. This ensures future retrievals return dense, parseable information rather than verbose conversation text.

---

### Memory Note Templates

#### Template 1 — Account / Transaction / Loan / Card / Fraud Queries
```
CUSTOMER: <full_name> (<customer_id>).
QUERY TYPE: <ACCOUNT_STATUS | TRANSACTION_INQUIRY | LOAN_INQUIRY | CARD_INQUIRY | FRAUD_REPORT>.
ACCOUNT: <account_id> (<account_type>, <account_number_masked>). STATUS: <status>. LOCK REASON: <lock_reason or "none">.
BALANCE: <current_balance> total / <available_balance> available.
TRANSACTION: <transaction_id> — <description>, <amount> <currency>, <status>. [Omit if not relevant.]
LOAN: <loan_id> — <loan_type>, <outstanding_balance> outstanding, <payments_overdue> payment(s) overdue, <status>. [Omit if not relevant.]
CARD: <card_id> — <card_type>, <card_number_masked>, <status>. BLOCK REASON: <block_reason or "none">. [Omit if not relevant.]
ISSUE: <one-sentence summary of customer concern>.
ACTION TAKEN: <what the agent said or did>.
ESCALATED: <Yes/No> — <reason and team if yes>.
CASE REF: <case_id if applicable, else omit>.
SUPERSEDES: <reference> — omit on first contact.
```

**Example (first contact — fraud lock):**
```
CUSTOMER: Maria Garcia (CUST-B003).
QUERY TYPE: ACCOUNT_STATUS.
ACCOUNT: ACC-100006 (CHECKING, ****8844). STATUS: LOCKED. LOCK REASON: FRAUD_ALERT.
BALANCE: $1,234.56 total / $0.00 available.
TRANSACTION: TXN-2026-000012 — $450.00 Unknown Merchant RU, COMPLETED (flagged). TXN-2026-000013 — $1,200.00 TechStore International, COMPLETED (flagged).
ISSUE: Account locked after two unauthorized international transactions on 2026-03-12. Card also blocked.
ACTION TAKEN: Explained lock and transactions. Transferred to fraud team. Provided case reference.
ESCALATED: Yes — FRAUD_ALERT. Fraud specialist team.
CASE REF: CASE-2026-0001.
```

**Example (returning customer — account still locked):**
```
CUSTOMER: Maria Garcia (CUST-B003).
QUERY TYPE: ACCOUNT_STATUS.
ACCOUNT: ACC-100006 (CHECKING, ****8844). STATUS: LOCKED. LOCK REASON: FRAUD_ALERT.
BALANCE: $1,234.56 total / $0.00 available.
ISSUE: Follow-up — account still locked 6 days after initial fraud lock. Case CASE-2026-0001 now IN_PROGRESS.
ACTION TAKEN: Confirmed investigation still open. Re-escalated to fraud team with urgency flag for funds-access concern.
ESCALATED: Yes — FRAUD_ALERT ongoing. Fraud specialist team (re-escalated).
CASE REF: CASE-2026-0001.
SUPERSEDES: ACC-100006 — prior note dated 2026-03-12, account still locked, investigation in progress.
```

---

#### Template 2 — General Queries
```
CUSTOMER: <full_name or "unknown">.
QUERY TYPE: GENERAL.
TOPIC: <brief topic, e.g. "how to dispute a transaction" or "wire transfer fees to Europe">.
KEY FACTS PROVIDED:
  - <bullet point 1>
  - <bullet point 2>
  - <bullet point 3>
FOLLOW-UP EXPECTED: <Yes/No> — <reason if yes>.
```

**Example:**
```
CUSTOMER: Yuki Tanaka (CUST-B013).
QUERY TYPE: GENERAL.
TOPIC: International wire transfer processing times and compliance review.
KEY FACTS PROVIDED:
  - International wires take 2–3 business days under standard compliance review
  - SWIFT tracking number provided to sender after compliance clearance
  - Wires over $10,000 require additional documentation per BSA requirements
  - Customer can call back with reference REF-2026-MM003 for status updates
FOLLOW-UP EXPECTED: Yes — customer will call back if wire not received within 3 business days.
```

---

### What Each Memory Field Enables

| Field stored | Enables in future sessions |
|---|---|
| `user_input` (customer's raw message) | Semantic search: "find sessions where a customer asked about a locked account due to fraud" |
| `CUSTOMER: {name} ({id})` | Customer identification without asking: returning customer says "any update?" and agent retrieves their account context |
| Account ID, type, last-4 | Implicit account reference: agent knows which account without customer repeating it |
| `STATUS: {status}` + `LOCK REASON` | Case evolution tracking: agent tells customer "since your last call, your account has moved from LOCKED back to ACTIVE" |
| Transaction ID and status | Transaction continuity: agent knows whether a PENDING item has posted or a FAILED payment was retried |
| Loan balance and overdue count | Delinquency tracking: agent knows whether payment was made since the last call |
| `ACTION TAKEN` | Avoids redundancy: agent does not repeat the same advice on a follow-up call |
| `ESCALATED: Yes` | Specialist context: if the call reaches a human, full prior history is available |
| `CASE REF` | Links memory to live support case: agent can check case status without the customer knowing the case ID |
| `SUPERSEDES: <ref>` | Temporal ordering: when multiple notes exist for the same account, agent knows which is the most recent authoritative record |

---

### When to Use `force_extract: true`

Pass `force_extract: true` in the `add_memory` call when the conversation contains many named entities (customer names, account IDs, transaction references, loan IDs, case numbers).

**Use `force_extract: true` for:**
- Any `FRAUD_REPORT` intent
- `ACCOUNT_STATUS` where account is LOCKED, FROZEN, or UNDER_REVIEW
- `LOAN_INQUIRY` where loan is DELINQUENT or DEFAULT
- Any session that references multiple transaction IDs or a support case number

**Skip `force_extract` (default False) for:**
- General procedure questions with no specific account context
- Simple balance checks on ACTIVE accounts with no issues
- FAQ-style queries

---

## Usage Notes

1. **Session Identity:** If the customer's session ID, phone number, or customer ID is available as a filter from the banking platform's authentication layer, pass it as a `filters` parameter to `retrieve_memory` to scope memory retrieval to this specific customer. Without a filter, the agent retrieves the most semantically relevant memories across all customers, which risks surfacing another customer's account details.

2. **Escalation Thresholds:** The escalation triggers in Task 3 are configurable starting points. The fraud threshold (any `FRAUD_REPORT`), the loan default threshold (3+ overdue payments), and the dispute amount threshold (>USD 500) should be tuned to the bank's operational capacity and risk policy.

3. **Data Privacy:** Account numbers, card numbers, and personal details retrieved from the database must never be echoed verbatim in the customer response. Always use the masked format (e.g. "your account ending in 8844") rather than full numbers. The memory note follows the same convention.

4. **Memory Freshness:** Call `offline_update` periodically to consolidate and deduplicate stored memories. Because `add_memory` is append-only, returning-customer records accumulate across sessions — `offline_update` merges entries flagged with `SUPERSEDES` and removes stale notes, keeping the vector index compact and retrieval relevant. Recommended schedule: nightly, triggered as a **CML Job** in the same project as the chatbot agent. Set the job command to invoke the LightMem MCP server's `offline_update` action and configure it to run at 02:00 local time to avoid overlap with peak support hours.

5. **Multilingual:** The LLM and LightMem embeddings support multilingual input. Customers whose `preferred_language` in the `customers` table is not `EN` (e.g. `ES`, `FR`, `JA`, `DE`) can write in their native language and the agent will respond in the same language.
