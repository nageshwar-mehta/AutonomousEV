"""
ESP32 EV Terminal Controller
=============================
pip install pyserial pynput

Run:
    python esp_controller.py --port /dev/ttyUSB0
    python esp_controller.py --port COM3          # Windows

Flags:
    --port    Serial port (required)
    --baud    Baud rate (default 115200)
    --list    List available ports and exit
"""

import argparse
import threading
import time
import sys
import serial
import serial.tools.list_ports
from pynput import keyboard

# ── state ─────────────────────────────────────────────────────────────────────
level    = 50
steering = "STRAIGHT"
ser      = None
running  = True
held     = set()

REPEAT_HZ  = 20
REPEAT_INT = 1.0 / REPEAT_HZ

# ── serial ────────────────────────────────────────────────────────────────────

def list_ports():
    ports = serial.tools.list_ports.comports()
    if ports:
        print("Available ports:")
        for p in ports:
            print(f"  {p.device}  —  {p.description}")
    else:
        print("No serial ports found.")

def open_serial(port, baud):
    global ser
    try:
        ser = serial.Serial(port, baud, timeout=1)
        time.sleep(2)
        print(f"[OK] Connected to {port} @ {baud}\n")
    except serial.SerialException as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

def send(ch):
    if ser and ser.is_open:
        ser.write(ch.encode())

def serial_reader():
    while running:
        if ser and ser.is_open and ser.in_waiting:
            try:
                line = ser.readline().decode(errors="replace").strip()
                if line:
                    print(f"\r[ESP32] {line}")
                    print_status()
            except Exception:
                pass
        time.sleep(0.01)

# ── actions ───────────────────────────────────────────────────────────────────

def speed_up():
    global level
    level = 50 if level < 50 else min(level + 10, 255)
    send('w')
    print_status("Speed Up")

def speed_down():
    global level
    level = max(level - 30, 0)
    send('s')
    print_status("Speed Down")

def stop():
    global level
    level = 0
    send(' ')
    print_status("!! STOP !!")

def go_left():
    global steering
    steering = "LEFT"
    send('a')
    print_status("Left")

def go_right():
    global steering
    steering = "RIGHT"
    send('d')
    print_status("Right")

def go_straight():
    global steering
    steering = "STRAIGHT"
    send('x')
    print_status("Straight")

# ── display ───────────────────────────────────────────────────────────────────

def print_status(action=""):
    bar_len = 20
    filled  = int((level / 255) * bar_len)
    bar     = "█" * filled + "░" * (bar_len - filled)
    pct     = level / 255 * 100
    steer_disp = {
        "STRAIGHT": "  ──▶──  ",
        "LEFT":     "◀── L ── ",
        "RIGHT":    " ── R ──▶",
    }.get(steering, steering)
    print(f"\r  Throttle [{bar}] {level:3d}/255 ({pct:5.1f}%)  |  Steering: {steer_disp}  |  {action:<14}", end="", flush=True)

# ── held-key repeat ───────────────────────────────────────────────────────────

KEY_ACTIONS = {'w': speed_up, 's': speed_down, 'a': go_left, 'd': go_right}

def repeat_loop():
    while running:
        for k in list(held):
            if k in KEY_ACTIONS:
                KEY_ACTIONS[k]()
        time.sleep(REPEAT_INT)

# ── pynput key mapping ────────────────────────────────────────────────────────

def resolve_key(key):
    """Return a single character string for the key, or None."""
    try:
        ch = key.char.lower() if key.char else None
        return ch
    except AttributeError:
        # special keys
        if key == keyboard.Key.space:
            return ' '
        if key == keyboard.Key.esc:
            return 'esc'
        return None

def on_press(key):
    k = resolve_key(key)
    if k is None:
        return
    if k == 'esc':
        quit_controller()
        return
    if k == ' ':
        stop()
        return
    if k == 'x':
        go_straight()
        return
    if k in KEY_ACTIONS and k not in held:
        held.add(k)
        KEY_ACTIONS[k]()

def on_release(key):
    k = resolve_key(key)
    if k is None:
        return
    held.discard(k)
    if k in ('a', 'd') and 'a' not in held and 'd' not in held:
        go_straight()

# ── quit ──────────────────────────────────────────────────────────────────────

def quit_controller():
    global running
    running = False
    print("\n\n[Controller] Stopped.")
    if ser and ser.is_open:
        ser.close()
    sys.exit(0)

# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="ESP32 EV Terminal Controller")
    parser.add_argument("--port", default=None)
    parser.add_argument("--baud", default=115200, type=int)
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    if args.list:
        list_ports()
        return

    if not args.port:
        print("Specify a port with --port  (use --list to see available ports)")
        sys.exit(1)

    open_serial(args.port, args.baud)

    print("Controls:")
    print("  W  — Accelerate (hold)")
    print("  S  — Brake / Decelerate (hold)")
    print("  A  — Steer Left (hold)")
    print("  D  — Steer Right (hold)")
    print("  X  — Straighten")
    print("  SPACE — Emergency Stop")
    print("  ESC — Quit\n")

    threading.Thread(target=serial_reader, daemon=True).start()
    threading.Thread(target=repeat_loop,   daemon=True).start()

    print_status("Ready")

    # pynput listener — no root needed
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()

if __name__ == "__main__":
    main()
