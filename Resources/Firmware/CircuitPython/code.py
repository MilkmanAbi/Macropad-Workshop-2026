"""
code.py — Macropad Workshop 2026
Main runtime: GPIO, mode switching, LED, execution routing.
Edit freely. No compiling. No tools. Just save and run.

Button 1 = GP9 | Button 2 = GP10 | Button 3 = GP11 | LED = GP16
"""

import board
import digitalio
import neopixel
import time
from keymaps import LAYERS, execute_action, build_custom_layer

# ── Hardware ──────────────────────────────────────────────────────────────────

BTN_PINS = [board.GP9, board.GP10, board.GP11]
LED_PIN  = board.GP16

buttons = []
for pin in BTN_PINS:
    b = digitalio.DigitalInOut(pin)
    b.direction = digitalio.Direction.INPUT
    b.pull = digitalio.Pull.UP      # Pull-up: LOW = pressed, HIGH = not pressed
    buttons.append(b)

# pixel_order=neopixel.GRB is the WS2812B standard — stated explicitly for clarity
led = neopixel.NeoPixel(LED_PIN, 1, brightness=0.3, auto_write=True,
                        pixel_order=neopixel.GRB)

# ── Load custom.conf ──────────────────────────────────────────────────────────

def load_custom_conf():
    conf = {}
    try:
        with open("custom.conf", "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, val = line.partition("=")
                    conf[key.strip().upper()] = val.strip()
    except OSError:
        pass
    return conf

LAYERS.append(build_custom_layer(load_custom_conf()))

# ── LED helpers ───────────────────────────────────────────────────────────────

RAINBOW_COLORS = [
    (255, 0,   0),
    (255, 127, 0),
    (255, 255, 0),
    (0,   255, 0),
    (0,   0,   255),
    (75,  0,   130),
    (148, 0,   211),
]
_rainbow_idx  = 0
_last_rainbow = 0.0

def set_led(color):
    if color != "RAINBOW":
        led[0] = color

def update_rainbow():
    global _rainbow_idx, _last_rainbow
    now = time.monotonic()
    if now - _last_rainbow >= 0.15:
        led[0] = RAINBOW_COLORS[_rainbow_idx % len(RAINBOW_COLORS)]
        _rainbow_idx  += 1
        _last_rainbow  = now

def blink_led(color, count, on_s=0.12, off_s=0.10):
    for _ in range(count):
        led[0] = color
        time.sleep(on_s)
        led[0] = (0, 0, 0)
        time.sleep(off_s)

# ── Comms sub-platform state ──────────────────────────────────────────────────
# Platforms cycle with LONG press of B1+B2 while on the comms layer.
# 0 = Teams (2 blinks), 1 = Zoom (3 blinks), 2 = Discord (4 blinks)

COMMS_LAYER_NAME = "Communication"
COMMS_PLATFORMS  = [2, 3, 4]
_comms_platform_idx = 0

def current_comms_blinks():
    return COMMS_PLATFORMS[_comms_platform_idx % len(COMMS_PLATFORMS)]

def cycle_comms_platform():
    global _comms_platform_idx
    _comms_platform_idx = (_comms_platform_idx + 1) % len(COMMS_PLATFORMS)
    blinks = current_comms_blinks()
    layer  = LAYERS[current_mode]
    print("[Comms] Platform blinks:", blinks)
    time.sleep(0.3)
    blink_led(layer["color"], count=blinks)

# ── Mode state ────────────────────────────────────────────────────────────────

current_mode = 0

def activate_mode(idx):
    global current_mode
    current_mode = idx % len(LAYERS)
    layer = LAYERS[current_mode]
    color = layer.get("color", (255, 255, 255))
    set_led(color)
    print("[Mode] ->", layer["name"])
    if layer["name"] == COMMS_LAYER_NAME:
        time.sleep(0.3)
        blink_led(layer["color"], count=current_comms_blinks())

activate_mode(0)

# ── Timing constants ──────────────────────────────────────────────────────────

DEBOUNCE_S   = 0.03   # 30 ms minimum to count as a real press
SHORT_HOLD_S = 0.05   # B1+B2 minimum to count as intentional (not accidental)
LONG_HOLD_S  = 0.80   # B1+B2 held >= 800ms = long press

# ── Button state ──────────────────────────────────────────────────────────────

prev_raw   = [False, False, False]
pressed_at = [0.0, 0.0, 0.0]

def read_buttons():
    return [not b.value for b in buttons]

# ── Main loop ─────────────────────────────────────────────────────────────────

print("Ready. B1+B2 short=next layer, long=next comms platform")

while True:
    now = time.monotonic()
    layer = LAYERS[current_mode]

    if layer.get("color") == "RAINBOW":
        update_rainbow()

    raw = read_buttons()

    # ── B1+B2 chord detection ────────────────────────────────────────────────
    # Wait for the chord to fully release, then decide short vs long.

    if raw[0] and raw[1] and not raw[2]:
        chord_start = time.monotonic()

        # Spin until both buttons are released (or B3 pressed = cancel)
        while True:
            still = read_buttons()
            if not still[0] or not still[1] or still[2]:
                break
            time.sleep(0.005)

        held = time.monotonic() - chord_start

        if held >= LONG_HOLD_S:
            if layer["name"] == COMMS_LAYER_NAME:
                cycle_comms_platform()
            else:
                activate_mode(current_mode + 1)
        elif held >= SHORT_HOLD_S:
            activate_mode(current_mode + 1)
        # else: too short, ignore

        # Reset state — prevents ghost-firing B1/B2 actions on release
        prev_raw   = [False, False, False]
        pressed_at = [time.monotonic(), time.monotonic(), time.monotonic()]
        time.sleep(0.05)
        continue

    # ── Individual buttons ───────────────────────────────────────────────────
    for i in range(3):
        if raw[i] and not prev_raw[i]:
            pressed_at[i] = now

        if not raw[i] and prev_raw[i]:
            held = now - pressed_at[i]
            if held >= DEBOUNCE_S:
                action = layer.get("btn" + str(i + 1))
                if action:
                    if layer["name"] == COMMS_LAYER_NAME:
                        effective_layer = dict(layer)
                        effective_layer["platform_blinks"] = current_comms_blinks()
                    else:
                        effective_layer = layer
                    print("[Press] B" + str(i + 1) + " ->", action)
                    execute_action(action, effective_layer)

        prev_raw[i] = raw[i]

    time.sleep(0.005)
