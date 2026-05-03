from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.brew_session import BrewSession
from app.models.device import Device, RigProfile
from app.models.equipment import Equipment
from app.models.fermentable import Fermentable
from app.models.hop import Hop
from app.models.misc import Misc
from app.models.recipe import Recipe, RecipeFermentable, RecipeHop, RecipeMisc, RecipeYeast
from app.models.style import Style
from app.models.yeast import Yeast

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(include_in_schema=False)


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

@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "devices": db.query(Device).order_by(Device.role).all(),
        "recent_recipes": db.query(Recipe).order_by(Recipe.created_at.desc()).limit(6).all(),
        "active_sessions": db.query(BrewSession).filter(
            BrewSession.status.in_(["brewing", "fermenting", "conditioning"])
        ).all(),
        "page": "dashboard",
    })


# ── Recipes ───────────────────────────────────────────────────────────────────

@router.get("/recipes", response_class=HTMLResponse)
def recipes_list(request: Request, q: str = "", db: Session = Depends(get_db)):
    query = db.query(Recipe)
    if q:
        query = query.filter(Recipe.name.ilike(f"%{q}%"))
    return templates.TemplateResponse("recipes/list.html", {
        "request": request,
        "recipes": query.order_by(Recipe.created_at.desc()).all(),
        "q": q,
        "page": "recipes",
    })


@router.get("/recipes/new", response_class=HTMLResponse)
def recipe_new(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("recipes/form.html", {
        "request": request,
        "recipe": None,
        "styles": db.query(Style).order_by(Style.name).all(),
        "equipment_list": db.query(Equipment).order_by(Equipment.name).all(),
        "page": "recipes",
    })


@router.get("/recipes/{recipe_id}/edit", response_class=HTMLResponse)
def recipe_edit(recipe_id: int, request: Request, db: Session = Depends(get_db)):
    recipe = db.get(Recipe, recipe_id)
    if not recipe:
        return RedirectResponse("/recipes", status_code=303)
    return templates.TemplateResponse("recipes/form.html", {
        "request": request,
        "recipe": recipe,
        "styles": db.query(Style).order_by(Style.name).all(),
        "equipment_list": db.query(Equipment).order_by(Equipment.name).all(),
        "page": "recipes",
    })


@router.get("/recipes/{recipe_id}", response_class=HTMLResponse)
def recipe_detail(recipe_id: int, request: Request, db: Session = Depends(get_db)):
    recipe = db.get(Recipe, recipe_id)
    if not recipe:
        return RedirectResponse("/recipes", status_code=303)
    return templates.TemplateResponse("recipes/detail.html", {
        "request": request,
        "recipe": recipe,
        "page": "recipes",
    })


@router.post("/recipes", response_class=HTMLResponse)
async def recipe_create(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    fermentables, hops, yeasts, miscs = _parse_ingredients(form)
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
    for obj in recipe.fermentables[:] + recipe.hops[:] + recipe.yeasts[:] + recipe.miscs[:]:
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
    db.commit()
    return RedirectResponse(f"/recipes/{recipe.id}", status_code=303)


@router.post("/recipes/{recipe_id}/delete")
def recipe_delete(recipe_id: int, db: Session = Depends(get_db)):
    recipe = db.get(Recipe, recipe_id)
    if recipe:
        db.delete(recipe)
        db.commit()
    return RedirectResponse("/recipes", status_code=303)


# ── Equipment ─────────────────────────────────────────────────────────────────

@router.get("/equipment", response_class=HTMLResponse)
def equipment_list(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("equipment/list.html", {
        "request": request,
        "equipment_list": db.query(Equipment).order_by(Equipment.name).all(),
        "page": "equipment",
    })


@router.post("/equipment", response_class=HTMLResponse)
async def equipment_create(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    db.add(Equipment(
        name=form["name"],
        batch_size_l=float(form["batch_size_l"]),
        boil_size_l=float(form["boil_size_l"]),
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
        db.delete(item)
        db.commit()
    return RedirectResponse("/equipment", status_code=303)


# ── Ingredients library ───────────────────────────────────────────────────────

@router.get("/ingredients", response_class=HTMLResponse)
def ingredients_list(request: Request, tab: str = "fermentables", db: Session = Depends(get_db)):
    return templates.TemplateResponse("ingredients/list.html", {
        "request": request,
        "fermentables": db.query(Fermentable).order_by(Fermentable.name).all(),
        "hops": db.query(Hop).order_by(Hop.name).all(),
        "yeasts": db.query(Yeast).order_by(Yeast.name).all(),
        "miscs": db.query(Misc).order_by(Misc.name).all(),
        "tab": tab,
        "page": "ingredients",
    })


# ── Devices / Controller ──────────────────────────────────────────────────────

@router.get("/devices", response_class=HTMLResponse)
def devices_page(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("devices/list.html", {
        "request": request,
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


# ── Brew sessions ─────────────────────────────────────────────────────────────

@router.get("/brew-sessions", response_class=HTMLResponse)
def brew_sessions_list(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("brew_sessions/list.html", {
        "request": request,
        "sessions": db.query(BrewSession).order_by(BrewSession.created_at.desc()).all(),
        "recipes": db.query(Recipe).order_by(Recipe.name).all(),
        "page": "brew_sessions",
    })


@router.post("/brew-sessions", response_class=HTMLResponse)
async def brew_session_create(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    db.add(BrewSession(
        recipe_id=int(form["recipe_id"]),
        status="planned",
        notes=form.get("notes") or None,
    ))
    db.commit()
    return RedirectResponse("/brew-sessions", status_code=303)


# ── HTMX ingredient row partials ──────────────────────────────────────────────

@router.get("/htmx/row/fermentable", response_class=HTMLResponse)
def htmx_fermentable_row(index: int, request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("partials/fermentable_row.html", {
        "request": request, "index": index,
        "fermentables": db.query(Fermentable).order_by(Fermentable.name).all(),
    })


@router.get("/htmx/row/hop", response_class=HTMLResponse)
def htmx_hop_row(index: int, request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("partials/hop_row.html", {
        "request": request, "index": index,
        "hops": db.query(Hop).order_by(Hop.name).all(),
    })


@router.get("/htmx/row/yeast", response_class=HTMLResponse)
def htmx_yeast_row(index: int, request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("partials/yeast_row.html", {
        "request": request, "index": index,
        "yeasts": db.query(Yeast).order_by(Yeast.name).all(),
    })


@router.get("/htmx/row/misc", response_class=HTMLResponse)
def htmx_misc_row(index: int, request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("partials/misc_row.html", {
        "request": request, "index": index,
        "miscs": db.query(Misc).order_by(Misc.name).all(),
    })
