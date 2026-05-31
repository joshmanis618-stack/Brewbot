from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.brew_program import BrewProgram, BrewStep, BrewSessionStep
from app.models.brew_session import BrewSession
from app.models.device import Device, RigProfile
from app.models.equipment import Equipment
from app.models.fermentable import Fermentable
from app.models.fermentation_reading import FermentationReading
from app.models.hop import Hop
from app.models.misc import Misc
from app.models.recipe import Recipe, RecipeFermentable, RecipeHop, RecipeMisc, RecipeYeast
from app.models.style import Style
from app.models.yeast import Yeast
from app.models.user import User
from app.models.barrel import Barrel, BarrelAgingRecord, BarrelAgingEntry, BarrelDispositionEntry
from app.models.spirits import StillRun, StillCut
from app.models.session_production import SessionDryHop, PackagingEntry
from app.models.settings import AppSettings
from app.models.fermentation_reading import FermentationReading as _FR
from app.models.grape_variety import GrapeVariety, RecipeGrape
from app.models.mash_step import MashStep
from app.models.wine import WineMLFEntry, WineFiningEntry
import json
import csv
import io
from datetime import timedelta
from fastapi.responses import JSONResponse, StreamingResponse
from app.services import backup as backup_service
from app.services import beerxml as beerxml_service
from app.services import calc as calc_service
from app.services import auth as auth_service

from app.utils.units import register as _register_units, parse_vol, parse_temp, parse_area

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
_register_units(templates.env)

# SRM color scale (1–40+) for barrel aging entry swatches
_SRM_HEX = [
    "#FFE699","#FFD878","#FFCA5A","#FFBF42","#FBB123",
    "#F8A600","#F39C00","#EA8F00","#E58500","#DE7C00",
    "#D77200","#CF6900","#CB6100","#C35900","#BB5100",
    "#B54C00","#B04500","#A63E00","#A13700","#9B3200",
    "#952D00","#8E2900","#882300","#821E00","#7B1A00",
    "#771900","#701400","#6A0F00","#640B00","#5E0800",
    "#580600","#520500","#4C0400","#470300","#420200",
    "#3D0200","#370100","#340100","#2E0100","#1A0000",
]
def _srm_hex(srm):
    if srm is None:
        return "#cccccc"
    idx = max(0, min(int(round(srm)) - 1, len(_SRM_HEX) - 1))
    return _SRM_HEX[idx]

templates.env.filters["srm_hex"] = _srm_hex

_public_router = APIRouter(include_in_schema=False)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.get(User, user_id)


def require_auth(request: Request, db: Session = Depends(get_db)) -> User:
    # First-run: no users exist yet
    if db.query(User).count() == 0:
        raise HTTPException(status_code=307, headers={"Location": "/setup"})
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=307, headers={"Location": f"/login?next={request.url.path}"})
    user = db.get(User, user_id)
    if not user or not user.is_active:
        request.session.clear()
        raise HTTPException(status_code=307, headers={"Location": "/login"})
    return user


router = APIRouter(include_in_schema=False, dependencies=[Depends(require_auth)])


# ── Public auth routes (no authentication required) ───────────────────────────

@_public_router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, next: str = "/", error: str = ""):
    return templates.TemplateResponse(request, "login.html", {"next": next, "error": error})

@_public_router.post("/login")
async def login_submit(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    username = form.get("username", "").strip()
    password = form.get("password", "")
    next_url = form.get("next", "/")
    user = db.query(User).filter(User.username == username, User.is_active == True).first()
    if not user or not auth_service.verify_password(password, user.password_hash):
        return RedirectResponse(f"/login?next={next_url}&error=Invalid+username+or+password", status_code=303)
    if user.totp_enabled:
        request.session["pending_user_id"] = user.id
        request.session["pending_next"] = next_url
        return RedirectResponse("/login/2fa", status_code=303)
    request.session["user_id"] = user.id
    return RedirectResponse(next_url or "/", status_code=303)

@_public_router.get("/login/2fa", response_class=HTMLResponse)
def totp_page(request: Request, error: str = ""):
    if "pending_user_id" not in request.session:
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse(request, "login_2fa.html", {"error": error})

@_public_router.post("/login/2fa")
async def totp_submit(request: Request, db: Session = Depends(get_db)):
    pending_id = request.session.get("pending_user_id")
    if not pending_id:
        return RedirectResponse("/login", status_code=303)
    form = await request.form()
    code = form.get("code", "").replace(" ", "")
    user = db.get(User, pending_id)
    if not user or not auth_service.verify_totp(user.totp_secret, code):
        return RedirectResponse("/login/2fa?error=Invalid+code", status_code=303)
    next_url = request.session.pop("pending_next", "/")
    request.session.pop("pending_user_id", None)
    request.session["user_id"] = user.id
    return RedirectResponse(next_url or "/", status_code=303)

@_public_router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)

@_public_router.get("/setup", response_class=HTMLResponse)
def setup_page(request: Request, db: Session = Depends(get_db)):
    if db.query(User).count() > 0:
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse(request, "setup.html", {})

@_public_router.post("/setup")
async def setup_submit(request: Request, db: Session = Depends(get_db)):
    if db.query(User).count() > 0:
        return RedirectResponse("/login", status_code=303)
    form = await request.form()
    username = form.get("username", "").strip()
    password = form.get("password", "")
    email = form.get("email", "").strip() or None
    if not username or not password:
        return templates.TemplateResponse(request, "setup.html", {"error": "Username and password are required."})
    db.add(User(
        username=username,
        email=email,
        password_hash=auth_service.hash_password(password),
    ))
    db.commit()
    return RedirectResponse("/login", status_code=303)


def _form_context(db: Session) -> dict:
    return {
        "styles": db.query(Style).order_by(Style.name).all(),
        "equipment_list": db.query(Equipment).order_by(Equipment.name).all(),
        "all_fermentables": db.query(Fermentable).order_by(Fermentable.name).all(),
        "all_hops": db.query(Hop).order_by(Hop.name).all(),
        "all_yeasts": db.query(Yeast).order_by(Yeast.name).all(),
        "all_miscs": db.query(Misc).order_by(Misc.name).all(),
        "all_grapes": db.query(GrapeVariety).order_by(GrapeVariety.name).all(),
    }


# ── Craft switcher ────────────────────────────────────────────────────────────

@_public_router.post("/set-craft")
async def set_craft(request: Request):
    form = await request.form()
    craft = form.get("craft", "beer")
    if craft in ("beer", "wine", "spirits", "mead", "cider", "seltzer"):
        request.session["craft"] = craft
    ref = request.headers.get("referer", "/")
    return RedirectResponse(ref, status_code=303)


@router.post("/set-units")
async def set_units(request: Request):
    form = await request.form()
    units = form.get("units", "metric")
    if units in ("metric", "imperial"):
        request.session["units"] = units
    ref = request.headers.get("referer", "/")
    return RedirectResponse(ref, status_code=303)


def _parse_ingredients(form):
    """Parse indexed ingredient rows from a multi-row form submission."""
    fermentables, hops, yeasts, miscs = [], [], [], []

    i = 0
    while form.get(f"fermentable_id_{i}"):
        fermentables.append({
            "fermentable_id": int(form[f"fermentable_id_{i}"]),
            "amount_kg": float(form.get(f"amount_kg_{i}", 0)),
            "add_after_boil": form.get(f"add_after_boil_{i}") == "1",
        })
        i += 1

    i = 0
    while form.get(f"hop_id_{i}"):
        hops.append({
            "hop_id": int(form[f"hop_id_{i}"]),
            "amount_g": float(form.get(f"hop_amount_g_{i}", 0)),
            "time_min": int(form.get(f"time_min_{i}", 60)),
            "use": form.get(f"hop_use_{i}", "Boil"),
            "form": form.get(f"hop_form_{i}", "Pellet"),
        })
        i += 1

    i = 0
    while form.get(f"yeast_id_{i}"):
        yeasts.append({
            "yeast_id": int(form[f"yeast_id_{i}"]),
            "amount": float(form.get(f"yeast_amount_{i}", 1.0)),
        })
        i += 1

    i = 0
    while form.get(f"misc_id_{i}"):
        miscs.append({
            "misc_id": int(form[f"misc_id_{i}"]),
            "amount": float(form.get(f"misc_amount_{i}", 0)),
            "use": form.get(f"misc_use_{i}", "Boil"),
            "time_min": int(form.get(f"misc_time_{i}", 0)),
            "amount_is_weight": form.get(f"misc_is_weight_{i}", "1") == "1",
        })
        i += 1

    return fermentables, hops, yeasts, miscs


# ── Dashboard ─────────────────────────────────────────────────────────────────

def _get_setting(db: Session, key: str, default: str = "") -> str:
    s = db.get(AppSettings, key)
    return s.value if s and s.value else default


def _set_setting(db: Session, key: str, value: str):
    s = db.get(AppSettings, key)
    if s:
        s.value = value
    else:
        db.add(AppSettings(key=key, value=value))


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    from datetime import date as date_type

    # Active fermentations with last two gravity readings for trend
    active = db.query(BrewSession).options(
        selectinload(BrewSession.recipe),
        selectinload(BrewSession.fermentation_readings),
    ).filter(BrewSession.status.in_(["brewing", "fermenting", "conditioning"])).all()

    fermentation_cards = []
    for s in active:
        readings = sorted(s.fermentation_readings, key=lambda r: r.recorded_at)
        last = readings[-1] if readings else None
        prev = readings[-2] if len(readings) >= 2 else None
        trend = None
        if last and prev and last.gravity and prev.gravity:
            diff = last.gravity - prev.gravity
            trend = "stable" if abs(diff) < 0.001 else ("dropping" if diff < 0 else "rising")
        fermentation_cards.append({
            "session": s,
            "last_reading": last,
            "trend": trend,
        })

    # Barrel aging — active records with targets
    from app.models.barrel import BarrelAgingRecord as _BAR
    barrel_cards = []
    barrel_records = db.query(_BAR).options(
        selectinload(_BAR.barrel), selectinload(_BAR.session).selectinload(BrewSession.recipe)
    ).filter(_BAR.end_date.is_(None)).all()
    now_dt = datetime.utcnow()
    for rec in barrel_records:
        days_in = (now_dt - rec.start_date).days
        target_days = rec.target_days
        if not target_days and rec.target_55gal_months and rec.barrel and rec.barrel.aging_multiplier:
            target_days = round(rec.target_55gal_months * 30 / rec.barrel.aging_multiplier)
        barrel_cards.append({
            "record": rec,
            "days_in": days_in,
            "target_days": target_days,
            "days_left": max(0, target_days - days_in) if target_days else None,
            "pct": min(100, days_in / target_days * 100) if target_days else None,
        })

    # Upcoming events (next 14 days)
    today = now_dt.date()
    horizon = today + timedelta(days=14)
    upcoming_sessions = db.query(BrewSession).options(selectinload(BrewSession.recipe)).filter(
        BrewSession.brew_date >= datetime.combine(today, datetime.min.time()),
        BrewSession.brew_date <= datetime.combine(horizon, datetime.max.time()),
        BrewSession.status == "planned",
    ).order_by(BrewSession.brew_date).all()

    # Low-stock alerts (thresholds: grain <1 kg, hops <50g, yeast <1 pkg, misc <50g)
    low_fermentables = db.query(Fermentable).filter(
        Fermentable.stock_qty.isnot(None), Fermentable.stock_qty < 1.0, Fermentable.stock_qty >= 0
    ).order_by(Fermentable.stock_qty).limit(5).all()
    low_hops = db.query(Hop).filter(
        Hop.stock_qty.isnot(None), Hop.stock_qty < 50.0, Hop.stock_qty >= 0
    ).order_by(Hop.stock_qty).limit(5).all()
    low_yeasts = db.query(Yeast).filter(
        Yeast.stock_qty.isnot(None), Yeast.stock_qty < 1.0, Yeast.stock_qty >= 0
    ).order_by(Yeast.stock_qty).limit(5).all()
    low_miscs = db.query(Misc).filter(
        Misc.stock_qty.isnot(None), Misc.stock_qty < 50.0, Misc.stock_qty >= 0
    ).order_by(Misc.stock_qty).limit(5).all()

    return templates.TemplateResponse(request, "dashboard.html", {
        "devices": db.query(Device).order_by(Device.role).all(),
        "recent_recipes": db.query(Recipe).order_by(Recipe.created_at.desc()).limit(6).all(),
        "active_sessions": active,
        "fermentation_cards": fermentation_cards,
        "barrel_cards": barrel_cards,
        "upcoming_sessions": upcoming_sessions,
        "low_stock": {
            "fermentables": low_fermentables,
            "hops": low_hops,
            "yeasts": low_yeasts,
            "miscs": low_miscs,
        },
        "page": "dashboard",
    })


# ── Recipes ───────────────────────────────────────────────────────────────────

