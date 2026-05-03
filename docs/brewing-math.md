# Brewing Math Reference

This document describes the formulas used in `app/services/calc.py` to estimate recipe statistics. All calculations run server-side when a recipe is saved and also run client-side in the recipe builder JavaScript for live previews.

---

## Units

Internally, all quantities are stored in metric units:

- Grain / fermentable weights: **kilograms (kg)**
- Hop weights: **grams (g)**
- Volume: **liters (L)**

Calculations convert to US units as needed (pounds, ounces, gallons) to match the traditional homebrew formulas below.

---

## OG — Original Gravity

Original gravity is the density of the wort before fermentation, expressed as a specific gravity (e.g., 1.052).

### Formula

```
OG = 1.0 + (sum of gravity points) / 1000
```

For each fermentable:

```
gravity_points = PPG × weight_lbs × efficiency_factor / batch_gal
```

Where:

- **PPG** (points per pound per gallon) = `(potential_SG - 1.0) × 1000`
  - Example: a malt with potential 1.037 contributes 37 PPG
- **weight_lbs** = `amount_kg × 2.20462`
- **batch_gal** = `batch_size_l × 0.264172`
- **efficiency_factor**:
  - `= mash_efficiency / 100` for grains and adjuncts that go through the mash
  - `= 1.0` for `Sugar`, `Extract`, and `Dry Extract` types (they do not require mashing)
  - `= 1.0` if the ingredient is flagged as "add after boil"

---

## FG — Final Gravity

Final gravity is the density of the beer after fermentation.

### Formula

```
FG = 1.0 + (OG - 1.0) × (1.0 - attenuation / 100)
```

Where **attenuation** is the average `attenuation_pct` across all yeasts in the recipe. If no yeast is specified, a default of 75% is used.

---

## ABV — Alcohol by Volume

```
ABV (%) = (OG - FG) × 131.25
```

This is the simplified Balling / de Clerck formula. It is accurate to within ~0.2% ABV for typical homebrew gravities.

---

## IBU — Bitterness (Tinseth formula)

International Bitterness Units (IBUs) are calculated using the Tinseth formula, which accounts for wort gravity and boil time.

### Formula

For each hop addition (excluding Dry Hop; Aroma additions with time = 0 are also excluded):

```
bigness_factor  = 1.65 × 0.000125 ^ (OG - 1.0)
boil_factor     = (1 - e^(-0.04 × time_min)) / 4.15
utilization     = bigness_factor × boil_factor
```

If the hop form is **Pellet**, apply a 10% utilization bonus:

```
utilization × = 1.1
```

Then:

```
IBU_addition = (alpha_pct / 100) × utilization × weight_oz × 7489 / batch_gal
```

Where:
- `weight_oz` = `amount_g × 0.035274`
- For **First Wort** hop additions, `time_min` is set to the full boil time

Total IBU = sum of all hop additions.

---

## SRM — Color (Morey formula)

SRM (Standard Reference Method) measures beer color on a scale from roughly 2 (pale straw) to 40+ (black).

### Formula

First calculate MCU (Malt Color Units):

```
MCU = sum of (color_srm × weight_lbs / batch_gal) for each fermentable
```

Then apply the Morey formula:

```
SRM = 1.4922 × MCU ^ 0.6859
```

The Morey formula is more accurate than the simpler Daniels formula for dark beers.

---

## Notes on efficiency bypass

The following fermentable types bypass the mash efficiency calculation and are always treated as 100% efficient:

| Type | Reason |
|---|---|
| `Sugar` | Fully fermentable; no mash required |
| `Extract` | Pre-converted liquid malt extract |
| `Dry Extract` | Pre-converted dry malt extract |

Additionally, any fermentable flagged **Add After Boil** is treated at 100% efficiency because it is not subject to boil losses.
