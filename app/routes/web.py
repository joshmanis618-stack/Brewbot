from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.brew_program import BrewProgram, BrewStep, BrewSessionStep
from app.models.brew_session import BrewSession
from app.models.device import Device, RigProfile
from app.models.equipment import Equipment
from app.models.fermentable import Fermentable
from app.models.hop import Hop
from app.models.misc import Misc
from app.models.recipe import Recipe, RecipeFermentable, RecipeHop, RecipeMisc, RecipeYeast
from app.models.style import Style
from app.models.yeast import Yeast
from app.services import calc as calc_service

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(include_in_schema=False)


def _form_context(db: Session) -> dict:
    return {
        "styles": db.query(Style).order_by(Style.name).all(),
        "equipment_list": db.query(Equipment).order_by(Equipment.name).all(),
        "all_fermentables": db.query(Fermentable).order_by(Fermentable.name).all(),
        "all_hops": db.query(Hop).order_by(Hop.name).all(),
        "all_yeasts": db.query(Yeast).order_by(Yeast.name).all(),
        "all_miscs": db.query(Misc).order_by(Misc.name).all(),
    }


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
    return templates.TemplateResponse(request, "dashboard.html", {
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
    return templates.TemplateResponse(request, "ingredients/list.html", {
        "fermentables": db.query(Fermentable).order_by(Fermentable.name).all(),
        "hops": db.query(Hop).order_by(Hop.name).all(),
        "yeasts": db.query(Yeast).order_by(Yeast.name).all(),
        "miscs": db.query(Misc).order_by(Misc.name).all(),
        "tab": tab,
        "page": "ingredients",
        "error": request.query_params.get("error"),
    })


def _in_use_error(name: str, tab: str) -> RedirectResponse:
    msg = f"{name} is used in one or more recipes and cannot be deleted."
    return RedirectResponse(f"/ingredients?tab={tab}&error={msg}", status_code=303)


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


@router.post("/brew-sessions/create", response_class=HTMLResponse)
async def brew_session_create(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    brew_date = None
    if form.get("brew_date"):
        brew_date = datetime.strptime(form["brew_date"], "%Y-%m-%d")
    db.add(BrewSession(
        recipe_id=int(form["recipe_id"]),
        status="planned",
        brew_date=brew_date,
        notes=form.get("notes") or None,
    ))
    db.commit()
    return RedirectResponse("/brew-sessions", status_code=303)


@router.post("/brew-sessions", response_class=HTMLResponse)
async def brew_session_create_modal(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    db.add(BrewSession(
        recipe_id=int(form["recipe_id"]),
        status="planned",
        notes=form.get("notes") or None,
    ))
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


# ── Unit / measurement converter ──────────────────────────────────────────────

@router.get("/converter", response_class=HTMLResponse)
def converter(request: Request):
    return templates.TemplateResponse(request, "converter.html", {"page": "converter"})
