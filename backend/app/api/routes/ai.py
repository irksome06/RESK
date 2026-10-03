from fastapi import APIRouter
from pydantic import BaseModel
from app.services.ai import explain

router = APIRouter(prefix="/ai", tags=["ai"])


class ExplainRequest(BaseModel):
    payload: dict


@router.post("/explain")
async def ai_explain(request: ExplainRequest):
    return await explain(request.payload)
