# RESK — Energy Intelligence & Optimization Platform

RESK is an industrial energy intelligence platform designed to help organizations monitor, analyze, and optimize energy consumption while maintaining operational and production efficiency. The platform focuses on turning energy and operational data into actionable decisions for reducing energy waste, operational costs, and unnecessary machine usage.

---

## Why RESK

Industrial facilities face volatile energy tariffs, strict operating caps, and complex machinery maintenance schedules. RESK addresses these challenges by enabling organizations to:

- **Reduce energy waste**: Identify baselines, anomalies, and consumption leaks across factory assets.
- **Lower operational costs**: Shift flexible workloads away from peak-tariff windows to reduce peak demand charges.
- **Improve equipment utilization**: Monitor active vs. idle machine cycles to balance workloads.
- **Coordinate maintenance and production**: Align predictive maintenance schedules with low-impact operating windows.
- **Make data-driven energy decisions**: Replace rule-of-thumb guesswork with telemetry analytics and machine learning insights.
- **Improve overall operational efficiency**: Deliver clear, actionable operational recommendations through a centralized dashboard.

---

## Core Capabilities

### 1. Energy Optimization
- Monitor real-time and historical power consumption across plant machinery.
- Detect inefficient consumption patterns, phase imbalances, and load spikes.
- Analyze Specific Energy Consumption (SEC) per production cycle.
- Deliver automated recommendations for energy-efficient production schedules.

### 2. Maintenance Scheduling
- Continuously track machine health indicators (vibration telemetry, temperature, bearing degradation).
- Support preventive and predictive maintenance planning before catastrophic failures occur.
- Reduce unplanned downtime through automated early-warning alerts.
- Coordinate scheduled maintenance windows with low-demand production periods.

### 3. Priority Settlement
- Prioritize high-value production jobs and mission-critical assets.
- Evaluate operational constraints, energy limits, and delivery deadlines concurrently.
- Support intelligent load shedding and workload distribution when operating near plant energy caps.

### 4. Machine Sleep Mode
- Identify machinery and auxiliary equipment operating in unproductive idle states.
- Recommend and trigger energy-saving low-power or sleep states during operational gaps.
- Eliminate parasitic baseline energy drain during shift changes, breaks, and staging periods.

### 5. Analytics & Decision Support
- Compute plant-wide energy efficiency metrics, load profiles, and deviation benchmarks.
- Provide actionable operational insights backed by statistical and machine learning models.
- Generate impact-aware optimization recommendations with estimated cost savings and ROI.
- Support what-if scenario simulations to evaluate the impact of shifting operating parameters.

### 6. Centralized Dashboard
The RESK Dashboard serves as the unified operational control surface for:
- Real-time and historical energy telemetry monitoring.
- Machine health and operational status tracking.
- Interactive anomaly and deviation feeds.
- Prioritized optimization recommendations.
- Upcoming maintenance windows and asset health scores.
- Key Performance Indicators (peak load, average load, energy cost, active asset counts).

---

## High-Level Architecture

```
         Organization / Facility Data (Sensors, Machinery, Telemetry)
                                      ↓
                         Data Processing & Analytics
             (Feature Engineering, Baseline Models, Ingestion)
                                      ↓
                      Energy + Operational Intelligence
            (Deviation Analysis, Machine Health, Anomaly Detection)
                                      ↓
                          Optimization & Scheduling
            (Load Shifting, Priority Settlement, Sleep Mode Engine)
                                      ↓
                          Recommendations / Actions
             (Cost Reduction, Alert Feeds, Preventive Actions)
                                      ↓
                               RESK Dashboard
                  (Unified Control, Analytics & Monitoring)
```

---

## Feature Matrix

| Feature | Purpose |
| :--- | :--- |
| **Energy Optimization** | Tracks power metrics, identifies consumption waste, and generates energy-reduction recommendations. |
| **Maintenance Scheduling** | Evaluates vibration/telemetry data to schedule predictive maintenance and prevent unexpected outages. |
| **Priority Settlement** | Schedules critical production batches against energy tariff constraints and plant operating caps. |
| **Machine Sleep Mode** | Detects idle assets and provides recommendations for low-power sleep modes to cut standby energy draw. |
| **Analytics & Decision Support** | Provides statistical baselines, anomaly detection, impact forecasting, and scenario evaluations. |
| **Dashboard** | Serves as the central interface for real-time telemetry, KPI metrics, maintenance alerts, and system health. |
| **Organization Authentication** | Ensures secure, enterprise-grade access control via verified company identity and isolated organization IDs. |

---

## Organization Authentication Flow

Access to the RESK platform is governed by an enterprise-grade organization authentication model:

```
[Organization Registration]
       │ Provide Company Name, Official Work Email, Industry Type
       ▼
[Official Email Verification]
       │ 6-Digit Secure Verification Code sent to Company Domain
       ▼
[Password Setup & Security Policy]
       │ Enforces length, character complexity, and strength indicators
       ▼
[RESK Organization ID Generation]
       │ Unique enterprise identifier generated (format: RESK-XXXXXX)
       ▼
[Authenticated Login]
       │ Login via RESK Organization ID + Password (JWT bearer token issued)
       ▼
[Protected Dashboard Session]
```

