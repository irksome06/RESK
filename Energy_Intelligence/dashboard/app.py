"""
Schneider Electric Smart Manufacturing Energy & Production Intelligence Dashboard.
Person 3: Energy & Production Intelligence Engine
2026 Yuva Yodha Energy Tech Hackathon Demonstration

Production-grade industrial control-room interface built with Streamlit and Plotly.
Sourced strictly from authoritative Python analytics and FastAPI REST services.
Adheres strictly to Person 1, Person 2, Person 3, and Person 4 responsibility boundaries.
"""

import os
import sys
import math
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
import requests
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# Add parent directory to PYTHONPATH
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from simulator.config import settings
from simulator.machine_simulator import DEFAULT_PROFILES
from simulator.demo_state import demo_state


def get_machine_display_name(machine_id: str) -> str:
    """Canonical single-source-of-truth machine display name from DEFAULT_PROFILES."""
    prof = DEFAULT_PROFILES.get(machine_id)
    name = prof.name if prof else machine_id
    return f"{machine_id} - {name}"


# Configuration & Backend Bridge
API_BASE_URL = os.environ.get("API_URL", "http://localhost:8000")

# Module singleton client for fast in-process API execution
_in_process_client = None


def get_fallback_client():
    """In-process FastAPI TestClient for zero-dependency local running."""
    global _in_process_client
    if _in_process_client is None:
        from fastapi.testclient import TestClient
        from api.main import app
        _in_process_client = TestClient(app)
    return _in_process_client


