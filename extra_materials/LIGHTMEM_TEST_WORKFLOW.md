# LightMem MCP Test Workflow

A simple 3-task workflow to test the LightMem MCP server's memory storage and retrieval capabilities using user input.

## Workflow Overview

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   TASK 1    │───▶│   TASK 2    │───▶│   TASK 3    │
│ Store from  │    │  Retrieve   │    │  Check      │
│ {input}     │    │  by {input} │    │  Status     │
└─────────────┘    └─────────────┘    └─────────────┘
```

**Input Placeholder:** `{input}` - User's question or message provided at workflow runtime

## MCP Server Configuration

```json
{
  "mcpServers": {
    "lightmem": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/FerdinandZhong/LightMem.git[mcp]", "lightmem-mcp"],
      "env": {
        "OPENAI_API_KEY": "${OPENAI_API_KEY}",
        "LIGHTMEM_DATA_PATH": "${LIGHTMEM_DATA_PATH}",
        "LIGHTMEM_COLLECTION_NAME": "${LIGHTMEM_COLLECTION_NAME}"
      }
    }
  }
}
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key for embeddings |
| `LIGHTMEM_DATA_PATH` | **Yes** | Persistent storage path for cross-session memory |
| `LIGHTMEM_COLLECTION_NAME` | No | Qdrant collection name (default: `lightmem_memory`) |

> **CRITICAL for Cross-Session Memory:**
>
> `LIGHTMEM_DATA_PATH` must point to a **shared, persistent location** - NOT a session-specific folder.
>
> **Good:** `/data/shared/lightmem/`, `/home/cdsw/lightmem_data/`
> **Bad:** `workflows/.../session/abc123/lightmem_data` (session-specific = no persistence)

## Available MCP Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `get_timestamp` | Get current timestamp | None |
| `add_memory` | Store a user/assistant conversation pair | `user_input`, `assistant_reply`, `timestamp`, `force_segment`, `force_extract` |
| `retrieve_memory` | Retrieve relevant memories by query | `query`, `limit`, `filters` |
| `offline_update` | Consolidate and update memory entries | `top_k`, `keep_top_n`, `score_threshold` |
| `show_lightmem_instance` | Show LightMem instance status | None |

---

## Task Definitions

### Task 1: Store Memory from User Input

**Description:**
First, use the `get_timestamp` tool to get the current timestamp. Then analyze the user's input provided in `{input}` and generate a helpful, informative response. Finally, use the `add_memory` tool to store this conversation pair with:
- `user_input`: Set to the user's original question/message from `{input}`
- `assistant_reply`: Set to your generated response
- `timestamp`: Set to the timestamp obtained from `get_timestamp`

If the user provides multiple questions or topics in their input, process each one separately and store multiple memories accordingly.

**Expected Output:**
```json
{
  "status": "success",
  "memories_stored": 1,
  "user_question": "<the user's input>",
  "assistant_response": "<your generated response>",
  "timestamp": "<timestamp>"
}
```

**Success Criteria:**
- `get_timestamp` returns a valid timestamp
- `add_memory` call returns status "success"
- User input is accurately captured
- Assistant response is helpful and relevant to the user's question

---

### Task 2: Retrieve Relevant Memories

**Description:**
Use the `retrieve_memory` tool to search for memories relevant to the user's current query in `{input}`. Set the `query` parameter to the user's input text and `limit` to 5 to retrieve the top 5 most relevant memories.

After retrieving memories, analyze the results and provide a response that:
1. Summarizes what relevant memories were found
2. Uses the retrieved context to provide a more informed answer to the user's question
3. Indicates if no relevant memories were found

**Expected Output:**
```json
{
  "status": "success",
  "query": "<user's input>",
  "memories_found": 5,
  "relevant_memories": ["<memory 1>", "<memory 2>", ...],
  "enhanced_response": "<response informed by retrieved memories>"
}
```

**Success Criteria:**
- `retrieve_memory` call returns without errors
- Retrieved memories are relevant to the query
- Response integrates retrieved context appropriately

---

### Task 3: Check System Status

**Description:**
Use the `show_lightmem_instance` tool to verify the LightMem instance is properly configured and healthy. Report the system status to the user.

**Expected Output:**
```json
{
  "status": "success",
  "system_healthy": true,
  "instance_details": "<configuration summary>"
}
```

**Success Criteria:**
- LightMem instance shows valid configuration
- No errors in system status check

---

## Agent Definition

### Memory Test Agent

| Attribute | Value |
|-----------|-------|
| **Name** | Memory Test Agent |
| **Role** | LightMem MCP Server Tester |

**Backstory:**
You are a QA specialist responsible for testing memory storage and retrieval systems. Your task is to systematically store test data, verify retrieval accuracy, and report on system health.

**Goal:**
1. Store diverse test memories using the `add_memory` tool
2. Test retrieval with various queries using `retrieve_memory`
3. Validate system configuration and compile test results

**Tools:** LightMem MCP Server tools (`get_timestamp`, `add_memory`, `retrieve_memory`, `show_lightmem_instance`)

---

---

## Single-Task Workflow (Recommended for Testing)

For a simpler test, create a single task with this description:

```
Analyze the user's input in {input}. First, use the `get_timestamp` tool to get the current time.
Then generate a helpful response to the user's question. Use the `add_memory` tool to store this
conversation with user_input set to the user's question and assistant_reply set to your response.
Finally, confirm the memory was stored successfully.
```

---

## Quick Test Commands

For manual testing outside the workflow:

```bash
# Set required environment variables
export OPENAI_API_KEY="your-key"
export LIGHTMEM_DATA_PATH="/path/to/persistent/storage"  # IMPORTANT: use persistent path!

# Test MCP server locally
uvx --from "git+https://github.com/FerdinandZhong/LightMem.git[mcp]" lightmem-mcp

# Or with MCP Inspector
npx @modelcontextprotocol/inspector uvx --from "git+https://github.com/FerdinandZhong/LightMem.git[mcp]" lightmem-mcp
```

## Notes

1. **First Run**: The first `add_memory` call may take longer as it initializes the Qdrant vector database locally.

2. **Data Persistence**: You **must** set `LIGHTMEM_DATA_PATH` to a persistent, shared location for cross-session memory to work. Without this, each session creates its own isolated storage.

3. **API Usage**: Each `add_memory` call makes API calls to OpenAI for embedding generation.

4. **Collection Isolation**: Use different `LIGHTMEM_COLLECTION_NAME` values to keep data separate between workflows.
