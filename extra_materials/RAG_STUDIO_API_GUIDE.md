# RAG Studio API Guide

This document describes how to use the RAG Studio API to query a chatbot with knowledge bases.

## Architecture Overview

RAG Studio consists of two backend services:

```
┌─────────────────────────────────────────────────────────────┐
│                      Java Backend                            │
│  (Spring Boot - Metadata Management)                        │
│  Port: 8080                                                 │
│  Endpoints: /api/v1/rag/*                                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Python Backend                           │
│  (FastAPI - LLM Operations)                                 │
│  Port: 8081                                                 │
│  Endpoints: /llm-service/*                                  │
└─────────────────────────────────────────────────────────────┘
```

## Core Concepts

### Knowledge Base (Data Source)

A knowledge base stores documents that the RAG system uses for retrieval. Documents are:
1. Uploaded to the knowledge base
2. Chunked based on file type (CSV/Excel use row-based chunking, others use sentence splitting)
3. Embedded and stored in a vector database (Qdrant or ChromaDB)

### Session

A session represents a chat conversation linked to one or more knowledge bases. It contains:
- `dataSourceIds` - List of knowledge base IDs to query
- `inferenceModel` - The LLM model for generating responses
- `rerankModel` - Optional model for reranking retrieved chunks
- `responseChunks` - Number of chunks to retrieve (top_k)
- `queryConfiguration` - Advanced settings (HyDE, summary filter, tool calling)

## API Endpoints

### Knowledge Base Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/rag/dataSources` | GET | List all knowledge bases |
| `/api/v1/rag/dataSources` | POST | Create a new knowledge base |
| `/api/v1/rag/dataSources/{id}` | GET | Get knowledge base details |
| `/api/v1/rag/dataSources/{id}` | DELETE | Delete a knowledge base |
| `/api/v1/rag/dataSources/{id}/files` | POST | Upload a file |
| `/api/v1/rag/dataSources/{id}/files` | GET | List all files |
| `/api/v1/rag/dataSources/{id}/files/{documentId}` | DELETE | Delete a file |
| `/api/v1/rag/dataSources/{id}/files/{documentId}/download` | GET | Download a file |

### Session Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/rag/sessions` | GET | List all sessions |
| `/api/v1/rag/sessions` | POST | Create a new session |
| `/api/v1/rag/sessions/{id}` | GET | Get session details |
| `/api/v1/rag/sessions/{id}` | POST | Update session |
| `/api/v1/rag/sessions/{id}` | DELETE | Delete session |

### Chat Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/llm-service/sessions/{id}/stream-completion` | POST | Query with streaming response |
| `/llm-service/sessions/{id}/chat` | POST | Query (deprecated) |
| `/llm-service/sessions/{id}/chat-history` | GET | Get chat history |
| `/llm-service/sessions/{id}/chat-history` | DELETE | Clear chat history |
| `/llm-service/sessions/suggest-questions` | POST | Get suggested questions |

## Usage Examples

### 1. Create a Knowledge Base

```bash
curl -X POST "http://localhost:8080/api/v1/rag/dataSources" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-knowledge-base",
    "embeddingModel": "amazon.titan-embed-text-v2",
    "chunkSize": 512,
    "chunkOverlapPercent": 10
  }'
```

**Response:**
```json
{
  "id": 1,
  "name": "my-knowledge-base",
  "embeddingModel": "amazon.titan-embed-text-v2",
  "chunkSize": 512,
  "chunkOverlapPercent": 10,
  "documentCount": 0
}
```

### 2. Upload Files

```bash
curl -X POST "http://localhost:8080/api/v1/rag/dataSources/1/files" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@my-data.csv"
```

### 3. Create a Chat Session

```bash
curl -X POST "http://localhost:8080/api/v1/rag/sessions" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-chat-session",
    "dataSourceIds": [1],
    "projectId": 1,
    "inferenceModel": "anthropic.claude-3-sonnet",
    "responseChunks": 5,
    "queryConfiguration": {
      "enableHyde": false,
      "enableSummaryFilter": true,
      "enableToolCalling": false
    }
  }'
```

