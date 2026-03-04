# Lab: Query Impala Data Workflow

## Overview

Build an agent workflow that enables natural language querying of an Impala data warehouse. The workflow uses two agents:
1. **Data Warehouse Query Specialist** - Executes SQL queries against Impala
2. **Document Conversion Specialist** - Generates formatted PDF reports

### Key Feature: Natural Language to SQL

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USER REQUEST                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  User: "Find the top 5 records with the highest max_temperature"            │
│                          ↓                                                  │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  Data Warehouse Query Specialist                                      │   │
│  │  • Analyzes natural language query                                    │   │
│  │  • Uses get_schema to understand table structure                      │   │
│  │  • Generates and executes SQL via execute_query                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                          ↓                                                  │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  Document Conversion Specialist                                       │   │
│  │  • Receives query results                                             │   │
│  │  • Formats data into structured PDF report                            │   │
│  │  • Writes PDF to shared location                                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                          ↓                                                  │
│  Agent: "Here are the top 5 temperature records: [PDF Report Generated]"   │
└─────────────────────────────────────────────────────────────────────────────┘
```

The workflow demonstrates **MCP server integration** for connecting to enterprise data warehouses using the Iceberg MCP Server.

---

## Prerequisites

- Access to Cloudera AI Agent Studio
- Access to CDP Management Console
- A Data Hub with Impala service running

---

## Part 1: Set Up Workload Password

### Step 1.1: Set Workload Password

1. In **CDP Management Console**, click your username (bottom-left) > **Profile**
2. Under **Workload Password**, click **Set Workload Password**
3. Create and save your password

![Set Workload Password](images/Impala_query_workflow/set_workload_password.png)

### Step 1.2: Note Connection Details

| Configuration | Value |
|---------------|-------|
| **Impala Host** | `sp-workshop-master0.min-cldr.u5hb-n231.a2.cloudera.site` |
| **Port** | `443` |
| **User** | Your workload username |
| **Password** | Your workload password |
| **Database** | `iot_data` |

---

## Part 2: Register the Iceberg MCP Server

1. In Agent Studio, go to **Tools Catalog** > **MCP Servers** > **Register**
2. Paste the MCP server configuration from [cloudera/iceberg-mcp-server](https://github.com/cloudera/iceberg-mcp-server):

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
        "IMPALA_HOST": "placeholder",
        "IMPALA_PORT": "443",
        "IMPALA_USER": "placeholder",
        "IMPALA_PASSWORD": "placeholder",
        "IMPALA_DATABASE": "default"
      }
    }
  }
}
```

3. Click **Register** (use placeholder values - actual credentials are entered later)

---

## Part 3: Build the Workflow

### Step 3.1: Import the Workflow Template

1. Go to **Agentic Workflows** > **Import Template**
2. Enter path: `/home/cdsw/query_impala_data_workflow.zip`
3. Click **Import**

![Import Workflow Template](images/Impala_query_workflow/import_impala_workflow_template.png)

### Step 3.2: Create Workflow from Template

Click the imported template to create a new workflow.

![Create Workflow from Template](images/Impala_query_workflow/create_workflow_from_template.png)

---

## Part 4: Understand the Workflow Architecture

This is a **sequential workflow** where agents execute tasks in order, passing results from one agent to the next.

### Workflow Settings

| Setting | Value |
|---------|-------|
| **Process** | Sequential |
| **Conversational** | No |
| **Number of Agents** | 2 |

### Agent Structure

| Agent | Role | Tools |
|-------|------|-------|
| **Data Warehouse Query Specialist** | Translates natural language to SQL and executes queries | Iceberg MCP (`execute_query`, `get_schema`) |
| **Document Conversion Specialist** | Formats query results into professional PDF reports | Write to Shared PDF |

### Iceberg MCP Server

The workflow uses the Iceberg MCP server for Impala connectivity:

**MCP Server Configuration:**
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

**Key Functions:**
- `execute_query` - Execute SQL queries against the Impala data warehouse
- `get_schema` - Retrieve table schema information for query generation

---

## Part 5: Configure the Agents

### Step 5.1: Configure Data Warehouse Query Specialist

Click edit on the **Data Warehouse Query Specialist** agent. Note how AI can generate agent properties (Role, Backstory, Goal) from just the agent name.

![Agent Properties Generated by AI](images/Impala_query_workflow/showing_how_agent_properties_can_be_generated_by_genai.png)

### Step 5.2: Add MCP Server to Agent

1. Click **+ Add MCP Server to Agent**
2. Select **iceberg-mcp-server**
3. Available tools: `execute_query`, `get_schema`
4. Click **Add MCP Server to Agent**

