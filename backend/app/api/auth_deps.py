import uuid

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

# Fresh per process — see get_local_dev_user().
_LOCAL_DEV_USER_ID = str(uuid.uuid4())


def normalize_role(role: object) -> str:
    if isinstance(role, Roles):
        return role.value
    return str(role).upper()


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    user_repo = UserRepository(db)
    return AuthService(user_repo)


def get_local_dev_user() -> dict:
    """The anonymous ADMIN served when auth is disabled.

    Reachable only when AUTH_ENABLED=False, DEBUG=True and ENVIRONMENT=local
    hold simultaneously — Settings refuses to construct otherwise, so this
    cannot be reached on any deployed host. See
    app/core/config.Settings._reject_auth_bypass_outside_local.

    The id is generated per process rather than being a fixed sentinel. The old
    hardcoded MVP_ANONYMOUS_USER_ID meant every local run shared one identity,
    so audit rows written during development were indistinguishable from each
    other and from anything that leaked in from another environment.
    """
    return {
        "id": _LOCAL_DEV_USER_ID,
        "name": "Local Dev (auth disabled)",
        "email": "local-dev@grademind.invalid",
        "role": Roles.ADMIN.value,
        "auth_disabled": True,
    }


def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    auth_service: AuthService = Depends(get_auth_service)
) -> dict:
    if not settings.AUTH_ENABLED:
        return get_local_dev_user()

    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == "bearer":
                token = parts[1]

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
