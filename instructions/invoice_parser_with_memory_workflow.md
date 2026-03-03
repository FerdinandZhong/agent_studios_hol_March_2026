# Lab: Invoice Parser with Memory Workflow

## Overview

Build a conversational agent workflow that demonstrates **cross-session memory** using LightMem MCP. This workflow can:
1. Process invoice images with PaddleOCR and store results in persistent memory
2. Answer questions about previously processed invoices in new conversations

### Key Feature: Cross-Session Memory

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CONVERSATION 1 (Image Upload)                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  User: [Uploads invoice_001.jpg] "Process this invoice"                     │
│                          ↓                                                  │
│  ┌──────────────────────────────────────┐                                   │
│  │  PaddleOCR Tool → LightMem: add_memory                                   │
│  └──────────────────────────────────────┘                                   │
│  Agent: "Invoice processed and stored. Found: vendor, amount, date..."      │
└─────────────────────────────────────────────────────────────────────────────┘

                    ═══════ PAGE REFRESH / NEW SESSION ═══════

┌─────────────────────────────────────────────────────────────────────────────┐
│                    CONVERSATION 2 (Memory Retrieval)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│  User: "What was the total amount on invoice_001?"                          │
│                          ↓                                                  │
│  ┌──────────────────────────────────────┐                                   │
│  │  LightMem: retrieve_memory → Answer                                      │
│  └──────────────────────────────────────┘                                   │
│  Agent: "Based on the stored invoice data, the total amount was $1,234.56"  │
└─────────────────────────────────────────────────────────────────────────────┘
```

The memory persists because it's stored in a **Qdrant vector database** that lives outside the session sandbox.

---

## Prerequisites

- Access to Cloudera AI Agent Studio
- Access to create CAI Jobs and Applications

---

## Part 1: Deploy Qdrant Vector Database

The LightMem MCP server needs a Qdrant vector database for persistent storage. Each participant deploys their own Qdrant instance.

### Step 1.1: Create a CAI Job

1. In your CAI project, go to **Jobs** > **New Job**
2. Configure the job:
   - **Name**: `Deploy Qdrant`
   - **Script**: `qdrant_cai_app/deploy_qdrant.py`
   - **Runtime**: Python 3.11

![Create Job for Qdrant](images/invoice_parser_with_mem_workflow/create_a_job_for_setting_up_qdrant_vectordb.png)

### Step 1.2: Add Environment Variable

Add the `app_suffix` environment variable to create a unique application name:

| Variable | Value |
|----------|-------|
| `app_suffix` | Your unique identifier (e.g., `user01`, `teamA`, your initials) |

![Add app_suffix Environment Variable](images/invoice_parser_with_mem_workflow/add_suffix_env_var_for_qdrant_application.png)

> **Important:** This suffix differentiates your Qdrant app from others. Use a unique value!

### Step 1.3: Run the Job

1. Click **Run** to execute the job
2. Wait for the job to complete
3. The job creates a CAI Application named `Qdrant Vector DB - <your_suffix>`

### Step 1.4: Verify Qdrant Application

Go to **Applications** and verify your Qdrant app is running:

![Qdrant Application Launched](images/invoice_parser_with_mem_workflow/qdrant_application_launched.png)

Note your Qdrant URL - you'll need it later:
```
https://<domain>/qdrant-<suffix>-<project_id>
```

![Running Qdrant Application](images/invoice_parser_with_mem_workflow/running_qdrant_application.png)

---

## Part 2: Import the Workflow Template

### Step 2.1: Import Template

1. In Agent Studio, go to **Agentic Workflows** > **Import Template**
2. Enter path: `/home/cdsw/invoice_parser_workflow_with_mem.zip`
3. Click **Import**

### Step 2.2: Create Workflow from Template

Click the imported template to create a new workflow.

---

## Part 3: Understand the Workflow Architecture

This is a **conversational hierarchical workflow** with a Manager Agent that routes requests to specialized worker agents.

### Workflow Settings

| Setting | Value |
|---------|-------|
| **Process** | Hierarchical |
| **Conversational** | Yes |
| **Use Default Manager** | No (custom manager) |

> **Note:** Since this is conversational, no task definitions are needed. The Manager Agent handles user messages and delegates to workers.

### Agent Structure

| Agent | Role | Tools |
|-------|------|-------|
| **Invoice Assistant Manager** | Routes requests to appropriate worker | - |
| **Invoice OCR & Memory Agent** | Extracts data from images, stores in memory | PaddleOCR, LightMem (`add_memory`) |
| **Invoice Query Agent** | Retrieves invoice data from memory | LightMem (`retrieve_memory`) |

### LightMem MCP Server

The workflow uses the LightMem MCP server for persistent memory:

![LightMem MCP Details](images/invoice_parser_with_mem_workflow/Details_of_lightmem_mcp.png)

**MCP Server Configuration:**
```json
{
  "mcpServers": {
    "lightmem": {
      "command": "uvx",
      "args": ["--refresh", "--from", "git+https://github.com/FerdinandZhong/LightMem.git@mcp-light", "lightmem-mcp"],
      "env": {
        "OPENAI_API_KEY": "${OPENAI_API_KEY}",
        "QDRANT_URL": "${QDRANT_URL}",
        "LIGHTMEM_COLLECTION_NAME": "${LIGHTMEM_COLLECTION_NAME}"
      }
    }
  }
}
```

**Key Functions:**
- `add_memory` - Store user input and assistant reply as a memory
- `retrieve_memory` - Semantic search to find relevant memories
- `get_timestamp` - Get current timestamp for memory metadata

### PaddleOCR Tool

The OCR agent uses PaddleOCR hosted via CAI Model Inference:

![PaddleOCR Tool Details](images/invoice_parser_with_mem_workflow/details_of_paddleOCR.png)

![PaddleOCR Model Endpoint](images/invoice_parser_with_mem_workflow/details_of_model_endpoint_of_paddleocr_hosted_through_CAI_inference.png)

![PaddleOCR Model from Nvidia](images/invoice_parser_with_mem_workflow/paddleOCR_model_weights_provided_by_nvidia.png)

---

## Part 4: Hands-On Experiment - Memory Comparison

This experiment demonstrates the difference between an empty memory store and one with existing data.

### Step 4.1: Configure with Your New Qdrant (Empty Memory)

1. Click **Configure** in the workflow editor
2. Under **Tools and MCPs**, find the LightMem MCP server
3. Set `QDRANT_URL` to your newly created Qdrant application URL:

![Point to New Qdrant](images/invoice_parser_with_mem_workflow/point_agents_to_new_qdrant_vector_db.png)

| Parameter | Value |
|-----------|-------|
| `QDRANT_URL` | `https://<domain>/qdrant-<your_suffix>-<project_id>` |
| `LIGHTMEM_COLLECTION_NAME` | `invoice_memory` |
| `OPENAI_API_KEY` | Your OpenAI API key |

