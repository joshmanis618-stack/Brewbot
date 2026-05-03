"""BeerXML import/export for Brewbot recipes."""
import logging
import xml.etree.ElementTree as ET

from sqlalchemy.orm import Session

from app.models.fermentable import Fermentable
from app.models.hop import Hop
from app.models.misc import Misc
from app.models.recipe import Recipe, RecipeFermentable, RecipeHop, RecipeMisc, RecipeYeast
from app.models.style import Style
from app.models.equipment import Equipment
from app.models.yeast import Yeast
from app.services import calc as calc_service

log = logging.getLogger(__name__)


def _sub(parent: ET.Element, tag: str, text: str) -> ET.Element:
    el = ET.SubElement(parent, tag)
    el.text = str(text) if text is not None else ""
    return el


def _srm_to_lovibond(srm: float) -> float:
    return (srm + 0.76) / 1.3546


def _lovibond_to_srm(lovibond: float) -> float:
    return lovibond * 1.3546 - 0.76


def export_recipes(recipes: list) -> str:
    root = ET.Element("RECIPES")

    for recipe in recipes:
        rec_el = ET.SubElement(root, "RECIPE")
        _sub(rec_el, "NAME", recipe.name or "")
        _sub(rec_el, "VERSION", "1")
        _sub(rec_el, "TYPE", recipe.type or "All Grain")
        _sub(rec_el, "BREWER", recipe.brewer or "")
        _sub(rec_el, "BATCH_SIZE", str(recipe.batch_size_l or 0))
        _sub(rec_el, "BOIL_SIZE", str(recipe.boil_size_l or 0))
        _sub(rec_el, "BOIL_TIME", str(recipe.boil_time_min or 60))
        _sub(rec_el, "EFFICIENCY", str(recipe.efficiency or 75.0))
        _sub(rec_el, "OG", str(recipe.og or 0))
        _sub(rec_el, "FG", str(recipe.fg or 0))
        _sub(rec_el, "EST_ABV", str(recipe.abv or 0))
        _sub(rec_el, "EST_COLOR", str(recipe.color_srm or 0))
        _sub(rec_el, "IBU", str(recipe.ibu or 0))
        _sub(rec_el, "IBU_METHOD", "Tinseth")
        _sub(rec_el, "NOTES", recipe.notes or "")

        style_el = ET.SubElement(rec_el, "STYLE")
        style = recipe.style
        _sub(style_el, "NAME", style.name if style else "")
        _sub(style_el, "VERSION", "1")
        _sub(style_el, "CATEGORY", style.category if style else "")
        _sub(style_el, "CATEGORY_NUMBER", "0")
        _sub(style_el, "STYLE_LETTER", style.style_letter if style else "")
        _sub(style_el, "STYLE_GUIDE", style.style_guide if style else "")
        _sub(style_el, "TYPE", style.type if style else "Ale")
        _sub(style_el, "OG_MIN", str(style.og_min or 0) if style else "0")
        _sub(style_el, "OG_MAX", str(style.og_max or 0) if style else "0")
        _sub(style_el, "FG_MIN", str(style.fg_min or 0) if style else "0")
        _sub(style_el, "FG_MAX", str(style.fg_max or 0) if style else "0")
        _sub(style_el, "IBU_MIN", str(style.ibu_min or 0) if style else "0")
        _sub(style_el, "IBU_MAX", str(style.ibu_max or 0) if style else "0")
        _sub(style_el, "COLOR_MIN", str(style.color_min or 0) if style else "0")
        _sub(style_el, "COLOR_MAX", str(style.color_max or 0) if style else "0")

        ferms_el = ET.SubElement(rec_el, "FERMENTABLES")
        for rf in recipe.fermentables:
            f = rf.fermentable
            f_el = ET.SubElement(ferms_el, "FERMENTABLE")
            _sub(f_el, "NAME", f.name)
            _sub(f_el, "VERSION", "1")
            _sub(f_el, "TYPE", f.type or "Grain")
            _sub(f_el, "AMOUNT", str(rf.amount_kg or 0))
            _sub(f_el, "YIELD", str(f.yield_pct or 75.0))
            _sub(f_el, "COLOR", str(round(_srm_to_lovibond(f.color_srm or 0), 2)))
            _sub(f_el, "ADD_AFTER_BOIL", "TRUE" if rf.add_after_boil else "FALSE")
            _sub(f_el, "ORIGIN", f.origin or "")

        hops_el = ET.SubElement(rec_el, "HOPS")
        for rh in recipe.hops:
            h = rh.hop
            h_el = ET.SubElement(hops_el, "HOP")
            _sub(h_el, "NAME", h.name)
            _sub(h_el, "VERSION", "1")
            _sub(h_el, "ALPHA", str(h.alpha_pct or 0))
            _sub(h_el, "AMOUNT", str((rh.amount_g or 0) / 1000.0))
            _sub(h_el, "USE", rh.use or "Boil")
            _sub(h_el, "TIME", str(rh.time_min or 0))
            _sub(h_el, "FORM", rh.form or "Pellet")

        yeasts_el = ET.SubElement(rec_el, "YEASTS")
        for ry in recipe.yeasts:
            y = ry.yeast
            y_el = ET.SubElement(yeasts_el, "YEAST")
            _sub(y_el, "NAME", y.name)
            _sub(y_el, "VERSION", "1")
            _sub(y_el, "TYPE", y.type or "Ale")
            _sub(y_el, "FORM", y.form or "Dry")
            _sub(y_el, "AMOUNT", str(ry.amount or 0.5))
            _sub(y_el, "LABORATORY", y.lab or "")
            _sub(y_el, "PRODUCT_ID", y.product_id or "")
            _sub(y_el, "MIN_TEMPERATURE", str(y.min_temp_c or 0))
            _sub(y_el, "MAX_TEMPERATURE", str(y.max_temp_c or 0))
            _sub(y_el, "ATTENUATION", str(y.attenuation_pct or 75.0))

        miscs_el = ET.SubElement(rec_el, "MISCS")
        for rm in recipe.miscs:
            m = rm.misc
            m_el = ET.SubElement(miscs_el, "MISC")
            _sub(m_el, "NAME", m.name)
            _sub(m_el, "VERSION", "1")
            _sub(m_el, "TYPE", m.type or "Other")
            _sub(m_el, "USE", rm.use or "Boil")
            _sub(m_el, "TIME", str(rm.time_min or 0))
            _sub(m_el, "AMOUNT", str(rm.amount or 0))

        ET.SubElement(rec_el, "WATERS")

    ET.indent(root)
    xml_body = ET.tostring(root, encoding="unicode", xml_declaration=False)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_body


