"""Login / me endpoints."""
from sqlalchemy.orm import Session

from src.models import User
from src.services import auth_service


def login(db: Session, payload) -> dict:
    token, user = auth_service.authenticate(db, payload.email, payload.password)
    return {
        "token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "role": user.role,
            "unit": user.unit,
        },
    }


def me(user: User) -> dict:
    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "role": user.role,
            "unit": user.unit,
        }
    }
