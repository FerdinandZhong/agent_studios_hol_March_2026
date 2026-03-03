# Lab: RAG Evaluation Workflow

## Overview

Build an agent workflow to evaluate a RAG (Retrieval-Augmented Generation) application. The workflow:
1. Generates Q&A pairs from document content as ground truth
2. Verifies Q&A quality
3. Uploads document to RAG Studio knowledge base
4. Queries RAG and compares responses against ground truth
5. Produces evaluation metrics (context relevance, faithfulness, correctness)

---

## Prerequisites

- Access to Cloudera AI Agent Studio
- RAG Studio with a knowledge base already created

---

## Part 1: Explore RAG Studio

Before building the evaluation workflow, explore RAG Studio directly to understand how it works.

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

## Part 2: Import the Workflow Template

### Step 2.1: Import Template

1. In Agent Studio, go to **Agentic Workflows** > **Import Template**
2. Enter path: `/home/cdsw/rag_evaluation_workflow.zip`
3. Click **Import**

### Step 2.2: Create Workflow from Template

Click the imported template to create a new workflow. The template includes 5 agents and 5 tasks for the full evaluation pipeline.

---

## Part 3: Modify Workflow for Text Input

The imported template uses file upload (`{Attachments}`). Due to browser restrictions, we'll modify it to accept copy-pasted text input (`{document_text}`) instead.

### Step 3.1: Update Agent 1 - Q&A Pair Generator

1. Click edit on the **Q&A Pair Generator** agent
2. Update the agent to work with text input instead of PDF:
   - Remove the PDF tool dependency
   - Update the Goal to reference `{document_text}` instead of PDF file

![Update Agent 1 for Text Input](images/RAG_evaluation_workflow/update_agent_1_to_have_text_input.png)

3. Delete the attached PDF tool since we're using text input:

![Agent 1 with Tool Deleted](images/RAG_evaluation_workflow/updated_agent_1_with_tool_deleted.png)

### Step 3.2: Update Agent 2 - Q&A Quality Verifier

1. Click edit on the **Q&A Quality Verifier** agent
2. Update to validate against `{document_text}` instead of re-reading the PDF

![Update Agent 2 for Text Input](images/RAG_evaluation_workflow/update_agent_2_to_have_text_input.png)

### Step 3.3: Update Agent 3 - Document Generator & Uploader

1. Click edit on **Agent 3**
2. This agent now needs to:
   - Generate a PDF from `{document_text}` using `write_to_shared_pdf` tool
   - Upload the generated PDF to RAG Studio using `rag_studio_tool`

![Update Agent 3](images/RAG_evaluation_workflow/update_of_agent_3.png)

3. Ensure the `rag_studio_tool` is attached with proper configuration:

![Tool Attached to Agent 3](images/RAG_evaluation_workflow/update_of_tool_attached_to_agent_3.png)

### Step 3.4: Update Tasks

Update the task descriptions to match the text input workflow:

![Sample Task Update](images/RAG_evaluation_workflow/sample_of_update_task.png)

| Task | Updated Description |
|------|---------------------|
| **Task 1** | Analyze the document content from `{document_text}` and generate 5-10 Q&A pairs as ground truth |
| **Task 2** | Validate Q&A pairs against `{document_text}` for accuracy and quality |
| **Task 3** | Generate PDF from `{document_text}` using `write_to_shared_pdf`, then upload to RAG Studio |
| **Task 4** | Query RAG Studio with validated questions and collect responses |
| **Task 5** | Evaluate RAG responses against ground truth, generate metrics report |

---

## Part 4: Configure RAG Studio Tool Parameters

### Step 4.1: Fill Tool Parameters

1. Click **Configure** in the workflow editor
2. Under **Tools and MCPs**, find `rag_studio_tool`
3. Enter your RAG Studio connection details:

![Fill Tool Parameters](images/RAG_evaluation_workflow/fill_up_parameters_of_tools.png)

| Parameter | Description |
|-----------|-------------|
| **base_url** | RAG Studio API URL |
| **api_key** | Authentication token |
| **knowledge_base_name** | Target knowledge base name |
| **project_id** | Project ID for sessions |
| **inference_model** | LLM model for generation |

---

## Part 5: Test the Workflow

### Step 5.1: Prepare Test Input

Copy the sample document text (from RAG_EVALUATION_WORKFLOW.md or your own document) into the `{document_text}` input field.

### Step 5.2: Run the Workflow

1. Click **Test** in the workflow editor
2. Paste your document text into `{document_text}`
3. Click **Run**

### Step 5.3: Monitor Progress

Watch the workflow execute through each stage:

![Workflow Progress](images/RAG_evaluation_workflow/workflow_progress_rag_querying.png)

### Step 5.4: Review Results

The final evaluation report includes metrics for each Q&A pair:

![RAG Evaluation Results](images/RAG_evaluation_workflow/result_of_rag_evaluation.png)

**Key Metrics:**
| Metric | Description |
|--------|-------------|
| **Context Relevance** | Are retrieved chunks relevant to the question? |
| **Faithfulness** | Is the answer grounded in retrieved context? |
| **Answer Relevance** | Does the answer address the question? |
| **Semantic Similarity** | How similar is the RAG answer to ground truth? |
| **Correctness** | Is the answer factually correct? |

---

## Interpreting Results

| Pattern | Diagnosis |
|---------|-----------|
| High Context Relevance + Low Correctness | Generation issue - retrieval works but LLM struggles |
| Low Context Relevance + Low Correctness | Retrieval issue - wrong chunks being retrieved |
| High all metrics | Good RAG performance |

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| RAG tool connection fails | Verify base_url, api_key, and knowledge_base_name |
| PDF generation fails | Check `write_to_shared_pdf` tool is properly attached |
| No Q&A pairs generated | Ensure document text is substantial enough |
| Low evaluation scores | Review knowledge base content and chunking strategy |

---

## Next Steps

- Test with different document types
- Compare evaluation results across different RAG configurations
- Adjust chunking strategies based on evaluation insights
- Integrate evaluation workflow into CI/CD pipeline
