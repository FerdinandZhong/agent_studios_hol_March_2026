# Invoice Parser Advanced - Technical Details

## Overview

Multi-agent CrewAI workflow for **Key Information Extraction (KIE)** from invoices and receipts using dual OCR models with AI-powered reconciliation.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Document Processing Manager                       │
│            (Hierarchical Coordinator - User Consent)                │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────────┐  ┌─────────────────────────────┐
│  Document Extraction        │  │  Document Q&A Analyst       │
│  Specialist                 │  │                             │
│  (agentic_kie_tool)         │  │  (No tools - uses context)  │
└─────────────┬───────────────┘  └─────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Agentic KIE Tool (CrewAI)                      │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐ │
│  │ Paddle Agent    │  │ Rolm Agent      │  │ Master Agent        │ │
│  │ (Text Detection)│→ │ (Vision-Language│→ │ (Reconciliation)    │ │
│  │                 │  │  Understanding) │  │                     │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

## Workflow Settings

| Setting | Value |
|---------|-------|
| **Process** | Hierarchical |
| **Conversational** | Yes |
| **Smart Workflow** | Yes |
| **Planning** | No |

## Agents

### Manager Agent: Document Processing Manager

| Field | Value |
|-------|-------|
| **Role** | Workflow Coordinator and User Interface Manager |
| **Key Behavior** | ALWAYS displays uploaded image back to user for confirmation before processing |
| **Delegation** | Routes to Extraction Specialist (OCR) or Q&A Analyst based on request |

### Worker Agent 1: Document Extraction Specialist

| Field | Value |
|-------|-------|
| **Role** | Invoice and Receipt Information Extraction |
| **Tool** | `agentic_kie_tool` (Retrieval Agent Tool) |
| **Capabilities** | Open-schema discovery, closed-schema extraction, confidence routing |

### Worker Agent 2: Document Q&A Analyst

| Field | Value |
|-------|-------|
| **Role** | Financial Document Interpreter and Question Answering Specialist |
| **Tools** | None (uses extracted data context) |
| **Capabilities** | Calculations, tax rate analysis, line item explanation, currency conversion |

## Core Tool: Agentic KIE Tool

### Dual-OCR Architecture

| Agent | Model | Purpose |
|-------|-------|---------|
| **Paddle Agent** | PaddleOCR | High-precision text detection with bounding boxes and confidence scores |
| **Rolm Agent** | RolmOCR (Vision-Language) | Document layout understanding, context-aware extraction |
| **Master Agent** | Configurable LLM | Reconciles outputs, deduplicates, produces final key-value pairs |

### Extraction Modes

#### Open Schema Mode (Default)
- Dynamic field discovery
- Extracts all meaningful key-value pairs found in document
- Returns `discovered_fields`, `canonical`, and `extras`

#### Closed Schema Mode
- Extracts only specified `target_fields`
- Uses confidence threshold for Paddle candidates
- Falls back to Rolm for unresolved fields

### Confidence-Based Routing

```
For each target field:
  1. Check Paddle candidate confidence
  2. If confidence >= threshold → Accept Paddle value
  3. If confidence < threshold → Use Rolm value (with evidence validation)
  4. If neither available → Mark as unresolved
```

### Evidence Validation

Rolm outputs are validated against source text to prevent hallucination:
- Field name presence check (normalized)
- Scalar value presence check
- Nested value token matching (minimum 3 characters)

## Tool Parameters

### User Parameters (Configuration)

| Parameter | Required | Description |
|-----------|----------|-------------|
| `paddle_url` | Yes | PaddleOCR endpoint URL |
| `rolm_url` | Yes | RolmOCR OpenAI-compatible endpoint |
| `jwt_token` | Yes | Bearer token for OCR APIs |
| `rolm_model` | No | Model name (default: `reducto/RolmOCR`) |
| `llm_model` | No | Master agent LLM (default: `gpt-4.1-mini`) |
| `llm_base_url` | Yes | OpenAI-compatible base URL |
| `llm_api_key` | Yes | API key for Master agent |

### Tool Parameters (Per-Invocation)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `action` | `extract` | Action to perform |
| `image_source` | - | File path or HTTP URL to image |
| `open_schema` | `true` | Enable dynamic discovery |
| `target_fields` | - | Comma-separated fields for closed-schema |
| `paddle_threshold` | `0.80` | Confidence threshold |
| `output_mode` | `deterministic` | `deterministic` or `full` |

## Output Schema

### Deterministic Output (Open Schema)

```json
{
  "mode": "open_schema_pass1",
  "discovered_fields": {
    "<field_name>": {
      "value": "<any>",
      "source": "paddle|rolm|both",
      "confidence": 0.95
    }
  },
  "canonical": {
    "total": {...},
    "subtotal": {...},
    "tax": {...},
    "date": {...},
    "currency": {...}
  },
  "extras": {
    "vendor_name": {...},
    "payment_method": {...}
  },
  "decision_log": {...}
}
```

### Deterministic Output (Closed Schema)

```json
{
  "paddle": {"total": {"value": "150.00", "confidence": 0.95}},
  "rolm": {"tax": "12.50"},
  "final": {"total": "150.00", "tax": "12.50", "date": "2024-01-15"},
  "routing": {
    "accepted_from_paddle": ["total", "date"],
    "from_rolm": ["tax"],
    "unresolved": ["currency"]
  },
  "decision_log": {...}
}
```

## Key Differentiators from Basic Invoice Parser

| Feature | Basic Parser | Advanced Parser |
|---------|--------------|-----------------|
| OCR Models | Single (PaddleOCR) | Dual (PaddleOCR + RolmOCR) |
| Extraction | Tool-based | Multi-agent CrewAI pipeline |
| Field Discovery | Fixed schema | Open + Closed schema modes |
| Confidence Routing | None | Threshold-based with fallback |
| Evidence Validation | None | Rolm output validation against source |
| Q&A Capability | Memory-based | Context-based analysis |
| User Consent | None | Image preview + confirmation required |

## Canonical Fields

The tool recognizes these standard invoice/receipt fields:

| Field | Description |
|-------|-------------|
| `total` | Grand total / Amount due |
| `subtotal` | Pre-tax subtotal |
| `tax` | Tax amount (VAT/GST) |
| `date` | Invoice/Receipt date |
| `currency` | Currency code (USD, EUR, etc.) |
| `items` | Line items indicator |
| `invoice_number` | Document identifier |
| `payment_method` | Payment type |
| `vendor` | Vendor/Merchant name |
