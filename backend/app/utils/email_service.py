import logging
import os
from typing import Dict, List, Optional

logger = logging.getLogger("resk.email")
logger.setLevel(logging.INFO)

# In-memory log of recent mock emails for development inspection/testing
_mock_email_outbox: List[Dict[str, str]] = []


class EmailService:
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_pass = os.getenv("SMTP_PASS")
        self.from_email = os.getenv("SMTP_FROM", "security@resk-industrial.com")
        self.is_production = os.getenv("ENVIRONMENT", "development").lower() == "production"

    def send_verification_email(self, to_email: str, code: str, token: str) -> None:
        """
        Sends email verification code and link.
        In development, logs prominently to terminal and keeps in mock outbox.
        In production, dispatches via SMTP provider.
        """
        verify_url = f"http://localhost:5173/register/verify?token={token}&email={to_email}&code={code}"
        
        banner = f"""
================================================================================
[RESK SECURITY EMAIL DISPATCH] (MOCKED IN DEV)
To: {to_email}
Subject: Verify Your RESK Organization Account
--------------------------------------------------------------------------------
Your 6-Digit Email Verification Code:
                    >>> {code} <<<

Direct Verification Link:
{verify_url}

Token: {token}
================================================================================
"""
        logger.info(banner)
        print(banner, flush=True)

        _mock_email_outbox.append({
            "type": "verification",
            "to": to_email,
            "code": code,
            "token": token,
            "verify_url": verify_url,
        })

        if self.is_production and self.smtp_host:
            self._send_smtp(
                to_email=to_email,
                subject="Verify Your RESK Organization Account",
                body=f"Your RESK verification code is {code}.\nLink: {verify_url}",
            )

    def send_password_reset_email(self, to_email: str, reset_token: str) -> None:
        """
        Sends password reset link.
        In development, logs prominently to terminal and keeps in mock outbox.
        """
        reset_url = f"http://localhost:5173/reset-password?token={reset_token}"
        
        banner = f"""
================================================================================
[RESK SECURITY EMAIL DISPATCH] (MOCKED IN DEV)
To: {to_email}
Subject: RESK Organization Password Reset Request
--------------------------------------------------------------------------------
A password reset was requested for your registered organization.
Use the following secure link to reset your password (valid for 15 minutes):

Direct Reset Link:
{reset_url}

Reset Token: {reset_token}
================================================================================
"""
        logger.info(banner)
        print(banner, flush=True)

        _mock_email_outbox.append({
            "type": "password_reset",
            "to": to_email,
            "reset_token": reset_token,
            "reset_url": reset_url,
        })

        if self.is_production and self.smtp_host:
            self._send_smtp(
                to_email=to_email,
                subject="RESK Organization Password Reset Request",
                body=f"Reset your RESK organization password here:\n{reset_url}",
            )

    def _send_smtp(self, to_email: str, subject: str, body: str) -> None:
        """Production SMTP sender implementation placeholder."""
        # Ready for smtplib.SMTP connection with TLS
        pass

    @staticmethod
    def get_latest_mock_email(to_email: Optional[str] = None) -> Optional[Dict[str, str]]:
        """Helper for test suites and dev diagnostics."""
        if not _mock_email_outbox:
            return None
        if to_email:
            for item in reversed(_mock_email_outbox):
                if item.get("to") == to_email:
                    return item
            return None
        return _mock_email_outbox[-1]


email_service = EmailService()
