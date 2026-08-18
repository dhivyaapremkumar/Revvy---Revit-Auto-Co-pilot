"""API routers package.

Phase 2 modules register their routers here, e.g.:

    from app.routers import auth, chat, code_rag, model_query, design, admin

Each router module must expose a module-level `router: APIRouter` instance
so it can be included in `app.main` via:

    app.include_router(auth.router, prefix="/api/v1")
"""
