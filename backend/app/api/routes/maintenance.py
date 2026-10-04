from fastapi import APIRouter
from app.services.demo_data import maintenance_windows

router = APIRouter(prefix="/maintenance", tags=["maintenance"])


@router.get("/windows")
def windows():
    return {"windows": maintenance_windows()}
