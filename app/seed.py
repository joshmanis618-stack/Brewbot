"""Seed the database with default ingredients, styles, and equipment profiles.
Called once on startup; skips any category that already has rows.
"""
from sqlalchemy.orm import Session

from app.models.fermentable import Fermentable
from app.models.hop import Hop
from app.models.yeast import Yeast
from app.models.misc import Misc
from app.models.style import Style
from app.models.equipment import Equipment


def _seed_fermentables(db: Session) -> None:
    if db.query(Fermentable).count():
        return
    items = [
        # Base malts
        dict(name="American 2-Row", type="Grain", origin="US", color_srm=1.8, potential=1.037, yield_pct=79.0, recommend_mash=True),
        dict(name="American 6-Row", type="Grain", origin="US", color_srm=1.8, potential=1.035, yield_pct=73.0, recommend_mash=True),
        dict(name="Pilsner Malt", type="Grain", origin="Germany", color_srm=1.6, potential=1.036, yield_pct=75.0, recommend_mash=True),
        dict(name="Pale Ale Malt", type="Grain", origin="US", color_srm=3.5, potential=1.036, yield_pct=78.0, recommend_mash=True),
        dict(name="Munich Malt", type="Grain", origin="Germany", color_srm=9.0, potential=1.037, yield_pct=77.0, recommend_mash=True),
        dict(name="Vienna Malt", type="Grain", origin="Germany", color_srm=3.5, potential=1.035, yield_pct=75.0, recommend_mash=True),
        dict(name="White Wheat Malt", type="Grain", origin="Germany", color_srm=2.0, potential=1.040, yield_pct=86.0, recommend_mash=True),
        dict(name="Rye Malt", type="Grain", origin="US", color_srm=3.7, potential=1.029, yield_pct=63.0, recommend_mash=True),
        # Caramel/Crystal malts
        dict(name="Carapils (Dextrine)", type="Grain", origin="US", color_srm=1.5, potential=1.033, yield_pct=72.0, recommend_mash=True),
        dict(name="Honey Malt", type="Grain", origin="Canada", color_srm=18.0, potential=1.037, yield_pct=80.0, recommend_mash=True),
        dict(name="Crystal 20L", type="Grain", origin="US", color_srm=20.0, potential=1.035, yield_pct=74.0, recommend_mash=True),
        dict(name="Crystal 40L", type="Grain", origin="US", color_srm=40.0, potential=1.034, yield_pct=74.0, recommend_mash=True),
        dict(name="Crystal 60L", type="Grain", origin="US", color_srm=60.0, potential=1.034, yield_pct=74.0, recommend_mash=True),
        dict(name="Crystal 80L", type="Grain", origin="US", color_srm=80.0, potential=1.033, yield_pct=74.0, recommend_mash=True),
        dict(name="Crystal 120L", type="Grain", origin="US", color_srm=120.0, potential=1.033, yield_pct=72.0, recommend_mash=True),
        dict(name="Special B", type="Grain", origin="Belgium", color_srm=180.0, potential=1.030, yield_pct=65.0, recommend_mash=True),
        # Roasted malts
        dict(name="Chocolate Malt", type="Grain", origin="US", color_srm=350.0, potential=1.034, yield_pct=70.0, recommend_mash=True),
        dict(name="Black Patent Malt", type="Grain", origin="US", color_srm=500.0, potential=1.028, yield_pct=60.0, recommend_mash=True),
        dict(name="Roasted Barley", type="Grain", origin="US", color_srm=300.0, potential=1.025, yield_pct=55.0, recommend_mash=True),
        dict(name="Carafa III (Dehusked)", type="Grain", origin="Germany", color_srm=500.0, potential=1.028, yield_pct=60.0, recommend_mash=True),
        # Adjuncts
        dict(name="Flaked Oats", type="Grain", origin="US", color_srm=1.0, potential=1.037, yield_pct=70.0, recommend_mash=True),
        dict(name="Flaked Wheat", type="Grain", origin="US", color_srm=2.0, potential=1.036, yield_pct=77.0, recommend_mash=True),
        dict(name="Flaked Corn (Maize)", type="Grain", origin="US", color_srm=0.5, potential=1.037, yield_pct=75.0, recommend_mash=True),
        dict(name="Flaked Barley", type="Grain", origin="US", color_srm=2.2, potential=1.032, yield_pct=70.0, recommend_mash=True),
        dict(name="Rice Hulls", type="Adjunct", origin="US", color_srm=0.0, potential=1.000, yield_pct=0.0, recommend_mash=True, notes="Lautering aid; adds no fermentables"),
        # Sugars & extracts
        dict(name="Table Sugar (Sucrose)", type="Sugar", origin="US", color_srm=0.0, potential=1.046, yield_pct=100.0, recommend_mash=False, add_after_boil=False),
        dict(name="Corn Sugar (Dextrose)", type="Sugar", origin="US", color_srm=0.0, potential=1.046, yield_pct=100.0, recommend_mash=False),
        dict(name="Honey", type="Sugar", origin="US", color_srm=2.0, potential=1.035, yield_pct=75.0, recommend_mash=False),
        dict(name="Light Dry Malt Extract", type="Dry Extract", origin="US", color_srm=4.0, potential=1.044, yield_pct=95.0, recommend_mash=False),
        dict(name="Amber Dry Malt Extract", type="Dry Extract", origin="US", color_srm=10.0, potential=1.044, yield_pct=95.0, recommend_mash=False),
        dict(name="Light Liquid Malt Extract", type="Extract", origin="US", color_srm=4.0, potential=1.036, yield_pct=75.0, recommend_mash=False),
        dict(name="Amber Liquid Malt Extract", type="Extract", origin="US", color_srm=10.0, potential=1.035, yield_pct=75.0, recommend_mash=False),
        dict(name="Wheat Dry Malt Extract", type="Dry Extract", origin="US", color_srm=3.0, potential=1.044, yield_pct=95.0, recommend_mash=False),
    ]
    db.bulk_insert_mappings(Fermentable, items)
    db.commit()


