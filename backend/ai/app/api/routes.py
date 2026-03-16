import uuid
from datetime import datetime, UTC
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import CopilotMessage, Incident
from app.schemas.schemas import ChatRequest, ChatResponse, IncidentCreate, IncidentResponse
from app.services.claude_service import chat

router = APIRouter()

@router.post("/ai/chat", response_model=ChatResponse, tags=["ai"])
async def copilot_chat(
    req: ChatRequest,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> ChatResponse:
    context = {}
    if req.service_id:
        context["service_id"] = req.service_id
    if req.incident_id:
        context["incident_id"] = str(req.incident_id)

    response_text = await chat(req.message, req.history, context)

    # persist message pair
    db.add(CopilotMessage(session_id=req.session_id, incident_id=req.incident_id, role="user", content=req.message, context=context))
    db.add(CopilotMessage(session_id=req.session_id, incident_id=req.incident_id, role="assistant", content=response_text, context=context))
    await db.flush()

    suggested = []
    if "rollback" in response_text.lower():
        suggested.append("nerve rollback --to=previous")
    if "logs" in response_text.lower():
        suggested.append("nerve logs --since=1h --filter=ERROR")
    if "postmortem" in response_text.lower():
        suggested.append("nerve postmortem create")

    return ChatResponse(session_id=req.session_id, response=response_text, suggested_actions=suggested)

@router.post("/ai/incidents", response_model=IncidentResponse, tags=["ai"])
async def create_incident(
    payload: IncidentCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> Incident:
    incident = Incident(**payload.model_dump())
    db.add(incident)
    await db.flush()
    await db.refresh(incident)
    return incident

@router.get("/ai/incidents", response_model=list[IncidentResponse], tags=["ai"])
async def list_incidents(
    service_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> list[Incident]:
    q = select(Incident).order_by(Incident.started_at.desc()).limit(50)
    if service_id:
        q = q.where(Incident.service_id == service_id)
    result = await db.execute(q)
    return list(result.scalars().all())
