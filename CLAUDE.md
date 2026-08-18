# CLAUDE.md - REVVY Project Rules

> Project-specific rules for Claude Code. This file is read automatically.

---

## Project Overview

**Project Name:** REVVY
**Description:** Natural-language Revit AI copilot with Tamil Nadu Building Code (TNCDBR) RAG — chat assistant and in-model querying from the pyRevit add-in, plus a voice-controlled agent (Claude + RevitMCP) that can generate/modify the model directly and check it against TNCDBR compliance on demand.
**Tech Stack:**
- Backend: FastAPI + Python 3.11+
- Revit Integration: pyRevit extension (Python)
- Frontend: React + TypeScript + Vite
- Database: PostgreSQL + SQLAlchemy + pgvector
- AI/LLM: OpenAI GPT (chat, RAG, command parsing)
- Auth: JWT (email/password)
- UI: Chakra UI

---

## Project Structure

```
revvy/
├── backend/
│   ├── app/
│   │   ├── main.py, config.py, database.py
│   │   ├── models/
│   │   │   ├── user.py, chat.py, code_document.py, code_chunk.py
│   │   │   └── model_query_log.py
│   │   ├── schemas/
│   │   ├── routers/
│   │   │   └── auth.py, chat.py, code_rag.py, model_query.py, admin.py
│   │   ├── services/
│   │   │   ├── llm_service.py       # OpenAI chat/completions
│   │   │   ├── rag_service.py       # pgvector embed/search
│   │   │   └── compliance_service.py # TNCDBR RAG-verdict logic, called by the ask_building_code MCP tool
│   │   └── auth/
│   ├── alembic/
│   └── tests/
├── revit-addin/
│   └── REVVY.extension/
│       ├── REVVY.tab/
│       │   └── Copilot.panel/
│       │       ├── Chat.pushbutton/
│       │       └── ModelQuery.pushbutton/
│       └── lib/                     # shared helpers, backend HTTP client
├── frontend/
│   ├── src/
│   │   ├── components/, pages/, hooks/, services/, context/, types/
│   └── package.json
├── data/
│   └── tncdbr/                      # source building-code PDFs/text for ingestion
├── .claude/commands/
├── skills/
├── agents/
└── PRPs/
```

---

## Code Standards

### Python (Backend + pyRevit add-in)
```python
# ALWAYS use type hints
def get_chat_session(db: Session, session_id: int) -> ChatSession:
    pass

# ALWAYS add docstrings for public functions
def query_code_rag(db: Session, query: str) -> CodeRagAnswer:
    """
    Search Tamil Nadu building code chunks via pgvector and return a cited answer.

    Args:
        db: Database session
        query: Natural-language compliance question

    Returns:
        CodeRagAnswer with answer text and cited CodeChunk references
    """
    pass
```

### TypeScript (Frontend)
```typescript
// ALWAYS define interfaces for props and data
interface ChatMessageProps {
  id: number;
  role: "user" | "assistant";
  content: string;
}

// NO any types allowed
const fetchChatSession = async (id: number): Promise<ChatSession> => {
  // ...
};
```

---

## Forbidden Patterns

### Backend
- Never use `print()` - use `logging` module
- Never store passwords in plain text
- Never hardcode secrets (OpenAI API key, DB credentials) - use environment variables
- Never use `SELECT *` - specify columns
- Never skip input validation

### Frontend
- Never use `any` type
- Never leave console.log in production
- Never skip error handling in async operations
- Never use inline styles - use Chakra UI

### Model generation (Revit model writes via the voice agent / RevitMCP)
- REVVY's own backend never writes to the live Revit model — model generation is driven by Claude (voice agent or Claude Desktop) acting through the RevitMCP connector's tools (e.g. `execute_revit_code`, `place_family`), not through a REVVY-owned confirm/apply pipeline
- The agent should check a generated/modified design against TNCDBR via the `ask_building_code` MCP tool (backed by `compliance_service.py`) rather than asserting compliance from its own knowledge
- Never fabricate a compliance verdict when `ask_building_code` returns no relevant TNCDBR excerpts — say so explicitly, same as the Code-RAG rule below

---

## Module-Specific Rules

### Chat Copilot
- Chat sessions and messages must belong to a user (`user_id` foreign key)
- Chat responses that reference building code must delegate to Code-RAG rather than answering from the LLM's own knowledge

### Code-RAG
- Every RAG answer must include section/clause citations; if no relevant chunk is found above the similarity threshold, return "not found in ingested code" rather than a guessed answer
- Ingested documents are chunked with section references preserved (never chunk across section boundaries when avoidable)

### Model Query
- Read queries (Model Query, and the RevitMCP `run_model_qa` tool) never mutate the Revit model

---

## API Conventions

- All endpoints prefixed with `/api/v1/`
- Use plural nouns for resources: `/chat/sessions`, `/code-documents`
- Return appropriate HTTP status codes:
  - 200: Success
  - 201: Created
  - 400: Bad Request
  - 401: Unauthorized
  - 404: Not Found
  - 409: Conflict

---

## Authentication

Email/password only for MVP (no OAuth).

### JWT Configuration
- Access token expires: 30 minutes
- Refresh token expires: 7 days
- Algorithm: HS256

### pyRevit Add-in Auth
- The Revit add-in authenticates to the backend using a per-user API token (issued after login on the web dashboard), never shared/service credentials

---

## Environment Variables

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/revvy

# Auth
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# OpenAI
OPENAI_API_KEY=sk-...

# Email
EMAIL_SERVICE_API_KEY=...

# Frontend
VITE_API_URL=http://localhost:8000

# pyRevit add-in
REVVY_BACKEND_URL=http://localhost:8000
```

---

## Development Commands

```bash
# Backend
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev

# Docker
docker-compose up -d

# Tests
pytest backend/tests -v
cd frontend && npm test

# Linting
ruff check backend/
cd frontend && npm run lint

# pyRevit add-in
# Copy/symlink revit-addin/REVVY.extension into %APPDATA%/pyRevit/Extensions and reload pyRevit in Revit
```

---

## Commit Message Format

```
feat([module]): add [feature]
fix([module]): fix [bug]
refactor([module]): refactor [component]
test([module]): add tests for [feature]
docs: update [documentation]
```

---

## Skills Reference

| Task | Skill to Read |
|------|---------------|
| Database models | skills/DATABASE.md |
| API + Auth | skills/BACKEND.md |
| React + UI | skills/FRONTEND.md |
| Testing | skills/TESTING.md |
| Deployment | skills/DEPLOYMENT.md |

---

## Agent Coordination

For complex tasks, the ORCHESTRATOR coordinates:
- DATABASE-AGENT → Backend models + pgvector setup
- BACKEND-AGENT → API development (chat, code-rag, model query, admin)
- FRONTEND-AGENT → UI components
- REVIT-ADDIN-AGENT → pyRevit extension panels + backend bridge
- TEST-AGENT → Testing
- REVIEW-AGENT → Code review, especially the RevitMCP compliance/QA tools' TNCDBR gate
- DEVOPS-AGENT → Deployment

Read agent definitions in `/agents/` folder.
