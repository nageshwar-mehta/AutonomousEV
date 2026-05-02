"""
Autonomous EV Controller — YOLO Lane Detection + PID Steering
==============================================================
Combines:
  • ESP32 serial vehicle control (W/S throttle, A/D/X steering)
  • RealSense + YOLO lane segmentation
  • PID controller that maps detected steering angle → LEFT/RIGHT/STRAIGHT commands

Install:
    pip install pyserial pynput ultralytics supervision torch pyrealsense2 opencv-python numpy

Run:
    python autonomous_vehicle.py --port /dev/ttyUSB0
    python autonomous_vehicle.py --port COM3

Flags:
    --port      Serial port (required)
    --baud      Baud rate (default 115200)
    --model     Path to YOLO .pt file (default: last.pt)
    --list      List available serial ports and exit
    --kp        PID Kp  (default 0.08)
    --ki        PID Ki  (default 0.001)
    --kd        PID Kd  (default 0.05)

PID Tuning Guide
----------------
Kp (Proportional) — primary steering force
  Start : 0.08
  Range : 0.01 – 0.30
  Too low  → sluggish lane correction, drifts wide on curves
  Too high → rapid left-right oscillation / hunting

Ki (Integral) — corrects persistent steady-state offset
  Start : 0.001
  Range : 0.0 – 0.010
  Too low  → vehicle stays slightly offset from center on long straights
  Too high → slow winding oscillation that grows over time (integral windup)

Kd (Derivative) — damps overshoot
  Start : 0.05
  Range : 0.01 – 0.20
  Too low  → overshoots center, wiggles through curves
  Too high → nervous / twitchy response to every small mask noise

STEERING_THRESHOLD — dead-band around center (degrees)
  Start : 3.0
  Range : 1.0 – 8.0
  Wider  → more STRAIGHT commands, calmer but slower to correct
  Narrower → more responsive but may oscillate on rough road
"""

import argparse
import threading
import time
import sys
import cv2
import numpy as np
import torch
import serial
import serial.tools.list_ports
from ultralytics import YOLO
from pynput import keyboard

try:
    import pyrealsense2 as rs
    REALSENSE_AVAILABLE = True
except ImportError:
    REALSENSE_AVAILABLE = False
    print("[WARN] pyrealsense2 not found — will use webcam fallback (index 0)")

# ═══════════════════════════════════════════════════════════════════════════════
#  CONFIG
# ═══════════════════════════════════════════════════════════════════════════════
SAFE_WIDTH,  SAFE_HEIGHT = 640, 480
MIN_CONF                 = 0.2
STEERING_THRESHOLD       = 0.5      # degrees dead-band before issuing a turn command
MAX_STEERING_ANGLE       = 30.0     # degrees (matches YOLO code)
PID_LOOP_HZ              = 35       # how often PID runs (Hz)

# ═══════════════════════════════════════════════════════════════════════════════
#  PID CONTROLLER
# ═══════════════════════════════════════════════════════════════════════════════
class PIDController:
    """Simple PID with anti-windup clamp."""

    def __init__(self, kp: float, ki: float, kd: float,
                 output_min: float = -MAX_STEERING_ANGLE,
                 output_max: float =  MAX_STEERING_ANGLE,
                 integral_limit: float = 20.0):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_min    = output_min
        self.output_max    = output_max
        self.integral_limit = integral_limit

        self._integral   = 0.0
        self._prev_error = 0.0
        self._prev_time  = None

    def reset(self):
        self._integral   = 0.0
        self._prev_error = 0.0
        self._prev_time  = None

    def compute(self, error: float) -> float:
        now = time.monotonic()
        dt  = (now - self._prev_time) if self._prev_time else (1.0 / PID_LOOP_HZ)
        dt  = max(dt, 1e-6)
        self._prev_time = now

        # Integral with anti-windup clamp
        self._integral += error * dt
        self._integral  = max(-self.integral_limit,
                              min(self.integral_limit, self._integral))

        derivative = (error - self._prev_error) / dt
        self._prev_error = error

        output = (self.kp * error +
                  self.ki * self._integral +
                  self.kd * derivative)

        return max(self.output_min, min(self.output_max, output))


# ═══════════════════════════════════════════════════════════════════════════════
#  SHARED STATE
# ═══════════════════════════════════════════════════════════════════════════════
state = {
    "level"          : 50,
    "steering"       : "STRAIGHT",
    "running"        : True,
    "autonomous"     : True,          # True = PID controls steering
    "raw_angle"      : 0.0,           # latest angle from YOLO
    "pid_output"     : 0.0,           # latest PID output
    "mask_pixels"    : 0,
}
held = set()
ser  = None
state_lock = threading.Lock()

