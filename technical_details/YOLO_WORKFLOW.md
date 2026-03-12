# Customs YOLO Agent Workflow — Technical Details

This document describes the sequential 4-agent workflow for image-based item detection and claim verification using a YOLO object detection API in CAI Agent Studio.

## Workflow Overview

The workflow performs 4 sequential tasks:
1. **Submission Checker** — Validate the claim JSON and uploaded image attachment
2. **YOLO Detector** — Run the YOLO API on the uploaded image and capture detection results
3. **Claim Comparison Analyst** — Compare detected labels against the submitted claim
4. **Final Report Generator** — Assemble the case record and produce a PDF investigation report

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                     CUSTOMS YOLO AGENT WORKFLOW                              │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Inputs: {claim_json}  +  {Attachments} (image file)                        │
│                  │                                                           │
│  ┌───────────┐   ┌───────────┐   ┌───────────┐   ┌───────────┐             │
│  │  TASK 1   │   │  TASK 2   │   │  TASK 3   │   │  TASK 4   │             │
│  │Submission │──▶│  YOLO     │──▶│  Claim    │──▶│  Final    │             │
│  │ Checker   │   │ Detector  │   │Comparison │   │  Report   │             │
│  └─────┬─────┘   └─────┬─────┘   └─────┬─────┘   └─────┬─────┘             │
│        │               │               │               │                   │
│        ▼               ▼               ▼               ▼                   │
│  ┌───────────┐   ┌───────────┐   ┌───────────┐   ┌───────────┐             │
│  │ AGENT 1   │   │ AGENT 2   │   │ AGENT 3   │   │ AGENT 4   │             │
│  │Submission │   │  YOLO     │   │Comparison │   │  Report   │             │
│  │ Validator │   │ Operator  │   │ Analyst   │   │ Generator │             │
│  └───────────┘   └───────────┘   └───────────┘   └───────────┘             │
│                                                                              │
│  Output:         Output:         Output:          Output:                   │
│  - item_id       - detection     - decision       - case_record JSON        │
│  - item_name       status          (match /       - PDF report              │
│  - attachment    - labels +         mismatch /                              │
│    path            confidence       uncertain /                             │
│  - pass/fail       scores           validation_                             │
│                  - bbox data        failed)                                 │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Workflow Settings

| Setting | Value |
|---------|-------|
| **Process** | Sequential |
| **Conversational** | No |
| **Smart Workflow** | Yes |
| **Planning** | No |

---

## Task Definitions

### Task 1: Submission Validation

**Description:**
Validate and standardize workflow inputs. Parse `{claim_json}`, extract `item_id` and `item_name`, validate `item_name` against the allowed category list, inspect uploaded artifact files provided via `{Attachments}`, select the image attachment to use for the case, and verify that the selected attachment filename (excluding extension) matches `item_id`. Return a clean structured payload for downstream detection. If any validation step fails, return `status = "fail"` with all issues listed.

**Validation Rules:**
- `claim_json` must be present and parseable as JSON
- `item_id` must be present and non-empty
- `item_name` must exactly match one of the 13 allowed categories (see list below)
- At least one valid image attachment must be present
- The attachment filename (without extension) must match `item_id`

**Allowed `item_name` Categories:**
`blade`, `Cans`, `CartonDrinks`, `dagger`, `GlassBottle`, `knife`, `PlasticBottle`, `scissors`, `SprayCans`, `SwissArmyKnife`, `Tin`, `VacuumCup`, `none`

**Expected Output:**
```json
{
  "item_id": "TEST001",
  "item_name": "VacuumCup",
  "selected_attachment": "TEST001.jpg",
  "source": "attachment",
  "status": "pass",
  "issues": []
}
```

**Success Criteria:**
- `claim_json` parsed successfully
- `item_name` validated against allowed list
- Attachment present with filename matching `item_id`
- Output is valid JSON with no markdown fences

---

### Task 2: YOLO Detection

**Description:**
Use the `YOLOapi` tool on the resolved image attachment selected in Task 1. Call the YOLO detection endpoint, capture the model output, and normalize it into a consistent schema including detected labels, confidence scores, and bounding box data. Clearly distinguish between: successful detection with objects found, successful detection with no objects, and tool failure.

**Expected Output:**
```json
{
  "detection_result": {
    "status": "success",
    "model": "yolo-model-name",
    "detections": [
      {
        "label": "VacuumCup",
        "confidence": 0.94,
        "bbox": [10, 20, 200, 180]
      }
    ]
  }
}
```

