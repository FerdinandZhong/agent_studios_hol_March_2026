# Invoice Parser with Memory - Integration Design

## Overview

Integrate LightMem MCP with the Invoice Parser workflow to enable cross-conversation memory for OCR-extracted invoice data.

## Workflow Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CONVERSATION 1 (Image Upload)                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  User: [Uploads invoice_001.jpg] "Process this invoice"                     │
│                          ↓                                                  │
│  ┌──────────────────────────────────────┐                                   │
│  │  PaddleOCR Tool                      │                                   │
│  │  - Extract text from image           │                                   │
│  │  - Output: structured invoice data   │                                   │
│  └──────────────────────────────────────┘                                   │
│                          ↓                                                  │
│  ┌──────────────────────────────────────┐                                   │
│  │  LightMem MCP: add_memory            │                                   │
│  │  - user_input: "invoice_001.jpg"     │                                   │
│  │  - assistant_reply: <OCR results>    │                                   │
│  └──────────────────────────────────────┘                                   │
│                          ↓                                                  │
│  Agent: "Invoice processed and stored. Found: vendor, amount, date..."      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

                    ═══════ PAGE REFRESH / NEW SESSION ═══════

┌─────────────────────────────────────────────────────────────────────────────┐
│                    CONVERSATION 2 (Memory Retrieval)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  User: "What was the total amount on invoice_001?"                          │
│                          ↓                                                  │
│  ┌──────────────────────────────────────┐                                   │
│  │  LightMem MCP: retrieve_memory       │                                   │
│  │  - query: "invoice_001"              │                                   │
│  │  - Returns: stored OCR data          │                                   │
│  └──────────────────────────────────────┘                                   │
│                          ↓                                                  │
│  Agent: "Based on the stored invoice data, the total amount was $1,234.56"  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Components

### 1. MCP Server Configuration

```json
{
  "mcpServers": {
    "lightmem": {
      "command": "uvx",
      "args": ["--refresh", "--from", "git+https://github.com/FerdinandZhong/LightMem.git@mcp-light", "lightmem-mcp"],
      "env": {
        "OPENAI_API_KEY": "${OPENAI_API_KEY}",
        "LIGHTMEM_DATA_PATH": "${LIGHTMEM_DATA_PATH}",
        "LIGHTMEM_COLLECTION_NAME": "${LIGHTMEM_COLLECTION_NAME}"
      }
    }
  }
}
```

> **IMPORTANT - Cross-Session Memory:**
>
> To enable memory persistence across conversations, `LIGHTMEM_DATA_PATH` must point to a **shared, persistent location** - NOT a session-specific folder.
>
> **Example paths:**
> - `/data/shared/lightmem/invoice_parser/` - shared storage for this workflow
> - `/home/cdsw/lightmem_data/` - user-level persistent storage
>
> **DO NOT use** session-specific paths like:
> - `workflows/.../session/c86905/lightmem_data` (this defeats cross-session memory)

### 2. Agents

#### Manager Agent: Invoice Assistant Manager
| Attribute | Value |
|-----------|-------|
| **Name** | Invoice Assistant Manager |
| **Role** | Conversational Invoice Workflow Coordinator |

**Backstory:**
```
You manage an invoice processing system with two specialized agents. You analyze each user message to determine the appropriate action:

1. When the user uploads an image file (check {Attachments}):
   - Delegate to the Invoice OCR & Memory Agent to extract and store the data

2. When the user asks questions about invoices (by name, vendor, amount, date, etc.):
   - Delegate to the Invoice Query Agent to retrieve from memory and answer

3. For general conversation or unclear requests:
   - Ask clarifying questions or provide helpful guidance about the system's capabilities

Always provide clear, helpful responses based on the delegated agent's output.
```

**Goal:**
```
Coordinate invoice processing by routing image uploads to the OCR agent for extraction and storage, and routing invoice queries to the Query agent for memory retrieval. Ensure users receive accurate, timely responses about their invoices.
```

---

#### Worker Agent 1: Invoice OCR & Memory Agent
| Attribute | Value |
|-----------|-------|
| **Name** | Invoice OCR & Memory Agent |
| **Role** | Invoice Data Extractor with Memory Storage |
| **Tools** | PaddleOCR Tool, LightMem MCP (add_memory, get_timestamp) |