# ═══════════════════════════════════════════════════════════════════════════════
#  SERIAL HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
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

def send(ch: str):
    if ser and ser.is_open:
        try:
            ser.write(ch.encode())
        except Exception:
            pass

def serial_reader():
    while state["running"]:
        if ser and ser.is_open and ser.in_waiting:
            try:
                line = ser.readline().decode(errors="replace").strip()
                if line:
                    print(f"\r[ESP32] {line}")
                    print_status()
            except Exception:
                pass
        time.sleep(0.01)


# ═══════════════════════════════════════════════════════════════════════════════
#  VEHICLE COMMANDS
# ═══════════════════════════════════════════════════════════════════════════════
def speed_up():
    with state_lock:
        lvl = state["level"]
        lvl = 50 if lvl < 50 else min(lvl + 10, 255)
        state["level"] = lvl
    send('w')
    print_status("Speed Up")

def speed_down():
    with state_lock:
        state["level"] = max(state["level"] - 30, 0)
    send('s')
    print_status("Speed Down")

def emergency_stop():
    with state_lock:
        state["level"] = 0
    send(' ')
    print_status("!! STOP !!")

def go_left():
    with state_lock:
        state["steering"] = "LEFT"
    send('a')

def go_right():
    with state_lock:
        state["steering"] = "RIGHT"
    send('d')

def go_straight():
    with state_lock:
        state["steering"] = "STRAIGHT"
    send('x')


