# ABS Contract Admin Agent — Implementation Plan

Context and decisions (from user clarifications):
- LLM: Gemini via Emergent LLM Key
- Procore: Generate JSON only for now (no live API push)
- Storage: Persistent uploads in MongoDB (GridFS)
- UX: Chat-based, ChatGPT-like walkthrough to produce final documents
- Core flow: File Upload → Text Extraction → Gemini Analysis → JSON/Markdown Output

## 1) Objectives
- Provide a reliable, chat-based assistant for construction contract administration (ABS-focused).
- Support all defined TASK_TYPEs with structured outputs:
  1) INITIAL_CONTRACT_REVIEW
  2) PROPOSAL_COMPARISON_AND_EXHIBIT
  3) PM_CONTRACT_REVIEW_SUMMARY
  4) PROCORE_MAPPING (JSON schema)
  5) ACCOUNT_MANAGER_SUMMARY_EMAIL
  6) NEGOTIATION_SUGGESTED_REPLY
  7) POST_EXECUTION_SUMMARY
- Persist files (PDF/DOCX) and chat sessions; allow users to resume work.
- Ensure outputs are consistent, well-structured, and ABS-friendly (not legal advice).
- Keep clean API design: all routes under /api, use MONGO_URL env, bind FastAPI 0.0.0.0:8001.

## 2) Phased Implementation

### Phase 1 — Core POC (Required)
Scope: Prove end-to-end core without full UI polish.
- Integrations: Use integration_playbook_expert_v2 to configure Gemini via Emergent LLM key.
- Text extraction: PDF (PyMuPDF), DOCX (docx2txt) with simple fallback.
- Minimal persistence: GridFS for file, Mongo for metadata (files, analysis logs).
- Deterministic prompt templates for each TASK_TYPE (concise versions for POC).

POC Steps:
1. Backend-only test script `test_core.py` covering:
   - get_llm_client() using Emergent LLM key (Gemini 1.5 Pro preferred).
   - extract_text_from_pdf(path) and extract_text_from_docx(path).
   - run_analysis(task_type, text_chunks[, aux_inputs]) → returns both JSON and Markdown.
   - save_file_to_gridfs(path) → file_id; save_analysis_result(file_id, task_type, outputs).
2. Prepare 2–3 small sample files (contracts/proposals) to validate extraction robustness.
3. Validate response length management (chunking/summarization before ask if needed).
4. Log token usage and handle common LLM errors (timeouts, rate limits) gracefully.
5. Success criteria below must pass before Phase 2.

POC User Stories (at least 5):
1. As a user, I can upload a single PDF and see extracted text length and first 500 chars.
2. As a user, I can trigger INITIAL_CONTRACT_REVIEW and receive JSON + Markdown outputs.
3. As a user, I can store outputs linked to the uploaded file and retrieve them later.
4. As a user, I get a clear error for unsupported files or empty documents.
5. As a user, I can download the JSON/Markdown results as files.

POC Success Criteria:
- LLM call succeeds with Gemini and returns coherent outputs for all TASK_TYPE templates.
- Extraction works for PDF and DOCX; failures return actionable error messages.
- Results saved in Mongo (GridFS + metadata) with retrievable IDs.
- End-to-end time < 30s for a 10–20 page doc on average.

---

### Phase 2 — Full App Development

Backend (FastAPI):
- Collections: files (GridFS), sessions, messages, analyses, users (optional placeholder for future auth).
- Key endpoints (all prefixed with /api):
  - POST /api/files/upload (multipart) → {file_id, name, size, mime}
  - GET  /api/files/{file_id} → metadata + preview text (first N chars)
  - POST /api/sessions → create chat session {session_id, task_type}
  - GET  /api/sessions/{session_id}
  - POST /api/sessions/{session_id}/messages → user message, optional file_ids → returns assistant message + outputs
  - POST /api/analyze → direct analysis without chat (task_type, file_ids)
  - GET  /api/analyses/{analysis_id} → saved result
  - GET  /api/health
- Services:
  - Text extraction service (PDF/DOCX) with chunking and caching.
  - LLM service (Gemini) with prompt templates and schema validation.
  - Serialization helpers for ObjectId/datetime.