![Add MCP Server to Agent](images/Impala_query_workflow/add_mcp_server_to_agent.png)

### Step 5.3: Add Tool to Document Conversion Specialist

1. Click edit on the **Document Conversion Specialist** agent
2. Click **+ Create or Edit Tools**
3. Search for "write", select **Write to Shared PDF** template
4. Click **Create Tool from Template**

![Add Tool to Second Agent](images/Impala_query_workflow/add_tool_to_second_agent.png)

---

## Part 6: Configure Tasks

Review the pre-configured tasks in the **Tasks** section:

![Task Configuration](images/Impala_query_workflow/task_definition_description_output.png)

| Task | Description | Agent |
|------|-------------|-------|
| Execute SQL Query | Based on the user's `{query}` to execute SQL query with the impala database | Data Warehouse Query Specialist |
| Generate Report | Generate the report based on the query results | Document Conversion Specialist |

---

## Part 7: Configure MCP Server Variables

1. Click **Configure** in the workflow editor
2. Under **Tools and MCPs**, find `iceberg-mcp-server`
3. Enter your actual connection details:

![Configure MCP Variables](images/Impala_query_workflow/fill_up_impala_variables_for_mcp.png)

| Variable | Value |
|----------|-------|
| **IMPALA_HOST** | Your Impala coordinator host |
| **IMPALA_PORT** | `443` |
| **IMPALA_USER** | Your workload username |
| **IMPALA_PASSWORD** | Your workload password |
| **IMPALA_DATABASE** | `iot_data` |

> **Note:** Values are stored in browser local storage, not sent to Agent Studio backend.

---

## Part 8: Test the Workflow

### Step 8.1: Run Test Query

1. Click **Test** in the workflow editor
2. Enter a natural language query:
   ```
   find the top 5 records with the highest max_temperature
   ```
3. Click **Run**

### Step 8.2: Review Results

![Test Results](images/Impala_query_workflow/agent_workflow_test_result.png)

### Step 8.3: Verify with Direct Query (Optional)

Run the equivalent SQL in Hue to verify results:

```sql
SELECT device_id, `location`, event_time, max_temperature, temperature_status
FROM iot_data.temperature_data
ORDER BY max_temperature DESC
LIMIT 5;
```

![Direct Query Results](images/Impala_query_workflow/sql_query_result.png)

---

## Part 9: Deploy the Workflow (Optional)

1. Click **Deploy** in the workflow editor
2. Configure deployment settings
3. The workflow becomes available as an API endpoint

---

## Part 10: Understanding the Agents

### Agent 1: Data Warehouse Query Specialist

| Field | Value |
|-------|-------|
| **Name** | `Data Warehouse Query Specialist` |
| **Role** | `Expert SQL Query Generator and Data Analyst` |
| **Backstory** | `You are a highly skilled data warehouse specialist with expertise in SQL query generation and Impala databases. You translate natural language requests into optimized SQL queries, leveraging schema information to ensure accurate results. You understand data types, table relationships, and best practices for querying large datasets efficiently.` |
| **Goal** | `Analyze the user's natural language query "{query}", use get_schema to understand the available tables and columns, then generate and execute an optimized SQL query using execute_query. Return the results in a clear, structured format.` |
| **Tools** | `Iceberg MCP (execute_query, get_schema)` |

### Agent 2: Document Conversion Specialist

| Field | Value |
|-------|-------|
| **Name** | `Document Conversion Specialist` |
| **Role** | `Professional Report Generator` |
| **Backstory** | `You are an expert in creating professional, well-formatted documents. You take raw data and transform it into clear, readable reports with proper structure, headings, and formatting. You understand how to present data effectively for business users.` |
| **Goal** | `Take the query results from the previous task and generate a professionally formatted PDF report. Include a summary of the data, properly formatted tables, and any relevant insights from the results.` |
| **Tools** | `Write to Shared PDF` |

---

## Key Takeaways

1. **MCP Integration**: The Iceberg MCP server provides seamless connectivity to Impala data warehouses
2. **Natural Language to SQL**: Users can query data without knowing SQL syntax
3. **Sequential Workflow**: Tasks execute in order, passing context between agents
4. **Report Generation**: Automatic PDF generation for professional output
5. **Secure Credentials**: MCP variables stored in browser local storage, not on server

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| MCP connection fails | Verify Impala host URL, workload password, port 443 accessibility |
| Query execution fails | Check table/column names, verify SELECT permissions |
| PDF tool fails | Recreate tool from template, check dependencies |

---

## Next Steps

- Add a third agent to upload reports to a CAI project
- Create a conversational version of this workflow
- Explore other MCP servers for different data sources