**Success Criteria:**
- `YOLOapi` tool called with the image attachment path from Task 1
- Detection status clearly indicated (`success` / `no_detections` / `failure`)
- Detected labels and confidence scores captured
- No business-level decisions made — detector output only

---

### Task 3: Claim and Detection Comparison

**Description:**
Compare the structured claim from Task 1 against the YOLO detection result from Task 2.

**Comparison Logic:**
- If Task 1 returned `status = "fail"` → skip comparison, return `decision = "validation_failed"`
- If `claimed_item = "none"` and detections are empty → `decision = "match"`
- If `claimed_item = "none"` and detections are not empty → `decision = "mismatch"`
- Otherwise compare claimed `item_name` against detected labels (case-insensitive matching acceptable)

**Decision Values:**

| Decision | Meaning |
|----------|---------|
| `match` | Detected item is consistent with the submitted claim |
| `mismatch` | Detected item contradicts the submitted claim |
| `uncertain` | Ambiguous or low-confidence result requiring review |
| `validation_failed` | Task 1 validation failed; comparison not performed |

**Expected Output:**
```json
{
  "item_id": "TEST001",
  "claimed_item": "VacuumCup",
  "detected_item": "VacuumCup",
  "decision": "match",
  "reasoning": "The detected item matches the submitted claim."
}
```

**Success Criteria:**
- Comparison skipped if validation failed in Task 1
- Special `none` rule applied correctly
- Output uses only the four allowed decision values
- Reasoning field is populated

---

### Task 4: Final Report Generation

**Description:**
Aggregate all outputs from Tasks 1–3 into a final structured case record. Always create a markdown report and call `write_to_shared_pdf` to produce a PDF — this tool **must be called on every run without exception**, including validation failure cases and `none` item cases.

**PDF Filename Convention:** `image_claim_verification_report_<item_id>.pdf`

**Case Status Mapping:**

| Decision | Case Status | Next Action |
|----------|-------------|-------------|
| `match` | `approved` | `no_followup_needed` |
| `mismatch` | `flagged_for_review` | `correct_claim_and_resubmit` |
| `uncertain` | `flagged_for_review` | Requires manual review |
| `validation_failed` | `flagged_for_review` | `correct_claim_and_resubmit` |
| Detection error | `detection_failed` | Retry or manual inspection |

**Expected Output:**
```json
{
  "case_record": {
    "item_id": "TEST001",
    "item_name": "VacuumCup",
    "decision": "match",
    "case_status": "approved",
    "next_action": "no_followup_needed",
    "summary": "The submitted claim is consistent with the detection result."
  },
  "report_pdf": {
    "path": "image_claim_verification_report_TEST001.pdf"
  }
}
```

**Success Criteria:**
- `write_to_shared_pdf` called before returning JSON
- PDF filename includes the current `item_id`
- Report title is always in **bold** (e.g., `**YOLO Detector report for TEST001**`)
- All case statuses use only the three allowed values: `approved`, `flagged_for_review`, `detection_failed`
- Valid JSON returned with no markdown fences

---

## Agent Definitions

### Agent 1: Submission Checker

| Attribute | Value |
|-----------|-------|
| **Name** | Submission Checker |
| **Role** | Submission Validation Specialist |
| **Tools** | None |
| **Temperature** | 0.1 |

**Backstory:**
You review the submitted claim information and uploaded files to make sure the case can be processed correctly. You validate the submitted claim JSON, inspect uploaded artifact files provided via `{Attachments}`, confirm that the required image input is present, and prepare a clean structured result for the next step. You do not perform image detection and you do not make case decisions.

**Goal:**
Parse `{claim_json}`, validate all required fields, match the attachment filename against `item_id`, and return a pass/fail structured payload. Produce no output other than the JSON object.

---

### Agent 2: YOLO Detector

| Attribute | Value |
|-----------|-------|
| **Name** | YOLO Detector |
| **Role** | Image Detection Execution Specialist |
| **Tools** | `YOLOapi` |
| **Temperature** | 0.1 |

**Backstory:**
You are the workflow's detector operator. Your job is to call the YOLO API tool on the resolved image and return the model output in a clean, standardized format. You do not interpret business meaning beyond the detector output, and you do not make approval or fraud decisions. You report what the model detected, preserve confidence values, and clearly distinguish between successful inference, no detections, and tool failures.

**Goal:**
Call `YOLOapi` with the selected attachment path, normalize the response into the standard detection schema, and output JSON only.

---

### Agent 3: Claim and YOLO Result Comparison Analyst

