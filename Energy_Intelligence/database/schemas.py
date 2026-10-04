"""
Canonical Industrial Telemetry Schema & API Data Contracts.
Defines Pydantic models for real-time telemetry validation, serialization,
and interoperability across Person 1, Person 2, Person 3, and Person 4.
"""

from enum import Enum
from typing import Optional, Any, Dict, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict, field_validator

from simulator.machine_states import MachineState


class TelemetrySource(str, Enum):
    """Origin of the telemetry data stream."""
    SIMULATOR = "simulator"
    SENSOR = "sensor"
    PLC = "plc"
    GATEWAY = "gateway"
    EXTERNAL = "external"


class TelemetryRecord(BaseModel):
    """
    Canonical Telemetry Record.
    Represents an industrial measurement event emitted by a machine, gateway, or simulator.
    Strictly validated for downstream SEC calculations, baseline ML, savings tracking, and health correlation.
    """
    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=False,
        populate_by_name=True,
    )

    # ==========================================
    # 1. CORE REQUIRED TELEMETRY
    # ==========================================
    timestamp: datetime = Field(
        ...,
        description="Event measurement timestamp (ISO 8601, UTC preferred)",
    )
    machine_id: str = Field(
        ...,
        description="Unique machine identifier (e.g., M01, CNC-02)",
        examples=["M01"],
    )
    power_kw: float = Field(
        ...,
        ge=0.0,
        description="Instantaneous / interval average active power demand in kW",
        examples=[7.8],
    )
    energy_kwh: float = Field(
        ...,
        ge=0.0,
        description="Cumulative active electrical energy meter reading in kWh",
        examples=[125.6],
    )
    machine_state: MachineState = Field(
        ...,
        description="Current operational state of the machine (from simulator.machine_states)",
        examples=[MachineState.RUNNING],
    )

    # ==========================================
    # 2. PRODUCTION FIELDS (Optional)
    # ==========================================
    # Production Count Semantics:
    # - production_count: Cumulative parts counter since shift/job start (monotonically non-decreasing integer).
    # - production_delta: Units produced strictly during this telemetry reporting interval.
    production_count: Optional[int] = Field(
        default=None,
        ge=0,
        description="Cumulative parts counter since shift / batch start",
        examples=[120],
    )
    production_delta: Optional[int] = Field(
        default=None,
        ge=0,
        description="Units produced during this specific telemetry interval",
        examples=[1],
    )
    cycle_time_sec: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Duration of the most recently completed production cycle in seconds (0.0 allowed if no cycle finished)",
        examples=[30.0],
    )

    # ==========================================
    # 3. SENSOR & ELECTRICAL FIELDS (Optional)
    # ==========================================
    voltage_v: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="RMS line-to-line or phase voltage in Volts",
        examples=[415.0],
    )
    current_a: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="RMS current draw in Amperes",
        examples=[12.4],
    )
    temperature_c: Optional[float] = Field(
        default=None,
        ge=-50.0,
        le=300.0,
        description="Machine motor / spindle temperature in Celsius (-50C to 300C)",
        examples=[52.4],
    )
    vibration: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Vibration velocity RMS or acceleration in mm/s or g",
        examples=[0.18],
    )
    rpm: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Spindle or drive shaft rotational speed in RPM",
        examples=[1450.0],
    )
    torque_nm: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Instantaneous motor torque in Newton-meters (Nm)",
        examples=[42.5],
    )

    # ==========================================
    # 4. HEALTH & ANOMALY FIELDS (From Person 2 - Optional)
    # ==========================================
    health_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Overall machine condition score (0 = critical fault, 100 = optimal)",
        examples=[94.0],
    )
    anomaly_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Anomaly probability score from predictive maintenance model (0.0 to 1.0)",
        examples=[0.08],
    )

    # ==========================================
    # 5. METADATA & VERSIONING
    # ==========================================
    source: TelemetrySource = Field(
        default=TelemetrySource.SIMULATOR,
        description="Origin source of the telemetry reading",
    )
    schema_version: str = Field(
        default="1.0",
        description="Telemetry contract schema version",
    )

    # ==========================================
    # VALIDATORS
    # ==========================================
    @field_validator("timestamp")
    @classmethod
    def normalize_timestamp_utc(cls, v: datetime) -> datetime:
        """Enforce timezone awareness and normalize to UTC."""
        if v.tzinfo is None:
            # Assume UTC if naive
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)

    @field_validator("machine_id")
    @classmethod
    def sanitize_machine_id(cls, v: str) -> str:
        """Strip whitespace and reject empty string IDs."""
        clean = v.strip()
        if not clean:
            raise ValueError("machine_id must be a non-empty string")
        return clean


