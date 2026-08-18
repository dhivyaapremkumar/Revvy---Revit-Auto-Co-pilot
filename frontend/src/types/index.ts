// Core domain types for REVVY, mirroring the DATABASE MODELS section of
// PRPs/revvy-prp.md. Field names use snake_case to match the FastAPI/
// Pydantic JSON responses directly (no camelCase mapping layer). Phase 2
// module agents should extend this file rather than redefining these
// shapes locally, and should add new request/response types alongside
// the entity they belong to.

// ---------------------------------------------------------------------------
// Auth / Users
// ---------------------------------------------------------------------------

export interface User {
  id: number;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_verified: boolean;
  /**
   * NOTE (FRONTEND-AGENT assumption): not listed on the User model in
   * PRPs/revvy-prp.md. Required by the Admin Panel module spec ("gate
   * behind an admin check ... using user.is_admin"). Verify BACKEND-AGENT
   * actually returns this field on GET/PUT /auth/me once that router lands.
   */
  is_admin: boolean;
  created_at: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

/** POST /api/v1/auth/login request body (assumption: JSON, not OAuth2 form -- verify with BACKEND-AGENT). */
export interface LoginPayload {
  email: string;
  password: string;
}

/** POST /api/v1/auth/register request body. */
export interface RegisterPayload {
  email: string;
  password: string;
  full_name?: string;
}

/** PUT /api/v1/auth/me request body. */
export interface UpdateProfilePayload {
  full_name?: string;
  email?: string;
}

/**
 * POST /api/v1/auth/forgot-password request body.
 * NOTE (assumption): this endpoint is NOT in the Module 1 endpoint table in
 * PRPs/revvy-prp.md (only register/login/refresh/logout/me are listed), but
 * Module 7 (Email Notifications) implies a password-reset flow exists and
 * this task explicitly requires a ForgotPasswordPage. Verify the actual
 * route/shape with BACKEND-AGENT.
 */
export interface ForgotPasswordPayload {
  email: string;
}

export interface ResetPasswordPayload {
  token: string;
  new_password: string;
}

// ---------------------------------------------------------------------------
// Chat Copilot
// ---------------------------------------------------------------------------

export interface ChatSession {
  id: number;
  user_id: number;
  title: string | null;
  revit_project_name: string | null;
  created_at: string;
  updated_at: string;
}

export type ChatMessageRole = 'user' | 'assistant';

export interface ChatMessage {
  id: number;
  session_id: number;
  role: ChatMessageRole;
  content: string;
  created_at: string;
}

/** POST /api/v1/chat/sessions request body. */
export interface CreateChatSessionPayload {
  title?: string;
  revit_project_name?: string;
}

/** POST /api/v1/chat/sessions/{id}/messages request body. */
export interface SendChatMessagePayload {
  content: string;
}

/**
 * GET /api/v1/chat/sessions/{id} response body ("Get session with
 * messages" per PRPs/revvy-prp.md). Assumption: the session fields are
 * flattened alongside a `messages` array rather than nested -- verify
 * against BACKEND-AGENT's actual response.
 */
export interface ChatSessionWithMessages extends ChatSession {
  messages: ChatMessage[];
}

// ---------------------------------------------------------------------------
// Code-RAG (Tamil Nadu Building Code)
// ---------------------------------------------------------------------------

export type CodeDocumentSourceType = 'tncdbr' | 'municipal_amendment';

export interface CodeDocument {
  id: number;
  title: string;
  source_type: CodeDocumentSourceType;
  jurisdiction: string;
  version: string;
  uploaded_by: number;
  file_path: string;
  created_at: string;
}

/** A single stored, embedded chunk of a CodeDocument. */
export interface CodeChunk {
  id: number;
  document_id: number;
  section_reference: string;
  content: string;
  created_at: string;
}

/** A citation attached to a cited RAG answer (POST /code-rag/query). */
export interface CodeChunkCitation {
  chunk_id: number;
  document_id: number;
  document_title: string;
  section_reference: string;
  content: string;
  similarity_score?: number;
}

export interface CodeQueryLog {
  id: number;
  user_id: number;
  query: string;
  answer: string;
  cited_chunks: CodeChunkCitation[];
  created_at: string;
}

/** POST /api/v1/code-rag/query request body. */
export interface CodeRagQueryPayload {
  query: string;
}

/** POST /api/v1/code-rag/query response body. */
export interface CodeRagQueryResponse {
  answer: string;
  cited_chunks: CodeChunkCitation[];
}

/** Non-file form fields sent alongside the file on POST /api/v1/code-documents (multipart). */
export interface CodeDocumentUploadMetadata {
  title: string;
  source_type: CodeDocumentSourceType;
  jurisdiction: string;
  version: string;
}

// ---------------------------------------------------------------------------
// Model Query
// ---------------------------------------------------------------------------

/** A single Revit element returned by a model query. */
export interface ModelElementResult {
  element_id: string;
  category: string;
  family_name: string | null;
  type_name: string | null;
  parameters: Record<string, string | number | boolean | null>;
}

/** Response shape for POST /api/v1/model/query. */
export interface ModelQueryResult {
  revit_project_name: string;
  query: string;
  result_summary: string;
  elements: ModelElementResult[];
}

export interface ModelQueryLog {
  id: number;
  user_id: number;
  revit_project_name: string;
  query: string;
  result_summary: string;
  created_at: string;
}

/** POST /api/v1/model/query request body. */
export interface ModelQueryPayload {
  revit_project_name: string;
  query: string;
}

// ---------------------------------------------------------------------------
// Admin / Analytics
// ---------------------------------------------------------------------------

/** PUT /api/v1/admin/users/{id} request body. */
export interface AdminUserUpdatePayload {
  is_active?: boolean;
  is_admin?: boolean;
}

/** A single "most-cited code section" tally used by the Analytics dashboard. */
export interface CitedSectionStat {
  section_reference: string;
  document_title: string;
  count: number;
}

/** One point in a queries-per-day time series used by the Analytics dashboard. */
export interface DailyCount {
  date: string;
  count: number;
}

/**
 * GET /api/v1/admin/stats response body.
 * NOTE (FRONTEND-AGENT assumption): PRPs/revvy-prp.md only says this
 * endpoint returns "Platform statistics" without a defined shape. This
 * shape is inferred from Module 6 Analytics' required panels (queries per
 * user, most-cited code sections). Verify against BACKEND-AGENT's actual
 * response once /admin/stats lands and adjust the mapping in
 * services/adminService.ts if field names differ.
 */
export interface AdminStats {
  total_users: number;
  active_users: number;
  code_queries_per_day: DailyCount[];
  model_queries_per_day: DailyCount[];
  code_queries_total: number;
  model_queries_total: number;
  most_cited_sections: CitedSectionStat[];
}

// ---------------------------------------------------------------------------
// Shared API envelopes
// ---------------------------------------------------------------------------

export interface ApiErrorResponse {
  detail: string | Array<{ msg: string; loc: Array<string | number> }>;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
