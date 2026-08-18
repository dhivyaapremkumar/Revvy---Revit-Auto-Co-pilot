# INITIAL.md - REVVY Product Definition

> Revit + AI Copilot — Natural-Language Revit Assistant with Tamil Nadu Building Code RAG

> **Superseded (2026-08-06):** Module 4's own "Design Generation" pipeline
> (LLM spec parser + confirm/apply flow inside REVVY's backend) has been
> removed. Model generation is now driven by chatting with Claude directly
> (voice or Claude Desktop) through the RevitMCP connector, with TNCDBR
> compliance checking exposed as an MCP tool backed by REVVY's existing
> `compliance_service.py`. Left below as historical context for what Module
> 4 originally specified; see CLAUDE.md for the current architecture.

---

## PRODUCT

### Name
REVVY

### Description
REVVY is an AI copilot embedded in Revit (via a pyRevit extension) plus a companion web dashboard. It lets architects and BIM designers ask natural-language questions about Revit workflows, query the open Revit model directly, search Tamil Nadu building code (TNCDBR) with cited answers, and generate design elements or full floor-plan layouts from a single command — with every generated design validated against Tamil Nadu building code and previewed for confirmation before it's written into the live model.

### Target User
Architects & BIM designers actively modeling in Revit who need fast natural-language answers, in-model queries, and Tamil Nadu building-code compliance checks without leaving their workflow.

### Type
- [x] SaaS (Software as a Service) + Revit plugin (pyRevit extension)

---

## TECH STACK

### Backend
- [x] FastAPI + Python 3.11+

### Revit Integration
- [x] pyRevit extension (Python) — runs inside Revit, talks to the FastAPI backend over HTTP

### Frontend (Web Dashboard)
- [x] React + TypeScript + Vite

### Database
- [x] PostgreSQL + SQLAlchemy
- [x] pgvector extension — stores Tamil Nadu Building Code embeddings for RAG

### AI / LLM
- [x] OpenAI GPT (chat, RAG answer generation, command parsing for design generation)

### Authentication
- [x] Email/Password only (JWT)

### UI Framework
- [x] Chakra UI

### Payments
- None for MVP (revisit post-MVP)

---

## MODULES

### Module 1: Authentication (Required)

**Description:** User authentication and authorization

**Models:**
- User: id, email, hashed_password, full_name, is_active, is_verified, created_at
- RefreshToken: id, user_id, token, expires_at, revoked

**API Endpoints:**
- POST /auth/register - Create new account
- POST /auth/login - Login with email/password
- POST /auth/refresh - Refresh access token
- POST /auth/logout - Revoke refresh token
- GET /auth/me - Get current user profile
- PUT /auth/me - Update profile

**Frontend Pages:**
- /login - Login page
- /register - Registration page
- /forgot-password - Forgot password page
- /profile - User profile page (protected)

---

### Module 2: Chat Copilot

**Description:** Natural-language chat assistant for Revit workflows — "how do I..." questions, command/workflow guidance, and design/modeling suggestions. Chat history is saved per user and accessible from both the pyRevit panel and the web dashboard.

**Models:**
```
ChatSession:
  - id, user_id (FK)
  - title, revit_project_name (nullable)
  - created_at, updated_at

ChatMessage:
  - id, session_id (FK)
  - role (user | assistant), content
  - created_at
```

**API Endpoints:**
```
GET    /api/chat/sessions              - List chat sessions
POST   /api/chat/sessions              - Create new session
GET    /api/chat/sessions/{id}         - Get session with messages
DELETE /api/chat/sessions/{id}         - Delete session
POST   /api/chat/sessions/{id}/messages - Send message, get AI response
```

**Frontend Pages:**
- /chat - Chat interface with session list + active conversation
- /chat/{sessionId} - Specific session detail

**pyRevit Panel:**
- Copilot chat pushbutton — opens a docked chat panel inside Revit

---

### Module 3: Code-RAG (Tamil Nadu Building Code)

**Description:** Retrieval-augmented search over the Tamil Nadu Combined Development and Building Rules (TNCDBR) and local municipal amendments. Answers setback, FSI/FAR, height, parking, fire-safety, and occupancy questions with citations to the specific clause/section. Powers the compliance gate used by Module 4's design generation.

**Models:**
```
CodeDocument:
  - id, title, source_type (tncdbr | municipal_amendment)
  - jurisdiction, version, uploaded_by (FK User), file_path
  - created_at

CodeChunk:
  - id, document_id (FK)
  - section_reference (e.g. "Rule 19(3)")
  - content, embedding (vector, pgvector)
  - created_at

CodeQueryLog:
  - id, user_id (FK), query, answer, cited_chunks (array of CodeChunk id)
  - created_at
```

**API Endpoints:**
```
POST   /api/code-documents              - Upload a code document (PDF/text) for ingestion
GET    /api/code-documents              - List ingested documents
DELETE /api/code-documents/{id}         - Remove a document + its chunks
POST   /api/code-rag/query              - Ask a code-compliance question, get cited answer
```

**Frontend Pages:**
- /code-library - List/upload/manage ingested code documents (admin)
- /code-search - Standalone code Q&A search with citations

---

### Module 4: Model Query & Design Generation

**Description:** Two-way interaction with the open Revit model.
1. **Query (read):** element counts, room/area schedules, parameter values, and cross-checking existing model values against Code-RAG (e.g. "does this staircase width meet TNCDBR minimum?").
2. **Generation (write):** create individual elements (walls, doors, windows, stairs, rooms) or full floor-plan layouts from a single natural-language command. Every generated design is validated against Tamil Nadu building code via Code-RAG *before* being applied, and shown to the user as a preview that requires explicit confirmation before it's committed to the live Revit model.

**Models:**
```
ModelQueryLog:
  - id, user_id (FK), revit_project_name
  - query, result_summary
  - created_at

DesignGenerationRequest:
  - id, user_id (FK), revit_project_name
  - command_text
  - scope (element | full_layout)
  - generated_spec (JSON — elements/parameters to create)
  - compliance_status (pending | passed | failed | overridden)
  - compliance_report (JSON — cited code checks + results)
  - status (previewed | confirmed | rejected | applied)
  - created_at, applied_at
```

**API Endpoints:**
```
POST   /api/model/query                        - Query the open model (read-only)
POST   /api/design/generate                    - Parse command -> generated_spec + compliance check -> preview
POST   /api/design/generate/{id}/confirm        - User confirms preview -> apply to live model via pyRevit bridge
POST   /api/design/generate/{id}/reject         - Discard a previewed design
GET    /api/design/generate                     - List past generation requests + outcomes
```

**Frontend Pages:**
- /model-query - Ad-hoc model query tool (mirrors in-Revit panel)
- /design-generation - History of generation requests, compliance reports, preview/confirm UI

**pyRevit Panel:**
- Model Query pushbutton — run queries against the currently open document
- Generate pushbutton — issue a generation command, review preview overlay in Revit, confirm/reject

---

### Module 5: Admin Panel

**Description:** Admin-only management interface for users, code document library, and system health.

**API Endpoints:**
- GET /admin/users - List all users
- PUT /admin/users/{id} - Update user status
- GET /admin/stats - Platform statistics (queries/day, generation success rate, most-cited code sections)
- GET /admin/code-documents - Manage code document ingestion pipeline

**Frontend Pages:**
- /admin - Admin dashboard (protected, admin only)
- /admin/users - User management
- /admin/code-documents - Code document management

---

### Module 6: Analytics Dashboard

**Description:** Usage metrics for the product team and firm admins.

**Frontend Pages:**
- /analytics - Queries per user, most-cited code sections, generation success/rejection rate, active sessions

---

### Module 7: Email Notifications

**Description:** Transactional emails — welcome, password reset, and compliance-check summary reports for completed design generations.

---

## MVP SCOPE

### Must Have (MVP)
- [x] User registration and login (email/password)
- [x] Chat Copilot (chat + history)
- [x] Code-RAG ingestion + cited Q&A search
- [x] Model Query (read-only queries on open Revit model)
- [x] Element-level design generation (walls, doors, windows, stairs, rooms) with compliance gate + preview/confirm
- [x] Full floor-plan/layout generation with compliance gate + preview/confirm
- [x] Admin panel (users + code document management)
- [x] Analytics dashboard
- [x] Email notifications (welcome, password reset, compliance report)

### Nice to Have (Post-MVP)
- [ ] Google OAuth login
- [ ] Payments/subscriptions
- [ ] Multi-jurisdiction building codes beyond Tamil Nadu
- [ ] Auto-apply generation without preview (opt-in power-user mode)

---

## ACCEPTANCE CRITERIA

### Authentication
- [ ] User can register with email/password
- [ ] User can login with email/password
- [ ] JWT tokens work correctly with refresh
- [ ] Protected routes redirect to login

### Chat Copilot
- [ ] User can start a session and send/receive messages
- [ ] Chat history persists and is retrievable from both pyRevit panel and web dashboard

### Code-RAG
- [ ] Uploaded TNCDBR/amendment documents are chunked, embedded, and stored in pgvector
- [ ] Queries return answers with correct section/clause citations
- [ ] Irrelevant/out-of-scope questions are clearly flagged as such (no hallucinated citations)

### Model Query & Design Generation
- [ ] Read queries return accurate element/parameter/room data from the open model
- [ ] Element-level and full-layout generation requests produce a `generated_spec` + compliance report before any write
- [ ] Non-compliant designs are flagged with the specific violated rule(s) before the user can confirm
- [ ] No design is written to the live Revit model without explicit user confirmation
- [ ] Rejected previews leave the Revit model unchanged

### Quality
- [ ] All API endpoints documented in OpenAPI
- [ ] Backend test coverage 80%+
- [ ] Frontend TypeScript strict mode passes
- [ ] Docker builds and runs successfully (backend + Postgres/pgvector); pyRevit extension documented for manual install

---

## SPECIAL REQUIREMENTS

### Security
- [x] Rate limiting on auth endpoints
- [x] Input validation on all endpoints
- [x] SQL injection prevention
- [x] XSS prevention
- [x] pyRevit extension authenticates to backend via per-user API token (not shared credentials)

### Integrations
- [x] OpenAI API for chat, RAG generation, and command parsing
- [x] pgvector for embeddings storage/search
- [x] Email service for notifications (welcome, reset password, compliance reports)
- [x] File upload service for code document ingestion (PDF/text)
- [ ] Stripe (not needed for MVP)

---

## AGENTS

> These agents build REVVY in parallel:

| Agent | Role | Works On |
|-------|------|----------|
| DATABASE-AGENT | Creates all models and migrations | All database models incl. pgvector setup |
| BACKEND-AGENT | Builds API endpoints and services | Auth, Chat, Code-RAG, Model Query, Design Generation, Admin |
| FRONTEND-AGENT | Creates UI pages and components | All web dashboard modules |
| REVIT-ADDIN-AGENT | Builds the pyRevit extension | Chat panel, Model Query panel, Generate panel + backend bridge |
| DEVOPS-AGENT | Sets up Docker, CI/CD, environments | Infrastructure |
| TEST-AGENT | Writes unit and integration tests | All code |
| REVIEW-AGENT | Security and code quality audit | All code |

---

# READY?

```bash
/generate-prp INITIAL.md
```

Then:

```bash
/execute-prp PRPs/revvy-prp.md
```
