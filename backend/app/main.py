import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from backend.app.database import Base, engine
from backend.app.routes.auth import router as auth_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("resk.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create database tables automatically
    logger.info("Initializing RESK database schema...")
    Base.metadata.create_all(bind=engine)
    logger.info("RESK database initialized successfully.")
    yield
    logger.info("RESK backend shutting down.")


app = FastAPI(
    title="RESK - Industrial Organization Authentication API",
    description="Enterprise organization identity, authentication, and registration management system.",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS for local development and production frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(auth_router)


@app.get("/", tags=["System"])
def root():
    return {
        "system": "RESK Industrial Platform",
        "status": "operational",
        "docs_url": "/docs",
        "api_prefix": "/auth",
    }


@app.get("/health", tags=["System"])
def health_check():
    return {"status": "healthy", "service": "resk-auth-backend"}
