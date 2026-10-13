"""Case-level endpoints: rule evaluation over the fields the web application stored."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from renova_extract.api.deps import require_internal_token
from renova_extract.rules.engine import RuleEngine
from renova_extract.rules.model import CaseIn, Evaluation

router = APIRouter(prefix="/v1/cases", tags=["cases"], dependencies=[Depends(require_internal_token)])


def get_engine(request: Request) -> RuleEngine:
    engine: RuleEngine = request.app.state.rule_engine
    return engine


@router.post("/evaluate", response_model=Evaluation)
def evaluate(case: CaseIn, engine: Annotated[RuleEngine, Depends(get_engine)]) -> Evaluation:
    """Runs the rules valid on the case's reference date. Findings are always 'do_sprawdzenia'."""
    return engine.evaluate(case)