- Config: Use env MONGO_URL; bind 0.0.0.0:8001; strict /api prefix.
- Error handling: standardized error model; file-type validation; size limits.

Prompt Templates (production variants) per TASK_TYPE:
- INITIAL_CONTRACT_REVIEW → Clause-by-clause + Key Issues + Redline Package Summary.
- PROPOSAL_COMPARISON_AND_EXHIBIT → Comparison table + Draft Exhibit sections.
- PM_CONTRACT_REVIEW_SUMMARY → Actionable PM summary sections.
- PROCORE_MAPPING → JSON-like structure mapping final clauses/exhibits/notes.
- ACCOUNT_MANAGER_SUMMARY_EMAIL → Email-style summary with clear bullets.
- NEGOTIATION_SUGGESTED_REPLY → Professional, collaborative reply with options.
- POST_EXECUTION_SUMMARY → What was agreed; ops handoff checklist.

Frontend (React + shadcn/ui):
- Chat layout: left sidebar (sessions, files), main chat pane, top action bar.
- Message composer: upload files, pick TASK_TYPE (chips), send prompt, show loading.
- Output viewers: tabs for JSON, Markdown, and Pretty Render; download buttons.
- State: session store (local + server), error toasts, retry, regenerate response.
- Accessibility: keyboard-first, data-testid on interactive elements, no transparent backgrounds.

Phase 2 User Stories (at least 5):
1. As a user, I can create a new chat session, pick a TASK_TYPE, and upload multiple files.
2. As a user, I can ask follow-up questions and receive refined outputs without reuploading.
3. As a user, I can switch between JSON/Markdown/Rendered views and download outputs.
4. As a user, I can resume a previous session and see full history and attached files.
5. As a user, I can run PROCORE_MAPPING to get a contract-ready JSON payload (no push).
6. As a user, I can view clear failure messages and retry failed analyses.
7. As a user, I can preview extracted text to confirm parsing before analysis.
8. As a user, I can copy-to-clipboard any generated section.

Testing (end of Phase 2):
- Lint: ruff on backend, ESLint on frontend.
- E2E with testing_agent: file upload, session flow, each TASK_TYPE generation, downloads, error cases.
- Verify all routes use /api; check no hardcoded URLs; validate serialization.

Non-Functional:
- Performance: chunking for long docs; basic caching of extraction per file_id.
- Reliability: retries/backoff for LLM; input size guards; clear error surfaces.
- Security (MVP): file-type and size validation; sanitize filenames; no auth yet (future).

Deliverables:
- Working backend + frontend with chat guidance to final document.
- Prompt library for 7 TASK_TYPEs (versioned in repo).
- Downloadable outputs and persistent sessions.

---

### Phase 3 — Enhancements (Post-MVP)
- Procore API push (OAuth, project selection, attachment upload).
- Auth (basic JWT), roles, and multi-user org contexts.
- Streaming responses (SSE) and background tasks for long analyses.
- Clause library, saved redlines, diff/compare views, templated exports (DOCX/PDF).
- Admin analytics (usage, token cost), audit logs.

## 3) Immediate Next Actions
1. Call integration_playbook_expert_v2 for Gemini via Emergent key; confirm SDK and model IDs.
2. Implement Phase 1 `test_core.py` with extraction + Gemini calls + Mongo save; fix until passes.
3. After POC success, run design_agent for UI guidelines; install any UI deps.
4. Build Phase 2 backend + frontend in parallel using bulk file writer; keep /api prefix.
5. Run linting, inspect logs, then execute testing_agent for E2E; fix issues.

## 4) Success Criteria (Go/No-Go)
- POC: Single-run script proves extraction + Gemini outputs + Mongo persistence for sample files.
- App: All Phase 2 user stories demonstrably work; no red screen errors; stable logs.
- Outputs: Structured JSON and clean Markdown per TASK_TYPE; downloadable; consistent.
- Env: Uses MONGO_URL; backend at 0.0.0.0:8001; frontend uses REACT_APP_BACKEND_URL; all endpoints under /api.
- Testing: testing_agent passes core scenarios; issues fixed and re-verified.
