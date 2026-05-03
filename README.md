# Brewbot

Brewbot is a homebrewing recipe and automation management system. It provides a web interface for building and scaling recipes, managing an ingredient library, designing step-by-step brew programs, and running an automated brew day with real-time hardware control over MQTT.

---

## Quick start

```bash
docker compose up --build
```

Then visit [http://localhost:8000](http://localhost:8000).

The first startup will apply database migrations and seed the ingredient library automatically.

---

## Features

- **Recipe builder** — build All Grain, Extract, or Partial Mash recipes with fermentables, hops, yeast, and miscellaneous additions. Live-calculated OG, FG, ABV, IBU, and SRM with style gauge overlays. Metric and imperial unit toggle.
- **Recipe scaler** — scale any recipe to a new batch size with optional efficiency adjustment. Saves as a new recipe; the original is unchanged.
- **Ingredient library** — manage your own fermentable, hop, yeast, and misc ingredient database with full CRUD.
- **Equipment profiles** — save batch size, boil volume, boil time, and system efficiency per brewing setup. Auto-fills the recipe builder when selected.
- **Brew programs** — define ordered automation sequences with manual, timer, temperature, and flow-volume trigger types. Assign device commands (open/close/on/off/setpoint) that fire when a step starts.
- **Brew sessions** — start a brew day session linked to a recipe and program. Walk through steps one at a time; device commands are dispatched over MQTT automatically.
- **Controller / MQTT** — register hardware devices (sensors, valves, pumps, heaters) with a device key. Brewbot publishes commands and subscribes to readings via the built-in Mosquitto broker.

---

## Tech stack

| Component | Technology |
|---|---|
| API & web server | FastAPI (Python) |
| Templating | Jinja2 + Bootstrap 5.3 |
| Database | PostgreSQL |
| Message broker | Mosquitto MQTT |
| Frontend interactivity | HTMX + vanilla JS |
| Containerization | Docker Compose |

---

## Project structure

```
brewbot/
  app/
    models/       SQLAlchemy ORM models (recipe, ingredient, device, session...)
    routes/       FastAPI route handlers (web.py for HTML, api.py for JSON)
    services/
      calc.py     Brewing math (OG, FG, ABV, IBU, SRM)
      mqtt.py     MQTT client and command dispatcher
    templates/    Jinja2 HTML templates
    static/       CSS and JS assets
  docs/           Hardware setup and protocol documentation
  docker-compose.yml
  Dockerfile
  alembic/        Database migration scripts
```

---

## Documentation

See the `docs/` folder for hardware and protocol details:

- [Raspberry Pi setup guide](docs/raspberry-pi-setup.md) — wiring, MQTT client script, systemd service
- [MQTT topic reference](docs/mqtt-topics.md) — topic names, payload formats, example flows
- [Brewing math reference](docs/brewing-math.md) — formulas used in `app/services/calc.py`
