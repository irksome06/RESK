import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_ENV: str = "development"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = True
    DEMO_MODE: bool = Field(default=True, description="Enable deterministic demonstration mode")

    # Database
    DATABASE_URL: str = Field(
        default="sqlite:///./energy_intelligence.db",
        description="Database connection string (PostgreSQL or SQLite fallback)",
    )

    # MQTT
    MQTT_BROKER_HOST: str = "localhost"
    MQTT_BROKER_PORT: int = 1883
    MQTT_USERNAME: Optional[str] = None
    MQTT_PASSWORD: Optional[str] = None
    MQTT_KEEPALIVE: int = 60
    MQTT_CLIENT_ID: str = "person3_energy_engine"
    MQTT_QOS: int = 1
    MQTT_RETAIN: bool = False
    MQTT_TOPIC_TELEMETRY: str = "factory/+/telemetry"
    MQTT_TOPIC_HEALTH: str = "factory/+/health"
    MQTT_TOPIC_ACTION: str = "factory/+/action"

    # Tariffs and Carbon (Configurable demonstration assumptions for Indian SME context)
    ELECTRICITY_COST_INR_PER_KWH: float = Field(
        default=8.00,
        description="Configurable demonstration electricity tariff assumption in INR/kWh (e.g. 8.00 INR/kWh)",
    )
    ELECTRICITY_TARIFF_INR_PER_KWH: float = Field(
        default=8.00,
        description="Alias for ELECTRICITY_COST_INR_PER_KWH (configurable demonstration tariff)",
    )
    GRID_EMISSION_FACTOR_KG_CO2_PER_KWH: float = Field(
        default=0.716,
        description="Configurable demonstration grid emission factor in kg CO2/kWh (CEA India baseline reference ~0.716)",
    )

    # Ollama / LLM
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen3:1.7b"
    LLM_TIMEOUT_SECONDS: int = 30

    # Deviation thresholds (%)
    DEVIATION_THRESHOLD_ELEVATED: float = 10.0
    DEVIATION_THRESHOLD_HIGH: float = 25.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
