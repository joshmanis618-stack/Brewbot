#!/usr/bin/env python3
"""
Brewbot Pi Controller
=====================
Runs on a Raspberry Pi (tested on Pi 4/5) and bridges GPIO hardware
to the Brewbot MQTT broker.

Supports:
  - DS18B20 temperature sensors (1-wire, any number)
  - Relay-controlled outputs: heaters, pumps, motorized valves, gas solenoids

HARDWARE SETUP (Pi 5):
  DS18B20:
    VCC  → 3.3V pin (pin 1)
    GND  → GND (pin 6)
    DATA → GPIO4 (pin 7)  + 4.7kΩ resistor between DATA and VCC
    Enable 1-wire: add  dtoverlay=w1-gpio  to /boot/firmware/config.txt
    then reboot.

  Relay board (active-low, common type):
    VCC  → 5V  (pin 2)
    GND  → GND (pin 6)
    IN1  → GPIO17  (heater / SSR / gas solenoid)
    IN2  → GPIO27  (pump)
    IN3  → GPIO22  (valve 1 — HLT→MLT)
    IN4  → GPIO23  (valve 2 — MLT→BK)
    IN5  → GPIO24  (valve 3 — spare)
    IN6  → GPIO25  (valve 4 — spare)

  Motorized ball valve (12V, 3-wire: open/close/common):
    Use two relay channels per valve — one for open, one for close.
    Never energise both simultaneously (add a small delay between).

INSTALL:
  See install.sh in this directory.

CONFIGURATION:
  Edit the DEVICES section below, or set environment variables.
  Required env vars:
    BREWBOT_MQTT_HOST  — IP/hostname of your Brewbot server  (default: 192.168.1.100)
    BREWBOT_MQTT_PORT  — MQTT broker port                    (default: 1883)
"""

import glob
import json
import logging
import os
import signal
import time
import threading
from dataclasses import dataclass, field
from typing import Optional

import paho.mqtt.client as mqtt

# ── Configuration ─────────────────────────────────────────────────────────────

MQTT_HOST = os.getenv("BREWBOT_MQTT_HOST", "192.168.1.100")
MQTT_PORT = int(os.getenv("BREWBOT_MQTT_PORT", "1883"))
READ_INTERVAL = int(os.getenv("BREWBOT_READ_INTERVAL", "30"))  # seconds

# ── Device definitions ────────────────────────────────────────────────────────
# Edit this section to match your wiring.
# Each relay pin is BCM-numbered.
# active_low=True for the common blue relay boards (IN pulled LOW to activate).

@dataclass
class TempSensor:
    device_key: str          # must be unique across all Brewbot devices
    name: str
    w1_id: str               # e.g. "28-0123456789ab"  (find in /sys/bus/w1/devices/)
    unit: str = "C"


@dataclass
class RelayOutput:
    device_key: str
    name: str
    pin: int                 # BCM pin number
    device_type: str = "relay"   # heater | pump | valve | gas_solenoid
    active_low: bool = True  # True = most hobby relay boards


TEMP_SENSORS: list[TempSensor] = [
    TempSensor("hlt_temp",  "HLT Temperature",  w1_id="28-REPLACE_HLT"),
    TempSensor("mlt_temp",  "MLT Temperature",  w1_id="28-REPLACE_MLT"),
    TempSensor("bk_temp",   "BK Temperature",   w1_id="28-REPLACE_BK"),
]

RELAY_OUTPUTS: list[RelayOutput] = [
    RelayOutput("hlt_heater",   "HLT Heater / Gas Solenoid", pin=17, device_type="heater"),
    RelayOutput("mlt_pump",     "Recirculation Pump",         pin=27, device_type="pump"),
    RelayOutput("hlt_mlt_valve","HLT→MLT Valve",             pin=22, device_type="valve"),
    RelayOutput("mlt_bk_valve", "MLT→BK Valve",              pin=23, device_type="valve"),
    RelayOutput("spare_valve_1","Spare Valve 1",              pin=24, device_type="valve"),
    RelayOutput("spare_valve_2","Spare Valve 2",              pin=25, device_type="valve"),
]

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("brewbot-pi")

# ── GPIO setup ────────────────────────────────────────────────────────────────

try:
    from gpiozero import OutputDevice
    GPIO_AVAILABLE = True
    log.info("gpiozero available — GPIO control enabled")
except ImportError:
    GPIO_AVAILABLE = False
    log.warning("gpiozero not found — running in simulation mode (no GPIO)")


class RelayDevice:
    """Thin wrapper so simulation mode works without hardware."""

    def __init__(self, output: RelayOutput):
        self.output = output
        self._dev = None
        if GPIO_AVAILABLE:
            self._dev = OutputDevice(
                output.pin,
                active_high=not output.active_low,
                initial_value=False,
            )

    def on(self):
        if self._dev:
            self._dev.on()
        log.info("→ ON  %s (GPIO %d)", self.output.name, self.output.pin)

    def off(self):
        if self._dev:
            self._dev.off()
        log.info("→ OFF %s (GPIO %d)", self.output.name, self.output.pin)

    def close(self):
        if self._dev:
            self._dev.close()


