"""Model Query module endpoint (read-only queries on the open Revit model)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.model_query import ModelQueryRequest, ModelQueryResponse
from app.services import model_query_service

router = APIRouter(prefix="/model", tags=["model-query"])


@router.post("/query", response_model=ModelQueryResponse)
async def query_model(
    data: ModelQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ModelQueryResponse:
    """Answer a read-only question about the currently open Revit model."""
    result_summary, raw_data = await model_query_service.run_model_query(
        db,
        user=current_user,
        revit_project_name=data.revit_project_name,
        query=data.query,
        model_state=data.model_state,
    )
    return ModelQueryResponse(result_summary=result_summary, raw_data=raw_data)
