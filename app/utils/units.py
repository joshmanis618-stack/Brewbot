"""
Unit conversion utilities.  All DB values are metric.
These helpers convert for display and parse form inputs back to metric.
"""

# ── Conversion constants ──────────────────────────────────────────────────────
L_PER_GAL = 3.785412
GAL_PER_L = 1.0 / L_PER_GAL
CM2_PER_IN2 = 6.4516
IN2_PER_CM2 = 1.0 / CM2_PER_IN2


# ── Display: metric → user units ─────────────────────────────────────────────

def disp_vol(val_l, units, decimals=2):
    """Liters → display value (gal if imperial, else unchanged)."""
    if val_l is None:
        return None
    v = val_l * GAL_PER_L if units == 'imperial' else float(val_l)
    return round(v, decimals)


def disp_temp(val_c, units, decimals=1):
    """°C → display value (°F if imperial, else unchanged)."""
    if val_c is None:
        return None
    v = val_c * 9.0 / 5.0 + 32.0 if units == 'imperial' else float(val_c)
    return round(v, decimals)


def disp_area(val_cm2, units, decimals=1):
    """cm² → display value (in² if imperial, else unchanged)."""
    if val_cm2 is None:
        return None
    v = val_cm2 * IN2_PER_CM2 if units == 'imperial' else float(val_cm2)
    return round(v, decimals)


# ── Parse: form input → metric ───────────────────────────────────────────────

def parse_vol(val_str, units):
    """Form volume string → liters."""
    if not val_str:
        return None
    v = float(val_str)
    return v * L_PER_GAL if units == 'imperial' else v


def parse_temp(val_str, units):
    """Form temperature string → °C."""
    if not val_str:
        return None
    v = float(val_str)
    return (v - 32.0) * 5.0 / 9.0 if units == 'imperial' else v


def parse_area(val_str, units):
    """Form area string → cm²."""
    if not val_str:
        return None
    v = float(val_str)
    return v * CM2_PER_IN2 if units == 'imperial' else v


# ── Unit label strings ────────────────────────────────────────────────────────

def vol_unit(units):   return 'gal' if units == 'imperial' else 'L'
def temp_unit(units):  return '°F'  if units == 'imperial' else '°C'
def area_unit(units):  return 'in²' if units == 'imperial' else 'cm²'
def sav_unit(units):   return 'in²/gal' if units == 'imperial' else 'cm²/L'


# ── Reference SA:V in the user's display unit ─────────────────────────────────

def ref_sav(units):
    """53-gallon reference SA:V in the display unit (75 cm²/L or ~44 in²/gal)."""
    return round(75.0 * IN2_PER_CM2 / GAL_PER_L, 1) if units == 'imperial' else 75.0


# ── Jinja2 filter/global registration helper ─────────────────────────────────

def register(jinja_env):
    """Register all filters and globals onto a Jinja2 Environment."""
    jinja_env.filters.update({
        'disp_vol':  lambda v, u: disp_vol(v, u),
        'disp_temp': lambda v, u: disp_temp(v, u),
        'disp_area': lambda v, u: disp_area(v, u),
    })
    jinja_env.globals.update({
        'vol_unit':  vol_unit,
        'temp_unit': temp_unit,
        'area_unit': area_unit,
        'sav_unit':  sav_unit,
        'ref_sav':   ref_sav,
    })
