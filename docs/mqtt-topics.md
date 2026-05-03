# MQTT Topic Reference

Brewbot uses a simple, flat topic hierarchy under the `brewbot/` prefix. All messages are exchanged between the Brewbot server and hardware clients (typically a Raspberry Pi running a controller script).

The Mosquitto broker is included in the Docker Compose stack and listens on port **1883** (plaintext).

---

## Topic structure

```
brewbot/{device_key}/{direction}
```

- `{device_key}` — a short, unique identifier for the device. Set when registering the device in the Brewbot UI. Use lowercase letters, digits, and underscores only.
- `{direction}` — one of `reading`, `command`, or `state`.

---

## Topics

### `brewbot/{device_key}/reading`

**Direction:** hardware → Brewbot server

Published by the hardware client to report a sensor measurement.

**Payload:** JSON object

```json
{"value": 65.3, "unit": "C"}
```

| Field | Type | Description |
|---|---|---|
| `value` | number | The measured value |
| `unit` | string | Unit of measurement: `"C"` for Celsius, `"F"` for Fahrenheit, `"L"` for liters, etc. |

**Example topics:**
- `brewbot/hlt_temp/reading` — HLT temperature sensor
- `brewbot/mlt_temp/reading` — mash tun temperature sensor
- `brewbot/flow_meter/reading` — flow meter volume

---

### `brewbot/{device_key}/command`

**Direction:** Brewbot server → hardware

Published by Brewbot when a brew step starts and has device commands configured, or when a user sends a manual command from the Controller page.

**Payload:** plain string (not JSON)

| Payload | Applies to | Meaning |
|---|---|---|
| `open` | Valve | Open the solenoid valve |
| `close` | Valve | Close the solenoid valve |
| `on` | Pump, Heater | Turn the device on |
| `off` | Pump, Heater | Turn the device off |
| `setpoint:NNN` | Heater | Set the temperature target to NNN degrees (e.g., `setpoint:68.5`) |

**Example topics:**
- `brewbot/hlt_valve/command`
- `brewbot/transfer_pump/command`
- `brewbot/hlt_heater/command`

---

### `brewbot/{device_key}/state`

**Direction:** hardware → Brewbot server

Published by the hardware client to confirm that a command was received and acted upon. Brewbot uses this to update the device's displayed state in the UI.

**Payload:** plain string

| Payload | Meaning |
|---|---|
| `open` | Valve confirmed open |
| `closed` | Valve confirmed closed |
| `on` | Device confirmed on |
| `off` | Device confirmed off |

---

## Device key naming conventions

Use descriptive, vessel-scoped names. Examples:

| Device | Suggested key |
|---|---|
| HLT temperature sensor | `hlt_temp` |
| Mash tun temperature sensor | `mlt_temp` |
| Boil kettle temperature sensor | `bk_temp` |
| HLT inlet solenoid valve | `hlt_valve` |
| Mash tun outlet valve | `mlt_valve` |
| Transfer (wort) pump | `transfer_pump` |
| Hot liquor recirculation pump | `hlt_pump` |
| HLT heating element controller | `hlt_heater` |
| Fermentation fridge temperature | `ferm_temp` |
| Flow meter on sparge line | `sparge_flow` |

---

## Example flow: brew step opens the HLT valve

1. The brewer clicks **Start Step** on the "Fill HLT" step in the Brew Day runner.
2. Brewbot looks up the commands attached to that step. It finds: device `hlt_valve`, command `open`.
3. Brewbot publishes `open` to `brewbot/hlt_valve/command`.
4. The Raspberry Pi, subscribed to that topic, receives the message and energizes the relay for GPIO pin wired to the HLT valve.
5. The Pi publishes `open` to `brewbot/hlt_valve/state`.
6. Brewbot receives the state confirmation and updates the device card in the UI to show "open."
7. When the HLT is full (timer or flow trigger), the next step starts with a `close` command on `hlt_valve`.
