from fastapi import APIRouter
from pydantic import BaseModel, Field
from app.services.optimization import optimize_schedule
from app.services.impact import impact_from

router = APIRouter(prefix="/simulation", tags=["simulation"])


class WhatIfRequest(BaseModel):
    load_shift_pct: float = Field(ge=-50, le=50, default=10)
    peak_cap_kw: float = Field(ge=200, le=1000, default=620)
    solar_add_kw: float = Field(ge=0, le=500, default=50)


@router.post("/what-if")
def what_if(request: WhatIfRequest):
    result = optimize_schedule()
    impact = impact_from(result)
    scale = max(0.5, 1 - request.load_shift_pct / 100)
    impact["cost_saved_inr"] = round(impact["cost_saved_inr"] + request.solar_add_kw * 7.3 * 30 + (request.peak_cap_kw - result.optimized_peak_kw) * 12, 1)
    impact["energy_saved_kwh"] = round(impact["energy_saved_kwh"] * scale + request.solar_add_kw * 0.68, 1)
    impact["co2_reduction_kg"] = round(impact["energy_saved_kwh"] * 0.71, 1)
    return {"scenario": request.model_dump(), "impact": impact, "optimized_schedule": result.schedule}
