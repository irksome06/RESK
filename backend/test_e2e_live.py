"""
Live HTTP End-to-End Test for RESK Authentication API on http://127.0.0.1:8000.
"""

import httpx

BASE_URL = "http://127.0.0.1:8000"

def test_live_auth_flow():
    client = httpx.Client(base_url=BASE_URL, timeout=10.0)

    print("\n--- [1] Health Check ---")
    resp = client.get("/health")
    assert resp.status_code == 200
    print(f"Server health: {resp.json()}")

    print("\n--- [2] Pre-Verification Code Dispatch ---")
    email = "security@quantum-defense-corp.com"
    send_resp = client.post("/auth/register/send-code", json={"official_email": email})
    assert send_resp.status_code == 200
    code = send_resp.json().get("dev_token")
    print(f"Code dispatched to {email}: {code}")

    print("\n--- [3] Registration ---")
    org_payload = {
        "organization_name": "Quantum Defense Systems",
        "official_email": email,
        "industry": "Cybersecurity & Infrastructure",
        "location": "Arlington, VA",
        "password": "DefenseSecure#2026",
        "confirm_password": "DefenseSecure#2026",
        "verification_code": code,
    }
    reg_resp = client.post("/auth/register", json=org_payload)
    assert reg_resp.status_code == 201, f"Reg failed: {reg_resp.text}"
    reg_data = reg_resp.json()
    reg_id = reg_data["registration_id"]
    print(f"Registered Successfully! Registration ID: {reg_id}")
    assert reg_id.startswith("RESK-")

    print("\n--- [4] Duplicate Registration Rejection ---")
    dup_resp = client.post("/auth/register", json=org_payload)
    assert dup_resp.status_code == 400
    print("Duplicate company email blocked properly (HTTP 400)")

    print("\n--- [5] Normal Login with Registration ID + Password ---")
    login_resp = client.post("/auth/login", json={
        "registration_id": reg_id,
        "password": "DefenseSecure#2026"
    })
    assert login_resp.status_code == 200
    token_data = login_resp.json()
    token = token_data["access_token"]
    print(f"Login Successful! Bearer Token received: {token[:20]}...")

    print("\n--- [6] Normal Login using Email MUST Fail ---")
    email_login = client.post("/auth/login", json={
        "registration_id": email,
        "password": "DefenseSecure#2026"
    })
    assert email_login.status_code == 401
    print("Attempting login with email rejected properly (401)")

    print("\n--- [7] Invalid Password Rejection ---")
    bad_pass = client.post("/auth/login", json={
        "registration_id": reg_id,
        "password": "IncorrectPassword!123"
    })
    assert bad_pass.status_code == 401
    print("Invalid password rejected properly (401)")

    print("\n--- [8] Protected GET /auth/me ---")
    me_resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    print(f"Authenticated Org Info: {me_data['organization_name']} ({me_data['registration_id']})")
    assert me_data["registration_id"] == reg_id

    print("\n--- [9] Protected Route Without Token Rejected ---")
    unauth_resp = client.get("/auth/me")
    assert unauth_resp.status_code == 401
    print("Protected route properly rejected unauthorized request (401)")

    print("\n--- [10] Forgot Password Request ---")
    forgot_resp = client.post("/auth/forgot-password", json={"company_email": email})
    assert forgot_resp.status_code == 200
    reset_token = forgot_resp.json().get("dev_token")
    print(f"Forgot password dispatched. Dev token: {reset_token[:12]}...")

    print("\n--- [11] Reset Password with Token ---")
    new_password = "NewIndustrialKey#2026"
    reset_resp = client.post("/auth/reset-password", json={
        "reset_token": reset_token,
        "new_password": new_password,
        "confirm_password": new_password
    })
    assert reset_resp.status_code == 200
    print("Password reset successful (HTTP 200)")

    print("\n--- [12] Re-using Expired/Used Reset Token Fails ---")
    reused_reset = client.post("/auth/reset-password", json={
        "reset_token": reset_token,
        "new_password": "AnotherPassword#2026",
        "confirm_password": "AnotherPassword#2026"
    })
    assert reused_reset.status_code == 400
    print("Re-used reset token rejected properly (400)")

    print("\n--- [13] Login with Registration ID + New Password ---")
    new_login = client.post("/auth/login", json={
        "registration_id": reg_id,
        "password": new_password
    })
    assert new_login.status_code == 200
    print("Logged in with updated credentials successfully!")

    print("\n--- [14] Old Password Fails ---")
    old_login = client.post("/auth/login", json={
        "registration_id": reg_id,
        "password": "DefenseSecure#2026"
    })
    assert old_login.status_code == 401
    print("Old password no longer valid (401)")

    print("\n--- [15] Logout ---")
    logout_resp = client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout_resp.status_code == 200
    print(f"Session terminated: {logout_resp.json()['message']}")

    print("\n==================== ALL 15 LIVE E2E TESTS PASSED ====================\n")

if __name__ == "__main__":
    test_live_auth_flow()