def _get_text(el: ET.Element, tag: str, default: str = "") -> str:
    child = el.find(tag)
    if child is None or child.text is None:
        return default
    return child.text.strip()


def import_recipes(xml_str: str, db: Session) -> list:
    root = ET.fromstring(xml_str)
    created_recipes = []

    for rec_el in root.findall("RECIPE"):
        recipe_name = _get_text(rec_el, "NAME")
        if not recipe_name:
            continue

        style_name = ""
        style_el = rec_el.find("STYLE")
        if style_el is not None:
            style_name = _get_text(style_el, "NAME")

        style = None
        if style_name:
            style = db.query(Style).filter(Style.name.ilike(style_name)).first()

        equip_name = _get_text(rec_el, "EQUIPMENT_NAME")
        equip = None
        if equip_name:
            equip = db.query(Equipment).filter_by(name=equip_name).first()

        recipe = Recipe(
            name=recipe_name,
            type=_get_text(rec_el, "TYPE", "All Grain"),
            style_id=style.id if style else None,
            equipment_id=equip.id if equip else None,
            batch_size_l=float(_get_text(rec_el, "BATCH_SIZE") or 0) or 19.0,
            boil_size_l=float(_get_text(rec_el, "BOIL_SIZE") or 0) or None,
            boil_time_min=int(float(_get_text(rec_el, "BOIL_TIME") or 60)),
            efficiency=float(_get_text(rec_el, "EFFICIENCY") or 75.0),
            notes=_get_text(rec_el, "NOTES") or None,
            brewer=_get_text(rec_el, "BREWER") or None,
        )
        db.add(recipe)
        db.flush()

        for f_el in rec_el.findall("./FERMENTABLES/FERMENTABLE"):
            fname = _get_text(f_el, "NAME")
            if not fname:
                continue
            ferm = db.query(Fermentable).filter_by(name=fname).first()
            if not ferm:
                lovibond = float(_get_text(f_el, "COLOR") or 0)
                srm = max(0.0, _lovibond_to_srm(lovibond))
                ferm = Fermentable(
                    name=fname,
                    type=_get_text(f_el, "TYPE", "Grain"),
                    origin=_get_text(f_el, "ORIGIN") or None,
                    color_srm=round(srm, 2),
                    yield_pct=float(_get_text(f_el, "YIELD") or 75.0),
                )
                db.add(ferm)
                db.flush()

            add_after_boil_str = _get_text(f_el, "ADD_AFTER_BOIL", "FALSE").upper()
            db.add(RecipeFermentable(
                recipe_id=recipe.id,
                fermentable_id=ferm.id,
                amount_kg=float(_get_text(f_el, "AMOUNT") or 0),
                add_after_boil=(add_after_boil_str == "TRUE"),
            ))

        for h_el in rec_el.findall("./HOPS/HOP"):
            hname = _get_text(h_el, "NAME")
            if not hname:
                continue
            hop = db.query(Hop).filter_by(name=hname).first()
            if not hop:
                hop = Hop(
                    name=hname,
                    origin=_get_text(h_el, "ORIGIN") or None,
                    alpha_pct=float(_get_text(h_el, "ALPHA") or 0),
                )
                db.add(hop)
                db.flush()

            amount_kg = float(_get_text(h_el, "AMOUNT") or 0)
            amount_g = amount_kg * 1000.0
            db.add(RecipeHop(
                recipe_id=recipe.id,
                hop_id=hop.id,
                amount_g=amount_g,
                time_min=int(float(_get_text(h_el, "TIME") or 60)),
                use=_get_text(h_el, "USE", "Boil"),
                form=_get_text(h_el, "FORM", "Pellet"),
            ))

        for y_el in rec_el.findall("./YEASTS/YEAST"):
            yname = _get_text(y_el, "NAME")
            if not yname:
                continue
            yeast = db.query(Yeast).filter_by(name=yname).first()
            if not yeast:
                yeast = Yeast(
                    name=yname,
                    lab=_get_text(y_el, "LABORATORY") or None,
                    product_id=_get_text(y_el, "PRODUCT_ID") or None,
                    type=_get_text(y_el, "TYPE", "Ale") or None,
                    form=_get_text(y_el, "FORM", "Dry") or None,
                    min_temp_c=float(_get_text(y_el, "MIN_TEMPERATURE") or 0) or None,
                    max_temp_c=float(_get_text(y_el, "MAX_TEMPERATURE") or 0) or None,
                    attenuation_pct=float(_get_text(y_el, "ATTENUATION") or 75.0),
                )
                db.add(yeast)
                db.flush()

            amount_raw = _get_text(y_el, "AMOUNT")
            amount = float(amount_raw) if amount_raw else 0.5
            db.add(RecipeYeast(
                recipe_id=recipe.id,
                yeast_id=yeast.id,
                amount=amount,
            ))

        for m_el in rec_el.findall("./MISCS/MISC"):
            mname = _get_text(m_el, "NAME")
            if not mname:
                continue
            misc = db.query(Misc).filter_by(name=mname).first()
            if not misc:
                misc = Misc(
                    name=mname,
                    type=_get_text(m_el, "TYPE") or None,
                )
                db.add(misc)
                db.flush()

            db.add(RecipeMisc(
                recipe_id=recipe.id,
                misc_id=misc.id,
                amount=float(_get_text(m_el, "AMOUNT") or 0),
                time_min=int(float(_get_text(m_el, "TIME") or 0)),
                use=_get_text(m_el, "USE", "Boil"),
            ))

        db.flush()
        db.refresh(recipe)
        calc_service.calculate(recipe)
        created_recipes.append(recipe)

    db.commit()
    return created_recipes