@router.get("/recipes", response_class=HTMLResponse)
def recipes_list(request: Request, q: str = "", db: Session = Depends(get_db)):
    query = db.query(Recipe)
    if q:
        query = query.filter(Recipe.name.ilike(f"%{q}%"))
    return templates.TemplateResponse(request, "recipes/list.html", {
        "recipes": query.order_by(Recipe.created_at.desc()).all(),
        "q": q,
        "page": "recipes",
    })


@router.get("/recipes/new", response_class=HTMLResponse)
def recipe_new(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "recipes/form.html", {
        "recipe": None, "page": "recipes", **_form_context(db),
    })


@router.get("/recipes/{recipe_id}/edit", response_class=HTMLResponse)
def recipe_edit(recipe_id: int, request: Request, db: Session = Depends(get_db)):
    recipe = db.get(Recipe, recipe_id)
    if not recipe:
        return RedirectResponse("/recipes", status_code=303)
    return templates.TemplateResponse(request, "recipes/form.html", {
        "recipe": recipe, "page": "recipes", **_form_context(db),
    })


@router.get("/recipes/{recipe_id}", response_class=HTMLResponse)
def recipe_detail(recipe_id: int, request: Request, db: Session = Depends(get_db)):
    recipe = db.get(Recipe, recipe_id)
    if not recipe:
        return RedirectResponse("/recipes", status_code=303)
    return templates.TemplateResponse(request, "recipes/detail.html", {
        "recipe": recipe,
        "page": "recipes",
    })


def _parse_grapes(form):
    grapes = []
    i = 0
    while form.get(f"grape_id_{i}"):
        grapes.append({
            "grape_id": int(form[f"grape_id_{i}"]),
            "amount_kg": float(form.get(f"grape_amount_kg_{i}", 0)),
            "percentage": float(form[f"grape_pct_{i}"]) if form.get(f"grape_pct_{i}") else None,
        })
        i += 1
    return grapes


def _parse_mash_steps(form):
    steps = []
    i = 0
    while form.get(f"mash_name_{i}") is not None or form.get(f"mash_temp_c_{i}"):
        temp_raw = form.get(f"mash_temp_c_{i}", "")
        time_raw = form.get(f"mash_time_min_{i}", "")
        if not temp_raw or not time_raw:
            i += 1
            continue
        steps.append({
            "step_number": i + 1,
            "name": form.get(f"mash_name_{i}") or None,
            "temp_c": float(temp_raw),
            "time_min": int(time_raw),
            "additions": form.get(f"mash_additions_{i}") or None,
            "notes": form.get(f"mash_notes_{i}") or None,
        })
        i += 1
    return steps


def _apply_craft_fields(recipe, form):
    recipe.craft = form.get("craft", "beer")
    recipe.wine_style = form.get("wine_style") or None
    recipe.skin_contact_days = int(form["skin_contact_days"]) if form.get("skin_contact_days") else None
    recipe.target_ta = float(form["target_ta"]) if form.get("target_ta") else None
    recipe.target_ph = float(form["target_ph"]) if form.get("target_ph") else None
    recipe.spirits_style = form.get("spirits_style") or None
    recipe.mead_style    = form.get("mead_style") or None
    recipe.cider_style   = form.get("cider_style") or None
    recipe.seltzer_style = form.get("seltzer_style") or None


