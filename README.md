<<<<<<< HEAD
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
=======
# Factory Energy Optimization Platform

A full-stack reference implementation based on the provided architecture:

- **Frontend:** React + TypeScript + Tailwind CSS + Recharts + Lucide
- **Backend:** FastAPI + Pydantic
- **Analytics:** Pandas + NumPy + scikit-learn
- **Optimization:** OR-Tools CP-SAT
- **AI explanation:** Gemini-compatible REST integration with a deterministic local fallback
- **API flow:** React → FastAPI → Data/Analytics + Optimization → Impact Engine → AI Explanation

The app ships with a generated 24-hour demo factory profile so the dashboard is useful immediately, while still keeping the backend boundaries clean enough to wire to real meter/SCADA data later.

## Run backend

```bash
cd backend
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows
# .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

## Run frontend

```bash
cd frontend
npm install
npm run dev
```

Open: http://localhost:5173

Set `VITE_API_URL` when the API is hosted elsewhere. By default it points to `http://localhost:8000/api`.

## Gemini

Set `GEMINI_API_KEY` in `backend/.env`. If it is missing, the AI endpoint returns a useful deterministic explanation generated from the optimization/analytics payload rather than failing the application.

## Main endpoints

- `GET /api/health`
- `GET /api/data/overview`
- `GET /api/data/timeseries?hours=24`
- `GET /api/analytics/anomalies?hours=24`
- `GET /api/analytics/baseline?hours=24`
- `POST /api/optimization/optimize`
- `POST /api/simulation/what-if`
- `GET /api/maintenance/windows`
- `POST /api/ai/explain`
- `GET /api/impact/summary`
>>>>>>> main
