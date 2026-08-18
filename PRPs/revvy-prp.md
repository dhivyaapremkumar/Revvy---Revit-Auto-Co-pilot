# PRP: REVVY

> Implementation blueprint for parallel agent execution

> **Superseded (2026-08-06):** Module 4's Design Generation pipeline
> described below has been removed from the backend. Model generation now
> happens through Claude (voice agent or Claude Desktop) driving the model
> directly via the RevitMCP connector; compliance checking is exposed as an
> MCP tool reusing `compliance_service.py`. Kept as historical context; see
> CLAUDE.md for the current architecture.

---

## METADATA

| Field | Value |
|-------|-------|
| **Product** | REVVY |
| **Type** | SaaS + Revit Plugin (pyRevit extension) |
| **Version** | 1.0 |
| **Created** | 2026-07-28 |
| **Complexity** | High |

---

## PRODUCT OVERVIEW

**Description:** REVVY is an AI copilot embedded in Revit (via a pyRevit extension) plus a companion web dashboard. It answers natural-language Revit workflow questions, searches Tamil Nadu building code (TNCDBR) with cited answers, queries the open Revit model, and generates design elements or full floor-plan layouts from a single command — every generated design is validated against Tamil Nadu building code and previewed for explicit user confirmation before it is written into the live model.

**Value Proposition:** Architects and BIM designers get instant, code-cited answers and AI-assisted modeling without leaving Revit or risking non-compliant designs reaching the live model unreviewed.

**MVP Scope:**
- [ ] User registration and login (email/password)
- [ ] Chat Copilot (chat + history, accessible from pyRevit panel and web dashboard)
- [ ] Code-RAG ingestion + cited Q&A search over TNCDBR
- [ ] Model Query (read-only queries on the open Revit model)
- [ ] Element-level design generation (walls, doors, windows, stairs, rooms) with compliance gate + preview/confirm
- [ ] Full floor-plan/layout generation with compliance gate + preview/confirm
- [ ] Admin panel (users + code document management)
- [ ] Analytics dashboard
- [ ] Email notifications (welcome, password reset, compliance report)

---

## TECH STACK

| Layer | Technology | Skill Reference |
|-------|------------|-----------------|
| Backend | FastAPI + Python 3.11+ | skills/BACKEND.md |
| Revit Integration | pyRevit extension (Python) | agents/revit-addin-agent.md (see Note below) |
| Frontend | React + TypeScript + Vite | skills/FRONTEND.md |
| Database | PostgreSQL + SQLAlchemy + pgvector | skills/DATABASE.md |
| AI / LLM | OpenAI GPT (chat, RAG, command parsing) | skills/BACKEND.md |
| Auth | JWT (email/password) + bcrypt | skills/BACKEND.md |
| UI | Chakra UI | skills/FRONTEND.md |
| Testing | pytest + RTL | skills/TESTING.md |
| Deployment | Docker + GitHub Actions | skills/DEPLOYMENT.md |

> **Note:** No `agents/revit-addin-agent.md` exists yet in `/agents/`. REVIT-ADDIN-AGENT tasks in this PRP should be executed by BACKEND-AGENT (Python-based pyRevit code is close enough to backend conventions) until a dedicated agent definition is added.

---

## DATABASE MODELS

### User
- id, email, hashed_password, full_name, is_active, is_verified, created_at

### RefreshToken
- id, user_id (FK -> User), token, expires_at, revoked

### ChatSession
- id, user_id (FK -> User), title, revit_project_name (nullable), created_at, updated_at

### ChatMessage
- id, session_id (FK -> ChatSession), role (user | assistant), content, created_at

### CodeDocument
- id, title, source_type (tncdbr | municipal_amendment), jurisdiction, version, uploaded_by (FK -> User), file_path, created_at

### CodeChunk
- id, document_id (FK -> CodeDocument), section_reference, content, embedding (vector, pgvector), created_at

### CodeQueryLog
- id, user_id (FK -> User), query, answer, cited_chunks (array of CodeChunk id), created_at