@router.post("/recipes", response_class=HTMLResponse)
async def recipe_create(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    fermentables, hops, yeasts, miscs = _parse_ingredients(form)
    grapes = _parse_grapes(form)
    mash_steps = _parse_mash_steps(form)
    recipe = Recipe(
        name=form["name"],
        type=form.get("type", "All Grain"),
        style_id=int(form["style_id"]) if form.get("style_id") else None,
        equipment_id=int(form["equipment_id"]) if form.get("equipment_id") else None,
        batch_size_l=float(form["batch_size_l"]),
        boil_size_l=float(form["boil_size_l"]) if form.get("boil_size_l") else None,
        boil_time_min=int(form.get("boil_time_min", 60)),
        efficiency=float(form.get("efficiency", 75.0)),
        notes=form.get("notes") or None,
        brewer=form.get("brewer") or None,
    )
    _apply_craft_fields(recipe, form)
    db.add(recipe)
    db.flush()
    for f in fermentables:
        db.add(RecipeFermentable(recipe_id=recipe.id, **f))
    for h in hops:
        db.add(RecipeHop(recipe_id=recipe.id, **h))
    for y in yeasts:
        db.add(RecipeYeast(recipe_id=recipe.id, **y))
    for m in miscs:
        db.add(RecipeMisc(recipe_id=recipe.id, **m))
    for g in grapes:
        db.add(RecipeGrape(recipe_id=recipe.id, **g))
    for s in mash_steps:
        db.add(MashStep(recipe_id=recipe.id, **s))
    db.flush()
    db.refresh(recipe)
    calc_service.calculate(recipe)
    db.commit()
    return RedirectResponse(f"/recipes/{recipe.id}", status_code=303)


@router.post("/recipes/{recipe_id}/update", response_class=HTMLResponse)
async def recipe_update(recipe_id: int, request: Request, db: Session = Depends(get_db)):
    recipe = db.get(Recipe, recipe_id)
    if not recipe:
        return RedirectResponse("/recipes", status_code=303)
    form = await request.form()
    recipe.name = form["name"]
    recipe.type = form.get("type", "All Grain")
    recipe.style_id = int(form["style_id"]) if form.get("style_id") else None
    recipe.equipment_id = int(form["equipment_id"]) if form.get("equipment_id") else None
    recipe.batch_size_l = float(form["batch_size_l"])
    recipe.boil_size_l = float(form["boil_size_l"]) if form.get("boil_size_l") else None
    recipe.boil_time_min = int(form.get("boil_time_min", 60))
    recipe.efficiency = float(form.get("efficiency", 75.0))
    recipe.notes = form.get("notes") or None
    recipe.brewer = form.get("brewer") or None

    fermentables, hops, yeasts, miscs = _parse_ingredients(form)
    grapes = _parse_grapes(form)
    mash_steps = _parse_mash_steps(form)
    _apply_craft_fields(recipe, form)
    for obj in (recipe.fermentables[:] + recipe.hops[:] + recipe.yeasts[:] +
                recipe.miscs[:] + recipe.grapes[:] + recipe.mash_steps[:]):
        db.delete(obj)
    db.flush()
    for f in fermentables:
        db.add(RecipeFermentable(recipe_id=recipe.id, **f))
    for h in hops:
        db.add(RecipeHop(recipe_id=recipe.id, **h))
    for y in yeasts:
        db.add(RecipeYeast(recipe_id=recipe.id, **y))
    for m in miscs:
        db.add(RecipeMisc(recipe_id=recipe.id, **m))
    for g in grapes:
        db.add(RecipeGrape(recipe_id=recipe.id, **g))
    for s in mash_steps:
        db.add(MashStep(recipe_id=recipe.id, **s))
    db.flush()
    db.refresh(recipe)
    calc_service.calculate(recipe)
    db.commit()
    return RedirectResponse(f"/recipes/{recipe.id}", status_code=303)


@router.post("/recipes/{recipe_id}/delete")
def recipe_delete(recipe_id: int, db: Session = Depends(get_db)):
    recipe = db.get(Recipe, recipe_id)
    if recipe:
        db.delete(recipe)
        db.commit()
    return RedirectResponse("/recipes", status_code=303)


@router.post("/recipes/{recipe_id}/clone")
def recipe_clone(recipe_id: int, db: Session = Depends(get_db)):
    recipe = db.get(Recipe, recipe_id)
    if not recipe:
        return RedirectResponse("/recipes", status_code=303)

    cloned = Recipe(
        name=f"{recipe.name} (Copy)",
        type=recipe.type,
        style_id=recipe.style_id,
        equipment_id=recipe.equipment_id,
        batch_size_l=recipe.batch_size_l,
        boil_size_l=recipe.boil_size_l,
        boil_time_min=recipe.boil_time_min,
        efficiency=recipe.efficiency,
        notes=recipe.notes,
        brewer=recipe.brewer,
        craft=recipe.craft,
        wine_style=recipe.wine_style,
        skin_contact_days=recipe.skin_contact_days,
        target_ta=recipe.target_ta,
        target_ph=recipe.target_ph,
        spirits_style=recipe.spirits_style,
        mead_style=recipe.mead_style,
        cider_style=recipe.cider_style,
        seltzer_style=recipe.seltzer_style,
    )
    db.add(cloned)
    db.flush()

    for rf in recipe.fermentables:
        db.add(RecipeFermentable(
            recipe_id=cloned.id,
            fermentable_id=rf.fermentable_id,
            amount_kg=rf.amount_kg,
            add_after_boil=rf.add_after_boil,
        ))
    for rh in recipe.hops:
        db.add(RecipeHop(
            recipe_id=cloned.id,
            hop_id=rh.hop_id,
            amount_g=rh.amount_g,
            time_min=rh.time_min,
            use=rh.use,
            form=rh.form,
        ))
    for ry in recipe.yeasts:
        db.add(RecipeYeast(
            recipe_id=cloned.id,
            yeast_id=ry.yeast_id,
            amount=ry.amount,
            add_to_secondary=ry.add_to_secondary,
        ))
    for rm in recipe.miscs:
        db.add(RecipeMisc(
            recipe_id=cloned.id,
            misc_id=rm.misc_id,
            amount=rm.amount,
            amount_is_weight=rm.amount_is_weight,
            time_min=rm.time_min,
            use=rm.use,
        ))
    for rg in recipe.grapes:
        db.add(RecipeGrape(
            recipe_id=cloned.id,
            grape_id=rg.grape_id,
            amount_kg=rg.amount_kg,
            percentage=rg.percentage,
        ))
    for ms in recipe.mash_steps:
        db.add(MashStep(
            recipe_id=cloned.id,
            step_number=ms.step_number,
            name=ms.name,
            temp_c=ms.temp_c,
            time_min=ms.time_min,
        ))

    db.flush()
    db.refresh(cloned)
    calc_service.calculate(cloned)
    db.commit()
    return RedirectResponse(f"/recipes/{cloned.id}/edit", status_code=303)


_NO_EFF_TYPES = {"Sugar", "Extract", "Dry Extract"}

@router.get("/recipes/{recipe_id}/scale", response_class=HTMLResponse)
def recipe_scale_form(recipe_id: int, request: Request, db: Session = Depends(get_db)):
    recipe = db.get(Recipe, recipe_id)
    if not recipe:
        return RedirectResponse("/recipes", status_code=303)
    return templates.TemplateResponse(request, "recipes/scale.html", {
        "recipe": recipe,
        "page": "recipes",
    })


@router.post("/recipes/{recipe_id}/scale")
async def recipe_scale_submit(recipe_id: int, request: Request, db: Session = Depends(get_db)):
    recipe = db.get(Recipe, recipe_id)
    if not recipe:
        return RedirectResponse("/recipes", status_code=303)

    form = await request.form()
    new_batch_l = float(form["new_batch_l"])
    new_efficiency = float(form.get("new_efficiency") or recipe.efficiency)
    new_name = form.get("new_name") or f"{recipe.name} (scaled)"

    batch_ratio = new_batch_l / recipe.batch_size_l
    old_eff = recipe.efficiency / 100.0
    new_eff = new_efficiency / 100.0

    scaled = Recipe(
        name=new_name,
        type=recipe.type,
        style_id=recipe.style_id,
        equipment_id=recipe.equipment_id,
        batch_size_l=new_batch_l,
        boil_size_l=round(recipe.boil_size_l * batch_ratio, 2) if recipe.boil_size_l else None,
        boil_time_min=recipe.boil_time_min,
        efficiency=new_efficiency,
        notes=recipe.notes,
        brewer=recipe.brewer,
    )
    db.add(scaled)
    db.flush()

    for rf in recipe.fermentables:
        ferm = db.get(Fermentable, rf.fermentable_id)
        if ferm and ferm.type in _NO_EFF_TYPES:
            new_kg = rf.amount_kg * batch_ratio
        else:
            new_kg = rf.amount_kg * batch_ratio * (old_eff / new_eff) if new_eff else rf.amount_kg * batch_ratio
        db.add(RecipeFermentable(
            recipe_id=scaled.id,
            fermentable_id=rf.fermentable_id,
            amount_kg=round(new_kg, 4),
            add_after_boil=rf.add_after_boil,
        ))

    for rh in recipe.hops:
        db.add(RecipeHop(
            recipe_id=scaled.id,
            hop_id=rh.hop_id,
            amount_g=round(rh.amount_g * batch_ratio, 2),
            time_min=rh.time_min,
            use=rh.use,
            form=rh.form,
        ))

    for ry in recipe.yeasts:
        db.add(RecipeYeast(
            recipe_id=scaled.id,
            yeast_id=ry.yeast_id,
            amount=round(ry.amount * batch_ratio, 2),
        ))

    for rm in recipe.miscs:
        db.add(RecipeMisc(
            recipe_id=scaled.id,
            misc_id=rm.misc_id,
            amount=round(rm.amount * batch_ratio, 2),
            use=rm.use,
            time_min=rm.time_min,
        ))

    db.flush()
    db.refresh(scaled)
    calc_service.calculate(scaled)
    db.commit()
    return RedirectResponse(f"/recipes/{scaled.id}", status_code=303)


# ── Equipment ─────────────────────────────────────────────────────────────────

@router.get("/equipment", response_class=HTMLResponse)
def equipment_list(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "equipment/list.html", {
        "equipment_list": db.query(Equipment).order_by(Equipment.name).all(),
        "page": "equipment",
    })


@router.post("/equipment", response_class=HTMLResponse)
async def equipment_create(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    db.add(Equipment(
        name=form["name"],
        craft=form.get("craft", "beer"),
        still_type=form.get("still_type") or None,
        batch_size_l=float(form["batch_size_l"]),
        boil_size_l=float(form.get("boil_size_l") or 0),
        boil_time_min=int(form.get("boil_time_min", 60)),
        efficiency=float(form.get("efficiency", 75.0)),
        trub_chiller_loss_l=float(form.get("trub_chiller_loss_l", 1.0)),
        notes=form.get("notes") or None,
    ))
    db.commit()
    return RedirectResponse("/equipment", status_code=303)


@router.post("/equipment/{equip_id}/delete")
def equipment_delete(equip_id: int, db: Session = Depends(get_db)):
    item = db.get(Equipment, equip_id)
    if item:
        # NULL out FK references so the delete doesn't violate constraints
        db.query(Recipe).filter(Recipe.equipment_id == equip_id).update({"equipment_id": None})
        db.query(BrewSession).filter(BrewSession.equipment_id == equip_id).update({"equipment_id": None})
        db.delete(item)
        db.commit()
    return RedirectResponse("/equipment", status_code=303)


# ── Ingredients library ───────────────────────────────────────────────────────

@router.get("/ingredients", response_class=HTMLResponse)
def ingredients_list(request: Request, tab: str = "fermentables", db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "ingredients/list.html", {
        "fermentables": db.query(Fermentable).order_by(Fermentable.name).all(),
        "hops": db.query(Hop).order_by(Hop.name).all(),
        "yeasts": db.query(Yeast).order_by(Yeast.name).all(),
        "miscs": db.query(Misc).order_by(Misc.name).all(),
        "grapes": db.query(GrapeVariety).order_by(GrapeVariety.name).all(),
        "tab": tab,
        "page": "ingredients",
        "error": request.query_params.get("error"),
    })


def _in_use_error(name: str, tab: str) -> RedirectResponse:
    msg = f"{name} is used in one or more recipes and cannot be deleted."
    return RedirectResponse(f"/ingredients?tab={tab}&error={msg}", status_code=303)


@router.post("/ingredients/ensure")
async def ensure_ingredient(request: Request, db: Session = Depends(get_db)):
    """Find ingredient by name (case-insensitive partial match) or create it. Returns {id}."""
    body = await request.json()
    category = body.get("category", "")
    name = (body.get("name") or "").strip()
    if not category or not name:
        return JSONResponse({"error": "category and name required"}, status_code=400)

    def _find(model, name_col):
        exact = db.query(model).filter(func.lower(name_col) == name.lower()).first()
        if exact:
            return exact
        return db.query(model).filter(func.lower(name_col).contains(name.lower())).first()

    if category == "fermentable":
        obj = _find(Fermentable, Fermentable.name)
        if not obj:
            obj = Fermentable(
                name=name,
                type=body.get("fermentable_type", "Grain"),
                color_srm=float(body["color_srm"]) if body.get("color_srm") else 2.0,
                potential=float(body["potential"]) if body.get("potential") else 1.037,
                yield_pct=float(body["yield_pct"]) if body.get("yield_pct") else 75.0,
            )
            db.add(obj); db.commit(); db.refresh(obj)
    elif category == "hop":
        obj = _find(Hop, Hop.name)
        if not obj:
            obj = Hop(
                name=name,
                alpha_pct=float(body["alpha_pct"]) if body.get("alpha_pct") else 10.0,
                type=body.get("hop_type"),
            )
            db.add(obj); db.commit(); db.refresh(obj)
    elif category == "yeast":
        obj = _find(Yeast, Yeast.name)
        if not obj:
            obj = Yeast(
                name=name,
                lab=body.get("lab"),
                type=body.get("yeast_type"),
                form=body.get("form", "Dry"),
                attenuation_pct=float(body["attenuation_pct"]) if body.get("attenuation_pct") else 75.0,
            )
            db.add(obj); db.commit(); db.refresh(obj)
    else:
        return JSONResponse({"error": f"unknown category: {category}"}, status_code=400)

    return JSONResponse({"id": obj.id})


# Fermentables
@router.post("/ingredients/fermentables/create")
async def fermentable_create(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    db.add(Fermentable(
        name=form["name"], type=form.get("type", "Grain"),
        origin=form.get("origin") or None,
        color_srm=float(form.get("color_srm") or 0),
        potential=float(form.get("potential") or 1.037),
        yield_pct=float(form.get("yield_pct") or 75),
        recommend_mash=form.get("recommend_mash") == "1",
        notes=form.get("notes") or None,
        cost_per_kg=float(form["cost_per_kg"]) if form.get("cost_per_kg") else None,
    ))
    db.commit()
    return RedirectResponse("/ingredients?tab=fermentables", status_code=303)


@router.post("/ingredients/fermentables/{item_id}/update")
async def fermentable_update(item_id: int, request: Request, db: Session = Depends(get_db)):
    item = db.get(Fermentable, item_id)
    if not item:
        return RedirectResponse("/ingredients?tab=fermentables", status_code=303)
    form = await request.form()
    item.name = form["name"]; item.type = form.get("type", "Grain")
    item.origin = form.get("origin") or None
    item.color_srm = float(form.get("color_srm") or 0)
    item.potential = float(form.get("potential") or 1.037)
    item.yield_pct = float(form.get("yield_pct") or 75)
    item.recommend_mash = form.get("recommend_mash") == "1"
    item.notes = form.get("notes") or None
    item.cost_per_kg = float(form["cost_per_kg"]) if form.get("cost_per_kg") else None
    db.commit()
    return RedirectResponse("/ingredients?tab=fermentables", status_code=303)


@router.post("/ingredients/fermentables/{item_id}/delete")
def fermentable_delete(item_id: int, db: Session = Depends(get_db)):
    item = db.get(Fermentable, item_id)
    if not item:
        return RedirectResponse("/ingredients?tab=fermentables", status_code=303)
    if db.query(RecipeFermentable).filter_by(fermentable_id=item_id).count():
        return _in_use_error(item.name, "fermentables")
    db.delete(item); db.commit()
    return RedirectResponse("/ingredients?tab=fermentables", status_code=303)


# Hops
@router.post("/ingredients/hops/create")
async def hop_create(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    db.add(Hop(
        name=form["name"], origin=form.get("origin") or None,
        type=form.get("type") or None,
        alpha_pct=float(form.get("alpha_pct") or 0),
        beta_pct=float(form.get("beta_pct")) if form.get("beta_pct") else None,
        notes=form.get("notes") or None,
        substitutes=form.get("substitutes") or None,
        cost_per_kg=float(form["cost_per_kg"]) if form.get("cost_per_kg") else None,
    ))
    db.commit()
    return RedirectResponse("/ingredients?tab=hops", status_code=303)


@router.post("/ingredients/hops/{item_id}/update")
async def hop_update(item_id: int, request: Request, db: Session = Depends(get_db)):
    item = db.get(Hop, item_id)
    if not item:
        return RedirectResponse("/ingredients?tab=hops", status_code=303)
    form = await request.form()
    item.name = form["name"]; item.origin = form.get("origin") or None
    item.type = form.get("type") or None
    item.alpha_pct = float(form.get("alpha_pct") or 0)
    item.beta_pct = float(form.get("beta_pct")) if form.get("beta_pct") else None
    item.notes = form.get("notes") or None
    item.substitutes = form.get("substitutes") or None
    item.cost_per_kg = float(form["cost_per_kg"]) if form.get("cost_per_kg") else None
    db.commit()
    return RedirectResponse("/ingredients?tab=hops", status_code=303)


@router.post("/ingredients/hops/{item_id}/delete")
def hop_delete(item_id: int, db: Session = Depends(get_db)):
    item = db.get(Hop, item_id)
    if not item:
        return RedirectResponse("/ingredients?tab=hops", status_code=303)
    if db.query(RecipeHop).filter_by(hop_id=item_id).count():
        return _in_use_error(item.name, "hops")
    db.delete(item); db.commit()
    return RedirectResponse("/ingredients?tab=hops", status_code=303)


# Yeasts
@router.post("/ingredients/yeasts/create")
async def yeast_create(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    db.add(Yeast(
        name=form["name"], lab=form.get("lab") or None,
        product_id=form.get("product_id") or None,
        type=form.get("type") or None, form=form.get("form") or None,
        attenuation_pct=float(form.get("attenuation_pct") or 75),
        min_temp_c=float(form.get("min_temp_c")) if form.get("min_temp_c") else None,
        max_temp_c=float(form.get("max_temp_c")) if form.get("max_temp_c") else None,
        flocculation=form.get("flocculation") or None,
        best_for=form.get("best_for") or None,
        notes=form.get("notes") or None,
        cost_per_pkg=float(form["cost_per_pkg"]) if form.get("cost_per_pkg") else None,
    ))
    db.commit()
    return RedirectResponse("/ingredients?tab=yeasts", status_code=303)


@router.post("/ingredients/yeasts/{item_id}/update")
async def yeast_update(item_id: int, request: Request, db: Session = Depends(get_db)):
    item = db.get(Yeast, item_id)
    if not item:
        return RedirectResponse("/ingredients?tab=yeasts", status_code=303)
    form = await request.form()
    item.name = form["name"]; item.lab = form.get("lab") or None
    item.product_id = form.get("product_id") or None
    item.type = form.get("type") or None; item.form = form.get("form") or None
    item.attenuation_pct = float(form.get("attenuation_pct") or 75)
    item.min_temp_c = float(form.get("min_temp_c")) if form.get("min_temp_c") else None
    item.max_temp_c = float(form.get("max_temp_c")) if form.get("max_temp_c") else None
    item.flocculation = form.get("flocculation") or None
    item.best_for = form.get("best_for") or None
    item.notes = form.get("notes") or None
    item.cost_per_pkg = float(form["cost_per_pkg"]) if form.get("cost_per_pkg") else None
    db.commit()
    return RedirectResponse("/ingredients?tab=yeasts", status_code=303)


@router.post("/ingredients/yeasts/{item_id}/delete")
def yeast_delete(item_id: int, db: Session = Depends(get_db)):
    item = db.get(Yeast, item_id)
    if not item:
        return RedirectResponse("/ingredients?tab=yeasts", status_code=303)
    if db.query(RecipeYeast).filter_by(yeast_id=item_id).count():
        return _in_use_error(item.name, "yeasts")
    db.delete(item); db.commit()
    return RedirectResponse("/ingredients?tab=yeasts", status_code=303)


# Miscs
@router.post("/ingredients/miscs/create")
async def misc_create(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    db.add(Misc(
        name=form["name"], type=form.get("type") or None,
        use_for=form.get("use_for") or None,
        notes=form.get("notes") or None,
        cost_per_unit=float(form["cost_per_unit"]) if form.get("cost_per_unit") else None,
    ))
    db.commit()
    return RedirectResponse("/ingredients?tab=miscs", status_code=303)


@router.post("/ingredients/miscs/{item_id}/update")
async def misc_update(item_id: int, request: Request, db: Session = Depends(get_db)):
    item = db.get(Misc, item_id)
    if not item:
        return RedirectResponse("/ingredients?tab=miscs", status_code=303)
    form = await request.form()
    item.name = form["name"]; item.type = form.get("type") or None
    item.use_for = form.get("use_for") or None
    item.notes = form.get("notes") or None
    item.cost_per_unit = float(form["cost_per_unit"]) if form.get("cost_per_unit") else None
    db.commit()
    return RedirectResponse("/ingredients?tab=miscs", status_code=303)


@router.post("/ingredients/miscs/{item_id}/delete")
def misc_delete(item_id: int, db: Session = Depends(get_db)):
    item = db.get(Misc, item_id)
    if not item:
        return RedirectResponse("/ingredients?tab=miscs", status_code=303)
    if db.query(RecipeMisc).filter_by(misc_id=item_id).count():
        return _in_use_error(item.name, "miscs")
    db.delete(item); db.commit()
    return RedirectResponse("/ingredients?tab=miscs", status_code=303)


# ── Devices / Controller ──────────────────────────────────────────────────────

@router.get("/devices", response_class=HTMLResponse)
def devices_page(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "devices/list.html", {
        "devices": db.query(Device).order_by(Device.role).all(),
        "rigs": db.query(RigProfile).all(),
        "page": "devices",
    })


@router.post("/devices", response_class=HTMLResponse)
async def device_create(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    db.add(Device(
        name=form["name"],
        device_key=form["device_key"],
        type=form["type"],
        role=form.get("role") or None,
        protocol=form.get("protocol", "mqtt"),
        rig_id=int(form["rig_id"]) if form.get("rig_id") else None,
    ))
    db.commit()
    return RedirectResponse("/devices", status_code=303)


@router.post("/devices/{device_id}/delete")
def device_delete(device_id: int, db: Session = Depends(get_db)):
    device = db.get(Device, device_id)
    if device:
        db.delete(device)
        db.commit()
    return RedirectResponse("/devices", status_code=303)


@router.post("/rigs")
async def rig_create(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    db.add(RigProfile(
        name=form["name"],
        type=form.get("type", "custom"),
        description=form.get("description") or None,
    ))
    db.commit()
    return RedirectResponse("/devices", status_code=303)


# ── Brew sessions ─────────────────────────────────────────────────────────────

@router.get("/brew-sessions", response_class=HTMLResponse)
def brew_sessions_list(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "brew_sessions/list.html", {
        "sessions": db.query(BrewSession).order_by(BrewSession.created_at.desc()).all(),
        "recipes": db.query(Recipe).order_by(Recipe.name).all(),
        "page": "brew_sessions",
    })


@router.get("/brew-sessions/new", response_class=HTMLResponse)
def brew_session_new(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "brew_sessions/form.html", {
        "recipes": db.query(Recipe).order_by(Recipe.name).all(),
        "page": "brew_sessions",
    })


def _deduct_inventory(recipe_id: int, db: Session):
    """Subtract recipe ingredient amounts from library stock quantities (clamp at 0)."""
    for rf in db.query(RecipeFermentable).filter(RecipeFermentable.recipe_id == recipe_id).all():
        if rf.fermentable and rf.fermentable.stock_qty is not None:
            rf.fermentable.stock_qty = max(0.0, (rf.fermentable.stock_qty or 0.0) - (rf.amount_kg or 0.0))
    for rh in db.query(RecipeHop).filter(RecipeHop.recipe_id == recipe_id).all():
        if rh.hop and rh.hop.stock_qty is not None:
            rh.hop.stock_qty = max(0.0, (rh.hop.stock_qty or 0.0) - (rh.amount_g or 0.0))
    for ry in db.query(RecipeYeast).filter(RecipeYeast.recipe_id == recipe_id).all():
        if ry.yeast and ry.yeast.stock_qty is not None:
            ry.yeast.stock_qty = max(0.0, (ry.yeast.stock_qty or 0.0) - (ry.amount or 0.0))
    for rm in db.query(RecipeMisc).filter(RecipeMisc.recipe_id == recipe_id).all():
        if rm.misc and rm.misc.stock_qty is not None:
            rm.misc.stock_qty = max(0.0, (rm.misc.stock_qty or 0.0) - (rm.amount or 0.0))


@router.post("/brew-sessions/create", response_class=HTMLResponse)
async def brew_session_create(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    brew_date = None
    if form.get("brew_date"):
        brew_date = datetime.strptime(form["brew_date"], "%Y-%m-%d")
    recipe_id = int(form["recipe_id"])
    db.add(BrewSession(
        recipe_id=recipe_id,
        status="planned",
        brew_date=brew_date,
        notes=form.get("notes") or None,
    ))
    if form.get("deduct_inventory"):
        _deduct_inventory(recipe_id, db)
    db.commit()
    return RedirectResponse("/brew-sessions", status_code=303)


@router.post("/brew-sessions", response_class=HTMLResponse)
async def brew_session_create_modal(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    recipe_id = int(form["recipe_id"])
    db.add(BrewSession(
        recipe_id=recipe_id,
        status="planned",
        notes=form.get("notes") or None,
    ))
    if form.get("deduct_inventory"):
        _deduct_inventory(recipe_id, db)
    db.commit()
    return RedirectResponse("/brew-sessions", status_code=303)


def _load_session_with_program(session_id: int, db: Session):
    return db.query(BrewSession).options(
        selectinload(BrewSession.recipe).selectinload(Recipe.brew_programs).selectinload(BrewProgram.steps).selectinload(BrewStep.commands),
        selectinload(BrewSession.brew_session_steps).selectinload(BrewSessionStep.step).selectinload(BrewStep.commands),
        selectinload(BrewSession.brew_session_steps).selectinload(BrewSessionStep.step).selectinload(BrewStep.trigger_device),
    ).get(session_id)


@router.get("/brew-sessions/{session_id}/run", response_class=HTMLResponse)
def brew_session_run(session_id: int, request: Request, db: Session = Depends(get_db)):
    session = _load_session_with_program(session_id, db)
    if not session:
        return RedirectResponse("/brew-sessions", status_code=303)

    program = None
    if session.recipe and session.recipe.brew_programs:
        program = session.recipe.brew_programs[0]

    if program:
        existing_step_ids = {ss.step_id for ss in session.brew_session_steps}
        new_steps = [
            BrewSessionStep(session_id=session.id, step_id=step.id, status="pending")
            for step in program.steps
            if step.id not in existing_step_ids
        ]
        if new_steps:
            for ns in new_steps:
                db.add(ns)
            db.commit()
            session = _load_session_with_program(session_id, db)
            if session.recipe and session.recipe.brew_programs:
                program = session.recipe.brew_programs[0]

    session_steps = sorted(session.brew_session_steps, key=lambda ss: ss.step.step_number)

    return templates.TemplateResponse(request, "brew_sessions/runner.html", {
        "session": session,
        "program": program,
        "session_steps": session_steps,
        "page": "brew_sessions",
    })


@router.post("/brew-sessions/{session_id}/steps/{session_step_id}/activate")
def brew_session_step_activate(session_id: int, session_step_id: int, db: Session = Depends(get_db)):
    ss = db.get(BrewSessionStep, session_step_id)
    if ss and ss.session_id == session_id:
        ss.status = "active"
        ss.started_at = datetime.utcnow()
        db.commit()
    return RedirectResponse(f"/brew-sessions/{session_id}/run", status_code=303)


@router.post("/brew-sessions/{session_id}/steps/{session_step_id}/complete")
def brew_session_step_complete(session_id: int, session_step_id: int, db: Session = Depends(get_db)):
    ss = db.get(BrewSessionStep, session_step_id)
    if ss and ss.session_id == session_id:
        ss.status = "complete"
        ss.completed_at = datetime.utcnow()
        db.commit()
    return RedirectResponse(f"/brew-sessions/{session_id}/run", status_code=303)


@router.post("/brew-sessions/{session_id}/steps/{session_step_id}/skip")
def brew_session_step_skip(session_id: int, session_step_id: int, db: Session = Depends(get_db)):
    ss = db.get(BrewSessionStep, session_step_id)
    if ss and ss.session_id == session_id:
        ss.status = "skipped"
        ss.completed_at = datetime.utcnow()
        db.commit()
    return RedirectResponse(f"/brew-sessions/{session_id}/run", status_code=303)


@router.post("/brew-sessions/{session_id}/update")
async def brew_session_update(session_id: int, request: Request, db: Session = Depends(get_db)):
    session = db.get(BrewSession, session_id)
    if not session:
        return RedirectResponse("/brew-sessions", status_code=303)
    form = await request.form()
    session.status = form.get("status", session.status)
    session.notes = form.get("notes") or None
    if form.get("brew_date"):
        try:
            session.brew_date = datetime.strptime(form["brew_date"], "%Y-%m-%d")
        except ValueError:
            pass
    else:
        session.brew_date = None
    if form.get("package_date"):
        try:
            session.package_date = datetime.strptime(form["package_date"], "%Y-%m-%d")
        except ValueError:
            pass
    else:
        session.package_date = None
    session.actual_og = float(form["actual_og"]) if form.get("actual_og") else None
    session.actual_fg = float(form["actual_fg"]) if form.get("actual_fg") else None
    session.actual_abv = float(form["actual_abv"]) if form.get("actual_abv") else None
    session.actual_batch_size_l = float(form["actual_batch_size_l"]) if form.get("actual_batch_size_l") else None
    session.actual_efficiency = float(form["actual_efficiency"]) if form.get("actual_efficiency") else None
    session.ferment_temp_c = float(form["ferment_temp_c"]) if form.get("ferment_temp_c") else None
    # Wine harvest intake fields
    session.brix_intake = float(form["brix_intake"]) if form.get("brix_intake") else None
    session.ph_intake = float(form["ph_intake"]) if form.get("ph_intake") else None
    session.ta_intake_g_l = float(form["ta_intake_g_l"]) if form.get("ta_intake_g_l") else None
    session.fruit_weight_kg = float(form["fruit_weight_kg"]) if form.get("fruit_weight_kg") else None
    session.fruit_source = form.get("fruit_source") or None
    if form.get("crush_date"):
        try:
            session.crush_date = datetime.strptime(form["crush_date"], "%Y-%m-%d")
        except ValueError:
            pass
    else:
        session.crush_date = None
    db.commit()
    return RedirectResponse(f"/brew-sessions/{session_id}", status_code=303)


@router.post("/brew-sessions/{session_id}/delete")
def brew_session_delete(session_id: int, db: Session = Depends(get_db)):
    session = db.get(BrewSession, session_id)
    if session:
        db.delete(session)
        db.commit()
    return RedirectResponse("/brew-sessions", status_code=303)


# ── Brew programs ─────────────────────────────────────────────────────────────

@router.get("/brew-programs", response_class=HTMLResponse)
def brew_programs_list(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "brew_programs/list.html", {
        "programs": db.query(BrewProgram).order_by(BrewProgram.name).all(),
        "page": "brew_programs",
    })


@router.get("/brew-programs/new", response_class=HTMLResponse)
def brew_program_new(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "brew_programs/form.html", {
        "program": None,
        "recipes": db.query(Recipe).order_by(Recipe.name).all(),
        "devices": db.query(Device).order_by(Device.name).all(),
        "page": "brew_programs",
    })


@router.post("/brew-programs/create")
async def brew_program_create(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    db.add(BrewProgram(
        name=form["name"],
        description=form.get("description") or None,
        recipe_id=int(form["recipe_id"]) if form.get("recipe_id") else None,
    ))
    db.commit()
    return RedirectResponse("/brew-programs", status_code=303)


@router.get("/brew-programs/{program_id}", response_class=HTMLResponse)
def brew_program_edit(program_id: int, request: Request, db: Session = Depends(get_db)):
    program = db.query(BrewProgram).options(
        selectinload(BrewProgram.steps).selectinload(BrewStep.commands),
        selectinload(BrewProgram.steps).selectinload(BrewStep.trigger_device),
    ).get(program_id)
    if not program:
        return RedirectResponse("/brew-programs", status_code=303)
    return templates.TemplateResponse(request, "brew_programs/form.html", {
        "program": program,
        "recipes": db.query(Recipe).order_by(Recipe.name).all(),
        "devices": db.query(Device).order_by(Device.name).all(),
        "page": "brew_programs",
    })


@router.post("/brew-programs/{program_id}/update")
async def brew_program_update(program_id: int, request: Request, db: Session = Depends(get_db)):
    program = db.get(BrewProgram, program_id)
    if not program:
        return RedirectResponse("/brew-programs", status_code=303)
    form = await request.form()
    program.name = form["name"]
    program.description = form.get("description") or None
    program.recipe_id = int(form["recipe_id"]) if form.get("recipe_id") else None
    db.commit()
    return RedirectResponse(f"/brew-programs/{program_id}", status_code=303)


@router.post("/brew-programs/{program_id}/delete")
def brew_program_delete(program_id: int, db: Session = Depends(get_db)):
    program = db.get(BrewProgram, program_id)
    if program:
        db.delete(program)
        db.commit()
    return RedirectResponse("/brew-programs", status_code=303)


@router.post("/brew-programs/{program_id}/steps/add")
async def brew_program_step_add(program_id: int, request: Request, db: Session = Depends(get_db)):
    program = db.get(BrewProgram, program_id)
    if not program:
        return RedirectResponse("/brew-programs", status_code=303)
    form = await request.form()
    max_step = db.query(func.max(BrewStep.step_number)).filter(
        BrewStep.program_id == program_id
    ).scalar() or 0
    db.add(BrewStep(
        program_id=program_id,
        step_number=max_step + 1,
        name=form["name"],
        description=form.get("description") or None,
        trigger_type=form.get("trigger_type", "manual"),
        trigger_value=float(form["trigger_value"]) if form.get("trigger_value") else None,
        trigger_device_id=int(form["trigger_device_id"]) if form.get("trigger_device_id") else None,
    ))
    db.commit()
    return RedirectResponse(f"/brew-programs/{program_id}", status_code=303)


@router.post("/brew-programs/{program_id}/steps/{step_id}/delete")
def brew_program_step_delete(program_id: int, step_id: int, db: Session = Depends(get_db)):
    step = db.get(BrewStep, step_id)
    if step and step.program_id == program_id:
        db.delete(step)
        db.commit()
    return RedirectResponse(f"/brew-programs/{program_id}", status_code=303)


# ── Settings / backup ────────────────────────────────────────────────────────

@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, saved: str = "", db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "settings.html", {
        "page": "settings",
        "saved": saved,
        "ai_provider": _get_setting(db, "ai_provider", "openai_compatible"),
        "ai_model": _get_setting(db, "ai_model", ""),
        "ai_api_key": _get_setting(db, "ai_api_key", ""),
        "ai_base_url": _get_setting(db, "ai_base_url", "http://localhost:11434/v1"),
    })


@router.get("/settings/export/json")
def settings_export_json(db: Session = Depends(get_db)):
    data = backup_service.export_all(db)
    return Response(
        content=json.dumps(data, indent=2, default=str),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="brewbot-backup.json"'},
    )


@router.post("/settings/import/json", response_class=HTMLResponse)
async def settings_import_json(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    data = json.loads(content)
    summary = backup_service.import_all(db, data)
    return templates.TemplateResponse(request, "settings.html", {
        "page": "settings",
        "imported": True,
        "import_summary": summary,
    })


@router.get("/settings/export/beerxml")
def settings_export_beerxml(recipe_id: int = None, db: Session = Depends(get_db)):
    if recipe_id is not None:
        recipe = db.get(Recipe, recipe_id)
        recipes = [recipe] if recipe else []
    else:
        recipes = db.query(Recipe).all()
    xml_str = beerxml_service.export_recipes(recipes)
    return Response(
        content=xml_str,
        media_type="application/xml",
        headers={"Content-Disposition": 'attachment; filename="brewbot-recipes.xml"'},
    )


@router.post("/settings/import/beerxml", response_class=HTMLResponse)
async def settings_import_beerxml(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    created = beerxml_service.import_recipes(content.decode("utf-8", errors="replace"), db)
    return templates.TemplateResponse(request, "settings.html", {
        "page": "settings",
        "beerxml_imported": True,
        "beerxml_count": len(created),
    })


@router.get("/settings/security", response_class=HTMLResponse)
def security_settings(request: Request, db: Session = Depends(get_db),
                       current_user: User = Depends(require_auth)):
    secret = auth_service.generate_totp_secret()
    totp_uri = auth_service.get_totp_uri(secret, current_user.username)
    return templates.TemplateResponse(request, "settings_security.html", {
        "page": "settings",
        "current_user": current_user,
        "totp_secret": secret,
        "totp_uri": totp_uri,
    })

@router.post("/settings/security/enable-2fa")
async def enable_2fa(request: Request, db: Session = Depends(get_db),
                     current_user: User = Depends(require_auth)):
    form = await request.form()
    secret = form.get("totp_secret", "")
    code = form.get("code", "").replace(" ", "")
    if not auth_service.verify_totp(secret, code):
        totp_uri = auth_service.get_totp_uri(secret, current_user.username)
        return templates.TemplateResponse(request, "settings_security.html", {
            "page": "settings",
            "current_user": current_user,
            "totp_secret": secret,
            "totp_uri": totp_uri,
            "error": "Invalid code — scan the QR code again and try once more.",
        })
    current_user.totp_secret = secret
    current_user.totp_enabled = True
    db.commit()
    return RedirectResponse("/settings/security?enabled=1", status_code=303)

@router.post("/settings/security/disable-2fa")
def disable_2fa(request: Request, db: Session = Depends(get_db),
                current_user: User = Depends(require_auth)):
    current_user.totp_secret = None
    current_user.totp_enabled = False
    db.commit()
    return RedirectResponse("/settings/security", status_code=303)

@router.post("/settings/security/change-password")
async def change_password(request: Request, db: Session = Depends(get_db),
                          current_user: User = Depends(require_auth)):
    form = await request.form()
    current_pw = form.get("current_password", "")
    new_pw = form.get("new_password", "")
    if not auth_service.verify_password(current_pw, current_user.password_hash):
        return RedirectResponse("/settings/security?pw_error=1", status_code=303)
    current_user.password_hash = auth_service.hash_password(new_pw)
    db.commit()
    return RedirectResponse("/settings/security?pw_changed=1", status_code=303)


# ── HTMX ingredient row partials ──────────────────────────────────────────────

@router.get("/htmx/row/fermentable", response_class=HTMLResponse)
def htmx_fermentable_row(index: int, request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "partials/fermentable_row.html", {
        "index": index,
        "fermentables": db.query(Fermentable).order_by(Fermentable.name).all(),
    })


@router.get("/htmx/row/hop", response_class=HTMLResponse)
def htmx_hop_row(index: int, request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "partials/hop_row.html", {
        "index": index,
        "hops": db.query(Hop).order_by(Hop.name).all(),
    })


@router.get("/htmx/row/yeast", response_class=HTMLResponse)
def htmx_yeast_row(index: int, request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "partials/yeast_row.html", {
        "index": index,
        "yeasts": db.query(Yeast).order_by(Yeast.name).all(),
    })


@router.get("/htmx/row/misc", response_class=HTMLResponse)
def htmx_misc_row(index: int, request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "partials/misc_row.html", {
        "index": index,
        "miscs": db.query(Misc).order_by(Misc.name).all(),
    })


@router.get("/htmx/row/grape", response_class=HTMLResponse)
def htmx_grape_row(index: int, request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "partials/grape_row.html", {
        "index": index,
        "grapes": db.query(GrapeVariety).order_by(GrapeVariety.name).all(),
    })


@router.get("/htmx/row/mash_step", response_class=HTMLResponse)
def htmx_mash_step_row(index: int, request: Request):
    return templates.TemplateResponse(request, "partials/mash_step_row.html", {"index": index})


# ── Unit / measurement converter ──────────────────────────────────────────────

@router.get("/converter", response_class=HTMLResponse)
def converter(request: Request):
    return templates.TemplateResponse(request, "converter.html", {"page": "converter"})


@router.get("/water-chemistry", response_class=HTMLResponse)
def water_chemistry(request: Request):
    return templates.TemplateResponse(request, "water_chemistry.html", {"page": "water_chemistry"})


# ── Inventory ─────────────────────────────────────────────────────────────────

@router.get("/inventory", response_class=HTMLResponse)
def inventory_page(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "inventory.html", {
        "fermentables": db.query(Fermentable).order_by(Fermentable.name).all(),
        "hops": db.query(Hop).order_by(Hop.name).all(),
        "yeasts": db.query(Yeast).order_by(Yeast.name).all(),
        "miscs": db.query(Misc).order_by(Misc.name).all(),
        "recipes": db.query(Recipe).order_by(Recipe.name).all(),
        "page": "inventory",
    })


@router.post("/inventory/fermentable/{item_id}/stock")
async def inventory_fermentable_stock(item_id: int, request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    qty = float(form.get("qty", 0))
    item = db.get(Fermentable, item_id)
    if item:
        item.stock_qty = qty
        db.commit()
    return HTMLResponse(
        f'<span id="stock-fermentable-{item_id}" class="badge bg-secondary px-2 py-1" '
        f'style="min-width:60px;text-align:center;">{qty:.2f} kg</span>'
    )


@router.post("/inventory/hop/{item_id}/stock")
async def inventory_hop_stock(item_id: int, request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    qty = float(form.get("qty", 0))
    item = db.get(Hop, item_id)
    if item:
        item.stock_qty = qty
        db.commit()
    return HTMLResponse(
        f'<span id="stock-hop-{item_id}" class="badge bg-secondary px-2 py-1" '
        f'style="min-width:60px;text-align:center;">{qty:.1f} g</span>'
    )


@router.post("/inventory/yeast/{item_id}/stock")
async def inventory_yeast_stock(item_id: int, request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    qty = float(form.get("qty", 0))
    item = db.get(Yeast, item_id)
    unit = item.stock_unit or "pkg" if item else "pkg"
    if item:
        item.stock_qty = qty
        db.commit()
    return HTMLResponse(
        f'<span id="stock-yeast-{item_id}" class="badge bg-secondary px-2 py-1" '
        f'style="min-width:60px;text-align:center;">{qty:.0f} {unit}</span>'
    )


@router.post("/inventory/misc/{item_id}/stock")
async def inventory_misc_stock(item_id: int, request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    qty = float(form.get("qty", 0))
    item = db.get(Misc, item_id)
    unit = item.stock_unit or "g" if item else "g"
    if item:
        item.stock_qty = qty
        db.commit()
    return HTMLResponse(
        f'<span id="stock-misc-{item_id}" class="badge bg-secondary px-2 py-1" '
        f'style="min-width:60px;text-align:center;">{qty:.1f} {unit}</span>'
    )


@router.get("/inventory/check/{recipe_id}", response_class=HTMLResponse)
def inventory_check(recipe_id: int, request: Request, db: Session = Depends(get_db)):
    recipe = db.get(Recipe, recipe_id)
    if not recipe:
        return HTMLResponse('<p class="text-muted">Recipe not found.</p>')

    rows = []

    for rf in recipe.fermentables:
        ferm = db.get(Fermentable, rf.fermentable_id)
        if not ferm:
            continue
        needed = rf.amount_kg
        have = ferm.stock_qty or 0.0
        ok = have >= needed
        rows.append({
            "name": ferm.name,
            "needed": f"{needed:.3f} kg",
            "have": f"{have:.3f} kg",
            "ok": ok,
        })

    for rh in recipe.hops:
        hop = db.get(Hop, rh.hop_id)
        if not hop:
            continue
        needed = rh.amount_g
        have = hop.stock_qty or 0.0
        ok = have >= needed
        rows.append({
            "name": hop.name,
            "needed": f"{needed:.1f} g",
            "have": f"{have:.1f} g",
            "ok": ok,
        })

    for ry in recipe.yeasts:
        yeast = db.get(Yeast, ry.yeast_id)
        if not yeast:
            continue
        needed = ry.amount
        have = yeast.stock_qty or 0.0
        unit = yeast.stock_unit or "pkg"
        ok = have >= needed
        rows.append({
            "name": yeast.name,
            "needed": f"{needed:.0f} {unit}",
            "have": f"{have:.0f} {unit}",
            "ok": ok,
        })

    for rm in recipe.miscs:
        misc = db.get(Misc, rm.misc_id)
        if not misc:
            continue
        needed = rm.amount
        have = misc.stock_qty or 0.0
        unit = misc.stock_unit or "g"
        ok = have >= needed
        rows.append({
            "name": misc.name,
            "needed": f"{needed:.1f} {unit}",
            "have": f"{have:.1f} {unit}",
            "ok": ok,
        })

    if not rows:
        return HTMLResponse('<p class="text-muted">No ingredients found for this recipe.</p>')

    html_rows = ""
    for row in rows:
        icon = '<i class="bi bi-check-circle-fill text-success"></i>' if row["ok"] else '<i class="bi bi-x-circle-fill text-danger"></i>'
        html_rows += (
            f'<tr>'
            f'<td>{row["name"]}</td>'
            f'<td class="text-end">{row["needed"]}</td>'
            f'<td class="text-end">{row["have"]}</td>'
            f'<td class="text-center">{icon}</td>'
            f'</tr>'
        )

    return HTMLResponse(
        '<table class="table table-sm table-hover mb-0">'
        '<thead class="table-light"><tr>'
        '<th>Ingredient</th>'
        '<th class="text-end">Required</th>'
        '<th class="text-end">In Stock</th>'
        '<th class="text-center">Status</th>'
        '</tr></thead>'
        f'<tbody>{html_rows}</tbody>'
        '</table>'
    )


# ── Brew session detail + fermentation readings ───────────────────────────────

@router.get("/brew-sessions/{session_id}", response_class=HTMLResponse)
def brew_session_detail(session_id: int, request: Request, db: Session = Depends(get_db)):
    session = db.query(BrewSession).options(
        selectinload(BrewSession.recipe),
        selectinload(BrewSession.fermentation_readings),
        selectinload(BrewSession.barrel_aging_records).selectinload(BarrelAgingRecord.barrel),
        selectinload(BrewSession.barrel_aging_records).selectinload(BarrelAgingRecord.entries),
        selectinload(BrewSession.barrel_aging_records).selectinload(BarrelAgingRecord.disposition_entries),
        selectinload(BrewSession.mlf_entries),
        selectinload(BrewSession.fining_entries),
        selectinload(BrewSession.still_runs).selectinload(StillRun.cuts),
        selectinload(BrewSession.dry_hops),
        selectinload(BrewSession.packaging_entries),
    ).filter(BrewSession.id == session_id).first()
    if not session:
        return RedirectResponse("/brew-sessions", status_code=303)

    readings_data = [
        {
            "x": r.recorded_at.isoformat(),
            "gravity": r.gravity,
            "temperature_c": r.temperature_c,
        }
        for r in session.fermentation_readings
    ]
    now_dt = datetime.utcnow()
    now_iso = now_dt.strftime("%Y-%m-%dT%H:%M")
    barrels = db.query(Barrel).filter(Barrel.is_active == True).order_by(Barrel.name).all()

    batch_cost = None
    recipe = session.recipe
    if recipe:
        cost_items = []
        total = 0.0
        for rf in recipe.fermentables:
            if rf.fermentable and rf.fermentable.cost_per_kg:
                c = rf.amount_kg * rf.fermentable.cost_per_kg
                cost_items.append({"name": rf.fermentable.name, "category": "Fermentable",
                                   "amount": f"{rf.amount_kg:.2f} kg", "cost": c})
                total += c
        for rh in recipe.hops:
            if rh.hop and rh.hop.cost_per_kg:
                c = (rh.amount_g / 1000.0) * rh.hop.cost_per_kg
                cost_items.append({"name": rh.hop.name, "category": "Hop",
                                   "amount": f"{rh.amount_g:.0f} g", "cost": c})
                total += c
        for ry in recipe.yeasts:
            if ry.yeast and ry.yeast.cost_per_pkg:
                c = ry.amount * ry.yeast.cost_per_pkg
                cost_items.append({"name": ry.yeast.name, "category": "Yeast",
                                   "amount": f"{ry.amount:.0f} pkg", "cost": c})
                total += c
        for rm in recipe.miscs:
            if rm.misc and rm.misc.cost_per_unit:
                c = rm.amount * rm.misc.cost_per_unit
                cost_items.append({"name": rm.misc.name, "category": "Misc",
                                   "amount": f"{rm.amount:.0f}", "cost": c})
                total += c
        if cost_items:
            batch_size = session.actual_batch_size_l or recipe.batch_size_l
            pkg_count = session.packaging_entries[-1].vessel_count if session.packaging_entries else None
            batch_cost = {
                "items": cost_items,
                "total": total,
                "batch_size_l": batch_size,
                "cost_per_l": total / batch_size if batch_size else None,
                "vessel_count": pkg_count,
                "cost_per_vessel": total / pkg_count if pkg_count else None,
            }

    return templates.TemplateResponse(request, "brew_sessions/detail.html", {
        "session": session,
        "readings_json": json.dumps(readings_data),
        "now_iso": now_iso,
        "now_dt": now_dt,
        "barrels": barrels,
        "batch_cost": batch_cost,
        "page": "brew_sessions",
    })


@router.post("/brew-sessions/{session_id}/readings")
async def brew_session_reading_create(session_id: int, request: Request, db: Session = Depends(get_db)):
    session = db.get(BrewSession, session_id)
    if not session:
        return RedirectResponse("/brew-sessions", status_code=303)
    form = await request.form()
    recorded_at_str = form.get("recorded_at", "")
    try:
        recorded_at = datetime.strptime(recorded_at_str, "%Y-%m-%dT%H:%M")
    except (ValueError, TypeError):
        recorded_at = datetime.utcnow()
    gravity_raw = form.get("gravity", "")
    temp_raw = form.get("temperature_c", "")
    ph_raw = form.get("ph", "")
    ta_raw = form.get("ta", "")
    so2_free_raw = form.get("so2_free", "")
    so2_total_raw = form.get("so2_total", "")
    db.add(FermentationReading(
        session_id=session_id,
        recorded_at=recorded_at,
        gravity=float(gravity_raw) if gravity_raw else None,
        temperature_c=float(temp_raw) if temp_raw else None,
        ph=float(ph_raw) if ph_raw else None,
        ta=float(ta_raw) if ta_raw else None,
        so2_free=float(so2_free_raw) if so2_free_raw else None,
        so2_total=float(so2_total_raw) if so2_total_raw else None,
        notes=form.get("notes") or None,
    ))
    db.commit()
    return RedirectResponse(f"/brew-sessions/{session_id}", status_code=303)


@router.post("/brew-sessions/{session_id}/readings/{reading_id}/delete")
def brew_session_reading_delete(session_id: int, reading_id: int, db: Session = Depends(get_db)):
    reading = db.get(FermentationReading, reading_id)
    if reading and reading.session_id == session_id:
        db.delete(reading)
        db.commit()
    return RedirectResponse(f"/brew-sessions/{session_id}", status_code=303)


# ── Wine MLF entries ─────────────────────────────────────────────────────────

@router.post("/brew-sessions/{session_id}/mlf-entries")
async def mlf_entry_create(session_id: int, request: Request, db: Session = Depends(get_db)):
    session = db.get(BrewSession, session_id)
    if not session:
        return RedirectResponse("/brew-sessions", status_code=303)
    form = await request.form()
    recorded_at_str = form.get("recorded_at", "")
    try:
        recorded_at = datetime.strptime(recorded_at_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        recorded_at = datetime.utcnow()
    db.add(WineMLFEntry(
        session_id=session_id,
        recorded_at=recorded_at,
        event_type=form.get("event_type", "test"),
        strain=form.get("strain") or None,
        temperature_c=float(form["temperature_c"]) if form.get("temperature_c") else None,
        result=form.get("result") or None,
        notes=form.get("notes") or None,
    ))
    db.commit()
    return RedirectResponse(f"/brew-sessions/{session_id}", status_code=303)


@router.post("/brew-sessions/{session_id}/mlf-entries/{entry_id}/delete")
def mlf_entry_delete(session_id: int, entry_id: int, db: Session = Depends(get_db)):
    entry = db.get(WineMLFEntry, entry_id)
    if entry and entry.session_id == session_id:
        db.delete(entry)
        db.commit()
    return RedirectResponse(f"/brew-sessions/{session_id}", status_code=303)


# ── Wine fining entries ───────────────────────────────────────────────────────

@router.post("/brew-sessions/{session_id}/fining-entries")
async def fining_entry_create(session_id: int, request: Request, db: Session = Depends(get_db)):
    session = db.get(BrewSession, session_id)
    if not session:
        return RedirectResponse("/brew-sessions", status_code=303)
    form = await request.form()
    date_str = form.get("date", "")
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        date = datetime.utcnow()
    db.add(WineFiningEntry(
        session_id=session_id,
        date=date,
        agent=form.get("agent", ""),
        rate_g_per_hl=float(form["rate_g_per_hl"]) if form.get("rate_g_per_hl") else None,
        volume_l=float(form["volume_l"]) if form.get("volume_l") else None,
        purpose=form.get("purpose") or None,
        notes=form.get("notes") or None,
    ))
    db.commit()
    return RedirectResponse(f"/brew-sessions/{session_id}", status_code=303)


@router.post("/brew-sessions/{session_id}/fining-entries/{entry_id}/delete")
def fining_entry_delete(session_id: int, entry_id: int, db: Session = Depends(get_db)):
    entry = db.get(WineFiningEntry, entry_id)
    if entry and entry.session_id == session_id:
        db.delete(entry)
        db.commit()
    return RedirectResponse(f"/brew-sessions/{session_id}", status_code=303)


# ── Wine tools ────────────────────────────────────────────────────────────────

@router.get("/wine-tools", response_class=HTMLResponse)
def wine_tools_page(request: Request):
    return templates.TemplateResponse(request, "wine_tools.html", {"page": "wine_tools"})


# ── Spirits tools ─────────────────────────────────────────────────────────────

@router.get("/spirits-tools", response_class=HTMLResponse)
def spirits_tools_page(request: Request):
    return templates.TemplateResponse(request, "spirits_tools.html", {"page": "spirits_tools"})


@router.get("/mead-tools", response_class=HTMLResponse)
def mead_tools_page(request: Request):
    return templates.TemplateResponse(request, "mead_tools.html", {"page": "mead_tools"})


# ── Still run log ─────────────────────────────────────────────────────────────

@router.post("/brew-sessions/{session_id}/still-runs")
async def still_run_create(session_id: int, request: Request, db: Session = Depends(get_db)):
    session = db.get(BrewSession, session_id)
    if not session:
        return RedirectResponse("/brew-sessions", status_code=303)
    form = await request.form()
    run_date = datetime.utcnow()
    if form.get("run_date"):
        try:
            run_date = datetime.strptime(form["run_date"], "%Y-%m-%d")
        except ValueError:
            pass
    existing = db.query(StillRun).filter(StillRun.session_id == session_id).count()
    db.add(StillRun(
        session_id=session_id,
        run_number=existing + 1,
        run_date=run_date,
        charge_volume_l=float(form["charge_volume_l"]) if form.get("charge_volume_l") else None,
        charge_abv=float(form["charge_abv"]) if form.get("charge_abv") else None,
        still_type=form.get("still_type") or "pot",
        notes=form.get("notes") or None,
    ))
    db.commit()
    return RedirectResponse(f"/brew-sessions/{session_id}", status_code=303)


@router.post("/brew-sessions/{session_id}/still-runs/{run_id}/delete")
def still_run_delete(session_id: int, run_id: int, db: Session = Depends(get_db)):
    run = db.get(StillRun, run_id)
    if run and run.session_id == session_id:
        db.delete(run)
        db.commit()
    return RedirectResponse(f"/brew-sessions/{session_id}", status_code=303)


@router.post("/brew-sessions/{session_id}/still-runs/{run_id}/cuts")
async def still_cut_create(session_id: int, run_id: int, request: Request, db: Session = Depends(get_db)):
    run = db.get(StillRun, run_id)
    if not run or run.session_id != session_id:
        return RedirectResponse(f"/brew-sessions/{session_id}", status_code=303)
    form = await request.form()
    db.add(StillCut(
        still_run_id=run_id,
        cut_type=form.get("cut_type", "hearts"),
        volume_l=float(form["volume_l"]) if form.get("volume_l") else None,
        start_abv=float(form["start_abv"]) if form.get("start_abv") else None,
        end_abv=float(form["end_abv"]) if form.get("end_abv") else None,
        appearance=form.get("appearance") or None,
        aroma=form.get("aroma") or None,
        flavor=form.get("flavor") or None,
        finish=form.get("finish") or None,
        overall_notes=form.get("overall_notes") or None,
    ))
    db.commit()
    return RedirectResponse(f"/brew-sessions/{session_id}", status_code=303)


@router.post("/brew-sessions/{session_id}/still-runs/{run_id}/cuts/{cut_id}/delete")
def still_cut_delete(session_id: int, run_id: int, cut_id: int, db: Session = Depends(get_db)):
    cut = db.get(StillCut, cut_id)
    if cut and cut.still_run_id == run_id:
        db.delete(cut)
        db.commit()
    return RedirectResponse(f"/brew-sessions/{session_id}", status_code=303)


# ── Barrel disposition log ─────────────────────────────────────────────────────

@router.post("/brew-sessions/{session_id}/barrel-aging/{record_id}/disposition")
async def barrel_disposition_create(session_id: int, record_id: int,
                                    request: Request, db: Session = Depends(get_db)):
    record = db.get(BarrelAgingRecord, record_id)
    if not record or record.session_id != session_id:
        return RedirectResponse(f"/brew-sessions/{session_id}", status_code=303)
    form = await request.form()
    event_date = datetime.utcnow()
    if form.get("event_date"):
        try:
            event_date = datetime.strptime(form["event_date"], "%Y-%m-%d")
        except ValueError:
            pass
    action = form.get("action", "proof check")
    db.add(BarrelDispositionEntry(
        record_id=record_id,
        event_date=event_date,
        action=action,
        proof_at_action=float(form["proof_at_action"]) if form.get("proof_at_action") else None,
        volume_l=float(form["volume_l"]) if form.get("volume_l") else None,
        destination=form.get("destination") or None,
        notes=form.get("notes") or None,
    ))
    # Update disposition status if action changes it
    if action in ("dumped", "bottled", "re-casked", "blended", "sold"):
        record.disposition = action
        if not record.end_date:
            record.end_date = event_date
    db.commit()
    return RedirectResponse(f"/brew-sessions/{session_id}", status_code=303)


@router.post("/brew-sessions/{session_id}/barrel-aging/{record_id}/disposition/{entry_id}/delete")
def barrel_disposition_delete(session_id: int, record_id: int, entry_id: int,
                               db: Session = Depends(get_db)):
    entry = db.get(BarrelDispositionEntry, entry_id)
    if entry and entry.record_id == record_id:
        db.delete(entry)
        db.commit()
    return RedirectResponse(f"/brew-sessions/{session_id}", status_code=303)


# ── Barrel registry ──────────────────────────────────────────────────────────

WOOD_TYPES = ["American Oak", "French Oak", "Hungarian Oak", "Cherry", "Acacia", "Mulberry", "Chestnut"]
CHAR_LEVELS = ["#1 Light", "#2 Medium", "#3 Heavy", "#4 Extra Heavy", "Light Toast", "Medium Toast", "Heavy Toast"]
PREVIOUS_CONTENTS = ["New/Virgin", "Bourbon", "Rye Whiskey", "Red Wine", "White Wine", "Sherry", "Port", "Rum", "Tequila", "Brandy"]


@router.get("/barrels", response_class=HTMLResponse)
def barrels_page(request: Request, db: Session = Depends(get_db)):
    barrels = db.query(Barrel).order_by(Barrel.name).all()
    active_records = (
        db.query(BarrelAgingRecord)
        .filter(BarrelAgingRecord.end_date.is_(None))
        .options(
            selectinload(BarrelAgingRecord.session).selectinload(BrewSession.recipe),
            selectinload(BarrelAgingRecord.entries),
        )
        .all()
    )
    active_by_barrel = {}
    for rec in active_records:
        active_by_barrel.setdefault(rec.barrel_id, []).append(rec)
    return templates.TemplateResponse(request, "barrels/list.html", {
        "barrels": barrels,
        "active_by_barrel": active_by_barrel,
        "now_dt": datetime.utcnow(),
        "wood_types": WOOD_TYPES,
        "char_levels": CHAR_LEVELS,
        "previous_contents": PREVIOUS_CONTENTS,
        "page": "barrels",
    })


@router.post("/barrels/create")
async def barrel_create(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    u = request.session.get("units", "metric")
    db.add(Barrel(
        name=form["name"],
        barrel_style=form.get("barrel_style") or "traditional",
        size_l=parse_vol(form.get("size_l"), u),
        wood_type=form.get("wood_type") or None,
        char_level=form.get("char_level") or None,
        previous_contents=form.get("previous_contents") or None,
        age_months=int(form["age_months"]) if form.get("age_months") else None,
        wood_contact_area_cm2=parse_area(form.get("wood_contact_area_cm2"), u),
        storage_temp_c=parse_temp(form.get("storage_temp_c"), u),
        notes=form.get("notes") or None,
    ))
    db.commit()
    return RedirectResponse("/barrels", status_code=303)


@router.post("/barrels/{barrel_id}/update")
async def barrel_update(barrel_id: int, request: Request, db: Session = Depends(get_db)):
    barrel = db.get(Barrel, barrel_id)
    if not barrel:
        return RedirectResponse("/barrels", status_code=303)
    form = await request.form()
    u = request.session.get("units", "metric")
    barrel.name = form["name"]
    barrel.barrel_style = form.get("barrel_style") or "traditional"
    barrel.size_l = parse_vol(form.get("size_l"), u)
    barrel.wood_type = form.get("wood_type") or None
    barrel.char_level = form.get("char_level") or None
    barrel.previous_contents = form.get("previous_contents") or None
    barrel.age_months = int(form["age_months"]) if form.get("age_months") else None
    barrel.wood_contact_area_cm2 = parse_area(form.get("wood_contact_area_cm2"), u)
    barrel.storage_temp_c = parse_temp(form.get("storage_temp_c"), u)
    barrel.notes = form.get("notes") or None
    db.commit()
    return RedirectResponse("/barrels", status_code=303)


@router.post("/barrels/{barrel_id}/delete")
def barrel_delete(barrel_id: int, db: Session = Depends(get_db)):
    barrel = db.get(Barrel, barrel_id)
    if barrel:
        db.delete(barrel)
        db.commit()
    return RedirectResponse("/barrels", status_code=303)


# ── Barrel aging on sessions ──────────────────────────────────────────────────

@router.post("/brew-sessions/{session_id}/barrel-aging/start")
async def barrel_aging_start(session_id: int, request: Request, db: Session = Depends(get_db)):
    session = db.get(BrewSession, session_id)
    if not session:
        return RedirectResponse("/brew-sessions", status_code=303)
    form = await request.form()
    start_date = datetime.utcnow()
    if form.get("start_date"):
        try:
            start_date = datetime.strptime(form["start_date"], "%Y-%m-%d")
        except ValueError:
            pass
    db.add(BarrelAgingRecord(
        barrel_id=int(form["barrel_id"]),
        session_id=session_id,
        start_date=start_date,
        target_days=int(form["target_days"]) if form.get("target_days") else None,
        target_55gal_months=float(form["target_55gal_months"]) if form.get("target_55gal_months") else None,
        fill_proof=float(form["fill_proof"]) if form.get("fill_proof") else None,
        disposition='aging',
        notes=form.get("notes") or None,
    ))
    db.commit()
    return RedirectResponse(f"/brew-sessions/{session_id}", status_code=303)


@router.post("/brew-sessions/{session_id}/barrel-aging/{record_id}/end")
async def barrel_aging_end(session_id: int, record_id: int, request: Request, db: Session = Depends(get_db)):
    record = db.get(BarrelAgingRecord, record_id)
    if record and record.session_id == session_id:
        form = await request.form()
        end_date = datetime.utcnow()
        if form.get("end_date"):
            try:
                end_date = datetime.strptime(form["end_date"], "%Y-%m-%d")
            except ValueError:
                pass
        record.end_date = end_date
        db.commit()
    return RedirectResponse(f"/brew-sessions/{session_id}", status_code=303)


@router.post("/brew-sessions/{session_id}/barrel-aging/{record_id}/entries")
async def barrel_aging_entry_create(session_id: int, record_id: int, request: Request, db: Session = Depends(get_db)):
    record = db.get(BarrelAgingRecord, record_id)
    if not record or record.session_id != session_id:
        return RedirectResponse(f"/brew-sessions/{session_id}", status_code=303)
    form = await request.form()
    recorded_at = datetime.utcnow()
    if form.get("recorded_at"):
        try:
            recorded_at = datetime.strptime(form["recorded_at"], "%Y-%m-%dT%H:%M")
        except ValueError:
            pass
    db.add(BarrelAgingEntry(
        record_id=record_id,
        recorded_at=recorded_at,
        gravity=float(form["gravity"]) if form.get("gravity") else None,
        abv=float(form["abv"]) if form.get("abv") else None,
        color_srm=float(form["color_srm"]) if form.get("color_srm") else None,
        flavor_notes=form.get("flavor_notes") or None,
        notes=form.get("notes") or None,
    ))
    db.commit()
    return RedirectResponse(f"/brew-sessions/{session_id}", status_code=303)


@router.post("/brew-sessions/{session_id}/barrel-aging/{record_id}/entries/{entry_id}/delete")
def barrel_aging_entry_delete(session_id: int, record_id: int, entry_id: int, db: Session = Depends(get_db)):
    entry = db.get(BarrelAgingEntry, entry_id)
    if entry and entry.record_id == record_id:
        db.delete(entry)
        db.commit()
    return RedirectResponse(f"/brew-sessions/{session_id}", status_code=303)


@router.post("/brew-sessions/{session_id}/barrel-aging/{record_id}/delete")
def barrel_aging_record_delete(session_id: int, record_id: int, db: Session = Depends(get_db)):
    record = db.get(BarrelAgingRecord, record_id)
    if record and record.session_id == session_id:
        db.delete(record)
        db.commit()
    return RedirectResponse(f"/brew-sessions/{session_id}", status_code=303)


# ── Session dry hop log ───────────────────────────────────────────────────────

@router.post("/brew-sessions/{session_id}/dry-hops")
async def dry_hop_create(session_id: int, request: Request, db: Session = Depends(get_db)):
    session = db.get(BrewSession, session_id)
    if not session:
        return RedirectResponse("/brew-sessions", status_code=303)
    form = await request.form()
    from datetime import date as date_type
    def _parse_date(s):
        try:
            return datetime.strptime(s, "%Y-%m-%d").date() if s else None
        except ValueError:
            return None
    db.add(SessionDryHop(
        session_id=session_id,
        variety=form.get("variety") or None,
        total_grams=float(form["total_grams"]) if form.get("total_grams") else None,
        rate_g_per_l=float(form["rate_g_per_l"]) if form.get("rate_g_per_l") else None,
        vessel=form.get("vessel") or None,
        temp_c=float(form["temp_c"]) if form.get("temp_c") else None,
        addition_date=_parse_date(form.get("addition_date")),
        removal_date=_parse_date(form.get("removal_date")),
        notes=form.get("notes") or None,
    ))
    db.commit()
    return RedirectResponse(f"/brew-sessions/{session_id}", status_code=303)


@router.post("/brew-sessions/{session_id}/dry-hops/{dh_id}/delete")
def dry_hop_delete(session_id: int, dh_id: int, db: Session = Depends(get_db)):
    dh = db.get(SessionDryHop, dh_id)
    if dh and dh.session_id == session_id:
        db.delete(dh)
        db.commit()
    return RedirectResponse(f"/brew-sessions/{session_id}", status_code=303)


# ── Session packaging log ──────────────────────────────────────────────────────

@router.post("/brew-sessions/{session_id}/packaging")
async def packaging_create(session_id: int, request: Request, db: Session = Depends(get_db)):
    session = db.get(BrewSession, session_id)
    if not session:
        return RedirectResponse("/brew-sessions", status_code=303)
    form = await request.form()
    def _parse_date(s):
        try:
            return datetime.strptime(s, "%Y-%m-%d").date() if s else None
        except ValueError:
            return None
    db.add(PackagingEntry(
        session_id=session_id,
        package_date=_parse_date(form.get("package_date")),
        method=form.get("method") or None,
        vessel_count=int(form["vessel_count"]) if form.get("vessel_count") else None,
        fill_volume_l=float(form["fill_volume_l"]) if form.get("fill_volume_l") else None,
        carbonation_vol=float(form["carbonation_vol"]) if form.get("carbonation_vol") else None,
        priming_sugar_type=form.get("priming_sugar_type") or None,
        priming_sugar_g=float(form["priming_sugar_g"]) if form.get("priming_sugar_g") else None,
        co2_psi=float(form["co2_psi"]) if form.get("co2_psi") else None,
        final_gravity=float(form["final_gravity"]) if form.get("final_gravity") else None,
        notes=form.get("notes") or None,
    ))
    db.commit()
    return RedirectResponse(f"/brew-sessions/{session_id}", status_code=303)


@router.post("/brew-sessions/{session_id}/packaging/{entry_id}/delete")
def packaging_delete(session_id: int, entry_id: int, db: Session = Depends(get_db)):
    entry = db.get(PackagingEntry, entry_id)
    if entry and entry.session_id == session_id:
        db.delete(entry)
        db.commit()
    return RedirectResponse(f"/brew-sessions/{session_id}", status_code=303)


# ── Production calendar ───────────────────────────────────────────────────────

@router.get("/calendar", response_class=HTMLResponse)
def production_calendar(request: Request, db: Session = Depends(get_db)):
    from app.models.barrel import BarrelAgingRecord as _BAR2
    sessions = db.query(BrewSession).options(selectinload(BrewSession.recipe)).all()
    barrel_records = db.query(_BAR2).options(
        selectinload(_BAR2.barrel), selectinload(_BAR2.session).selectinload(BrewSession.recipe)
    ).all()

    events = []
    for s in sessions:
        name = s.recipe.name if s.recipe else f"Session #{s.id}"
        if s.brew_date:
            events.append({"title": f"Brew: {name}", "start": s.brew_date.strftime("%Y-%m-%d"),
                           "color": "#f59e0b", "url": f"/brew-sessions/{s.id}", "extendedProps": {"type": "brew"}})
        if s.package_date:
            events.append({"title": f"Package: {name}", "start": s.package_date.strftime("%Y-%m-%d"),
                           "color": "#10b981", "url": f"/brew-sessions/{s.id}", "extendedProps": {"type": "package"}})
        if s.crush_date:
            events.append({"title": f"Crush: {name}", "start": s.crush_date.strftime("%Y-%m-%d"),
                           "color": "#8b5cf6", "url": f"/brew-sessions/{s.id}", "extendedProps": {"type": "crush"}})

    for rec in barrel_records:
        barrel_name = rec.barrel.name if rec.barrel else "Barrel"
        session_name = rec.session.recipe.name if rec.session and rec.session.recipe else ""
        label = f"{barrel_name}" + (f" ({session_name})" if session_name else "")
        if rec.start_date:
            events.append({"title": f"Fill: {label}", "start": rec.start_date.strftime("%Y-%m-%d"),
                           "color": "#92400e", "extendedProps": {"type": "barrel_fill"}})
        if rec.end_date:
            events.append({"title": f"Barrel Out: {label}", "start": rec.end_date.strftime("%Y-%m-%d"),
                           "color": "#d97706", "extendedProps": {"type": "barrel_out"}})
        elif rec.target_days and rec.start_date:
            from datetime import timedelta as _td
            target_date = rec.start_date + _td(days=rec.target_days)
            events.append({"title": f"Target: {label}", "start": target_date.strftime("%Y-%m-%d"),
                           "color": "#d97706", "extendedProps": {"type": "barrel_target"}})

    return templates.TemplateResponse(request, "calendar.html", {
        "events_json": json.dumps(events),
        "page": "calendar",
    })


# ── Data export ────────────────────────────────────────────────────────────────

def _csv_response(filename: str, headers: list, rows: list) -> StreamingResponse:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(headers)
    w.writerows(rows)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/sessions.csv")
def export_sessions_csv(db: Session = Depends(get_db)):
    sessions = db.query(BrewSession).options(selectinload(BrewSession.recipe)).order_by(BrewSession.id).all()
    rows = []
    for s in sessions:
        rows.append([
            s.id, s.recipe.name if s.recipe else "", s.status, s.craft or "",
            s.brew_date.strftime("%Y-%m-%d") if s.brew_date else "",
            s.package_date.strftime("%Y-%m-%d") if s.package_date else "",
            s.actual_og or "", s.actual_fg or "", s.actual_abv or "",
            s.actual_batch_size_l or "", s.actual_efficiency or "",
            (s.notes or "").replace("\n", " "),
        ])
    return _csv_response("sessions.csv",
        ["ID", "Recipe", "Status", "Craft", "Brew Date", "Package Date",
         "OG", "FG", "ABV%", "Batch L", "Efficiency%", "Notes"], rows)


@router.get("/export/fermentation-readings.csv")
def export_fermentation_csv(db: Session = Depends(get_db)):
    readings = db.query(FermentationReading).options(
        selectinload(FermentationReading.session).selectinload(BrewSession.recipe)
    ).order_by(FermentationReading.session_id, FermentationReading.recorded_at).all()
    rows = [[
        r.id, r.session_id,
        r.session.recipe.name if r.session and r.session.recipe else "",
        r.recorded_at.strftime("%Y-%m-%d %H:%M") if r.recorded_at else "",
        r.gravity or "", r.temperature_c or "", r.ph or "", r.ta or "",
        r.so2_free or "", r.so2_total or "", r.notes or "",
    ] for r in readings]
    return _csv_response("fermentation_readings.csv",
        ["ID", "Session ID", "Recipe", "Recorded At", "Gravity", "Temp C",
         "pH", "TA g/L", "Free SO2", "Total SO2", "Notes"], rows)


@router.get("/export/barrel-entries.csv")
def export_barrel_csv(db: Session = Depends(get_db)):
    from app.models.barrel import BarrelAgingRecord as _BAR3, BarrelAgingEntry as _BAE
    entries = db.query(_BAE).options(
        selectinload(_BAE.record).selectinload(_BAR3.barrel),
        selectinload(_BAE.record).selectinload(_BAR3.session).selectinload(BrewSession.recipe),
    ).order_by(_BAE.record_id, _BAE.recorded_at).all()
    rows = [[
        e.id, e.record_id,
        e.record.barrel.name if e.record and e.record.barrel else "",
        e.record.session.recipe.name if e.record and e.record.session and e.record.session.recipe else "",
        e.recorded_at.strftime("%Y-%m-%d") if e.recorded_at else "",
        e.gravity or "", e.abv or "", e.color_srm or "",
        e.flavor_notes or "", e.notes or "",
    ] for e in entries]
    return _csv_response("barrel_entries.csv",
        ["ID", "Record ID", "Barrel", "Recipe", "Date", "Gravity", "ABV%", "SRM",
         "Flavor Notes", "Notes"], rows)


# ── AI chat ────────────────────────────────────────────────────────────────────

@router.post("/ai/chat")
async def ai_chat(request: Request, db: Session = Depends(get_db)):
    import httpx
    body = await request.json()
    message = body.get("message", "").strip()
    context = body.get("context", {})
    history = body.get("history", [])  # [{role, content}, ...]

    if not message:
        return JSONResponse({"error": "Empty message"}, status_code=400)

    provider = _get_setting(db, "ai_provider", "openai_compatible")
    model = _get_setting(db, "ai_model", "")
    api_key = _get_setting(db, "ai_api_key", "")
    base_url = _get_setting(db, "ai_base_url", "http://localhost:11434/v1")

    if not model:
        return JSONResponse({"error": "AI model not configured — visit Settings → AI Assistant."}, status_code=503)

    system = (
        "You are a helpful brewing assistant embedded in Brewbot, a craft beverage production management system. "
        "You help with brewing calculations, recipes, fermentation troubleshooting, and production planning. "
        "Be concise and practical.\n\n"
        "FORM FILL: When the user asks you to create a recipe, write a grain bill, mash schedule, hop schedule, or yeast selection, "
        "include a JSON block at the END of your response in this exact format:\n"
        "```json\n"
        '{"fill": {"simple": {"name": "...", "batch_size_l": 20, "efficiency": 72}, '
        '"fermentables": [{"name": "Pale Malt (2 Row)", "fermentable_type": "Grain", "color_srm": 2, "potential": 1.037, "yield_pct": 75, "amount_kg": 4.5}], '
        '"hops": [{"name": "Citra", "alpha_pct": 12, "hop_type": "Bittering", "amount_g": 30, "time_min": 60, "use": "Boil"}], '
        '"yeasts": [{"name": "Safale US-05", "lab": "Fermentis", "yeast_type": "Ale", "form": "Dry", "attenuation_pct": 77, "amount_packets": 1}], '
        '"mash_steps": [{"name": "Single Infusion", "temp_c": 67, "duration_min": 60}]}}\n'
        "```\n"
        "Always include fermentable_type (Grain/Sugar/Extract/Dry Extract/Adjunct), color_srm, potential, yield_pct for fermentables. "
        "Always include alpha_pct for hops. Always include lab, yeast_type (Ale/Lager/Wine/Champagne), form (Dry/Liquid), attenuation_pct for yeasts. "
        "hop 'use' values: Boil, Dry Hop, First Wort, Aroma, Mash. "
        "These properties let the system auto-create ingredients that don't exist yet. "
        "The user will be shown a confirmation dialog before anything is applied.\n"
    )
    if context:
        system += f"\nCurrent page: {context.get('title','')}, URL: {context.get('url','')}"
        if context.get("data"):
            system += f"\nPage context: {json.dumps(context['data'])[:1000]}"

    messages = history[-10:] + [{"role": "user", "content": message}]

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, read=120.0)) as client:
            if provider == "anthropic":
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
                             "Content-Type": "application/json"},
                    json={"model": model, "max_tokens": 1024, "system": system, "messages": messages},
                )
                resp.raise_for_status()
                text = resp.json()["content"][0]["text"]
            else:
                url = base_url.rstrip("/") + "/chat/completions"
                headers = {"Content-Type": "application/json"}
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"
                resp = await client.post(url, headers=headers,
                    json={"model": model, "messages": [{"role": "system", "content": system}] + messages})
                resp.raise_for_status()
                text = resp.json()["choices"][0]["message"]["content"]
        return JSONResponse({"response": text})
    except Exception as e:
        return JSONResponse({"error": f"AI request failed: {str(e)[:200]}"}, status_code=502)


@router.get("/settings/ai", response_class=HTMLResponse)
def ai_settings_get(request: Request, db: Session = Depends(get_db)):
    return RedirectResponse("/settings", status_code=303)


@router.post("/settings/ai")
async def ai_settings_post(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    _set_setting(db, "ai_provider", form.get("ai_provider", "openai_compatible"))
    _set_setting(db, "ai_model", form.get("ai_model", ""))
    _set_setting(db, "ai_api_key", form.get("ai_api_key", ""))
    _set_setting(db, "ai_base_url", form.get("ai_base_url", ""))
    db.commit()
    return RedirectResponse("/settings?saved=ai", status_code=303)


# ── Shopping list ──────────────────────────────────────────────────────────────

@router.get("/shopping-list", response_class=HTMLResponse)
def shopping_list(request: Request, db: Session = Depends(get_db)):
    from collections import defaultdict

    all_sessions = (
        db.query(BrewSession)
        .options(selectinload(BrewSession.recipe))
        .filter(BrewSession.status.in_(["planned", "brewing", "fermenting"]))
        .order_by(BrewSession.brew_date.asc().nullslast())
        .all()
    )

    session_ids = [int(v) for k, v in request.query_params.multi_items() if k == "session_ids"]

    shopping = None
    if session_ids:
        selected = (
            db.query(BrewSession)
            .options(
                selectinload(BrewSession.recipe).selectinload(Recipe.fermentables),
                selectinload(BrewSession.recipe).selectinload(Recipe.hops),
                selectinload(BrewSession.recipe).selectinload(Recipe.yeasts),
                selectinload(BrewSession.recipe).selectinload(Recipe.miscs),
            )
            .filter(BrewSession.id.in_(session_ids))
            .all()
        )

        fermentable_needs = defaultdict(lambda: {"name": "", "needed": 0.0, "stock": 0.0, "unit": "kg"})
        hop_needs = defaultdict(lambda: {"name": "", "needed": 0.0, "stock": 0.0, "unit": "g"})
        yeast_needs = defaultdict(lambda: {"name": "", "needed": 0.0, "stock": 0.0, "unit": "pkg"})
        misc_needs = defaultdict(lambda: {"name": "", "needed": 0.0, "stock": 0.0, "unit": "g"})

        for sess in selected:
            if not sess.recipe:
                continue
            for rf in sess.recipe.fermentables:
                f = rf.fermentable
                fermentable_needs[f.id]["name"] = f.name
                fermentable_needs[f.id]["needed"] += rf.amount_kg or 0.0
                fermentable_needs[f.id]["stock"] = f.stock_qty or 0.0
            for rh in sess.recipe.hops:
                h = rh.hop
                hop_needs[h.id]["name"] = h.name
                hop_needs[h.id]["needed"] += rh.amount_g or 0.0
                hop_needs[h.id]["stock"] = h.stock_qty or 0.0
            for ry in sess.recipe.yeasts:
                y = ry.yeast
                yeast_needs[y.id]["name"] = f"{y.name} ({y.lab or '?'})"
                yeast_needs[y.id]["needed"] += ry.amount or 0.0
                yeast_needs[y.id]["stock"] = y.stock_qty or 0.0
                yeast_needs[y.id]["unit"] = y.stock_unit or "pkg"
            for rm in sess.recipe.miscs:
                m = rm.misc
                misc_needs[m.id]["name"] = m.name
                misc_needs[m.id]["needed"] += rm.amount or 0.0
                misc_needs[m.id]["stock"] = m.stock_qty or 0.0
                misc_needs[m.id]["unit"] = m.stock_unit or "g"

        def _sort_key(x):
            return x["stock"] - x["needed"]

        shopping = {
            "fermentables": sorted(fermentable_needs.values(), key=_sort_key),
            "hops": sorted(hop_needs.values(), key=_sort_key),
            "yeasts": sorted(yeast_needs.values(), key=_sort_key),
            "miscs": sorted(misc_needs.values(), key=_sort_key),
            "session_names": [s.recipe.name if s.recipe else f"#{s.id}" for s in selected],
        }

    return templates.TemplateResponse(request, "shopping_list.html", {
        "all_sessions": all_sessions,
        "selected_ids": session_ids,
        "shopping": shopping,
        "page": "shopping_list",
    })


# ── Grape variety library ─────────────────────────────────────────────────────

@router.post("/grapes/create")
async def grape_create(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    db.add(GrapeVariety(
        name=form["name"],
        color=form.get("color") or None,
        origin=form.get("origin") or None,
        notes=form.get("notes") or None,
    ))
    db.commit()
    return RedirectResponse("/ingredients?tab=grapes", status_code=303)


@router.post("/grapes/{item_id}/update")
async def grape_update(item_id: int, request: Request, db: Session = Depends(get_db)):
    item = db.get(GrapeVariety, item_id)
    if not item:
        return RedirectResponse("/ingredients?tab=grapes", status_code=303)
    form = await request.form()
    item.name = form["name"]
    item.color = form.get("color") or None
    item.origin = form.get("origin") or None
    item.notes = form.get("notes") or None
    db.commit()
    return RedirectResponse("/ingredients?tab=grapes", status_code=303)


@router.post("/grapes/{item_id}/delete")
def grape_delete(item_id: int, db: Session = Depends(get_db)):
    item = db.get(GrapeVariety, item_id)
    if not item:
        return RedirectResponse("/ingredients?tab=grapes", status_code=303)
    if db.query(RecipeGrape).filter_by(grape_id=item_id).count():
        msg = f"{item.name} is used in one or more recipes and cannot be deleted."
        return RedirectResponse(f"/ingredients?tab=grapes&error={msg}", status_code=303)
    db.delete(item)
    db.commit()
    return RedirectResponse("/ingredients?tab=grapes", status_code=303)


# Export public (unauthenticated) router for main.py
public_router = _public_router
