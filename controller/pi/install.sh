#!/bin/bash
# Brewbot Pi Controller — one-shot setup script
# Run as: bash install.sh
# Tested on Raspberry Pi OS Bookworm (64-bit), Pi 4 and Pi 5.
set -e

echo "=== Brewbot Pi Controller Setup ==="

# 1. System packages
echo "[1/5] Installing system packages..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3-pip python3-lgpio

# 2. Enable 1-wire for DS18B20 sensors
echo "[2/5] Enabling 1-wire interface..."
CONFIG=/boot/firmware/config.txt
if ! grep -q "dtoverlay=w1-gpio" "$CONFIG"; then
    echo "dtoverlay=w1-gpio" | sudo tee -a "$CONFIG"
    echo "      → Added dtoverlay=w1-gpio to $CONFIG (reboot required)"
else
    echo "      → 1-wire already enabled"
fi

# 3. Python dependencies
echo "[3/5] Installing Python packages..."
pip3 install --break-system-packages paho-mqtt gpiozero

# 4. Discover connected DS18B20 sensors
echo "[4/5] Probing 1-wire bus..."
echo "      Plug in your DS18B20 sensors, then run:"
echo "        ls /sys/bus/w1/devices/28-*"
echo "      Copy the IDs into brewbot_controller.py → TEMP_SENSORS"

# 5. Systemd service
echo "[5/5] Installing systemd service..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE=/etc/systemd/system/brewbot-controller.service

sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Brewbot Pi Controller
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=${SCRIPT_DIR}
ExecStart=/usr/bin/python3 ${SCRIPT_DIR}/brewbot_controller.py
Restart=on-failure
RestartSec=10
Environment=BREWBOT_MQTT_HOST=192.168.1.100

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable brewbot-controller
echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "  1. Edit brewbot_controller.py — set MQTT_HOST and your sensor IDs"
echo "  2. Reboot the Pi to activate 1-wire:  sudo reboot"
echo "  3. After reboot, start the service:   sudo systemctl start brewbot-controller"
echo "  4. Check logs:                         journalctl -u brewbot-controller -f"
