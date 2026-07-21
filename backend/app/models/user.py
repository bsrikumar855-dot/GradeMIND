from sqlalchemy import Column, String, DateTime, Boolean, Enum, Integer
from sqlalchemy.sql import func
import uuid
from app.core.database import Base, GUID
from app.utils.roles import Roles


class User(Base):
    """
    SQLAlchemy model blueprint for User.
    Defines the database schema for the user table.
    """
    __tablename__ = "users"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(Roles, name="user_roles"), nullable=False, default=Roles.STUDENT)
    
    # Account Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # Audit & Security
    last_login = Column(DateTime(timezone=True), nullable=True)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=True,
        onupdate=func.now()
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)
