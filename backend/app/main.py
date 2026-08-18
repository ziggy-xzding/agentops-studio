from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.agents.registry import AgentNotFound
from app.api.agents import router as agents_router
from app.api.runs import router as runs_router
from app.api.work_orders import router as work_orders_router
from app.config import get_settings
from app.db import initialize_database
from app.domain.runs import InvalidTransition
from app.services.runs import RunNotFound, WorkOrderNotFound


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="AgentOps Studio API",
    version="0.1.0",
    description="Operate human-in-the-loop agent workflows with observable run state.",
    lifespan=lifespan,
)
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RunNotFound)
async def handle_not_found(_: Request, exc: RunNotFound) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"detail": {"code": "run_not_found", "message": str(exc)}},
    )


@app.exception_handler(AgentNotFound)
async def handle_agent_not_found(_: Request, exc: AgentNotFound) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"detail": {"code": "agent_not_found", "message": str(exc)}},
    )


@app.exception_handler(WorkOrderNotFound)
async def handle_work_order_not_found(_: Request, exc: WorkOrderNotFound) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"detail": {"code": "work_order_not_found", "message": str(exc)}},
    )


@app.exception_handler(InvalidTransition)
async def handle_invalid_transition(_: Request, exc: InvalidTransition) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={"detail": {"code": "invalid_transition", "message": str(exc)}},
    )


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(runs_router, prefix="/api")
app.include_router(agents_router, prefix="/api")
app.include_router(work_orders_router, prefix="/api")
