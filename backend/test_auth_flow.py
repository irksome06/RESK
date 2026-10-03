"""
Unit & Integration Test Suite for RESK Authentication API.
Validates:
1. Organization registration (generates unique RESK-XXXXXX ID, hashes password, saves unverified)
2. Duplicate company email prevention
3. Email verification flow
4. Attempted login before verification (blocked with 403)
5. Normal login with Registration ID + Password
6. Invalid credentials handling (401)
7. Protected GET /auth/me
8. Forgot password request (no user leak)
9. Reset password with token
10. Login with new password
"""

import os
import sys

# Ensure backend package is in python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from fastapi.testclient import TestClient
from backend.app.database import Base, engine, SessionLocal
from backend.app.main import app
from backend.app.utils.email_service import email_service

client = TestClient(app)

def run_tests():
    print("\n==================== STARTING RESK AUTH TEST SUITE ====================")
    # Ensure fresh DB tables
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    test_company = {
        "organization_name": "AeroDynamics Heavy Industries",
        "official_email": "ops@aerodynamics-industrial.com",
        "industry": "Aerospace & Defense",
        "location": "Stuttgart, Germany",
        "password": "SecurePassword#2025",
        "confirm_password": "SecurePassword#2025",
    }

    # 1. Register organization
    print("\n[TEST 1] POST /auth/register...")
    resp = client.post("/auth/register", json=test_company)
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
    reg_data = resp.json()
    reg_id = reg_data["registration_id"]
    print(f"  -> Success! Generated Registration ID: {reg_id}")
    assert reg_id.startswith("RESK-"), f"Registration ID should start with RESK-, got {reg_id}"
    assert len(reg_id) == 11, f"Expected 11 chars (RESK-XXXXXX), got {len(reg_id)}"
    assert reg_data["email_verified"] is False, "Should be unverified initially"

    # Get verification code from mock email service
    latest_email = email_service.get_latest_mock_email(test_company["official_email"])
    assert latest_email is not None, "Mock email should have been recorded"
    verify_code = latest_email["code"]
    verify_token = latest_email["token"]
    print(f"  -> Captured Mock Verification Code: {verify_code}, Token: {verify_token[:8]}...")

    # 2. Test duplicate registration prevention
    print("\n[TEST 2] Duplicate company email rejection...")
    dup_resp = client.post("/auth/register", json=test_company)
    assert dup_resp.status_code == 400, f"Expected 400 for duplicate, got {dup_resp.status_code}"
    print("  -> Success! Duplicate registration was properly rejected.")

    # 3. Test login BEFORE email verification (must be forbidden)
    print("\n[TEST 3] Login attempt before email verification...")
    unverified_login = client.post("/auth/login", json={
        "registration_id": reg_id,
        "password": test_company["password"]
    })
    assert unverified_login.status_code == 403, f"Expected 403, got {unverified_login.status_code}"
    print("  -> Success! Unverified login blocked with 403 Forbidden.")

    # 4. Test email verification with code
    print("\n[TEST 4] POST /auth/verify-email...")
    verify_resp = client.post("/auth/verify-email", json={
        "email": test_company["official_email"],
        "code": verify_code
    })
    assert verify_resp.status_code == 200, f"Expected 200, got {verify_resp.status_code}: {verify_resp.text}"
    print("  -> Success! Email verified successfully.")

    # 5. Normal login with Registration ID + Password
    print("\n[TEST 5] Normal login with Registration ID + Password...")
    login_resp = client.post("/auth/login", json={
        "registration_id": reg_id,
        "password": test_company["password"]
    })
    assert login_resp.status_code == 200, f"Expected 200, got {login_resp.status_code}: {login_resp.text}"
    login_data = login_resp.json()
    assert "access_token" in login_data
    access_token = login_data["access_token"]
    assert login_data["organization"]["registration_id"] == reg_id
    assert login_data["organization"]["email_verified"] is True
    print(f"  -> Success! Authenticated token received: {access_token[:16]}...")

    # 6. Test invalid login credentials
    print("\n[TEST 6] Invalid credentials rejection...")
    bad_login = client.post("/auth/login", json={
        "registration_id": reg_id,
        "password": "WrongPassword999!"
    })
    assert bad_login.status_code == 401, f"Expected 401, got {bad_login.status_code}"
    print("  -> Success! Bad password rejected with 401 Unauthorized.")

    # 7. Test protected route GET /auth/me
    print("\n[TEST 7] GET /auth/me with Bearer token...")
    me_resp = client.get("/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert me_resp.status_code == 200, f"Expected 200, got {me_resp.status_code}: {me_resp.text}"
    me_data = me_resp.json()
    assert me_data["registration_id"] == reg_id
    assert me_data["organization_name"] == test_company["organization_name"]
    print(f"  -> Success! Retrieved profile: {me_data['organization_name']} ({me_data['registration_id']})")

    # 8. Test forgot password flow
    print("\n[TEST 8] POST /auth/forgot-password...")
    forgot_resp = client.post("/auth/forgot-password", json={
        "company_email": test_company["official_email"]
    })
    assert forgot_resp.status_code == 200
    # Also test unknown email doesn't leak existence
    unknown_forgot = client.post("/auth/forgot-password", json={
        "company_email": "unknown-nonexistent@example.com"
    })
    assert unknown_forgot.status_code == 200
    assert unknown_forgot.json()["message"] == forgot_resp.json()["message"]
    print("  -> Success! Generic response returned without revealing email existence.")

    # Get reset token from mock email service
    reset_email = email_service.get_latest_mock_email(test_company["official_email"])
    assert reset_email is not None and reset_email["type"] == "password_reset"
    reset_token = reset_email["reset_token"]
    print(f"  -> Captured Reset Token: {reset_token[:8]}...")

    # 9. Test password reset
    print("\n[TEST 9] POST /auth/reset-password...")
    new_password = "BrandNewPassword#2026"
    reset_resp = client.post("/auth/reset-password", json={
        "reset_token": reset_token,
        "new_password": new_password,
        "confirm_password": new_password
    })
    assert reset_resp.status_code == 200, f"Expected 200, got {reset_resp.status_code}: {reset_resp.text}"
    print("  -> Success! Password reset succeeded.")

    # 10. Login with new password
    print("\n[TEST 10] Login with Registration ID + new password...")
    new_login_resp = client.post("/auth/login", json={
        "registration_id": reg_id,
        "password": new_password
    })
    assert new_login_resp.status_code == 200, f"Expected 200, got {new_login_resp.status_code}: {new_login_resp.text}"
    print("  -> Success! Successfully logged in with newly reset password.")

    # Old password should now fail
    old_login_resp = client.post("/auth/login", json={
        "registration_id": reg_id,
        "password": test_company["password"]
    })
    assert old_login_resp.status_code == 401
    print("  -> Success! Old password is no longer valid.")

    print("\n==================== ALL 10 AUTH TESTS PASSED! ====================\n")

if __name__ == "__main__":
    run_tests()
