# Brewbot

Brewbot is a craft beverage production management platform for beer, wine, and spirits. It covers the full production lifecycle: recipe formulation, mash scheduling, fermentation tracking, barrel aging management, winemaker lab logging, and hardware automation over MQTT — all from a self-hosted web interface.

---

## Quick start

```bash
docker compose up --build
```

Then visit [http://localhost:8000](http://localhost:8000).

The first startup applies all database migrations and seeds the ingredient library automatically.

---

## Platform setup

### Windows

1. Download and install **[Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)**.
2. During installation, choose the **WSL 2** backend when prompted (recommended). If you already have Docker Desktop installed, confirm WSL 2 is enabled under *Settings → General → Use the WSL 2 based engine*.
3. Open **PowerShell** or **Windows Terminal** and navigate to the project folder:
   ```powershell
   cd path\to\brewbot
   docker compose up --build
   ```
4. Visit [http://localhost:8000](http://localhost:8000).

> **Note:** Docker Desktop requires Windows 10 (version 1903 or later) or Windows 11. If prompted to install or update WSL 2, follow the link Docker provides — it is a one-time step.

### macOS

1. Download and install **[Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/)**.
2. Open **Terminal**, navigate to the project folder, and run:
   ```bash
   docker compose up --build
   ```
3. Visit [http://localhost:8000](http://localhost:8000).

### Linux

Docker Engine and Docker Compose are available via your distribution's package manager. On Debian/Ubuntu:

```bash
sudo apt update && sudo apt install docker.io docker-compose-plugin
sudo usermod -aG docker $USER   # allows running docker without sudo (re-login after)
```

Then:

```bash
docker compose up --build
```

---

## Features

### Recipe management
- **Multi-craft recipe builder** — Beer (All Grain / Extract / Partial Mash), Wine, and Spirits recipes in a single unified builder. Craft-specific sections (mash schedule, grape bill, still type) appear automatically.
- **Live stats** — OG, FG, ABV, IBU, and SRM calculated in real time as you build. Style gauge overlays show where your recipe sits within BJCP / competition targets.
- **Mash schedule** — step mash support with temperature, time, additions, and notes per step. Full metric/imperial unit toggle.
- **Ingredient library** — manage your own fermentable, hop, yeast, miscellaneous, and grape variety databases.
- **Equipment profiles** — save batch size, boil volume, boil time, and system efficiency per production setup. Auto-fills the recipe builder when selected.
- **Recipe scaler** — scale any recipe to a new batch size with optional efficiency adjustment. Saves as a new recipe; original is unchanged.
- **Import** — import recipes from BeerXML files.

### Production sessions
- **Brew sessions** — track each production run with actual OG, FG, ABV, and efficiency. ABV and efficiency auto-calculate from entered gravity readings.
- **Fermentation log** — time-series gravity, temperature, pH, titratable acidity (TA), free SO₂, and total SO₂ readings with an interactive chart.
- **Wine harvest intake** — record Brix, pH, TA, fruit weight, crush date, and source at intake. Displayed as a summary strip on the session.
- **MLF tracker** — log malolactic fermentation events (inoculation, test results, completion) with strain and temperature. Live status badge tracks progression.
- **Fining agent log** — record agent, rate (g/hL), volume treated, purpose, and notes. Total dose calculated automatically.

### Barrel aging
- **Barrel registry** — track barrel size, wood type, char level, previous contents, and status. SA:V (surface area-to-volume ratio) is calculated automatically and compared to a 53-gallon reference.
- **Aging rate calculator** — combines SA:V and storage temperature into a single aging multiplier using Arrhenius scaling. Small barrels and warm storage age proportionally faster.
- **Bad Motivator support** — stainless bain-marie setups with a wood lid or insert: enter actual wood contact area (with a built-in lid area calculator) to get an accurate SA:V.
- **Aging records** — link any production session to a barrel. Track days in barrel, 53-gallon equivalent months, and a target aging countdown.
- **Tasting entries** — log flavor notes, gravity, ABV, and color (SRM swatch) at each tasting pull.

### Wine tools
A dedicated calculator page (visible when craft is set to Wine) with:
- **SO₂ management** — molecular SO₂ from free SO₂ and pH, required free SO₂ for a target molecular level, and K₂S₂O₅ / Camden tablet dosing for a given volume.
- **SO₂ reference table** — free SO₂ targets at 0.8 ppm molecular across pH 2.9–4.0.
- **Acid adjustment** — tartaric, citric, or malic acid addition to hit a target TA; deacidification guidance for lowering TA.
- **Chaptalisation** — sugar or honey addition to reach a target Brix / potential ABV.

### Automation
- **Brew programs** — define ordered step sequences with manual, timer, temp-above, temp-below, and flow-volume trigger types. Assign device commands (open/close/on/off/setpoint) that fire when a step starts.
- **Session runner** — walk through a program step by step during production; commands are dispatched over MQTT automatically.
- **Controller** — register hardware devices (sensors, valves, pumps, heaters) with a device key. Live readings display on the dashboard via WebSocket.

### General
- **Dark mode** — full dark/light theme toggle, persisted per browser.
- **Unit toggle** — metric/imperial switch in the navbar. All volume, weight, temperature, and area fields convert throughout the UI. Server session keeps the preference consistent across pages.
- **Inventory** — track ingredient stock levels.
- **Unit converter** — standalone page for common brewing unit conversions.

---

## Tech stack

| Component | Technology |
|---|---|
| API & web server | FastAPI (Python) |
| Templating | Jinja2 + Bootstrap 5.3 |
| Database | PostgreSQL + SQLAlchemy |
| Migrations | Alembic |
| Message broker | Mosquitto MQTT |
| Frontend interactivity | HTMX + vanilla JS |
| Containerization | Docker Compose |

---

## Project structure

```
brewbot/
  app/
    models/         SQLAlchemy ORM models
    routes/         FastAPI route handlers (web.py HTML, api.py JSON)
    services/
      calc.py       Brewing math (OG, FG, ABV, IBU, SRM)
      mqtt.py       MQTT client and command dispatcher
    templates/      Jinja2 HTML templates
    static/         CSS and JS assets
    utils/
      units.py      Unit conversion helpers and Jinja2 filter registration
  alembic/          Database migration scripts (0001 → 0005)
  docs/             Hardware setup and protocol documentation
  docker-compose.yml
  Dockerfile
```

---

## Documentation

See the `docs/` folder for hardware and protocol details:

- [Raspberry Pi setup guide](docs/raspberry-pi-setup.md) — wiring, MQTT client script, systemd service
- [MQTT topic reference](docs/mqtt-topics.md) — topic names, payload formats, example flows
- [Brewing math reference](docs/brewing-math.md) — formulas used in `app/services/calc.py`
