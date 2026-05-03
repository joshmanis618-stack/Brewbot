import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

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
from app.routes.web import router as web_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
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
app.include_router(devices_router)   # /devices, /rigs, /ws/readings — no prefix

# Web routes (HTML pages)
app.include_router(web_router)
