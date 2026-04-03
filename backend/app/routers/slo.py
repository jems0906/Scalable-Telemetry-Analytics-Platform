from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.security import require_roles
from app.services.slo import evaluate_slos
from app.services.slo import fetch_slos

router = APIRouter(prefix="/slo", tags=["slo"])


@router.get("/status")
def get_slo_status(service_name: str | None = None, _: str = Depends(require_roles("viewer", "operator"))):
    return {"slos": fetch_slos(service_name)}


@router.post("/evaluate")
def evaluate_slo_now(db: Session = Depends(get_db), _: str = Depends(require_roles("operator"))):
    statuses = evaluate_slos(db)
    return {"status": "ok", "evaluated": len(statuses)}
