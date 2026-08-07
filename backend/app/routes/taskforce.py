from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from backend.app.database import get_session
from backend.app.models.case import Case
from backend.app.services.taskforce_service import (
    TASKFORCE_MEMBERS,
    get_llm_agent_brief,
    taskforce_service,
)

router = APIRouter(prefix='/taskforce', tags=['taskforce'])


@router.get('/overview')
def get_taskforce_overview(session: Session = Depends(get_session)):
    cases = session.exec(select(Case)).all()
    return taskforce_service.build_overview(cases)


@router.post('/brief/{case_id}')
def get_case_agent_brief(case_id: str, session: Session = Depends(get_session)):
    """
    Generate an LLM-powered agent brief for a specific case.
    Returns each taskforce member's assessment of the case.
    """
    case = session.exec(select(Case).where(Case.id == case_id)).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    briefs = []
    for member in TASKFORCE_MEMBERS:
        brief_text = get_llm_agent_brief(member["name"], member["role"], case)
        briefs.append({
            "agent": member["name"],
            "role": member["role"],
            "brief": brief_text,
        })

    return {
        "caseId": case_id,
        "customerName": case.customer_name,
        "category": case.category,
        "status": case.status,
        "agentBriefs": briefs,
    }
