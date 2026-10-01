import os
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.organization import Organization
from backend.app.schemas.auth import (
    ForgotPasswordRequest,
    GenericMessageResponse,
    LoginRequest,
    OrganizationCreate,
    OrganizationResponse,
    RegistrationSuccessResponse,
    ResetPasswordRequest,
    SendVerificationCodeRequest,
    TokenResponse,
    VerifyEmailRequest,
)
from backend.app.services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])
security_bearer = HTTPBearer(auto_error=False)


def get_current_organization(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Organization:
    """Dependency that extracts and validates Bearer token."""
    raw_token = None
    if credentials:
        raw_token = credentials.credentials
    elif authorization and authorization.lower().startswith("bearer "):
        raw_token = authorization.split(" ")[1]

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return auth_service.get_organization_from_token(db, raw_token)


@router.post(
    "/register",
    response_model=RegistrationSuccessResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new Organization",
)
def register(org_data: OrganizationCreate, db: Session = Depends(get_db)):
    """
    Registers a new organization:
    - Validates company name, official email, industry, location, and strong password
    - Generates unique Registration ID (e.g. RESK-7F42K9)
    - Hashes password with bcrypt
    - Dispatches verification token/code
    """
    org, code, token = auth_service.register_organization(db, org_data)

    is_dev = os.getenv("ENVIRONMENT", "development").lower() != "production"

    return RegistrationSuccessResponse(
        message="Organization successfully registered. Please verify your official email.",
        registration_id=org.registration_id,
        email_verified=org.email_verified,
        verification_code_sent=not org.email_verified,
        dev_verification_code=code if is_dev and not org.email_verified else None,
    )


@router.post(
    "/register/send-code",
    response_model=GenericMessageResponse,
    summary="Send verification code for registration step 2",
)
def send_verification_code(req: SendVerificationCodeRequest, db: Session = Depends(get_db)):
    """
    Dispatches a 6-digit verification code to the company email during step 2.
    """
    code, token = auth_service.send_verification_code(db, req.official_email)
    is_dev = os.getenv("ENVIRONMENT", "development").lower() != "production"

    return GenericMessageResponse(
        message=f"Verification code sent to {req.official_email}",
        dev_token=code if is_dev else None,
    )


@router.post(
    "/verify-email",
    response_model=GenericMessageResponse,
    summary="Verify organization email address",
)
def verify_email(req: VerifyEmailRequest, db: Session = Depends(get_db)):
    """
    Verifies email address using either token link or email + 6-digit code.
    """
    if not req.token and not (req.email and req.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either verification token or email and 6-digit code must be provided.",
        )

    org, reg_id = auth_service.verify_email(db, token=req.token, email=req.email, code=req.code)

    detail_msg = f"Organization {reg_id} is now verified." if reg_id else "Email verified successfully."
    return GenericMessageResponse(
        message="Email verification successful. You can now log in using your Registration ID and password.",
        detail=detail_msg,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Sign in using Organization Registration ID and Password",
)
def login(creds: LoginRequest, db: Session = Depends(get_db)):
    """
    Normal login: MUST use Organization Registration ID + Password.
    Do NOT use email or phone for normal login.
    """
    org, access_token = auth_service.authenticate_organization(
        db,
        registration_id=creds.registration_id,
        password=creds.password,
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        organization=OrganizationResponse.model_validate(org),
    )


@router.post(
    "/forgot-password",
    response_model=GenericMessageResponse,
    summary="Request password reset using company email",
)
def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Password recovery initiated using official company email.
    Generates a secure temporary reset token.
    CRITICAL: Does not reveal whether an email exists through the API response.
    """
    dev_token = auth_service.forgot_password(db, req.company_email)
    is_dev = os.getenv("ENVIRONMENT", "development").lower() != "production"

    return GenericMessageResponse(
        message="If this email is associated with a registered organization, password recovery instructions have been dispatched.",
        dev_token=dev_token if is_dev else None,
    )


@router.post(
    "/reset-password",
    response_model=GenericMessageResponse,
    summary="Reset password using reset token and new password",
)
def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Updates the organization password using a valid temporary reset token.
    """
    auth_service.reset_password(db, reset_token=req.reset_token, new_password=req.new_password)
    return GenericMessageResponse(
        message="Password has been successfully updated. You may now sign in using your Registration ID.",
    )


@router.post(
    "/logout",
    response_model=GenericMessageResponse,
    summary="Sign out / invalidate current session",
)
def logout(current_org: Organization = Depends(get_current_organization)):
    """
    Terminates session. Client clears stored JWT token.
    """
    return GenericMessageResponse(
        message=f"Session for organization {current_org.registration_id} successfully terminated."
    )


@router.get(
    "/me",
    response_model=OrganizationResponse,
    summary="Get authenticated organization profile",
)
def get_me(current_org: Organization = Depends(get_current_organization)):
    """
    Protected route returning authenticated organization information.
    """
    return OrganizationResponse.model_validate(current_org)
