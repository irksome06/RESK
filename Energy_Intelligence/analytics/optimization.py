"""
Phase 10 Optimization Opportunity Engine & Efficiency Priority Intelligence.
Generates deterministic, evidence-based efficiency recommendations without crossing
into machine control (Person 1) or fault diagnosis (Person 2).

Core Rules:
1. Persistent above-baseline energy -> Investigate sustained operating conditions.
2. Significant idle energy -> Evaluate shortening idle or transitioning to low-power sleep mode.
3. High Specific Energy Consumption (SEC) -> Review production and operating parameters.
4. Degraded operating state with positive deviation -> Coordinate with machine-health layer.
5. High production throughput with rising SEC -> Review throughput efficiency.

Priority Score represents:
Energy-efficiency investigation priority (NOT machine failure probability or health score).
"""

from typing import List, Dict, Any, Optional
from database.schemas import TelemetryRecord, MachineState
from analytics.sec import calculate_sec
from analytics.savings import compute_machine_savings, calculate_roi_payback
from simulator.config import settings


class OptimizationOpportunityEngine:
    """
    Deterministic rule-based recommendation generator for industrial efficiency opportunities.
    """

    def __init__(
        self,
        idle_energy_threshold_pct: float = 15.0,
        high_sec_threshold_pct: float = 10.0,
        persistent_deviation_threshold_pct: float = 15.0,
    ):
        self.idle_energy_threshold_pct = idle_energy_threshold_pct
        self.high_sec_threshold_pct = high_sec_threshold_pct
        self.persistent_deviation_threshold_pct = persistent_deviation_threshold_pct

    def evaluate_machine(
        self,
        machine_id: str,
        records: List[TelemetryRecord],
        tariff_inr: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Scans machine telemetry history and returns detected efficiency opportunities.
        """
        if len(records) < 5:
            return []

        tariff = tariff_inr or settings.ELECTRICITY_COST_INR_PER_KWH
        savings_summary = compute_machine_savings(records, tariff_inr=tariff)
        opportunities: List[Dict[str, Any]] = []

        dev_kwh = savings_summary["deviation_kwh"]
        dev_pct = savings_summary["baseline_gap_pct"]
        dev_status = savings_summary.get("deviation_status", "NORMAL")
        persistent_intervals = savings_summary.get("persistent_intervals", 0)
        actual_kwh = savings_summary["actual_energy_kwh"]
        expected_kwh = savings_summary["expected_energy_kwh"]
        actual_sec = savings_summary.get("actual_sec_kwh_per_unit")
        expected_sec = savings_summary.get("expected_sec_kwh_per_unit")
        total_prod = savings_summary.get("total_production_units", 0)

        # 1. Condition: Persistent Above-Baseline Energy
        if dev_status == "PERSISTENT_ABOVE_BASELINE" or persistent_intervals >= 3:
            monthly_sav = round(savings_summary["persistent_savings_inr"] * 30.0, 2)
            roi = calculate_roi_payback(monthly_savings_inr=monthly_sav)
            priority_score = min(100.0, round(50.0 + min(30.0, dev_pct * 0.5) + min(20.0, persistent_intervals * 5.0), 1))
            opportunities.append({
                "opportunity_id": f"OPP-{machine_id}-PERSISTENT",
                "machine_id": machine_id,
                "category": "OPERATIONAL_DEVIATION",
                "condition": "Persistent above-baseline energy consumption",
                "reason": (
                    f"Machine {machine_id} exhibited {persistent_intervals} consecutive intervals "
                    f"with energy consumption exceeding expected baseline by {dev_pct}%."
                ),
                "supporting_metric": f"Excess energy: {dev_kwh:.4f} kWh (+{dev_pct}%)",
                "suggested_action": (
                    "Investigate operating conditions contributing to sustained above-baseline consumption; "
                    "review mechanical alignment and tooling resistance."
                ),
                "confidence": "HIGH",
                "priority_score": priority_score,
                "priority_level": "HIGH" if priority_score >= 70 else "MEDIUM",
                "estimated_monthly_savings_inr": monthly_sav,
                "estimated_annual_savings_inr": roi["annual_savings_inr"],
            })

        # 2. Condition: Significant Idle Energy
        idle_records = [r for r in records if r.machine_state == MachineState.IDLE]
        if idle_records and actual_kwh > 0:
            idle_kwh = sum(
                (r.power_kw * (r.dt_seconds if hasattr(r, "dt_seconds") and r.dt_seconds else 2.0) / 3600.0)
                for r in idle_records
            )
            idle_pct = round((idle_kwh / actual_kwh) * 100.0, 2)
            if idle_pct >= self.idle_energy_threshold_pct:
                monthly_sav = round(idle_kwh * 0.5 * tariff * 30.0, 2)  # Assume 50% reducible
                roi = calculate_roi_payback(monthly_savings_inr=monthly_sav)
                priority_score = min(100.0, round(30.0 + min(40.0, idle_pct), 1))
                opportunities.append({
                    "opportunity_id": f"OPP-{machine_id}-IDLE",
                    "machine_id": machine_id,
                    "category": "IDLE_REDUCTION",
                    "condition": "Significant energy consumed in IDLE state",
                    "reason": f"IDLE state accounts for {idle_pct}% of total electrical consumption ({idle_kwh:.4f} kWh).",
                    "supporting_metric": f"Idle energy proportion: {idle_pct}% of total consumption",
                    "suggested_action": (
                        "Evaluate whether idle periods can be shortened or transitioned "
                        "to an appropriate low-power sleep mode during prolonged non-production intervals."
                    ),
                    "confidence": "HIGH",
                    "priority_score": priority_score,
                    "priority_level": "HIGH" if priority_score >= 70 else "MEDIUM",
                    "estimated_monthly_savings_inr": monthly_sav,
                    "estimated_annual_savings_inr": roi["annual_savings_inr"],
                })

        # 3. Condition: High Specific Energy Consumption (SEC)
        if actual_sec is not None and expected_sec is not None and expected_sec > 0:
            sec_gap_pct = round(((actual_sec - expected_sec) / expected_sec) * 100.0, 2)
            if sec_gap_pct >= self.high_sec_threshold_pct:
                monthly_sav = round((actual_sec - expected_sec) * total_prod * tariff * 30.0, 2)
                roi = calculate_roi_payback(monthly_savings_inr=monthly_sav)
                priority_score = min(100.0, round(40.0 + min(40.0, sec_gap_pct), 1))
                opportunities.append({
                    "opportunity_id": f"OPP-{machine_id}-SEC",
                    "machine_id": machine_id,
                    "category": "PROCESS_EFFICIENCY",
                    "condition": "Elevated Specific Energy Consumption (SEC)",
                    "reason": f"Observed SEC ({actual_sec:.4f} kWh/unit) exceeds baseline expected SEC ({expected_sec:.4f} kWh/unit) by {sec_gap_pct}%.",
                    "supporting_metric": f"SEC gap: +{sec_gap_pct}% ({actual_sec:.4f} vs {expected_sec:.4f} kWh/unit)",
                    "suggested_action": (
                        "Review production and operating parameters for opportunities to reduce energy per unit; "
                        "verify feed rates and cycle timing."
                    ),
                    "confidence": "HIGH" if total_prod > 50 else "MEDIUM",
                    "priority_score": priority_score,
                    "priority_level": "HIGH" if priority_score >= 70 else "MEDIUM",
                    "estimated_monthly_savings_inr": monthly_sav,
                    "estimated_annual_savings_inr": roi["annual_savings_inr"],
                })

        # 4. Condition: Degraded State + Positive Deviation
        degraded_records = [r for r in records if r.machine_state == MachineState.DEGRADED]
        if degraded_records and dev_kwh > 0:
            priority_score = 85.0
            opportunities.append({
                "opportunity_id": f"OPP-{machine_id}-DEGRADED",
                "machine_id": machine_id,
                "category": "MAINTENANCE_ALIGNMENT",
                "condition": "Degraded operational state accompanied by energy deviation",
                "reason": (
                    f"Machine {machine_id} operated in DEGRADED state with {len(degraded_records)} observations, "
                    f"coinciding with above-baseline consumption of {dev_kwh:.4f} kWh."
                ),
                "supporting_metric": f"Degraded samples: {len(degraded_records)}, Deviation: +{dev_kwh:.4f} kWh",
                "suggested_action": (
                    "Coordinate with the machine-health layer (Person 2) to investigate mechanical/thermal "
                    "operating conditions and prevent energy penalty."
                ),
                "confidence": "HIGH",
                "priority_score": priority_score,
                "priority_level": "HIGH",
                "estimated_monthly_savings_inr": round(savings_summary["potential_savings_inr"] * 30.0, 2),
                "estimated_annual_savings_inr": round(savings_summary["potential_savings_inr"] * 365.0, 2),
            })

        # 5. Condition: High Throughput with Rising SEC
        prod_rates = [r.production_delta for r in records if r.production_delta and r.production_delta > 0]
        if len(prod_rates) > 10 and actual_sec is not None and expected_sec is not None:
            if total_prod > 100 and actual_sec > expected_sec * 1.05 and dev_pct > 8.0:
                priority_score = 65.0
                opportunities.append({
                    "opportunity_id": f"OPP-{machine_id}-THROUGHPUT",
                    "machine_id": machine_id,
                    "category": "THROUGHPUT_OPTIMIZATION",
                    "condition": "High production throughput with escalating energy intensity",
                    "reason": (
                        f"Machine produced {total_prod} units but showed rising SEC ({actual_sec:.4f} kWh/unit) "
                        f"and above-baseline energy (+{dev_pct}%)."
                    ),
                    "supporting_metric": f"Production: {total_prod} units, SEC: {actual_sec:.4f} kWh/unit",
                    "suggested_action": (
                        "Review whether increased throughput is causing disproportionate friction, thermal buildup, "
                        "or operating outside optimal efficiency curve."
                    ),
                    "confidence": "MEDIUM",
                    "priority_score": priority_score,
                    "priority_level": "MEDIUM",
                    "estimated_monthly_savings_inr": round(savings_summary["potential_savings_inr"] * 20.0, 2),
                    "estimated_annual_savings_inr": round(savings_summary["potential_savings_inr"] * 240.0, 2),
                })

        return opportunities

    def evaluate_factory(
        self,
        machine_records_dict: Dict[str, List[TelemetryRecord]],
        tariff_inr: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Aggregates and prioritizes opportunities across all factory machines.
        """
        all_opps: List[Dict[str, Any]] = []
        for m_id, recs in machine_records_dict.items():
            opps = self.evaluate_machine(m_id, recs, tariff_inr=tariff_inr)
            all_opps.extend(opps)

        # Rank strictly by energy-efficiency priority score
        all_opps.sort(key=lambda x: x["priority_score"], reverse=True)
        return all_opps


# Singleton opportunity engine instance
opportunity_engine = OptimizationOpportunityEngine()
