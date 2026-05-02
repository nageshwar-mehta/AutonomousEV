# Autonomous EV Control System

This repository contains the complete software stack for controlling an **Autonomous Electric Vehicle (EV)** using:

* 🧠 Computer Vision (YOLO Lane Detection)
* 🎯 PID-based Steering Control
* 🔌 ESP32-based Hardware Interface
* 📡 Serial Communication + Remote Access (SSH)

---

## Project Structure

```
├── Throttle_Direction_control.ino   # ESP32 firmware (low-level control)
├── autonomous_vehicle.py            # Main autonomous driving logic
├── esp_controller.py                # Manual control via keyboard
├── seg.py                           # Lane detection visualization
├── last (3).pt                      # Trained YOLO model weights
├── ssh_setup.md                     # Jetson setup & SSH instructions
```

---

## 📄 File Descriptions

### 🔹 `autonomous_vehicle.py`

> **Core Autonomous System**

* Uses camera input (RealSense/Webcam) to detect lanes
* Loads YOLO model (`.pt`) for segmentation
* Computes steering angle from detected lane
* Applies **PID controller** for smooth steering
* Sends commands (`W/S/A/D/X`) to ESP32 via serial

💡 Key features:

* Autonomous + Manual toggle (TAB)
* Real-time visualization
* PID tuning support

---

### 🔹 `esp_controller.py`

> 🎮 **Manual Control Interface**

* Keyboard-based EV control
* Sends commands to ESP32:
  * `W/S` → throttle
  * `A/D` → steering
  * `X` → straighten
  * `SPACE` → emergency stop

💡 Useful for:

* Testing hardware
* Debugging steering/throttle independently

---

### 🔹 `seg.py`

> 👁️ **Lane Detection Testing Tool**

* Runs YOLO model on camera feed
* Displays segmentation masks for lanes
* Helps verify model performance before deployment

💡 Use this before running full autonomous system (trust issues with models are real 😅)

---

### 🔹 `last (3).pt`

> 🧠 **Trained YOLO Model Weights**

* Contains trained lane detection model
* Used by:
  * `autonomous_vehicle.py`
  * `seg.py`

---

### 🔹 `Throttle_Direction_control.ino`

> 🔌 **ESP32 Firmware (Hardware Layer)**

* Controls:
  * 🚀 Throttle via DAC output
  * 🔁 Steering via relay-based hydraulic system

#### Inputs (via Serial):

* `W` → Increase speed
* `S` → Decrease speed
* `A` → Turn left
* `D` → Turn right
* `X` → Straight
* `SPACE` → Stop

💡 Also reads analog feedback (filter output voltage)

---

### 🔹 `ssh_setup.md`

> 🌐 **Remote Access Setup**

* Instructions to:
  * Configure **Jetson Orin as server**
  * Enable SSH access
  * Control EV remotely from any system

---

## System Workflow

```
Camera → YOLO Model → Lane Mask → Steering Angle
        ↓
     PID Controller
        ↓
   Serial Commands
        ↓
     ESP32 (Actuation)
        ↓
  Steering + Throttle Control
```

---

## How to Run

### 1️⃣ Install Dependencies

```bash
pip install pyserial pynput ultralytics supervision torch opencv-python numpy
```

---

### 2️⃣ Run Autonomous Mode

```bash
python autonomous_vehicle.py --port COM3
```

---

### 3️⃣ Run Manual Mode (Optional)

```bash
python esp_controller.py --port COM3
```

---

### 4️⃣ Test Lane Detection Only

```bash
python seg.py
```

---

## Controls Summary

| Key   | Action             |
| ----- | ------------------ |
| W     | Accelerate         |
| S     | Brake              |
| A     | Left               |
| D     | Right              |
| X     | Straight           |
| SPACE | Emergency Stop     |
| TAB   | Auto/Manual Toggle |

---

## Key Concepts Used

* YOLO Segmentation
* PID Control System
* Serial Communication (UART)
* Embedded Systems (ESP32)
* Real-time Computer Vision

---

## Notes

* Ensure correct **serial port** is selected and command will change if you are working with **LINUX** environment.
* Model path must match `.pt` file location
* PID tuning is critical for stable driving
* Camera calibration affects lane detection accuracy
