"""
Phase 9 Machine-Level Energy Deviation Contribution Analytics.
Identifies and ranks which industrial machines contribute most to factory-level above-baseline energy:
- Computes factory-wide actual energy, expected baseline energy, and net deviation.
- Calculates each machine's percentage contribution to total positive factory deviation.
- Ranks machines strictly by energy deviation contribution (not by health score).
- Safely handles zero or negative total deviation denominators.
"""

from typing import List, Dict, Any, Optional


def compute_machine_contributions(
    machine_deviations: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Ranks machines by their contribution to factory above-baseline energy.

    Args:
        machine_deviations: List of per-machine deviation dictionaries, each containing:
            - machine_id
            - actual_energy_kwh
            - expected_energy_kwh
            - deviation_kwh
            - deviation_pct
            - status (optional)

    Returns:
        Dict containing:
            - factory_actual_kwh: float
            - factory_expected_kwh: float
            - factory_deviation_kwh: float
            - factory_deviation_pct: float
            - total_positive_deviation_kwh: float
            - factory_status: NORMAL, ABOVE_BASELINE, BELOW_BASELINE
            - contributors: List of machine contribution summaries ranked descending
    """
    if not machine_deviations:
        return {
            "factory_actual_kwh": 0.0,
            "factory_expected_kwh": 0.0,
            "factory_deviation_kwh": 0.0,
            "factory_deviation_pct": 0.0,
            "total_positive_deviation_kwh": 0.0,
            "factory_status": "NORMAL",
            "contributors": [],
        }

    factory_actual = sum(float(m.get("actual_energy_kwh", 0.0)) for m in machine_deviations)
    factory_expected = sum(float(m.get("expected_energy_kwh", 0.0)) for m in machine_deviations)
    factory_deviation = round(factory_actual - factory_expected, 6)

    if factory_expected > 1e-6:
        factory_deviation_pct = round((factory_deviation / factory_expected) * 100.0, 2)
    else:
        factory_deviation_pct = 0.0 if abs(factory_deviation) < 1e-6 else (100.0 if factory_actual > 0 else 0.0)

    # Total positive deviation across all machines
    positive_deviations = [
        max(0.0, float(m.get("deviation_kwh", 0.0))) for m in machine_deviations
    ]
    total_positive = round(sum(positive_deviations), 6)

    contributors: List[Dict[str, Any]] = []

    for m in machine_deviations:
        m_id = str(m.get("machine_id", "UNKNOWN"))
        act = float(m.get("actual_energy_kwh", 0.0))
        exp = float(m.get("expected_energy_kwh", 0.0))
        dev = float(m.get("deviation_kwh", 0.0))
        dev_pct = float(m.get("deviation_pct", 0.0))
        state = m.get("machine_state")

        # Contribution calculation with safe denominator guard
        if dev > 0.0 and total_positive > 1e-6:
            contrib_pct = round((dev / total_positive) * 100.0, 2)
        else:
            contrib_pct = 0.0

        contributors.append({
            "machine_id": m_id,
            "actual_energy_kwh": round(act, 6),
            "expected_energy_kwh": round(exp, 6),
            "deviation_kwh": round(dev, 6),
            "deviation_pct": round(dev_pct, 2),
            "contribution_pct": contrib_pct,
            "is_positive_contributor": dev > 0.0,
            "machine_state": state,
        })

    # Rank machines descending by deviation_kwh and contribution_pct
    contributors.sort(key=lambda x: x["deviation_kwh"], reverse=True)

    if factory_deviation_pct > 15.0:
        f_status = "ABOVE_BASELINE"
    elif factory_deviation_pct < -15.0:
        f_status = "BELOW_BASELINE"
    else:
        f_status = "NORMAL"

    return {
        "factory_actual_kwh": round(factory_actual, 6),
        "factory_expected_kwh": round(factory_expected, 6),
        "factory_deviation_kwh": factory_deviation,
        "factory_deviation_pct": factory_deviation_pct,
        "total_positive_deviation_kwh": total_positive,
        "factory_status": f_status,
        "contributors": contributors,
    }
