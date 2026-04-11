"""
keymaps.py — Macropad Workshop 2026
All layers, keybindings, macros, and the action executor.
Hack this file. Add actions, change bindings. No compiling needed.
"""

import usb_hid
import time
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode
from adafruit_hid.consumer_control import ConsumerControl
from adafruit_hid.consumer_control_code import ConsumerControlCode

# ── HID devices ───────────────────────────────────────────────────────────────

kbd    = Keyboard(usb_hid.devices)
layout = KeyboardLayoutUS(kbd)
cc     = ConsumerControl(usb_hid.devices)

# ── Layer definitions ─────────────────────────────────────────────────────────
# btn1/btn2/btn3 = action string (see execute_action for full list)
# color          = (R, G, B) tuple or "RAINBOW"
# Custom layer is appended at runtime by code.py after reading custom.conf

LAYERS = [
    # 1. Clipboard — Cyan
    {
        "name":  "Clipboard",
        "color": (0, 200, 200),
        "btn1":  "COPY",
        "btn2":  "PASTE",
        "btn3":  "CUT",
    },
    # 2. Media — Purple
    {
        "name":  "Media",
        "color": (120, 0, 200),
        "btn1":  "VOL_UP",
        "btn2":  "VOL_DOWN",
        "btn3":  "PLAY_PAUSE",
    },
    # 3. Communication — Orange
    # platform_blinks is set here as the DEFAULT only.
    # At runtime, code.py manages the live platform via _comms_platform_idx
    # and injects the correct blinks count before calling execute_action.
    # Long press B1+B2 cycles: Teams(2) -> Zoom(3) -> Discord(4) -> Teams
    {
        "name":            "Communication",
        "color":           (255, 80, 0),
        "platform_blinks": 2,
        "btn1":            "MIC_TOGGLE",
        "btn2":            "SPEAKER_MUTE",
        "btn3":            "CAM_TOGGLE",
    },
    # 4. Coding — Red
    {
        "name":  "Coding",
        "color": (200, 0, 0),
        "btn1":  "SAVE",
        "btn2":  "UNDO",
        "btn3":  "REDO",
    },
    # 5. Troll — Rainbow
    {
        "name":  "Troll",
        "color": "RAINBOW",
        "btn1":  "OPEN_BROWSER",
        "btn2":  "RICKROLL",
        "btn3":  "NYAN_CAT",
    },
    # 6. Custom — loaded from custom.conf by code.py
]

# ── Platform shortcuts ────────────────────────────────────────────────────────
# Keyed by platform_blinks value (2=Teams, 3=Zoom, 4=Discord)
# None = no shortcut exists for that action on that platform

COMMS_SHORTCUTS = {
    # Microsoft Teams
    2: {
        "MIC_TOGGLE":   ([Keycode.CONTROL, Keycode.SHIFT], Keycode.M),
        "SPEAKER_MUTE": None,
        "CAM_TOGGLE":   ([Keycode.CONTROL, Keycode.SHIFT], Keycode.O),
    },
    # Zoom
    3: {
        "MIC_TOGGLE":   ([Keycode.ALT], Keycode.A),
        "SPEAKER_MUTE": None,
        "CAM_TOGGLE":   ([Keycode.ALT], Keycode.V),
    },
    # Discord
    4: {
        "MIC_TOGGLE":   ([Keycode.CONTROL, Keycode.SHIFT], Keycode.M),
        "SPEAKER_MUTE": ([Keycode.CONTROL, Keycode.SHIFT], Keycode.D),
        "CAM_TOGGLE":   ([Keycode.CONTROL, Keycode.SHIFT], Keycode.V),
    },
}

# ── HID helpers ───────────────────────────────────────────────────────────────

def _tap(*keycodes):
    kbd.press(*keycodes)
    time.sleep(0.05)
    kbd.release_all()
    time.sleep(0.05)

def _type(text):
    layout.write(text)
    time.sleep(0.04)

def _open_run_dialog():
    _tap(Keycode.WINDOWS, Keycode.R)
    time.sleep(0.6)

def _open_url(url):
    """Rubber-ducky: Win+R -> type URL -> Enter. Works on any Windows machine."""
    _open_run_dialog()
    _type(url)
    time.sleep(0.1)
    _tap(Keycode.ENTER)

# ── Action executor ───────────────────────────────────────────────────────────
# Add new actions here and they work everywhere: layers + custom.conf.
#
# Normalisation rules (handles spaces from custom.conf partition parsing):
#   "COPY"                          -> cmd="COPY",        val=""
#   "OPENWEBSITE = https://..."     -> cmd="OPENWEBSITE", val="https://..."
#   "TYPE = hello world"            -> cmd="TYPE",        val="hello world"  (case preserved)
#   "SHORTCUT = CTRL+SHIFT+T"       -> cmd="SHORTCUT",    val="CTRL+SHIFT+T"

