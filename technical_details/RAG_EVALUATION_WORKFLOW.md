# RAG Evaluation Workflow - Agent Design

This document describes the sequential task-agent workflow for evaluating RAG (Retrieval-Augmented Generation) applications using CAI's Agent Studio.

## Workflow Overview

The RAG evaluation workflow performs the following 5 sequential tasks:
1. **Generate Ground Truth** - Read an uploaded PDF file and generate question-answer pairs
2. **Verify Quality** - Validate and score the generated Q&A pairs
3. **Upload Document** - Upload the file to an existing RAG Studio knowledge base
4. **Query RAG** - Query the RAG system using the validated questions
5. **Evaluate Results** - Evaluate both retrieval and generation quality

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│                           RAG EVALUATION SEQUENTIAL WORKFLOW                                 │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │  TASK 1  │    │  TASK 2  │    │  TASK 3  │    │  TASK 4  │    │  TASK 5  │              │
│  │ Generate │───▶│  Verify  │───▶│  Upload  │───▶│  Query   │───▶│ Evaluate │              │
│  │Ground Trh│    │  Quality │    │ Document │    │   RAG    │    │ Results  │              │
│  └────┬─────┘    └────┬─────┘    └────┬─────┘    └────┬─────┘    └────┬─────┘              │
│       │               │               │               │               │                     │
│       ▼               ▼               ▼               ▼               ▼                     │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │ AGENT 1  │    │ AGENT 2  │    │ AGENT 3  │    │ AGENT 4  │    │ AGENT 5  │              │
│  │  Q&A Pair│    │  Quality │    │ Document │    │RAG Query │    │Evaluation│              │
│  │ Generator│    │ Verifier │    │ Uploader │    │Specialist│    │ Analyst  │              │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘              │
│                                                                                              │
│  Output:         Output:         Output:         Output:         Output:                    │
│  - 5-10 Q&A      - Validated     - Upload        - RAG responses - Retrieval               │
│    pairs           Q&A pairs       status        - Retrieved       metrics                 │
│  - Source refs   - Quality       - Doc ID          chunks        - Generation              │
│  - Question        scores                                          metrics                 │
│    types         - Issues                                        - Report                  │
│                    flagged                                                                 │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Alternative Path: Text Input (No File Upload)

For users who cannot upload files through the browser, Tasks 1-3 and Agents 1-3 have alternative versions that accept copy-pasted text as input.

**Use these alternatives when:**
- File upload is disabled or blocked
- User prefers to paste document content directly
- Testing with text snippets rather than full documents

**Workflow Input Variable:** `{document_text}` - User pastes the document content here

