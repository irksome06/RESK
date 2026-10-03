from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.models.organization import (
    Organization,
    EmailVerificationToken,
    PasswordResetToken,
    utc_now,
)
from backend.app.schemas.auth import OrganizationCreate
from backend.app.utils.email_service import email_service
from backend.app.utils.security import (
    hash_password,
    verify_password,
    generate_registration_id,
    generate_verification_code,
    generate_secure_token,
    create_access_token,
    decode_access_token,
)


class AuthService:
    @staticmethod
    def register_organization(db: Session, org_in: OrganizationCreate) -> Tuple[Organization, str, str]:
        """
        Validates input, checks for duplicate email, generates unique Registration ID,
        hashes password, creates organization, and dispatches email verification token.
        """
        # Check duplicate official email
        existing = db.query(Organization).filter(
            Organization.official_email == org_in.official_email.lower().strip()
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An organization with this official email address is already registered.",
            )

        # Generate unique Registration ID
        max_attempts = 10
        registration_id = None
        for _ in range(max_attempts):
            candidate_id = generate_registration_id()
            if not db.query(Organization).filter(Organization.registration_id == candidate_id).first():
                registration_id = candidate_id
                break

        if not registration_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate a unique Registration ID. Please retry.",
            )

        # Hash password securely
        password_hash = hash_password(org_in.password)

        # Check if pre-verified code was supplied
        is_already_verified = False
        if org_in.verification_code:
            valid_token = db.query(EmailVerificationToken).filter(
                EmailVerificationToken.email == org_in.official_email.lower().strip(),
                EmailVerificationToken.code == org_in.verification_code.strip(),
                EmailVerificationToken.used == False,
                EmailVerificationToken.expires_at > utc_now(),
            ).first()
            if valid_token:
                valid_token.used = True
                is_already_verified = True

        new_org = Organization(
            registration_id=registration_id,
            organization_name=org_in.organization_name.strip(),
            official_email=org_in.official_email.lower().strip(),
            industry=org_in.industry.strip(),
            location=org_in.location.strip(),
            password_hash=password_hash,
            email_verified=is_already_verified,
        )
        db.add(new_org)
        db.flush()

        # Generate verification token & code
        code = generate_verification_code()
        token = generate_secure_token(32)
        verification_record = EmailVerificationToken(
            email=new_org.official_email,
            token=token,
            code=code,
            expires_at=utc_now() + timedelta(hours=24),
            used=is_already_verified,
        )
        db.add(verification_record)
        db.commit()
        db.refresh(new_org)

        if not is_already_verified:
            email_service.send_verification_email(new_org.official_email, code, token)

        return new_org, code, token

    @staticmethod
    def send_verification_code(db: Session, email: str) -> Tuple[str, str]:
        """
        Generates and sends an email verification code for registration step 2.
        """
        normalized_email = email.lower().strip()

        # Check if already registered and verified
        existing_org = db.query(Organization).filter(
            Organization.official_email == normalized_email
        ).first()
        if existing_org and existing_org.email_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This email address is already registered and verified.",
            )

        code = generate_verification_code()
        token = generate_secure_token(32)
        verification_record = EmailVerificationToken(
            email=normalized_email,
            token=token,
            code=code,
            expires_at=utc_now() + timedelta(minutes=30),
            used=False,
        )
        db.add(verification_record)
        db.commit()

        email_service.send_verification_email(normalized_email, code, token)
        return code, token

    @staticmethod
    def verify_email(
        db: Session,
        token: Optional[str] = None,
        email: Optional[str] = None,
        code: Optional[str] = None,
    ) -> Tuple[Organization, str]:
        """
        Verifies organization email via either token or email+code.
        """
        query = db.query(EmailVerificationToken).filter(
            EmailVerificationToken.used == False,
            EmailVerificationToken.expires_at > utc_now(),
        )

        matched_record: Optional[EmailVerificationToken] = None

        if token:
            matched_record = query.filter(EmailVerificationToken.token == token.strip()).first()
        elif email and code:
            matched_record = query.filter(
                EmailVerificationToken.email == email.lower().strip(),
                EmailVerificationToken.code == code.strip(),
            ).first()

        if not matched_record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid, expired, or previously used verification code or token.",
            )

        matched_record.used = True

        # Find associated organization if registered
        org = db.query(Organization).filter(
            Organization.official_email == matched_record.email
        ).first()

        if org:
            org.email_verified = True
            db.commit()
            db.refresh(org)
            return org, org.registration_id

        db.commit()
        return None, ""

    @staticmethod
    def authenticate_organization(db: Session, registration_id: str, password: str) -> Tuple[Organization, str]:
        """
        Normal Login MUST use: Organization Registration ID + Password.
        Verifies credentials, checks email verification status, and produces JWT access token.
        """
        cleaned_reg_id = registration_id.strip().upper()
        org = db.query(Organization).filter(Organization.registration_id == cleaned_reg_id).first()

        if not org or not verify_password(password, org.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Organization Registration ID or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not org.email_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your organization email is not yet verified. Please verify your email before signing in.",
            )

        token_payload = {
            "sub": org.organization_id,
            "reg_id": org.registration_id,
            "name": org.organization_name,
        }
        access_token = create_access_token(data=token_payload)

        return org, access_token

    @staticmethod
    def forgot_password(db: Session, company_email: str) -> Optional[str]:
        """
        Generates secure temporary reset token.
        CRITICAL: Does not reveal whether an email exists through the API response.
        """
        normalized_email = company_email.lower().strip()
        org = db.query(Organization).filter(Organization.official_email == normalized_email).first()

        dev_token = None
        if org:
            reset_token = generate_secure_token(32)
            reset_record = PasswordResetToken(
                organization_id=org.organization_id,
                token=reset_token,
                expires_at=utc_now() + timedelta(minutes=15),
                used=False,
            )
            db.add(reset_record)
            db.commit()

            email_service.send_password_reset_email(org.official_email, reset_token)
            dev_token = reset_token

        return dev_token

    @staticmethod
    def reset_password(db: Session, reset_token: str, new_password: str) -> None:
        """
        Validates reset token and updates password securely.
        """
        reset_record = db.query(PasswordResetToken).filter(
            PasswordResetToken.token == reset_token.strip(),
            PasswordResetToken.used == False,
            PasswordResetToken.expires_at > utc_now(),
        ).first()

        if not reset_record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The password reset link is invalid, has expired, or has already been used.",
            )

        org = db.query(Organization).filter(
            Organization.organization_id == reset_record.organization_id
        ).first()

        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Associated organization not found.",
            )

        org.password_hash = hash_password(new_password)
        reset_record.used = True
        db.commit()

    @staticmethod
    def get_organization_from_token(db: Session, token: str) -> Organization:
        """
        Decodes JWT token and retrieves active organization.
        """
        payload = decode_access_token(token)
        if not payload or "sub" not in payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication session.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        org = db.query(Organization).filter(
            Organization.organization_id == payload["sub"]
        ).first()

        if not org:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Organization no longer exists.",
            )

        return org


auth_service = AuthService()