### Password Recovery & Session Management
- **Password Recovery**: Dispatches secure, time-limited password reset tokens via email without leaking organizational existence (`/auth/forgot-password` and `/auth/reset-password`).
- **Session Protection**: All protected API endpoints validate standard Bearer JWT tokens; frontend routes are guarded by `<ProtectedRoute>` wrappers.

---

## Technology Stack

Technologies verified and present in this repository:

### Frontend
- **Framework & Runtime**: React 19 (`react`, `react-dom`)
- **Build Tool**: Vite 8 (`vite`, `@vitejs/plugin-react`)
- **Routing**: React Router v7 (`react-router-dom`)
- **Styling**: Tailwind CSS v4 (`tailwindcss`, `@tailwindcss/vite`) + Custom Industrial Dark Theme CSS
- **Iconography**: Lucide React (`lucide-react`)
- **Linter**: Oxlint (`oxlint`)

### Backend
- **Framework**: FastAPI (Python 3.10+)
- **ASGI Server**: Uvicorn (`uvicorn[standard]`)
- **Data Validation & Settings**: Pydantic v2 (`pydantic`, `pydantic-settings`)
- **Security & Cryptography**: PyJWT (`pyjwt`), Bcrypt (`bcrypt`), Passlib
- **HTTP Client**: HTTPX (`httpx`)
- **Form Handling**: Python-Multipart (`python-multipart`)
- **Email Validation**: Email-Validator (`email-validator`)

### Database
- **Primary Relational Store**: SQLite (`resk.db` for local development)
- **Production Relational Store**: PostgreSQL (supported via `psycopg2-binary` and Docker Compose)
- **ORM & Migrations**: SQLAlchemy 2.0 (`sqlalchemy`)

### Analytics & Machine Learning
- **Machine Learning & Modeling**: Scikit-Learn (`scikit-learn`), XGBoost (`xgboost`)
- **Scientific Computing**: NumPy (`numpy`), Pandas (`pandas`)
- **Model Persistence**: Joblib (`joblib`)
- **Exploratory Data Analysis**: Jupyter Notebooks (`machine_health/*.ipynb`)

### Visualization
- **Auxiliary Intelligence Dashboard**: Streamlit (`streamlit` in `Energy_Intelligence/dashboard/app.py`)
- **Interactive Visualizations**: Plotly (`plotly`)
- **Diagnostic Plotting**: Matplotlib & Seaborn (`machine_health/outputs/eda/`)

### Infrastructure & Messaging
- **Containerization**: Docker Compose (`Energy_Intelligence/docker-compose.yml`)
- **Message Broker**: Eclipse Mosquitto MQTT (`eclipse-mosquitto:2.0`, `paho-mqtt`)

---

## Project Structure

```
RESK/
├── backend/                       # Authentication & Core API Service
│   ├── app/
│   │   ├── models/                # SQLAlchemy database models (Organization, Tokens)
│   │   ├── schemas/               # Pydantic validation schemas
│   │   ├── services/              # Authentication and verification business logic
│   │   ├── routes/                # FastAPI router endpoints (/auth/*)
│   │   ├── utils/                 # Security, JWT tokens, bcrypt, email service
│   │   ├── database.py            # Database engine and session configuration
│   │   └── main.py                # FastAPI application entrypoint & CORS middleware
│   ├── requirements.txt           # Backend Python dependencies
│   ├── test_auth_flow.py          # Unit & integration tests for auth
│   ├── test_e2e_live.py           # Live end-to-end HTTP tests
│   └── .env.example               # Backend environment template
├── frontend/                      # User Interface Application
│   ├── src/
│   │   ├── components/            # UI components (Navbar, Footer, ProtectedRoute, forms)
│   │   ├── context/               # React Context providers (AuthContext)
│   │   ├── pages/                 # Route pages (Login, Register, Dashboard, Recovery)
│   │   ├── services/              # API client with JWT interceptor (api.js)
│   │   ├── App.jsx                # React Router v7 route definitions
│   │   ├── index.css              # Industrial dark theme design system
│   │   └── main.jsx               # React DOM entrypoint
│   ├── package.json               # Frontend dependencies & scripts
│   ├── vite.config.js             # Vite configuration with React & Tailwind plugins
│   └── .env.example               # Frontend environment template
├── Energy_Intelligence/           # Energy & Production Intelligence Engine
│   ├── analytics/                 # Energy deviation, efficiency, and SEC calculation
│   ├── api/                       # Telemetry, baseline, and forecasting API routes
│   ├── dashboard/                 # Streamlit operational dashboard (app.py)
│   ├── database/                  # Telemetry schema and repository layer
│   ├── llm/                       # LLM Copilot integration & fallback rules
│   ├── ml/                        # Training pipelines and baseline evaluation
│   ├── models/                    # Serialized models (energy_baseline.joblib, etc.)
│   ├── mqtt/                      # MQTT broker publishers and subscribers
│   ├── simulator/                 # Factory machine state simulator
│   ├── tests/                     # Unit and integration test suite
│   ├── requirements.txt           # Engine Python dependencies
│   └── docker-compose.yml         # Mosquitto & PostgreSQL container definitions
├── machine_health/                # Machine Health & Predictive Maintenance
│   ├── data/                      # Vibration test datasets
│   ├── outputs/                   # Serialized anomaly models, reports, and EDA plots
│   ├── *.ipynb                    # Feature engineering & ML training workflows
│   ├── test_synthetic_dummy_dataset.py # Anomaly detector test suite
│   └── README.md                  # Machine health module documentation
├── .gitignore
├── resk.db                        # Development SQLite database
└── README.md                      # Project documentation
```