class TelemetryIngestResponse(BaseModel):
    """API response model after validating incoming telemetry."""
    status: str = "accepted"
    machine_id: str
    timestamp: datetime
    message: str = "Telemetry accepted"


# Alias for explicit naming
TelemetryAcceptedResponse = TelemetryIngestResponse


class HealthResponse(BaseModel):
    """Health check response schema."""
    status: str = "healthy"
    service: str = "person3-energy-intelligence"
    version: str = "1.0.0"
    uptime_seconds: Optional[float] = None
    telemetry_store_count: int = 0
    mqtt_status: str = "DISCONNECTED"


class MachineSummary(BaseModel):
    """Unified machine overview separating static configuration from observed telemetry."""
    machine_id: str
    name: str
    rated_power_kw: float
    nominal_uph: Optional[float] = None
    last_seen: Optional[datetime] = None
    machine_state: Optional[MachineState] = None
    current_power_kw: Optional[float] = None
    current_energy_kwh: Optional[float] = None
    total_telemetry_count: int = 0


class FactorySnapshot(BaseModel):
    """Aggregated real-time factory snapshot directly derivable from latest telemetry."""
    timestamp: datetime
    machines_seen: int
    machines_running: int
    machines_idle: int
    machines_sleep: int
    machines_degraded: int
    machines_overload: int
    total_power_kw: float
    total_production: Optional[int] = None


# ==========================================
# MACHINE ASSET SCHEMAS (Preserved from Phase 1)
# ==========================================
class MachineBase(BaseModel):
    id: str
    name: str
    rated_power_kw: float = 7.5


class MachineResponse(MachineBase):
    model_config = ConfigDict(from_attributes=True)
    created_at: Optional[datetime] = None