# ═══════════════════════════════════════════════════════════════════════════════
#  DISPLAY
# ═══════════════════════════════════════════════════════════════════════════════
def print_status(action=""):
    with state_lock:
        lvl     = state["level"]
        steer   = state["steering"]
        auto    = state["autonomous"]
        angle   = state["raw_angle"]
        pid_out = state["pid_output"]

    bar_len = 20
    filled  = int((lvl / 255) * bar_len)
    bar     = "█" * filled + "░" * (bar_len - filled)
    pct     = lvl / 255 * 100
    steer_disp = {
        "STRAIGHT": "  ──▶──  ",
        "LEFT"    : "◀── L ── ",
        "RIGHT"   : " ── R ──▶",
    }.get(steer, steer)
    mode = "AUTO" if auto else "MANUAL"
    print(
        f"\r  [{mode}]  Throttle [{bar}] {lvl:3d}/255 ({pct:5.1f}%)"
        f"  |  Steer: {steer_disp}"
        f"  |  Angle: {angle:+6.1f}°  PID: {pid_out:+6.2f}"
        f"  |  {action:<14}",
        end="", flush=True
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  KEYBOARD
# ═══════════════════════════════════════════════════════════════════════════════
REPEAT_INT = 1.0 / PID_LOOP_HZ
KEY_ACTIONS = {'w': speed_up, 's': speed_down}   # A/D only in manual mode

def resolve_key(key):
    try:
        ch = key.char.lower() if key.char else None
        return ch
    except AttributeError:
        if key == keyboard.Key.space: return ' '
        if key == keyboard.Key.esc:   return 'esc'
        return None

def on_press(key):
    k = resolve_key(key)
    if k is None: return

    if k == 'esc':
        quit_controller()
        return

    if k == ' ':
        emergency_stop()
        return

    # Toggle autonomous / manual steering with TAB
    if k == '\t':
        with state_lock:
            state["autonomous"] = not state["autonomous"]
        mode = "AUTO" if state["autonomous"] else "MANUAL"
        print_status(f"Mode → {mode}")
        return

    # Manual steering override (only active when autonomous=False)
    if k == 'x':
        go_straight()
        print_status("Straight")
        return

    if k in ('a', 'd') and not state["autonomous"]:
        if k not in held:
            held.add(k)
            if k == 'a': go_left()
            else:        go_right()
        return

    # Throttle keys always work
    if k in KEY_ACTIONS and k not in held:
        held.add(k)
        KEY_ACTIONS[k]()

def on_release(key):
    k = resolve_key(key)
    if k is None: return
    held.discard(k)
    if k in ('a', 'd') and 'a' not in held and 'd' not in held:
        go_straight()

def repeat_loop():
    while state["running"]:
        for k in list(held):
            if k in KEY_ACTIONS:
                KEY_ACTIONS[k]()
        time.sleep(REPEAT_INT)


# ═══════════════════════════════════════════════════════════════════════════════
#  YOLO + LANE DETECTION
# ═══════════════════════════════════════════════════════════════════════════════
def overlay_mask(frame, mask, color=(0, 255, 0), alpha=0.35):
    out = frame.copy()
    out[mask == 1] = (out[mask == 1] * (1 - alpha) +
                      np.array(color) * alpha).astype(np.uint8)
    return out

def compute_steering_angle(mask):
    h, w  = mask.shape
    roi   = mask[int(h * 0.6):h, :]
    ys, xs = np.where(roi == 1)
    if len(xs) == 0:
        return 0.0
    error            = np.mean(xs) - w / 2
    normalized_error = error / (w / 2)
    return float(normalized_error * MAX_STEERING_ANGLE)


# ═══════════════════════════════════════════════════════════════════════════════
#  PID → STEERING COMMAND
# ═══════════════════════════════════════════════════════════════════════════════
def pid_to_steering(pid_output: float):
    """Map PID output (degrees) to serial command."""
    if abs(pid_output) < STEERING_THRESHOLD:
        go_straight()
    elif pid_output < 0:
        go_left()
    else:
        go_right()


# ═══════════════════════════════════════════════════════════════════════════════
#  VISION THREAD
# ═══════════════════════════════════════════════════════════════════════════════
def vision_loop(model_path: str, pid: PIDController):
    """Runs YOLO detection and updates PID steering in a background thread."""

    print(f"[vision] loading model: {model_path}")
    model = YOLO(model_path)
    if torch.cuda.is_available():
        model.to("cuda")
        print("[vision] GPU")
    else:
        print("[vision] CPU")

    # ── Camera setup ──────────────────────────────────────────────────────────
    if REALSENSE_AVAILABLE:
        pipeline = rs.pipeline()
        cfg      = rs.config()
        cfg.enable_stream(rs.stream.color, SAFE_WIDTH, SAFE_HEIGHT,
                          rs.format.bgr8, 30)
        pipeline.start(cfg)
        print("[vision] RealSense started")

        def get_frame():
            frames = pipeline.wait_for_frames()
            cf     = frames.get_color_frame()
            return np.asanyarray(cf.get_data()) if cf else None

        def stop_camera():
            pipeline.stop()
    else:
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  SAFE_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, SAFE_HEIGHT)
        print("[vision] Webcam started")

        def get_frame():
            ret, frame = cap.read()
            return frame if ret else None

        def stop_camera():
            cap.release()

    # ── Detection loop ────────────────────────────────────────────────────────
    prev_pid_time = time.monotonic()

    while state["running"]:
        frame = get_frame()
        if frame is None:
            time.sleep(0.01)
            continue

        h, w = frame.shape[:2]
        results = model(frame, agnostic_nms=True)[0]

        combined_mask = np.zeros((h, w), dtype=np.uint8)
        try:
            if hasattr(results, "masks") and results.masks is not None:
                masks_np = results.masks.data
                if isinstance(masks_np, torch.Tensor):
                    masks_np = masks_np.detach().cpu().numpy()
                for m in masks_np:
                    m_bin = (m > 0.5).astype(np.uint8)
                    if m_bin.shape != (h, w):
                        m_bin = cv2.resize(m_bin, (w, h),
                                           interpolation=cv2.INTER_NEAREST)
                    combined_mask = np.logical_or(combined_mask, m_bin).astype(np.uint8)
        except Exception:
            pass

        # Box fallback if no mask
        if combined_mask.sum() == 0 and hasattr(results, "boxes") and results.boxes:
            for box in results.boxes:
                if float(box.conf.cpu().numpy()) < MIN_CONF:
                    continue
                x1, y1, x2, y2 = box.xyxy.cpu().numpy().astype(int)[0]
                cv2.rectangle(combined_mask, (x1, y1), (x2, y2), 1, -1)

        raw_angle = compute_steering_angle(combined_mask)

        # ── PID at fixed rate ──────────────────────────────────────────────
        now = time.monotonic()
        if now - prev_pid_time >= (1.0 / PID_LOOP_HZ):
            prev_pid_time = now
            # error = raw_angle (0 means centered; negative = veer left)
            pid_output = pid.compute(raw_angle)

            with state_lock:
                state["raw_angle"]   = raw_angle
                state["pid_output"]  = pid_output
                state["mask_pixels"] = int(combined_mask.sum())

            if state["autonomous"]:
                pid_to_steering(pid_output)
                print_status()

        # ── Visualisation window ───────────────────────────────────────────
        frame_out = overlay_mask(frame, combined_mask) if combined_mask.sum() > 0 else frame.copy()

        # steering arrow
        cx = w // 2
        ex = int(cx + raw_angle * 5)
        ey = int(h * 0.7)
        cv2.arrowedLine(frame_out, (cx, h), (ex, ey), (0, 0, 255), 4)
        cv2.putText(frame_out, f"Angle: {raw_angle:+.1f} deg  PID: {state['pid_output']:+.2f}",
                    (10, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        mode_text = "MODE: AUTO (TAB to toggle)" if state["autonomous"] else "MODE: MANUAL (TAB to toggle)"
        cv2.putText(frame_out, mode_text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 220, 80), 2)

        # side panel
        panel = np.full((h, 280, 3), (30, 30, 30), dtype=np.uint8)
        lines = [
            ("AUTONOMOUS CTRL", (0, 220, 80)),
            (f"Angle : {raw_angle:+.2f} deg", (200, 200, 200)),
            (f"PID out: {state['pid_output']:+.2f}", (100, 180, 255)),
            (f"Steer  : {state['steering']}", (255, 200, 60)),
            (f"Throttle: {state['level']}", (200, 200, 200)),
            (f"Mask px: {state['mask_pixels']}", (150, 150, 150)),
            ("", (0,0,0)),
            ("W/S — Throttle", (180, 180, 180)),
            ("TAB — Auto/Manual", (180, 180, 180)),
            ("A/D — Manual steer", (180, 180, 180)),
            ("SPACE — E-Stop", (255, 80, 80)),
            ("ESC — Quit", (255, 80, 80)),
        ]
        for i, (text, col) in enumerate(lines):
            cv2.putText(panel, text, (10, 40 + i * 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, col, 1)

        disp = np.hstack([frame_out, panel])
        cv2.imshow("Autonomous Lane Control", disp)

        if cv2.waitKey(1) & 0xFF == 27:
            state["running"] = False
            break

    stop_camera()
    cv2.destroyAllWindows()


# ═══════════════════════════════════════════════════════════════════════════════
#  QUIT
# ═══════════════════════════════════════════════════════════════════════════════
def quit_controller():
    state["running"] = False
    print("\n\n[Controller] Stopped.")
    if ser and ser.is_open:
        ser.close()
    sys.exit(0)


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description="Autonomous EV: YOLO + PID + ESP32")
    parser.add_argument("--port",  default=None)
    parser.add_argument("--baud",  default=115200, type=int)
    parser.add_argument("--model", default=r"/home/aashish/Downloads/last (3) (1).pt",
                        help="Path to YOLO segmentation model (.pt)")
    parser.add_argument("--list",  action="store_true")
    parser.add_argument("--kp",    default=0.07,  type=float, help="PID Kp")
    parser.add_argument("--ki",    default=0.002, type=float, help="PID Ki")
    parser.add_argument("--kd",    default=0.15,  type=float, help="PID Kd")
    args = parser.parse_args()

    if args.list:
        list_ports()
        return

    if not args.port:
        print("Specify a port with --port  (use --list to see available ports)")
        sys.exit(1)

    open_serial(args.port, args.baud)

    pid = PIDController(kp=args.kp, ki=args.ki, kd=args.kd)
    print(f"[PID] Kp={args.kp}  Ki={args.ki}  Kd={args.kd}")
    print(f"[PID] Steering threshold: ±{STEERING_THRESHOLD}°")

    print("\nControls:")
    print("  W       — Accelerate (hold)")
    print("  S       — Brake / Decelerate (hold)")
    print("  TAB     — Toggle Autonomous / Manual steering")
    print("  A / D   — Manual steer Left / Right (Manual mode only)")
    print("  X       — Straighten (Manual mode)")
    print("  SPACE   — Emergency Stop")
    print("  ESC     — Quit\n")
    print("  Default mode: AUTONOMOUS (PID controls steering, you control throttle)\n")

    threading.Thread(target=serial_reader, daemon=True).start()
    threading.Thread(target=repeat_loop,   daemon=True).start()
    threading.Thread(target=vision_loop,   args=(args.model, pid), daemon=True).start()

    print_status("Ready")

    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()


if __name__ == "__main__":
    main()
