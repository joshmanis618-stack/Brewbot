# Raspberry Pi Hardware Controller Setup

This guide walks through setting up a Raspberry Pi as the hardware controller for Brewbot. The Pi runs a Python MQTT client that subscribes to device command topics and publishes sensor readings back to the Brewbot server.

---

## Hardware requirements

- Raspberry Pi 3B+ or newer (Pi 4 recommended for reliability)
- Relay board (e.g., 4- or 8-channel 5V relay) for switching pumps and solenoid valves
- Temperature sensors:
  - **DS18B20** (one-wire, waterproof probe) — inexpensive and easy to wire
  - **PT100 / PT1000** (RTD) — more accurate; requires a MAX31865 or similar amplifier board
- 12V or 24V solenoid valves (matched to your relay output voltage)
- 12V or 24V DC pumps (e.g., March or Chugger-style magnetic drive pumps)
- Appropriate power supplies for relay loads

---

## How MQTT works in Brewbot

Brewbot runs a Mosquitto MQTT broker inside Docker on port 1883 (plaintext). The Pi acts as a client that:

1. Connects to the broker at the host machine's IP address on port 1883.
2. Subscribes to `brewbot/{device_key}/command` for each registered device.
3. Publishes temperature and sensor readings to `brewbot/{device_key}/reading`.
4. Publishes state confirmations to `brewbot/{device_key}/state` after acting on a command.

Register each device in the Brewbot UI (Controller page) with a matching `device_key` before running the Pi script.

---

## Registering a device in Brewbot

1. Open the Brewbot UI and navigate to **Controller**.
2. Click **Add Device**.
3. Fill in a descriptive name (e.g., "HLT Temperature") and a device key (e.g., `hlt_temp`).
4. Select the device type (Sensor, Valve, Pump, or Heater).
5. Save. The device key must match exactly what you use in the Pi script.

---

## DS18B20 one-wire temperature sensor wiring

| DS18B20 pin | Pi connection |
|---|---|
| VCC (red) | 3.3V (pin 1) |
| GND (black) | GND (pin 6) |
| DATA (yellow) | GPIO4 (pin 7) |

Add a 4.7k ohm pull-up resistor between DATA and VCC.

Enable the one-wire interface:

```bash
sudo raspi-config
# Interface Options -> 1-Wire -> Yes
sudo reboot
```

Read temperature from the sensor:

```python
import glob
import time

def read_ds18b20():
    base_dir = '/sys/bus/w1/devices/'
    device_folder = glob.glob(base_dir + '28*')[0]
    device_file = device_folder + '/w1_slave'

    with open(device_file, 'r') as f:
        lines = f.readlines()

    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        with open(device_file, 'r') as f:
            lines = f.readlines()

    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos + 2:]
        return float(temp_string) / 1000.0  # Celsius
```

---

## Pi-side MQTT client script

Install dependencies:

```bash
pip install paho-mqtt RPi.GPIO
```

Example script (`brewbot_controller.py`):

```python
import json
import time
import threading
import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO

# --- Configuration ---
BROKER_HOST = "192.168.1.100"   # IP of the machine running docker compose
BROKER_PORT = 1883

# Map device_key -> GPIO BCM pin number
VALVE_PINS = {
    "hlt_valve":      17,
    "mlt_valve":      27,
    "transfer_valve": 22,
}
PUMP_PINS = {
    "transfer_pump":  23,
}
TEMP_DEVICE_KEY = "hlt_temp"

# GPIO setup
GPIO.setmode(GPIO.BCM)
for pin in list(VALVE_PINS.values()) + list(PUMP_PINS.values()):
    GPIO.setup(pin, GPIO.OUT, initial=GPIO.HIGH)  # HIGH = relay off (active-low relay)


def set_relay(pin, on: bool):
    # Active-low relay: LOW = energized (on)
    GPIO.output(pin, GPIO.LOW if on else GPIO.HIGH)


def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT broker (rc={rc})")
    # Subscribe to command topics for all known devices
    for key in list(VALVE_PINS.keys()) + list(PUMP_PINS.keys()):
        topic = f"brewbot/{key}/command"
        client.subscribe(topic)
        print(f"  Subscribed: {topic}")


def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode().strip().lower()
    # Extract device_key from topic: brewbot/{device_key}/command
    parts = topic.split("/")
    if len(parts) != 3:
        return
    device_key = parts[1]

    if device_key in VALVE_PINS:
        pin = VALVE_PINS[device_key]
        if payload == "open":
            set_relay(pin, on=True)
            client.publish(f"brewbot/{device_key}/state", "open")
            print(f"{device_key}: opened")
        elif payload == "close":
            set_relay(pin, on=False)
            client.publish(f"brewbot/{device_key}/state", "closed")
            print(f"{device_key}: closed")

    elif device_key in PUMP_PINS:
        pin = PUMP_PINS[device_key]
        if payload == "on":
            set_relay(pin, on=True)
            client.publish(f"brewbot/{device_key}/state", "on")
            print(f"{device_key}: on")
        elif payload == "off":
            set_relay(pin, on=False)
            client.publish(f"brewbot/{device_key}/state", "off")
            print(f"{device_key}: off")


def publish_temperature_loop(client):
    """Read DS18B20 and publish every 10 seconds."""
    while True:
        try:
            temp_c = read_ds18b20()
            payload = json.dumps({"value": round(temp_c, 2), "unit": "C"})
            client.publish(f"brewbot/{TEMP_DEVICE_KEY}/reading", payload)
            print(f"Published temp: {temp_c:.2f} C")
        except Exception as e:
            print(f"Temperature read error: {e}")
        time.sleep(10)


# --- DS18B20 reader (see above) ---
import glob

def read_ds18b20():
    base_dir = '/sys/bus/w1/devices/'
    device_folder = glob.glob(base_dir + '28*')[0]
    device_file = device_folder + '/w1_slave'
    with open(device_file, 'r') as f:
        lines = f.readlines()
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        with open(device_file, 'r') as f:
            lines = f.readlines()
    equals_pos = lines[1].find('t=')
    return float(lines[1][equals_pos + 2:]) / 1000.0


# --- Main ---
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)

# Publish temperature readings in a background thread
t = threading.Thread(target=publish_temperature_loop, args=(client,), daemon=True)
t.start()

client.loop_forever()
```

---

## Auto-start with systemd

Create `/etc/systemd/system/brewbot-controller.service`:

```ini
[Unit]
Description=Brewbot Hardware Controller
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/brewbot-controller
ExecStart=/usr/bin/python3 /home/pi/brewbot-controller/brewbot_controller.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable brewbot-controller
sudo systemctl start brewbot-controller
sudo systemctl status brewbot-controller
```

View logs:

```bash
journalctl -u brewbot-controller -f
```
