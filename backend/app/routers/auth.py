from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.security import authenticate_user, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(payload: LoginRequest):
    role = authenticate_user(payload.username, payload.password)
    if not role:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(subject=payload.username, role=role)
    return {"access_token": token, "token_type": "bearer", "role": role}