### ModelQueryLog
- id, user_id (FK -> User), revit_project_name, query, result_summary, created_at

### DesignGenerationRequest
- id, user_id (FK -> User), revit_project_name, command_text, scope (element | full_layout), generated_spec (JSON), compliance_status (pending | passed | failed | overridden), compliance_report (JSON), status (previewed | confirmed | rejected | applied), created_at, applied_at

---

## MODULES

### Module 1: Authentication
**Agents:** DATABASE-AGENT + BACKEND-AGENT + FRONTEND-AGENT

**Backend Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/auth/register | Create account |
| POST | /api/v1/auth/login | Get tokens |
| POST | /api/v1/auth/refresh | Refresh token |
| POST | /api/v1/auth/logout | Revoke refresh token |
| GET | /api/v1/auth/me | Current user |
| PUT | /api/v1/auth/me | Update profile |

**Frontend Pages:**
| Route | Page | Components |
|-------|------|------------|
| /login | LoginPage | LoginForm |
| /register | RegisterPage | RegisterForm |
| /forgot-password | ForgotPasswordPage | ResetForm |
| /profile | ProfilePage | ProfileForm (protected) |

---

### Module 2: Chat Copilot
**Agents:** BACKEND-AGENT + FRONTEND-AGENT + REVIT-ADDIN-AGENT

**Backend Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/chat/sessions | List chat sessions |
| POST | /api/v1/chat/sessions | Create new session |
| GET | /api/v1/chat/sessions/{id} | Get session with messages |
| DELETE | /api/v1/chat/sessions/{id} | Delete session |
| POST | /api/v1/chat/sessions/{id}/messages | Send message, get AI response |

**Frontend Pages:**
| Route | Page | Components |
|-------|------|------------|
| /chat | ChatListPage | SessionList, ChatWindow |
| /chat/{sessionId} | ChatDetailPage | ChatWindow, MessageBubble |

**pyRevit Panel:** Chat.pushbutton — docked chat panel inside Revit, calls the same `/chat` endpoints.

---

### Module 3: Code-RAG (Tamil Nadu Building Code)
**Agents:** DATABASE-AGENT + BACKEND-AGENT + FRONTEND-AGENT

**Backend Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/code-documents | Upload code document for ingestion |
| GET | /api/v1/code-documents | List ingested documents |
| DELETE | /api/v1/code-documents/{id} | Remove document + chunks |
| POST | /api/v1/code-rag/query | Ask a code-compliance question, get cited answer |

**Frontend Pages:**
| Route | Page | Components |
|-------|------|------------|
| /code-library | CodeLibraryPage | DocumentUpload, DocumentList (admin) |
| /code-search | CodeSearchPage | SearchBar, CitedAnswer |

---

### Module 4: Model Query & Design Generation
**Agents:** BACKEND-AGENT + FRONTEND-AGENT + REVIT-ADDIN-AGENT

**Backend Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/model/query | Query the open model (read-only) |
| POST | /api/v1/design/generate | Parse command -> generated_spec + compliance check -> preview |
| POST | /api/v1/design/generate/{id}/confirm | Confirm preview -> apply to live model via pyRevit bridge |
| POST | /api/v1/design/generate/{id}/reject | Discard a previewed design |
| GET | /api/v1/design/generate | List past generation requests + outcomes |

**Frontend Pages:**
| Route | Page | Components |
|-------|------|------------|
| /model-query | ModelQueryPage | QueryForm, ResultTable |
| /design-generation | DesignGenerationPage | RequestHistory, CompliancePreview, ConfirmRejectControls |

**pyRevit Panel:**
- ModelQuery.pushbutton — run queries against the currently open document
- Generate.pushbutton — issue a generation command, render preview overlay in Revit, confirm/reject inline

**Critical rule (from CLAUDE.md):** No design (element or full layout) is written to the live Revit model without explicit user confirmation, and every request must run the compliance gate before preview is shown.

