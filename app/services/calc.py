"""Brewing math: OG, FG, ABV, IBU (Tinseth), SRM (Morey)."""
import math
from app.models.recipe import Recipe


_KG_TO_LB = 2.20462
_L_TO_GAL = 0.264172
_G_TO_OZ = 0.035274


def calculate(recipe: Recipe) -> None:
    """Compute and write og/fg/abv/ibu/color_srm onto *recipe* in-place."""
    batch_gal = (recipe.batch_size_l or 19.0) * _L_TO_GAL
    efficiency = (recipe.efficiency or 75.0) / 100.0
    boil_min = recipe.boil_time_min or 60

    og = _calc_og(recipe, batch_gal, efficiency)
    fg = _calc_fg(recipe, og)
    abv = round((og - fg) * 131.25, 2)
    ibu = _calc_ibu(recipe, og, batch_gal, boil_min)
    srm = _calc_srm(recipe, batch_gal)

    recipe.og = round(og, 4)
    recipe.fg = round(fg, 4)
    recipe.abv = abv
    recipe.ibu = round(ibu, 1)
    recipe.color_srm = round(srm, 1)


def _calc_og(recipe: Recipe, batch_gal: float, efficiency: float) -> float:
    points = 0.0
    for rf in recipe.fermentables:
        f = rf.fermentable
        lbs = rf.amount_kg * _KG_TO_LB
        ppg = (f.potential - 1.0) * 1000.0  # points per pound per gallon
        # Sugars, extracts, and add-after-boil items don't go through mash
        if f.type in ("Sugar", "Extract", "Dry Extract") or rf.add_after_boil:
            eff = 1.0
        else:
            eff = efficiency
        points += ppg * lbs * eff / batch_gal
    return 1.0 + points / 1000.0


def _calc_fg(recipe: Recipe, og: float) -> float:
    if recipe.yeasts:
        attenuation = sum(ry.yeast.attenuation_pct for ry in recipe.yeasts) / len(recipe.yeasts)
    else:
        attenuation = 75.0
    return 1.0 + (og - 1.0) * (1.0 - attenuation / 100.0)


def _calc_ibu(recipe: Recipe, og: float, batch_gal: float, boil_min: int) -> float:
    total = 0.0
    for rh in recipe.hops:
        use = rh.use
        if use == "Dry Hop":
            continue
        if use == "Aroma" and rh.time_min == 0:
            continue

        time = boil_min if use == "First Wort" else rh.time_min
        bigness = 1.65 * (0.000125 ** (og - 1.0))
        boil_factor = (1.0 - math.exp(-0.04 * time)) / 4.15
        utilization = bigness * boil_factor
        if rh.form == "Pellet":
            utilization *= 1.1

        oz = rh.amount_g * _G_TO_OZ
        total += (rh.hop.alpha_pct / 100.0) * utilization * oz * 7489.0 / batch_gal
    return total


def _calc_srm(recipe: Recipe, batch_gal: float) -> float:
    mcu = 0.0
    for rf in recipe.fermentables:
        lbs = rf.amount_kg * _KG_TO_LB
        mcu += rf.fermentable.color_srm * lbs / batch_gal
    if mcu <= 0:
        return 0.0
    return 1.4922 * (mcu ** 0.6859)
