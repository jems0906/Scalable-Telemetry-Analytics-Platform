from fastapi import APIRouter, Depends

from app.security import require_roles
from app.services.alerts import fetch_alert_history

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("/history")
def get_alert_history(limit: int = 100, _: str = Depends(require_roles("viewer", "operator"))):
    return {"alerts": fetch_alert_history(limit)}
