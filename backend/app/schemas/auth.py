import re
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


class OrganizationBase(BaseModel):
    organization_name: str = Field(..., min_length=2, max_length=255, description="Official company or organization name")
    official_email: EmailStr = Field(..., description="Official enterprise email address")
    industry: str = Field(..., min_length=2, max_length=100, description="Industry sector")
    location: str = Field(..., min_length=2, max_length=100, description="Headquarters or operating location")


class OrganizationCreate(OrganizationBase):
    password: str = Field(..., min_length=8, max_length=128, description="Strong master password")
    confirm_password: Optional[str] = Field(None, description="Password confirmation")
    verification_code: Optional[str] = Field(None, description="Optional verification code if verified during wizard")

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter (A-Z)")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter (a-z)")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one numeric digit (0-9)")
        if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", v):
            raise ValueError("Password must contain at least one special character")
        return v

    @field_validator("confirm_password")
    @classmethod
    def validate_passwords_match(cls, v: Optional[str], values) -> Optional[str]:
        # Only validate if confirm_password was passed
        if v is not None and "password" in values.data and v != values.data["password"]:
            raise ValueError("Passwords do not match")
        return v


class SendVerificationCodeRequest(BaseModel):
    official_email: EmailStr


class VerifyEmailRequest(BaseModel):
    token: Optional[str] = None
    email: Optional[EmailStr] = None
    code: Optional[str] = None


class LoginRequest(BaseModel):
    registration_id: str = Field(..., description="Organization Registration ID (format: RESK-XXXXXX)")
    password: str = Field(..., description="Master password")

    @field_validator("registration_id")
    @classmethod
    def format_registration_id(cls, v: str) -> str:
        cleaned = v.strip().upper()
        if not cleaned:
            raise ValueError("Registration ID is required")
        return cleaned


class ForgotPasswordRequest(BaseModel):
    company_email: EmailStr = Field(..., description="Official registered company email")


class ResetPasswordRequest(BaseModel):
    reset_token: str = Field(..., min_length=10, description="Password reset token")
    new_password: str = Field(..., min_length=8, max_length=128, description="New strong password")
    confirm_password: Optional[str] = None

    @field_validator("new_password")
    @classmethod
    def validate_new_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter (A-Z)")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter (a-z)")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one numeric digit (0-9)")
        if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", v):
            raise ValueError("Password must contain at least one special character")
        return v

    @field_validator("confirm_password")
    @classmethod
    def validate_reset_passwords_match(cls, v: Optional[str], values) -> Optional[str]:
        if v is not None and "new_password" in values.data and v != values.data["new_password"]:
            raise ValueError("Passwords do not match")
        return v


class OrganizationResponse(BaseModel):
    organization_id: str
    registration_id: str
    organization_name: str
    official_email: str
    industry: str
    location: str
    email_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class RegistrationSuccessResponse(BaseModel):
    message: str
    registration_id: str
    email_verified: bool
    verification_code_sent: bool
    dev_verification_code: Optional[str] = None  # Helper for development


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    organization: OrganizationResponse


class GenericMessageResponse(BaseModel):
    message: str
    detail: Optional[str] = None
    dev_token: Optional[str] = None  # Helper for testing forgot-password flow in dev