**Backstory:**
```
You specialize in extracting data from invoice images using OCR and storing the results in persistent memory. When a user uploads an image, you extract all relevant information and store it with the image filename as the key identifier for future retrieval.

IMPORTANT - Memory Storage Format:
When storing invoice data using add_memory, you MUST format the data as follows:
- user_input: Set to the image filename (e.g., "invoice_001.jpg")
- assistant_reply: A structured JSON string containing:
  {
    "filename": "<image filename>",
    "extracted_text": "<raw OCR text>",
    "parsed_fields": {
      "vendor": "<vendor name if found>",
      "invoice_number": "<invoice number if found>",
      "date": "<invoice date if found>",
      "total_amount": "<total amount if found>",
      "line_items": [<list of items if found>]
    }
  }

This structured format enables accurate retrieval in future conversations.
```

**Goal:**
```
Extract invoice data using PaddleOCR, parse the key fields (vendor, invoice number, date, amount, line items), and store it in LightMem memory with the image filename as the identifier. Always use the structured JSON format for storage.
```

#### Worker Agent 2: Invoice Query Agent
| Attribute | Value |
|-----------|-------|
| **Name** | Invoice Query Agent |
| **Role** | Invoice Memory Retrieval Specialist |
| **Tools** | LightMem MCP (retrieve_memory), Write to Shared PDF |

**Backstory:**
```
You help users query previously processed invoices from memory. When users ask about an invoice by name or content, you retrieve the stored OCR data and provide accurate answers.

IMPORTANT - Retrieved Memory Format:
Retrieved memories contain structured invoice data in this format:
- The memory text contains: "User: <filename>\nAssistant: <JSON data>"
- The JSON data includes: filename, extracted_text, and parsed_fields
- parsed_fields contains: vendor, invoice_number, date, total_amount, line_items

When answering user questions:
1. Parse the retrieved JSON to extract the specific field they're asking about
2. If they ask about "total" or "amount", look in parsed_fields.total_amount
3. If they ask about "vendor" or "company", look in parsed_fields.vendor
4. For general questions, summarize the relevant parsed_fields
```

**Goal:**
```
Retrieve invoice data from LightMem memory based on user queries (invoice name, vendor, amount, etc.) and provide accurate, helpful responses. Parse the structured JSON in retrieved memories to answer specific questions about invoice contents.
```

### 3. Workflow Settings

| Setting | Value |
|---------|-------|
| **Process** | Hierarchical |
| **Conversational** | Yes |
| **Use Default Manager** | No (custom manager defined above) |
| **Smart Workflow** | Yes |

> **Note:** Since this is a conversational workflow, no task definition is needed. The Manager Agent handles user messages directly and delegates to worker agents as appropriate.

## Setup Steps

### Step 1: Add LightMem MCP to Workflow
1. Open the Invoice Parser workflow in Agent Studio
2. Go to MCP Servers configuration
3. Add the LightMem MCP server with the configuration above

### Step 2: Configure Manager Agent
1. Disable "Use Default Manager"
2. Create a new Manager Agent with the configuration above
3. Set the manager's backstory and goal as specified

### Step 3: Modify Worker Agents
1. **OCR Agent**: Add LightMem MCP tools (`add_memory`, `get_timestamp`) alongside PaddleOCR
2. **Query Agent**: Replace or update to use LightMem MCP (`retrieve_memory`) tool
3. Update backstories and goals as specified above

### Step 4: Test the Flow
1. **Test Upload**: Upload an invoice image, verify OCR extraction and memory storage
2. **Test Retrieval**: Start a new conversation, ask about the invoice by name
3. **Verify**: Confirm the agent retrieves stored data without needing the image again

## Environment Variables Required

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | For LightMem embeddings and OpenAI operations |
| `LIGHTMEM_DATA_PATH` | Yes | **Persistent storage path** for cross-session memory (e.g., `/data/shared/lightmem/invoices/`) |
| `LIGHTMEM_COLLECTION_NAME` | No | Qdrant collection name (default: `lightmem_memory`). Use unique names to separate data between workflows. |
| `PADDLE_OCR_ENDPOINT` | Yes | PaddleOCR service endpoint URL |
| `PADDLE_OCR_API_KEY` | No | API key for PaddleOCR (if authentication required) |

## Key Benefits

1. **No Re-upload Required**: Once processed, invoice data persists across sessions
2. **Quick Retrieval**: Semantic search finds relevant invoices by name or content
3. **Cross-Session Memory**: Data survives page refresh/new conversations
4. **Scalable**: Can store many invoices and query any of them later
