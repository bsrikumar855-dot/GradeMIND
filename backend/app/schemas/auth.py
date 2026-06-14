from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from uuid import UUID
from typing import Optional
import re

class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Full name of the user")
    email: EmailStr = Field(..., description="Unique email address of the user")
    password: str = Field(..., min_length=8, max_length=128, description="Plaintext password, minimum 8 characters")
    role: Optional[str] = Field(None, description="Optional role of the user (e.g. teacher, student)")

    @field_validator('email')
    @classmethod
    def email_to_lower(cls, v: str) -> str:
        return v.lower()

    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")
        if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", v):
            raise ValueError("Password must contain at least one special character")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Jane Doe",
                "email": "jane.doe@example.com",
                "password": "Password123!"
            }
        }
    )

class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="Refresh token")


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="Plaintext password")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "jane.doe@example.com",
                "password": "secret_password_123"
            }
        }
    )


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type, typically 'bearer'")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer"
            }
        }
    )


class UserResponse(BaseModel):
    id: UUID = Field(..., description="Unique user identifier")
    name: str = Field(..., description="User's full name")
    email: EmailStr = Field(..., description="User's email address")
    role: str = Field(..., description="User's system role (e.g. admin, teacher, student)")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Jane Doe",
                "email": "jane.doe@example.com",
                "role": "TEACHER"
            }
        }
    )
