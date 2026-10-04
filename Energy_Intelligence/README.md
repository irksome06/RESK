# Person 3: Energy & Production Intelligence Engine

A core module of the Smart Manufacturing solution for Indian SMEs (YUVA_SM).
Built on the paradigm: **MEASURE → UNDERSTAND → OPTIMIZE → VERIFY → EXPLAIN** with a focus on **Production-Aware Energy Intelligence**.

---

## 🚀 Quick Start (Complete End-to-End Demonstration)

Follow these steps to run the complete pipeline and launch the Smart Manufacturing Dashboard:

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. (Optional) Start Infrastructure
```bash
# If running Mosquitto broker & PostgreSQL via Docker (optional; SQLite fallback used automatically):
docker compose up -d mosquitto
```

### 3. Run the Authoritative Final Demonstration Runner
```bash
python scripts/run_final_demo.py
```
*Executes the clean 15-step industrial demonstration sequence (Normal → Idle → Sleep → Degraded → Overload → Recovery), establishes the authoritative analysis window, verifies strict mathematical reconciliation, prints the authoritative summary, and queries the grounded Energy Copilot.*

### 4. Start the FastAPI Intelligence Engine
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```
*Interactive Swagger documentation available at: `http://localhost:8000/docs`*

### 5. Launch the Industrial Energy Intelligence Control Center
```bash
streamlit run dashboard/app.py
```
*Presentation-grade industrial control-room interface adhering to Schneider Electric standards: 11 operational sections, real-time KPIs, Plotly time-series and baseline charts, machine fleet intelligence table, interactive asset deep-dives, operational state bar charts, non-production idle energy analysis, short-horizon forecasts, IPMVP savings verification, and grounded Energy Copilot.*

### 6. Run the Full Test Suite
```bash
pytest -q
```
*295 automated tests passing across Phases 1–13.6 (0 failures).*

---

## 🏛️ Architecture Overview

The system acts as the analytical bridge between **Person 1** (Optimization/Control), **Person 2** (Predictive Maintenance/Health), and **Person 4** (Central Dashboard).

```
[Person 1: Sleep / Power Actions] ──┐
                                     ├──► [MQTT Broker: Mosquitto]
[Person 2: Health / Vibe / Temp]  ──┤          │
                                     │          ▼
[Simulator: Realistic Machines]   ──┘    [MQTT Subscriber]
                                                │
                                                ▼
                                    ┌───────────────────────┐
                                    │ Person 3 Engine       │
                                    │ • Deterministic SEC   │
                                    │ • ML Baseline (XGB)   │
                                    │ • Energy Forecasting  │
                                    │ • Savings & CO2 Engine│
                                    │ • Health Correlation  │
                                    │ • Qwen 1.7B Copilot   │
                                    └───────────┬───────────┘
                                                │
                                ┌───────────────┴───────────────┐
                                ▼                               ▼
                     [FastAPI REST Endpoints]        [WebSocket Live Stream]
                                │                               │
                                └───────────────┬───────────────┘
                                                ▼
                                    [Person 4: Dashboard]
```

---

## 📁 Directory Structure

```
person3_energy_intelligence/
│
├── simulator/           # Multi-machine industrial physics-based simulator
│   ├── machine_simulator.py
│   ├── machine_states.py
│   └── config.py
│
├── mqtt/                # MQTT pub/sub pipeline with auto-reconnect
│   ├── publisher.py
│   └── subscriber.py
│
├── api/                 # FastAPI REST and WebSocket endpoints
│   ├── main.py
│   ├── telemetry.py
│   ├── machines.py
│   ├── metrics.py
│   ├── savings.py
│   └── copilot.py
│
├── database/            # SQLAlchemy ORM and PostgreSQL / SQLite models
│   ├── database.py
│   ├── models.py
│   └── schemas.py
│
├── analytics/           # Deterministic analytics (SEC, carbon, savings, utilization)
│   ├── sec.py
│   ├── baseline.py
│   ├── savings.py
│   ├── carbon.py
│   └── efficiency.py
│
├── ml/                  # ML baseline modeling, TimeSeriesSplit CV, forecasting
│   ├── preprocessing.py
│   ├── baseline_models.py
│   ├── forecasting.py
│   ├── train.py
│   └── evaluate.py
│
├── llm/                 # Qwen3 / Ollama local Energy Copilot integration
│   ├── ollama_client.py
│   ├── context_builder.py
│   └── prompts.py
│
├── data/
│   ├── raw/             # Raw collected telemetry
│   └── processed/       # Curated training datasets
│
├── tests/               # Pytest verification suite
│   ├── test_scaffolding.py
│
├── .env.example         # Environment template
├── requirements.txt     # Python dependencies
├── docker-compose.yml   # Mosquitto & PostgreSQL setup
└── README.md
```

---

## 🚀 Quickstart & Setup Commands

### 1. Configure Environment
```bash
cd person3_energy_intelligence
cp .env.example .env
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Phase 1 Verification Tests
```bash
pytest tests/test_scaffolding.py -v
```

### 4. Run the FastAPI Development Server
```bash
uvicorn api.main:app --reload --port 8000
```
Visit API Documentation at: `http://localhost:8000/docs`

---

## 📡 Telemetry Contract (Phase 2)

