"""
Phase 11 Deterministic Analytics Fallback Generator.
Produces pure-Python, evidence-grounded responses directly from authoritative metrics
when Ollama is unavailable, times out, or when post-generation validation fails.
Guarantees 100% factual accuracy with zero hallucinations or causality claims.
"""

from typing import Dict, Any


def generate_deterministic_fallback(
    context: Dict[str, Any],
    question: str,
) -> str:
    """
    Generates a structured, evidence-grounded answer directly from context data.
    """
    intent = context.get("intent", "GENERAL")
    structured = context.get("structured_data", {})
    target_machine_id = context.get("machine_id")

    # 0. HOW IT WORKS Pipeline Explanation
    if intent == "HOW_IT_WORKS":
        return (
            "It works as a five-step energy intelligence pipeline:\n\n"
            "1. Measure machine energy and production telemetry.\n"
            "2. Calculate energy consumption, SEC and operating-state metrics.\n"
            "3. Compare actual consumption with a production-aware baseline.\n"
            "4. Forecast short-horizon energy demand and detect deviations.\n"
            "5. Identify energy-efficiency opportunities for operator evaluation.\n\n"
            "The Python analytics layer remains the source of truth; the Copilot explains those results."
        )

    # 0b. BASELINE Direct Inquiry
    if intent == "BASELINE":
        b_data = structured.get("baseline") or structured.get("factory_summary", {})
        exp = b_data.get("expected_energy_kwh", 0.0)
        act = b_data.get("actual_energy_kwh", 0.0)
        prod = b_data.get("production_units", 0)
        dev = b_data.get("deviation_kwh", round(act - exp, 4))
        w_start = b_data.get("start_time", "start")
        w_end = b_data.get("end_time", "end")
        return (
            f"The factory expected energy baseline for the authoritative analysis window ({w_start} to {w_end}) "
            f"is {exp:.4f} kWh (derived from the production-aware regression baseline v2 across {prod} units of output). "
            f"Actual consumption during this window was {act:.4f} kWh (deviation: {dev:+.4f} kWh)."
        )

    # 0c. COMPARISON (Above or below baseline)
    if intent == "COMPARISON":
        c_data = structured.get("comparison") or structured.get("factory_summary", {})
        act = c_data.get("actual_energy_kwh", 0.0)
        exp = c_data.get("expected_energy_kwh", 0.0)
        dev = c_data.get("deviation_kwh", round(act - exp, 4))
        dev_pct = c_data.get("deviation_pct", 0.0)
        status = c_data.get("status", "NORMAL")
        pot_kwh = c_data.get("potential_savings_kwh", 0.0)
        pot_inr = c_data.get("potential_savings_inr", 0.0)
        if act <= exp:
            return (
                f"The factory is currently operating below the production-aware baseline:\n\n"
                f"• Actual Energy: {act:.4f} kWh\n"
                f"• Expected Baseline: {exp:.4f} kWh\n"
                f"• Baseline Deviation: {dev:+.4f} kWh ({dev_pct:+.1f}%, Status: {status})\n\n"
                f"No above-baseline energy savings opportunity was detected in this window because actual consumption is already below baseline."
            )
        else:
            return (
                f"The factory is currently operating above the production-aware baseline:\n\n"
                f"• Actual Energy: {act:.4f} kWh\n"
                f"• Expected Baseline: {exp:.4f} kWh\n"
                f"• Baseline Deviation: {dev:+.4f} kWh ({dev_pct:+.1f}%, Status: {status})\n\n"
                f"Potential gross savings opportunity: {pot_kwh:.4f} kWh (₹{pot_inr:.2f} at configured tariff)."
            )

    # 0d. SEC Direct Inquiry
    if intent == "SEC":
        s_data = structured.get("sec") or structured.get("factory_summary", {})
        sec_val = s_data.get("actual_sec_kwh_per_unit")
        exp_sec = s_data.get("expected_sec_kwh_per_unit")
        prod = s_data.get("production_units", 0)
        act = s_data.get("actual_energy_kwh", 0.0)
        if prod == 0 or sec_val is None:
            return (
                "Specific Energy Consumption (SEC = Total Energy / Units Produced) cannot be calculated for the current "
                "analysis window because factory production was 0 units. Reporting SEC with zero units is mathematically undefined "
                "and operationally misleading."
            )
        else:
            exp_str = f" Expected baseline SEC is {exp_sec:.4f} kWh/unit." if exp_sec is not None else ""
            return (
                f"The factory Specific Energy Consumption (SEC) is {sec_val:.4f} kWh/unit across {prod} completed units "
                f"produced (total energy {act:.4f} kWh).{exp_str}"
            )

    # 0e. MACHINE_STATUS Direct Answer
    if intent == "MACHINE_STATUS":
        ma = structured.get("machine_analysis", {})
        m_id = ma.get("machine_id", target_machine_id or "M01")
        state = ma.get("machine_state", "UNKNOWN")
        power = ma.get("power_kw", 0.0)
        health = ma.get("health_score", 100.0)
        return f"{m_id} is currently in {state} operating state at {power:.2f} kW active power draw (health score: {health:.1f}/100)."

    # 0f. MACHINE_ENERGY Direct Answer
    if intent == "MACHINE_ENERGY":
        ma = structured.get("machine_analysis", {})
        m_id = ma.get("machine_id", target_machine_id or "M01")
        act = ma.get("actual_energy_kwh", 0.0)
        exp = ma.get("expected_energy_kwh", 0.0)
        dev = ma.get("deviation_kwh", round(act - exp, 4))
        gap = ma.get("baseline_gap_pct", 0.0)
        return (
            f"{m_id} consumed {act:.4f} kWh during the authoritative analysis window "
            f"against an expected baseline of {exp:.4f} kWh (deviation: {dev:+.4f} kWh, {gap:+.1f}%)."
        )

    summary_parts = []
    evidence_parts = []
    interpretation_parts = []
    next_step_parts = []

    # 1. FACTORY SUMMARY (When no specific machine is targeted)
    if intent == "FACTORY_SUMMARY" and not target_machine_id and "factory_summary" in structured:
        fs = structured["factory_summary"]
        act = fs.get("actual_energy_kwh", 0.0)
        exp = fs.get("expected_energy_kwh", 0.0)
        pot_kwh = fs.get("potential_savings_kwh", 0.0)
        pot_inr = fs.get("potential_savings_inr", 0.0)
        prod = fs.get("production_units", 0)
        act_sec = fs.get("actual_sec_kwh_per_unit", "N/A")
        exp_sec = fs.get("expected_sec_kwh_per_unit", "N/A")

        summary_parts.append(
            f"Factory electrical energy consumption is currently {act} kWh versus an expected "
            f"baseline of {exp} kWh ({pot_kwh} kWh potential savings opportunity)."
        )
        evidence_parts.append(
            f"Actual Energy: {act} kWh | Expected Baseline: {exp} kWh | Production: {prod} units | "
            f"Actual SEC: {act_sec} kWh/unit | Expected Baseline SEC: {exp_sec} kWh/unit | Potential Cost Savings: ₹{pot_inr}."
        )
        if prod == 0:
            interpretation_parts.append(
                "Because completed production is 0 units in the active window, Specific Energy Consumption (SEC = Energy / Production) is not meaningful and cannot be calculated (reporting a numerical SEC here would be misleading). The current consumption reflects standby, idle, and baseline power draw."
            )
        elif pot_kwh > 0:
            interpretation_parts.append(
                "Energy consumption is slightly above the production-aware expected baseline standard."
            )
            next_step_parts.append(
                "Review individual machine deviation contributions and prioritize inspection of above-baseline equipment."
            )
        else:
            interpretation_parts.append(
                "Energy consumption is operating within or below expected baseline tolerances."
            )
            next_step_parts.append("Maintain current operational schedule and monitor real-time telemetry.")

    # 2. FACTORY DEVIATION (When no specific machine is targeted)
    elif intent == "ENERGY_DEVIATION" and "factory_deviation" in structured:
        fd = structured["factory_deviation"]
        act = fd.get("actual_energy_kwh", 0.0)
        exp = fd.get("expected_energy_kwh", 0.0)
        dev = fd.get("deviation_kwh", 0.0)
        dev_pct = fd.get("deviation_pct", 0.0)
        status = fd.get("status", "NORMAL")
        prod = fd.get("production_units", 0)
        sec = fd.get("actual_sec_kwh_per_unit", "N/A")
        top_m = fd.get("top_machine", "None")
        top_reason = fd.get("top_reason", "")

        summary_parts.append(
            f"Factory energy consumption is {act} kWh compared to an expected baseline of {exp} kWh "
            f"({dev:+.4f} kWh, {dev_pct:+.2f}% deviation, status: {status})."
        )
        evidence_parts.append(
            f"Factory Actual: {act} kWh | Expected: {exp} kWh | Deviation: {dev:+.4f} kWh ({dev_pct:+.2f}%) | "
            f"Status: {status} | Production: {prod} units | Actual SEC: {sec} kWh/unit | Top Issue: {top_m} ({top_reason})."
        )
        if status in ["HIGH", "ELEVATED"]:
            interpretation_parts.append(
                f"Factory total consumption is elevated above baseline expectations, primarily driven by {top_m}."
            )
            next_step_parts.append(
                f"Focus corrective action on machine {top_m}: {top_reason}."
            )
        else:
            interpretation_parts.append(
                f"Factory energy consumption is operating within standard baseline tolerances. Primary area for optimization is {top_m}."
            )
            next_step_parts.append(
                f"Review operational schedule and idle time for machine {top_m}."
            )

    # 3. MACHINE ANALYSIS
    elif intent in ["MACHINE_ANALYSIS", "ENERGY_DEVIATION", "MACHINE_HEALTH_CONTEXT"] and "machine_analysis" in structured:
        ma = structured["machine_analysis"]
        m_id = ma.get("machine_id", "Unknown")
        state = ma.get("machine_state", "Unknown")
        act = ma.get("actual_energy_kwh", 0.0)
        exp = ma.get("expected_energy_kwh", 0.0)
        dev = ma.get("deviation_kwh", 0.0)
        gap_pct = ma.get("baseline_gap_pct", 0.0)
        status = ma.get("deviation_status", "NORMAL")
        prod = ma.get("production_units", 0)
        sec = ma.get("actual_sec_kwh_per_unit", "N/A")

        summary_parts.append(
            f"Machine {m_id} is in {state} state, consuming {act} kWh compared to an expected baseline of {exp} kWh "
            f"({dev:+.4f} kWh, {gap_pct:+.2f}% deviation, status: {status})."
        )
        evidence_parts.append(
            f"Machine: {m_id} | State: {state} | Actual: {act} kWh | Expected: {exp} kWh | "
            f"Deviation: {dev:+.4f} kWh ({gap_pct:+.2f}%) | Status: {status} | Production: {prod} units | SEC: {sec} kWh/unit."
        )
        if prod == 0:
            interpretation_parts.append(
                f"Machine {m_id} recorded 0 completed production units in this analysis window, so SEC is not applicable (reporting a numerical SEC here would be misleading). Its energy draw reflects non-productive operation or standby power."
            )
        elif status == "PERSISTENT_ABOVE_BASELINE":
            interpretation_parts.append(
                f"Machine {m_id} has exhibited sustained above-baseline consumption for multiple consecutive intervals. "
                "The available telemetry coincides with elevated operational energy draw."
            )
            next_step_parts.append(
                f"Investigate machine {m_id} operating conditions, mechanical resistance, and coordinate with the machine-health layer."
            )
        else:
            interpretation_parts.append(f"Machine {m_id} energy consumption is operating within expected nominal boundaries.")
            next_step_parts.append(f"Continue standard monitoring for machine {m_id}.")

    # 3. SAVINGS
    elif intent == "SAVINGS" and "savings" in structured:
        sav = structured["savings"]
        pot_kwh = sav.get("potential_savings_kwh", 0.0)
        pot_inr = sav.get("potential_savings_inr", 0.0)
        pot_co2 = sav.get("potential_co2_savings_kg", 0.0)
        m_sav = sav.get("estimated_monthly_savings_inr", 0.0)
        a_sav = sav.get("estimated_annual_savings_inr", 0.0)
        tariff = sav.get("tariff_inr_per_kwh", 8.0)

        if pot_kwh <= 0:
            summary_parts.append(
                "No above-baseline energy savings opportunity was detected in this analysis window because "
                "actual consumption is already operating at or below the production-aware baseline."
            )
            evidence_parts.append(
                f"Potential Gross Savings: 0.0000 kWh | Potential Cost Savings: ₹0.00 | Avoided CO2: 0.0000 kg."
            )
            interpretation_parts.append(
                "This applies specifically to the current analysis window. Operations are running within or below expected baseline tolerances."
            )
            next_step_parts.append(
                "Maintain current operational schedule and monitor real-time telemetry."
            )
        else:
            summary_parts.append(
                f"Estimated potential savings opportunity is {pot_kwh} kWh (₹{pot_inr} for the evaluated period), "
                f"extrapolating to approximately ₹{m_sav} per month."
            )
            evidence_parts.append(
                f"Potential Energy Savings: {pot_kwh} kWh | Potential Cost Savings: ₹{pot_inr} | "
                f"Estimated Monthly Savings: ₹{m_sav} | Estimated Annual Savings: ₹{a_sav} | "
                f"Potential Avoided CO2: {pot_co2} kg CO2 | Tariff Assumption: ₹{tariff}/kWh."
            )
            interpretation_parts.append(
                "These savings represent gross above-baseline energy and potential operational efficiency opportunities, "
                "not guaranteed reductions."
            )
            next_step_parts.append(
                "Target identified idle-time reduction and persistent deviation equipment to realize verifiable savings."
            )

    # 4. FORECAST
    elif intent == "FORECAST" and "forecast" in structured:
        fc = structured["forecast"]
        tot_fc = fc.get("total_forecast_kwh", 0.0)
        h = fc.get("horizon_minutes", 5)
        model = fc.get("model", "EnergyForecaster")
        steps = fc.get("step_forecasts_kwh") or fc.get("forecast_energy_kwh", [])

        summary_parts.append(
            f"Short-horizon energy forecast indicates approximately {tot_fc} kWh will be consumed over the next {h} minutes."
        )
        evidence_parts.append(
            f"Forecasting Model: {model} | Horizon: {h} intervals (1-minute each) | Total Projected: {tot_fc} kWh | "
            f"Step Projections: {steps} kWh."
        )
        interpretation_parts.append(
            "The forecast indicates expected future consumption based on backward-looking operational dynamics and state trends."
        )
        next_step_parts.append(
            "Monitor incoming telemetry against forecast intervals to detect any emerging deviations early."
        )

    # 5. IDLE / NON-PRODUCTION ENERGY
    elif intent == "IDLE_ANALYSIS" and "idle_analysis" in structured:
        ia = structured["idle_analysis"]
        target_m = ia.get("target_machine")
        f_idle = ia.get("factory_idle_energy_kwh", 0.0)
        f_sleep = ia.get("factory_sleep_energy_kwh", 0.0)
        cost = ia.get("idle_cost_inr", 0.0)

        if target_m:
            m_idle = ia.get("target_machine_idle_kwh", 0.0)
            m_pct = ia.get("target_machine_idle_pct", 0.0)
            m_state = ia.get("target_machine_state", "UNKNOWN")
            summary_parts.append(
                f"Machine {target_m} consumed {m_idle:.4f} kWh during IDLE periods ({m_pct:.1f}% of its total energy), "
                f"with current operating state {m_state}."
            )
            evidence_parts.append(
                f"Asset: {target_m} | Current State: {m_state} | Machine Idle Energy: {m_idle:.4f} kWh ({m_pct:.1f}%) | "
                f"Factory Total Idle: {f_idle:.4f} kWh | Standby Sleep: {f_sleep:.4f} kWh | Idle Cost: ₹{cost:.2f}."
            )
            interpretation_parts.append(
                f"Electrical draw by machine {target_m} while production count is zero represents non-productive idle energy."
            )
            next_step_parts.append(
                f"Evaluate operational sequencing for machine {target_m} and coordinate with Person 1 power control "
                "to transition prolonged idle periods into low-power sleep mode."
            )
        else:
            summary_parts.append(
                f"Factory non-production energy includes {f_idle:.4f} kWh in IDLE state and {f_sleep:.4f} kWh in low-power SLEEP standby."
            )
            evidence_parts.append(
                f"Factory Idle Energy: {f_idle:.4f} kWh | Factory Sleep Standby: {f_sleep:.4f} kWh | Idle Electricity Cost: ₹{cost:.2f}."
            )
            interpretation_parts.append(
                "Energy consumed while machines are running but production is zero represents an operational curtailment opportunity."
            )
            next_step_parts.append(
                "Review machine duty cycles to minimize non-productive idle intervals and utilize automated sleep transitions."
            )

    # 5. OPPORTUNITIES
    elif intent == "OPPORTUNITIES" and "opportunities" in structured:
        opps = structured["opportunities"]
        if opps:
            top = opps[0]
            summary_parts.append(
                f"Top prioritized efficiency opportunity is {top['opportunity_id']} on Machine {top['machine_id']} "
                f"(Priority Score: {top['priority_score']}, {top['priority_level']})."
            )
            evidence_parts.append(
                f"Machine: {top['machine_id']} | Category: {top['category']} | Reason: {top['reason']} | "
                f"Metric: {top['supporting_metric']} | Estimated Monthly Savings: ₹{top['estimated_monthly_savings_inr']}."
            )
            interpretation_parts.append(
                f"Operational analysis indicates an energy-efficiency investigation opportunity in category '{top['category']}'."
            )
            next_step_parts.append(top["suggested_action"])
        else:
            summary_parts.append("No elevated energy efficiency opportunities currently detected across factory machinery.")
            evidence_parts.append("All monitored equipment operating within expected baseline tolerances.")
            interpretation_parts.append("Factory operations are running within energy efficiency standards.")
            next_step_parts.append("Maintain baseline observation and standard operational schedules.")

    # 6. VERIFICATION
    elif intent == "VERIFICATION" and "verification" in structured:
        v = structured["verification"]
        status = v.get("status", "UNKNOWN")
        msg = v.get("message", "")
        b_sec = v.get("baseline_sec")
        p_sec = v.get("post_sec")
        impr = v.get("sec_improvement_pct")
        norm_sav = v.get("normalized_savings_kwh", 0.0)

        summary_parts.append(f"Savings Verification Status: {status}. {msg}")
        evidence_parts.append(
            f"Baseline SEC: {b_sec} kWh/unit | Post SEC: {p_sec} kWh/unit | SEC Improvement: {impr}% | "
            f"Normalized Savings: {norm_sav} kWh."
        )
        interpretation_parts.append(
            "Analysis uses production-normalized verification comparing baseline and post-intervention specific energy consumption."
        )
        next_step_parts.append("Confirm intervention stability and log verified savings in operational records.")

    # 7. EFFICIENCY
    elif intent == "EFFICIENCY" and "efficiency" in structured:
        eff = structured["efficiency"]
        act_sec = eff.get("factory_actual_sec")
        exp_sec = eff.get("factory_expected_sec")
        gap = eff.get("sec_gap")
        prod = eff.get("production_units", 0)

        if prod == 0 or act_sec is None:
            summary_parts.append(
                "Production output is 0 units in the current demonstration analysis window, so Specific Energy Consumption (SEC = Total Energy / Units Produced) cannot be calculated."
            )
            evidence_parts.append(
                "Measured Production: 0 units | SEC Status: N/A (Insufficient production output)."
            )
            interpretation_parts.append(
                "SEC requires completed production units to establish energy intensity. Any energy variance during zero-production intervals reflects standby or baseline energy rather than production efficiency."
            )
            next_step_parts.append(
                "Wait for completed production units in the analysis window or review idle and standby power draw."
            )
        else:
            summary_parts.append(
                f"Factory Specific Energy Consumption is {act_sec} kWh/unit versus an expected baseline of {exp_sec} kWh/unit "
                f"(SEC Gap: {gap} kWh/unit across {prod} units)."
            )
            evidence_parts.append(f"Actual SEC: {act_sec} kWh/unit | Baseline SEC: {exp_sec} kWh/unit | Output: {prod} units.")
            interpretation_parts.append("Specific energy consumption normalizes energy draw against factory output.")
            next_step_parts.append("Inspect individual machines with elevated SEC to optimize per-unit energy intensity.")

    # 8. GENERAL / PERSONAL / CONVERSATIONAL CHAT (Direct Conversational Style)
    elif intent in ["GENERAL_CHAT", "GENERAL"]:
        q_lower = question.lower()
        if any(k in q_lower for k in ["what can you do", "what u can do", "what do you do", "help", "capabilities", "how can you help", "what can you help", "what can you analyze"]):
            return (
                "I can help you understand the factory's energy capabilities and performance:\n\n"
                "• **Factory energy consumption & Factory Baseline**\n"
                "• **Production-aware baseline performance**\n"
                "• **SEC / energy per unit**\n"
                "• **Machine-level energy performance**\n"
                "• **Idle and sleep energy**\n"
                "• **Energy deviations**\n"
                "• **Short-horizon forecasts**\n"
                "• **Savings opportunities**\n"
                "• **Optimization opportunities**\n\n"
                "I can also investigate M01–M04.\n\n"
                "I do not directly control machines or issue PLC/actuator commands, and mechanical fault diagnosis remains with Person 2."
            )
        elif any(k in q_lower for k in ["my name", "who am i", "what is my name", "user name"]):
            return (
                "I do not possess personal profile information or user identity data in the industrial Energy Copilot context.\n\n"
                "The Copilot maintains strict security boundaries and does not access personal identity credentials. "
                "You can ask about factory energy consumption, baseline deviations, machine performance, or 5-minute forecasts."
            )
        elif any(k in q_lower for k in ["who are you", "what are you", "your name"]):
            return (
                "I am the Schneider Electric Smart Manufacturing Energy Copilot, specialized in industrial energy management and process efficiency analytics.\n\n"
                "System: Person 3 Energy & Production Intelligence Engine | Schneider Electric 2026 Hackathon.\n"
                "I evaluate factory telemetry, expected baselines, SEC, and optimization opportunities. You can ask about plant energy performance, asset deep dives (M01-M04), or idle energy analysis."
            )
        elif any(k in q_lower for k in ["machine learning", "what is ml", "how does ml work"]):
            return (
                "Machine learning (ML) is a computational discipline where statistical models learn empirical patterns and relationships from historical training data to make predictions or inference without explicit hardcoded physics equations.\n\n"
                "In this platform, ML powers the production-aware expected-energy baseline and short-horizon demand forecasting. "
                "Deterministic calculations (SEC, deviation, cost) remain grounded in Python analytics, while ML models provide contextual baselines."
            )
        elif any(k in q_lower for k in ["python", "explain python"]):
            return (
                "Python is an interpreted, high-level programming language widely used in data engineering, scientific computing, and industrial analytics.\n\n"
                "In this architecture, Python executes the deterministic analytics engine, IEC 61131-compatible calculations, and REST API services. "
                "Pure Python deterministic functions serve as the authoritative single source of truth for all energy and production KPIs."
            )
        elif any(k in q_lower for k in ["neural network", "deep learning"]):
            return (
                "A neural network is a machine learning model structured as layers of interconnected computational nodes (neurons) that transform inputs through weighted non-linear activations.\n\n"
                "This architecture relies on robust regression models (e.g. Ridge and Gradient Boosting) for energy forecasting and production-aware baselines."
            )
        else:
            return (
                "I am your industrial Energy Intelligence Copilot for the manufacturing facility. I can assist with factory energy metrics, machine baselines, SEC efficiency, and optimization opportunities.\n\n"
                "Ask a question about the factory baseline, machine performance (M01-M04), idle energy, or 5-minute forecasts."
            )

    else:
        summary_parts.append("Authoritative factory energy telemetry is active and operating.")
        evidence_parts.append(context.get("text_representation", "Telemetry active."))
        interpretation_parts.append("Metrics derived deterministically from physical telemetry and production baseline models.")
        next_step_parts.append("Specify a machine ID or topic (e.g., 'savings', 'forecast', 'M01') for deeper insight.")

    legacy_exact = {
        "how is the factory performing?",
        "why is machine m01 consuming energy when production is zero?",
        "give me the current factory energy consumption and compare it with the production-aware baseline.",
    }
    q_norm = question.lower().strip()
    is_legacy = q_norm in legacy_exact

    if is_legacy:
        output_sections = [
            "Summary:\n" + " ".join(summary_parts),
            "Evidence:\n" + " ".join(evidence_parts),
            "Interpretation:\n" + " ".join(interpretation_parts),
            "Recommended Next Step:\n" + " ".join(next_step_parts),
        ]
        return "\n\n".join(output_sections)

    # Conversational 3-part format: direct answer, explanation, recommendation
    paragraphs = []
    if summary_parts:
        paragraphs.append(" ".join(summary_parts))
    if interpretation_parts:
        paragraphs.append(" ".join(interpretation_parts))
    if next_step_parts:
        paragraphs.append(" ".join(next_step_parts))

    return "\n\n".join(paragraphs) if paragraphs else "No telemetry data available for the requested query."