# ==========================================
# PERSON 2: MACHINE HEALTH CONTRACT
# ==========================================
class MachineHealthMessage(BaseModel):
    """
    Health telemetry message contract emitted by Person 2 (Condition Monitoring).
    Published over factory/{machine_id}/health.
    """
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    timestamp: datetime = Field(..., description="Measurement timestamp (UTC)")
    machine_id: str = Field(..., description="Machine asset ID")
    health_score: float = Field(..., ge=0.0, le=100.0, description="Condition health index (0-100)")
    anomaly_score: float = Field(..., ge=0.0, le=1.0, description="Predictive anomaly probability (0.0-1.0)")
    temperature_c: Optional[float] = Field(default=None, description="Measured temperature in Celsius")
    vibration: Optional[float] = Field(default=None, ge=0.0, description="Vibration RMS velocity in mm/s")
    rpm: Optional[float] = Field(default=None, ge=0.0, description="Rotational speed in RPM")

    @field_validator("timestamp")
    @classmethod
    def normalize_timestamp_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)

    @field_validator("machine_id")
    @classmethod
    def sanitize_machine_id(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("machine_id must be a non-empty string")
        return clean


# ==========================================
# PERSON 1: OPTIMIZATION ACTION CONTRACT
# ==========================================
class MachineActionType(str, Enum):
    SLEEP = "SLEEP"
    WAKE = "WAKE"
    SET_LOAD = "SET_LOAD"
    STOP = "STOP"
    START = "START"


class MachineActionMessage(BaseModel):
    """
    Optimization action message contract emitted by Person 1 (Energy Optimization).
    Published over factory/{machine_id}/action.
    """
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    timestamp: datetime = Field(..., description="Action timestamp (UTC)")
    machine_id: str = Field(..., description="Target machine asset ID")
    action: MachineActionType = Field(..., description="Optimization command type")
    duration_sec: Optional[int] = Field(default=None, ge=0, description="Intended action duration in seconds")
    reason: Optional[str] = Field(default=None, description="Human/algorithm explanation for optimization action")

    @field_validator("timestamp")
    @classmethod
    def normalize_timestamp_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)

    @field_validator("machine_id")
    @classmethod
    def sanitize_machine_id(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("machine_id must be a non-empty string")
        return clean


# ==========================================
# PHASE 7: DETERMINISTIC ENERGY ANALYTICS SCHEMAS
# ==========================================

class StateEnergyBreakdown(BaseModel):
    """Energy and duration distribution across operational states."""
    running: float = 0.0
    idle: float = 0.0
    sleep: float = 0.0
    degraded: float = 0.0
    overload: float = 0.0

    # Detailed unit-annotated breakdown
    running_energy_kwh: float = 0.0
    idle_energy_kwh: float = 0.0
    sleep_energy_kwh: float = 0.0
    degraded_energy_kwh: float = 0.0
    overload_energy_kwh: float = 0.0

    # Operational times (hours)
    running_time_hours: float = 0.0
    idle_time_hours: float = 0.0
    sleep_time_hours: float = 0.0
    degraded_time_hours: float = 0.0
    overload_time_hours: float = 0.0

    # Idle & Sleep specific metrics for Person 1 energy optimization
    idle_power_average_kw: float = 0.0
    idle_energy_pct: float = 0.0
    sleep_energy_pct: float = 0.0


class DataQualityReport(BaseModel):
    """Transparency report on telemetry reliability, anomalies, and calculation method."""
    status: str = "OK"  # OK, INSUFFICIENT_DATA, INVALID_NON_MONOTONIC_ENERGY, PRODUCTION_UNAVAILABLE, PRODUCTION_COUNTER_RESET, ENERGY_COUNTER_RESET, INVALID_TIME_RANGE
    calculation_method: str = "METER_DELTA"  # METER_DELTA or POWER_INTEGRATION
    warnings: list[str] = []


class MachineEnergyAnalysis(BaseModel):
    """Deterministic energy and production performance analysis for an individual machine."""
    machine_id: str
    start_time: datetime
    end_time: datetime
    elapsed_hours: float

    # Core energy & production KPIs
    energy_kwh: Optional[float] = None
    production_units: Optional[int] = None
    production_rate_units_per_hour: Optional[float] = None

    # Efficiency indicators
    sec_kwh_per_unit: Optional[float] = None
    utilization_pct: Optional[float] = None

    # State breakdown
    state_energy: StateEnergyBreakdown = Field(default_factory=StateEnergyBreakdown)

    # Cost & Environmental metrics
    energy_cost_inr: Optional[float] = None
    electricity_rate_inr_per_kwh: float = 8.50
    co2_kg: Optional[float] = None
    grid_emission_factor_kg_per_kwh: float = 0.716

    # Quality metadata
    data_quality: DataQualityReport = Field(default_factory=DataQualityReport)


class FactoryEnergyAnalysis(BaseModel):
    """Aggregate deterministic factory-wide energy and production intelligence."""
    start_time: datetime
    end_time: datetime
    elapsed_hours: float
    machines_analyzed_count: int

    total_factory_energy_kwh: Optional[float] = None
    total_factory_production_units: Optional[int] = None
    factory_sec_kwh_per_unit: Optional[float] = None
    factory_utilization_pct: Optional[float] = None

    state_energy: StateEnergyBreakdown = Field(default_factory=StateEnergyBreakdown)

    total_energy_cost_inr: Optional[float] = None
    total_co2_kg: Optional[float] = None

    machines: list[MachineEnergyAnalysis] = []
    data_quality: DataQualityReport = Field(default_factory=DataQualityReport)


# ==========================================
# ==========================================
# 7. PHASE 8 / 8.1 — ENERGY BASELINE MODEL SCHEMAS
# ==========================================

class BaselinePredictionRequest(BaseModel):
    """
    Input features for production-aware energy baseline prediction (V2).
    Accepts operational conditions and production parameters.
    Does NOT require power_kw or energy_kwh.
    """
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    machine_id: str = Field(default="M01", description="Machine identifier (e.g. M01)")
    machine_state: MachineState = Field(default=MachineState.RUNNING, description="Machine operational state")
    production_delta: int = Field(default=0, ge=0, description="Units produced during interval")
    production_rate: Optional[float] = Field(default=None, ge=0.0, description="Production rate (units/hr)")
    production_rate_units_per_hour: Optional[float] = Field(default=None, ge=0.0, description="Alias for production_rate (units/hr)")
    dt_seconds: float = Field(default=2.0, gt=0.0, description="Interval duration in seconds")

    # Mechanical, Thermal & Operational features
    rpm: Optional[float] = Field(default=1450.0, ge=0.0, description="Motor speed (RPM)")
    torque_nm: Optional[float] = Field(default=0.0, ge=0.0, description="Motor torque (Nm)")
    temperature_c: Optional[float] = Field(default=50.0, description="Machine temperature (°C)")
    vibration: Optional[float] = Field(default=0.18, ge=0.0, description="Vibration RMS (mm/s)")
    health_score: Optional[float] = Field(default=100.0, ge=0.0, le=100.0, description="Machine health score (0-100)")
    anomaly_score: Optional[float] = Field(default=0.0, ge=0.0, description="Anomaly score")
    hour_of_day: Optional[float] = Field(default=12.0, ge=0.0, le=24.0, description="Hour of day (0-24)")
    hour: Optional[float] = Field(default=None, ge=0.0, le=24.0, description="Alias for hour_of_day (0-24)")
    day_of_week: Optional[float] = Field(default=2.0, ge=0.0, le=6.0, description="Day of week (0=Mon, 6=Sun)")

    # Optional legacy/electrical fields (ignored by V2 production-aware model)
    power_kw: Optional[float] = Field(default=None, ge=0.0, description="Active power demand in kW (ignored by V2 model)")
    voltage_v: Optional[float] = Field(default=None, ge=0.0, description="Line voltage (V) (ignored by V2 model)")
    current_a: Optional[float] = Field(default=None, ge=0.0, description="Current (A) (ignored by V2 model)")


class BaselinePredictionResponse(BaseModel):
    """
    Response schema for production-aware energy baseline prediction.
    """
    expected_energy_kwh: float = Field(..., ge=0.0, description="Predicted baseline energy for interval in kWh")
    model_name: str = Field(..., description="Name of selected estimator")
    model_version: str = Field(default="v2_production_aware", description="Model version")
    features_used: dict = Field(default_factory=dict, description="Operational features passed to estimator")
    status: str = Field(default="OK", description="Inference status")


class EnergyDeviationRequest(BaseModel):
    """
    Request schema for calculating energy deviation between actual and expected energy.
    """
    actual_energy_kwh: float = Field(..., ge=0.0, description="Measured actual interval energy consumption in kWh")
    expected_energy_kwh: float = Field(..., ge=0.0, description="Predicted baseline expected energy in kWh")


class EnergyDeviationResponse(BaseModel):
    """
    Response schema for energy deviation analysis.
    """
    actual_energy_kwh: float = Field(..., ge=0.0, description="Actual energy consumed in kWh")
    expected_energy_kwh: float = Field(..., ge=0.0, description="Expected baseline energy in kWh")
    deviation_kwh: float = Field(..., description="Energy deviation (actual - expected) in kWh")
    deviation_pct: float = Field(..., description="Percentage deviation from baseline (%)")
    is_above_baseline: bool = Field(..., description="True if actual consumption exceeded baseline")
    status: str = Field(default="OK", description="Analysis status")


# ==========================================
# 8. PHASE 9 — FORECASTING & DEVIATION INTELLIGENCE SCHEMAS
# ==========================================

class MachineForecastResponse(BaseModel):
    """
    Short-horizon energy forecast for an individual machine.
    """
    machine_id: str
    horizon_minutes: int
    forecast_interval_minutes: int = 1
    forecast_energy_kwh: list[float]
    total_forecast_kwh: Optional[float] = None
    model: str
    model_version: str = "v1"
    status: str = "OK"
    disclaimer: str = (
        "Forecast indicates estimated future consumption under current operating dynamics; "
        "not a guaranteed future event."
    )


class FactoryForecastResponse(BaseModel):
    """
    Aggregated short-horizon energy forecast across the entire factory.
    """
    horizon_minutes: int
    forecast_interval_minutes: int = 1
    total_factory_forecast_kwh: float
    factory_step_forecasts_kwh: list[float]
    machine_forecasts: dict[str, Any]
    model: str
    model_version: str = "v1"
    status: str = "OK"
    disclaimer: str = (
        "Forecast indicates estimated future consumption under current operating dynamics; "
        "not a guaranteed future event."
    )


class MachineDeviationStatusResponse(BaseModel):
    """
    Machine-level deviation response combining Phase 8.1 expected baseline with
    deterministic persistence intelligence.
    """
    machine_id: str
    actual_energy_kwh: float
    expected_energy_kwh: float
    deviation_kwh: float
    deviation_pct: float
    status: str  # NORMAL, ABOVE_BASELINE, PERSISTENT_ABOVE_BASELINE, BELOW_BASELINE
    persistent_intervals: int = 0
    interpretation: Optional[str] = None


class FactoryDeviationStatusResponse(BaseModel):
    """
    Factory-level total deviation between actual and expected energy.
    """
    factory_actual_energy_kwh: float
    factory_expected_energy_kwh: float
    factory_deviation_kwh: float
    factory_deviation_pct: float
    status: str
    machine_count: int


class DeviationContributor(BaseModel):
    """
    Machine contribution to factory-level positive energy deviation.
    """
    machine_id: str
    actual_energy_kwh: float
    expected_energy_kwh: float
    deviation_kwh: float
    deviation_pct: float
    contribution_pct: float


class FactoryContributorsResponse(BaseModel):
    """
    Ranking of machines by contribution to positive factory energy deviation.
    """
    factory_deviation_kwh: float
    total_positive_factory_deviation: float
    contributors: list[DeviationContributor]


class StateDeviationItem(BaseModel):
    """
    Deviation analysis for an individual operational state.
    """
    state: str
    actual_energy_kwh: float
    expected_energy_kwh: float
    deviation_kwh: float
    deviation_pct: float


class StateDeviationsResponse(BaseModel):
    """
    State-level energy deviation breakdown across all operating states.
    """
    total_actual_kwh: float
    total_expected_kwh: float
    total_deviation_kwh: float
    states: list[StateDeviationItem]


# ==========================================
# 9. PHASE 10 — SAVINGS ESTIMATION & EFFICIENCY INTELLIGENCE SCHEMAS
# ==========================================

class FactorySavingsResponse(BaseModel):
    """
    Factory-wide aggregated potential and persistent savings opportunity.
    """
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    actual_energy_kwh: float
    expected_energy_kwh: float
    above_baseline_kwh: float
    potential_savings_kwh: Optional[float] = None
    persistent_opportunity_kwh: float
    savings_rate_pct: float
    baseline_gap_pct: float
    potential_savings_inr: float
    persistent_savings_inr: float
    potential_co2_savings_kg: float
    persistent_co2_savings_kg: float
    tariff_inr_per_kwh: float
    emission_factor_kg_per_kwh: float
    machine_count: int = 0
    tariff_label: str = "Configurable demonstration tariff"
    emission_factor_label: str = "Configurable demonstration grid emission factor"


class MachineSavingsResponse(BaseModel):
    """
    Machine-level potential and persistent savings opportunity.
    """
    machine_id: str
    actual_energy_kwh: float
    expected_energy_kwh: float
    deviation_kwh: float
    potential_savings_kwh: float
    persistent_opportunity_kwh: float
    savings_rate_pct: float
    baseline_gap_pct: float
    potential_savings_inr: float
    persistent_savings_inr: float
    potential_co2_savings_kg: float
    persistent_co2_savings_kg: float
    total_production_units: int
    actual_sec_kwh_per_unit: Optional[float] = None
    expected_sec_kwh_per_unit: Optional[float] = None
    sec_gap_kwh_per_unit: Optional[float] = None
    deviation_status: str = "NORMAL"
    persistent_intervals: int = 0
    tariff_inr_per_kwh: float
    emission_factor_kg_per_kwh: float


class StateSavingsItem(BaseModel):
    """
    Savings potential broken down by machine operational state.
    """
    machine_state: str
    actual_energy_kwh: float
    expected_energy_kwh: float
    deviation_kwh: float
    positive_deviation_kwh: float
    potential_savings_kwh: float
    potential_savings_inr: float
    potential_co2_savings_kg: float
    production_units: int
    sec_kwh_per_unit: Optional[float] = None


class StateSavingsResponse(BaseModel):
    """
    State-level savings breakdown response across all states.
    """
    total_actual_kwh: float
    total_expected_kwh: float
    total_deviation_kwh: float
    total_positive_deviation_kwh: float
    total_potential_savings_inr: float
    total_potential_co2_savings_kg: float
    states: list[StateSavingsItem]


class MachineEfficiencyResponse(BaseModel):
    """
    Production-normalized machine efficiency metrics and SEC.
    """
    machine_id: str
    production_units: int
    actual_energy_kwh: float
    expected_energy_kwh: float
    actual_sec_kwh_per_unit: Optional[float] = None
    expected_sec_kwh_per_unit: Optional[float] = None
    sec_gap_kwh_per_unit: Optional[float] = None
    sec_improvement_pct: Optional[float] = None
    potential_savings_kwh: float
    potential_savings_inr: float
    potential_co2_savings_kg: float
    sample_count: int


class FactoryEfficiencyResponse(BaseModel):
    """
    Aggregated factory production-normalized efficiency and SEC.
    """
    production_units: int
    actual_energy_kwh: float
    expected_energy_kwh: float
    actual_sec_kwh_per_unit: Optional[float] = None
    expected_sec_kwh_per_unit: Optional[float] = None
    sec_gap_kwh_per_unit: Optional[float] = None
    sec_improvement_pct: Optional[float] = None
    potential_savings_kwh: float
    potential_savings_inr: float
    potential_co2_savings_kg: float
    machine_count: int
    machine_efficiencies: list[MachineEfficiencyResponse] = []


class SavingsVerificationRequest(BaseModel):
    """
    Input data for before/after production-normalized savings verification.
    """
    intervention_id: Optional[str] = Field(default="INT-001", description="Intervention identifier")
    machine_id: Optional[str] = Field(default="M01", description="Target machine ID")
    intervention_type: Optional[str] = Field(default="IDLE_REDUCTION", description="Intervention category")
    baseline_actual_energy_kwh: float = Field(..., ge=0.0, description="Total baseline energy consumed in kWh")
    baseline_production_units: float = Field(..., ge=0.0, description="Total units produced during baseline period")
    post_actual_energy_kwh: float = Field(..., ge=0.0, description="Total post-intervention energy in kWh")
    post_production_units: float = Field(..., ge=0.0, description="Total units produced during post-intervention period")
    baseline_intervals: int = Field(default=10, ge=1, description="Number of baseline observation intervals")
    post_intervals: int = Field(default=10, ge=1, description="Number of post-intervention observation intervals")
    min_intervals: int = Field(default=5, ge=1, description="Minimum intervals required for verification")
    min_production_units: float = Field(default=1.0, ge=0.0, description="Minimum production units required")
    significance_threshold_pct: float = Field(default=2.0, ge=0.0, description="Minimum SEC improvement % to declare SAVINGS_VERIFIED")
    tariff_inr: Optional[float] = Field(default=None, description="Optional custom tariff in INR/kWh")
    emission_factor_kg: Optional[float] = Field(default=None, description="Optional custom grid emission factor")
    implementation_cost_inr: Optional[float] = Field(default=None, ge=0.0, description="Optional intervention cost for payback ROI")


class SavingsVerificationResponse(BaseModel):
    """
    Results of production-normalized savings verification and ROI payback analysis.
    """
    status: str = Field(..., description="NO_BASELINE, INSUFFICIENT_DATA, NO_IMPROVEMENT, IMPROVEMENT_DETECTED, SAVINGS_VERIFIED")
    message: str
    baseline_sec: Optional[float] = None
    post_sec: Optional[float] = None
    sec_improvement_pct: Optional[float] = None
    expected_post_energy_kwh: Optional[float] = None
    post_actual_energy_kwh: float
    normalized_savings_kwh: float
    estimated_savings_inr: float
    estimated_co2_savings_kg: float
    payback_months: Optional[float] = None
    annual_savings_inr: Optional[float] = None
    tariff_inr_per_kwh: float
    emission_factor_kg_per_kwh: float
    assumptions: str


class OptimizationOpportunityItem(BaseModel):
    """
    Individual evidence-based energy optimization opportunity.
    """
    opportunity_id: str
    machine_id: str
    category: str
    condition: str
    reason: str
    supporting_metric: str
    suggested_action: str
    confidence: str
    priority_score: float
    priority_level: str
    estimated_monthly_savings_inr: float
    estimated_annual_savings_inr: float


class OptimizationOpportunitiesResponse(BaseModel):
    """
    Prioritized energy-efficiency investigation opportunities across the factory.
    """
    total_opportunities: int
    high_priority_count: int
    total_estimated_annual_savings_inr: float
    opportunities: list[OptimizationOpportunityItem]


# ==========================================
# 10. PHASE 11 — ENERGY COPILOT SCHEMAS
# ==========================================

class CopilotChatRequest(BaseModel):
    """
    User query request to the Energy Copilot.
    """
    question: str = Field(..., min_length=2, description="Natural language question about energy performance")
    machine_id: Optional[str] = Field(default=None, description="Optional target machine ID (e.g. M01)")
    history: Optional[List[Dict[str, str]]] = Field(default=None, description="Optional recent conversational history")


class CopilotMachineQueryRequest(BaseModel):
    """
    Machine-specific query request to the Energy Copilot.
    """
    question: str = Field(..., min_length=2, description="Natural language question specific to the machine")
    history: Optional[List[Dict[str, str]]] = Field(default=None, description="Optional recent conversational history")


class CopilotChatResponse(BaseModel):
    """
    Evidence-grounded response from the Energy Copilot.
    """
    answer: str = Field(..., description="Grounded natural language response")
    intent: str = Field(..., description="Classified intent category")
    grounded: bool = Field(default=True, description="True if answer validated against authoritative analytics")
    context_summary: Dict[str, Any] = Field(default_factory=dict, description="Summary of evidence context used")
    model_used: str = Field(default="qwen3:1.7b", description="Model name or deterministic fallback")
    fallback_used: bool = Field(default=False, description="True if deterministic analytics fallback was used")
    validation_passed: bool = Field(default=True, description="True if hallucination and boundary checks passed")


class CopilotSummaryResponse(BaseModel):
    """
    Concise executive factory energy summary generated by Energy Copilot.
    """
    timestamp: datetime = Field(..., description="Generation timestamp in UTC")
    factory_summary: str = Field(..., description="Grounded natural language executive summary")
    energy_kwh: float = Field(..., description="Actual factory energy consumed in kWh")
    expected_energy_kwh: float = Field(..., description="Production-aware baseline expected energy in kWh")
    potential_savings_kwh: float = Field(..., description="Gross above-baseline energy in kWh")
    potential_savings_inr: float = Field(..., description="Estimated cost savings in INR")
    actual_sec_kwh_per_unit: Optional[float] = Field(default=None, description="Factory Specific Energy Consumption")
    production_units: int = Field(default=0, description="Total units produced")
    top_opportunity: Optional[str] = Field(default=None, description="Top energy-efficiency investigation target")
    recommended_action: str = Field(..., description="Actionable next step recommendation")
    model_used: str = Field(default="qwen3:1.7b")


# ==========================================
# 11. PHASE 12 DEMONSTRATION & INTEGRATION SCHEMAS
# ==========================================

class DemoStatusResponse(BaseModel):
    """
    Live status of the factory demonstration runner and system pipelines.
    """
    status: str = Field(..., description="Operational status: IDLE, RUNNING, or COMPLETED")
    running: bool = Field(..., description="True if demonstration runner is currently active")
    elapsed_time_seconds: float = Field(..., description="Elapsed run duration in seconds")
    telemetry_count: int = Field(..., description="Total telemetry records ingested")
    latest_telemetry_timestamp: Optional[str] = Field(default=None, description="ISO timestamp of most recent telemetry event")
    machines_active: int = Field(default=4, description="Number of active machines monitored")
    current_scenario_phase: str = Field(..., description="Current scenario phase: PHASE_A_NORMAL, etc.")
    database_connected: bool = Field(..., description="True if database is connected")
    mqtt_connected: bool = Field(..., description="True if MQTT subscriber/pipeline is connected")
    demo_mode: bool = Field(default=True, description="True if running in demonstration mode")


class DemoFactorySnapshotResponse(BaseModel):
    """
    Unified end-to-end factory intelligence snapshot combining analytics, baseline,
    forecast, savings, efficiency, and optimization opportunities.
    """
    timestamp: datetime = Field(..., description="Snapshot timestamp in UTC")
    machines: List[str] = Field(..., description="List of monitored machine identifiers")
    production: Dict[str, Any] = Field(..., description="Factory-wide production metrics")
    energy: Dict[str, Any] = Field(..., description="Factory-wide electrical energy metrics")
    sec: Optional[float] = Field(default=None, description="Factory Specific Energy Consumption in kWh/unit")
    utilization: float = Field(..., description="Factory operational utilization rate (0.0 to 1.0)")
    baseline: Dict[str, Any] = Field(..., description="Expected-energy baseline metrics")
    deviation: Dict[str, Any] = Field(..., description="Actual vs expected baseline deviation analysis")
    forecast: Dict[str, Any] = Field(..., description="Short-horizon 1-5 minute future energy forecast")
    savings: Dict[str, Any] = Field(..., description="Identified potential and verified savings")
    efficiency: Dict[str, Any] = Field(..., description="Process efficiency ratings and SEC indices")
    optimization_opportunities: List[Dict[str, Any]] = Field(default_factory=list, description="Prioritized energy optimization opportunities")
    machine_status: List[Dict[str, Any]] = Field(default_factory=list, description="Summary status for each machine")
    analysis_window: Dict[str, Any] = Field(default_factory=dict, description="Authoritative temporal analysis window")


class DemoMachineDetailResponse(BaseModel):
    """
    Unified machine-level view integrating electrical telemetry, production-aware baseline,
    deviation, forecast, savings, Person 2 health context, and optimization opportunities.
    """
    machine_id: str = Field(..., description="Machine identifier (e.g. M01)")
    machine_name: str = Field(..., description="Machine profile name")
    machine_type: str = Field(..., description="Machine category/type")
    current_state: str = Field(..., description="Current operational state: RUNNING, IDLE, etc.")
    power_kw: float = Field(..., description="Latest active power reading in kW")
    energy_kwh: float = Field(..., description="Cumulative energy reading in kWh")
    actual_energy_kwh: Optional[float] = Field(default=None, description="Actual interval energy consumed during evaluated window in kWh")
    production_units: int = Field(..., description="Total units produced by this machine")
    sec: Optional[float] = Field(default=None, description="Machine Specific Energy Consumption in kWh/unit")
    utilization_rate: float = Field(..., description="Productive utilization rate")
    baseline_expected_energy_kwh: Optional[float] = Field(default=None, description="Production-aware expected energy in kWh")
    deviation_kwh: Optional[float] = Field(default=None, description="Energy deviation (actual - expected) in kWh")
    deviation_pct: Optional[float] = Field(default=None, description="Percentage deviation from expected baseline")
    deviation_status: str = Field(default="NORMAL", description="Deviation classification: NORMAL, ELEVATED, or HIGH")
    forecast_next_5min_kwh: Optional[float] = Field(default=None, description="Projected energy demand over next 5 minutes")
    savings_opportunity: Dict[str, Any] = Field(default_factory=dict, description="Potential savings in kWh, INR, and CO2")
    efficiency: Dict[str, Any] = Field(default_factory=dict, description="Production-normalized efficiency metrics")
    health_context: Dict[str, Any] = Field(default_factory=dict, description="Contextual health signals from Person 2 (temp, vibration, anomaly)")
    optimization_opportunities: List[Dict[str, Any]] = Field(default_factory=list, description="Actionable optimization opportunities for this machine")