---

### Module 5: Admin Panel
**Agents:** BACKEND-AGENT + FRONTEND-AGENT

**Backend Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/admin/users | List all users |
| PUT | /api/v1/admin/users/{id} | Update user status |
| GET | /api/v1/admin/stats | Platform statistics |
| GET | /api/v1/admin/code-documents | Manage code document ingestion |

**Frontend Pages:**
| Route | Page | Components |
|-------|------|------------|
| /admin | AdminDashboardPage | StatsSummary |
| /admin/users | AdminUsersPage | UserTable |
| /admin/code-documents | AdminCodeDocsPage | DocumentTable |

---

### Module 6: Analytics Dashboard
**Agents:** FRONTEND-AGENT (consumes Module 5's `/admin/stats`)

**Frontend Pages:**
| Route | Page | Components |
|-------|------|------------|
| /analytics | AnalyticsPage | UsageCharts, CitedSectionsList, GenerationSuccessRate |

---

### Module 7: Email Notifications
**Agents:** BACKEND-AGENT

**Backend Services:** `services/email_service.py` — welcome email, password reset, compliance-report summary (triggered internally by Auth and Design Generation modules, no dedicated public endpoints).

---

## PHASE EXECUTION PLAN

**Phase 1: Foundation (4 agents in parallel)**
- DATABASE-AGENT: All 9 models, migrations, pgvector extension setup, database.py
- BACKEND-AGENT: main.py, config.py, project structure, OpenAI + email service scaffolding
- FRONTEND-AGENT: Vite setup, folder structure, base Chakra UI components
- DEVOPS-AGENT: Docker (incl. Postgres+pgvector image), CI/CD, env files

**Validation Gate 1:** `pip install -r backend/requirements.txt`, `alembic upgrade head`, `npm install`, `docker-compose config`

**Phase 2: Modules (backend + frontend + revit-addin parallel per module)**
- Auth Module: JWT endpoints + Login/Register/Profile pages
- Chat Copilot: chat endpoints + web chat UI + pyRevit Chat panel
- Code-RAG: ingestion + pgvector search endpoints + code library/search UI
- Model Query & Design Generation: query/generate/confirm/reject endpoints + compliance_service + preview UI + pyRevit ModelQuery/Generate panels
- Admin Panel + Analytics: admin endpoints + admin/analytics UI
- Email Notifications: email_service wired into Auth + Design Generation flows

**Validation Gate 2:** `ruff check backend/`, `mypy backend/`, `npm run lint`, `npm run type-check`

**Phase 3: Quality (3 agents in parallel)**
- TEST-AGENT: pytest + RTL tests, 80%+ coverage, with explicit tests for the compliance-gate and confirm/reject state machine on `DesignGenerationRequest`
- REVIEW-AGENT: Security audit (API token handling for pyRevit add-in, prompt-injection resistance in Code-RAG/chat, no unconfirmed model writes)
- RESEARCH-AGENT: Best-practices validation for pgvector similarity search tuning and OpenAI function/tool-calling for command parsing

**Final Validation:** Full test suite, `docker-compose up -d`, `curl localhost:8000/health`, manual pyRevit extension load check

---

## VALIDATION GATES

| Gate | Commands |
|------|----------|
| 1 | `alembic upgrade head`, `npm install`, `docker-compose config` |
| 2 | `ruff check backend/`, `npm run type-check` |
| 3 | `pytest --cov --cov-fail-under=80`, `npm test` |
| Final | `docker-compose up -d`, `curl localhost:8000/health` |

---

## ENVIRONMENT VARIABLES

```env
DATABASE_URL=postgresql://user:password@localhost:5432/revvy
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
OPENAI_API_KEY=sk-...
EMAIL_SERVICE_API_KEY=...
VITE_API_URL=http://localhost:8000
REVVY_BACKEND_URL=http://localhost:8000
```

---

## NEXT STEP

Execute with parallel agents:
/execute-prp PRPs/revvy-prp.md
