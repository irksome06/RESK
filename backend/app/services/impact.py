from __future__ import annotations


def impact_from(optimization) -> dict:
    energy_saved_kwh = max(0.0, (optimization.baseline_peak_kw - optimization.optimized_peak_kw) * 4.2)
    cost_saved = max(0.0, optimization.baseline_cost - optimization.optimized_cost)
    peak_reduction = max(0.0, optimization.baseline_peak_kw - optimization.optimized_peak_kw)
    co2_reduction = energy_saved_kwh * 0.71
    roi = cost_saved / 18000 if cost_saved else 0
    return {
        "energy_saved_kwh": round(energy_saved_kwh, 1),
        "cost_saved_inr": round(cost_saved, 1),
        "peak_reduction_kw": round(peak_reduction, 1),
        "co2_reduction_kg": round(co2_reduction, 1),
        "roi_pct": round(roi * 100, 1),
        "payback_days": round(18000 / max(cost_saved, 1) / 30, 1),
    }