| Attribute | Value |
|-----------|-------|
| **Name** | Claim and YOLO Result Comparison Analyst |
| **Role** | YOLO Detection Result and Claim JSON Comparison |
| **Tools** | None |
| **Temperature** | 0.1 |

**Backstory:**
You compare what the detector found against what the claimant declared. You identify matches, missing claimed items, unexpected detected items, and cases where the image or claim may need resubmission. You are not the detector and you do not make workflow management decisions.

**Goal:**
Evaluate consistency between the structured claim and the structured YOLO output. Produce a decision (`match`, `mismatch`, `uncertain`, or `validation_failed`) with reasoning. Apply the `none` special case rule.

---

### Agent 4: Final Report Generator

| Attribute | Value |
|-----------|-------|
| **Name** | Final Report Generator |
| **Role** | Final PDF Report Specialist |
| **Tools** | `write_to_shared_pdf` |
| **Temperature** | 0.1 |

**Backstory:**
You assemble the outputs of the previous agents into one complete and consistent case record. You do not run detection and you do not reinterpret the model beyond the structured comparison result you receive. You are responsible for presenting the final decision clearly and generating a PDF report for operational review. You MUST invoke the `write_to_shared_pdf` tool on every run, with no exceptions.

**Goal:**
Build the final case record JSON, create a markdown report, call `write_to_shared_pdf` with a filename based on `item_id`, then return valid JSON only.

---

## Required Tools

### 1. YOLOapi

| Parameter | Type | Description |
|-----------|------|-------------|
| `api_url` | User config | YOLO detection endpoint URL (default: the configured deployment URL) |
| `image_path` | Tool arg | Relative path to the image file in the workspace (e.g., `scan.png`) |

**Behavior:** Sends the image as `multipart/form-data` to the YOLO API endpoint and returns the JSON detection response. Returns `{"error": "..."}` on file-not-found or API failure.

**Requirements:** `pydantic`, `requests`

---

### 2. Write to Shared PDF

Generates a PDF from markdown content and writes it to the shared workspace.

| Parameter | Description |
|-----------|-------------|
| `output_file` | PDF filename (e.g., `image_claim_verification_report_TEST001.pdf`) |
| `markdown_content` | Markdown string to render as the PDF body |

---

## Workflow Summary

| Stage | Task | Agent | Tool | Input | Output |
|-------|------|-------|------|-------|--------|
| 1 | Submission Validation | Submission Checker | — | `{claim_json}` + `{Attachments}` | Validated payload or fail report |
| 2 | YOLO Detection | YOLO Detector | `YOLOapi` | Attachment path from Task 1 | Detection labels, confidence, bbox |
| 3 | Claim Comparison | Comparison Analyst | — | Tasks 1 & 2 outputs | `match` / `mismatch` / `uncertain` / `validation_failed` |
| 4 | Report Generation | Final Report Generator | `write_to_shared_pdf` | Tasks 1–3 outputs | Case record JSON + PDF report |

---

## Decision Flow

```
{claim_json} + {Attachments}
         │
    ┌────▼────┐
    │ Task 1  │──── validation fail ────────────────────────────┐
    │ Checker │                                                 │
    └────┬────┘                                                 │
         │ pass                                                  │
    ┌────▼────┐                                                 │
    │ Task 2  │──── tool failure ───────────────────────────────┤
    │  YOLO   │                                                 │
    └────┬────┘                                                 │
         │ detections                                            │
    ┌────▼────┐                                                 │
    │ Task 3  │                                                 │
    │ Compare │                                                 │
    └────┬────┘                                                 │
         │                                                       │
    ┌────▼────────────────────────────────────────────────────▼─┐
    │ Task 4: Final Report Generator                             │
    │ Always calls write_to_shared_pdf regardless of path taken  │
    └────────────────────────────────────────────────────────────┘
```

---

## Usage Notes

1. **Attachment Filename Convention**: The uploaded image filename (without extension) must exactly match `item_id` in the claim JSON (e.g., `item_id = "TEST001"` requires attachment `TEST001.jpg`).

2. **Allowed Categories**: `item_name` must exactly match one of the 13 allowed categories. Case matters (e.g., `VacuumCup` not `vacuumcup`).

3. **`none` Category**: Use `item_name = "none"` when claiming no prohibited item is present. This triggers the special comparison rule: match if no detections, mismatch if detections exist.

4. **PDF Always Generated**: The workflow always produces a PDF report — even for validation failures and `none` submissions. This ensures a complete audit trail.

5. **YOLO API Configuration**: The `api_url` in `YOLOapi` user parameters must point to the deployed YOLO model inference endpoint. The default is pre-configured for the Cloudera-hosted deployment.
