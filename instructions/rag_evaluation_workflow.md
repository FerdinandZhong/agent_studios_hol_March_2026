# Lab: RAG Evaluation Workflow

## Overview

Build an agent workflow to evaluate a RAG (Retrieval-Augmented Generation) application. The workflow performs 5 sequential tasks:

1. **Generate Ground Truth** - Generate Q&A pairs from document content
2. **Verify Quality** - Validate and score the Q&A pairs
3. **Upload Document** - Upload to RAG Studio knowledge base
4. **Query RAG** - Query RAG with validated questions, collect responses
5. **Evaluate Results** - Compare RAG outputs against ground truth

### Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                     RAG EVALUATION SEQUENTIAL WORKFLOW                        │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌────────┐│
│  │  TASK 1  │    │  TASK 2  │    │  TASK 3  │    │  TASK 4  │    │ TASK 5 ││
│  │ Generate │───▶│  Verify  │───▶│  Upload  │───▶│  Query   │───▶│Evaluate││
│  │Ground Trh│    │  Quality │    │ Document │    │   RAG    │    │Results ││
│  └────┬─────┘    └────┬─────┘    └────┬─────┘    └────┬─────┘    └───┬────┘│
│       │               │               │               │              │      │
│       ▼               ▼               ▼               ▼              ▼      │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌────────┐│
│  │ AGENT 1  │    │ AGENT 2  │    │ AGENT 3  │    │ AGENT 4  │    │AGENT 5 ││
│  │  Q&A Pair│    │  Quality │    │ Document │    │RAG Query │    │Evaluat-││
│  │ Generator│    │ Verifier │    │ Uploader │    │Specialist│    │ion     ││
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘    └────────┘│
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

- Access to Cloudera AI Agent Studio
- RAG Studio with a knowledge base already created

---

## Part 1: Explore RAG Studio

Before building the evaluation workflow, explore RAG Studio directly.

### Step 1.1: View Knowledge Base

In RAG Studio, view your existing knowledge base with uploaded documents.

![RAG Studio Knowledge Base](images/RAG_evaluation_workflow/RAG_studio_knowledge_base.png)

### Step 1.2: Query RAG Studio Directly

Test the RAG system by querying it directly with a question.

![Query RAG Studio Directly](images/RAG_evaluation_workflow/Query_RAG_studio_direcly_with_knowledge_base.png)

### Step 1.3: Review Retrieved Resources

Examine the retrieved chunks/resources that RAG uses to generate answers.

![RAG Query Show Resources](images/RAG_evaluation_workflow/RAG_studio_query_show_resources.png)

---

## Part 2: Create the RAG Studio Tool

The workflow uses a custom `rag_studio_tool` to interact with RAG Studio. This tool is already included in the workflow template, but understanding its structure helps with troubleshooting.

### Step 2.1: Tool Overview

The `rag_studio_tool` supports these actions:

| Action | Description |
|--------|-------------|
| `query` | Search the knowledge base with a question |
| `upload_document` | Upload a document to a knowledge base |
| `list_knowledge_bases` | List available knowledge bases |
| `get_sessions` | List all sessions |
| `get_chat_history` | Get chat history with evaluations |


Tool.py

