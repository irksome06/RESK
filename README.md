# RESK — Enterprise Organization Access & Identity Management System

A dark industrial-tech organization authentication and identity system built with **FastAPI** (Python) and **React + Vite + Tailwind CSS**.

---

## Architecture & Authentication Rules

### The Identity Flow:

```
REGISTRATION:
Company Email
        ↓
Email Verification
        ↓
Password
        ↓
Generate Registration ID
        ↓
RESK-XXXXXX

NORMAL LOGIN:
Registration ID + Password
(Official email is NOT an accepted normal login identifier)

PASSWORD RECOVERY:
Company Email
        ↓
Reset Link/Token
        ↓
New Password
```

---

## Project Structure

```
RESK/
├── backend/
│   ├── app/
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── organization.py       # Organization, EmailVerificationToken, PasswordResetToken
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   └── auth.py               # Pydantic validation schemas
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   └── auth_service.py       # Business logic for registration, auth, recovery
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   └── auth.py               # API endpoints
│   │   ├── utils/
│   │   │   ├── __init__.py
│   │   │   ├── security.py           # Bcrypt password hashing, JWT, ID generation
│   │   │   └── email_service.py      # Structured email dispatch (mock/SMTP)
│   │   ├── database.py               # SQLAlchemy engine and session
│   │   └── main.py                   # FastAPI app entrypoint & CORS
│   ├── requirements.txt              # Backend dependencies
│   ├── test_auth_flow.py             # Unit & integration test suite
│   ├── test_e2e_live.py              # Live HTTP end-to-end test suite
│   ├── .env.example
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Navbar.jsx            # Top navigation & system status
│   │   │   ├── Footer.jsx            # Industrial defense footer
│   │   │   ├── ProtectedRoute.jsx    # Guard for authenticated routes
│   │   │   ├── PasswordInput.jsx     # Show/hide password toggle
│   │   │   └── PasswordStrengthIndicator.jsx # Live complexity checklist
│   │   ├── context/
│   │   │   └── AuthContext.jsx       # Auth provider & state management
│   │   ├── pages/
│   │   │   ├── LoginPage.jsx         # /login
│   │   │   ├── RegisterPage.jsx      # /register (3-step wizard)
│   │   │   ├── RegisterVerifyPage.jsx# /register/verify
│   │   │   ├── RegisterSuccessPage.jsx# /register/success (Copy ID)
│   │   │   ├── ForgotPasswordPage.jsx# /forgot-password
│   │   │   ├── ResetPasswordPage.jsx # /reset-password
│   │   │   └── DashboardPage.jsx     # /dashboard (Protected)
│   │   ├── services/
│   │   │   └── api.js                # API client with token interceptor
│   │   ├── App.jsx                   # React Router configuration
│   │   ├── index.css                 # Industrial dark tech styling
│   │   └── main.jsx
│   ├── public/
│   │   └── shield.svg                # Industrial SVG icon
│   ├── .env.example
│   ├── .env
│   ├── package.json
│   └── vite.config.js
├── MACHINE_HEALTH/
│   ├── data/                 # Evaluation and sample vibration test datasets
│   ├── notebooks/            # Bearing health ML development notebook
│   ├── outputs/              # Diagnostic EDA figures, evaluation plots, and audit reports
│   │   ├── eda/
│   │   ├── evaluation/
│   │   ├── models/           # Pretrained Isolation Forest pipeline (1.99 MB)
│   │   └── reports/
│   ├── scripts/              # Independent test and verification harness
│   ├── requirements.txt      # Module Python dependencies
│   ├── .gitignore
│   └── README.md             # Machine Health module documentation
├── .gitignore
└── README.md
```

---

## Frontend Routes

| Route | Description |
|---|---|
| `/login` | Primary login portal using **Organization Registration ID + Password** |
| `/register` | 3-step organization registration wizard (Profile, Verify Email, Password) |
| `/register/verify` | Standalone email verification page (supports query params or code) |
| `/register/success` | Success screen displaying generated `RESK-XXXXXX` ID with Copy button |
| `/forgot-password` | Password recovery via registered company email |
| `/reset-password` | Set new password using secure temporary reset token |
| `/dashboard` | Protected facility overview displaying organization profile & telemetry |

---

## Backend API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/auth/register` | Validates input, generates `RESK-XXXXXX`, hashes password, stores org |
| `POST` | `/auth/register/send-code` | Dispatches 6-digit verification code to official company email |
| `POST` | `/auth/verify-email` | Verifies email via token or email + 6-digit code |
| `POST` | `/auth/login` | Normal login using `registration_id` + `password` (Returns JWT) |
| `POST` | `/auth/forgot-password` | Dispatches reset token (Does not reveal if email exists) |
| `POST` | `/auth/reset-password` | Updates password using valid reset token |
| `POST` | `/auth/logout` | Terminates active session / token invalidation |
| `GET` | `/auth/me` | Protected route returning authenticated organization details |
| `GET` | `/health` | Backend health check |

---

## How to Run the Backend

1. Navigate to `backend/`:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the server:
   ```bash
   uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
5. Interactive API Documentation:
   - Swagger UI: `http://localhost:8000/docs`
   - ReDoc: `http://localhost:8000/redoc`

---

## How to Run the Frontend

1. Navigate to `frontend/`:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```
4. Open your browser at `http://localhost:5173`.

---

## Mocked Email Functionality

In development mode (`ENVIRONMENT=development`):
- Email dispatches (verification codes and password reset links) are prominently logged to the server terminal with clear ASCII banners.
- Verification codes and reset tokens are also recorded in an in-memory queue and surfaced in development responses for seamless manual and automated testing.
- The `EmailService` is pre-architected with SMTP configuration hooks (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`) to enable live SMTP delivery when configured in production.
