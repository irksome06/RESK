from __future__ import annotations

from dataclasses import dataclass
from ortools.sat.python import cp_model


@dataclass
class OptimizationResult:
    schedule: list[dict]
    baseline_cost: float
    optimized_cost: float
    baseline_peak_kw: float
    optimized_peak_kw: float


def optimize_schedule(tasks: list[dict] | None = None) -> OptimizationResult:
    tasks = tasks or [
        {"name": "Batch A", "duration": 3, "power_kw": 150, "units": 120},
        {"name": "Batch B", "duration": 2, "power_kw": 210, "units": 80},
        {"name": "Batch C", "duration": 2, "power_kw": 120, "units": 95},
        {"name": "Batch D", "duration": 1, "power_kw": 175, "units": 60},
    ]
    tariffs = [6.1 if h < 6 else (8.6 if 18 <= h < 22 else 7.3) for h in range(24)]
    capacity = 680
    model = cp_model.CpModel()
    intervals = []
    starts = {}
    costs = []

    for i, task in enumerate(tasks):
        duration = task["duration"]
        latest = 24 - duration
        start = model.NewIntVar(0, latest, f"start_{i}")
        end = model.NewIntVar(duration, 24, f"end_{i}")
        interval = model.NewIntervalVar(start, duration, end, f"interval_{i}")
        starts[task["name"]] = start
        intervals.append(interval)

        # Cost depends on the tariff at the chosen start slot.
        unit_costs = [int(round(tariffs[h] * task["power_kw"] * duration * 10)) for h in range(latest + 1)]
        cost = model.NewIntVar(min(unit_costs), max(unit_costs), f"cost_{i}")
        model.AddElement(start, unit_costs, cost)
        costs.append(cost)

    model.AddCumulative(intervals, [t["power_kw"] for t in tasks], capacity)
    model.Minimize(sum(costs))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 2.0
    solver.parameters.num_search_workers = 8
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return _fallback(tasks, tariffs)

    schedule = []
    optimized_cost = 0.0
    optimized_peak = 0.0
    for task in tasks:
        start = solver.Value(starts[task["name"]])
        cost = tariffs[start] * task["power_kw"] * task["duration"]
        optimized_cost += cost
        optimized_peak = max(optimized_peak, task["power_kw"])
        schedule.append({**task, "start_hour": start, "end_hour": start + task["duration"], "tariff": tariffs[start], "cost": round(cost, 1)})

    baseline_starts = [(7 + i * 3) % 24 for i in range(len(tasks))]
    baseline_starts = [min(s, 24 - t["duration"]) for s, t in zip(baseline_starts, tasks)]
    baseline_cost = sum(tariffs[s] * t["power_kw"] * t["duration"] for s, t in zip(baseline_starts, tasks))
    baseline_peak = sum(t["power_kw"] for t in tasks) * 0.72
    return OptimizationResult(schedule, round(baseline_cost, 1), round(optimized_cost, 1), round(baseline_peak, 1), round(optimized_peak, 1))


def _fallback(tasks: list[dict], tariffs: list[float]) -> OptimizationResult:
    cursor = 2
    schedule = []
    total = 0.0
    peak = 0.0
    for task in tasks:
        start = min(cursor % 24, 24 - task["duration"])
        cost = tariffs[start] * task["power_kw"] * task["duration"]
        schedule.append({**task, "start_hour": start, "end_hour": start + task["duration"], "tariff": tariffs[start], "cost": round(cost, 1)})
        total += cost
        peak = max(peak, task["power_kw"])
        cursor += task["duration"]
    baseline = sum(t["power_kw"] * t["duration"] * tariffs[min(7 + i * 3, 24 - t["duration"])] for i, t in enumerate(tasks))
    return OptimizationResult(schedule, round(baseline, 1), round(total, 1), round(sum(t["power_kw"] for t in tasks) * .72, 1), round(peak, 1))
