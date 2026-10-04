from fastapi import APIRouter
from pydantic import BaseModel, Field
from app.services.optimization import optimize_schedule
from app.services.impact import impact_from

router = APIRouter(prefix="/optimization", tags=["optimization"])


class Task(BaseModel):
    name: str
    duration: int = Field(ge=1, le=8)
    power_kw: int = Field(ge=1, le=1000)
    units: int = Field(ge=1, le=100000)


class OptimizationRequest(BaseModel):
    tasks: list[Task] | None = None


@router.post("/optimize")
def optimize(request: OptimizationRequest):
    result = optimize_schedule([task.model_dump() for task in request.tasks] if request.tasks else None)
    return {
        "schedule": result.schedule,
        "baseline_cost": result.baseline_cost,
        "optimized_cost": result.optimized_cost,
        "baseline_peak_kw": result.baseline_peak_kw,
        "optimized_peak_kw": result.optimized_peak_kw,
        "impact": impact_from(result),
    }
