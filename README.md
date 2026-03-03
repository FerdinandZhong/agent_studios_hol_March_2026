# SP Hands-on Lab - Agent Studio Workshop

This repository contains materials for the Agent Studio hands-on workshop.

## Workshop Overview

Students will learn to set up and configure AI agent workflows in Cloudera's Agent Studio using pre-built templates.

## Templates

The following workflow templates are available in the `templates/` directory:

| Template | Description |
|----------|-------------|
| `RAG_evaluation_workflow.zip` | RAG system evaluation workflow with Q&A pair generation and metrics |
| `query_impala_data_workflow.zip` | Data querying workflow using Impala |
| `invoice_parser_workflow.zip` | Document parsing workflow for invoice processing |

## Setup Instructions

1. Download the template zip file for your exercise
2. Import into Agent Studio via the workflow import feature
3. Configure required tools and connections
4. Follow the step-by-step instructions in the `instructions/` directory

## Directory Structure

```
SP_hol/
├── README.md
├── templates/           # Workflow template zip files
│   ├── RAG_evaluation_workflow.zip
│   ├── query_impala_data_workflow.zip
│   └── invoice_parser_workflow.zip
└── instructions/        # Step-by-step workshop guides
```

## Prerequisites

- Access to Cloudera AI Studio
- API keys for required services (OpenAI, etc.)
- Basic understanding of AI agents and workflows