**Response:**
```json
{
  "id": 1,
  "name": "my-chat-session",
  "dataSourceIds": [1],
  "projectId": 1,
  "inferenceModel": "anthropic.claude-3-sonnet",
  "responseChunks": 5
}
```

### 4. Query the Chatbot (Streaming)

```bash
curl -X POST "http://localhost:8081/llm-service/sessions/1/stream-completion" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What information is in the knowledge base?"
  }'
```

**Response (Server-Sent Events):**
```
data: {"event": {"type": "thinking", "name": "thinking", "timestamp": 1234567890}}
data: {"event": {"type": "done", "name": "agent_done", "timestamp": 1234567890}}
data: {"text": "Based on the documents"}
data: {"text": " in your knowledge base..."}
data: {"event": {"type": "done", "name": "chat_done", "timestamp": 1234567890}}
data: {"response_id": "uuid-here"}
```

### 5. Get Chat History

```bash
curl -X GET "http://localhost:8081/llm-service/sessions/1/chat-history"
```

**Response:**
```json
{
  "data": [
    {
      "id": "uuid",
      "session_id": 1,
      "rag_message": {
        "user": "What information is in the knowledge base?",
        "assistant": "Based on the documents..."
      },
      "source_nodes": [...],
      "evaluations": [
        {"name": "relevance", "value": 0.85},
        {"name": "faithfulness", "value": 0.92}
      ],
      "timestamp": 1234567890
    }
  ]
}
```

## Chunking Strategies

RAG Studio uses different chunking strategies based on file type:

### Tabular Data (CSV, Excel)

- **Each row is treated as a single chunk**
- **Format:** Key-value JSON where keys are column headers
- **Best practices:**
  - Use meaningful column headers
  - Place descriptive content in early columns
  - Keep headers consistent across files

**Example:**
```csv
Description,Status,Priority
Fix login bug,Open,High
```

Becomes:
```json
{"Description": "Fix login bug", "Status": "Open", "Priority": "High"}
```

### Text Documents (PDF, DOCX, TXT, MD)

- Uses LlamaIndex's `SentenceSplitter`
- Configurable `chunk_size` (default: 512 tokens)
- Configurable `chunk_overlap` percentage

### Presentations (PPTX)

- One slide per document/chunk

## Query Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `enableHyde` | false | Use Hypothetical Document Embeddings for better retrieval |
| `enableSummaryFilter` | true | Pre-filter documents using summaries |
| `enableToolCalling` | false | Enable agentic tool calling |
| `disableStreaming` | false | Return complete response instead of streaming |
| `responseChunks` | 5 | Number of chunks to retrieve (top_k) |

## Important Notes

### RAG Limitations for Analytical Queries

RAG works best for **descriptive and lookup queries**. It may not return accurate results for **aggregation queries** that require scanning all data:

| Works Well | Doesn't Work Well |
|------------|-------------------|
| "What happened when sensor X failed?" | "What's the highest temperature?" |
| "Describe the readings from device Y" | "How many sensors reported errors?" |
| "What is the status of sensor Z?" | "What's the average humidity?" |

For analytical queries (MAX, MIN, AVG, COUNT, SUM), consider using direct database queries or SQL-based analytics tools.

### Authentication

Most endpoints require authentication via:
- `remote-user` header for user identification
- `Authorization: Bearer <token>` for API access

## Error Handling

Common HTTP status codes:
- `200` - Success
- `400` - Bad request (invalid parameters)
- `401` - Unauthorized
- `404` - Resource not found
- `500` - Internal server error

## Related Files

- Session API: `llm-service/app/routers/index/sessions/__init__.py`
- Chat Service: `llm-service/app/services/chat/chat.py`
- Chunking (CSV): `llm-service/app/ai/indexing/readers/csv.py`
- Chunking (Excel): `llm-service/app/ai/indexing/readers/excel.py`
- Java Session Controller: `backend/src/main/java/com/cloudera/cai/rag/sessions/SessionController.java`
