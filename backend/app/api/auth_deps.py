from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.core.config import settings
from app.core.security import decode_access_token
from app.utils.roles import Roles

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)
MVP_ANONYMOUS_USER_ID = "00000000-0000-0000-0000-000000000000"


def normalize_role(role: object) -> str:
    if isinstance(role, Roles):
        return role.value
    return str(role).upper()


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    user_repo = UserRepository(db)
    return AuthService(user_repo)


def get_mvp_anonymous_user() -> dict:
    return {
        "id": MVP_ANONYMOUS_USER_ID,
        "name": "MVP Anonymous",
        "email": None,
        "role": Roles.ADMIN.value,
        "auth_disabled": True,
    }


def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    auth_service: AuthService = Depends(get_auth_service)
) -> dict:
    if not settings.AUTH_ENABLED:
        return get_mvp_anonymous_user()

    if not token:
        token = request.query_params.get("token")
        
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    email: str = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload is missing subject",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    return auth_service.get_current_user_by_email(email)

class RoleChecker:
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = [normalize_role(role) for role in allowed_roles]

    def __call__(self, user: dict = Depends(get_current_user)) -> dict:
        user_role = normalize_role(user.get("role"))
        if user_role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted for role: {user_role}"
            )
        user["role"] = user_role
        return user

# Reusable role guards
require_admin = RoleChecker([Roles.ADMIN.value])
require_teacher = RoleChecker([Roles.TEACHER.value])
require_teacher_or_admin = RoleChecker([Roles.TEACHER.value, Roles.ADMIN.value])