# ── DS18B20 reading ───────────────────────────────────────────────────────────

def read_ds18b20(w1_id: str) -> Optional[float]:
    path = f"/sys/bus/w1/devices/{w1_id}/w1_slave"
    try:
        with open(path) as f:
            lines = f.readlines()
        if "YES" not in lines[0]:
            return None
        temp_str = lines[1].split("t=")[1].strip()
        return round(int(temp_str) / 1000.0, 2)
    except (FileNotFoundError, IndexError, ValueError) as e:
        log.warning("Could not read %s: %s", w1_id, e)
        return None


def list_w1_devices() -> list[str]:
    return [
        os.path.basename(p)
        for p in glob.glob("/sys/bus/w1/devices/28-*")
    ]

# ── MQTT client ───────────────────────────────────────────────────────────────

class BrewbotController:

    def __init__(self):
        self._relays: dict[str, RelayDevice] = {
            r.device_key: RelayDevice(r) for r in RELAY_OUTPUTS
        }
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.on_disconnect = self._on_disconnect

        # Last-will: mark all devices offline if we drop off
        self._client.will_set(
            "brewbot/pi_controller/state",
            json.dumps({"online": False}),
            retain=True,
        )

        self._stop = threading.Event()

    # ── MQTT callbacks ────────────────────────────────────────────────────────

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            log.info("MQTT connected to %s:%s", MQTT_HOST, MQTT_PORT)
            self._announce_all()
            self._subscribe_commands()
            client.publish(
                "brewbot/pi_controller/state",
                json.dumps({"online": True}),
                retain=True,
            )
        else:
            log.error("MQTT connect failed: %s", reason_code)

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        log.warning("MQTT disconnected (rc=%s) — will reconnect", reason_code)

    def _on_message(self, client, userdata, msg):
        topic = msg.topic
        try:
            payload = json.loads(msg.payload)
        except (json.JSONDecodeError, TypeError):
            return

        # Topic: brewbot/{device_key}/command
        parts = topic.split("/")
        if len(parts) == 3 and parts[2] == "command":
            device_key = parts[1]
            self._handle_command(device_key, payload)

    # ── Device management ─────────────────────────────────────────────────────

    def _announce_all(self):
        """Register every device with the Brewbot server."""
        for sensor in TEMP_SENSORS:
            self._client.publish("brewbot/register", json.dumps({
                "device_key": sensor.device_key,
                "name": sensor.name,
                "type": "temperature_sensor",
            }))
        for output in RELAY_OUTPUTS:
            self._client.publish("brewbot/register", json.dumps({
                "device_key": output.device_key,
                "name": output.name,
                "type": output.device_type,
            }))
        log.info("Announced %d sensors + %d outputs",
                 len(TEMP_SENSORS), len(RELAY_OUTPUTS))

    def _subscribe_commands(self):
        for output in RELAY_OUTPUTS:
            topic = f"brewbot/{output.device_key}/command"
            self._client.subscribe(topic)
            log.debug("Subscribed: %s", topic)

    def _handle_command(self, device_key: str, payload: dict):
        relay = self._relays.get(device_key)
        if not relay:
            log.warning("Unknown device_key in command: %s", device_key)
            return
        action = payload.get("action", "").lower()
        if action == "on":
            relay.on()
        elif action == "off":
            relay.off()
        else:
            log.warning("Unknown action '%s' for %s", action, device_key)

    # ── Sensor polling ────────────────────────────────────────────────────────

    def _poll_sensors(self):
        while not self._stop.is_set():
            for sensor in TEMP_SENSORS:
                value = read_ds18b20(sensor.w1_id)
                if value is not None:
                    self._client.publish(
                        f"brewbot/{sensor.device_key}/reading",
                        json.dumps({"value": value, "unit": sensor.unit}),
                    )
                    log.debug("%s = %.2f %s", sensor.device_key, value, sensor.unit)
                else:
                    log.warning("No reading from %s (%s)", sensor.device_key, sensor.w1_id)
            self._stop.wait(READ_INTERVAL)

    # ── Run ───────────────────────────────────────────────────────────────────

    def run(self):
        log.info("Discovered 1-wire devices: %s", list_w1_devices() or ["none"])

        self._client.connect_async(MQTT_HOST, MQTT_PORT, keepalive=60)
        self._client.loop_start()

        poll_thread = threading.Thread(target=self._poll_sensors, daemon=True)
        poll_thread.start()

        log.info("Brewbot Pi Controller running. Press Ctrl+C to stop.")
        try:
            while not self._stop.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()

    def shutdown(self):
        log.info("Shutting down...")
        self._stop.set()
        for relay in self._relays.values():
            relay.off()   # safe state: everything off on exit
            relay.close()
        self._client.publish(
            "brewbot/pi_controller/state",
            json.dumps({"online": False}),
            retain=True,
        )
        self._client.loop_stop()
        self._client.disconnect()
        log.info("Shutdown complete.")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    controller = BrewbotController()
    signal.signal(signal.SIGTERM, lambda *_: controller.shutdown())
    controller.run()
