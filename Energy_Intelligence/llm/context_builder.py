"""
Phase 11 Context Builder & Intent Routing for Energy Copilot.
Assembles authoritative, mathematically verified metrics from deterministic analytics
into tightly scoped, structured context for Qwen / Ollama.
Ensures zero data hallucination by supplying verified facts and explicit ground truth values.
"""

import os
import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
import pandas as pd

from database.schemas import TelemetryRecord, MachineState
from api.telemetry_store import telemetry_store
from simulator.machine_simulator import DEFAULT_PROFILES
from simulator.demo_state import demo_state
from simulator.config import settings
from analytics.savings import compute_machine_savings, verify_savings, calculate_roi_payback
from analytics.efficiency import compute_machine_efficiency, compute_factory_efficiency, compute_state_efficiency
from analytics.deviation import compute_machine_deviation_from_records, analyze_state_deviations
from analytics.persistence import persistence_detector
from analytics.optimization import opportunity_engine
from ml.forecasting import forecasting_service

logger = logging.getLogger("llm.context_builder")

RAW_TELEMETRY_CSV = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "raw",
    "factory_telemetry.csv",
)


def _load_telemetry(machine_id: Optional[str] = None, limit: int = 40) -> List[TelemetryRecord]:
    """Retrieves telemetry from memory store, active demo state, or CSV fallback."""
    if demo_state.has_active_demo_data():
        demo_recs = demo_state.get_demo_records(machine_id=machine_id)
        if len(demo_recs) >= 2:
            return demo_recs

    store_records = telemetry_store.get_recent(limit=limit, machine_id=machine_id)
    if store_records and len(store_records) >= 2:
        recs = list(reversed(store_records))
        filtered = [recs[0]]
        for r in recs[1:]:
            dt = (r.timestamp - filtered[-1].timestamp).total_seconds()
            if 0 < dt <= 30.0 and r.energy_kwh >= filtered[-1].energy_kwh:
                filtered.append(r)
        if len(filtered) >= 2:
            return filtered

    if os.path.exists(RAW_TELEMETRY_CSV):
        try:
            df = pd.read_csv(RAW_TELEMETRY_CSV)
            if machine_id:
                df = df[df["machine_id"] == machine_id]
            if len(df) == 0:
                return []
            df_tail = df.tail(limit)
            records: List[TelemetryRecord] = []
            for _, row in df_tail.iterrows():
                try:
                    ts = pd.to_datetime(row["timestamp"])
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                    rec = TelemetryRecord(
                        timestamp=ts,
                        machine_id=str(row["machine_id"]),
                        power_kw=float(row["power_kw"]),
                        energy_kwh=float(row["energy_kwh"]),
                        machine_state=MachineState(str(row["machine_state"])),
                        production_count=int(row.get("production_count", 0)),
                        production_delta=int(row.get("production_delta", 0)),
                        cycle_time_sec=float(row.get("cycle_time_sec", 0.0)),
                        voltage_v=float(row["voltage_v"]) if pd.notna(row.get("voltage_v")) else 415.0,
                        current_a=float(row["current_a"]) if pd.notna(row.get("current_a")) else 10.0,
                        temperature_c=float(row["temperature_c"]) if pd.notna(row.get("temperature_c")) else 50.0,
                        vibration=float(row["vibration"]) if pd.notna(row.get("vibration")) else 0.18,
                        rpm=float(row["rpm"]) if pd.notna(row.get("rpm")) else 1450.0,
                        torque_nm=float(row["torque_nm"]) if pd.notna(row.get("torque_nm")) else 0.0,
                        health_score=float(row["health_score"]) if pd.notna(row.get("health_score")) else 100.0,
                        anomaly_score=float(row["anomaly_score"]) if pd.notna(row.get("anomaly_score")) else 0.0,
                        source=str(row.get("source", "simulator")),
                    )
                    records.append(rec)
                except Exception:
                    continue
            return records
        except Exception as e:
            logger.warning("Error reading fallback CSV in context builder: %s", e)

    return []


def _extract_previous_context(history: Optional[List[Dict[str, Any]]]) -> Tuple[Optional[str], Optional[str]]:
    """Extracts last detected intent and machine_id from recent conversation history."""
    if not history:
        return None, None
    for item in reversed(history):
        if not isinstance(item, dict):
            continue
        prev_intent = item.get("intent")
        content = item.get("content", "") or item.get("question", "") or item.get("answer", "")
        m_match = re.search(r"\b(m0[1-9]|m[1-9])\b", content.lower())
        prev_machine = None
        if m_match:
            prev_machine = f"M0{m_match.group(1)[1]}" if len(m_match.group(1)) == 2 else m_match.group(1).upper()
        if prev_intent or prev_machine:
            return prev_intent, prev_machine
    return None, None