The canonical telemetry model ([`database/schemas.py`](file:///Users/mohammadrehan/Documents/YUVA_SM/person3_energy_intelligence/database/schemas.py)) serves as the formal contract between physical/simulated assets, ingestion brokers, and downstream analytical and ML pipelines.

### 1. Canonical Telemetry Specification

| Field | Type | Unit | Required | Validation & Semantics |
| :--- | :--- | :--- | :---: | :--- |
| `timestamp` | `datetime` | UTC | **Yes** | ISO 8601 timestamp of measurement event. Naive timestamps auto-normalized to UTC. |
| `machine_id` | `str` | - | **Yes** | Non-empty machine identifier (e.g. `"M01"`). Leading/trailing whitespace stripped. |
| `power_kw` | `float` | kW | **Yes** | Instantaneous active electrical power demand ($\ge 0.0\text{ kW}$). |
| `energy_kwh` | `float` | kWh | **Yes** | Cumulative active electrical energy meter reading ($\ge 0.0\text{ kWh}$). |
| `machine_state` | `MachineState` | - | **Yes** | Current state enum: `RUNNING`, `IDLE`, `SLEEP`, `DEGRADED`, `OVERLOAD`. |
| `production_count` | `int` | units | No | Cumulative units produced since shift/batch startup ($\ge 0$). Distinct from missing. |
| `production_delta` | `int` | units | No | Units finished strictly during this telemetry interval ($\ge 0$). |
| `cycle_time_sec` | `float` | sec | No | Duration of latest completed production cycle ($\ge 0.0\text{ s}$). $0.0$ when no unit completed. |
| `voltage_v` | `float` | V | No | Line-to-line RMS voltage ($\ge 0.0\text{ V}$). |
| `current_a` | `float` | A | No | Phase RMS current draw ($\ge 0.0\text{ A}$). |
| `temperature_c` | `float` | °C | No | Motor/bearing temperature ($-50.0\text{°C} \le T \le 300.0\text{°C}$). Sub-zero supported. |
| `vibration` | `float` | mm/s | No | Overall RMS vibration velocity ($\ge 0.0\text{ mm/s}$). |
| `rpm` | `float` | RPM | No | Spindle/shaft rotational speed ($\ge 0.0\text{ RPM}$). |
| `torque_nm` | `float` | Nm | No | Motor shaft mechanical torque ($\ge 0.0\text{ Nm}$). |
| `health_score` | `float` | index | No | Asset health index from Person 2 ($0.0 \le H \le 100.0$). |
| `anomaly_score` | `float` | prob | No | Anomaly likelihood from Person 2 ($0.0 \le A \le 1.0$). |
| `source` | `TelemetrySource`| - | No | Ingestion source (`simulator`, `sensor`, `plc`, `gateway`, `external`). Default: `simulator`. |
| `schema_version` | `str` | - | No | Semantic schema contract version. Default: `"1.0"`. |

### 2. Semantic Distinctions & Engineering Design Decisions

- **Power vs. Energy**: `power_kw` is the instantaneous or interval-average rate of doing work ($P$). `energy_kwh` is the monotonically increasing physical energy meter register ($E = \int P \, dt$). The schema preserves both without attempting synthetic conversions.
- **Production Count Semantics**:
  - `production_count` represents the cumulative machine register (typical of PLC memory counters).
  - `production_delta` optionally provides the delta within the sampling window.
  - **Missing vs. Zero**: `production_count: None` signifies a non-production machine or missing sensor, whereas `production_count: 0` explicitly flags zero output during an active operational window. This prevents erroneous zero-division during SEC calculation.
- **Timestamping Policy**: `timestamp` represents the *physical measurement/event occurrence time*. Server reception time is handled separately at the ingestion gateway layer. All timestamps are validated as timezone-aware UTC.
- **Machine State Semantics**:
  - `RUNNING`: Machine actively engaged in cutting/milling/processing with normal load profile.
  - `IDLE`: Machine powered on and available, but zero parts produced.
  - `SLEEP`: Low-power standby triggered autonomously or by operator optimization.
  - `DEGRADED`: Mechanical wear/thermal distress; elevated SEC and vibration.
  - `OVERLOAD`: Excessive current/power beyond thermal rating; high stress.

### 3. Interoperability & Integration Boundaries

- **Person 1 (Optimization)**: Emits control state actions (`SLEEP`, power limits) over `factory/{machine_id}/action`. Person 3 measures resulting power reduction and computes verified energy savings.
- **Person 2 (Machine Health)**: Publishes condition monitoring telemetry (`temperature_c`, `vibration`, `health_score`, `anomaly_score`) over `factory/{machine_id}/health`. Person 3 correlates degraded health with SEC deterioration.
- **Person 3 (This Module)**: Ingests telemetry, stores time-series historical data, calculates SEC, trains baseline regression models, verifies savings, and hosts the Qwen Copilot.
- **Person 4 (Dashboard)**: Consumes clean validated telemetry and analytical KPIs via REST and WebSocket streaming.

### 4. Canonical JSON Example

```json
{
  "timestamp": "2026-10-02T10:30:00Z",
  "machine_id": "M01",
  "power_kw": 7.8,
  "energy_kwh": 125.6,
  "voltage_v": 415.0,
  "current_a": 12.4,
  "production_count": 120,
  "production_delta": 1,
  "cycle_time_sec": 30.0,
  "machine_state": "RUNNING",
  "temperature_c": 52.4,
  "vibration": 0.18,
  "rpm": 1450.0,
  "health_score": 94.0,
  "anomaly_score": 0.08,
  "source": "simulator",
  "schema_version": "1.0"
}
```

---

## 🏭 Industrial Machine Simulator (Phase 3)

> [!NOTE]
> **Engineering Model Disclaimer**: This simulator is a synthetic engineering model for demonstration and development. It is not claimed to represent a specific real industrial machine.

### 1. Purpose & Core Physics
The simulator generates physically consistent, multi-machine industrial telemetry validating against [`TelemetryRecord`](file:///Users/mohammadrehan/Documents/YUVA_SM/person3_energy_intelligence/database/schemas.py). Instead of independent random numbers, variables are governed by coupled electro-thermal-mechanical relations:

$$\text{State} \longrightarrow \text{Power} \longrightarrow \text{Accumulated Energy} \longrightarrow \text{Production} \longrightarrow \text{Thermal Mass} \longrightarrow \text{Vibration} \longrightarrow \text{Health Index} \longrightarrow \text{SEC}$$

### 2. Simulated Industrial Assets

| Asset ID | Machine Type | Rated Power ($P_{\text{rated}}$) | Nominal UPH | Nominal RPM | Idle Power | Sleep Power | Nominal Temp | Nominal Vib |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **M01** | CNC Milling Center 1 | 7.5 kW | 120 uph | 1450 RPM | ~1.35 kW | ~0.35 kW | 50.0 °C | 0.18 mm/s |
| **M02** | Heavy Lathe 2 | 6.8 kW | 100 uph | 1200 RPM | ~1.36 kW | ~0.30 kW | 48.0 °C | 0.16 mm/s |
| **M03** | Stamping Press 3 | 8.2 kW | 130 uph | 1500 RPM | ~1.39 kW | ~0.40 kW | 52.0 °C | 0.20 mm/s |
| **M04** | Precision Grinder 4 | 5.5 kW | 90 uph | 2800 RPM | ~1.05 kW | ~0.25 kW | 45.0 °C | 0.15 mm/s |

### 3. Machine States & Behavior
- **`RUNNING`**: Normal active duty; power $\approx P_{\text{rated}} \pm \text{noise}$, stable production ($100-130\text{ uph}$), thermal steady state, healthy vibration ($0.15-0.20\text{ mm/s}$).
- **`IDLE`**: Machine powered but awaiting work; production = 0, power drops to $\approx 18-20\%$ of nominal, vibration drops, temperature slowly cools. (Crucial baseline for Person 1 sleep mode trigger).
- **`SLEEP`**: Standby energy-saving mode; production = 0, power drops to deep standby ($0.2-0.5\text{ kW}$), RPM = 0, vibration $\approx 0\text{ mm/s}$.
- **`DEGRADED`**: Component wear / mechanical friction; power increases ($1.15-1.35\times$), production throughput drops ($80-90\%$), vibration increases ($0.35-0.75\text{ mm/s}$), temperature climbs ($60-75\text{°C}$), and **Specific Energy Consumption (SEC) deteriorates**.
- **`OVERLOAD`**: Severe mechanical/electrical stress; power climbs ($1.35-1.60\times$), current draw spikes, temperature rises rapidly ($70-85\text{°C}$), accelerated health decay.

### 4. Physical Formulation
- **Power Model**: $P(t) = P_{\text{rated}} \times \text{StateFactor} \times (1 + \alpha_{\text{deg}} \cdot \text{deg\_level}) + \text{noise}$.
- **Energy Model**: Cumulative integration $\Delta E = P(t) \cdot \Delta t_{\text{hours}}$, strictly monotonic ($E_{t+1} \ge E_t$).
- **Production Model**: Fractional units buffer accumulating at $\frac{\text{effective\_UPH}}{3600} \cdot \Delta t$, incrementing `production_count` when crossing integer thresholds.
- **Thermal Inertia Model**: Newton heat transfer $\frac{dT}{dt} = \frac{Q_{\text{gen}} - Q_{\text{loss}}}{C_{\text{thermal}}}$, preventing abrupt jumps and modeling cooling toward ambient ($28\text{°C}$).
- **Electrical Model**: 3-Phase RMS current derived via $I = \frac{1000 \cdot P}{\sqrt{3} \cdot V \cdot \text{PF}}$ with $V \approx 415\text{ V}$.
- **Health & Anomaly Scoring**: Explainable composite index factoring temperature excess, vibration excess, and component wear, bounded within $[0, 100]$ and $[0.0, 1.0]$.

### 5. Multi-Phase Demonstration Scenario Controller
The [`DemoScenarioController`](file:///Users/mohammadrehan/Documents/YUVA_SM/person3_energy_intelligence/simulator/scenarios.py) orchestrates the 6 key operational phases:
1. **Phase A (Normal)**: All machines running stably.
2. **Phase B (Idle)**: M01 enters IDLE (production drops to 0, power remains at ~1.35 kW).
3. **Phase C (Sleep)**: Person 1 triggers SLEEP on M01 (power drops to ~0.35 kW; verified energy savings opportunity).
4. **Phase D (Degraded)**: M03 suffers progressive wear (power & vibration increase, health drops to ~65, SEC rises).
5. **Phase E (Overload)**: M02 experiences extreme electrical & load stress (high current, rapid temperature rise).
6. **Phase F (Recovery)**: Maintenance intervention on M03 (gradual thermal dissipation, vibration reduction, health restores).

### 6. Running the Simulator
```bash
python3 -c "
from simulator.machine_simulator import FactorySimulator
sim = FactorySimulator(seed=42)
for record in sim.step(dt_seconds=1.0):
    print(record.machine_id, record.machine_state.value, f'{record.power_kw} kW', f'{record.temperature_c} C')
"
```

---

## 📡 MQTT Telemetry Pipeline (Phase 4)

> [!WARNING]
> **Local Development Security Notice**: The local Mosquitto setup allows anonymous connections without TLS on port 1883 strictly for hackathon prototyping and development. Production SME deployments must enforce TLS (port 8883) with X.509 mutual certificates, user/password or token-based authentication, and machine-level Access Control Lists (ACLs).

### 1. MQTT End-to-End Architecture

```
[FactorySimulator]
        │ (TelemetryRecord)
        ▼
 [MQTTPublisher]  (Persistent connection, QoS 1, retain=False)
        │
        ▼ (factory/{machine_id}/telemetry)
[Mosquitto Broker] ◄── [Person 2: Health Alerts] (factory/{machine_id}/health)
        │          ◄── [Person 1: Optimization Actions] (factory/{machine_id}/action)
        ▼
 [MQTTSubscriber] (Paho loop_start(), auto-reconnect backoff 1s–30s)
        │
        ├──► JSON decoding & schema validation (Pydantic)
        ├──► Malformed / invalid payload isolation (Never crashes)
        │
        ▼ (Type-Safe Dispatches)
 [Application Callbacks] ──► (Future PostgreSQL & Analytics Ingestion)
```

### 2. Standardized Factory Topics

All topic construction and parsing is centralized in [`mqtt/topics.py`](file:///Users/mohammadrehan/Documents/YUVA_SM/person3_energy_intelligence/mqtt/topics.py) to prevent hardcoded string scattering:

| Topic Pattern | Role | Direction | Payload Contract |
| :--- | :--- | :---: | :--- |
| `factory/{machine_id}/telemetry` | Machine telemetry stream | Publish & Subscribe | [`TelemetryRecord`](file:///Users/mohammadrehan/Documents/YUVA_SM/person3_energy_intelligence/database/schemas.py) |
| `factory/{machine_id}/health` | Machine condition & anomaly alerts | Emitted by Person 2 | [`MachineHealthMessage`](file:///Users/mohammadrehan/Documents/YUVA_SM/person3_energy_intelligence/database/schemas.py) |
| `factory/{machine_id}/action` | Optimization commands (`SLEEP`, `WAKE`) | Emitted by Person 1 | [`MachineActionMessage`](file:///Users/mohammadrehan/Documents/YUVA_SM/person3_energy_intelligence/database/schemas.py) |

### 3. Quality of Service (QoS) & Retention Policy
- **QoS Strategy**: QoS 1 (At least once delivery) is configured across telemetry, health, and action streams. This guarantees message delivery across fluctuating industrial Wi-Fi/Ethernet links.
- **Deduplication**: Because QoS 1 allows potential message duplicates during network retries, deduplication will be formally enforced at the ingestion and PostgreSQL database layer in Phase 6 using unique `(machine_id, timestamp)` constraints.
- **Retention**: `retain = False` is enforced for high-frequency telemetry to avoid flooding newly connecting subscribers with stale instantaneous readings.

### 4. Resilient Error Handling & Reconnection
- **Zero-Crash Ingestion**: Malformed JSON strings, negative power readings, or invalid enum states are rejected safely at the Pydantic boundary, incrementing error counters while keeping the subscriber operational.
- **Callback Isolation**: Exceptions inside application analytics callbacks are caught and logged without killing the Paho network loop.
- **Exponential Reconnection Backoff**: Automatic reconnection starts at 1 second, doubling up to a maximum 30 seconds (`reconnect_delay_set(min_delay=1, max_delay=30)`).

### 5. Running the MQTT Pipeline

#### Step 1: Start Mosquitto Broker (Docker or Homebrew)
```bash
# Option A: Using Docker Compose
docker compose up -d mosquitto

# Option B: Using Homebrew (macOS)
brew services start mosquitto
```

#### Step 2: Run End-to-End Simulation Demo
```bash
python3 scripts/run_mqtt_demo.py
```
*(If no broker is active, the script outputs actionable launch instructions without hanging).*

---

## ⚡ FastAPI Backend Layer (Phase 5)

> [!NOTE]
> **Storage Limitation Notice**: Phase 5 utilizes a thread-safe, bounded in-memory store ([`InMemoryTelemetryStore`](file:///Users/mohammadrehan/Documents/YUVA_SM/person3_energy_intelligence/api/telemetry_store.py)) strictly for REST querying, mock testing, and API integration. Long-term relational persistence and time-series querying will be implemented with PostgreSQL in Phase 6.

### 1. Ingestion & Retrieval Architecture

```
[External HTTP Client] ──► POST /telemetry ──┐
                                             ▼
                               ┌───────────────────────────┐
                               │ ingest_telemetry_record() │
                               └─────────────┬─────────────┘
                                             │
[MQTT Broker] ──► [MQTTSubscriber] ──────────┘
                                             │
                                             ▼
                               ┌───────────────────────────┐
                               │ InMemoryTelemetryStore    │
                               │ (Bounded, Thread-Safe)    │
                               └─────────────┬─────────────┘
                                             │
                                ┌────────────┴────────────┐
                                ▼                         ▼
                        GET /telemetry            GET /factory/snapshot
                        GET /machines             GET /telemetry/latest/{id}
```

### 2. Implemented Endpoints

| Method | Endpoint | Description | Response Schema |
| :---: | :--- | :--- | :--- |
| `GET` | `/` | Service root metadata & environment status | JSON metadata |
| `GET` | `/health` | Health check endpoint | `{"status": "healthy"}` |
| `POST` | `/telemetry` | Validate and ingest a single canonical telemetry record | `TelemetryAcceptedResponse` (201) |
| `GET` | `/telemetry` | Query recent telemetry records (newest first, optional `machine_id`, `limit`) | `List[TelemetryRecord]` |
| `GET` | `/telemetry/latest/{machine_id}` | Fetch the single most recent record for a machine (or 404) | `TelemetryRecord` |
| `GET` | `/machines` | List machine summaries combining static profiles with dynamic metrics | `List[MachineSummary]` |
| `GET` | `/machines/{machine_id}` | Detailed asset summary and latest telemetry observation (or 404) | `MachineSummary` |
| `GET` | `/factory/snapshot` | Aggregated factory state (machines seen, states, power sum, production) | `FactorySnapshot` |

### 3. How to Run the Server & Documentation
```bash
# Start the FastAPI server with live reload
uvicorn api.main:app --reload --port 8000
```
- Interactive Swagger UI: `http://localhost:8000/docs`
- ReDoc UI: `http://localhost:8000/redoc`

### 4. Example `curl` Commands

#### Ingest a Telemetry Record:
```bash
curl -X POST http://localhost:8000/telemetry \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "2026-10-02T12:00:00Z",
    "machine_id": "M01",
    "power_kw": 7.8,
    "energy_kwh": 125.6,
    "machine_state": "RUNNING",
    "production_count": 120
  }'
```

#### Fetch Latest Telemetry for a Machine:
```bash
curl http://localhost:8000/telemetry/latest/M01
```

#### Fetch Live Factory Snapshot:
```bash
curl http://localhost:8000/factory/snapshot
```

---

## 🗄️ PostgreSQL Database Persistence (Phase 6)

> [!IMPORTANT]
> **Scope Notice**: Phase 6 establishes durable relational database persistence, indexing, session management, and idempotent duplicate handling. Advanced SEC calculations, baseline ML models, forecasting, and savings tracking belong to subsequent phases.

### 1. Ingestion & Persistence Pipeline

```
Factory Simulator / Field Sensors
             │
             ▼
     MQTT Broker (QoS 1)
             │
             ▼
      MQTTSubscriber
             │
             ▼
 TelemetryRecord Validation
             │
             ▼
 TelemetryRepository (DAO)
             │
    ┌────────┴────────┐
    ▼                 ▼
PostgreSQL        FastAPI APIs
(Authoritative)   (REST / Latest / Snapshots)
```

Both MQTT subscriber callbacks and REST `POST /telemetry` route directly through the unified `TelemetryRepository`, making the relational database the single durable source of truth.

### 2. Database Schema (`telemetry` Table)

| Column | Type | Nullable | Description |
| :--- | :--- | :---: | :--- |
| `id` | `INTEGER` | No | Auto-incrementing primary key |
| `timestamp` | `TIMESTAMP WITH TIME ZONE` | No | Telemetry measurement time (ISO 8601 UTC) |
| `machine_id` | `VARCHAR(50)` | No | Machine identifier (e.g. `M01`, `CNC-02`) |
| `power_kw` | `FLOAT` | No | Active electrical demand in kW |
| `energy_kwh` | `FLOAT` | No | Cumulative active energy in kWh |
| `machine_state` | `VARCHAR(50)` | No | Operating state (`RUNNING`, `IDLE`, `SLEEP`, `DEGRADED`, `OVERLOAD`) |
| `production_count`| `INTEGER` | Yes | Cumulative piece counter |
| `production_delta`| `INTEGER` | Yes | Production units completed during interval |
| `cycle_time_sec` | `FLOAT` | Yes | Machine cycle duration in seconds |
| `voltage_v` | `FLOAT` | Yes | Bus voltage in Volts |
| `current_a` | `FLOAT` | Yes | Phase current in Amperes |
| `temperature_c` | `FLOAT` | Yes | Motor/bearing temperature in °C |
| `vibration` | `FLOAT` | Yes | Vibration amplitude in mm/s RMS |
| `rpm` | `FLOAT` | Yes | Shaft speed in RPM |
| `torque_nm` | `FLOAT` | Yes | Mechanical torque in Nm |
| `health_score` | `FLOAT` | Yes | Predictive health score (0-100) from Person 2 |
| `anomaly_score` | `FLOAT` | Yes | Diagnostic anomaly score (0.0-1.0) |
| `source` | `VARCHAR(50)` | Yes | Data origin (`simulator`, `sensor`, `plc`, `gateway`) |
| `schema_version`| `VARCHAR(20)` | Yes | Schema contract version (`1.0`) |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | Yes | Record database insertion timestamp |

### 3. Industrial Time-Series Indexing

To support low-latency querying across high-frequency industrial time-series data:
- **`uq_telemetry_machine_timestamp`** (`UNIQUE(machine_id, timestamp)`): Enforces idempotency and prevents duplicate MQTT QoS 1 message retries.
- **`ix_telemetry_machine_timestamp`** (`machine_id, timestamp`): Primary index pattern for analytics querying machine time-windows (`M01 between t_start and t_end`).
- **`ix_telemetry_timestamp_desc`** (`timestamp DESC`): Accelerates reverse-chronological feeds and latest observation subqueries.
- **`ix_telemetry_state_machine`** (`machine_state, machine_id`): Rapidly indexes idle, degraded, and sleep state intervals for energy waste analysis.

### 4. Idempotent Duplicate Handling (MQTT QoS 1)

In distributed MQTT networks, network hiccups trigger message re-deliveries.
1. The unique constraint `(machine_id, timestamp)` prevents duplicate records.
2. In `save_telemetry()`, an `IntegrityError` is caught safely using nested transaction savepoints, rolling back without corrupting the active database session.
3. In `POST /telemetry`, sending a duplicate record returns `HTTP 409 Conflict` (`"Duplicate telemetry record ... already exists"`).
4. In background MQTT ingestion, duplicate records are skipped cleanly and logged without thread disruption.

### 5. Session Safety & Concurrency

- **FastAPI Requests**: Utilize request-scoped sessions via `get_db()` dependency generator with automatic rollback on unhandled exceptions and guaranteed cleanup.
- **MQTT Subscriber**: Operates on a background thread and uses `get_db_context()` to instantiate isolated, short-lived database sessions independent of HTTP request lifecycles.
- **Resilient Fallback**: Automatically connects to PostgreSQL if available; if PostgreSQL daemon is offline, falls back seamlessly to SQLite (`sqlite:///./energy_intelligence.db`) to ensure zero test disruptions.

### 6. Local Setup & Docker Commands

```bash
# Start PostgreSQL & Mosquitto via Docker Compose
docker compose up -d postgres mosquitto

# Verify PostgreSQL container is healthy
docker compose ps postgres

# Run database tests
python3 -m pytest tests/test_database.py -v

# Run full test suite
python3 -m pytest -v
```

---

## 📊 Deterministic Energy Analytics (Phase 7)

> [!IMPORTANT]
> **Deterministic Non-ML Phase**: Phase 7 converts raw telemetry history into mathematically transparent and reproducible industrial energy & production KPIs. No machine learning, regression, or forecasting models are used in this phase.

### 1. Calculation Pipeline

```
RAW TELEMETRY (Timestamp, kW, Cumulative kWh, State, Production Count/Delta)
                                   │
                                   ▼
        ┌──────────────────────────────────────────────────────┐
        │ 1. Time Window Validation & Interval dt Calculation  │
        └──────────────────────────┬───────────────────────────┘
                                   │
                                   ▼
        ┌──────────────────────────────────────────────────────┐
        │ 2. Energy Consumption & Non-Monotonic Meter Check    │
        │    Primary: ΔE = last_kWh - first_kWh (Monotonic)    │
        │    Secondary: Trapezoidal Power Integration Fallback │
        └──────────────────────────┬───────────────────────────┘
                                   │
                                   ▼
        ┌──────────────────────────────────────────────────────┐
        │ 3. Production Throughput & Rate (pieces / hour)      │
        │    ΔP = last_count - first_count (Reset Protection)  │
        └──────────────────────────┬───────────────────────────┘
                                   │
                                   ▼
        ┌──────────────────────────────────────────────────────┐
        │ 4. Specific Energy Consumption (SEC = Energy / Prod) │
        │    Energy per unit (Safe Zero Division Protection)   │
        └──────────────────────────┬───────────────────────────┘
                                   │
                                   ▼
        ┌──────────────────────────────────────────────────────┐
        │ 5. Operational Utilization & State Energy Breakdown  │
        │    Productive (RUNNING, DEGRADED, OVERLOAD)          │
        │    Non-Productive (IDLE, SLEEP)                      │
        └──────────────────────────┬───────────────────────────┘
                                   │
                                   ▼
        ┌──────────────────────────────────────────────────────┐
        │ 6. Energy Economics & Environmental Impact           │
        │    Cost (₹) = Energy (kWh) × Tariff (₹/kWh)          │
        │    CO2 (kg) = Energy (kWh) × Grid Factor (kg/kWh)    │
        └──────────────────────────────────────────────────────┘
```

### 2. Core Definitions & Formulations

| Metric | Units | Mathematical Formula | Interpretation / Boundary Rules |
| :--- | :--- | :--- | :--- |
| **Instantaneous Power ($P$)** | kW | Active electrical demand register | Power drawn at instantaneous sample $t_i$. |
| **Accumulated Energy ($E$)** | kWh | Cumulative meter register | $E_{consumed} = E_{end} - E_{start}$ if monotonic. Flags `INVALID_NON_MONOTONIC_ENERGY` if meter drops. |
| **Production Throughput ($P_{units}$)** | units | $Count_{end} - Count_{start}$ or $\sum \Delta P_i$ | Pieces completed in window. Differentiates `0` (zero made) from `None` (unmonitored). |
| **Production Rate** | units/hr | $P_{units} / \Delta t_{hours}$ | Hourly production velocity. Returns `None` if $\Delta t = 0$. |
| **Specific Energy Consumption (SEC)** | kWh/unit | $E_{consumed} / P_{units}$ | Fundamental industrial benchmark. Returns `None` if $P_{units} \le 0$ (prevents division by zero). |
| **Operational Utilization** | % | $(\sum t_{productive} / \sum t_{total}) \times 100$ | Productive states: `RUNNING`, `DEGRADED`, `OVERLOAD`. Non-productive: `IDLE`, `SLEEP`. |
| **Idle Energy** | kWh | $\sum_{i \in IDLE} \Delta E_i$ | Energy consumed while machine is unproductively energized. Used by Person 1 for sleep scheduling. |
| **Idle Power Average** | kW | $E_{idle} / t_{idle}$ | Baseline no-load power draw. |
| **Electricity Cost** | INR (₹) | $E_{consumed} \times \text{Tariff}$ | Default configured tariff: ₹8.50/kWh (Indian Commercial/Industrial LT). |
| **CO2 Emissions** | kg CO2 | $E_{consumed} \times \text{Emission Factor}$ | Default CEA India grid emission factor: 0.716 kg CO2/kWh. |

### 3. Factory Aggregation Rules

1. **Factory SEC**: Computed as $\frac{\sum \text{Total Factory Energy}}{\sum \text{Total Factory Production}}$, **NEVER** as the naive average of machine SEC values.
2. **Factory Utilization**: Computed as $\frac{\sum \text{Total Productive Machine Hours}}{\sum \text{Total Observed Machine Hours}} \times 100$.
3. **State Breakdown**: Sum of energy and time spent in each state across all active machines.

### 4. API Endpoints & Example Requests

#### Machine Deterministic Analytics:
```bash
# Query 1-hour deterministic KPIs for machine M01
curl "http://localhost:8000/analytics/machines/M01?start_time=2026-10-02T10:00:00Z&end_time=2026-10-02T11:00:00Z"
```

**Example JSON Response:**
```json
{
  "machine_id": "M01",
  "start_time": "2026-10-02T10:00:00Z",
  "end_time": "2026-10-02T11:00:00Z",
  "elapsed_hours": 1.0,
  "energy_kwh": 4.75,
  "production_units": 40,
  "production_rate_units_per_hour": 40.0,
  "sec_kwh_per_unit": 0.1187,
  "utilization_pct": 50.0,
  "state_energy": {
    "running": 2.0,
    "idle": 0.3,
    "sleep": 0.05,
    "degraded": 2.4,
    "overload": 0.0,
    "running_energy_kwh": 2.0,
    "idle_energy_kwh": 0.3,
    "sleep_energy_kwh": 0.05,
    "degraded_energy_kwh": 2.4,
    "overload_energy_kwh": 0.0,
    "running_time_hours": 0.25,
    "idle_time_hours": 0.25,
    "sleep_time_hours": 0.25,
    "degraded_time_hours": 0.25,
    "overload_time_hours": 0.0,
    "idle_power_average_kw": 1.2,
    "idle_energy_pct": 6.32,
    "sleep_energy_pct": 1.05
  },
  "energy_cost_inr": 40.38,
  "electricity_rate_inr_per_kwh": 8.5,
  "co2_kg": 3.401,
  "grid_emission_factor_kg_per_kwh": 0.716,
  "data_quality": {
    "status": "OK",
    "calculation_method": "METER_DELTA",
    "warnings": []
  }
}
```

#### Factory-Wide Deterministic Analytics:
```bash
# Query aggregate factory KPIs over the time window
curl "http://localhost:8000/analytics/factory?start_time=2026-10-02T10:00:00Z&end_time=2026-10-02T11:00:00Z"
```

---

## ⚡ Phase 8.1: Production-Aware Energy Baseline Modeling (V2)

### 1. Architectural Motivation & V1 vs V2 Comparison
In Phase 8 (V1), `power_kw` was inadvertently included as an input feature to estimate `interval_energy_kwh = energy_kwh[t] - energy_kwh[t-1]`. Because $E \approx P \times \Delta t / 3600$, the linear model achieved near $R^2 = 1.0$ simply by learning the physical energy meter integral rather than an operational, production-aware expected baseline.

In **Phase 8.1 (V2)**, the architecture was corrected:
- **Phase 8 (V1)**: Preserved as `models/energy_baseline_v1_power_based.joblib` (diagnostic meter consistency check).
- **Phase 8.1 (V2)**: Production-aware baseline answering:
  > *"Given what the machine produced and how it operated, how much energy would we normally expect it to consume?"*

### 2. Feature Architecture
- **Strictly Excluded Features**: `power_kw`, `energy_kwh`, `interval_energy_kwh`, `current_a`, `voltage_v`.
- **Production & Operating Features**:
  - Production context: `production_delta`, `production_rate`
  - Kinematics & Mechanics: `rpm`, `torque_nm`
  - Asset Condition: `temperature_c`, `vibration`, `health_score`, `anomaly_score`
  - Temporal & Interval: `hour_of_day`, `day_of_week`, `dt_seconds`
  - Categoricals: `machine_state`, `machine_id` (one-hot encoded with `handle_unknown="ignore"`)

### 3. Persisted Datasets
Deterministic multi-phase operational cycles across all 4 machine profiles (M01 CNC Milling Center, M02 Heavy Lathe, M03 Stamping Press, M04 Precision Grinder) are persisted to disk:
- **Raw Telemetry**: `data/raw/factory_telemetry.csv` (3,600 raw records)
- **Processed Baseline Data**: `data/processed/baseline_training_data.csv` (3,596 valid intervals)

### 4. Chronological Validation & Model Comparison
- **Split Strategy**: Chronological 80/20 train/test split (2,876 train / 720 holdout test).
- **CV Strategy**: `TimeSeriesSplit(n_splits=5)` exclusively on the training partition.
- **Untouched Test Set**: Evaluated once after model selection.

| Model | CV MAE (kWh) | CV Std MAE | CV RMSE (kWh) | CV $R^2$ | Best Hyperparameters | Test MAE (kWh) | Test RMSE (kWh) | Test $R^2$ | Selected |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Linear Regression** | **$1.8 \times 10^{-5}$** | **$2.0 \times 10^{-6}$** | **$2.5 \times 10^{-5}$** | **0.9998** | *(default OLS)* | **$1.6 \times 10^{-5}$** | **$2.3 \times 10^{-5}$** | **0.9998** | **YES (Winner)** |
| Ridge Regression | $2.0 \times 10^{-5}$ | $3.0 \times 10^{-6}$ | $2.8 \times 10^{-5}$ | 0.9998 | `alpha=0.01` | $1.8 \times 10^{-5}$ | $2.5 \times 10^{-5}$ | 0.9998 | No |
| Gradient Boosting | $4.9 \times 10^{-5}$ | $8.1 \times 10^{-5}$ | $8.6 \times 10^{-5}$ | 0.9916 | `lr=0.05, depth=5, n=200` | $8.0 \times 10^{-6}$ | $1.4 \times 10^{-5}$ | 0.9999 | No |
| Random Forest | $6.0 \times 10^{-5}$ | $1.02 \times 10^{-4}$ | $1.04 \times 10^{-4}$ | 0.9872 | `depth=10, n=200` | $7.0 \times 10^{-6}$ | $1.2 \times 10^{-5}$ | 1.0000 | No |
| XGBoost Regressor | $1.59 \times 10^{-4}$ | $1.96 \times 10^{-4}$ | $3.21 \times 10^{-4}$ | 0.9016 | `lr=0.03, depth=3, n=200` | $5.1 \times 10^{-5}$ | $8.1 \times 10^{-5}$ | 0.9980 | No |

### 5. Representative State Sanity Check
Evaluating expected energy on the holdout test set across operational states:
- **RUNNING** (M01, rpm=1450, torque=30): Actual = 0.004170 kWh, Expected = 0.004169 kWh (Deviation: +0.02%)
- **IDLE** (M01, rpm=20, torque=0): Actual = 0.000770 kWh, Expected = 0.000772 kWh (Deviation: -0.26%)
- **SLEEP** (M01, rpm=0, torque=0): Actual = 0.000200 kWh, Expected = 0.000194 kWh (Deviation: +3.09%)
- **DEGRADED** (M03, wear=high): Actual = 0.005760 kWh, Expected = 0.005740 kWh (Deviation: +0.35%)
- **OVERLOAD** (M02, load=heavy): Actual = 0.006770 kWh, Expected = 0.006815 kWh (Deviation: -0.66%)

Physical hierarchy holds consistently: $E_{\text{SLEEP}} < E_{\text{IDLE}} < E_{\text{RUNNING}}$.

### 6. Persisted Artifacts
- `models/energy_baseline_v1_power_based.joblib`: Preserved Phase 8 V1 model.
- `models/energy_baseline_v2_production_aware.joblib`: Phase 8.1 production-aware pipeline.
- `models/energy_baseline.joblib`: Primary active baseline (points to V2).
- `models/energy_baseline_metadata.json`: Complete audit metadata, splits, and parameters.
- `data/processed/baseline_experiment_results.json`: Full benchmark comparison log.

### 7. REST API Endpoints

#### Baseline Prediction (`POST /baseline/predict`)
```bash
curl -X POST "http://localhost:8000/baseline/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "machine_id": "M01",
    "machine_state": "RUNNING",
    "production_delta": 2,
    "production_rate": 120.0,
    "rpm": 1450.0,
    "torque_nm": 30.0,
    "temperature_c": 48.0,
    "vibration": 0.18,
    "dt_seconds": 2.0
  }'
```
Response:
```json
{
  "expected_energy_kwh": 0.002619,
  "model_name": "LinearRegression",
  "model_version": "v2_production_aware",
  "features_used": {
    "production_delta": 2.0,
    "production_rate": 120.0,
    "rpm": 1450.0,
    "torque_nm": 30.0,
    "temperature_c": 48.0,
    "vibration": 0.18,
    "machine_state": "RUNNING",
    "machine_id": "M01"
  },
  "status": "OK"
}
```

#### Energy Deviation (`POST /baseline/deviation`)
```bash
curl -X POST "http://localhost:8000/baseline/deviation" \
  -H "Content-Type: application/json" \
  -d '{
    "actual_energy_kwh": 0.003100,
    "expected_energy_kwh": 0.002619
  }'
```
Response:
```json

---

## 🔮 Phase 9: Energy Forecasting & Deviation Intelligence

Phase 9 establishes the forward-looking prediction and retrospective deviation layer of the Person 3 engine:
$$\text{FORECAST} \longrightarrow \text{DETECT} \longrightarrow \text{EXPLAIN}$$

### 1. Short-Horizon Energy Forecasting Engine
- **Aggregation Horizon**: Aggregates high-frequency 2-second telemetry into practical **1-minute energy consumption intervals** ($E_{\text{1min}} = \sum \Delta E_{2s}$), filtering high-frequency electrical noise while preserving operational state dynamics.
- **Forecasting Horizon**: Recursive multi-step projection supporting $t+1$ to $t+5$ intervals (1 to 5 minutes ahead).
- **Leakage Prevention**: All features are strictly backward-looking historical lags ($y_{t-1}, y_{t-2}, y_{t-3}$), rolling statistics (mean, std), and operational states. Targets are shifted strictly forward without future leakage.
- **Strict Chronological Validation**: 80/20 chronological train/test split with 5-fold `TimeSeriesSplit` cross-validation. Test set held out until final model evaluation.
- **Mandatory Benchmark & Metric**: Evaluated against the **Naive Persistence Forecaster** ($\hat{y}_{t+h} = y_t$) using **MASE** (Mean Absolute Scaled Error) alongside MAE, RMSE, and $R^2$.

#### Model Benchmark Results (1-minute Energy Forecast)

| Model | CV MAE (kWh) | CV RMSE (kWh) | CV $R^2$ | Test MAE (kWh) | Test RMSE (kWh) | Test $R^2$ | Test MASE | Status |
|---|---|---|---|---|---|---|---|---|
| **GradientBoostingRegressor** | **0.000156** | **0.000212** | **0.9998** | **0.004418** | **0.007629** | **0.9405** | **0.0667** | **Selected** |
| Random Forest Regressor | 0.000171 | 0.000224 | 0.9998 | 0.005120 | 0.008431 | 0.9273 | 0.0773 | Evaluated |
| XGBoost Regressor | 0.000210 | 0.000275 | 0.9996 | 0.006240 | 0.010150 | 0.8948 | 0.0942 | Evaluated |
| Moving Average (MA-3) | 0.018940 | 0.024100 | 0.6520 | 0.045100 | 0.052300 | 0.3800 | 0.6810 | Baseline |
| Naive Persistence | 0.020212 | 0.027510 | 0.5401 | 0.066230 | 0.074520 | 0.2205 | 1.0000 | Benchmark |
| Ridge Regression | 0.025340 | 0.031200 | 0.4900 | 0.071200 | 0.082100 | 0.1800 | 1.0750 | Evaluated |

*GradientBoostingRegressor achieved a **93.3% error reduction** over Naive Persistence ($\text{MASE} = 0.0667 \ll 1.0$).*

---

### 2. Energy Deviation Intelligence
Uses the Phase 8.1 retrospective production-aware baseline:
$$\text{deviation\_kwh} = \text{actual\_energy} - \text{expected\_energy}$$
$$\text{deviation\_pct} = \frac{\text{deviation\_kwh}}{\text{expected\_energy}} \times 100$$

- **Deterministic Terminology**: Clear industrial semantics (`above-baseline consumption`, `below-baseline consumption`, `energy deviation`).
- **Persistent Deviation Detector**:
  - Prevents single-interval sensor noise from triggering false alarms.
  - Requires $N$ consecutive intervals ($N=3$, default) exceeding configurable threshold ($\pm 15.0\%$) to trigger `PERSISTENT_ABOVE_BASELINE`.
  - State classifications: `NORMAL`, `ABOVE_BASELINE`, `PERSISTENT_ABOVE_BASELINE`, `BELOW_BASELINE`.
- **Machine Contribution Analysis**:
  - Quantifies each machine's contribution to factory-level positive energy deviation:
    $$\text{contribution\_pct} = \frac{\max(0, \text{deviation\_kwh}_i)}{\sum \max(0, \text{deviation\_kwh}_j)} \times 100$$
  - Safely handles zero or negative total deviation denominators.
- **Operational State-Level Aggregation**:
  - Breaks down actual vs expected energy across states (`RUNNING`, `IDLE`, `SLEEP`, `DEGRADED`, `OVERLOAD`).

---

### 3. Phase 9 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/forecast/machine/{machine_id}` | Short-horizon multi-step forecast (1 to 5 min) for a machine |
| `GET` | `/forecast/factory` | Aggregated factory-wide forecast across all machines |
| `GET` | `/deviation/machine/{machine_id}` | Actual vs expected deviation with persistence detection |
| `GET` | `/deviation/factory` | Aggregated factory-level energy deviation |
| `GET` | `/deviation/contributors` | Machines ranked by % contribution to positive deviation |
| `GET` | `/deviation/states` | Energy deviation breakdown grouped by machine operating state |

---

## 💰 Phase 10: Savings Estimation, Efficiency Analytics & Optimization Intelligence

Phase 10 builds the business, operational efficiency, and financial intelligence layer:
$$\text{MEASURE} \longrightarrow \text{BASELINE} \longrightarrow \text{DEVIATION} \longrightarrow \text{IDENTIFY OPPORTUNITY} \longrightarrow \text{ESTIMATE SAVINGS} \longrightarrow \text{VERIFY SAVINGS}$$

### 1. Deterministic Savings Methodology
- **Gross Above-Baseline Energy**:
  $$\text{potential\_savings\_kwh} = \max(0, \text{actual\_energy\_kwh} - \text{expected\_energy\_kwh})$$
  *(Clamped strictly at zero; negative savings are never reported).*
- **Conservative Persistent Opportunity**:
  $$\text{persistent\_savings\_kwh} = \text{potential\_savings\_kwh} \quad \text{if } \text{status} == \text{PERSISTENT\_ABOVE\_BASELINE} \quad \text{else } 0$$
- **Configurable Demonstration Assumptions**:
  - Electricity Tariff: `8.00 INR/kWh` (configurable demonstration tariff assumption).
  - Grid Emission Factor: `0.716 kg CO₂/kWh` (CEA India baseline reference).
  - $\text{savings\_inr} = \text{savings\_kwh} \times \text{tariff}$
  - $\text{co2\_savings\_kg} = \text{savings\_kwh} \times \text{emission\_factor}$

---

### 2. Production-Normalized Efficiency (SEC)
- Specific Energy Consumption:
  $$\text{SEC} = \frac{\text{energy\_kwh}}{\text{production\_units}} \quad (\text{kWh/unit})$$
  *(Safe handling: when production units = 0, SEC is reported as `null` / `None`, never zero or division-by-zero error).*
- Production-Normalized Savings Verification (IPMVP-Inspired Engineering Standard):
  $$\text{expected\_post\_energy} = \text{post\_production} \times \text{baseline\_sec}$$
  $$\text{normalized\_savings\_kwh} = \max(0, \text{expected\_post\_energy} - \text{post\_actual\_energy})$$
  $$\text{sec\_improvement\_pct} = \frac{\text{baseline\_sec} - \text{post\_sec}}{\text{baseline\_sec}} \times 100$$
- **Deterministic Verification Statuses**:
  - `NO_BASELINE`: Baseline energy or production is zero or missing.
  - `INSUFFICIENT_DATA`: Intervals or post-production below statistical minimum requirements.
  - `NO_IMPROVEMENT`: Post-intervention SEC is greater than or equal to baseline SEC.
  - `IMPROVEMENT_DETECTED`: Positive SEC reduction, but below verification threshold ($< 2\%$).
  - `SAVINGS_VERIFIED`: Significant positive SEC reduction ($\ge 2\%$) with verified production.

---

### 3. Financial Payback & ROI
- Annualized Savings:
  $$\text{annual\_savings\_inr} = \text{monthly\_savings\_inr} \times 12$$
- Simple Payback Horizon:
  $$\text{payback\_months} = \frac{\text{implementation\_cost\_inr}}{\text{monthly\_savings\_inr}}$$
  *(Returns `null` if monthly savings $\le 0$ or implementation cost is not provided; never fabricates costs).*

---

### 4. Optimization Opportunity Engine
Deterministic evidence-based rule generator prioritizing operational investigations (without controlling machines or diagnosing faults):
1. **Persistent Above-Baseline Energy**: Sustained $>15\%$ excess over expected baseline.
2. **Significant Idle Energy**: IDLE state energy $>15\%$ of machine total.
3. **Elevated SEC**: Observed SEC exceeds baseline expected SEC by $>10\%$.
4. **Degraded State with Excess Consumption**: Operating in DEGRADED mode with positive deviation.
5. **Throughput Efficiency Escalation**: High volume production accompanied by escalating SEC.

*Priority Score (0 to 100)*: Represents **energy-efficiency investigation priority** (NOT machine failure probability).

---

### 5. Phase 10 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/savings/factory` | Factory aggregated potential & persistent savings opportunity |
| `GET` | `/savings/machine/{machine_id}` | Machine potential savings, persistent opportunity, and SEC gap |
| `GET` | `/savings/states` | Energy savings and positive deviation by operating state |
| `GET` | `/efficiency/factory` | Factory-wide production-normalized efficiency and SEC |
| `GET` | `/efficiency/machine/{machine_id}` | Machine-level production-normalized efficiency and SEC |
| `GET` | `/machines/{machine_id}/savings` | Legacy endpoint preserved for backwards compatibility |

---

## 🤖 Phase 11: Energy Copilot / Natural-Language Energy Intelligence

Phase 11 establishes the natural-language conversational interface over the authoritative deterministic analytics engine:
$$\text{User Query} \longrightarrow \text{Intent Routing} \longrightarrow \text{Context Builder} \longrightarrow \text{Authoritative Analytics} \longrightarrow \text{Qwen3 1.7B / Ollama} \longrightarrow \text{Validation} \longrightarrow \text{Grounded Answer}$$

### 1. Fundamental Principle: The LLM is NOT the Source of Truth
- **Authoritative Calculations:** All numbers (energy, baseline, deviation, SEC, savings, cost in ₹, avoided carbon, forecast) are computed deterministically in Python. The LLM is strictly prohibited from performing independent arithmetic or inventing figures.
- **Role of the LLM:** Summarize, explain, compare, contextualize, and frame actionable recommendations from the supplied evidence.
- **Fault-Tolerant Deterministic Fallback:** If Ollama is offline, times out, or if output fails post-generation validation, the Copilot seamlessly generates an authoritative Python-derived response without crashing FastAPI.

---

### 2. Intent Routing & Context Selection
Incoming queries are classified using a deterministic intent router:
- `FACTORY_SUMMARY`: Overall factory KPIs, energy, baseline, SEC, and total savings opportunity.
- `MACHINE_ANALYSIS`: Specific machine performance, state, deviation, and operational parameters.
- `ENERGY_DEVIATION`: Analysis of above-baseline or below-baseline consumption gaps.
- `SAVINGS`: Potential savings, monthly/annual financial projections (₹), and avoided CO₂.
- `EFFICIENCY`: Specific Energy Consumption (SEC in kWh/unit) and production intensity.
- `FORECAST`: Phase 9 short-horizon projection (1 to 5 intervals, 1-minute each).
- `OPPORTUNITIES`: Prioritized investigation targets from the Phase 10 opportunity engine.
- `VERIFICATION`: Production-normalized before/after savings verification and status.
- `MACHINE_HEALTH_CONTEXT`: Operational condition indicators (temperature, vibration, state) without fault claims.
- `GENERAL`: Broad conversational queries grounded in active telemetry.

---

### 3. Hallucination Defense & Boundary Enforcement
Every generated response passes post-generation validation:
1. **Numeric Grounding Validation:** Checks that cited numerical values (kWh, %, ₹, kg) match the authoritative analytics context within numerical tolerance.
2. **Machine-Health Boundary (Person 2):** Prohibits diagnosing component failures or claiming failure probabilities (e.g. rejects "bearing failure" or "motor will fail in X days").
3. **Machine-Control Boundary (Person 1):** Prohibits issuing direct machine control commands (e.g. rejects "shut down the machine immediately"). Recommendations are framed strictly as operational investigation opportunities.
4. **Causation Guard:** Rejects claims of certainty about unproven causal links (e.g. rejects "the excess energy is definitely caused by...").

---

### 4. Phase 11 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/copilot/chat` | Natural-language query interface grounded in factory analytics |
| `GET` | `/copilot/summary` | Executive factory energy performance summary |
| `POST` | `/copilot/machine/{machine_id}` | Machine-specific performance query |
| `POST` | `/copilot/query` | Legacy query endpoint preserved for backwards compatibility |

---

### 5. Running the Interactive Copilot Demo
```bash
python scripts/demo_copilot.py
```
Demonstrates queries across factory performance, prioritization, savings estimation, and machine investigation.

---

## ⚡ Phase 12: Unified End-to-End Demonstration, Integration & Dashboard

Phase 12 unifies all components into a coherent, production-grade Smart Manufacturing demonstration.

### 1. Unified End-to-End Pipeline
```
[Simulator M01–M04] → [MQTT Pub/Sub] → [FastAPI] → [Database] → [Analytics Engine] → [ML Baseline & Forecast] → [Savings & Opportunities] → [AI Copilot] → [Streamlit Dashboard]
```

### 2. Phase 12 Demonstration API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/demo/status` | Live demonstration execution state, scenario phase, and subsystem connectivity |
| `GET` | `/demo/factory` | Unified factory intelligence snapshot combining analytics, baseline, forecast, savings, and opportunities |
| `GET` | `/demo/machine/{machine_id}` | Unified machine-level profile with Person 2 health context |

### 3. Interactive Smart Manufacturing Dashboard (`dashboard/app.py`)
Built with Streamlit and Plotly, the dashboard provides a unified operational command center across 9 core sections:
1. **Factory Overview:** Real-time KPI metric cards (Energy, Production, SEC, Cost, CO₂, Utilization, Savings).
2. **Energy vs Production:** Production-normalized correlation analysis.
3. **Actual vs Baseline:** Grouped comparative chart distinguishing Normal, Above Baseline, and Persistent Above Baseline.
4. **Machine Fleet Table:** Asset-level tabular status with Person 2 health scores.
5. **Energy State Breakdown:** Donut chart of energy by operating state (Running, Idle, Sleep, Degraded, Overload).
6. **Short-Horizon Forecast:** Multi-step forward energy projection (1–5 minutes ahead).
7. **Savings Intelligence:** Potential above-baseline savings vs verified post-intervention savings.
8. **Optimization Opportunities:** Prioritized energy efficiency recommendations.
9. **AI Copilot:** Natural-language question and answer grounded in authoritative analytics.

### 4. Running the Demonstration
```bash
# 1. Run the end-to-end pipeline runner
python scripts/run_factory_demo.py

# 2. Launch the dashboard
streamlit run dashboard/app.py
```

---

## How the Energy Intelligence Copilot Works

The Grounded Energy Intelligence Copilot provides natural-language insight into factory energy dynamics while strictly eliminating numerical hallucinations:

```
User Message
     │
     ▼
Intent Detection (classify_intent)
     │
     ├── If GENERAL_CHAT ──────────► Conversational capabilities without fake analytics
     │
     └── If INDUSTRIAL DOMAIN ─────► Fetch Authoritative Analytics Context
                                           │
                                           ▼
                                 Qwen3 1.7B (via Ollama)
                                           │
                                  (Fallback if offline)
                                           ▼
                                 Deterministic Analytic Engine
                                           │
                                           ▼
                                 Grounding Validation (Reconciliation Check)
                                           │
                                           ▼
                                 Conversational Response to UI
```

### Critical Architectural Principle: The LLM is NOT the Source of Truth
- **Authoritative Source:** Python analytics (`analytics/`, `ml/`, `database/`) calculate all energy, production, SEC, baseline deviations, forecasts, and savings.
- **LLM Role:** The LLM (or deterministic fallback) acts solely as a natural-language interpreter and synthesiser. It translates pre-calculated mathematical facts into contextual operational insights.
- **Hallucination Prevention:** The Copilot never fabricates numerical values. If production output is zero, it explicitly states: *"Production is 0 in the current analysis window, so SEC cannot be calculated."*
- **Responsibility Boundaries:** The Copilot never issues direct machine control commands (owned by Person 1) or mechanical fault diagnoses (owned by Person 2).

---

## Phase 13.1 Verification Summary
- **Test Suite Status:** 331 tests passing, 0 failing (100% pass rate).
- **Consistency Verification:** `scripts/validate_dashboard_consistency.py` verifies all 12 mathematical and data-window reconciliation checkpoints.
- **Conversational Demo:** `scripts/demo_copilot_conversation.py` validates multi-turn conversational continuity.