def _seed_hops(db: Session) -> None:
    if db.query(Hop).count():
        return
    items = [
        # American hops
        dict(name="Cascade", origin="US", type="Both", alpha_pct=5.5, beta_pct=7.0, notes="Floral, citrus, grapefruit"),
        dict(name="Centennial", origin="US", type="Both", alpha_pct=10.0, beta_pct=4.5, notes="Citrus, floral, mild pine"),
        dict(name="Chinook", origin="US", type="Both", alpha_pct=13.0, beta_pct=3.5, notes="Pine, spice, mild citrus"),
        dict(name="Citra", origin="US", type="Both", alpha_pct=12.0, beta_pct=4.0, notes="Citrus, tropical fruit, melon"),
        dict(name="Columbus (CTZ)", origin="US", type="Bittering", alpha_pct=15.0, beta_pct=4.5, notes="Pungent, spicy, citrus"),
        dict(name="Amarillo", origin="US", type="Both", alpha_pct=9.5, beta_pct=6.0, notes="Orange, grapefruit, tropical"),
        dict(name="Simcoe", origin="US", type="Both", alpha_pct=13.0, beta_pct=4.5, notes="Pine, passionfruit, earthy"),
        dict(name="Mosaic", origin="US", type="Both", alpha_pct=12.5, beta_pct=3.5, notes="Tropical fruit, citrus, berry"),
        dict(name="Nugget", origin="US", type="Bittering", alpha_pct=13.0, beta_pct=4.5, notes="Heavy herbal, resin, spice"),
        dict(name="Willamette", origin="US", type="Aroma", alpha_pct=5.0, beta_pct=3.0, notes="Floral, spicy, earthy"),
        dict(name="Northern Brewer", origin="US", type="Both", alpha_pct=8.0, beta_pct=4.0, notes="Mint, pine, earthy"),
        dict(name="Cluster", origin="US", type="Both", alpha_pct=7.0, beta_pct=4.5, notes="Floral, earthy, spicy"),
        dict(name="Galaxy", origin="Australia", type="Both", alpha_pct=14.0, beta_pct=5.5, notes="Passionfruit, citrus, peach"),
        dict(name="El Dorado", origin="US", type="Both", alpha_pct=15.0, beta_pct=7.0, notes="Watermelon, pear, tropical"),
        dict(name="Idaho 7", origin="US", type="Both", alpha_pct=13.0, beta_pct=5.5, notes="Stone fruit, pine, black tea"),
        # European hops
        dict(name="Saaz", origin="Czech Republic", type="Aroma", alpha_pct=3.5, beta_pct=3.0, notes="Mild spice, floral, earthy"),
        dict(name="Hallertau Mittelfrüh", origin="Germany", type="Aroma", alpha_pct=4.5, beta_pct=4.0, notes="Mild floral, spicy, herbal"),
        dict(name="Hallertau Blanc", origin="Germany", type="Both", alpha_pct=10.0, beta_pct=5.0, notes="Gooseberry, passionfruit, grape"),
        dict(name="Tettnang", origin="Germany", type="Aroma", alpha_pct=4.5, beta_pct=3.5, notes="Fine spice, floral, earthy"),
        dict(name="Spalt", origin="Germany", type="Aroma", alpha_pct=4.0, beta_pct=4.0, notes="Mild, spicy, herbal"),
        dict(name="Magnum", origin="Germany", type="Bittering", alpha_pct=12.0, beta_pct=7.0, notes="Clean bittering, mild herbal"),
        dict(name="Perle", origin="Germany", type="Both", alpha_pct=8.0, beta_pct=4.0, notes="Mint, herbal, floral"),
        dict(name="East Kent Goldings", origin="UK", type="Aroma", alpha_pct=5.0, beta_pct=2.5, notes="Spicy, earthy, floral, honey"),
        dict(name="Fuggle", origin="UK", type="Aroma", alpha_pct=4.5, beta_pct=2.0, notes="Earthy, woody, soft fruit"),
        dict(name="Target", origin="UK", type="Bittering", alpha_pct=11.0, beta_pct=4.5, notes="Sage, herbal, citrus"),
        dict(name="Styrian Goldings", origin="Slovenia", type="Aroma", alpha_pct=5.5, beta_pct=3.5, notes="Spicy, herbal, earthy"),
        dict(name="Nelson Sauvin", origin="New Zealand", type="Both", alpha_pct=12.0, beta_pct=6.5, notes="White wine, grape, passionfruit"),
    ]
    db.bulk_insert_mappings(Hop, items)
    db.commit()