def fetch_api(endpoint: str, method: str = "GET", payload: dict = None) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    Robust API fetcher: attempts live HTTP first, falls back to in-process FastAPI client.
    Guarantees that the dashboard never crashes if uvicorn is offline.
    """
    url = f"{API_BASE_URL}{endpoint}"
    try:
        if method == "GET":
            res = requests.get(url, timeout=3.0)
        else:
            res = requests.post(url, json=payload, timeout=30.0)
        if res.status_code == 200:
            return res.json(), "LIVE_HTTP"
    except Exception:
        pass

    # Fallback to in-process FastAPI client
    client = get_fallback_client()
    try:
        if method == "GET":
            res = client.get(endpoint)
        else:
            res = client.post(endpoint, json=payload)
        if res.status_code == 200:
            return res.json(), "IN_PROCESS"
    except Exception as e:
        return None, f"ERROR: {e}"

    return None, "FAILED"


# -------------------------------------------------------------
# SAFE FORMATTING HELPERS (Never show NaN, inf, None)
# -------------------------------------------------------------
def safe_val(val: Any, default: str = "N/A") -> str:
    if val is None:
        return default
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return default
    return str(val)


def safe_float(val: Any, decimals: int = 4, default: str = "N/A") -> str:
    if val is None:
        return default
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return default
        return f"{f:.{decimals}f}"
    except (ValueError, TypeError):
        return default


def safe_sec(sec: Any) -> str:
    if sec is None:
        return "N/A (0 prod)"
    try:
        f = float(sec)
        if math.isnan(f) or math.isinf(f):
            return "N/A (0 prod)"
        return f"{f:.4f} kWh/unit"
    except (ValueError, TypeError):
        return "N/A (0 prod)"


def safe_currency(val: Any) -> str:
    if val is None:
        return "₹0.00"
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return "₹0.00"
        return f"₹{f:,.2f}"
    except (ValueError, TypeError):
        return "₹0.00"


# -------------------------------------------------------------
# DASHBOARD RENDERING FUNCTION
# -------------------------------------------------------------
def render_dashboard():
    """Renders the presentation-grade industrial dashboard."""
    st.set_page_config(
        page_title="Schneider Electric | Energy & Production Intelligence",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Custom Industrial Theme CSS
    st.markdown("""
    <style>
        .main {
            background-color: #0E1117;
            color: #E2E8F0;
        }
        .demo-banner {
            background: linear-gradient(90deg, #1E293B 0%, #0F172A 100%);
            border: 1px solid #334155;
            border-left: 5px solid #3DCD58;
            border-radius: 6px;
            padding: 12px 18px;
            margin-bottom: 18px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .metric-card {
            background-color: #161B26;
            border: 1px solid #262F40;
            border-radius: 6px;
            padding: 14px 16px;
            margin-bottom: 12px;
            height: 100%;
        }
        .metric-card-title {
            color: #94A3B8;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            margin-bottom: 6px;
        }
        .metric-card-val {
            color: #F8FAFC;
            font-size: 22px;
            font-weight: 700;
            line-height: 1.2;
        }
        .metric-card-sub {
            color: #64748B;
            font-size: 11px;
            margin-top: 4px;
        }
        .badge {
            display: inline-block;
            padding: 2px 7px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 0.5px;
            margin-right: 4px;
        }
        .badge-measured { background-color: #1E3A8A; color: #93C5FD; border: 1px solid #3B82F6; }
        .badge-calc { background-color: #064E3B; color: #6EE7B7; border: 1px solid #10B981; }
        .badge-pred { background-color: #4C1D95; color: #C4B5FD; border: 1px solid #8B5CF6; }
        .badge-rec { background-color: #78350F; color: #FCD34D; border: 1px solid #F59E0B; }
        .status-normal { color: #3DCD58; font-weight: 600; }
        .status-elevated { color: #F5A623; font-weight: 600; }
        .status-high { color: #EF4444; font-weight: 600; }
    </style>
    """, unsafe_allow_html=True)

    # SIDEBAR CONTROLS
    st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/9/95/Schneider_Electric_2007.svg", width=190)
    st.sidebar.markdown("### **ENERGY INTELLIGENCE ENGINE**")
    st.sidebar.caption("**Person 3** — Energy & Production Intelligence")

    status_data, backend_mode = fetch_api("/demo/status")

    st.sidebar.markdown("#### **SYSTEM STATUS**")
    if status_data:
        backend_active = "🟢" if backend_mode else "🔴"
        db_active = "🟢" if status_data.get("database_connected") else "🟡"
        telem_active = "🟢" if (status_data.get("telemetry_count", 0) > 0 or status_data.get("mqtt_connected")) else "⚪"
        st.sidebar.markdown(f"{backend_active} **Backend Connected**")
        st.sidebar.markdown(f"{db_active} **Database Connected**")
        st.sidebar.markdown(f"{telem_active} **Telemetry Active**")
    else:
        st.sidebar.warning("Connecting to Intelligence Engine...")

    st.sidebar.divider()
    st.sidebar.markdown("#### **DEMO CONTROLS**")

    col_sb1, col_sb2 = st.sidebar.columns(2)
    with col_sb1:
        if st.sidebar.button("▶️ Run Demo", use_container_width=True, help="Executes 6-phase canonical demonstration scenario"):
            with st.spinner("Executing 6-phase scenario and ingesting telemetry..."):
                from scripts.run_final_demo import run_authoritative_demo
                run_authoritative_demo(steps_per_phase=10, dt_seconds=1.0)
                st.rerun()

    with col_sb2:
        if st.sidebar.button("🔄 Reset Demo", use_container_width=True, help="Resets demo telemetry buffer and baseline"):
            demo_state.reset()
            if "copilot_result" in st.session_state:
                st.session_state["copilot_result"] = None
            if "copilot_query" in st.session_state:
                st.session_state["copilot_query"] = "What is the factory energy consumption and how does it compare with baseline?"
            st.rerun()

    if st.sidebar.button("⚡ Refresh Data", use_container_width=True):
        st.rerun()

    st.sidebar.divider()
    curr_phase = status_data.get('current_scenario_phase', 'PHASE_A_NORMAL') if status_data else 'PHASE_A_NORMAL'
    st.sidebar.markdown(f"**DEMO SCENARIO:** `{curr_phase}`")

    st.sidebar.divider()
    st.sidebar.markdown("#### **FLEET NAVIGATION**")

    machine_options = ["All Factory Assets"] + [get_machine_display_name(m_id) for m_id in sorted(DEFAULT_PROFILES.keys())]
    selected_machine_option = st.sidebar.selectbox("Inspect Asset:", options=machine_options, index=0)
    selected_m_id = None if selected_machine_option.startswith("All") else selected_machine_option.split(" - ")[0]

    # Move technical/debug details into expandable System Diagnostics
    with st.sidebar.expander("⚙️ System Diagnostics", expanded=False):
        if status_data:
            st.markdown(f"**Backend Mode:** `{backend_mode}`")
            st.markdown(f"**Telemetry Count:** `{status_data.get('telemetry_count', 0):,}` records")
            st.markdown(f"**Elapsed Time:** `{status_data.get('elapsed_time_seconds', 0.0):.1f}s`")
            st.markdown(f"**Database:** `{'Connected (PostgreSQL/SQLite)' if status_data.get('database_connected') else 'Fallback In-Memory'}`")
            st.markdown(f"**MQTT Ingestion:** `{'Active QoS 1' if status_data.get('mqtt_connected') else 'In-Process Loop'}`")
            st.markdown(f"**Model Type:** `Ridge Regression (Production-Aware)`")
        else:
            st.caption("Diagnostics unavailable while connecting.")

    st.sidebar.divider()
    st.sidebar.caption("Configured Tariff: ₹8.50/kWh | Configured CO₂ Factor: 0.716 kg CO₂/kWh")
    st.sidebar.markdown("""
    <small style='color: #64748B;'>
    <b>Responsibility Boundaries:</b><br>
    • Person 1: Machine Power & Sleep Control<br>
    • Person 2: Component Mechanical Health<br>
    • <b>Person 3: Energy & Production Analytics</b><br>
    • Person 4: Platform & Cloud Infrastructure
    </small>
    """, unsafe_allow_html=True)

    # TOP DEMO BANNER
    st.markdown("""
    <div class="demo-banner">
        <div>
            <span style="color: #3DCD58; font-weight: 700; font-size: 14px;">⚡ DEMONSTRATION — SIMULATED FACTORY TELEMETRY</span>
            <div style="color: #94A3B8; font-size: 12px; margin-top: 2px;">
                Person 3 Energy & Production Intelligence Engine | Schneider Electric 2026 Smart Manufacturing Hackathon
            </div>
        </div>
        <div>
            <span class="badge badge-measured">[MEASURED]</span>
            <span class="badge badge-calc">[CALCULATED]</span>
            <span class="badge badge-pred">[PREDICTED]</span>
            <span class="badge badge-rec">[RECOMMENDED]</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # FETCH AUTHORITATIVE FACTORY SNAPSHOT
    factory_snapshot, _ = fetch_api("/demo/factory")

    if not factory_snapshot:
        st.error("Unable to load factory telemetry snapshot. Ensure backend engine is initialized.")
        st.stop()

    prod_info = factory_snapshot.get("production", {})
    energy_info = factory_snapshot.get("energy", {})
    sec_val = factory_snapshot.get("sec")
    util_val = factory_snapshot.get("utilization", 0.0)
    dev_info = factory_snapshot.get("deviation", {})
    savings_info = factory_snapshot.get("savings", {})
    machines_status = factory_snapshot.get("machine_status", [])
    window_info = factory_snapshot.get("analysis_window", {}) or {}
    df_machines = pd.DataFrame(machines_status)

    # AUTHORITATIVE ANALYSIS WINDOW DISPLAY
    w_start = window_info.get("start_time", "N/A")
    w_end = window_info.get("end_time", "N/A")
    w_dur = window_info.get("duration_seconds", 0.0)
    st.markdown(f"""
    <div style="background-color: #161B26; border: 1px solid #262F40; border-radius: 6px; padding: 8px 16px; margin-bottom: 16px; display: flex; align-items: center; justify-content: space-between; font-size: 12px;">
        <div>
            <span style="color: #94A3B8; font-weight: 600; text-transform: uppercase;">⏱️ Authoritative Analysis Window:</span>
            <span style="color: #F8FAFC; margin-left: 8px; font-family: monospace;">{w_start} → {w_end}</span>
        </div>
        <div>
            <span style="color: #94A3B8;">Window Duration:</span>
            <span style="color: #38BDF8; font-weight: 700; margin-left: 4px;">{w_dur:.1f} sec</span>
            <span style="color: #64748B; margin-left: 8px;">(All metrics strictly share this temporal window)</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 1. FACTORY OVERVIEW KPIS
    st.markdown("### **1. Factory Intelligence Overview**")
    kpi_cols = st.columns(8)

    with kpi_cols[0]:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-card-title"><span class="badge badge-calc">[CALC]</span> Total Energy</div>
            <div class="metric-card-val">{safe_float(energy_info.get('actual_energy_kwh'), 4)} <small style='font-size:12px;'>kWh</small></div>
            <div class="metric-card-sub">Demo analysis window</div>
        </div>
        """, unsafe_allow_html=True)

    with kpi_cols[1]:
        total_units = prod_info.get('total_units', 0)
        active_prod = prod_info.get('active_producing_machines', 0)
        running_cnt = prod_info.get('running_machines', 0)
        if total_units == 0:
            prod_sub = f"{running_cnt}/4 running (0 producing)"
        else:
            prod_sub = f"{active_prod}/4 producing ({running_cnt} running)"
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-card-title"><span class="badge badge-measured">[MEAS]</span> Production</div>
            <div class="metric-card-val">{safe_val(total_units)} <small style='font-size:12px;'>units</small></div>
            <div class="metric-card-sub">{prod_sub}</div>
        </div>
        """, unsafe_allow_html=True)

    with kpi_cols[2]:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-card-title"><span class="badge badge-calc">[CALC]</span> Factory SEC</div>
            <div class="metric-card-val">{safe_float(sec_val, 4)}</div>
            <div class="metric-card-sub">kWh/unit (Normalized)</div>
        </div>
        """, unsafe_allow_html=True)

    with kpi_cols[3]:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-card-title"><span class="badge badge-pred">[PRED]</span> Baseline</div>
            <div class="metric-card-val">{safe_float(energy_info.get('expected_energy_kwh'), 4)} <small style='font-size:12px;'>kWh</small></div>
            <div class="metric-card-sub">Production-aware model</div>
        </div>
        """, unsafe_allow_html=True)

    with kpi_cols[4]:
        dev_kwh = dev_info.get("deviation_kwh", 0.0)
        dev_pct = dev_info.get("deviation_pct", 0.0)
        dev_status = dev_info.get("status", "NORMAL")
        status_class = "status-normal" if dev_kwh <= 0 else ("status-elevated" if dev_status == "ELEVATED" else "status-high")
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-card-title"><span class="badge badge-calc">[CALC]</span> Deviation</div>
            <div class="metric-card-val {status_class}">{dev_kwh:+.4f} <small style='font-size:12px;'>kWh</small></div>
            <div class="metric-card-sub">{dev_pct:+.1f}% vs baseline ({dev_status})</div>
        </div>
        """, unsafe_allow_html=True)

    with kpi_cols[5]:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-card-title"><span class="badge badge-calc">[CALC]</span> Energy Cost</div>
            <div class="metric-card-val">{safe_currency(energy_info.get('cost_inr'))}</div>
            <div class="metric-card-sub">Tariff: ₹8.50/kWh</div>
        </div>
        """, unsafe_allow_html=True)

    with kpi_cols[6]:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-card-title"><span class="badge badge-calc">[CALC]</span> Carbon Footprint</div>
            <div class="metric-card-val">{safe_float(energy_info.get('co2_kg'), 4)} <small style='font-size:12px;'>kg</small></div>
            <div class="metric-card-sub">Configured: 0.716 kg CO₂/kWh</div>
        </div>
        """, unsafe_allow_html=True)

    with kpi_cols[7]:
        pot_kwh = savings_info.get("potential_savings_kwh", 0.0)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-card-title"><span class="badge badge-calc">[CALC]</span> Potential Savings</div>
            <div class="metric-card-val">{safe_float(pot_kwh, 4)} <small style='font-size:12px;'>kWh</small></div>
            <div class="metric-card-sub">{safe_currency(savings_info.get('potential_savings_inr'))} gross opportunity</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    # 2. ENERGY VS PRODUCTION & 3. ACTUAL VS BASELINE
    col_chart1, col_chart2 = st.columns([1, 1])

    with col_chart1:
        st.markdown("#### **2. Energy vs Production Activity**")
        if not df_machines.empty and "production_units" in df_machines.columns:
            fig_prod = px.scatter(
                df_machines,
                x="production_units",
                y="energy_kwh",
                size="power_kw",
                color="state",
                hover_name="name",
                text="machine_id",
                labels={
                    "production_units": "Production Output (Units) [MEASURED]",
                    "energy_kwh": "Consumed Energy in Window (kWh) [CALCULATED]",
                    "power_kw": "Active Power (kW)",
                    "state": "Operating State",
                },
                color_discrete_map={
                    "RUNNING": "#3DCD58",
                    "IDLE": "#F5A623",
                    "SLEEP": "#3B82F6",
                    "DEGRADED": "#EF4444",
                    "OVERLOAD": "#8B5CF6",
                },
                title="Asset Energy Consumption vs Production Output",
            )
            fig_prod.update_traces(textposition="top center", marker=dict(opacity=0.9, line=dict(width=1, color="#1E293B")))
            fig_prod.update_layout(
                template="plotly_dark",
                height=320,
                margin=dict(l=10, r=10, t=35, b=10),
                plot_bgcolor="#161B26",
                paper_bgcolor="#161B26",
            )
            st.plotly_chart(fig_prod, use_container_width=True)
            st.caption("<small style='color:#64748B;'>Bubble size represents active power demand (kW). High energy with zero production indicates unproductive states.</small>", unsafe_allow_html=True)
        else:
            st.info("Accumulating machine telemetry for production analysis...")

    with col_chart2:
        st.markdown("#### **3. Actual vs Production-Aware Baseline**")
        act_e = energy_info.get("actual_energy_kwh", 0.0)
        exp_e = energy_info.get("expected_energy_kwh", 0.0)

        fig_base = go.Figure()
        fig_base.add_trace(go.Bar(
            name="Expected Baseline [PREDICTED]",
            x=["Factory Aggregate"],
            y=[exp_e],
            marker_color="#3B82F6",
            text=[f"{exp_e:.4f} kWh"],
            textposition="auto",
        ))
        fig_base.add_trace(go.Bar(
            name="Actual Energy [CALCULATED]",
            x=["Factory Aggregate"],
            y=[act_e],
            marker_color="#3DCD58" if dev_kwh <= 0 else ("#F5A623" if dev_status == "ELEVATED" else "#EF4444"),
            text=[f"{act_e:.4f} kWh"],
            textposition="auto",
        ))
        fig_base.update_layout(
            title=f"Baseline Deviation: {dev_kwh:+.4f} kWh ({dev_pct:+.1f}%) | Status: {dev_status}",
            barmode="group",
            template="plotly_dark",
            height=320,
            margin=dict(l=10, r=10, t=35, b=10),
            plot_bgcolor="#161B26",
            paper_bgcolor="#161B26",
            yaxis_title="Energy (kWh)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig_base, use_container_width=True)
        
        if dev_kwh <= 0:
            if prod_info.get('total_units', 0) == 0:
                st.caption("<small style='color:#3DCD58;'>✓ <b>Below Baseline:</b> Actual factory consumption is operating below model baseline expectations for this window. Production output is zero, so production efficiency cannot be evaluated using SEC.</small>", unsafe_allow_html=True)
            else:
                st.caption("<small style='color:#3DCD58;'>✓ <b>Nominal Efficiency:</b> Actual factory consumption is operating below model baseline expectations.</small>", unsafe_allow_html=True)
        else:
            st.caption(f"<small style='color:#F5A623;'>⚠️ <b>Above-Baseline Draw:</b> Factory is consuming +{dev_kwh:.4f} kWh above expected operating envelope.</small>", unsafe_allow_html=True)

    st.divider()

    # 4. MACHINE FLEET TABLE
    st.markdown("### **4. Monitored Machine Fleet Intelligence**")

    if not df_machines.empty:
        display_df = df_machines[[
            "machine_id", "name", "state", "power_kw", "energy_kwh", "cumulative_energy_kwh",
            "production_units", "sec", "deviation_pct", "deviation_status", "health_score"
        ]].copy()
        display_df.columns = [
            "ID", "Asset Profile", "State [MEAS]", "Power (kW) [MEAS]", "Energy Consumed (kWh) [CALC]", 
            "Cumulative Meter (kWh) [MEAS]", "Production (u) [MEAS]", "SEC (kWh/u) [CALC]", "Deviation (%)", "Energy Status", "Health [P2 CONTEXT]"
        ]
        st.dataframe(
            display_df.style.format({
                "Power (kW) [MEAS]": "{:.2f}",
                "Energy Consumed (kWh) [CALC]": "{:.4f}",
                "Cumulative Meter (kWh) [MEAS]": "{:.4f}",
                "Production (u) [MEAS]": "{:d}",
                "SEC (kWh/u) [CALC]": lambda x: f"{x:.4f}" if pd.notna(x) else "N/A",
                "Deviation (%)": "{:+.1f}%",
                "Health [P2 CONTEXT]": "{:.1f}",
            }),
            use_container_width=True,
        )
        st.caption("<small style='color:#64748B;'>*Note: Energy Consumed is interval consumption over the analysis window. Cumulative Meter is the absolute meter register. Health metrics are provided as context by Person 2.*</small>", unsafe_allow_html=True)
    else:
        st.info("No active telemetry records available in the current window.")

    # 5. ASSET DEEP-DIVE & HEALTH TELEMETRY
    st.divider()
    st.markdown("### **5. Asset Deep-Dive & Health Telemetry**")

    asset_choices = {m_id: get_machine_display_name(m_id) for m_id in sorted(DEFAULT_PROFILES.keys())}
    if selected_m_id:
        inspect_m_id = selected_m_id
        st.caption(f"Currently inspecting **{get_machine_display_name(inspect_m_id)}** (Controlled via Fleet Navigation in sidebar)")
    else:
        inspect_m_id = "M01"
        st.caption(f"Currently inspecting **{get_machine_display_name(inspect_m_id)}** (Default asset for deep analysis. Select a specific asset in Fleet Navigation to switch)")

    m_detail, _ = fetch_api(f"/demo/machine/{inspect_m_id}")

    if m_detail:
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        with m_col1:
            st.markdown(
                '<div class="metric-card">'
                '<div class="metric-card-title"><span class="badge badge-measured">[MEAS]</span> Operational State</div>'
                f'<div class="metric-card-val">{m_detail.get("current_state", "UNKNOWN")}</div>'
                f'<div class="metric-card-sub">Power: {safe_float(m_detail.get("power_kw"), 2)} kW</div>'
                '</div>',
                unsafe_allow_html=True,
            )
            
        with m_col2:
            st.markdown(
                '<div class="metric-card">'
                '<div class="metric-card-title"><span class="badge badge-calc">[CALC]</span> Consumed Energy</div>'
                f'<div class="metric-card-val">{safe_float(m_detail.get("actual_energy_kwh"), 4)} <small style="font-size:12px;">kWh</small></div>'
                f'<div class="metric-card-sub" title="Interval delta used for analysis">Cumulative meter: {safe_float(m_detail.get("energy_kwh"), 4)} kWh</div>'
                '</div>',
                unsafe_allow_html=True,
            )

        with m_col3:
            m_dev = m_detail.get("deviation_kwh", 0.0) or 0.0
            m_dev_pct = m_detail.get("deviation_pct", 0.0) or 0.0
            st.markdown(
                '<div class="metric-card">'
                '<div class="metric-card-title"><span class="badge badge-calc">[CALC]</span> Baseline Deviation</div>'
                f'<div class="metric-card-val">{m_dev:+.4f} <small style="font-size:12px;">kWh</small></div>'
                f'<div class="metric-card-sub">Expected: {safe_float(m_detail.get("baseline_expected_energy_kwh"), 4)} kWh ({m_dev_pct:+.1f}%)</div>'
                '</div>',
                unsafe_allow_html=True,
            )

        with m_col4:
            st.markdown(
                '<div class="metric-card">'
                '<div class="metric-card-title"><span class="badge badge-calc">[CALC]</span> Process SEC</div>'
                f'<div class="metric-card-val">{safe_sec(m_detail.get("sec"))}</div>'
                f'<div class="metric-card-sub">Production: {safe_val(m_detail.get("production_units"))} units</div>'
                '</div>',
                unsafe_allow_html=True,
            )

        hc = m_detail.get("health_context", {})
        curr_state = m_detail.get("current_state", "UNKNOWN")
        disp_rpm = 0.0 if curr_state in ("SLEEP", "OFF") else hc.get('rpm', 1450.0)
        st.markdown("##### **Person 2 Contextual Health Signals (Advisory Only)**")
        hc_cols = st.columns(6)
        hc_cols[0].metric("Health Score", f"{hc.get('health_score', 100.0):.1f}/100")
        hc_cols[1].metric("Anomaly Score", f"{hc.get('anomaly_score', 0.0):.3f}")
        hc_cols[2].metric("Temperature", f"{hc.get('temperature_c', 50.0):.1f} °C")
        hc_cols[3].metric("Vibration RMS", f"{hc.get('vibration', 0.15):.3f} mm/s")
        hc_cols[4].metric("Motor Speed", f"{disp_rpm:.0f} RPM")
        hc_cols[5].metric(
            "Productive Utilization",
            f"{m_detail.get('utilization_rate', 0.0) * 100:.1f}%",
            help="Calculated over the authoritative analysis window as (Productive Time [RUNNING, DEGRADED, OVERLOAD] / Total Observed Time) * 100.",
        )
        st.caption("<small style='color:#64748B;'>*Responsibility boundary: Health and anomaly metrics are ingested as context from Person 2's subsystem. Mechanical fault diagnosis remains exclusive to Person 2.*</small>", unsafe_allow_html=True)

    st.divider()

    # 6. OPERATIONAL STATE ENERGY & 7. NON-PRODUCTION ENERGY
    col_state1, col_state2 = st.columns([1, 1])

    with col_state1:
        st.markdown("### **6. Operational State Energy Allocation**")
        state_eff_data, _ = fetch_api("/savings/states")
        
        if state_eff_data and "states" in state_eff_data:
            df_states = pd.DataFrame(state_eff_data["states"])
            if not df_states.empty:
                if "machine_state" in df_states.columns and "state" not in df_states.columns:
                    df_states["state"] = df_states["machine_state"]
                if "actual_energy_kwh" in df_states.columns and "energy_kwh" not in df_states.columns:
                    df_states["energy_kwh"] = df_states["actual_energy_kwh"]

                fig_bar_state = px.bar(
                    df_states,
                    x="state",
                    y="energy_kwh",
                    color="state",
                    text="energy_kwh",
                    labels={"state": "Operating State", "energy_kwh": "Energy Consumed (kWh)"},
                    color_discrete_map={
                        "RUNNING": "#3DCD58",
                        "IDLE": "#F5A623",
                        "SLEEP": "#3B82F6",
                        "DEGRADED": "#EF4444",
                        "OVERLOAD": "#8B5CF6",
                    },
                    title="Energy Consumption by Machine Operational State (Bar Chart)",
                )
                fig_bar_state.update_traces(texttemplate="%{y:.4f} kWh", textposition="outside")
                fig_bar_state.update_layout(
                    template="plotly_dark",
                    height=300,
                    margin=dict(l=10, r=10, t=35, b=10),
                    plot_bgcolor="#161B26",
                    paper_bgcolor="#161B26",
                    showlegend=False,
                    yaxis_title="Energy (kWh)",
                )
                st.plotly_chart(fig_bar_state, use_container_width=True)
                st.caption("<small style='color:#64748B;'>Reveals electrical energy consumed during non-productive intervals (IDLE and SLEEP states).</small>", unsafe_allow_html=True)
        else:
            st.info("Operational state aggregation accumulating...")

    with col_state2:
        st.markdown("### **7. Non-Production Energy Intelligence**")
        
        idle_kwh = 0.0
        sleep_kwh = 0.0
        total_factory_kwh = energy_info.get("actual_energy_kwh", 0.0) or 0.0001
        
        if state_eff_data and "states" in state_eff_data:
            for s in state_eff_data["states"]:
                s_name = s.get("state") or s.get("machine_state")
                s_e = s.get("energy_kwh") or s.get("actual_energy_kwh", 0.0)
                if s_name == "IDLE":
                    idle_kwh = s_e
                elif s_name == "SLEEP":
                    sleep_kwh = s_e

        idle_pct = (idle_kwh / total_factory_kwh * 100.0) if total_factory_kwh > 0 else 0.0
        sleep_pct = (sleep_kwh / total_factory_kwh * 100.0) if total_factory_kwh > 0 else 0.0

        st.markdown(f"""
        <div class="metric-card">
            <h5 style="color: #F5A623; margin-top: 0;">Unproductive Idle Energy Allocation</h5>
            <p style="font-size: 20px; font-weight: 700; margin: 0;">{idle_kwh:.4f} kWh <span style="font-size: 13px; color: #F5A623;">({idle_pct:.1f}% of factory total)</span></p>
            <p style="color: #94A3B8; font-size: 12px; margin-top: 4px;">Energy consumed while production count is zero. Represents operational curtailment opportunity.</p>
            <hr style="border-color: #262F40; margin: 10px 0;"/>
            <h5 style="color: #3B82F6; margin-top: 0;">ECO Sleep Standby Draw</h5>
            <p style="font-size: 18px; font-weight: 600; margin: 0;">{sleep_kwh:.4f} kWh <span style="font-size: 13px; color: #3B82F6;">({sleep_pct:.1f}% of factory total)</span></p>
            <p style="color: #94A3B8; font-size: 12px; margin-top: 4px;">Low-power baseline standby mode configured via Person 1 power optimization rules.</p>
        </div>
        """, unsafe_allow_html=True)
        st.caption("<small style='color:#64748B;'>*Wording note: Idle energy represents an operational optimization opportunity, not necessarily waste. During demonstration, M01 experienced an IDLE cycle during Phase B which contributes to this factory allocation.*</small>", unsafe_allow_html=True)

    st.divider()

    # 8. SHORT-HORIZON FORECAST & 9. SAVINGS VERIFICATION
    col_fc, col_sav = st.columns([1, 1])

    with col_fc:
        st.markdown("### **8. Short-Horizon Energy Consumption Forecast [PREDICTED]**")
        fc_info = factory_snapshot.get("forecast", {})
        intervals = fc_info.get("intervals", [])
        
        if intervals:
            tot_fc = fc_info.get('total_forecast_kwh', 0.0)
            avg_fc = (tot_fc / len(intervals)) if len(intervals) > 0 else (tot_fc / 5.0)
            st.markdown(f"""
            <div style="background-color: #161B26; border: 1px solid #262F40; border-radius: 6px; padding: 10px 14px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="color: #94A3B8; font-size: 11px; font-weight: 600; text-transform: uppercase;">FORECASTED ENERGY — NEXT 5 MINUTES</div>
                    <div style="color: #38BDF8; font-size: 20px; font-weight: 700; margin-top: 2px;">{tot_fc:.4f} <small style="font-size: 12px; color: #94A3B8;">kWh (Total 5-min)</small></div>
                </div>
                <div style="text-align: right;">
                    <div style="color: #94A3B8; font-size: 11px; font-weight: 600; text-transform: uppercase;">AVERAGE DEMAND RATE</div>
                    <div style="color: #F8FAFC; font-size: 16px; font-weight: 600; margin-top: 2px;">~{avg_fc:.4f} <small style="font-size: 12px; color: #94A3B8;">kWh/min</small></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            df_fc = pd.DataFrame(intervals)
            fig_fc = px.line(
                df_fc,
                x="step",
                y="forecast_energy_kwh",
                markers=True,
                title="Forward Interval 1–5: Projected Energy per 1-Minute Interval",
                labels={"step": "Forward Interval (1-5, 1-min steps)", "forecast_energy_kwh": "Projected Energy per 1-Min Interval (kWh)"},
            )
            fig_fc.update_traces(line_color="#38BDF8", line_width=2.5, marker=dict(size=7))
            fig_fc.update_layout(
                template="plotly_dark",
                height=260,
                margin=dict(l=10, r=10, t=35, b=10),
                plot_bgcolor="#161B26",
                paper_bgcolor="#161B26",
                yaxis_title="Projected kWh/min",
            )
            st.plotly_chart(fig_fc, use_container_width=True)
            step_sum = sum(x.get('forecast_energy_kwh', 0.0) for x in intervals)
            st.caption(f"<small style='color:#38BDF8;'><b>Projected Energy Consumption — Next 5 Minutes:</b> {tot_fc:.4f} kWh (Sum of five 1-minute steps: {step_sum:.4f} kWh) | <b>Average Rate:</b> ~{avg_fc:.4f} kWh/min | Model: {fc_info.get('model_type', 'GradientBoostingRegressor')}</small>", unsafe_allow_html=True)
        else:
            st.info("Forecasting model initialized. Projecting next 5 intervals...")

    with col_sav:
        st.markdown("### **9. Savings Intelligence & Production-Normalized Verification**")
        
        verified_kwh = savings_info.get("verified_savings_kwh", 0.0)
        tot_units = prod_info.get("total_units", 0)
        if tot_units == 0:
            verified_status = "INSUFFICIENT DATA"
            verified_sub = "No production output was recorded in the analysis window, so production-normalized SEC improvement cannot be verified."
        else:
            verified_status = "SAVINGS_VERIFIED" if verified_kwh > 0 else "NO_IMPROVEMENT"
            verified_sub = "Production-normalized Specific Energy Consumption improvement post-intervention."

        pot_sav_kwh = savings_info.get("potential_savings_kwh", 0.0)
        pot_sav_inr = safe_currency(savings_info.get("potential_savings_inr"))
        pot_co2 = safe_float(savings_info.get("potential_co2_kg"), 4)

        if pot_sav_kwh <= 0:
            savings_explanation_html = (
                '<p style="color: #94A3B8; font-size: 11px; margin-top: 4px; line-height: 1.4;">'
                'No above-baseline energy savings opportunity was detected in this window because actual '
                'consumption is already operating below the production-aware baseline. '
                'Potential gross savings: 0.0000 kWh (₹0.00).'
                '</p>'
            )
        else:
            savings_explanation_html = (
                f'<p style="color: #94A3B8; font-size: 11px; margin-top: 2px;">'
                f'Derived as max(0, Actual - Expected). Potential avoided emissions: {pot_co2} kg CO₂.'
                '</p>'
            )

        savings_card_html = (
            '<div class="metric-card">'
            '<div style="display: flex; justify-content: space-between; align-items: center;">'
            '<h5 style="color: #10B981; margin: 0;">Potential Gross Savings Opportunity</h5>'
            '<span class="badge badge-calc">[CALCULATED]</span>'
            '</div>'
            f'<p style="font-size: 20px; font-weight: 700; margin: 4px 0 0 0;">{pot_sav_kwh:.4f} kWh <span style="font-size: 14px; color: #10B981;">({pot_sav_inr})</span></p>'
            f'{savings_explanation_html}'
            '<hr style="border-color: #262F40; margin: 10px 0;"/>'
            '<div style="display: flex; justify-content: space-between; align-items: center;">'
            '<h5 style="color: #38BDF8; margin: 0;">Verified Savings (Production-Normalized SEC)</h5>'
            '<span class="badge badge-pred">[VERIFIED]</span>'
            '</div>'
            f'<p style="font-size: 18px; font-weight: 600; margin: 4px 0 0 0;">{verified_kwh:.4f} kWh <span style="font-size: 12px; color: #94A3B8;">(Status: {verified_status})</span></p>'
            f'<p style="color: #94A3B8; font-size: 11px; margin-top: 2px;">{verified_sub}</p>'
            '</div>'
        )
        st.markdown(savings_card_html, unsafe_allow_html=True)
        st.caption("<small style='color:#64748B;'>*Production-normalized verification methodology inspired by measurement and verification principles; not accredited IPMVP verification. Potential savings represent gross above-baseline reduction; not guaranteed financial ROI. ROI/payback is only computed when implementation CAPEX is explicitly configured.*</small>", unsafe_allow_html=True)

    st.divider()

    # 10. PRIORITIZED OPTIMIZATION OPPORTUNITIES
    st.markdown("### **10. Prioritized Energy Optimization Opportunities [RECOMMENDED]**")

    opps = factory_snapshot.get("optimization_opportunities", [])
    if opps:
        for opp in opps[:4]:
            cat = opp.get("category", "OPERATIONAL_DEVIATION")
            p_score = opp.get("priority_score", 50.0)
            m_target = opp.get("machine_id", "Factory")
            
            cat_badge_color = {
                "IDLE_REDUCTION": "#F59E0B",
                "OPERATIONAL_DEVIATION": "#EF4444",
                "PROCESS_EFFICIENCY": "#10B981",
                "MAINTENANCE_ALIGNMENT": "#8B5CF6",
                "THROUGHPUT_OPTIMIZATION": "#3B82F6",
            }.get(cat, "#64748B")

            st.markdown(f"""
            <div class="metric-card" style="border-left: 4px solid {cat_badge_color};">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span class="badge" style="background-color: {cat_badge_color}22; color: {cat_badge_color}; border: 1px solid {cat_badge_color};">{cat}</span>
                    <span style="color: #F8FAFC; font-weight: 700; font-size: 13px;">Priority Score: {p_score:.0f}/100</span>
                </div>
                <h5 style="margin: 8px 0 4px 0; color: #F8FAFC;">Target Asset: <b>{m_target}</b></h5>
                <p style="color: #CBD5E1; font-size: 13px; margin-bottom: 4px;">{opp.get('reason')}</p>
                <p style="color: #10B981; font-size: 12px; margin: 0;"><b>Suggested Analytic Action:</b> {opp.get('suggested_action')}</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No persistent above-baseline energy deviation was detected in the current analysis window. All machines operating nominally within expected baseline limits.")

    st.caption("<small style='color:#64748B;'>*Responsibility note: Person 3 identifies energy and process efficiency opportunities for operator evaluation. Direct actuator or PLC commands belong to Person 1.*</small>", unsafe_allow_html=True)

    st.divider()

    # 11. GROUNDED ENERGY COPILOT (PERSISTENT CONVERSATIONAL INTERFACE)
    # Ensure proper session state model
    if "copilot_messages" not in st.session_state:
        # Check if chat_messages exists for backward compatibility
        if "chat_messages" in st.session_state and isinstance(st.session_state["chat_messages"], list):
            st.session_state["copilot_messages"] = st.session_state["chat_messages"]
        else:
            st.session_state["copilot_messages"] = [
                {
                    "role": "assistant",
                    "content": (
                        "Hello! I am your factory Energy Intelligence Copilot.\n\n"
                        "I can help you understand energy consumption, production-aware baselines, SEC, "
                        "idle and sleep energy, machine-level performance, forecasts, savings opportunities, "
                        "and operational efficiency.\n\n"
                        "For example, you can ask:\n"
                        "• What is the factory energy consumption?\n"
                        "• Which machine should I investigate first?\n"
                        "• Why is M01 consuming energy while not producing?\n"
                        "• Can we calculate SEC right now?\n"
                        "• What is the predicted energy consumption for the next 5 minutes?\n\n"
                        "All numerical answers are grounded directly in authoritative Python factory analytics."
                    ),
                    "intent": "GENERAL_CHAT",
                    "model_used": "system",
                    "fallback_used": True,
                    "grounded": True,
                    "context_summary": {},
                }
            ]
    # Keep chat_messages synchronized for backward compatibility
    st.session_state["chat_messages"] = st.session_state["copilot_messages"]

    if "copilot_draft" not in st.session_state:
        st.session_state["copilot_draft"] = ""
    if "copilot_input_key" not in st.session_state:
        st.session_state["copilot_input_key"] = 0

    copilot_header_col1, copilot_header_col2 = st.columns([4, 1])
    with copilot_header_col1:
        st.markdown("### **11. Grounded Energy Intelligence Copilot**")
        st.caption("Interactive conversational assistant grounded strictly in authoritative Python factory analytics.")
    with copilot_header_col2:
        if st.button("🧹 Clear Chat", use_container_width=True, help="Clear conversation history without resetting telemetry or demo state"):
            st.session_state["copilot_messages"] = [
                {
                    "role": "assistant",
                    "content": "Conversation cleared. How can I help you with factory energy and production analytics?",
                    "intent": "GENERAL_CHAT",
                    "model_used": "system",
                    "fallback_used": True,
                    "grounded": True,
                    "context_summary": {},
                }
            ]
            st.session_state["chat_messages"] = st.session_state["copilot_messages"]
            st.session_state["copilot_draft"] = ""
            st.session_state["copilot_input_key"] = st.session_state.get("copilot_input_key", 0) + 1
            st.rerun()

    # Preset Quick Action Queries (Populate input only - do NOT auto-submit into chat)
    st.markdown("##### **Quick Preset Queries**")
    preset_cols = st.columns(5)
    if preset_cols[0].button("🏭 Factory Baseline", use_container_width=True, help="Populate factory baseline comparison query"):
        st.session_state["copilot_draft"] = "Give me the current factory energy consumption and compare it with the production-aware baseline."
        st.session_state["copilot_input_key"] = st.session_state.get("copilot_input_key", 0) + 1
        st.rerun()
    if preset_cols[1].button("⚠️ Top Opportunity", use_container_width=True, help="Populate top priority efficiency opportunity query"):
        st.session_state["copilot_draft"] = "Which energy optimization opportunity currently has the highest calculated priority, and what evidence supports it?"
        st.session_state["copilot_input_key"] = st.session_state.get("copilot_input_key", 0) + 1
        st.rerun()
    if preset_cols[2].button("💤 Idle Energy Analysis", use_container_width=True, help="Populate non-production energy query"):
        st.session_state["copilot_draft"] = "How much energy is being consumed during non-production states, especially IDLE and SLEEP?"
        st.session_state["copilot_input_key"] = st.session_state.get("copilot_input_key", 0) + 1
        st.rerun()
    if preset_cols[3].button("🔍 Machine M01 Status", use_container_width=True, help="Populate machine M01 status query"):
        st.session_state["copilot_draft"] = "Give me the current operational and energy status of M01."
        st.session_state["copilot_input_key"] = st.session_state.get("copilot_input_key", 0) + 1
        st.rerun()
    if preset_cols[4].button("🔮 5-Min Forecast", use_container_width=True, help="Populate 5-minute forecast query"):
        st.session_state["copilot_draft"] = "What is the predicted energy consumption for the next five minutes?"
        st.session_state["copilot_input_key"] = st.session_state.get("copilot_input_key", 0) + 1
        st.rerun()

    # Example Questions Chips (Populate input only - do NOT auto-submit into chat)
    st.markdown("##### **Example Questions**")
    example_cols = st.columns(5)
    if example_cols[0].button("❓ What can you do?", use_container_width=True):
        st.session_state["copilot_draft"] = "What can you do?"
        st.session_state["copilot_input_key"] = st.session_state.get("copilot_input_key", 0) + 1
        st.rerun()
    if example_cols[1].button("⚡ Total Energy", use_container_width=True):
        st.session_state["copilot_draft"] = "What is the factory energy consumption?"
        st.session_state["copilot_input_key"] = st.session_state.get("copilot_input_key", 0) + 1
        st.rerun()
    if example_cols[2].button("📉 Can we calculate SEC?", use_container_width=True):
        st.session_state["copilot_draft"] = "Can we calculate SEC right now?"
        st.session_state["copilot_input_key"] = st.session_state.get("copilot_input_key", 0) + 1
        st.rerun()
    if example_cols[3].button("🚨 Investigate Asset", use_container_width=True):
        st.session_state["copilot_draft"] = "Which machine should I investigate first?"
        st.session_state["copilot_input_key"] = st.session_state.get("copilot_input_key", 0) + 1
        st.rerun()
    if example_cols[4].button("⚖️ Baseline Efficiency", use_container_width=True):
        st.session_state["copilot_draft"] = "How does factory energy compare with baseline?"
        st.session_state["copilot_input_key"] = st.session_state.get("copilot_input_key", 0) + 1
        st.rerun()

    def handle_copilot_submission(query_text: str):
        cleaned_query = query_text.strip()
        if not cleaned_query:
            return

        # 1. Append user message to history
        st.session_state["copilot_messages"].append({
            "role": "user",
            "content": cleaned_query,
        })
        st.session_state["chat_messages"] = st.session_state["copilot_messages"]

        # 2. Build bounded history payload (last 8 messages)
        history_payload = []
        for m in st.session_state["copilot_messages"][:-1][-8:]:
            if m.get("role") in ("user", "assistant") and m.get("content"):
                history_payload.append({
                    "role": m["role"],
                    "content": m["content"],
                })

        # 3. Request payload with optional machine context from dashboard selection
        payload = {
            "question": cleaned_query,
            "history": history_payload,
        }
        # If user did not specify machine in text, default to currently selected machine in dashboard
        sel_machine = st.session_state.get("selected_machine_id")
        if sel_machine and sel_machine not in ("All", "ALL"):
            payload["machine_id"] = sel_machine

        with st.spinner("Analyzing authoritative Python evidence and generating explanation..."):
            res, _ = fetch_api("/copilot/chat", method="POST", payload=payload)
            if res and isinstance(res, dict):
                st.session_state["copilot_messages"].append({
                    "role": "assistant",
                    "content": res.get("answer", "No response generated."),
                    "intent": res.get("intent", "GENERAL_CHAT"),
                    "model_used": res.get("model_used", "deterministic_analytics_fallback"),
                    "fallback_used": res.get("fallback_used", False),
                    "context_summary": res.get("context_summary", {}),
                    "grounded": res.get("grounded", True),
                })
            else:
                st.session_state["copilot_messages"].append({
                    "role": "assistant",
                    "content": "Unable to connect to Copilot intelligence backend. Please verify FastAPI service is running on port 8000.",
                    "intent": "ERROR",
                    "model_used": "system",
                    "fallback_used": True,
                    "context_summary": {},
                    "grounded": False,
                })
            st.session_state["chat_messages"] = st.session_state["copilot_messages"]

    # Bounded internally scrollable chat history container
    st.markdown("##### **Conversation History**")
    chat_container = st.container(height=420)
    with chat_container:
        for msg in st.session_state["copilot_messages"]:
            role = msg.get("role", "assistant")
            content = msg.get("content", "")

            if role == "user":
                import html
                escaped_content = html.escape(content).replace("\n", "<br>")
                st.markdown(
                    f"""
                    <div style="background: linear-gradient(135deg, #1E293B, #0F172A); border: 1px solid #334155; border-left: 4px solid #3B82F6; border-radius: 8px; padding: 12px 16px; margin-bottom: 12px;">
                        <div style="font-weight: 600; color: #60A5FA; margin-bottom: 4px; font-size: 13px;">👤 You</div>
                        <div style="color: #F1F5F9; font-size: 14px; line-height: 1.5;">{escaped_content}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                intent = msg.get("intent", "GENERAL_CHAT")
                if intent == "GENERAL_CHAT":
                    badge_html = '<span style="font-size: 11px; background-color: #334155; color: #CBD5E1; padding: 2px 8px; border-radius: 4px; border: 1px solid #475569;">GENERAL CHAT</span>'
                elif intent in ("MACHINE_ANALYSIS", "DEEP_DIVE", "MACHINE_HEALTH_CONTEXT"):
                    badge_html = f'<span style="font-size: 11px; background-color: #064E3B; color: #A7F3D0; padding: 2px 8px; border-radius: 4px; border: 1px solid #059669;">GROUNDED ✓ | {intent}</span>'
                else:
                    badge_html = f'<span style="font-size: 11px; background-color: #064E3B; color: #A7F3D0; padding: 2px 8px; border-radius: 4px; border: 1px solid #059669;">GROUNDED ✓ | {intent}</span>'

                import html
                escaped_content = html.escape(content).replace("\n", "<br>")
                st.markdown(
                    f"""
                    <div style="background: linear-gradient(135deg, #0F172A, #161E2E); border: 1px solid #1E293B; border-left: 4px solid #10B981; border-radius: 8px; padding: 14px 16px; margin-bottom: 12px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <span style="font-weight: 600; color: #34D399; font-size: 13px;">🤖 Energy Copilot</span>
                            {badge_html}
                        </div>
                        <div style="color: #E2E8F0; font-size: 14px; line-height: 1.6;">{escaped_content}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                ctx = msg.get("context_summary")
                if ctx and isinstance(ctx, dict) and len(ctx) > 0:
                    with st.expander("🔍 Telemetry Evidence & Provenance", expanded=False):
                        st.markdown(f"**Grounding Validation:** PASSED &nbsp;|&nbsp; **Engine:** `{msg.get('model_used', 'Deterministic')}` &nbsp;|&nbsp; **Deterministic Fallback:** `{msg.get('fallback_used', False)}`")
                        st.json(ctx)

    # Question Input Form (Always visible below bounded chat container)
    st.markdown("##### **Ask Copilot**")
    current_key = st.session_state.get("copilot_input_key", 0)
    with st.form(key=f"copilot_form_{current_key}", clear_on_submit=False):
        col_input, col_submit = st.columns([5, 1])
        with col_input:
            user_question = st.text_input(
                "Ask Copilot anything about the factory...",
                value=st.session_state.get("copilot_draft", ""),
                placeholder="Ask Copilot anything about the factory (e.g. Which machine should I investigate first?)...",
                label_visibility="collapsed",
            )
        with col_submit:
            submit_clicked = st.form_submit_button("🚀 Ask Copilot", type="primary", use_container_width=True)

    if submit_clicked:
        cleaned = user_question.strip()
        if cleaned:
            # Process query
            st.session_state["copilot_draft"] = ""
            st.session_state["copilot_input_key"] = current_key + 1
            handle_copilot_submission(cleaned)
            st.rerun()
        else:
            st.warning("Please type a question before submitting to Copilot.")

    st.markdown("<br><hr><center><small style='color: #64748B;'>Schneider Electric Smart Manufacturing 2026 | Person 3: Energy & Production Intelligence Engine</small></center>", unsafe_allow_html=True)


if __name__ == "__main__" or "streamlit" in sys.argv[0]:
    render_dashboard()
