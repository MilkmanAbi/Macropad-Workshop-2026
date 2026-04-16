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

# ── GP29 virtual GND — pull low FIRST before anything else ───────────────────
# The PCB routes switch GND through GP29 instead of actual GND.
# Must be driven low immediately or buttons are floating and won't work.
_gnd = digitalio.DigitalInOut(board.GP29)
_gnd.direction = digitalio.Direction.OUTPUT
_gnd.value = False

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

# MilkmanAbi: FUCK. I genuinely dunno if there's a bug here or nah, hn. Idk, just test later OwO

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

# ── Memory Game ───────────────────────────────────────────────────────────────
# Triggered by pressing ALL THREE buttons at once.
# 4 rounds of increasing sequence length. Match the colours to win.
# B1 = Red, B2 = Blue, B3 = Green
# Win = rickroll. Always.

GAME_COLORS = [
    (200, 0,   0  ),   # B1 — GP9  — Red
    (0,   200, 0  ),   # B2 — GP10 — Green
    (0,   0,   200),   # B3 — GP11 — Blue
]

# ── Speed control ─────────────────────────────────────────────────────────────
# GAME_SPEED: multiplier on all timings. Higher = slower.
#   0.5 = fast (punishing)
#   1.0 = default
#   1.8 = slow and comfy (good for carnival — want people to win)
# SPEED_RAMP: how much GAME_SPEED shrinks each round (0 = no ramp).
#   0.0 = same speed all 4 rounds
#   0.1 = gets slightly faster each round (adds a little pressure by round 4)
GAME_SPEED = 1.8
SPEED_RAMP = 0.1

# Pre-set sequences per round — keeps difficulty fair and showable
GAME_ROUNDS = [
    [1, 2, 0, 2],           # Round 1 — 4 steps
    [2, 0, 1, 2, 2, 0],     # Round 2 — 6 steps
    [0, 1, 2, 0, 1, 2, 1],  # Round 3 — 7 steps
]

def _game_flash(btn_idx, spd, duration=0.35):
    led[0] = GAME_COLORS[btn_idx]
    time.sleep(duration * spd)
    led[0] = (0, 0, 0)
    time.sleep(0.15 * spd)

def _game_show_sequence(seq, spd):
    """Flash the sequence for the player to watch."""
    time.sleep(0.4 * spd)
    for idx in seq:
        _game_flash(idx, spd)
    time.sleep(0.2 * spd)

def _game_wait_input(expected_seq):
    """Wait for player to press buttons in order. Returns True if correct."""
    # Drain any buttons still held from the sequence show or previous press
    while any(read_buttons()):
        time.sleep(0.005)
    time.sleep(0.05)  # extra settle time

    for expected in expected_seq:
        # Wait for a single button press
        pressed = None
        while pressed is None:
            raw = read_buttons()
            for i in range(3):
                if raw[i]:
                    pressed = i
                    break
            time.sleep(0.005)

        # Wait for release
        while read_buttons()[pressed]:
            time.sleep(0.005)

        if pressed != expected:
            # Wrong! Flash red fast 3x
            for _ in range(3):
                led[0] = (255, 0, 0)
                time.sleep(0.08)
                led[0] = (0, 0, 0)
                time.sleep(0.08)
            print("[Game] WRONG! Expected B" + str(expected+1) + " got B" + str(pressed+1))
            return False

        # Correct — brief flash of the right colour as feedback
        led[0] = GAME_COLORS[pressed]
        time.sleep(0.12)
        led[0] = (0, 0, 0)
        time.sleep(0.08)

    return True

def _game_round_pass():
    """White flash = round cleared."""
    for _ in range(2):
        led[0] = (200, 200, 200)
        time.sleep(0.18)
        led[0] = (0, 0, 0)
        time.sleep(0.12)

def _game_win():
    """Rainbow flash then rickroll."""
    print("[Game] YOU WIN! Initiating surprise...")
    for color in [(255,0,0),(255,127,0),(0,255,0),(0,0,255),(148,0,211)]:
        led[0] = color
        time.sleep(0.1)
    led[0] = (0, 0, 0)
    time.sleep(0.2)
    from keymaps import execute_action as _ea
    _ea("OPENWEBSITE = https://www.youtube.com/watch?v=klfT41uZniI")

def run_memory_game():
    print("[Game] Entering memory game mode!")
    # Startup animation — cycle R G B
    for c in GAME_COLORS:
        led[0] = c
        time.sleep(0.2)
    led[0] = (0, 0, 0)
    time.sleep(0.5)

    spd = GAME_SPEED  # local copy so GAME_SPEED constant stays untouched

    for round_num, seq in enumerate(GAME_ROUNDS):
        print("[Game] Round", round_num + 1, "spd:", spd, "seq:", seq)

        # Show the sequence at current speed
        _game_show_sequence(seq, spd)

        # Get input (no time pressure on input — just sequence show speed ramps)
        if not _game_wait_input(seq):
            print("[Game] Game over. Back to normal mode.")
            time.sleep(0.5)
            activate_mode(current_mode)
            return

        # Round cleared
        _game_round_pass()
        print("[Game] Round", round_num + 1, "cleared!")
        time.sleep(0.4)

        # Ramp up speed for next round (lower spd = faster flashes)
        spd = max(0.4, spd - SPEED_RAMP)

    # All 4 rounds done — they earned the rickroll
    _game_win()
    time.sleep(1.0)
    activate_mode(current_mode)

# ── Main loop ─────────────────────────────────────────────────────────────────

print("Ready. B1+B2 short=next layer, long=next comms platform")

while True:
    now = time.monotonic()
    layer = LAYERS[current_mode]

    if layer.get("color") == "RAINBOW":
        update_rainbow()

    raw = read_buttons()

    # ── B1+B2+B3 chord — secret game mode trigger ────────────────────────────
    if raw[0] and raw[1] and raw[2]:
        # Wait for all released
        while any(read_buttons()):
            time.sleep(0.005)
        prev_raw   = [False, False, False]
        pressed_at = [time.monotonic()] * 3
        run_memory_game()
        continue

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