---

## Installation & Setup

### Prerequisites
- **Node.js** (v18 or higher) and **npm**
- **Python** (v3.10 or higher) and **pip**
- **Git**

---

### Backend Setup

1. Open a terminal and navigate to `backend/`:
   ```bash
   cd backend
   ```

2. Create and activate a Python virtual environment:
   ```bash
   # On Windows (PowerShell):
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # On macOS / Linux:
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   ```bash
   # Copy the example environment file
   cp .env.example .env
   ```

   Key configuration variables (`backend/.env`):
   ```ini
   ENVIRONMENT=development
   PORT=8000
   HOST=0.0.0.0
   DATABASE_URL=sqlite:///./resk.db
   SECRET_KEY=your-secure-jwt-secret-key
   ACCESS_TOKEN_EXPIRE_MINUTES=1440

   # Optional: Live SMTP configuration (defaults to logged console mocks in development)
   SMTP_HOST=
   SMTP_PORT=587
   SMTP_USER=
   SMTP_PASS=
   SMTP_FROM=security@resk-industrial.com
   ```

5. Start the backend server:
   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   *(If running from the workspace root instead of `backend/`, use: `uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload`)*

6. Verify the backend:
   - Health Check: `http://127.0.0.1:8000/health`
   - Interactive Swagger API Docs: `http://127.0.0.1:8000/docs`
   - ReDoc Documentation: `http://127.0.0.1:8000/redoc`

---

### Frontend Setup

1. Open a separate terminal and navigate to `frontend/`:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Configure environment variables:
   ```bash
   # Copy the example environment file
   cp .env.example .env
   ```

   Configuration variables (`frontend/.env`):
   ```ini
   VITE_API_BASE_URL=http://localhost:8000
   ```

4. Start the development server:
   ```bash
   npm run dev
   ```

5. Open your browser and navigate to `http://localhost:5173`.

---

## Development Guidelines

- **Branch-Based Workflow**: All new capabilities and fixes must be developed on dedicated feature branches (e.g., `feature/energy-optimization`, `feature/alert-system`).
- **Isolation**: Keep specialized module logic (machine health models, energy analytics) organized within their respective package boundaries.
- **Testing Before Merging**:
  - Run backend unit and integration suites (`pytest backend/test_auth_flow.py`).
  - Run frontend linting (`npm run lint` in `frontend/`).
  - Verify end-to-end functionality locally before creating a pull request.
- **Pull Requests**: Pull requests must target the `main` branch. Provide clear PR descriptions summarizing modified files, test verification steps, and dependencies.

---

## Contribution Workflow

1. Fork or clone the repository:
   ```bash
   git clone https://github.com/irksome06/RESK.git
   cd RESK
   ```
2. Create a clean branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. Implement changes adhering to the repository coding style and architectural separation.
4. Run tests and verify the build passes:
   ```bash
   # In frontend/:
   npm run build
   # In backend/:
   python -m pytest
   ```
5. Commit with descriptive commit messages:
   ```bash
   git commit -m "feat(module): descriptive explanation of changes"
   ```
6. Push the branch to your remote and open a Pull Request against `main`.

---

## Planned Roadmap

The following capabilities represent planned future enhancements (not currently implemented in production):

- **Real-Time IoT & Sensor Integration**: Native OPC-UA and Modbus protocols for direct industrial PLC and sensor streaming.
- **Advanced Energy Forecasting**: Multi-day probabilistic load forecasting accounting for weather, ambient factory conditions, and demand response events.
- **Automated Machine Control**: Automated closed-loop control to trigger equipment sleep modes and load shedding via industrial gateways.
- **Carbon & Emissions Analytics**: Scope 1 and Scope 2 greenhouse gas emissions tracking tied directly to energy grid carbon intensity factors.
- **Advanced Scenario Simulation**: Digital twin simulation for evaluating plant-wide layout modifications, machinery upgrades, and solar/battery microgrid sizing.
- **Cloud-Scale Deployment**: Kubernetes Helm charts, multi-tenant organization isolation, and managed cloud timeseries database backends.

---

## License

License: To be determined