def _seed_yeasts(db: Session) -> None:
    if db.query(Yeast).count():
        return
    items = [
        # Dry ale yeasts
        dict(name="Safale US-05", lab="Fermentis", product_id="US-05", type="Ale", form="Dry", attenuation_pct=77.0, min_temp_c=15.0, max_temp_c=24.0, flocculation="Medium", best_for="American ales, IPAs, Pale Ales"),
        dict(name="Safale S-04", lab="Fermentis", product_id="S-04", type="Ale", form="Dry", attenuation_pct=75.0, min_temp_c=15.0, max_temp_c=24.0, flocculation="High", best_for="English ales, Bitters, Stouts"),
        dict(name="Safale BE-256", lab="Fermentis", product_id="BE-256", type="Ale", form="Dry", attenuation_pct=82.0, min_temp_c=15.0, max_temp_c=30.0, flocculation="High", best_for="Belgian strong ales, Abbey"),
        dict(name="Safale WB-06", lab="Fermentis", product_id="WB-06", type="Wheat", form="Dry", attenuation_pct=86.0, min_temp_c=18.0, max_temp_c=24.0, flocculation="Low", best_for="Wheat beers, Hefeweizens"),
        # Dry lager yeasts
        dict(name="Saflager W-34/70", lab="Fermentis", product_id="W-34/70", type="Lager", form="Dry", attenuation_pct=80.0, min_temp_c=9.0, max_temp_c=15.0, flocculation="High", best_for="German lagers, Pilsners"),
        dict(name="Saflager S-23", lab="Fermentis", product_id="S-23", type="Lager", form="Dry", attenuation_pct=81.0, min_temp_c=9.0, max_temp_c=15.0, flocculation="High", best_for="Lagers, Märzen"),
        # Wyeast ale
        dict(name="WY1056 American Ale", lab="Wyeast", product_id="1056", type="Ale", form="Liquid", attenuation_pct=77.0, min_temp_c=16.0, max_temp_c=22.0, flocculation="Low", best_for="American ales, clean fermentation"),
        dict(name="WY1068 West Coast Ale", lab="Wyeast", product_id="1068", type="Ale", form="Liquid", attenuation_pct=75.0, min_temp_c=18.0, max_temp_c=23.0, flocculation="Medium", best_for="West coast IPAs"),
        dict(name="WY1084 Irish Ale", lab="Wyeast", product_id="1084", type="Ale", form="Liquid", attenuation_pct=73.0, min_temp_c=16.0, max_temp_c=22.0, flocculation="Medium", best_for="Irish Stout, Porter"),
        dict(name="WY1272 American Ale II", lab="Wyeast", product_id="1272", type="Ale", form="Liquid", attenuation_pct=73.0, min_temp_c=16.0, max_temp_c=22.0, flocculation="High", best_for="American ales, Pale Ales"),
        dict(name="WY1318 London Ale III", lab="Wyeast", product_id="1318", type="Ale", form="Liquid", attenuation_pct=73.0, min_temp_c=17.0, max_temp_c=22.0, flocculation="High", best_for="English ales, Bitters, ESB"),
        dict(name="WY1968 London ESB", lab="Wyeast", product_id="1968", type="Ale", form="Liquid", attenuation_pct=67.0, min_temp_c=17.0, max_temp_c=22.0, flocculation="Very High", best_for="ESB, English ales"),
        dict(name="WY3068 Weihenstephan Weizen", lab="Wyeast", product_id="3068", type="Wheat", form="Liquid", attenuation_pct=75.0, min_temp_c=18.0, max_temp_c=24.0, flocculation="Low", best_for="Hefeweizen, Wheat"),
        dict(name="WY3787 Trappist High Gravity", lab="Wyeast", product_id="3787", type="Ale", form="Liquid", attenuation_pct=78.0, min_temp_c=18.0, max_temp_c=26.0, flocculation="Medium", best_for="Belgian Tripel, Dubbel, Quad"),
        dict(name="WY3944 Belgian Witbier", lab="Wyeast", product_id="3944", type="Wheat", form="Liquid", attenuation_pct=74.0, min_temp_c=17.0, max_temp_c=24.0, flocculation="Medium", best_for="Witbier, Belgian white"),
        # Wyeast lager
        dict(name="WY2124 Bohemian Lager", lab="Wyeast", product_id="2124", type="Lager", form="Liquid", attenuation_pct=75.0, min_temp_c=8.0, max_temp_c=14.0, flocculation="Medium", best_for="Czech Pils, Bohemian lager"),
        dict(name="WY2206 Bavarian Lager", lab="Wyeast", product_id="2206", type="Lager", form="Liquid", attenuation_pct=75.0, min_temp_c=8.0, max_temp_c=14.0, flocculation="Medium", best_for="Märzen, Bock, Munich lager"),
        # White Labs ale
        dict(name="WLP001 California Ale", lab="White Labs", product_id="WLP001", type="Ale", form="Liquid", attenuation_pct=76.0, min_temp_c=18.0, max_temp_c=23.0, flocculation="Medium", best_for="American ales, IPAs, clean ales"),
        dict(name="WLP004 Irish Ale", lab="White Labs", product_id="WLP004", type="Ale", form="Liquid", attenuation_pct=70.0, min_temp_c=18.0, max_temp_c=23.0, flocculation="Medium", best_for="Dry Irish Stout, Porter"),
        dict(name="WLP090 San Diego Super", lab="White Labs", product_id="WLP090", type="Ale", form="Liquid", attenuation_pct=80.0, min_temp_c=18.0, max_temp_c=23.0, flocculation="Medium", best_for="American IPA, West Coast Pale"),
        dict(name="WLP300 Hefeweizen Ale", lab="White Labs", product_id="WLP300", type="Wheat", form="Liquid", attenuation_pct=73.0, min_temp_c=18.0, max_temp_c=22.0, flocculation="Low", best_for="Hefeweizen, Dunkelweizen"),
        dict(name="WLP500 Monastery Ale", lab="White Labs", product_id="WLP500", type="Ale", form="Liquid", attenuation_pct=78.0, min_temp_c=18.0, max_temp_c=23.0, flocculation="Medium", best_for="Belgian Tripel, Dubbel, Golden Strong"),
        # White Labs lager
        dict(name="WLP800 Pilsner Lager", lab="White Labs", product_id="WLP800", type="Lager", form="Liquid", attenuation_pct=74.0, min_temp_c=10.0, max_temp_c=14.0, flocculation="Medium", best_for="Czech and German Pilsner"),
        dict(name="WLP830 German Lager", lab="White Labs", product_id="WLP830", type="Lager", form="Liquid", attenuation_pct=75.0, min_temp_c=10.0, max_temp_c=14.0, flocculation="Medium", best_for="Märzen, Bock, Helles"),
    ]
    db.bulk_insert_mappings(Yeast, items)
    db.commit()