```python
"""
Tool template for calling Paddle OCR HTTP endpoint.

Supports:
- infer (single image)
- infer_batch (multiple images)

Input images can be local file paths or HTTP/HTTPS URLs.
"""

import argparse
import base64
import json
import mimetypes
import os
from typing import Any, Dict, List, Literal, Optional

import requests
from pydantic import BaseModel, Field


class UserParameters(BaseModel):
    """
    Args:
        endpoint_url (str): Paddle OCR endpoint URL.
        api_key (Optional[str]): API key/JWT token for Bearer auth.
        timeout_seconds (int): HTTP timeout in seconds.
    """

    endpoint_url: str = Field(
        description="Paddle OCR endpoint URL, e.g. https://.../paddle-ocr/v1/infer"
    )
    api_key: Optional[str] = Field(
        default=None,
        description="Bearer token value (without 'Bearer ' prefix)",
    )
    timeout_seconds: int = Field(default=60, description="HTTP timeout in seconds")


class ToolParameters(BaseModel):
    action: Literal["infer", "infer_batch"] = Field(
        description="Action to perform: infer (single image) or infer_batch (multiple images)"
    )

    image_source: Optional[str] = Field(
        default=None,
        description="Single image source for infer: local path or HTTP/HTTPS URL",
    )
    image_sources: Optional[List[str]] = Field(
        default=None,
        description="List of image sources for infer_batch",
    )

    output_mode: Literal["raw", "text", "lines"] = Field(
        default="text",
        description=(
            "Output format: raw (full response JSON), text (joined OCR text), "
            "lines (structured lines with confidence)"
        ),
    )


def _guess_mime(source: str) -> str:
    mime_type, _ = mimetypes.guess_type(source)
    return mime_type or "image/png"


def _load_image_bytes(image_source: str) -> bytes:
    if image_source.startswith(("http://", "https://")):
        response = requests.get(image_source, timeout=30)
        response.raise_for_status()
        return response.content

    with open(image_source, "rb") as f:
        return f.read()


def _to_data_url(image_source: str) -> str:
    image_bytes = _load_image_bytes(image_source)
    mime_type = _guess_mime(image_source)
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


def _build_headers(config: UserParameters) -> Dict[str, str]:
    headers: Dict[str, str] = {"Content-Type": "application/json", "accept": "application/json"}
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"
    return headers


def _extract_lines_from_paddle_response(result: Any) -> List[Dict[str, Any]]:
    lines: List[Dict[str, Any]] = []

    def add_line(text: Any, confidence: Any = None):
        text_str = str(text).strip() if text is not None else ""
        if not text_str:
            return
        line: Dict[str, Any] = {"text": text_str}
        if isinstance(confidence, (int, float)):
            line["confidence"] = float(confidence)
        lines.append(line)

    # Current endpoint shape:
    # {"data":[{"text_detections":[{"text_prediction":{"text":"...","confidence":0.99}, ...}]}]}
    if isinstance(result, dict) and isinstance(result.get("data"), list):
        for item in result["data"]:
            if not isinstance(item, dict):
                continue
            text_detections = item.get("text_detections")
            if not isinstance(text_detections, list):
                continue
            for detection in text_detections:
                if not isinstance(detection, dict):
                    continue
                prediction = detection.get("text_prediction", {})
                if isinstance(prediction, dict):
                    add_line(prediction.get("text"), prediction.get("confidence"))
        return lines

    # Fallback shapes.
    if isinstance(result, list):
        for item in result:
            if isinstance(item, dict) and "text" in item:
                add_line(item.get("text"), item.get("confidence"))
            elif isinstance(item, list) and len(item) >= 2:
                candidate = item[1]
                if isinstance(candidate, (list, tuple)) and len(candidate) >= 1:
                    confidence = candidate[1] if len(candidate) > 1 else None
                    add_line(candidate[0], confidence)
        return lines

    if isinstance(result, dict):
        if isinstance(result.get("output"), list):
            for item in result["output"]:
                if isinstance(item, dict) and "text" in item:
                    add_line(item.get("text"), item.get("confidence"))
        elif isinstance(result.get("text"), str):
            add_line(result.get("text"))
        elif isinstance(result.get("result"), str):
            add_line(result.get("result"))

    return lines


def _format_output(result: Any, output_mode: str) -> str:
    if output_mode == "raw":
        return json.dumps(result, indent=2, ensure_ascii=False)

    lines = _extract_lines_from_paddle_response(result)

    if output_mode == "lines":
        return json.dumps({"line_count": len(lines), "lines": lines}, indent=2, ensure_ascii=False)

    # output_mode == "text"
    text = "\n".join(line["text"] for line in lines)
    return text if text else ""


def _call_paddle(config: UserParameters, image_sources: List[str]) -> Any:
    payload = {
        "input": [
            {
                "type": "image_url",
                "url": _to_data_url(source),
            }
            for source in image_sources
        ]
    }
    headers = _build_headers(config)

    response = requests.post(
        config.endpoint_url,
        headers=headers,
        json=payload,
        timeout=config.timeout_seconds,
    )
    response.raise_for_status()
    return response.json()


def run_tool(config: UserParameters, args: ToolParameters) -> str:
    try:
        if args.action == "infer":
            if not args.image_source:
                return "Error: 'image_source' is required for action='infer'."
            if not args.image_source.startswith(("http://", "https://")) and not os.path.exists(args.image_source):
                return f"Error: image file not found: {args.image_source}"

            result = _call_paddle(config, [args.image_source])
            return _format_output(result, args.output_mode)

        if args.action == "infer_batch":
            if not args.image_sources:
                return "Error: 'image_sources' is required for action='infer_batch'."

            for source in args.image_sources:
                if not source.startswith(("http://", "https://")) and not os.path.exists(source):
                    return f"Error: image file not found: {source}"

            result = _call_paddle(config, args.image_sources)
            return _format_output(result, args.output_mode)

        return f"Error: Unsupported action '{args.action}'."

    except requests.exceptions.RequestException as e:
        return f"Paddle OCR request failed: {str(e)}"
    except Exception as e:
        return f"Tool execution failed: {str(e)}"


OUTPUT_KEY = "tool_output"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-params", required=True, help="JSON string for tool configuration")
    parser.add_argument("--tool-params", required=True, help="JSON string for tool arguments")
    cli_args = parser.parse_args()

    user_params_dict = json.loads(cli_args.user_params)
    tool_params_dict = json.loads(cli_args.tool_params)

    config = UserParameters(**user_params_dict)
    params = ToolParameters(**tool_params_dict)

    output = run_tool(config, params)
    print(OUTPUT_KEY, output)


```

