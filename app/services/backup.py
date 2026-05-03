"""JSON backup / restore for all Brewbot data."""
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.brew_program import BrewProgram, BrewStep, BrewStepCommand
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

log = logging.getLogger(__name__)


def _dt(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def export_all(db: Session) -> dict:
    fermentables = []
    for f in db.query(Fermentable).all():
        fermentables.append({
            "name": f.name,
            "type": f.type,
            "origin": f.origin,
            "supplier": f.supplier,
            "color_srm": f.color_srm,
            "potential": f.potential,
            "yield_pct": f.yield_pct,
            "moisture_pct": f.moisture_pct,
            "diastatic_power": f.diastatic_power,
            "protein_pct": f.protein_pct,
            "max_in_batch_pct": f.max_in_batch_pct,
            "add_after_boil": f.add_after_boil,
            "recommend_mash": f.recommend_mash,
            "notes": f.notes,
        })

    hops = []
    for h in db.query(Hop).all():
        hops.append({
            "name": h.name,
            "origin": h.origin,
            "type": h.type,
            "alpha_pct": h.alpha_pct,
            "beta_pct": h.beta_pct,
            "hsi": h.hsi,
            "caryophyllene_pct": h.caryophyllene_pct,
            "cohumulone_pct": h.cohumulone_pct,
            "myrcene_pct": h.myrcene_pct,
            "humulene_pct": h.humulene_pct,
            "notes": h.notes,
            "substitutes": h.substitutes,
        })

    yeasts = []
    for y in db.query(Yeast).all():
        yeasts.append({
            "name": y.name,
            "lab": y.lab,
            "product_id": y.product_id,
            "type": y.type,
            "form": y.form,
            "min_temp_c": y.min_temp_c,
            "max_temp_c": y.max_temp_c,
            "attenuation_pct": y.attenuation_pct,
            "flocculation": y.flocculation,
            "best_for": y.best_for,
            "notes": y.notes,
        })

    miscs = []
    for m in db.query(Misc).all():
        miscs.append({
            "name": m.name,
            "type": m.type,
            "use_for": m.use_for,
            "notes": m.notes,
        })

    equipment = []
    for e in db.query(Equipment).all():
        equipment.append({
            "name": e.name,
            "batch_size_l": e.batch_size_l,
            "boil_size_l": e.boil_size_l,
            "boil_time_min": e.boil_time_min,
            "efficiency": e.efficiency,
            "hop_utilization": e.hop_utilization,
            "trub_chiller_loss_l": e.trub_chiller_loss_l,
            "lauter_deadspace_l": e.lauter_deadspace_l,
            "top_up_water_l": e.top_up_water_l,
            "notes": e.notes,
        })

    rig_profiles = []
    for r in db.query(RigProfile).all():
        rig_profiles.append({
            "name": r.name,
            "type": r.type,
            "description": r.description,
        })

    devices = []
    for d in db.query(Device).all():
        devices.append({
            "name": d.name,
            "device_key": d.device_key,
            "type": d.type,
            "role": d.role,
            "protocol": d.protocol,
            "config": d.config,
            "rig_name": d.rig.name if d.rig else None,
        })

    recipes = []
    for recipe in db.query(Recipe).all():
        ferms = []
        for rf in recipe.fermentables:
            ferms.append({
                "fermentable_name": rf.fermentable.name,
                "amount_kg": rf.amount_kg,
                "add_after_boil": rf.add_after_boil,
            })
        recipe_hops = []
        for rh in recipe.hops:
            recipe_hops.append({
                "hop_name": rh.hop.name,
                "amount_g": rh.amount_g,
                "time_min": rh.time_min,
                "use": rh.use,
                "form": rh.form,
            })
        recipe_yeasts = []
        for ry in recipe.yeasts:
            recipe_yeasts.append({
                "yeast_name": ry.yeast.name,
                "amount": ry.amount,
                "add_to_secondary": ry.add_to_secondary,
            })
        recipe_miscs = []
        for rm in recipe.miscs:
            recipe_miscs.append({
                "misc_name": rm.misc.name,
                "amount": rm.amount,
                "amount_is_weight": rm.amount_is_weight,
                "time_min": rm.time_min,
                "use": rm.use,
            })
        recipes.append({
            "name": recipe.name,
            "type": recipe.type,
            "style_name": recipe.style.name if recipe.style else None,
            "equipment_name": recipe.equipment.name if recipe.equipment else None,
            "batch_size_l": recipe.batch_size_l,
            "boil_size_l": recipe.boil_size_l,
            "boil_time_min": recipe.boil_time_min,
            "efficiency": recipe.efficiency,
            "og": recipe.og,
            "fg": recipe.fg,
            "abv": recipe.abv,
            "ibu": recipe.ibu,
            "color_srm": recipe.color_srm,
            "notes": recipe.notes,
            "brewer": recipe.brewer,
            "version": recipe.version,
            "created_at": _dt(recipe.created_at),
            "updated_at": _dt(recipe.updated_at),
            "fermentables": ferms,
            "hops": recipe_hops,
            "yeasts": recipe_yeasts,
            "miscs": recipe_miscs,
        })

    brew_programs = []
    for prog in db.query(BrewProgram).all():
        steps = []
        for step in prog.steps:
            commands = []
            for cmd in step.commands:
                commands.append({
                    "device_key": cmd.device.device_key if cmd.device else None,
                    "command": cmd.command,
                })
            steps.append({
                "step_number": step.step_number,
                "name": step.name,
                "description": step.description,
                "trigger_type": step.trigger_type,
                "trigger_value": step.trigger_value,
                "trigger_device_key": step.trigger_device.device_key if step.trigger_device else None,
                "commands": commands,
            })
        brew_programs.append({
            "name": prog.name,
            "description": prog.description,
            "recipe_name": prog.recipe.name if prog.recipe else None,
            "created_at": _dt(prog.created_at),
            "steps": steps,
        })

    brew_sessions = []
    for session in db.query(BrewSession).all():
        brew_sessions.append({
            "recipe_name": session.recipe.name if session.recipe else None,
            "status": session.status,
            "brew_date": _dt(session.brew_date),
            "package_date": _dt(session.package_date),
            "actual_og": session.actual_og,
            "actual_fg": session.actual_fg,
            "actual_abv": session.actual_abv,
            "actual_batch_size_l": session.actual_batch_size_l,
            "actual_efficiency": session.actual_efficiency,
            "ferment_temp_c": session.ferment_temp_c,
            "notes": session.notes,
            "created_at": _dt(session.created_at),
            "updated_at": _dt(session.updated_at),
        })

    return {
        "version": "1.0",
        "app": "Brewbot",
        "exported_at": datetime.utcnow().isoformat(),
        "fermentables": fermentables,
        "hops": hops,
        "yeasts": yeasts,
        "miscs": miscs,
        "equipment": equipment,
        "rig_profiles": rig_profiles,
        "devices": devices,
        "recipes": recipes,
        "brew_programs": brew_programs,
        "brew_sessions": brew_sessions,
    }


def import_all(db: Session, data: dict) -> dict:
    counts = {}

    # Fermentables
    created = 0
    for item in data.get("fermentables", []):
        name = item.get("name")
        if not name:
            continue
        if db.query(Fermentable).filter_by(name=name).first():
            continue
        db.add(Fermentable(
            name=name,
            type=item.get("type", "Grain"),
            origin=item.get("origin"),
            supplier=item.get("supplier"),
            color_srm=item.get("color_srm") or 0.0,
            potential=item.get("potential") or 1.037,
            yield_pct=item.get("yield_pct") or 75.0,
            moisture_pct=item.get("moisture_pct") or 4.0,
            diastatic_power=item.get("diastatic_power") or 0.0,
            protein_pct=item.get("protein_pct"),
            max_in_batch_pct=item.get("max_in_batch_pct"),
            add_after_boil=item.get("add_after_boil", False),
            recommend_mash=item.get("recommend_mash", True),
            notes=item.get("notes"),
        ))
        created += 1
    counts["fermentables"] = created

    # Hops
    created = 0
    for item in data.get("hops", []):
        name = item.get("name")
        if not name:
            continue
        if db.query(Hop).filter_by(name=name).first():
            continue
        db.add(Hop(
            name=name,
            origin=item.get("origin"),
            type=item.get("type"),
            alpha_pct=item.get("alpha_pct") or 0.0,
            beta_pct=item.get("beta_pct"),
            hsi=item.get("hsi"),
            caryophyllene_pct=item.get("caryophyllene_pct"),
            cohumulone_pct=item.get("cohumulone_pct"),
            myrcene_pct=item.get("myrcene_pct"),
            humulene_pct=item.get("humulene_pct"),
            notes=item.get("notes"),
            substitutes=item.get("substitutes"),
        ))
        created += 1
    counts["hops"] = created

    # Yeasts
    created = 0
    for item in data.get("yeasts", []):
        name = item.get("name")
        if not name:
            continue
        if db.query(Yeast).filter_by(name=name).first():
            continue
        db.add(Yeast(
            name=name,
            lab=item.get("lab"),
            product_id=item.get("product_id"),
            type=item.get("type"),
            form=item.get("form"),
            min_temp_c=item.get("min_temp_c"),
            max_temp_c=item.get("max_temp_c"),
            attenuation_pct=item.get("attenuation_pct") or 75.0,
            flocculation=item.get("flocculation"),
            best_for=item.get("best_for"),
            notes=item.get("notes"),
        ))
        created += 1
    counts["yeasts"] = created

    # Miscs
    created = 0
    for item in data.get("miscs", []):
        name = item.get("name")
        if not name:
            continue
        if db.query(Misc).filter_by(name=name).first():
            continue
        db.add(Misc(
            name=name,
            type=item.get("type"),
            use_for=item.get("use_for"),
            notes=item.get("notes"),
        ))
        created += 1
    counts["miscs"] = created

    # Equipment
    created = 0
    for item in data.get("equipment", []):
        name = item.get("name")
        if not name:
            continue
        if db.query(Equipment).filter_by(name=name).first():
            continue
        db.add(Equipment(
            name=name,
            batch_size_l=item.get("batch_size_l") or 19.0,
            boil_size_l=item.get("boil_size_l") or 23.0,
            boil_time_min=item.get("boil_time_min") or 60,
            efficiency=item.get("efficiency") or 75.0,
            hop_utilization=item.get("hop_utilization") or 100.0,
            trub_chiller_loss_l=item.get("trub_chiller_loss_l") or 1.0,
            lauter_deadspace_l=item.get("lauter_deadspace_l") or 0.0,
            top_up_water_l=item.get("top_up_water_l") or 0.0,
            notes=item.get("notes"),
        ))
        created += 1
    counts["equipment"] = created

    # Rig profiles
    created = 0
    for item in data.get("rig_profiles", []):
        name = item.get("name")
        if not name:
            continue
        if db.query(RigProfile).filter_by(name=name).first():
            continue
        db.add(RigProfile(
            name=name,
            type=item.get("type", "custom"),
            description=item.get("description"),
        ))
        created += 1
    counts["rig_profiles"] = created

    db.flush()

    # Devices
    created = 0
    for item in data.get("devices", []):
        device_key = item.get("device_key")
        if not device_key:
            continue
        if db.query(Device).filter_by(device_key=device_key).first():
            continue
        rig = None
        if item.get("rig_name"):
            rig = db.query(RigProfile).filter_by(name=item["rig_name"]).first()
        db.add(Device(
            name=item.get("name") or device_key,
            device_key=device_key,
            type=item.get("type", "temperature_sensor"),
            role=item.get("role"),
            protocol=item.get("protocol", "mqtt"),
            config=item.get("config") or {},
            rig_id=rig.id if rig else None,
        ))
        created += 1
    counts["devices"] = created

    db.flush()

    # Recipes
    created = 0
    for item in data.get("recipes", []):
        name = item.get("name")
        if not name:
            continue

        style = None
        if item.get("style_name"):
            style = db.query(Style).filter_by(name=item["style_name"]).first()

        equip = None
        if item.get("equipment_name"):
            equip = db.query(Equipment).filter_by(name=item["equipment_name"]).first()

        recipe = Recipe(
            name=name,
            type=item.get("type", "All Grain"),
            style_id=style.id if style else None,
            equipment_id=equip.id if equip else None,
            batch_size_l=item.get("batch_size_l") or 19.0,
            boil_size_l=item.get("boil_size_l"),
            boil_time_min=item.get("boil_time_min") or 60,
            efficiency=item.get("efficiency") or 75.0,
            notes=item.get("notes"),
            brewer=item.get("brewer"),
            version=item.get("version") or 1,
        )
        db.add(recipe)
        db.flush()

        for fitem in item.get("fermentables", []):
            fname = fitem.get("fermentable_name")
            if not fname:
                continue
            ferm = db.query(Fermentable).filter_by(name=fname).first()
            if not ferm:
                log.warning("import_all: fermentable %r not found, skipping", fname)
                continue
            db.add(RecipeFermentable(
                recipe_id=recipe.id,
                fermentable_id=ferm.id,
                amount_kg=fitem.get("amount_kg") or 0.0,
                add_after_boil=fitem.get("add_after_boil", False),
            ))

        for hitem in item.get("hops", []):
            hname = hitem.get("hop_name")
            if not hname:
                continue
            hop = db.query(Hop).filter_by(name=hname).first()
            if not hop:
                log.warning("import_all: hop %r not found, skipping", hname)
                continue
            db.add(RecipeHop(
                recipe_id=recipe.id,
                hop_id=hop.id,
                amount_g=hitem.get("amount_g") or 0.0,
                time_min=hitem.get("time_min") or 60,
                use=hitem.get("use", "Boil"),
                form=hitem.get("form", "Pellet"),
            ))

        for yitem in item.get("yeasts", []):
            yname = yitem.get("yeast_name")
            if not yname:
                continue
            yeast = db.query(Yeast).filter_by(name=yname).first()
            if not yeast:
                log.warning("import_all: yeast %r not found, skipping", yname)
                continue
            db.add(RecipeYeast(
                recipe_id=recipe.id,
                yeast_id=yeast.id,
                amount=yitem.get("amount") or 1.0,
                add_to_secondary=yitem.get("add_to_secondary", False),
            ))

        for mitem in item.get("miscs", []):
            mname = mitem.get("misc_name")
            if not mname:
                continue
            misc = db.query(Misc).filter_by(name=mname).first()
            if not misc:
                log.warning("import_all: misc %r not found, skipping", mname)
                continue
            db.add(RecipeMisc(
                recipe_id=recipe.id,
                misc_id=misc.id,
                amount=mitem.get("amount") or 0.0,
                amount_is_weight=mitem.get("amount_is_weight", True),
                time_min=mitem.get("time_min") or 0,
                use=mitem.get("use", "Boil"),
            ))

        db.flush()
        db.refresh(recipe)
        calc_service.calculate(recipe)
        created += 1
    counts["recipes"] = created

    db.flush()

    # Brew programs
    created = 0
    for item in data.get("brew_programs", []):
        name = item.get("name")
        if not name:
            continue

        recipe = None
        if item.get("recipe_name"):
            recipe = db.query(Recipe).filter_by(name=item["recipe_name"]).first()

        prog = BrewProgram(
            name=name,
            description=item.get("description"),
            recipe_id=recipe.id if recipe else None,
        )
        db.add(prog)
        db.flush()

        for sitem in item.get("steps", []):
            trigger_device = None
            if sitem.get("trigger_device_key"):
                trigger_device = db.query(Device).filter_by(device_key=sitem["trigger_device_key"]).first()

            step = BrewStep(
                program_id=prog.id,
                step_number=sitem.get("step_number") or 1,
                name=sitem.get("name") or "Step",
                description=sitem.get("description"),
                trigger_type=sitem.get("trigger_type", "manual"),
                trigger_value=sitem.get("trigger_value"),
                trigger_device_id=trigger_device.id if trigger_device else None,
            )
            db.add(step)
            db.flush()

            for citem in sitem.get("commands", []):
                dkey = citem.get("device_key")
                if not dkey:
                    continue
                device = db.query(Device).filter_by(device_key=dkey).first()
                if not device:
                    log.warning("import_all: device_key %r not found, skipping command", dkey)
                    continue
                db.add(BrewStepCommand(
                    step_id=step.id,
                    device_id=device.id,
                    command=citem.get("command", ""),
                ))

        created += 1
    counts["brew_programs"] = created

    # Brew sessions
    created = 0
    for item in data.get("brew_sessions", []):
        recipe_name = item.get("recipe_name")
        if not recipe_name:
            continue
        recipe = db.query(Recipe).filter_by(name=recipe_name).first()
        if not recipe:
            log.warning("import_all: recipe %r not found for brew session, skipping", recipe_name)
            continue

        session = BrewSession(
            recipe_id=recipe.id,
            status=item.get("status", "planned"),
            brew_date=item.get("brew_date"),
            package_date=item.get("package_date"),
            actual_og=item.get("actual_og"),
            actual_fg=item.get("actual_fg"),
            actual_abv=item.get("actual_abv"),
            actual_batch_size_l=item.get("actual_batch_size_l"),
            actual_efficiency=item.get("actual_efficiency"),
            ferment_temp_c=item.get("ferment_temp_c"),
            notes=item.get("notes"),
        )
        db.add(session)
        created += 1
    counts["brew_sessions"] = created

    db.commit()
    return counts
