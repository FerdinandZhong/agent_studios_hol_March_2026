# Cloudera AI Agent Studio — Workflow Assets

A collection of reusable Agent Studio workflow templates, technical references, and enablement materials for demos, workshops, and customer engagements.

---

## What's in This Repo

| Directory | Contents |
|-----------|----------|
| `templates/` | Importable workflow `.zip` files ready to load into Agent Studio |
| `technical_details/` | Deep-dive architecture and configuration docs for each workflow |
| `instructions/` | Step-by-step guides and business-facing summaries |

---

## Workflow Templates

| Template | Use Case | Description |
|----------|----------|-------------|
| `impala_query_workflow.zip` | Data Analytics | Natural language to SQL — query Impala/CDW data and generate PDF reports |
| `RAG_evaluation_workflow.zip` | AI Quality Assurance | Automated RAG system evaluation with Q&A pair generation and 5-metric scoring |
| `RAG_evaluation_attachment_file.zip` | AI Quality Assurance | Variant of RAG evaluation supporting direct file attachment input |
| `invoice_advanced_parser.zip` | Document Processing | Dual-OCR invoice extraction (PaddleOCR + RolmOCR) with confidence routing |
| `invoice_parser_workflow_with_mem.zip` | Document Processing | Invoice OCR with cross-session memory — query past invoices without re-uploading |
| `fraud_detection_workflow.zip` | Trade Compliance | Trade fraud detection pipeline: OCR → price check → compliance → intelligence → risk report |
| `customer_service_workflow.zip` | Customer Support | Memory-enabled customs call centre chatbot with live shipment and duty lookups |
| `yolo_workflow.zip` | Computer Vision | Item claim verification using YOLO object detection against customs declarations |

### Importing a Template

1. Download the `.zip` file for the workflow you want
2. In Agent Studio, go to **Workflows → Import**
3. Upload the `.zip` — agents, tasks, and tools are pre-configured
4. Set required environment variables and tool endpoints (see technical details below)

---

## Technical Details

Architecture docs, agent definitions, task descriptions, tool parameters, and example outputs for each workflow:

| Document | Workflow |
|----------|----------|
| [`technical_details/impala_query_workflow.md`](technical_details/impala_query_workflow.md) | Natural Language Data Analytics |
| [`technical_details/RAG_EVALUATION_WORKFLOW.md`](technical_details/RAG_EVALUATION_WORKFLOW.md) | RAG Evaluation |
| [`technical_details/invoice_advanced_parser.md`](technical_details/invoice_advanced_parser.md) | Advanced Invoice Parser |
| [`technical_details/invoice_parser_with_memory.md`](technical_details/invoice_parser_with_memory.md) | Invoice Parser with Memory |
| [`technical_details/TRADE_FRAUD_DETECTION_WORKFLOW_SIMPLIFIED.md`](technical_details/TRADE_FRAUD_DETECTION_WORKFLOW_SIMPLIFIED.md) | Trade Fraud Detection |
| [`technical_details/CUSTOMS_CHATBOT_WORKFLOW.md`](technical_details/CUSTOMS_CHATBOT_WORKFLOW.md) | Customs Call Centre Chatbot |
| [`technical_details/YOLO_WORKFLOW.md`](technical_details/YOLO_WORKFLOW.md) | YOLO Item Claim Verification |

---

## Instructions & Enablement Materials

| Document | Audience | Contents |
|----------|----------|----------|
| [`instructions/workflow_summary_business.md`](instructions/workflow_summary_business.md) | Business / Executive | Non-technical problem/solution summaries with ASCII diagrams and business value for all 7 workflows |
| [`instructions/workflow_summary.md`](instructions/workflow_summary.md) | Technical | Hands-on workshop guide |
| [`instructions/query_impala_data_workflow.md`](instructions/query_impala_data_workflow.md) | Technical | Impala query workflow setup guide |
| [`instructions/rag_evaluation_workflow.md`](instructions/rag_evaluation_workflow.md) | Technical | RAG evaluation workflow setup guide |
| [`instructions/invoice_parser_with_memory_workflow.md`](instructions/invoice_parser_with_memory_workflow.md) | Technical | Invoice parser with memory setup guide |

---

## Directory Structure

```
SP_hol/
├── README.md
├── templates/                          # Importable workflow zip files
│   ├── impala_query_workflow.zip
│   ├── RAG_evaluation_workflow.zip
│   ├── RAG_evaluation_attachment_file.zip
│   ├── invoice_advanced_parser.zip
│   ├── invoice_parser_workflow_with_mem.zip
│   ├── fraud_detection_workflow.zip
│   ├── customer_service_workflow.zip
│   └── yolo_workflow.zip
├── technical_details/                  # Architecture and configuration docs
│   ├── impala_query_workflow.md
│   ├── RAG_EVALUATION_WORKFLOW.md
│   ├── invoice_advanced_parser.md
│   ├── invoice_parser_with_memory.md
│   ├── TRADE_FRAUD_DETECTION_WORKFLOW_SIMPLIFIED.md
│   ├── CUSTOMS_CHATBOT_WORKFLOW.md
│   └── YOLO_WORKFLOW.md
└── instructions/                       # Workshop guides and enablement docs
    ├── workflow_summary_business.md
    ├── workflow_summary.md
    ├── query_impala_data_workflow.md
    ├── rag_evaluation_workflow.md
    └── invoice_parser_with_memory_workflow.md
```

---

## Prerequisites

- Access to Cloudera AI (CAI) with Agent Studio enabled
- API keys for required services (varies by workflow — see each workflow's technical details doc)
- For SQL workflows: access to a Cloudera Data Warehouse (CDW) / Impala endpoint
- For RAG workflows: a configured RAG Studio knowledge base
- For memory workflows: OpenAI API key (used by LightMem for embeddings)