### Step 4.2: Test Query (No Memory)

1. Click **Test** in the workflow editor
2. Ask a question about invoices:
   ```
   What's the highest receipt amount?
   ```
3. Observe the result - **no memories found**:

![No Memory Retrieved](images/invoice_parser_with_mem_workflow/no_mem_can_be_retrieved.png)

The agent cannot answer because your new Qdrant instance has no stored invoice data.

### Step 4.3: Configure with Existing Qdrant (With Memory)

Now switch to a Qdrant instance that already has invoice data stored:

1. Go back to **Configure**
2. Change `QDRANT_URL` to the shared Qdrant URL (provided by instructor):

![Point to Existing Qdrant](images/invoice_parser_with_mem_workflow/point_back_to_the_one_with_mem.png)

| Parameter | Value |
|-----------|-------|
| `QDRANT_URL` | `<instructor_provided_url>` |

### Step 4.4: Test Query (With Memory)

1. Click **Test** again
2. Ask the same question:
   ```
   What's the highest receipt amount?
   ```
3. Observe the result - **memory retrieved and question answered**:

![Memory Retrieved Successfully](images/invoice_parser_with_mem_workflow/mem_retrieved_for_answering_question.png)

The agent now retrieves stored invoice data and provides an accurate answer!

---

## Part 5: Understanding the Agents

### Manager Agent: Invoice Assistant Manager

| Field | Value |
|-------|-------|
| **Name** | `Invoice Assistant Manager` |
| **Role** | `Conversational Invoice Workflow Coordinator` |
| **Backstory** | `You manage an invoice processing system with two specialized agents. You analyze each user message to determine the appropriate action: (1) When the user uploads an image file (check {Attachments}), delegate to the Invoice OCR & Memory Agent to extract and store the data. (2) When the user asks questions about invoices (by name, vendor, amount, date, etc.), delegate to the Invoice Query Agent to retrieve from memory and answer. (3) For general conversation or unclear requests, ask clarifying questions or provide helpful guidance about the system's capabilities.` |
| **Goal** | `Coordinate invoice processing by routing image uploads to the OCR agent for extraction and storage, and routing invoice queries to the Query agent for memory retrieval. Ensure users receive accurate, timely responses about their invoices.` |

### Worker Agent 1: Invoice OCR & Memory Agent

| Field | Value |
|-------|-------|
| **Name** | `Invoice OCR & Memory Agent` |
| **Role** | `Invoice Data Extractor with Memory Storage` |
| **Tools** | `PaddleOCR Tool`, `LightMem MCP (add_memory, get_timestamp)` |
| **Goal** | `Extract invoice data using PaddleOCR, parse the key fields (vendor, invoice number, date, amount, line items), and store it in LightMem memory with the image filename as the identifier. Always use the structured JSON format for storage.` |

### Worker Agent 2: Invoice Query Agent

| Field | Value |
|-------|-------|
| **Name** | `Invoice Query Agent` |
| **Role** | `Invoice Memory Retrieval Specialist` |
| **Tools** | `LightMem MCP (retrieve_memory)`, `Write to Shared PDF` |
| **Goal** | `Retrieve invoice data from LightMem memory based on user queries (invoice name, vendor, amount, etc.) and provide accurate, helpful responses. Parse the structured JSON in retrieved memories to answer specific questions about invoice contents.` |

---

## Key Takeaways

1. **Memory Persistence**: LightMem + Qdrant enables cross-session memory storage
2. **Conversational Workflow**: No task definitions needed - Manager Agent routes requests
3. **Hierarchical Process**: Manager delegates to specialized workers
4. **Vector Database**: Qdrant provides semantic search over stored memories
5. **Isolation via app_suffix**: Each participant can have their own Qdrant instance

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Qdrant job fails | Check CDSW environment variables are available |
| No memories retrieved | Verify QDRANT_URL points to correct instance |
| LightMem MCP fails to start | Check OPENAI_API_KEY is set correctly |
| OCR extraction fails | Verify PaddleOCR endpoint URL and API key |

---

## Next Steps

- Upload invoice images to store new memories in your Qdrant instance
- Query stored invoices by vendor, amount, or date
- Experiment with different LIGHTMEM_COLLECTION_NAME values to separate data
- Explore building similar memory-enabled workflows for other use cases