def _seed_miscs(db: Session) -> None:
    if db.query(Misc).count():
        return
    items = [
        dict(name="Irish Moss", type="Fining", use_for="Boil fining — add 15 min before flameout to improve clarity"),
        dict(name="Whirlfloc Tablet", type="Fining", use_for="Boil fining — add 5–10 min before flameout"),
        dict(name="Gelatin", type="Fining", use_for="Cold-side fining — dissolve in warm water, add to cold fermenter"),
        dict(name="Bentonite", type="Fining", use_for="Fining for clarity, especially in wine and mead"),
        dict(name="Gypsum (CaSO4)", type="Water Agent", use_for="Sulfate addition — accentuates bitterness and dryness"),
        dict(name="Calcium Chloride (CaCl2)", type="Water Agent", use_for="Chloride addition — accentuates malt character and fullness"),
        dict(name="Epsom Salt (MgSO4)", type="Water Agent", use_for="Magnesium and sulfate addition"),
        dict(name="Baking Soda (NaHCO3)", type="Water Agent", use_for="Raises mash pH; adds alkalinity"),
        dict(name="Lactic Acid (88%)", type="Water Agent", use_for="Lowers mash/sparge pH"),
        dict(name="Phosphoric Acid (10%)", type="Water Agent", use_for="Lowers mash pH with no flavor impact"),
        dict(name="Campden Tablet (K-Meta)", type="Water Agent", use_for="Removes chloramine/chlorine from water; 1 tablet per 20 gal"),
        dict(name="Chalk (CaCO3)", type="Water Agent", use_for="Raises pH and adds calcium; use for dark beers"),
        dict(name="Priming Sugar", type="Other", use_for="Bottling carbonation — typically 4–5 oz per 5 gal batch"),
        dict(name="Yeast Nutrient", type="Other", use_for="Provides nutrients for healthy yeast fermentation"),
        dict(name="Acid Malt", type="Other", use_for="Naturally acidic malt used to adjust mash pH"),
        dict(name="Orange Peel (Sweet)", type="Flavor", use_for="Witbier, Belgian ales — add at flameout"),
        dict(name="Orange Peel (Bitter)", type="Flavor", use_for="Belgian ales — add last 5 min of boil"),
        dict(name="Coriander Seed", type="Spice", use_for="Witbier — add at flameout"),
        dict(name="Grains of Paradise", type="Spice", use_for="Belgian ales, Saison — add at flameout"),
        dict(name="Vanilla Bean", type="Flavor", use_for="Stout, Porter — add to secondary"),
        dict(name="Cacao Nibs", type="Flavor", use_for="Chocolate stout, Porter — add to secondary"),
        dict(name="Lactose (Milk Sugar)", type="Other", use_for="Milk stout, Sweet stout — unfermentable; add to boil"),
    ]
    db.bulk_insert_mappings(Misc, items)
    db.commit()


