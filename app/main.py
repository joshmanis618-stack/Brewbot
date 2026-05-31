import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.database import engine, SessionLocal
from app.models import Base
from app.services import mqtt as mqtt_service
import app.seed as seed_module

# API routes
from app.routes.recipes import router as recipes_router
from app.routes.equipment import router as equipment_router
from app.routes.styles import router as styles_router
from app.routes.brew_sessions import router as brew_sessions_router
from app.routes.ingredients import fermentables_router, hops_router, yeasts_router, miscs_router
from app.routes.devices import router as devices_router

# Web (HTML) routes — registered last so API routes take precedence on /
from app.routes.web import router as web_router, public_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Create all tables from current models (idempotent, safe on existing DBs)
    Base.metadata.create_all(bind=engine)

    # 2. Alembic: stamp fresh installs as current; upgrade existing installs
    from alembic.config import Config
    from alembic import command as alembic_command
    from sqlalchemy import inspect as sa_inspect, text

    alembic_cfg = Config("alembic.ini")
    with engine.connect() as conn:
        if not sa_inspect(engine).has_table("alembic_version"):
            # Brand-new DB — create_all already built everything; just record current revision
            alembic_command.stamp(alembic_cfg, "head")
        else:
            # Existing install — apply any pending migrations
            alembic_command.upgrade(alembic_cfg, "head")

    db = SessionLocal()
    try:
        seed_module.run(db)
    finally:
        db.close()
    mqtt_task = asyncio.create_task(mqtt_service.run())
    yield
    mqtt_task.cancel()
    try:
        await mqtt_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="Brewbot",
    description="Server-based homebrewing recipe manager and brew system controller",
    lifespan=lifespan,
)

app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET", "change-me-in-production-use-env-var"),
    session_cookie="brewbot_session",
    max_age=86400 * 7,  # 7 days
    same_site="lax",
    https_only=False,
)

# Static files
app.mount(
    "/static",
    StaticFiles(directory=str(Path(__file__).parent / "static")),
    name="static",
)

# API routes (prefixed with /api to avoid clashing with web routes)
app.include_router(recipes_router, prefix="/api")
app.include_router(equipment_router, prefix="/api")
app.include_router(styles_router, prefix="/api")
app.include_router(brew_sessions_router, prefix="/api")
app.include_router(fermentables_router, prefix="/api")
app.include_router(hops_router, prefix="/api")
app.include_router(yeasts_router, prefix="/api")
app.include_router(miscs_router, prefix="/api")
app.include_router(devices_router, prefix="/api")  # must be /api — avoids shadowing web GET/POST /devices

# Web routes (HTML pages) — public (unauthenticated) routes first
app.include_router(public_router)
app.include_router(web_router)
