# Qdrant CAI Application

Run Qdrant vector database as a Cloudera AI (CAI) Application for persistent vector storage.

## Why Use This?

MCP servers in Agent Studio run inside bubblewrap sandboxes with filesystem isolation. Local Qdrant storage gets discarded when the sandbox exits. Running Qdrant as a separate CAI Application provides:

- **Persistent storage** - Data survives across sessions
- **Shared access** - Multiple workflows can share the same Qdrant instance
- **No sandbox issues** - Runs outside the MCP sandbox

## Deployment Options

### Option 1: CAI Job (Recommended)

Run `deploy_qdrant.py` as a CAI Job from within an existing project:

```bash
python qdrant_cai_app/deploy_qdrant.py
```

This uses auto-set environment variables (`CDSW_APIV2_KEY`, `CDSW_DOMAIN`, `CDSW_PROJECT_ID`).

### Option 2: GitHub Actions

Trigger the workflow manually from GitHub Actions. Required secrets:

| Secret | Description |
|--------|-------------|
| `CML_HOST` | CML workspace URL |
| `CML_API_KEY` | CML API key |
| `GH_PAT` | GitHub PAT for git sync (optional) |

## Files

| File | Description |
|------|-------------|
| `run_qdrant.py` | Runs Qdrant server (used by CAI Application) |
| `deploy_qdrant.py` | Deploy from CAI Job |
| `deploy_from_github.py` | Deploy from GitHub Actions |

## Configuration

### Qdrant Server (run_qdrant.py)

| Setting | Value |
|---------|-------|
| Host | `127.0.0.1` |
| Port | `8100` |
| Data Path | `/home/cdsw/qdrant_data` |
| Version | v1.13.2 |

### Application Resources

| Resource | Value |
|----------|-------|
| CPU | 2 cores |
| Memory | 8 GB |

## Usage with LightMem MCP

After deployment, configure LightMem to use the remote Qdrant:

```json
{
  "mcpServers": {
    "lightmem": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/FerdinandZhong/LightMem.git@mcp-light", "lightmem-mcp"],
      "env": {
        "OPENAI_API_KEY": "${OPENAI_API_KEY}",
        "QDRANT_URL": "https://your-domain/qdrant-projectid",
        "LIGHTMEM_COLLECTION_NAME": "my_collection"
      }
    }
  }
}
```

## Architecture

```
Agent Studio Workflow
+------------------+
|  MCP Server      |  (bubblewrap sandbox)
|  (LightMem)      |
+--------+---------+
         | HTTP
         v
+------------------+
|  Qdrant CAI App  |
|  (port 8100)     |
+--------+---------+
         |
         v
+------------------+
|  /home/cdsw/     |
|  qdrant_data/    |  (persistent storage)
+------------------+
```
