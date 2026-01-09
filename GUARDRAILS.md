# ABS Contract Admin Agent - Guardrails & Security Protocol

## 1. Model Selection & Safety
- **Primary Model:** GPT-5.2 (via Emergent Integrations)
- **Fallback Model:** GPT-4o
- **Safety Mode:** Strict "Contract Admin" persona enforced.

## 2. Guardrails
The following guardrails are hardcoded into the system prompts and architecture:

### A. Hallucination Prevention
- **Strict Grounding:** The model is explicitly instructed to use *only* the provided document text.
- **Citation Requirement:** Critical dates and clauses must be backed by evidence (page number or text snippet).
- **Ambiguity Flagging:** If a date or term is ambiguous, the model must flag it (e.g., "Low Confidence") rather than guessing.

### B. Content Restrictions
- **No Legal Advice:** The system explicitly states it provides "contract administration guidance" and NOT legal advice.
- **Scope Limitation:** The model refuses to analyze non-contract documents (e.g., unrelated creative writing).

### C. Output Validation
- **Structured JSON:** All outputs are forced into a strict JSON schema to prevent free-form rambling.
- **Regex Parsing:** The backend extracts *only* the valid JSON object, discarding any potential "jailbreak" conversation text.

## 3. Ephemeral Processing & Data Privacy

### A. Data Retention Policy (Ephemeral)
- **Automatic Deletion (TTL):** All uploaded files, chat sessions, and analysis reports are automatically deleted from the database **24 hours** after creation.
- **Storage:** Data is stored in a secure MongoDB instance with Time-To-Live (TTL) indexes active.

### B. Training Data Exclusion
- **No Training:** Data processed via the Emergent/OpenAI API is **NOT** used to train future models.
- **Isolation:** Each analysis session is isolated. Context is not shared between different users or sessions.

## 4. Implementation Details
- **TTL Indexes:**
  - `documents` collection: Expires 24h after `upload_date`.
  - `sessions` collection: Expires 24h after `created_at`.
  - `analyses` collection: Expires 24h after `created_at`.
