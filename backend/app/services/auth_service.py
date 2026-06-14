from fastapi import HTTPException, status
from app.schemas.auth import RegisterRequest, LoginRequest
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.utils.roles import Roles
from app.repositories.user_repository import UserRepository
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.services.audit_service import AuditService
from datetime import datetime, timezone, timedelta
from typing import Optional
import hashlib
from uuid import uuid4


def ensure_utc(dt):
    """Normalize a datetime to UTC-aware. SQLite returns naive datetimes."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

class AuthService:
    """
    Service class handling authentication business logic.
    """

    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo
        self.db = user_repo.session

    def _serialize_user(self, user: User) -> dict:
        role = user.role.value if isinstance(user.role, Roles) else str(user.role)
        return {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": role.upper()
        }

    def register_user(self, user_data: RegisterRequest, ip_address: Optional[str] = None) -> dict:
        existing_user = self.user_repo.get_user_by_email(user_data.email)
        if existing_user:
            AuditService.log_event(self.db, "Registration Failed - Duplicate", None, ip_address)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        hashed_pw = hash_password(user_data.password)
        user_role = Roles.STUDENT
        if user_data.role:
            try:
                user_role = Roles[user_data.role.upper()]
            except KeyError:
                pass

        new_user = User(
            name=user_data.name,
            email=user_data.email,
            password_hash=hashed_pw,
            role=user_role
        )
        
        created_user = self.user_repo.create_user(new_user)
        AuditService.log_event(self.db, "User Registration", created_user.id, ip_address)
        
        return self._serialize_user(created_user)

    def login_user(self, login_data: LoginRequest, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> dict:
        user = self.user_repo.get_user_by_email(login_data.email)
        if not user:
            AuditService.log_event(self.db, "Login Failed - Not Found", None, ip_address)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled"
            )
            
        # Check lockout
        if user.locked_until and ensure_utc(user.locked_until) > datetime.now(timezone.utc):
            AuditService.log_event(self.db, "Login Failed - Account Locked", user.id, ip_address)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is locked due to multiple failed login attempts. Try again later."
            )

        if not verify_password(login_data.password, user.password_hash):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= 5:
                user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
                AuditService.log_event(self.db, "Account Lock", user.id, ip_address)
            self.user_repo.update_user(user)
            
            AuditService.log_event(self.db, "Login Failed - Wrong Password", user.id, ip_address)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Success
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login = datetime.now(timezone.utc)
        self.user_repo.update_user(user)
        
        AuditService.log_event(self.db, "Login Success", user.id, ip_address)
        
        payload = {
            "sub": user.email,
            "id": str(user.id),
            "role": user.role.value if isinstance(user.role, Roles) else user.role,
            "name": user.name
        }
        
        access_token = create_access_token(data=payload)
        refresh_token = create_refresh_token(data={"sub": user.email, "id": str(user.id), "jti": str(uuid4())})
        
        # Store refresh token
        token_entry = RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh_token),
            device_info=user_agent,
            ip_address=ip_address,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7)
        )
        self.db.add(token_entry)
        self.db.commit()
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": self._serialize_user(user)
        }
        
    def refresh_access_token(self, refresh_token: str, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> dict:
        payload = decode_token(refresh_token, expected_type="refresh")
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        email = payload.get("sub")
        user = self.user_repo.get_user_by_email(email)
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User inactive or not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Verify token against DB
        t_hash = hash_token(refresh_token)
        token_record = self.db.query(RefreshToken).filter(RefreshToken.token_hash == t_hash).first()
        
        if not token_record or token_record.revoked or ensure_utc(token_record.expires_at) < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token is revoked or invalid",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Rotate refresh token
        token_record.revoked = True
        self.db.commit()
            
        new_payload = {
            "sub": user.email,
            "id": str(user.id),
            "role": user.role.value if isinstance(user.role, Roles) else user.role,
            "name": user.name
        }
        
        new_access_token = create_access_token(data=new_payload)
        new_refresh_token = create_refresh_token(data={"sub": user.email, "id": str(user.id), "jti": str(uuid4())})
        
        # Store new refresh token
        new_token_entry = RefreshToken(
            user_id=user.id,
            token_hash=hash_token(new_refresh_token),
            device_info=user_agent,
            ip_address=ip_address,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7)
        )
        self.db.add(new_token_entry)
        self.db.commit()
        
        AuditService.log_event(self.db, "Token Refresh", user.id, ip_address)
        
        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "user": self._serialize_user(user)
        }

    def logout_user(self, refresh_token: str, ip_address: Optional[str] = None) -> None:
        t_hash = hash_token(refresh_token)
        token_record = self.db.query(RefreshToken).filter(RefreshToken.token_hash == t_hash).first()
        
        if token_record and not token_record.revoked:
            token_record.revoked = True
            self.db.commit()
            AuditService.log_event(self.db, "Logout Success", token_record.user_id, ip_address)

    def get_current_user_by_email(self, email: str) -> dict:
        user = self.user_repo.get_user_by_email(email)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found or inactive"
            )
        return self._serialize_user(user)