def _seed_styles(db: Session) -> None:
    if db.query(Style).count():
        return
    items = [
        # BJCP 2021 — major styles
        dict(name="American Light Lager", category="Standard American Beer", style_guide="BJCP 2021", style_letter="1A", type="Lager", og_min=1.028, og_max=1.040, fg_min=0.998, fg_max=1.008, ibu_min=8, ibu_max=12, color_min=2, color_max=3, abv_min=2.8, abv_max=4.2),
        dict(name="American Lager", category="Standard American Beer", style_guide="BJCP 2021", style_letter="1B", type="Lager", og_min=1.040, og_max=1.050, fg_min=1.004, fg_max=1.010, ibu_min=8, ibu_max=18, color_min=2, color_max=4, abv_min=4.2, abv_max=5.3),
        dict(name="Cream Ale", category="Standard American Beer", style_guide="BJCP 2021", style_letter="1C", type="Ale", og_min=1.042, og_max=1.055, fg_min=1.006, fg_max=1.012, ibu_min=8, ibu_max=20, color_min=2, color_max=5, abv_min=4.2, abv_max=5.6),
        dict(name="American Wheat Beer", category="Standard American Beer", style_guide="BJCP 2021", style_letter="1D", type="Ale", og_min=1.040, og_max=1.055, fg_min=1.008, fg_max=1.013, ibu_min=8, ibu_max=15, color_min=3, color_max=6, abv_min=4.0, abv_max=5.5),
        dict(name="International Pale Lager", category="International Lager", style_guide="BJCP 2021", style_letter="2A", type="Lager", og_min=1.042, og_max=1.050, fg_min=1.008, fg_max=1.012, ibu_min=18, ibu_max=25, color_min=2, color_max=6, abv_min=4.6, abv_max=6.0),
        dict(name="Munich Helles", category="Pale Malty European Lager", style_guide="BJCP 2021", style_letter="3A", type="Lager", og_min=1.044, og_max=1.048, fg_min=1.006, fg_max=1.012, ibu_min=16, ibu_max=22, color_min=3, color_max=5, abv_min=4.7, abv_max=5.4),
        dict(name="Festbier", category="Pale Malty European Lager", style_guide="BJCP 2021", style_letter="3B", type="Lager", og_min=1.054, og_max=1.057, fg_min=1.010, fg_max=1.014, ibu_min=18, ibu_max=25, color_min=4, color_max=7, abv_min=5.8, abv_max=6.3),
        dict(name="Czech Premium Pale Lager", category="Czech Lager", style_guide="BJCP 2021", style_letter="3C", type="Lager", og_min=1.044, og_max=1.060, fg_min=1.013, fg_max=1.017, ibu_min=30, ibu_max=45, color_min=3.5, color_max=6, abv_min=4.2, abv_max=5.8),
        dict(name="Munich Dunkel", category="Dark European Lager", style_guide="BJCP 2021", style_letter="8A", type="Lager", og_min=1.048, og_max=1.056, fg_min=1.010, fg_max=1.016, ibu_min=18, ibu_max=28, color_min=14, color_max=28, abv_min=4.5, abv_max=5.6),
        dict(name="Schwarzbier", category="Dark European Lager", style_guide="BJCP 2021", style_letter="8B", type="Lager", og_min=1.046, og_max=1.052, fg_min=1.010, fg_max=1.016, ibu_min=20, ibu_max=35, color_min=19, color_max=30, abv_min=4.4, abv_max=5.4),
        dict(name="Märzen", category="Amber Malty European Lager", style_guide="BJCP 2021", style_letter="6B", type="Lager", og_min=1.054, og_max=1.060, fg_min=1.010, fg_max=1.014, ibu_min=18, ibu_max=24, color_min=8, color_max=17, abv_min=5.8, abv_max=6.3),
        dict(name="Vienna Lager", category="Amber Malty European Lager", style_guide="BJCP 2021", style_letter="7A", type="Lager", og_min=1.048, og_max=1.055, fg_min=1.010, fg_max=1.014, ibu_min=18, ibu_max=30, color_min=9, color_max=15, abv_min=4.7, abv_max=5.5),
        dict(name="German Pils", category="Bitter European Beer", style_guide="BJCP 2021", style_letter="5D", type="Lager", og_min=1.044, og_max=1.050, fg_min=1.008, fg_max=1.013, ibu_min=22, ibu_max=40, color_min=2, color_max=5, abv_min=4.6, abv_max=5.3),
        dict(name="Traditional Bock", category="Bock", style_guide="BJCP 2021", style_letter="6C", type="Lager", og_min=1.064, og_max=1.072, fg_min=1.013, fg_max=1.019, ibu_min=20, ibu_max=27, color_min=14, color_max=22, abv_min=6.3, abv_max=7.2),
        dict(name="Doppelbock", category="Bock", style_guide="BJCP 2021", style_letter="9A", type="Lager", og_min=1.072, og_max=1.112, fg_min=1.016, fg_max=1.024, ibu_min=16, ibu_max=26, color_min=6, color_max=25, abv_min=7.0, abv_max=10.0),
        dict(name="Weizen/Weissbier", category="Wheat Beer", style_guide="BJCP 2021", style_letter="10A", type="Wheat", og_min=1.044, og_max=1.052, fg_min=1.010, fg_max=1.014, ibu_min=8, ibu_max=15, color_min=2, color_max=6, abv_min=4.3, abv_max=5.6),
        dict(name="Dunkles Weissbier", category="Wheat Beer", style_guide="BJCP 2021", style_letter="10B", type="Wheat", og_min=1.044, og_max=1.056, fg_min=1.010, fg_max=1.014, ibu_min=10, ibu_max=18, color_min=14, color_max=23, abv_min=4.3, abv_max=5.6),
        dict(name="Ordinary Bitter", category="British Bitter", style_guide="BJCP 2021", style_letter="11A", type="Ale", og_min=1.030, og_max=1.039, fg_min=1.007, fg_max=1.011, ibu_min=25, ibu_max=35, color_min=8, color_max=14, abv_min=3.2, abv_max=3.8),
        dict(name="Best Bitter", category="British Bitter", style_guide="BJCP 2021", style_letter="11B", type="Ale", og_min=1.040, og_max=1.048, fg_min=1.008, fg_max=1.012, ibu_min=25, ibu_max=40, color_min=8, color_max=16, abv_min=3.8, abv_max=4.6),
        dict(name="Extra Special Bitter", category="British Bitter", style_guide="BJCP 2021", style_letter="11C", type="Ale", og_min=1.048, og_max=1.060, fg_min=1.010, fg_max=1.016, ibu_min=30, ibu_max=50, color_min=8, color_max=18, abv_min=4.6, abv_max=6.2),
        dict(name="British Golden Ale", category="Pale British Beer", style_guide="BJCP 2021", style_letter="12A", type="Ale", og_min=1.038, og_max=1.053, fg_min=1.006, fg_max=1.012, ibu_min=20, ibu_max=45, color_min=2, color_max=6, abv_min=3.8, abv_max=5.0),
        dict(name="British IPA", category="Pale British Beer", style_guide="BJCP 2021", style_letter="12C", type="Ale", og_min=1.050, og_max=1.075, fg_min=1.010, fg_max=1.018, ibu_min=40, ibu_max=60, color_min=6, color_max=14, abv_min=5.0, abv_max=7.5),
        dict(name="Irish Red Ale", category="Irish Beer", style_guide="BJCP 2021", style_letter="15A", type="Ale", og_min=1.036, og_max=1.046, fg_min=1.010, fg_max=1.014, ibu_min=18, ibu_max=28, color_min=9, color_max=14, abv_min=3.8, abv_max=5.0),
        dict(name="Dry Irish Stout", category="Irish Beer", style_guide="BJCP 2021", style_letter="15B", type="Ale", og_min=1.036, og_max=1.044, fg_min=1.007, fg_max=1.011, ibu_min=25, ibu_max=45, color_min=25, color_max=40, abv_min=4.0, abv_max=5.0),
        dict(name="Sweet Stout", category="Dark British Beer", style_guide="BJCP 2021", style_letter="16A", type="Ale", og_min=1.044, og_max=1.060, fg_min=1.012, fg_max=1.024, ibu_min=20, ibu_max=40, color_min=30, color_max=40, abv_min=4.0, abv_max=6.0),
        dict(name="Oatmeal Stout", category="Dark British Beer", style_guide="BJCP 2021", style_letter="16B", type="Ale", og_min=1.045, og_max=1.065, fg_min=1.010, fg_max=1.018, ibu_min=25, ibu_max=40, color_min=22, color_max=40, abv_min=4.2, abv_max=5.9),
        dict(name="Blonde Ale", category="Pale American Ale", style_guide="BJCP 2021", style_letter="18A", type="Ale", og_min=1.038, og_max=1.054, fg_min=1.008, fg_max=1.013, ibu_min=15, ibu_max=28, color_min=3, color_max=6, abv_min=3.8, abv_max=5.5),
        dict(name="American Pale Ale", category="Pale American Ale", style_guide="BJCP 2021", style_letter="18B", type="Ale", og_min=1.045, og_max=1.060, fg_min=1.010, fg_max=1.015, ibu_min=30, ibu_max=50, color_min=5, color_max=10, abv_min=4.5, abv_max=6.2),
        dict(name="American Amber Ale", category="Amber and Brown American Beer", style_guide="BJCP 2021", style_letter="19A", type="Ale", og_min=1.045, og_max=1.060, fg_min=1.010, fg_max=1.015, ibu_min=25, ibu_max=40, color_min=10, color_max=17, abv_min=4.5, abv_max=6.2),
        dict(name="American Brown Ale", category="Amber and Brown American Beer", style_guide="BJCP 2021", style_letter="19C", type="Ale", og_min=1.045, og_max=1.060, fg_min=1.010, fg_max=1.016, ibu_min=20, ibu_max=30, color_min=18, color_max=35, abv_min=4.3, abv_max=6.2),
        dict(name="American Stout", category="American Porter and Stout", style_guide="BJCP 2021", style_letter="20B", type="Ale", og_min=1.050, og_max=1.075, fg_min=1.010, fg_max=1.022, ibu_min=35, ibu_max=75, color_min=30, color_max=40, abv_min=5.0, abv_max=7.0),
        dict(name="American IPA", category="IPA", style_guide="BJCP 2021", style_letter="21A", type="Ale", og_min=1.056, og_max=1.070, fg_min=1.008, fg_max=1.014, ibu_min=40, ibu_max=70, color_min=6, color_max=14, abv_min=5.5, abv_max=7.5),
        dict(name="Specialty IPA: New England IPA", category="IPA", style_guide="BJCP 2021", style_letter="21B", type="Ale", og_min=1.060, og_max=1.085, fg_min=1.010, fg_max=1.015, ibu_min=25, ibu_max=60, color_min=3, color_max=7, abv_min=6.0, abv_max=9.0),
        dict(name="Double IPA", category="Strong American Ale", style_guide="BJCP 2021", style_letter="22A", type="Ale", og_min=1.065, og_max=1.085, fg_min=1.008, fg_max=1.018, ibu_min=60, ibu_max=120, color_min=6, color_max=14, abv_min=7.5, abv_max=10.0),
        dict(name="American Strong Ale", category="Strong American Ale", style_guide="BJCP 2021", style_letter="22B", type="Ale", og_min=1.062, og_max=1.090, fg_min=1.014, fg_max=1.024, ibu_min=50, ibu_max=100, color_min=7, color_max=19, abv_min=6.3, abv_max=10.0),
        dict(name="American Barleywine", category="Strong American Ale", style_guide="BJCP 2021", style_letter="22C", type="Ale", og_min=1.080, og_max=1.120, fg_min=1.016, fg_max=1.030, ibu_min=50, ibu_max=100, color_min=10, color_max=19, abv_min=8.0, abv_max=12.0),
        dict(name="Witbier", category="Belgian Ale", style_guide="BJCP 2021", style_letter="24A", type="Wheat", og_min=1.044, og_max=1.052, fg_min=1.008, fg_max=1.012, ibu_min=8, ibu_max=20, color_min=2, color_max=4, abv_min=4.5, abv_max=5.5),
        dict(name="Saison", category="Belgian Ale", style_guide="BJCP 2021", style_letter="25B", type="Ale", og_min=1.048, og_max=1.065, fg_min=1.002, fg_max=1.008, ibu_min=20, ibu_max=35, color_min=5, color_max=14, abv_min=5.0, abv_max=7.0),
        dict(name="Belgian Golden Strong Ale", category="Strong Belgian Ale", style_guide="BJCP 2021", style_letter="25C", type="Ale", og_min=1.070, og_max=1.095, fg_min=1.005, fg_max=1.016, ibu_min=22, ibu_max=35, color_min=3, color_max=6, abv_min=7.5, abv_max=10.5),
        dict(name="American Porter", category="Porter", style_guide="BJCP 2021", style_letter="20A", type="Ale", og_min=1.050, og_max=1.070, fg_min=1.012, fg_max=1.018, ibu_min=25, ibu_max=50, color_min=22, color_max=40, abv_min=4.8, abv_max=6.5),
        dict(name="Russian Imperial Stout", category="American Porter and Stout", style_guide="BJCP 2021", style_letter="20C", type="Ale", og_min=1.075, og_max=1.115, fg_min=1.018, fg_max=1.030, ibu_min=50, ibu_max=90, color_min=30, color_max=40, abv_min=8.0, abv_max=12.0),
    ]
    db.bulk_insert_mappings(Style, items)
    db.commit()