def execute_action(action, layer=None):
    action = action.strip()

    if "=" in action:
        cmd = action.split("=", 1)[0].strip().upper()
        val = action.split("=", 1)[1].strip()   # preserve case for TYPE/URLs
    else:
        cmd = action.strip().upper()
        val = ""

    # ── Clipboard ─────────────────────────────────────────────────────────────
    if cmd == "COPY":
        _tap(Keycode.CONTROL, Keycode.C)

    elif cmd == "PASTE":
        _tap(Keycode.CONTROL, Keycode.V)

    elif cmd == "CUT":
        _tap(Keycode.CONTROL, Keycode.X)

    elif cmd == "SELECT_ALL":
        _tap(Keycode.CONTROL, Keycode.A)

    # ── Editing ───────────────────────────────────────────────────────────────
    elif cmd == "SAVE":
        _tap(Keycode.CONTROL, Keycode.S)

    elif cmd == "UNDO":
        _tap(Keycode.CONTROL, Keycode.Z)

    elif cmd == "REDO":
        _tap(Keycode.CONTROL, Keycode.Y)

    elif cmd == "FIND":
        _tap(Keycode.CONTROL, Keycode.F)

    elif cmd == "NEW_TAB":
        _tap(Keycode.CONTROL, Keycode.T)

    elif cmd == "CLOSE_TAB":
        _tap(Keycode.CONTROL, Keycode.W)

    elif cmd == "SCREENSHOT":
        _tap(Keycode.WINDOWS, Keycode.SHIFT, Keycode.S)

    # ── Media ─────────────────────────────────────────────────────────────────
    elif cmd == "VOL_UP":
        cc.send(ConsumerControlCode.VOLUME_INCREMENT)

    elif cmd == "VOL_DOWN":
        cc.send(ConsumerControlCode.VOLUME_DECREMENT)

    elif cmd == "MUTE":
        cc.send(ConsumerControlCode.MUTE)

    elif cmd == "PLAY_PAUSE":
        cc.send(ConsumerControlCode.PLAY_PAUSE)

    elif cmd == "NEXT_TRACK":
        cc.send(ConsumerControlCode.SCAN_NEXT_TRACK)

    elif cmd == "PREV_TRACK":
        cc.send(ConsumerControlCode.SCAN_PREVIOUS_TRACK)

    # ── Comms (platform-aware) ────────────────────────────────────────────────
    elif cmd in ("MIC_TOGGLE", "SPEAKER_MUTE", "CAM_TOGGLE"):
        blinks = (layer or {}).get("platform_blinks", 2)
        combo  = COMMS_SHORTCUTS.get(blinks, {}).get(cmd)
        if combo:
            modifiers, key = combo
            kbd.press(*modifiers, key)
            time.sleep(0.05)
            kbd.release_all()

    # ── Browser / rubber ducky ────────────────────────────────────────────────
    elif cmd == "OPEN_BROWSER":
        _open_run_dialog()
        _type("https://")

    elif cmd == "RICKROLL":
        _open_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    elif cmd == "NYAN_CAT":
        _open_url("https://www.nyan.cat")

    elif cmd == "OPENWEBSITE":
        _open_url(val)              # val is the URL, case preserved

    elif cmd == "TYPE":
        _type(val)                  # val typed as-is, original case

    elif cmd == "SHORTCUT":
        _parse_shortcut(val.upper())

    else:
        print("[WARN] Unknown action:", action)

# ── Shortcut parser ───────────────────────────────────────────────────────────
# Parses "CTRL+SHIFT+T" style strings from custom.conf SHORTCUT= values.

_KEY_MAP = {
    "CTRL":    Keycode.CONTROL,
    "CONTROL": Keycode.CONTROL,
    "ALT":     Keycode.ALT,
    "SHIFT":   Keycode.SHIFT,
    "WIN":     Keycode.WINDOWS,
    "WINDOWS": Keycode.WINDOWS,
    "GUI":     Keycode.GUI,
    "ENTER":   Keycode.ENTER,
    "ESC":     Keycode.ESCAPE,
    "TAB":     Keycode.TAB,
    "SPACE":   Keycode.SPACEBAR,
    "BACK":    Keycode.BACKSPACE,
    "DEL":     Keycode.DELETE,
    "UP":      Keycode.UP_ARROW,
    "DOWN":    Keycode.DOWN_ARROW,
    "LEFT":    Keycode.LEFT_ARROW,
    "RIGHT":   Keycode.RIGHT_ARROW,
    "F1":  Keycode.F1,  "F2":  Keycode.F2,  "F3":  Keycode.F3,
    "F4":  Keycode.F4,  "F5":  Keycode.F5,  "F6":  Keycode.F6,
    "F7":  Keycode.F7,  "F8":  Keycode.F8,  "F9":  Keycode.F9,
    "F10": Keycode.F10, "F11": Keycode.F11, "F12": Keycode.F12,
}

def _parse_shortcut(keys_str):
    parts = [p.strip() for p in keys_str.split("+")]
    keycodes = []
    for part in parts:
        if part in _KEY_MAP:
            keycodes.append(_KEY_MAP[part])
        elif len(part) == 1:
            kc = getattr(Keycode, part, None)
            if kc:
                keycodes.append(kc)
            else:
                print("[WARN] Unknown key:", part)
        else:
            print("[WARN] Unknown key:", part)
    if keycodes:
        kbd.press(*keycodes)
        time.sleep(0.05)
        kbd.release_all()
        time.sleep(0.05)

# ── Custom layer builder ──────────────────────────────────────────────────────
# Called from code.py. Reads the parsed custom.conf dict.

def build_custom_layer(conf):
    layer = {
        "name":  conf.get("NAME", "Custom"),
        "color": (0, 255, 136),
        "btn1":  conf.get("BUTTON1", "COPY"),
        "btn2":  conf.get("BUTTON2", "PASTE"),
        "btn3":  conf.get("BUTTON3", "CUT"),
    }
    raw_color = conf.get("COLOR", "").strip().upper()
    if raw_color == "RAINBOW":
        layer["color"] = "RAINBOW"
    elif raw_color.startswith("0X"):
        try:
            h = int(raw_color, 16)
            layer["color"] = ((h >> 16) & 0xFF, (h >> 8) & 0xFF, h & 0xFF)
        except ValueError:
            pass
    return layer
