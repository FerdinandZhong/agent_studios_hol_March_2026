# Query Impala Data Workflow - Technical Details

## Overview

Sequential two-agent workflow for **natural language to SQL** conversion against an Impala data warehouse, with automated PDF report generation. Users ask questions in plain English, and the workflow translates them to optimized SQL queries via the Iceberg MCP Server, then formats results into professional reports.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         User Query (Natural Language)                 │
│               "Find top 5 records with highest max_temperature"      │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Agent 1: Data Warehouse Query Specialist                            │
│                                                                      │
│  ┌─────────────────┐    ┌─────────────────┐                         │
│  │  get_schema      │    │  execute_query   │                        │
│  │  (Discover       │ →  │  (Run generated  │                        │
│  │   tables/cols)   │    │   SQL on Impala) │                        │
│  └─────────────────┘    └─────────────────┘                         │
│            ↑                                                         │
│            └── Iceberg MCP Server ──────────────────────┐           │
│                                                          │           │
│  Connection: IMPALA_HOST:443 → CDP Data Hub (Impala)    │           │
└─────────────────────────────┬───────────────────────────────────────┘
                              │ Query results passed via sequential context
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Agent 2: Document Conversion Specialist                             │
│                                                                      │
│  ┌─────────────────────────┐                                        │
│  │  Write to Shared PDF     │                                        │
│  │  (Markdown → PDF)        │                                        │
│  └─────────────────────────┘                                        │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
                    ┌────────────────────┐
                    │  PDF Report        │
                    │  /workspace/*.pdf  │
                    └────────────────────┘
```

## Workflow Settings

| Setting | Value |
|---------|-------|
| **Process** | Sequential |
| **Conversational** | No |
| **Smart Workflow** | Yes |
| **Planning** | No |
| **Number of Agents** | 2 |

## Agents

### Agent 1: Data Warehouse Query Specialist

| Field | Value |
|-------|-------|
| **Role** | Expert SQL Query Generator and Data Analyst |
| **Backstory** | Seasoned data professional with expertise in Impala databases, SQL optimization, and data modeling. Translates complex data requests into actionable insights. |
| **Goal** | Analyze the user's natural language query `{query}`, use `get_schema` to understand available tables and columns, then generate and execute an optimized SQL query using `execute_query`. |
| **Tools** | Iceberg MCP (`execute_query`, `get_schema`) |
| **Temperature** | 0.1 |
| **Allow Delegation** | No |

### Agent 2: Document Conversion Specialist

| Field | Value |
|-------|-------|
| **Role** | Professional Report Generator |
| **Backstory** | Expert in creating professional, well-formatted documents. Transforms raw data into clear, readable reports with proper structure, headings, and formatting. |
| **Goal** | Take query results from the previous task and generate a professionally formatted PDF report with summary, tables, and relevant insights. |
| **Tools** | Write to Shared PDF |
| **Temperature** | 0.1 |
| **Allow Delegation** | No |

## Tasks

| Task | Description | Expected Output | Agent |
|------|-------------|-----------------|-------|
| Execute SQL Query | Based on the user's `{query}` to execute SQL query with the Impala database | The result of execution of the SQL query | Data Warehouse Query Specialist |
| Generate Report | Generate the PDF report based on the query results | The report is generated | Document Conversion Specialist |

**Input Variable:** `{query}` — Natural language question from the user

## MCP Server: Iceberg MCP Server

### Configuration

```json
{
  "mcpServers": {
    "iceberg-mcp-server": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/cloudera/iceberg-mcp-server@main",
        "run-server"
      ],
      "env": {
        "IMPALA_HOST": "${IMPALA_HOST}",
        "IMPALA_PORT": "443",
        "IMPALA_USER": "${IMPALA_USER}",
        "IMPALA_PASSWORD": "${IMPALA_PASSWORD}",
        "IMPALA_DATABASE": "${IMPALA_DATABASE}"
      }
    }
  }
}
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `IMPALA_HOST` | Yes | Impala coordinator hostname (e.g., `sp-workshop-master0.min-cldr.u5hb-n231.a2.cloudera.site`) |
| `IMPALA_PORT` | Yes | Connection port (default: `443` for TLS) |
| `IMPALA_USER` | Yes | CDP workload username |
| `IMPALA_PASSWORD` | Yes | CDP workload password |
| `IMPALA_DATABASE` | Yes | Target database (e.g., `iot_data`) |

### MCP Functions

| Function | Description |
|----------|-------------|
| `get_schema` | Retrieves table and column metadata from the Impala database. The agent uses this to understand available data before generating SQL. |
| `execute_query` | Executes a SQL query against the Impala data warehouse and returns results. |

### Query Flow

```
User: "Find top 5 records with highest max_temperature"
  │
  ├─ 1. Agent calls get_schema → discovers tables, columns, types
  │
  ├─ 2. Agent generates SQL:
  │     SELECT device_id, location, event_time, max_temperature, temperature_status
  │     FROM iot_data.temperature_data
  │     ORDER BY max_temperature DESC
  │     LIMIT 5;
  │
  └─ 3. Agent calls execute_query → returns result rows
```

## Tool: Write to Shared PDF

### Purpose

Converts Markdown content to a styled PDF file, written to the artifact directory (`/workspace`).

### Implementation

| Component | Detail |
|-----------|--------|
| **Library** | `markdown-it-py` for Markdown parsing, `WeasyPrint` for PDF rendering |
| **Input** | `output_file` (filename), `markdown_content` (Markdown string) |
| **Output** | `{"path": "<filename>"}` |
| **User Parameters** | None |

### Tool Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `output_file` | string | PDF filename (e.g., `report.pdf`) — written to `/workspace` |
| `markdown_content` | string | Markdown content including tables, headings, and formatting |

### Key Dependencies

```
markdown-it-py
weasyprint
pandas
```

## Data Flow

```
1. User submits {query} (natural language)
       │
2. Task 1: Data Warehouse Query Specialist
       ├── Calls get_schema via Iceberg MCP
       ├── Generates optimized SQL from natural language + schema
       ├── Calls execute_query via Iceberg MCP
       └── Returns structured query results
       │
3. Task 2: Document Conversion Specialist
       ├── Receives query results from Task 1 context
       ├── Formats results as Markdown (tables, summary, insights)
       ├── Calls Write to Shared PDF tool
       └── Returns PDF file path
       │
4. Output: PDF report at /workspace/report.pdf
```

## Security Notes

- MCP environment variables (credentials) are stored in **browser local storage**, not sent to the Agent Studio backend
- Connection to Impala uses TLS (port 443)
- Workload password must be set in CDP Management Console before use

## Sample Query & Output

**Input:**
```
find the top 5 records with the highest max_temperature
```

**Generated SQL:**
```sql
SELECT device_id, `location`, event_time, max_temperature, temperature_status
FROM iot_data.temperature_data
ORDER BY max_temperature DESC
LIMIT 5;
```

**Output:** PDF report containing a formatted table of results with column headers, data rows, and summary insights.