```
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│                     ALTERNATIVE PATH: TEXT INPUT (Tasks 1-3)                                 │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                              │
│  ┌────────────┐    ┌────────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐          │
│  │  TASK 1-A  │    │  TASK 2-A  │    │ TASK 3-A │    │  TASK 4  │    │  TASK 5  │          │
│  │ Generate   │───▶│  Verify    │───▶│ Generate │───▶│  Query   │───▶│ Evaluate │          │
│  │(Text Input)│    │(Text Input)│    │ & Upload │    │   RAG    │    │ Results  │          │
│  └─────┬──────┘    └─────┬──────┘    └────┬─────┘    └────┬─────┘    └────┬─────┘          │
│        │                 │                │               │               │                 │
│        ▼                 ▼                ▼               ▼               ▼                 │
│  ┌────────────┐    ┌────────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐          │
│  │ AGENT 1-A  │    │ AGENT 2-A  │    │ AGENT 3-A│    │ AGENT 4  │    │ AGENT 5  │          │
│  │  Q&A Pair  │    │  Quality   │    │  Doc Gen │    │RAG Query │    │Evaluation│          │
│  │Gen (Text)  │    │Ver (Text)  │    │& Uploader│    │Specialist│    │ Analyst  │          │
│  └────────────┘    └────────────┘    └──────────┘    └──────────┘    └──────────┘          │
│                                                                                              │
│  Input: {document_text}  (user copy-pastes document content)                                │
│  Task 3-A generates PDF from text input, then uploads to RAG Studio                        │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Task Definitions

### Task 1: Generate Ground Truth

**Description:**
Use the `pdf_tool` with action `readpdf` and pdf parameter set to `{Attachments}` to extract the text content from the uploaded PDF document. After reading the document content, analyze it thoroughly and generate a comprehensive set of question-answer pairs that will serve as the ground truth dataset for RAG evaluation. The generated Q&A pairs must be diverse, covering different question types and difficulty levels to thoroughly test the RAG system's retrieval and generation capabilities. Finally, use the `write_to_shared_pdf` tool with output_file set to `"qa_pairs_report.pdf"` and markdown_content containing the formatted Q&A pairs to create a visual report for the user.

**Expected Output:**
A JSON object containing 5-10 Q&A pairs with the following structure:
- `document_name`: Name of the source document
- `qa_pairs`: Array of Q&A objects, each containing:
  - `id`: Unique identifier
  - `question`: The question text
  - `answer`: The ground truth answer
  - `type`: Question type (factual/reasoning/summarization/comparison)
  - `source_reference`: Location in document where answer is found

**Success Criteria:**
- Minimum 5, maximum 10 Q&A pairs generated
- At least 2 different question types represented
- All answers are verifiable from the source document
- Output is valid JSON format

---

### Task 2: Verify Quality

**Description:**
Use the `pdf_tool` with action `readpdf` and pdf parameter set to `{Attachments}` to read the source document. Then review and validate the Q&A pairs generated in Task 1 against the document content to ensure they meet quality standards for RAG evaluation. Verify that each answer is factually accurate and grounded in the source document. Assess each pair for accuracy, clarity, completeness, and appropriate difficulty classification. Filter out low-quality pairs and provide quality scores for approved pairs. Finally, use the `write_to_shared_pdf` tool with output_file set to `"qa_verification_report.pdf"` and markdown_content containing the validation results, quality scores, and any flagged issues to create a visual report for the user.

**Expected Output:**
A JSON validation report containing:
- `validation_summary`: Overall statistics (total pairs, approved count, flagged count, overall quality score, question type coverage)
- `validated_pairs`: Array of Q&A pairs with added fields:
  - `quality_score`: Score from 0-1
  - `status`: "approved" or "flagged"
  - `issues`: Array of identified problems (empty if approved)
- `recommendations`: Suggestions for improvement if needed

**Success Criteria:**
- All Q&A pairs from Task 1 are evaluated
- Each pair has a quality score assigned
- Approved pairs have quality score >= 0.8
- Flagged pairs have clear issue descriptions
- At least 5 approved pairs available for downstream tasks

---

### Task 1-Alt: Generate Ground Truth (Text Input)

**Description:**
Analyze the document content provided directly as text input `{document_text}` (copy-pasted by the user). Generate a comprehensive set of question-answer pairs that will serve as the ground truth dataset for RAG evaluation. The generated Q&A pairs must be diverse, covering different question types and difficulty levels to thoroughly test the RAG system's retrieval and generation capabilities. Finally, use the `write_to_shared_pdf` tool with output_file set to `"qa_pairs_report.pdf"` and markdown_content containing the formatted Q&A pairs to create a visual report for the user.

**Expected Output:**
A JSON object containing 5-10 Q&A pairs with the following structure:
- `document_name`: "User Provided Text" or extracted title from content
- `qa_pairs`: Array of Q&A objects, each containing:
  - `id`: Unique identifier
  - `question`: The question text
  - `answer`: The ground truth answer
  - `type`: Question type (factual/reasoning/summarization/comparison)
  - `source_reference`: Section or paragraph reference in the text

**Success Criteria:**
- Minimum 5, maximum 10 Q&A pairs generated
- At least 2 different question types represented
- All answers are verifiable from the provided text content
- Output is valid JSON format

---

### Task 2-Alt: Verify Quality (Text Input)

**Description:**
Review and validate the Q&A pairs generated in the previous task against the original text content provided as `{document_text}`. Verify that each answer is factually accurate and grounded in the source text. Assess each pair for accuracy, clarity, completeness, and appropriate difficulty classification. Filter out low-quality pairs and provide quality scores for approved pairs. Finally, use the `write_to_shared_pdf` tool with output_file set to `"qa_verification_report.pdf"` and markdown_content containing the validation results, quality scores, and any flagged issues to create a visual report for the user.

**Expected Output:**
A JSON validation report containing:
- `validation_summary`: Overall statistics (total pairs, approved count, flagged count, overall quality score, question type coverage)
- `validated_pairs`: Array of Q&A pairs with added fields:
  - `quality_score`: Score from 0-1
  - `status`: "approved" or "flagged"
  - `issues`: Array of identified problems (empty if approved)
- `recommendations`: Suggestions for improvement if needed

**Success Criteria:**
- All Q&A pairs from the previous task are evaluated
- Each pair has a quality score assigned
- Approved pairs have quality score >= 0.8
- Flagged pairs have clear issue descriptions
- At least 5 approved pairs available for downstream tasks

---

### Task 3-Alt: Generate PDF and Upload Document (Text Input)

**Description:**
First, use the `write_to_shared_pdf` tool with output_file set to `"source_document.pdf"` and markdown_content set to the text content from `{document_text}` to generate a PDF document from the user's pasted text. Then, use the `rag_studio_tool` with action `upload_document` and file_path parameter set to the generated PDF path to upload the document to the configured RAG Studio knowledge base. Ensure the document is successfully ingested and ready for retrieval queries. This task converts the text input into a searchable document in the RAG system.

**Expected Output:**
A JSON status report containing:
- `pdf_generation`: Object with:
  - `status`: "success" or "failure"
  - `file_path`: Path to the generated PDF
  - `file_name`: "source_document.pdf"
- `upload_status`: Object with:
  - `status`: "success" or "failure"
  - `knowledge_base_name`: Name of the target knowledge base
  - `knowledge_base_id`: ID of the knowledge base
  - `document_name`: Name of the uploaded document
  - `message`: Descriptive status message
  - `timestamp`: Upload completion time

**Success Criteria:**
- PDF successfully generated from text input
- Document upload completes without errors
- Upload confirmation received from RAG Studio API
- Knowledge base is correctly identified

---

### Task 3: Upload Document

**Description:**
Use the `rag_studio_tool` with action `upload_document` and file_path parameter set to `{Attachments}` to upload the source PDF document to the configured RAG Studio knowledge base. Ensure the document is successfully ingested and ready for retrieval queries. This task prepares the RAG system for evaluation by making the document searchable.

**Expected Output:**
A JSON status report containing:
- `status`: "success" or "failure"
- `knowledge_base_name`: Name of the target knowledge base
- `knowledge_base_id`: ID of the knowledge base
- `document_name`: Name of the uploaded document
- `message`: Descriptive status message
- `timestamp`: Upload completion time

**Success Criteria:**
- Document upload completes without errors
- Upload confirmation received from RAG Studio API
- Document name matches the source file
- Knowledge base is correctly identified

---

### Task 4: Query RAG

**Description:**
For each approved question from the validated Q&A pairs, use the `rag_studio_tool` with action `query` and the query parameter set to the question text. Execute all queries against the RAG Studio knowledge base and collect both the RAG-generated answers and the retrieved source chunks for each query. This task gathers the RAG system outputs needed for evaluation comparison.

**Expected Output:**
A JSON object containing query results:
- `query_results`: Array of result objects, each containing:
  - `id`: Matching the Q&A pair ID
  - `question`: The question sent to RAG
  - `ground_truth_answer`: Expected answer from Q&A pairs
  - `rag_answer`: Answer generated by RAG system
  - `retrieved_chunks`: Array of source chunks returned by retrieval
  - `question_type`: Type classification for analysis

**Success Criteria:**
- All approved Q&A pairs are queried
- Each query returns a RAG-generated answer
- Retrieved chunks are captured for each query
- No query timeouts or API errors
- Results maintain traceability to original Q&A pair IDs

---

### Task 5: Evaluate Results

**Description:**
Perform comprehensive evaluation of RAG system performance by comparing RAG outputs against ground truth answers. Apply multiple evaluation metrics covering both retrieval quality (context relevance) and generation quality (faithfulness, answer relevance, semantic similarity, correctness). Generate a detailed evaluation report with per-question scores and overall summary statistics. Finally, use the `write_to_shared_pdf` tool with output_file set to `"rag_evaluation_report.pdf"` and markdown_content containing the complete evaluation results, metrics summary, detailed per-question analysis, and recommendations to create a comprehensive visual report for the user.

**Expected Output:**
A JSON evaluation report containing:
- `evaluation_summary`: Aggregate metrics
  - `total_questions`: Number of questions evaluated
  - `avg_context_relevance`: Average retrieval quality (0-1)
  - `avg_faithfulness`: Average grounding score (0-1)
  - `avg_answer_relevance`: Average relevance score (0-1)
  - `avg_semantic_similarity`: Average similarity to ground truth (0-1)
  - `avg_correctness`: Average factual accuracy (0-1)
- `detailed_results`: Per-question breakdown with all scores and reasoning
- `recommendations`: Actionable insights for RAG improvement

**Success Criteria:**
- All query results from Task 4 are evaluated
- All 5 metrics are computed for each question
- Scores are within valid range (0-1)
- Reasoning is provided for each evaluation
- Summary statistics are correctly calculated
- Recommendations are actionable and specific

---

## Agent Definitions

### Agent 1: Q&A Pair Generator

| Attribute | Value |
|-----------|-------|
| **Name** | QA Pair Generator |
| **Role** | Ground Truth Dataset Creator for RAG Evaluation |

**Backstory:**
You are an expert in creating high-quality question-answer pairs for evaluating RAG systems. You have deep experience in reading documents, identifying key information, and formulating diverse question types that thoroughly test retrieval and generation capabilities. You understand that effective RAG evaluation requires questions of varying difficulty and types - from simple factual lookups to complex reasoning questions. Your Q&A pairs serve as the gold standard ground truth against which RAG system outputs will be measured.

**Goal:**
1. Read and thoroughly analyze the provided PDF document.
2. Generate 5-10 high-quality question-answer pairs that cover:
   - **Factual Questions** (2-3): Direct information retrieval (e.g., "What is the value of X?")
   - **Reasoning Questions** (2-3): Require connecting multiple pieces of information (e.g., "Why did X lead to Y?")
   - **Summarization Questions** (1-2): Require synthesizing information (e.g., "What are the main points about X?")
   - **Comparison Questions** (1-2): Compare different concepts or entities in the document
3. For each Q&A pair, provide:
   - `question`: The question text
   - `answer`: The expected correct answer (ground truth)
   - `type`: Question type (factual/reasoning/summarization/comparison)
   - `source_reference`: Page number or section where the answer can be found
4. Output the Q&A pairs in JSON format for downstream processing.

**Output Format:**
```json
{
  "document_name": "filename.pdf",
  "qa_pairs": [
    {
      "id": 1,
      "question": "...",
      "answer": "...",
      "type": "factual",
      "source_reference": "Page 3, Section 2.1"
    }
  ]
}
```

---

### Agent 2: Q&A Quality Verifier

| Attribute | Value |
|-----------|-------|
| **Name** | QA Quality Verifier |
| **Role** | Ground Truth Dataset Quality Assurance Specialist |

**Backstory:**
You have extensive experience in data validation and quality assurance within AI and machine learning projects. Over the years, you have developed a keen eye for spotting subtle errors and inconsistencies in large datasets. You approach your work methodically, combining automated checks with thoughtful manual review to guarantee that datasets are reliable and useful for downstream applications. You understand that the quality of ground truth data directly impacts evaluation accuracy - a flawed Q&A pair will produce misleading evaluation results. Your rigorous validation ensures that only high-quality, unambiguous Q&A pairs proceed to the evaluation pipeline.

**Goal:**
1. Receive the Q&A pairs generated by the Q&A Pair Generator.
2. Validate each Q&A pair against the following quality criteria:

   **Answer Quality Checks:**
   - Is the answer factually accurate based on the source document?
   - Is the answer complete (not missing key information)?
   - Is the answer concise (not overly verbose)?

   **Question Quality Checks:**
   - Is the question clear and unambiguous?
   - Is the question answerable from the document?
   - Does the question type match its classification (factual/reasoning/summarization/comparison)?

   **Coverage Checks:**
   - Are different question types adequately represented?
   - Do the questions cover different sections/topics of the document?
   - Is there sufficient diversity in difficulty levels?

   **Consistency Checks:**
   - Are there any duplicate or near-duplicate questions?
   - Are the source references accurate?
   - Is the JSON format valid and complete?

3. For each Q&A pair, assign a quality score (0-1) and flag any issues.
4. Output a validation report with:
   - Approved Q&A pairs (quality score >= 0.8)
   - Flagged Q&A pairs with specific issues
   - Overall dataset quality assessment
   - Recommendations for improvement (if needed)

**Output Format:**
```json
{
  "validation_summary": {
    "total_pairs": 10,
    "approved": 8,
    "flagged": 2,
    "overall_quality_score": 0.85,
    "question_type_coverage": {
      "factual": 3,
      "reasoning": 3,
      "summarization": 2,
      "comparison": 2
    }
  },
  "validated_pairs": [
    {
      "id": 1,
      "question": "...",
      "answer": "...",
      "type": "factual",
      "source_reference": "Page 3",
      "quality_score": 0.95,
      "status": "approved",
      "issues": []
    },
    {
      "id": 2,
      "question": "...",
      "answer": "...",
      "type": "reasoning",
      "source_reference": "Page 5",
      "quality_score": 0.65,
      "status": "flagged",
      "issues": ["Answer is incomplete", "Missing key context"]
    }
  ],
  "recommendations": ["Consider revising flagged Q&A pairs before proceeding"]
}
```

---

### Agent 1-Alt: Q&A Pair Generator (Text Input)

| Attribute | Value |
|-----------|-------|
| **Name** | QA Pair Generator (Text Input) |
| **Role** | Ground Truth Dataset Creator for RAG Evaluation (Text-Based) |

**Backstory:**
You are an expert in creating high-quality question-answer pairs for evaluating RAG systems. You have deep experience in analyzing text content, identifying key information, and formulating diverse question types that thoroughly test retrieval and generation capabilities. Unlike your PDF-reading counterpart, you work directly with text content that users copy and paste, making you ideal for situations where file uploads are not available. You understand that effective RAG evaluation requires questions of varying difficulty and types - from simple factual lookups to complex reasoning questions. Your Q&A pairs serve as the gold standard ground truth against which RAG system outputs will be measured.

**Goal:**
1. Receive and thoroughly analyze the provided text content from `{document_text}`.
2. Generate 5-10 high-quality question-answer pairs that cover:
   - **Factual Questions** (2-3): Direct information retrieval (e.g., "What is the value of X?")
   - **Reasoning Questions** (2-3): Require connecting multiple pieces of information (e.g., "Why did X lead to Y?")
   - **Summarization Questions** (1-2): Require synthesizing information (e.g., "What are the main points about X?")
   - **Comparison Questions** (1-2): Compare different concepts or entities in the text
3. For each Q&A pair, provide:
   - `question`: The question text
   - `answer`: The expected correct answer (ground truth)
   - `type`: Question type (factual/reasoning/summarization/comparison)
   - `source_reference`: Section, paragraph, or quote where the answer can be found
4. Output the Q&A pairs in JSON format for downstream processing.

**Output Format:**
```json
{
  "document_name": "User Provided Text",
  "qa_pairs": [
    {
      "id": 1,
      "question": "...",
      "answer": "...",
      "type": "factual",
      "source_reference": "Paragraph 3, starting with '...'"
    }
  ]
}
```

---

### Agent 2-Alt: Q&A Quality Verifier (Text Input)

| Attribute | Value |
|-----------|-------|
| **Name** | QA Quality Verifier (Text Input) |
| **Role** | Ground Truth Dataset Quality Assurance Specialist (Text-Based) |

**Backstory:**
You have extensive experience in data validation and quality assurance within AI and machine learning projects. Over the years, you have developed a keen eye for spotting subtle errors and inconsistencies in large datasets. You approach your work methodically, combining automated checks with thoughtful manual review to guarantee that datasets are reliable and useful for downstream applications. Unlike your PDF-reading counterpart, you work directly with text content that users copy and paste, allowing you to validate Q&A pairs even when file uploads are not available. You understand that the quality of ground truth data directly impacts evaluation accuracy - a flawed Q&A pair will produce misleading evaluation results. Your rigorous validation ensures that only high-quality, unambiguous Q&A pairs proceed to the evaluation pipeline.

**Goal:**
1. Receive the Q&A pairs generated by the Q&A Pair Generator (Text Input).
2. Reference the original text content from `{document_text}` for validation.
3. Validate each Q&A pair against the following quality criteria:

   **Answer Quality Checks:**
   - Is the answer factually accurate based on the provided text?
   - Is the answer complete (not missing key information)?
   - Is the answer concise (not overly verbose)?

   **Question Quality Checks:**
   - Is the question clear and unambiguous?
   - Is the question answerable from the text?
   - Does the question type match its classification (factual/reasoning/summarization/comparison)?

   **Coverage Checks:**
   - Are different question types adequately represented?
   - Do the questions cover different sections/topics of the text?
   - Is there sufficient diversity in difficulty levels?

   **Consistency Checks:**
   - Are there any duplicate or near-duplicate questions?
   - Are the source references accurate and verifiable in the text?
   - Is the JSON format valid and complete?

4. For each Q&A pair, assign a quality score (0-1) and flag any issues.
5. Output a validation report with:
   - Approved Q&A pairs (quality score >= 0.8)
   - Flagged Q&A pairs with specific issues
   - Overall dataset quality assessment
   - Recommendations for improvement (if needed)

**Output Format:**
```json
{
  "validation_summary": {
    "total_pairs": 10,
    "approved": 8,
    "flagged": 2,
    "overall_quality_score": 0.85,
    "question_type_coverage": {
      "factual": 3,
      "reasoning": 3,
      "summarization": 2,
      "comparison": 2
    }
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
  "recommendations": ["..."]
}
```

---

### Agent 3-Alt: Document Generator and Uploader (Text Input)

| Attribute | Value |
|-----------|-------|
| **Name** | Document Generator and Uploader (Text Input) |
| **Role** | PDF Generator and RAG Knowledge Base Manager |

**Backstory:**
You are responsible for converting text content into PDF documents and managing them in the RAG Studio knowledge base. Unlike the standard Document Uploader who works with existing files, you handle situations where users provide text content directly through copy-paste. You understand that the text must first be properly formatted as a PDF document before it can be uploaded to the RAG system for indexing. Your expertise ensures that text-based inputs are seamlessly converted and ingested into the knowledge base, enabling RAG evaluation even when file uploads are not available.

**Goal:**
1. Receive the text content from `{document_text}`.
2. Use the `write_to_shared_pdf` tool with:
   - `output_file`: "source_document.pdf"
   - `markdown_content`: The text content from `{document_text}`
3. After PDF generation, use the `rag_studio_tool` with `action: "upload_document"` to upload the generated PDF to the configured knowledge base.
4. Verify both operations were successful.
5. Report the combined status including:
   - PDF generation success/failure and file path
   - Upload success/failure status
   - Knowledge base name and ID
   - Document name
6. Pass control to the next stage once upload is confirmed.

**Tools:** `write_to_shared_pdf`, `rag_studio_tool` (action: `upload_document`)

**Output Format:**
```json
{
  "pdf_generation": {
    "status": "success",
    "file_path": "/path/to/source_document.pdf",
    "file_name": "source_document.pdf"
  },
  "upload_status": {
    "status": "success",
    "knowledge_base_name": "...",
    "knowledge_base_id": "...",
    "document_name": "source_document.pdf",
    "message": "Document uploaded successfully",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

---

### Agent 3: Document Uploader

| Attribute | Value |
|-----------|-------|
| **Name** | Document Uploader |
| **Role** | RAG Knowledge Base Manager |

**Backstory:**
You are responsible for managing documents in the RAG Studio knowledge base. Your task is to ensure documents are properly uploaded and indexed before evaluation queries can be executed. You understand the importance of verifying successful uploads and ensuring the document is ready for retrieval.

**Goal:**
1. Receive the file path of the document to upload.
2. Use the `rag_studio_tool` with `action: "upload_document"` to upload the file to the configured knowledge base.
3. Verify the upload was successful.
4. Report the upload status including:
   - Success/failure status
   - Knowledge base name and ID
   - Document name
5. Pass control to the next stage once upload is confirmed.

**Tool:** `rag_studio_tool` (action: `upload_document`)

---

### Agent 4: RAG Query Specialist

| Attribute | Value |
|-----------|-------|
| **Name** | RAG Query Specialist |
| **Role** | RAG System Tester and Response Collector |

**Backstory:**
You are an expert in testing RAG systems by executing queries and collecting comprehensive response data. Your role is critical in the evaluation pipeline - you systematically query the RAG system with each ground truth question and meticulously record both the generated answers and the retrieved context chunks. You understand that evaluation requires not just the final answer but also the intermediate retrieval results to assess both retrieval and generation quality.

**Goal:**
1. Receive the list of Q&A pairs from the Ground Truth Generator.
2. For each question in the Q&A pairs:
   - Use `rag_studio_tool` with `action: "query"` to send the question to RAG Studio
   - Collect the RAG-generated answer
   - Collect the retrieved source chunks/documents
3. Compile all results in a structured format:
   - Original question
   - Ground truth answer (from Q&A pairs)
   - RAG-generated answer
   - Retrieved chunks/sources
4. Output the compiled results for evaluation.

**Tool:** `rag_studio_tool` (action: `query`)

**Output Format:**
```json
{
  "query_results": [
    {
      "id": 1,
      "question": "...",
      "ground_truth_answer": "...",
      "rag_answer": "...",
      "retrieved_chunks": ["...", "..."],
      "question_type": "factual"
    }
  ]
}
```

---

### Agent 5: RAG Evaluation Analyst

| Attribute | Value |
|-----------|-------|
| **Name** | RAG Evaluation Analyst |
| **Role** | RAG Quality Assessment Specialist |

**Backstory:**
You are an expert in evaluating RAG system performance using established metrics. You have deep knowledge of both retrieval and generation evaluation methodologies. You understand that RAG evaluation must assess two distinct components: (1) whether the retrieval found relevant context, and (2) whether the generation produced accurate, faithful answers. You use LLM-as-judge techniques combined with semantic analysis to provide comprehensive, objective evaluations.

**Goal:**
Evaluate each query result using the following metrics:

#### Retrieval Metric

1. **Context Relevance** (0-1): How relevant are the retrieved chunks to answering the question?
   - Score 1.0: Retrieved chunks contain all necessary information
   - Score 0.5: Retrieved chunks contain partial information
   - Score 0.0: Retrieved chunks are irrelevant

#### Generation Metrics

2. **Faithfulness** (0-1): Is the generated answer supported by the retrieved context?
   - Score 1.0: Answer is fully grounded in retrieved context
   - Score 0.5: Answer is partially grounded, some claims unsupported
   - Score 0.0: Answer contains hallucinations or contradicts context

3. **Answer Relevance** (0-1): Does the generated answer address the question?
   - Score 1.0: Directly and completely answers the question
   - Score 0.5: Partially answers or includes irrelevant information
   - Score 0.0: Does not answer the question

4. **Semantic Similarity** (0-1): How similar is the RAG answer to the ground truth?
   - Score 1.0: Semantically equivalent
   - Score 0.5: Captures main idea but differs in details
   - Score 0.0: Completely different meaning

5. **Correctness** (0-1): Is the RAG answer factually correct compared to ground truth?
   - Score 1.0: Fully correct
   - Score 0.5: Partially correct
   - Score 0.0: Incorrect

**Output Format:**
```json
{
  "evaluation_summary": {
    "total_questions": 10,
    "avg_context_relevance": 0.85,
    "avg_faithfulness": 0.90,
    "avg_answer_relevance": 0.88,
    "avg_semantic_similarity": 0.82,
    "avg_correctness": 0.80
  },
  "detailed_results": [
    {
      "id": 1,
      "question": "...",
      "question_type": "factual",
      "scores": {
        "context_relevance": 0.9,
        "faithfulness": 1.0,
        "answer_relevance": 0.85,
        "semantic_similarity": 0.8,
        "correctness": 0.9
      },
      "reasoning": "..."
    }
  ],
  "recommendations": ["..."]
}
```

---

## Workflow Summary

### Standard Path (File Upload)

| Stage | Task | Agent | Tool | Input | Output |
|-------|------|-------|------|-------|--------|
| 1 | Generate Ground Truth | Q&A Pair Generator | PDF Reader | PDF file | 5-10 Q&A pairs |
| 2 | Verify Quality | Q&A Quality Verifier | LLM validation | Q&A pairs | Validated Q&A pairs |
| 3 | Upload Document | Document Uploader | `rag_studio_tool` (upload) | File path | Upload confirmation |
| 4 | Query RAG | RAG Query Specialist | `rag_studio_tool` (query) | Validated Q&A pairs | RAG responses + chunks |
| 5 | Evaluate | Evaluation Analyst | LLM-as-judge | Query results | Evaluation report |

### Alternative Path (Text Input - No File Upload)

| Stage | Task | Agent | Tool | Input | Output |
|-------|------|-------|------|-------|--------|
| 1-Alt | Generate Ground Truth (Text) | Q&A Pair Generator (Text Input) | LLM analysis | `{document_text}` | 5-10 Q&A pairs |
| 2-Alt | Verify Quality (Text) | Q&A Quality Verifier (Text Input) | LLM validation | Q&A pairs + `{document_text}` | Validated Q&A pairs |
| 3-Alt | Generate PDF & Upload | Document Generator & Uploader (Text Input) | `write_to_shared_pdf` + `rag_studio_tool` (upload) | `{document_text}` | Generated PDF + Upload confirmation |
| 4 | Query RAG | RAG Query Specialist | `rag_studio_tool` (query) | Validated Q&A pairs | RAG responses + chunks |
| 5 | Evaluate | Evaluation Analyst | LLM-as-judge | Query results | Evaluation report |

---

## Evaluation Metrics Summary

### Retrieval Metrics
| Metric | Description | Scale |
|--------|-------------|-------|
| Context Relevance | How relevant are retrieved chunks to the question | 0-1 |

### Generation Metrics
| Metric | Description | Scale |
|--------|-------------|-------|
| Faithfulness | Is the answer grounded in retrieved context | 0-1 |
| Answer Relevance | Does the answer address the question | 0-1 |
| Semantic Similarity | How similar is RAG answer to ground truth | 0-1 |
| Correctness | Is the answer factually correct | 0-1 |

---

## Required Tools

### 1. RAG Studio Tool (`rag_studio_tool`)

**Actions:**
- `query`: Search the knowledge base with a question
- `upload_document`: Upload a document to a knowledge base
- `list_knowledge_bases`: List available knowledge bases
- `get_sessions`: List all sessions
- `get_chat_history`: Get chat history with evaluations

**User Parameters:**
- `base_url`: RAG Studio API URL
- `api_key`: Authentication token
- `knowledge_base_name`: Target knowledge base name
- `project_id`: Project ID for session creation
- `inference_model`: LLM model for generation
- `timeout_seconds`: HTTP timeout

### 2. PDF Reader (Built-in or Custom)

For reading and extracting text from PDF documents to generate Q&A pairs.

---

## Usage Notes

1. **Knowledge Base Setup**: Ensure the target knowledge base exists in RAG Studio before running the workflow.

2. **Document Indexing Time**: After uploading a document, there may be a delay for chunking and embedding. Consider adding a wait/verification step.

3. **Evaluation Interpretation**:
   - High Context Relevance + Low Correctness = Generation issue
   - Low Context Relevance + Low Correctness = Retrieval issue
   - High all metrics = Good RAG performance

4. **Question Diversity**: The 5-10 Q&A pairs should cover different difficulty levels and question types for comprehensive evaluation.

5. **Choosing Between Standard and Alternative Paths**:
   - **Use Standard Path (Tasks 1, 2, 3)** when:
     - File upload is available in the browser
     - Working with PDF documents
     - Need automatic text extraction from files
   - **Use Alternative Path (Tasks 1-Alt, 2-Alt, 3-Alt)** when:
     - File upload is blocked or disabled
     - User prefers to copy-paste document content
     - Working with text snippets or non-PDF content
     - Testing with smaller text samples
     - The alternative path generates a PDF from text input and uploads it to RAG Studio

6. **Text Input Best Practices** (for Alternative Path):
   - Ensure the pasted text preserves formatting (paragraphs, sections)
   - Include section headers if available for better source references
   - For long documents, consider evaluating in chunks
   - The `{document_text}` input has no strict length limit, but very long texts may affect LLM context limits

---

## Sample Document for Testing (Alternative Path)

The following sample document can be used to test the Alternative Path workflow. Copy and paste this content into the `{document_text}` input variable.

### Sample: Artificial Intelligence in the Power Sector

---

**Summary of "Artificial Intelligence in the Power Sector"**

*Authors: Baloko Makala and Tonci Bakovic, International Finance Corporation (IFC)*

---

#### Overview and Context

The document explores how artificial intelligence (AI) is transforming the global energy sector, with a specific focus on emerging markets.

Emerging markets face acute energy challenges, including:
- Rising demand
- Lack of universal access
- Prevalent efficiency issues such as informal grid connections (power theft) that lead to unbilled power and increased carbon emissions

Currently, around **860 million people globally lack access to electricity**, which acts as a fundamental impediment to development, health, and poverty reduction.

---

#### Key Applications of AI in the Power Sector

**1. Smart Grids and Data Analytics**

AI, particularly machine learning, is essential for analyzing the massive amounts of data generated by smart meters, sensors, and Phasor Measurement Units (PMUs) to improve grid reliability and efficiency.

**2. Renewable Energy Integration**

AI addresses the intermittent nature of renewable sources like solar and wind by predicting weather patterns and energy output, which helps grid operators balance loads and manage energy storage effectively. DeepMind, for instance, uses neural networks trained on weather forecasts to predict wind power output 36 hours in advance.

**3. Theft Prevention**

In Brazil, the utility company Ampla utilizes AI to identify unusual consumption patterns, anticipate consumer behavior, and effectively target and curb power theft in complex urban areas.

**4. Predictive Maintenance and Fault Detection**

AI combined with sensors and drones allows companies to monitor equipment continuously, detect faults, and perform preventive maintenance before catastrophic failures occur.

**5. Expanding Access in Low-Income Countries**

AI-supported business models, such as the pay-as-you-go smart-solar solutions by Azuri Technologies, learn a household's energy needs and adjust power output (like dimming lights or slowing fans) to optimize off-grid power usage in rural Africa.

---

#### Challenges and Future Outlook

**Knowledge Gap**

AI companies often possess strong computer science skills but lack the specialized knowledge required to understand complex power systems, a problem that is particularly acute in emerging markets.

**Connectivity Issues**

The success of AI and smart meters relies on continuous data transmission, which is severely limited in rural or low-income areas lacking reliable cellular network coverage.

**Cybersecurity Risks**

The digital transformation of power grids has made them vulnerable to hackers, transforming cyberattacks into threats that can be as damaging as natural disasters.

**Model Limitations**

AI models often act as "black boxes" whose inner workings are poorly understood by users, posing a security risk. They are also susceptible to inaccurate data and require safeguards when deployed in critical energy systems.

---

*This sample document is provided for testing the RAG Evaluation Workflow using the Alternative Path (Text Input).*