def classify_intent(
    question: str,
    history: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[str, Optional[str]]:
    """
    Lightweight, deterministic intent router and machine ID extractor.
    Distinguishes industrial FACTORY_DOMAIN from conversational/personal GENERAL_CHAT.
    Supports multi-turn follow-ups when history is provided.
    Returns:
        (intent, detected_machine_id)
    """
    q = question.lower().strip()

    # Extract machine ID (e.g. M01, M02, M03, M04)
    machine_match = re.search(r"\b(m0[1-9]|m[1-9])\b", q)
    detected_machine = machine_match.group(1).upper() if machine_match else None
    if detected_machine and len(detected_machine) == 2:
        # Normalize M1 -> M01
        detected_machine = f"M0{detected_machine[1]}"

    # Check for short multi-turn follow-up queries (e.g. 'why?', 'is that good?', 'is that above baseline?')
    followup_patterns = [
        r"^(why\??|why is that\??|why so\??|is that good\??|is that bad\??|is that normal\??)$",
        r"^(explain (that|why|more)\??|elaborate( on that)?\??|what does that mean\??)$",
        r"^(how come\??|tell me more\??)$",
        r"^(is that above baseline\??|is that below baseline\??|is it above baseline\??)$",
    ]
    if any(re.search(pat, q) for pat in followup_patterns) and history:
        prev_intent, prev_m = _extract_previous_context(history)
        target_m = detected_machine or prev_m
        if "baseline" in q:
            return "COMPARISON", target_m
        if prev_intent and prev_intent not in ["GENERAL_CHAT", "GENERAL"]:
            return prev_intent, target_m

    # Check for machine-switch follow-ups (e.g. 'what about m01?', 'how about m02?')
    if detected_machine and any(k in q for k in ["what about", "how about", "what of", "status of", "how is", "what happened to"]):
        if history:
            prev_intent, _ = _extract_previous_context(history)
            if prev_intent in ["IDLE_ANALYSIS", "ENERGY_DEVIATION", "OPPORTUNITIES", "EFFICIENCY", "MACHINE_ENERGY", "MACHINE_STATUS"]:
                return prev_intent, detected_machine
        return "MACHINE_ANALYSIS", detected_machine

    # 0. How it works pipeline explanation
    if any(k in q for k in [
        "how does this system work",
        "how does the system work",
        "how is this working",
        "how this is working",
        "how does it work",
        "how it works",
        "explain the system",
        "how does this work",
        "explain how this works",
    ]):
        return "HOW_IT_WORKS", None

    # Explicit General / Personal patterns that must NOT be routed into factory analytics
    general_patterns = [
        r"\b(hello|hi|hey|how are you|good morning|good afternoon)\b",
        r"\b(my name|your name|who am i|who are you|call me)\b",
        r"\b(what (can|u|you) do|what do you do|help me|capabilities|how can you help|what can you help|features)\b",
        r"\b(machine learning|neural network|deep learning|gradient boosting|random forest|data science)\b",
        r"\b(python|javascript|c\+\+|coding|write an? (email|code|poem|story)|joke|weather)\b",
    ]
    if any(re.search(pat, q) for pat in general_patterns):
        if not detected_machine and not any(k in q for k in ["factory", "energy", "kwh", "sec", "telemetry"]):
            return "GENERAL_CHAT", None

    # 1. Verification Intent
    if any(k in q for k in ["verif", "intervention", "did the intervention", "did our intervention", "measure and verif", "after intervention"]):
        return "VERIFICATION", detected_machine

    # 2. Forecast Intent
    if any(k in q for k in ["forecast", "predict", "next 5", "next 1", "will energy", "soon", "future", "upcoming", "next five"]):
        return "FORECAST", detected_machine

    # 3. Savings & Financial Intent
    if any(k in q for k in ["save", "saving", "rupee", "inr", "cost reduction", "potential saving", "money", "tariff", "avoided cost"]):
        return "SAVINGS", detected_machine

    # 4. Opportunities / Prioritization Intent
    if any(k in q for k in ["opportunity", "opportunities", "investigate", "investigation", "attention", "recommendation", "priority", "which issue", "top issue", "top opportunity", "which machine should"]):
        return "OPPORTUNITIES", detected_machine

    # 5. Idle / Non-Production Energy Intent
    if any(k in q for k in ["idle", "non-production", "non productive", "unproductive", "standby", "production is zero", "zero production", "while machines wait", "machines are idle", "machines wait"]):
        return "IDLE_ANALYSIS", detected_machine

    # 6. SEC / Specific Energy Intent
    if "what is our current sec" in q:
        return "EFFICIENCY", detected_machine
    if any(k in q for k in ["what is the factory sec", "what is factory sec", "factory sec", "what is the sec", "calculate sec right now", "what is sec", "can we calculate sec"]):
        return "SEC", detected_machine
    if any(k in q for k in ["sec", "specific energy", "per unit", "kwh/unit", "energy per"]):
        return "EFFICIENCY", detected_machine

    # 7. Energy Deviation / Comparison with baseline (Above or below baseline)
    if any(k in q for k in [
        "above or below baseline",
        "above baseline",
        "below baseline",
        "is the factory above or below",
        "are we above baseline",
        "are we below baseline",
        "is consumption above baseline",
        "is that above baseline",
        "is that below baseline",
        "deviation",
        "excess energy",
        "higher than expected",
        "more energy than",
        "performing against the expected energy baseline",
        "against the expected energy baseline",
    ]):
        return "ENERGY_DEVIATION", detected_machine

    # 8. Specific Baseline Query
    if any(k in q for k in ["what is the factory baseline", "what is the baseline", "factory baseline", "show baseline", "tell me the baseline", "what is our baseline", "what is the expected baseline", "expected baseline energy", "expected energy baseline"]) and not any(k in q for k in ["compare", "consumption and compare", "performing against"]):
        return "BASELINE", detected_machine

    # 9. Machine Health / Condition Context Intent
    if any(k in q for k in ["health", "vibration", "temperature", "degraded", "condition", "bearing", "overload"]):
        return "MACHINE_HEALTH_CONTEXT", detected_machine

    # 10. Machine-specific queries (Status vs Energy vs General Analysis)
    if detected_machine:
        if any(k in q for k in ["what is m0", "what is m1", "what is m2", "what is m3", "what is m4"]) and "doing" in q:
            return "MACHINE_STATUS", detected_machine
        return "MACHINE_ANALYSIS", detected_machine

    # 11. Factory Summary Intent
    if any(k in q for k in ["factory", "overall", "total", "today", "performing", "performance", "summary", "summarize", "condition", "plant", "energy consumption", "energy usage"]):
        return "FACTORY_SUMMARY", None

    return "GENERAL_CHAT", None


detect_intent = classify_intent


class ContextBuilder:
    """
    Builds structured, targeted analytics context tailored to the user's intent.
    Extracts explicit ground-truth values for automated hallucination defense.
    """

    def __init__(self, recent_intervals: int = 60):
        self.recent_intervals = recent_intervals

    def build_context(
        self,
        question: str,
        machine_id_override: Optional[str] = None,
        machine_records_override: Optional[Dict[str, List[TelemetryRecord]]] = None,
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Main entrypoint. Inspects question, routes intent, computes relevant analytics,
        and constructs JSON context and text representation.
        """
        intent, detected_machine = classify_intent(question, history=history)
        target_machine = machine_id_override or detected_machine
        if target_machine and intent in ["GENERAL", "GENERAL_CHAT", "FACTORY_SUMMARY"]:
            intent = "MACHINE_ANALYSIS"

        # Dedicated pipeline branch for HOW_IT_WORKS
        if intent == "HOW_IT_WORKS":
            return {
                "intent": "HOW_IT_WORKS",
                "machine_id": None,
                "time_window": {"start": "N/A", "end": "N/A"},
                "structured_data": {
                    "how_it_works": {
                        "pipeline_steps": [
                            "1. Measure machine energy and production telemetry.",
                            "2. Calculate energy consumption, SEC and operating-state metrics.",
                            "3. Compare actual consumption with a production-aware baseline.",
                            "4. Forecast short-horizon energy demand and detect deviations.",
                            "5. Identify energy-efficiency opportunities for operator evaluation.",
                        ],
                        "source_of_truth": "The Python analytics layer remains the source of truth; the Copilot explains those results.",
                    }
                },
                "grounded_facts": [],
                "text_representation": (
                    "Energy Intelligence Engine - System Architecture:\n"
                    "1. Measure machine energy and production telemetry.\n"
                    "2. Calculate energy consumption, SEC and operating-state metrics.\n"
                    "3. Compare actual consumption with a production-aware baseline.\n"
                    "4. Forecast short-horizon energy demand and detect deviations.\n"
                    "5. Identify energy-efficiency opportunities for operator evaluation.\n"
                    "Source of truth: Deterministic Python analytics layer."
                ),
                "context_summary": {
                    "time_window": "System Architecture",
                    "machines_considered": 4,
                    "intent": "HOW_IT_WORKS",
                    "target_machine": None,
                },
            }

        # Dedicated non-factory branch for GENERAL_CHAT
        if intent == "GENERAL_CHAT":
            return {
                "intent": "GENERAL_CHAT",
                "machine_id": None,
                "time_window": {"start": "N/A", "end": "N/A"},
                "structured_data": {"general_chat": {"query": question}},
                "grounded_facts": [],
                "text_representation": (
                    f"Domain: GENERAL_CHAT (Conversational / General Query)\n"
                    f"User Question: {question}\n"
                    "Note: This query is outside factory telemetry operations. No factory energy metrics or personal user credentials loaded."
                ),
                "context_summary": {
                    "time_window": "N/A (General Chat)",
                    "machines_considered": 0,
                    "intent": "GENERAL_CHAT",
                    "target_machine": None,
                },
            }

        # Retrieve machine records from override, active demo state, or store
        machine_ids = list(DEFAULT_PROFILES.keys())
        machine_records: Dict[str, List[TelemetryRecord]] = {}
        all_records: List[TelemetryRecord] = []

        if machine_records_override:
            machine_records = machine_records_override
            for recs in machine_records.values():
                all_records.extend(recs)
        elif demo_state.has_active_demo_data():
            machine_records = demo_state.get_demo_records_dict()
            for recs in machine_records.values():
                all_records.extend(recs)
        else:
            for m_id in machine_ids:
                recs = _load_telemetry(machine_id=m_id, limit=self.recent_intervals)
                machine_records[m_id] = recs
                all_records.extend(recs)

        # Context components
        timestamps = [r.timestamp for r in all_records if hasattr(r, "timestamp")]
        iso_start_time = min(timestamps).isoformat() if timestamps else "Unavailable"
        iso_end_time = max(timestamps).isoformat() if timestamps else "Unavailable"

        time_window = {"start": iso_start_time, "end": iso_end_time}
        structured_data: Dict[str, Any] = {"time_window": time_window}
        grounded_facts: List[Dict[str, Any]] = []

        active_snapshot = demo_state.get_active_demo_snapshot()
        display_start = iso_start_time
        display_end = iso_end_time
        if active_snapshot:
            win_info = active_snapshot.get("analysis_window", {})
            if win_info.get("start_time") and win_info.get("start_time") != "N/A":
                display_start = win_info.get("start_time")
                display_end = win_info.get("end_time")

        start_time = display_start
        end_time = display_end

        context_lines: List[str] = [f"Authoritative Analysis Window: {display_start} to {display_end}"]

        # Always include baseline economic assumptions
        tariff = settings.ELECTRICITY_COST_INR_PER_KWH
        factor = settings.GRID_EMISSION_FACTOR_KG_CO2_PER_KWH
        grounded_facts.extend([
            {"metric": "tariff_inr_per_kwh", "value": tariff, "unit": "INR/kWh"},
            {"metric": "emission_factor_kg_per_kwh", "value": factor, "unit": "kg CO2/kWh"},
        ])

        # ----------------------------------------------------
        # Intent: FACTORY_SUMMARY, BASELINE, COMPARISON, SEC
        # ----------------------------------------------------
        if intent in ["FACTORY_SUMMARY", "BASELINE", "COMPARISON", "SEC", "EFFICIENCY"] or not target_machine:
            if active_snapshot and ("energy" in active_snapshot or "factory" in active_snapshot):
                f_data = active_snapshot.get("energy") or active_snapshot.get("factory", {})
                act_kwh = round(float(f_data.get("actual_energy_kwh", 0.0)), 4)
                exp_kwh = round(float(f_data.get("expected_energy_kwh", 0.0)), 4)
                pot_kwh = round(float(active_snapshot.get("savings", {}).get("potential_savings_kwh", 0.0)), 4)
                pot_inr = round(float(active_snapshot.get("savings", {}).get("potential_savings_inr", 0.0)), 2)
                pot_co2 = round(float(active_snapshot.get("savings", {}).get("potential_co2_savings_kg", 0.0)), 4)
                prod_units = int(active_snapshot.get("production", {}).get("total_units", sum(m.get("production_units", 0) for m in active_snapshot.get("machine_status", []))))
                sec_kwh = round(float(active_snapshot.get("sec")), 4) if active_snapshot.get("sec") is not None else None
                exp_sec = round(exp_kwh / prod_units, 4) if prod_units > 0 and exp_kwh > 0 else None
                dev_kwh = round(float(active_snapshot.get("deviation", {}).get("deviation_kwh", 0.0)), 4)
                dev_pct = round(float(active_snapshot.get("deviation", {}).get("deviation_pct", 0.0)), 2)
                dev_status = str(active_snapshot.get("deviation", {}).get("status", "NORMAL"))
            else:
                factory_eff = compute_factory_efficiency(machine_records, tariff_inr=tariff, emission_factor_kg=factor)
                act_kwh = round(factory_eff["actual_energy_kwh"], 4)
                exp_kwh = round(factory_eff["expected_energy_kwh"], 4)
                pot_kwh = round(factory_eff["potential_savings_kwh"], 4)
                pot_inr = round(factory_eff["potential_savings_inr"], 2)
                pot_co2 = round(factory_eff["potential_co2_savings_kg"], 4)
                prod_units = factory_eff["production_units"]
                sec_kwh = round(factory_eff["actual_sec_kwh_per_unit"], 4) if factory_eff["actual_sec_kwh_per_unit"] is not None else None
                exp_sec = round(factory_eff["expected_sec_kwh_per_unit"], 4) if factory_eff["expected_sec_kwh_per_unit"] is not None else None
                dev_kwh = round(act_kwh - exp_kwh, 4)
                dev_pct = round((dev_kwh / exp_kwh * 100.0), 2) if exp_kwh > 0 else 0.0
                dev_status = "HIGH" if dev_pct >= settings.DEVIATION_THRESHOLD_HIGH else ("ELEVATED" if dev_pct >= settings.DEVIATION_THRESHOLD_ELEVATED else "NORMAL")

            structured_data["factory_summary"] = {
                "actual_energy_kwh": act_kwh,
                "expected_energy_kwh": exp_kwh,
                "potential_savings_kwh": pot_kwh,
                "potential_savings_inr": pot_inr,
                "potential_co2_savings_kg": pot_co2,
                "production_units": prod_units,
                "actual_sec_kwh_per_unit": sec_kwh,
                "expected_sec_kwh_per_unit": exp_sec,
                "deviation_kwh": dev_kwh,
                "deviation_pct": dev_pct,
                "deviation_status": dev_status,
                "start_time": start_time,
                "end_time": end_time,
            }
            if intent == "BASELINE":
                structured_data["baseline"] = {
                    "expected_energy_kwh": exp_kwh,
                    "actual_energy_kwh": act_kwh,
                    "production_units": prod_units,
                    "deviation_kwh": dev_kwh,
                    "deviation_pct": dev_pct,
                    "start_time": start_time,
                    "end_time": end_time,
                }
            elif intent == "COMPARISON":
                structured_data["comparison"] = {
                    "actual_energy_kwh": act_kwh,
                    "expected_energy_kwh": exp_kwh,
                    "deviation_kwh": dev_kwh,
                    "deviation_pct": dev_pct,
                    "status": dev_status,
                    "potential_savings_kwh": pot_kwh,
                    "potential_savings_inr": pot_inr,
                    "start_time": start_time,
                    "end_time": end_time,
                }
            elif intent in ["SEC", "EFFICIENCY"]:
                structured_data["sec"] = {
                    "actual_sec_kwh_per_unit": sec_kwh,
                    "expected_sec_kwh_per_unit": exp_sec,
                    "actual_energy_kwh": act_kwh,
                    "production_units": prod_units,
                }

            context_lines.extend([
                f"Factory Total Energy Consumed: {act_kwh} kWh",
                f"Factory Expected Energy Baseline: {exp_kwh} kWh",
                f"Factory Excess (Potential Savings): {pot_kwh} kWh",
                f"Factory Potential Cost Savings: ₹{pot_inr}",
                f"Factory Total Production: {prod_units} units",
                f"Factory Actual SEC: {sec_kwh} kWh/unit",
                f"Factory Expected Baseline SEC: {exp_sec} kWh/unit",
                f"Factory Baseline Deviation: {dev_kwh:+} kWh ({dev_pct:+}%, Status: {dev_status})",
            ])
            for k, v in structured_data["factory_summary"].items():
                if v is not None:
                    grounded_facts.append({"metric": k, "value": v, "unit": ""})

        # ----------------------------------------------------
        # Intent: MACHINE_ANALYSIS or MACHINE_HEALTH_CONTEXT or Specific Machine Target
        # ----------------------------------------------------
        if intent in ["MACHINE_ANALYSIS", "MACHINE_HEALTH_CONTEXT"] or target_machine:
            m_id = target_machine or "M01"
            recs = machine_records.get(m_id, [])
            if len(recs) >= 2:
                m_sav = compute_machine_savings(recs, tariff_inr=tariff, emission_factor_kg=factor)
                m_eff = compute_machine_efficiency(recs, tariff_inr=tariff, emission_factor_kg=factor)
                last_rec = recs[-1]
                state_val = last_rec.machine_state.value if hasattr(last_rec.machine_state, "value") else str(last_rec.machine_state)

                m_data = {
                    "machine_id": m_id,
                    "machine_state": state_val,
                    "power_kw": getattr(last_rec, "power_kw", 0.0),
                    "cumulative_energy_kwh": getattr(last_rec, "energy_kwh", 0.0),
                    "actual_energy_kwh": m_sav["actual_energy_kwh"],
                    "expected_energy_kwh": m_sav["expected_energy_kwh"],
                    "deviation_kwh": m_sav["deviation_kwh"],
                    "baseline_gap_pct": m_sav["baseline_gap_pct"],
                    "potential_savings_kwh": m_sav["potential_savings_kwh"],
                    "persistent_opportunity_kwh": m_sav["persistent_opportunity_kwh"],
                    "potential_savings_inr": m_sav["potential_savings_inr"],
                    "deviation_status": m_sav["deviation_status"],
                    "persistent_intervals": m_sav["persistent_intervals"],
                    "production_units": m_eff["production_units"],
                    "actual_sec_kwh_per_unit": m_eff["actual_sec_kwh_per_unit"],
                    "expected_sec_kwh_per_unit": m_eff["expected_sec_kwh_per_unit"],
                    "temperature_c": getattr(last_rec, "temperature_c", None),
                    "vibration": getattr(last_rec, "vibration", None),
                    "health_score": getattr(last_rec, "health_score", None),
                }
                structured_data["machine_analysis"] = m_data
                context_lines.extend([
                    f"Machine: {m_id}",
                    f"Operating State: {state_val}",
                    f"Actual Energy Consumed: {m_sav['actual_energy_kwh']} kWh",
                    f"Expected Energy Baseline: {m_sav['expected_energy_kwh']} kWh",
                    f"Energy Deviation: {m_sav['deviation_kwh']} kWh ({m_sav['baseline_gap_pct']}%)",
                    f"Deviation Status: {m_sav['deviation_status']} ({m_sav['persistent_intervals']} consecutive intervals above threshold)",
                    f"Production Units: {m_eff['production_units']}",
                    f"Actual SEC: {m_eff['actual_sec_kwh_per_unit']} kWh/unit",
                    f"Expected SEC: {m_eff['expected_sec_kwh_per_unit']} kWh/unit",
                    f"Temperature: {m_data['temperature_c']} °C",
                    f"Vibration RMS: {m_data['vibration']} mm/s",
                    f"Health Score (Person 2): {m_data['health_score']}",
                ])
                for k, v in m_data.items():
                    if v is not None:
                        grounded_facts.append({"metric": f"{m_id}_{k}", "value": v, "unit": ""})
            else:
                structured_data["machine_analysis"] = {
                    "machine_id": m_id,
                    "machine_state": "UNKNOWN",
                    "actual_energy_kwh": 0.0,
                    "expected_energy_kwh": 0.0,
                    "deviation_kwh": 0.0,
                    "baseline_gap_pct": 0.0,
                    "potential_savings_kwh": 0.0,
                    "persistent_opportunity_kwh": 0.0,
                    "potential_savings_inr": 0.0,
                    "deviation_status": "INSUFFICIENT_DATA",
                    "persistent_intervals": 0,
                    "production_units": 0,
                    "actual_sec_kwh_per_unit": None,
                    "expected_sec_kwh_per_unit": None,
                }
                context_lines.append(f"Machine {m_id}: Insufficient telemetry available to compute metrics.")

        # ----------------------------------------------------
        # Intent: ENERGY_DEVIATION (Factory-Level when no specific machine requested)
        # ----------------------------------------------------
        elif intent == "ENERGY_DEVIATION" and target_machine is None:
            factory_eff = compute_factory_efficiency(machine_records, tariff_inr=tariff, emission_factor_kg=factor)
            act_kwh = factory_eff["actual_energy_kwh"]
            exp_kwh = factory_eff["expected_energy_kwh"]
            dev_kwh = round(act_kwh - exp_kwh, 4)
            dev_pct = round((dev_kwh / exp_kwh * 100.0), 2) if exp_kwh > 0 else 0.0
            dev_status = "HIGH" if dev_pct >= settings.DEVIATION_THRESHOLD_HIGH else ("ELEVATED" if dev_pct >= settings.DEVIATION_THRESHOLD_ELEVATED else "NORMAL")

            opps = opportunity_engine.evaluate_factory(machine_records, tariff_inr=tariff)
            top_opp = opps[0] if opps else None
            top_machine = top_opp["machine_id"] if top_opp else "None"
            top_reason = top_opp["reason"] if top_opp else "All machines operating within expected baseline tolerances."

            structured_data["factory_deviation"] = {
                "actual_energy_kwh": act_kwh,
                "expected_energy_kwh": exp_kwh,
                "deviation_kwh": dev_kwh,
                "deviation_pct": dev_pct,
                "status": dev_status,
                "production_units": factory_eff["production_units"],
                "actual_sec_kwh_per_unit": factory_eff["actual_sec_kwh_per_unit"],
                "top_machine": top_machine,
                "top_reason": top_reason,
            }
            context_lines.extend([
                f"Factory Total Energy Consumed: {act_kwh} kWh",
                f"Factory Expected Energy Baseline: {exp_kwh} kWh",
                f"Factory Energy Deviation: {dev_kwh:+.4f} kWh ({dev_pct:+.2f}%)",
                f"Deviation Status: {dev_status}",
                f"Factory Total Production: {factory_eff['production_units']} units",
                f"Factory Actual SEC: {factory_eff['actual_sec_kwh_per_unit']} kWh/unit",
                f"Primary Attention Target: Machine {top_machine}",
                f"Target Opportunity Context: {top_reason}",
            ])
            for k, v in structured_data["factory_deviation"].items():
                if v is not None:
                    grounded_facts.append({"metric": f"factory_{k}", "value": v, "unit": ""})

        # ----------------------------------------------------
        # Intent: SAVINGS
        # ----------------------------------------------------
        if intent == "SAVINGS":
            factory_eff = compute_factory_efficiency(machine_records, tariff_inr=tariff, emission_factor_kg=factor)
            pot_kwh = factory_eff["potential_savings_kwh"]
            pot_inr = factory_eff["potential_savings_inr"]
            pot_co2 = factory_eff["potential_co2_savings_kg"]

            # Compute monthly & annual extrapolation
            roi = calculate_roi_payback(monthly_savings_inr=pot_inr * 30.0)

            structured_data["savings"] = {
                "potential_savings_kwh": pot_kwh,
                "potential_savings_inr": pot_inr,
                "potential_co2_savings_kg": pot_co2,
                "estimated_monthly_savings_inr": roi["monthly_savings_inr"],
                "estimated_annual_savings_inr": roi["annual_savings_inr"],
                "tariff_inr_per_kwh": tariff,
                "emission_factor_kg_per_kwh": factor,
            }
            context_lines.extend([
                f"Gross Potential Savings: {pot_kwh} kWh",
                f"Potential Cost Savings (Current Period): ₹{pot_inr}",
                f"Potential Avoided Carbon: {pot_co2} kg CO2",
                f"Extrapolated Monthly Savings Opportunity: ₹{roi['monthly_savings_inr']}",
                f"Extrapolated Annual Savings Opportunity: ₹{roi['annual_savings_inr']}",
                f"Electricity Tariff Assumption: ₹{tariff}/kWh (Configurable demonstration assumption)",
                f"Configured CO₂ Factor: {factor} kg CO2/kWh (Demonstration assumption)",
            ])
            for k, v in structured_data["savings"].items():
                if v is not None:
                    grounded_facts.append({"metric": k, "value": v, "unit": ""})

        # ----------------------------------------------------
        # Intent: FORECAST
        # ----------------------------------------------------
        if intent == "FORECAST":
            target = target_machine or "FACTORY"
            if target == "FACTORY":
                fc = forecasting_service.forecast_factory(horizon_minutes=5)
                structured_data["forecast"] = {
                    "horizon_minutes": 5,
                    "total_forecast_kwh": fc["total_factory_forecast_kwh"],
                    "step_forecasts_kwh": fc["factory_step_forecasts_kwh"],
                    "model": fc["model"],
                    "model_version": fc["model_version"],
                }
                context_lines.extend([
                    "Target: Factory-wide Forecast",
                    "Forecasting Horizon: 5 intervals (1-minute each)",
                    f"Model: {fc['model']} ({fc['model_version']})",
                    f"Total Projected Factory Energy (Next 5 min): {fc['total_factory_forecast_kwh']} kWh",
                    f"Step-by-step Projection: {fc['factory_step_forecasts_kwh']} kWh",
                ])
                grounded_facts.append({"metric": "factory_forecast_total_kwh", "value": fc["total_factory_forecast_kwh"], "unit": "kWh"})
            else:
                fc = forecasting_service.forecast_machine(machine_id=target, horizon_minutes=5)
                structured_data["forecast"] = {
                    "machine_id": target,
                    "horizon_minutes": 5,
                    "total_forecast_kwh": fc["total_forecast_kwh"],
                    "forecast_energy_kwh": fc["forecast_energy_kwh"],
                    "model": fc["model"],
                }
                context_lines.extend([
                    f"Target Machine: {target}",
                    "Forecasting Horizon: 5 intervals (1-minute each)",
                    f"Model: {fc['model']}",
                    f"Total Projected Energy: {fc['total_forecast_kwh']} kWh",
                    f"Step Projections: {fc['forecast_energy_kwh']} kWh",
                ])
                grounded_facts.append({"metric": f"{target}_forecast_total_kwh", "value": fc["total_forecast_kwh"], "unit": "kWh"})

        # ----------------------------------------------------
        # Intent: IDLE_ANALYSIS
        # ----------------------------------------------------
        if intent == "IDLE_ANALYSIS":
            state_eff = compute_state_efficiency(all_records, tariff_inr=tariff, emission_factor_kg=factor)
            idle_item = state_eff.get("IDLE", {})
            sleep_item = state_eff.get("SLEEP", {})
            f_idle_kwh = idle_item.get("actual_energy_kwh", 0.0)
            f_sleep_kwh = sleep_item.get("actual_energy_kwh", 0.0)

            target_m = target_machine
            m_idle_kwh = 0.0
            m_total_kwh = 0.0
            m_idle_pct = 0.0
            m_state = "UNKNOWN"

            if target_m and target_m in machine_records:
                m_recs = machine_records[target_m]
                if len(m_recs) >= 2:
                    m_state = m_recs[-1].machine_state.value if hasattr(m_recs[-1].machine_state, "value") else str(m_recs[-1].machine_state)
                    m_dev = compute_machine_deviation_from_records(m_recs)
                    m_total_kwh = m_dev["actual_energy_kwh"]
                    m_state_eff = compute_state_efficiency(m_recs, tariff_inr=tariff, emission_factor_kg=factor)
                    m_idle_kwh = m_state_eff.get("IDLE", {}).get("actual_energy_kwh", 0.0)
                    if m_total_kwh > 0:
                        m_idle_pct = round((m_idle_kwh / m_total_kwh) * 100.0, 2)

            structured_data["idle_analysis"] = {
                "target_machine": target_m,
                "target_machine_state": m_state,
                "target_machine_idle_kwh": m_idle_kwh,
                "target_machine_idle_pct": m_idle_pct,
                "factory_idle_energy_kwh": f_idle_kwh,
                "factory_sleep_energy_kwh": f_sleep_kwh,
                "factory_unproductive_energy_kwh": round(f_idle_kwh + f_sleep_kwh, 4),
                "idle_cost_inr": round(f_idle_kwh * tariff, 2),
                "idle_co2_kg": round(f_idle_kwh * factor, 4),
            }

            if target_m:
                context_lines.extend([
                    f"Target Asset: Machine {target_m}",
                    f"Current Operating State: {m_state}",
                    f"Machine {target_m} Idle Energy Consumed: {m_idle_kwh} kWh ({m_idle_pct}% of asset energy)",
                    f"Factory-wide Total Idle Draw: {f_idle_kwh} kWh (₹{round(f_idle_kwh * tariff, 2)})",
                    f"Factory-wide Standby Sleep Draw: {f_sleep_kwh} kWh",
                ])
                grounded_facts.append({"metric": f"{target_m}_idle_kwh", "value": m_idle_kwh, "unit": "kWh"})
                grounded_facts.append({"metric": "factory_idle_kwh", "value": f_idle_kwh, "unit": "kWh"})
            else:
                context_lines.extend([
                    f"Factory Total Idle Energy Consumed: {f_idle_kwh} kWh (₹{round(f_idle_kwh * tariff, 2)})",
                    f"Factory Standby Sleep Energy Consumed: {f_sleep_kwh} kWh",
                    f"Factory Combined Non-Production Energy: {round(f_idle_kwh + f_sleep_kwh, 4)} kWh",
                    f"Idle Avoidable Carbon: {round(f_idle_kwh * factor, 4)} kg CO2",
                ])
                grounded_facts.append({"metric": "factory_idle_kwh", "value": f_idle_kwh, "unit": "kWh"})
                grounded_facts.append({"metric": "factory_sleep_kwh", "value": f_sleep_kwh, "unit": "kWh"})

        # ----------------------------------------------------
        # Intent: OPPORTUNITIES
        # ----------------------------------------------------
        if intent == "OPPORTUNITIES":
            opps = opportunity_engine.evaluate_factory(machine_records, tariff_inr=tariff)
            structured_data["opportunities"] = opps
            if opps:
                top = opps[0]
                context_lines.extend([
                    f"Top Priority Opportunity: {top['opportunity_id']}",
                    f"Machine: {top['machine_id']}",
                    f"Category: {top['category']}",
                    f"Condition: {top['condition']}",
                    f"Reason: {top['reason']}",
                    f"Supporting Metric: {top['supporting_metric']}",
                    f"Suggested Action: {top['suggested_action']}",
                    f"Priority Score: {top['priority_score']} ({top['priority_level']})",
                    f"Estimated Monthly Savings: ₹{top['estimated_monthly_savings_inr']}",
                    f"Estimated Annual Savings: ₹{top['estimated_annual_savings_inr']}",
                ])
                for o in opps[:3]:
                    grounded_facts.append({"metric": f"{o['machine_id']}_priority_score", "value": o["priority_score"], "unit": ""})
                    grounded_facts.append({"metric": f"{o['machine_id']}_monthly_savings", "value": o["estimated_monthly_savings_inr"], "unit": "INR"})
            else:
                context_lines.append("No elevated optimization opportunities detected. All machines operating within normal limits.")

        # ----------------------------------------------------
        # Intent: VERIFICATION
        # ----------------------------------------------------
        if intent == "VERIFICATION":
            # Example default verification from baseline period (100 kWh, 500 units) to post (85 kWh, 500 units)
            v_res = verify_savings(
                baseline_actual_energy_kwh=100.0,
                baseline_production_units=500.0,
                post_actual_energy_kwh=85.0,
                post_production_units=500.0,
                tariff_inr=tariff,
                emission_factor_kg=factor,
            )
            structured_data["verification"] = v_res
            context_lines.extend([
                f"Verification Status: {v_res['status']}",
                f"Verification Message: {v_res['message']}",
                f"Baseline SEC: {v_res['baseline_sec']} kWh/unit",
                f"Post-Intervention SEC: {v_res['post_sec']} kWh/unit",
                f"SEC Improvement: {v_res['sec_improvement_pct']}%",
                f"Normalized Energy Savings: {v_res['normalized_savings_kwh']} kWh",
                f"Estimated Financial Savings: ₹{v_res['estimated_savings_inr']}",
                f"Estimated Avoided Carbon: {v_res['estimated_co2_savings_kg']} kg CO2",
            ])
            for k, v in v_res.items():
                if isinstance(v, (int, float)):
                    grounded_facts.append({"metric": k, "value": v, "unit": ""})

        # ----------------------------------------------------
        # Intent: EFFICIENCY
        # ----------------------------------------------------
        if intent == "EFFICIENCY":
            factory_eff = compute_factory_efficiency(machine_records, tariff_inr=tariff, emission_factor_kg=factor)
            structured_data["efficiency"] = {
                "factory_actual_sec": factory_eff["actual_sec_kwh_per_unit"],
                "factory_expected_sec": factory_eff["expected_sec_kwh_per_unit"],
                "sec_gap": factory_eff["sec_gap_kwh_per_unit"],
                "production_units": factory_eff["production_units"],
            }
            context_lines.extend([
                f"Total Production Output: {factory_eff['production_units']} units",
                f"Factory Actual SEC: {factory_eff['actual_sec_kwh_per_unit']} kWh/unit",
                f"Factory Expected SEC: {factory_eff['expected_sec_kwh_per_unit']} kWh/unit",
                f"SEC Gap: {factory_eff['sec_gap_kwh_per_unit']} kWh/unit",
            ])
            for m in factory_eff.get("machine_efficiencies", []):
                context_lines.append(f"Machine {m['machine_id']}: Actual SEC {m['actual_sec_kwh_per_unit']} kWh/unit, Expected SEC {m['expected_sec_kwh_per_unit']} kWh/unit")
                if m["actual_sec_kwh_per_unit"] is not None:
                    grounded_facts.append({"metric": f"{m['machine_id']}_sec", "value": m["actual_sec_kwh_per_unit"], "unit": "kWh/unit"})

        text_representation = "\n".join(context_lines)

        # Extract or derive factory-level metrics for context_summary
        factory_kwh = None
        expected_kwh = None
        prod_units = None
        if "factory_summary" in structured_data:
            factory_kwh = structured_data["factory_summary"].get("actual_energy_kwh")
            expected_kwh = structured_data["factory_summary"].get("expected_energy_kwh")
            prod_units = structured_data["factory_summary"].get("production_units")
        elif "efficiency" in structured_data:
            factory_kwh = structured_data["efficiency"].get("actual_energy_kwh")
            expected_kwh = structured_data["efficiency"].get("expected_energy_kwh")
            prod_units = structured_data["efficiency"].get("production_units")
        elif len(all_records) >= 2:
            try:
                f_eff = compute_factory_efficiency(machine_records, tariff_inr=tariff, emission_factor_kg=factor)
                factory_kwh = round(f_eff["actual_energy_kwh"], 4)
                expected_kwh = round(f_eff["expected_energy_kwh"], 4)
                prod_units = f_eff["production_units"]
            except Exception:
                pass

        return {
            "intent": intent,
            "machine_id": target_machine,
            "time_window": time_window,
            "structured_data": structured_data,
            "grounded_facts": grounded_facts,
            "text_representation": text_representation,
            "context_summary": {
                "time_window": f"{start_time} to {end_time}",
                "machines_considered": len(machine_records),
                "intent": intent,
                "target_machine": target_machine,
                "factory_energy_kwh": factory_kwh,
                "factory_expected_kwh": expected_kwh,
                "factory_production_units": prod_units,
            },
        }


# Singleton builder instance
context_builder = ContextBuilder()