### Step 2.2: User Parameters

These parameters are configured per-workflow (you'll fill these in Part 5):

| Parameter | Description | Example |
|-----------|-------------|---------|
| `base_url` | RAG Studio API URL | `https://ragstudio-xxx.cloudera.site` |
| `api_key` | API key for authentication | Bearer token |
| `knowledge_base_name` | Target knowledge base name | `Local Companies` |
| `project_id` | Project ID for session creation | `1` |
| `inference_model` | LLM model for generation | `gpt-4` |
| `response_chunks` | Number of chunks to return | `5` |
| `timeout_seconds` | HTTP timeout | `60` |

### Step 2.3: Tool Parameters (Agent Use)

When agents use the tool, they specify:

| Parameter | Description |
|-----------|-------------|
| `action` | One of: `query`, `upload_document`, `list_knowledge_bases`, `get_sessions`, `get_chat_history` |
| `query` | The question to send (for `query` action) |
| `file_path` | Local file path (for `upload_document` action) |
| `session_id` | Session ID (for `get_chat_history` action) |

### Step 2.4: Tool Code Reference

The tool is built with Python using `requests` and `pydantic`. Key functions:

```python
# requirements.txt
requests>=2.31.0
pydantic>=2.0.0
```

The tool handles:
- Session creation and cleanup for queries
- Streaming response parsing from RAG Studio
- Document upload via multipart form
- Knowledge base discovery by name

---

## Part 3: Import the Workflow Template

### Step 3.1: Import Template

1. In Agent Studio, go to **Agentic Workflows** > **Import Template**
2. Enter path: `/home/cdsw/rag_evaluation_workflow.zip`
3. Click **Import**

![Import Workflow Template](images/RAG_evaluation_workflow/import_workflow_template.png)

### Step 3.2: Create Workflow from Template

Click the imported template to create a new workflow. The template includes 5 agents and 5 tasks.

---

## Part 4: Modify Workflow for Text Input

The imported template uses file upload (`{Attachments}`). Due to browser restrictions, we'll modify it to accept copy-pasted text input (`{document_text}`) instead.

### Why Text Input?

- File upload may be blocked in some environments
- Easier to test with text snippets
- Works with any text content, not just PDFs

### Step 4.1: Update Agent 1 - Q&A Pair Generator

1. Click edit on the **Q&A Pair Generator** agent
2. **Delete** the attached PDF tool (not needed for text input)
3. Update the agent properties using the table below:

![Update Agent 1 for Text Input](images/RAG_evaluation_workflow/update_agent_1_to_have_text_input.png)

![Agent 1 with Tool Deleted](images/RAG_evaluation_workflow/updated_agent_1_with_tool_deleted.png)

#### Agent 1 (Text Input) - Copy/Paste Values

| Field | Value |
|-------|-------|
| **Name** | `QA Pair Generator (Text Input)` |
| **Role** | `Ground Truth Dataset Creator for RAG Evaluation (Text-Based)` |
| **Backstory** | `You are an expert in creating high-quality question-answer pairs for evaluating RAG systems. You have deep experience in analyzing text content, identifying key information, and formulating diverse question types that thoroughly test retrieval and generation capabilities. Unlike your PDF-reading counterpart, you work directly with text content that users copy and paste, making you ideal for situations where file uploads are not available. You understand that effective RAG evaluation requires questions of varying difficulty and types - from simple factual lookups to complex reasoning questions. Your Q&A pairs serve as the gold standard ground truth against which RAG system outputs will be measured.` |
| **Goal** | See below (multi-line) |

**Goal (copy this):**
```
1. Receive and thoroughly analyze the provided text content from {document_text}.
2. Generate 5-10 high-quality question-answer pairs covering: Factual Questions (2-3), Reasoning Questions (2-3), Summarization Questions (1-2), Comparison Questions (1-2).
3. For each Q&A pair, provide: question, answer, type (factual/reasoning/summarization/comparison), source_reference.
4. Output the Q&A pairs in the following JSON format:
{
  "document_name": "User Provided Text",
  "qa_pairs": [
    {
      "id": 1,
      "question": "What is the question text?",
      "answer": "The ground truth answer",
      "type": "factual",
      "source_reference": "Paragraph 3, starting with '...'"
    }
  ]
}
```

---

### Step 4.2: Update Agent 2 - Q&A Quality Verifier

1. Click edit on the **Q&A Quality Verifier** agent
2. Update to validate against `{document_text}` instead of PDF

![Update Agent 2 for Text Input](images/RAG_evaluation_workflow/update_agent_2_to_have_text_input.png)

#### Agent 2 (Text Input) - Copy/Paste Values

| Field | Value |
|-------|-------|
| **Name** | `QA Quality Verifier (Text Input)` |
| **Role** | `Ground Truth Dataset Quality Assurance Specialist (Text-Based)` |
| **Backstory** | `You have extensive experience in data validation and quality assurance within AI and machine learning projects. Over the years, you have developed a keen eye for spotting subtle errors and inconsistencies in large datasets. You approach your work methodically, combining automated checks with thoughtful manual review to guarantee that datasets are reliable and useful for downstream applications. Unlike your PDF-reading counterpart, you work directly with text content that users copy and paste, allowing you to validate Q&A pairs even when file uploads are not available. You understand that the quality of ground truth data directly impacts evaluation accuracy - a flawed Q&A pair will produce misleading evaluation results. Your rigorous validation ensures that only high-quality, unambiguous Q&A pairs proceed to the evaluation pipeline.` |
| **Goal** | See below (multi-line) |

**Goal (copy this):**
```
1. Receive the Q&A pairs generated by the Q&A Pair Generator.
2. Reference the original text content from {document_text} for validation.
3. Validate each Q&A pair for: Answer accuracy, completeness, conciseness; Question clarity and answerability; Question type coverage and diversity; No duplicates, accurate source references.
4. Assign quality score (0-1) to each pair, flag issues.
5. Output validation report in the following JSON format:
{
  "validation_summary": {
    "total_pairs": 10,
    "approved": 8,
    "flagged": 2,
    "overall_quality_score": 0.85,
    "question_type_coverage": {"factual": 3, "reasoning": 3, "summarization": 2, "comparison": 2}
  },
  "validated_pairs": [
    {
      "id": 1,
      "question": "...",
      "answer": "...",
      "type": "factual",
      "source_reference": "Paragraph 3",
      "quality_score": 0.95,
      "status": "approved",
      "issues": []
    }
  ],
  "recommendations": ["Consider revising flagged Q&A pairs before proceeding"]
}
```

---

### Step 4.3: Update Agent 3 - Document Generator & Uploader

1. Click edit on **Agent 3**
2. This agent now generates PDF from text AND uploads it
3. Ensure both `write_to_shared_pdf` and `rag_studio_tool` are attached

![Update Agent 3](images/RAG_evaluation_workflow/update_of_agent_3.png)

![Tool Attached to Agent 3](images/RAG_evaluation_workflow/update_of_tool_attached_to_agent_3.png)

#### Agent 3 (Text Input) - Copy/Paste Values

| Field | Value |
|-------|-------|
| **Name** | `Document Generator and Uploader (Text Input)` |
| **Role** | `PDF Generator and RAG Knowledge Base Manager` |
| **Backstory** | `You are responsible for converting text content into PDF documents and managing them in the RAG Studio knowledge base. Unlike the standard Document Uploader who works with existing files, you handle situations where users provide text content directly through copy-paste. You understand that the text must first be properly formatted as a PDF document before it can be uploaded to the RAG system for indexing. Your expertise ensures that text-based inputs are seamlessly converted and ingested into the knowledge base, enabling RAG evaluation even when file uploads are not available.` |
| **Goal** | See below (multi-line) |
| **Tools** | `write_to_shared_pdf`, `rag_studio_tool` |

**Goal (copy this):**
```
1. Receive the text content from {document_text}.
2. Use write_to_shared_pdf tool with output_file="source_document.pdf" and markdown_content set to the text content.
3. After PDF generation, use rag_studio_tool with action="upload_document" to upload the generated PDF to the configured knowledge base.
4. Verify both operations were successful.
5. Report combined status in the following JSON format:
{
  "pdf_generation": {
    "status": "success",
    "file_path": "/home/cdsw/source_document.pdf",
    "file_name": "source_document.pdf"
  },
  "upload_status": {
    "status": "success",
    "knowledge_base_name": "My Knowledge Base",
    "knowledge_base_id": "kb-123",
    "document_name": "source_document.pdf",
    "message": "Document uploaded successfully",
    "timestamp": "2026-03-03T10:30:00Z"
  }
}
```

---

### Step 4.4: Update Tasks

Update the task descriptions to match the text input workflow:

![Sample Task Update](images/RAG_evaluation_workflow/sample_of_update_task.png)

#### Task 1 (Text Input) - Copy/Paste Values

| Field | Value |
|-------|-------|
| **Description** | `Analyze the document content provided directly as text input {document_text} (copy-pasted by the user). Generate a comprehensive set of question-answer pairs that will serve as the ground truth dataset for RAG evaluation. The generated Q&A pairs must be diverse, covering different question types and difficulty levels to thoroughly test the RAG system's retrieval and generation capabilities. Finally, use the write_to_shared_pdf tool with output_file set to "qa_pairs_report.pdf" and markdown_content containing the formatted Q&A pairs to create a visual report for the user.` |
| **Expected Output** | See below (multi-line) |
| **Assigned Agent** | `QA Pair Generator (Text Input)` |

**Expected Output (copy this):**
```
A JSON object containing 5-10 Q&A pairs with the following structure:
{
  "document_name": "User Provided Text",
  "qa_pairs": [
    {"id": 1, "question": "...", "answer": "...", "type": "factual", "source_reference": "Paragraph 3"}
  ]
}
```

#### Task 2 (Text Input) - Copy/Paste Values

| Field | Value |
|-------|-------|
| **Description** | `Review and validate the Q&A pairs generated in the previous task against the original text content provided as {document_text}. Verify that each answer is factually accurate and grounded in the source text. Assess each pair for accuracy, clarity, completeness, and appropriate difficulty classification. Filter out low-quality pairs and provide quality scores for approved pairs. Finally, use the write_to_shared_pdf tool with output_file set to "qa_verification_report.pdf" and markdown_content containing the validation results, quality scores, and any flagged issues to create a visual report for the user.` |
| **Expected Output** | See below (multi-line) |
| **Assigned Agent** | `QA Quality Verifier (Text Input)` |

**Expected Output (copy this):**
```
A JSON validation report with the following structure:
{
  "validation_summary": {"total_pairs": 10, "approved": 8, "flagged": 2, "overall_quality_score": 0.85, "question_type_coverage": {...}},
  "validated_pairs": [{"id": 1, "question": "...", "answer": "...", "type": "factual", "quality_score": 0.95, "status": "approved", "issues": []}],
  "recommendations": ["..."]
}
```

#### Task 3 (Text Input) - Copy/Paste Values

| Field | Value |
|-------|-------|
| **Description** | `First, use the write_to_shared_pdf tool with output_file set to "source_document.pdf" and markdown_content set to the text content from {document_text} to generate a PDF document from the user's pasted text. Then, use the rag_studio_tool with action "upload_document" and file_path parameter set to the generated PDF path to upload the document to the configured RAG Studio knowledge base. Ensure the document is successfully ingested and ready for retrieval queries.` |
| **Expected Output** | See below (multi-line) |
| **Assigned Agent** | `Document Generator and Uploader (Text Input)` |

**Expected Output (copy this):**
```
A JSON status report with the following structure:
{
  "pdf_generation": {"status": "success", "file_path": "/home/cdsw/source_document.pdf", "file_name": "source_document.pdf"},
  "upload_status": {"status": "success", "knowledge_base_name": "...", "knowledge_base_id": "...", "document_name": "source_document.pdf", "message": "Document uploaded successfully", "timestamp": "..."}
}
```

#### Task 4 - Copy/Paste Values (No changes needed)

| Field | Value |
|-------|-------|
| **Description** | `For each approved question from the validated Q&A pairs, use the rag_studio_tool with action "query" and the query parameter set to the question text. Execute all queries against the RAG Studio knowledge base and collect both the RAG-generated answers and the retrieved source chunks for each query.` |
| **Expected Output** | See below (multi-line) |
| **Assigned Agent** | `RAG Query Specialist` |

**Expected Output (copy this):**
```
A JSON object with the following structure:
{
  "query_results": [
    {"id": 1, "question": "...", "ground_truth_answer": "...", "rag_answer": "...", "retrieved_chunks": ["chunk 1...", "chunk 2..."], "question_type": "factual"}
  ]
}
```

#### Task 5 - Copy/Paste Values (No changes needed)

| Field | Value |
|-------|-------|
| **Description** | `Perform comprehensive evaluation of RAG system performance by comparing RAG outputs against ground truth answers. Apply multiple evaluation metrics covering both retrieval quality (context relevance) and generation quality (faithfulness, answer relevance, semantic similarity, correctness). Generate a detailed evaluation report with per-question scores and overall summary statistics. Finally, use the write_to_shared_pdf tool with output_file set to "rag_evaluation_report.pdf" to create a comprehensive visual report.` |
| **Expected Output** | See below (multi-line) |
| **Assigned Agent** | `RAG Evaluation Analyst` |

**Expected Output (copy this):**
```
A JSON evaluation report with the following structure:
{
  "evaluation_summary": {"total_questions": 10, "avg_context_relevance": 0.85, "avg_faithfulness": 0.90, "avg_answer_relevance": 0.88, "avg_semantic_similarity": 0.82, "avg_correctness": 0.80},
  "detailed_results": [{"id": 1, "question": "...", "question_type": "factual", "scores": {"context_relevance": 0.9, "faithfulness": 1.0, "answer_relevance": 0.85, "semantic_similarity": 0.8, "correctness": 0.9}, "reasoning": "..."}],
  "recommendations": ["..."]
}
```

---

## Part 5: Generate CDP API Key

Before configuring the RAG Studio tool, you need to generate a CDP API key for authentication. This key allows the workflow to securely access RAG Studio.

### Step 5.1: Navigate to User Settings

1. In CDP Management Console, click your username (bottom-left)
2. Select **User Settings**

![Go to User Settings](images/RAG_evaluation_workflow/go_to_user_settings.png)

### Step 5.2: Create API Key

1. In the User Settings page, find the **API Keys** section
2. Click **Create API Key**

![Click Create API Key](images/RAG_evaluation_workflow/click_create_api_key.png)

### Step 5.3: Select Key Audiences

1. In the Create API Key dialog, select **both audiences**:
   - Control Plane API
   - Workload API
2. Click **Create**

![Select Both Audiences](images/RAG_evaluation_workflow/click_both_audiences.png)

> **Note:** Selecting both audiences ensures the key works for all RAG Studio operations.

### Step 5.4: Copy the Generated Key

1. **Important:** Copy the generated API key immediately
2. Store it securely - you won't be able to see it again after closing this dialog
3. You'll use this key as the `api_key` parameter in Part 6

![Copy the Generated Key](images/RAG_evaluation_workflow/copy_the_generated_key.png)

> **Warning:** The API key is only shown once. If you lose it, you'll need to create a new one.

---

## Part 6: Configure RAG Studio Tool Parameters

### Step 6.1: Fill Tool Parameters

1. Click **Configure** in the workflow editor
2. Under **Tools and MCPs**, find `rag_studio_tool`
3. Enter your RAG Studio connection details:

![Fill Tool Parameters](images/RAG_evaluation_workflow/fill_up_parameters_of_tools.png)

| Parameter | Description |
|-----------|-------------|
| **base_url** | Your assigned RAG Studio URL (e.g., `https://ragstudio-xxx.cloudera.site`) |
| **api_key** | Your CDP token |
| **knowledge_base_name** | Name of your knowledge base |
| **project_id** | Project ID (usually `1`) |
| **inference_model** | LLM model name |
| **response_chunks** | Number of chunks (default: `5`) |
| **timeout_seconds** | Timeout (default: `60`) |

---

## Part 7: Test the Workflow

### Step 7.1: Prepare Test Input

Use the sample document below or your own content. Copy and paste into `{document_text}`:

<details>
<summary>Click to expand sample document</summary>

```
Summary of "Artificial Intelligence in the Power Sector"

Authors: Baloko Makala and Tonci Bakovic, International Finance Corporation (IFC)

Overview and Context

The document explores how artificial intelligence (AI) is transforming the global energy sector, with a specific focus on emerging markets.

Emerging markets face acute energy challenges, including:
- Rising demand
- Lack of universal access
- Prevalent efficiency issues such as informal grid connections (power theft) that lead to unbilled power and increased carbon emissions

Currently, around 860 million people globally lack access to electricity, which acts as a fundamental impediment to development, health, and poverty reduction.

Key Applications of AI in the Power Sector

1. Smart Grids and Data Analytics

AI, particularly machine learning, is essential for analyzing the massive amounts of data generated by smart meters, sensors, and Phasor Measurement Units (PMUs) to improve grid reliability and efficiency.

2. Renewable Energy Integration

AI addresses the intermittent nature of renewable sources like solar and wind by predicting weather patterns and energy output, which helps grid operators balance loads and manage energy storage effectively. DeepMind, for instance, uses neural networks trained on weather forecasts to predict wind power output 36 hours in advance.

3. Theft Prevention

In Brazil, the utility company Ampla utilizes AI to identify unusual consumption patterns, anticipate consumer behavior, and effectively target and curb power theft in complex urban areas.

4. Predictive Maintenance and Fault Detection

AI combined with sensors and drones allows companies to monitor equipment continuously, detect faults, and perform preventive maintenance before catastrophic failures occur.

5. Expanding Access in Low-Income Countries

AI-supported business models, such as the pay-as-you-go smart-solar solutions by Azuri Technologies, learn a household's energy needs and adjust power output (like dimming lights or slowing fans) to optimize off-grid power usage in rural Africa.

Challenges and Future Outlook

Knowledge Gap: AI companies often possess strong computer science skills but lack the specialized knowledge required to understand complex power systems, a problem that is particularly acute in emerging markets.

Connectivity Issues: The success of AI and smart meters relies on continuous data transmission, which is severely limited in rural or low-income areas lacking reliable cellular network coverage.

Cybersecurity Risks: The digital transformation of power grids has made them vulnerable to hackers, transforming cyberattacks into threats that can be as damaging as natural disasters.

Model Limitations: AI models often act as "black boxes" whose inner workings are poorly understood by users, posing a security risk. They are also susceptible to inaccurate data and require safeguards when deployed in critical energy systems.
```

</details>

### Step 7.2: Run the Workflow

1. Click **Test** in the workflow editor
2. Paste your document text into `{document_text}`
3. Click **Run**

### Step 7.3: Monitor Progress

Watch the workflow execute through each stage:

![Workflow Progress](images/RAG_evaluation_workflow/workflow_progress_rag_querying.png)

### Step 7.4: Review Results

The final evaluation report includes metrics for each Q&A pair:

![RAG Evaluation Results](images/RAG_evaluation_workflow/result_of_rag_evaluation.png)

---

## Part 8: Understanding Evaluation Metrics

### Retrieval Metric

| Metric | Description | Scale |
|--------|-------------|-------|
| **Context Relevance** | Are retrieved chunks relevant to answering the question? | 0-1 |

- Score 1.0: Retrieved chunks contain all necessary information
- Score 0.5: Retrieved chunks contain partial information
- Score 0.0: Retrieved chunks are irrelevant

### Generation Metrics

| Metric | Description | Scale |
|--------|-------------|-------|
| **Faithfulness** | Is the answer grounded in retrieved context? | 0-1 |
| **Answer Relevance** | Does the answer address the question? | 0-1 |
| **Semantic Similarity** | How similar is RAG answer to ground truth? | 0-1 |
| **Correctness** | Is the answer factually correct? | 0-1 |

### Interpreting Results

| Pattern | Diagnosis |
|---------|-----------|
| High Context Relevance + Low Correctness | Generation issue - retrieval works but LLM struggles |
| Low Context Relevance + Low Correctness | Retrieval issue - wrong chunks being retrieved |
| High all metrics | Good RAG performance |
| Low Faithfulness + High Correctness | Answer is correct but includes info not in context (potential hallucination) |

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| RAG tool connection fails | Verify base_url, api_key, and knowledge_base_name |
| PDF generation fails | Check `write_to_shared_pdf` tool is properly attached to Agent 3 |
| No Q&A pairs generated | Ensure document text is substantial enough (500+ words recommended) |
| Low evaluation scores | Review knowledge base content and chunking strategy |
| "Knowledge base not found" | Run `list_knowledge_bases` action to see available names |

---

## Next Steps

- Test with different document types and domains
- Compare evaluation results across different RAG configurations
- Adjust chunking strategies based on evaluation insights
- Experiment with different inference models