def _seed_equipment(db: Session) -> None:
    if db.query(Equipment).count():
        return
    items = [
        dict(name="5 Gallon All-Grain", batch_size_l=19.0, boil_size_l=26.0, boil_time_min=60, efficiency=72.0, trub_chiller_loss_l=1.9, notes="Standard 5-gallon all-grain system"),
        dict(name="5 Gallon BIAB", batch_size_l=19.0, boil_size_l=28.0, boil_time_min=60, efficiency=68.0, trub_chiller_loss_l=1.9, notes="Brew-in-a-bag, single vessel"),
        dict(name="5 Gallon Extract", batch_size_l=19.0, boil_size_l=19.0, boil_time_min=60, efficiency=95.0, trub_chiller_loss_l=1.9, notes="Extract brewing; fill to 19L post-boil"),
        dict(name="3 Gallon Small Batch", batch_size_l=11.0, boil_size_l=15.0, boil_time_min=60, efficiency=70.0, trub_chiller_loss_l=1.0, notes="Small-batch / countertop system"),
        dict(name="10 Gallon All-Grain", batch_size_l=38.0, boil_size_l=50.0, boil_time_min=60, efficiency=72.0, trub_chiller_loss_l=3.8, notes="10-gallon two-tier or three-tier system"),
        dict(name="1 BBL (31 gal) Pilot", batch_size_l=117.0, boil_size_l=150.0, boil_time_min=60, efficiency=78.0, trub_chiller_loss_l=8.0, notes="1-barrel pilot / nano brewery"),
    ]
    db.bulk_insert_mappings(Equipment, items)
    db.commit()


def run(db: Session) -> None:
    _seed_fermentables(db)
    _seed_hops(db)
    _seed_yeasts(db)
    _seed_miscs(db)
    _seed_styles(db)
    _seed_equipment(db)
