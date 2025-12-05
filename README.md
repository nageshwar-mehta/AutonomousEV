
---

# Relay Steering + Serial-Controlled Throttle System

This project implements a **basic drive-and-steer control system** using an **ESP32**, leveraging:

* **DAC output (analog throttle)**
* **Digital relay control (LEFT / RIGHT / STRAIGHT steering)**
* **Serial input commands for real-time control**
* **ADC feedback to read filter output voltage**

The code is written for a custom buggy / EV prototype system where the ESP32 controls **motor throttle** and **steering direction**.

---

## 🚗 1. Purpose of This Code

This program exists to provide a **simple, human-debuggable control interface** over USB serial, allowing you to:

### ✔ Control Throttle

Generate an **analog voltage (0–3.3 V)** using ESP32’s DAC to drive:

* Motor controllers
* ESC throttle lines
* Filtered PWM circuits

### ✔ Control Steering

Use **four relays** (R1–R4) to switch steering configurations:

* **Straight**
* **Left turn**
* **Right turn**

This is typically used when steering is achieved through **polarity-based motor actuation**, **hydraulic valve solenoids**, or **H-bridge-type steering systems**.

### ✔ Monitor System Feedback

The code reads ADC values from a **filter output pin**, so you can:

* Verify DAC output
* Log motor controller response
* Validate signal conditioning circuits

---

## 🔌 2. Hardware Connections

### **DAC Output**

| Component              | Pin     |
| ---------------------- | ------- |
| DAC output to throttle | GPIO 25 |

### **ADC Input**

| Component     | Pin            |
| ------------- | -------------- |
| Filter output | GPIO 34 (ADC1) |

### **Relay Steering Control**

| Relay | Pin | Purpose          |
| ----- | --- | ---------------- |
| R1    | 4   | Steering control |
| R2    | 5   | Steering control |
| R3    | 13  | Steering control |
| R4    | 14  | Steering control |

These four relays create **three states**:

| State        | R1   | R2   | R3   | R4   |
| ------------ | ---- | ---- | ---- | ---- |
| **Straight** | HIGH | HIGH | HIGH | HIGH |
| **Left**     | LOW  | LOW  | HIGH | HIGH |
| **Right**    | HIGH | HIGH | LOW  | LOW  |

---

## 🧠 3. How the System Works

### 🟦 A. Throttle Control (DAC)

The ESP32 has a built-in **8-bit DAC**, so values 0–255 map to:

```
0   → 0 V  
255 → ~3.3 V
```

The code dynamically adjusts `level` based on serial input:

| Input   | Action                         |
| ------- | ------------------------------ |
| `W`     | Speed up (increase DAC output) |
| `S`     | Slow down                      |
| `SPACE` | Emergency stop (DAC=0)         |

### 🟧 B. Steering Control (Relays)

The code stores steering state in:

```cpp
int steeringState = 0;  // 0=straight, 1=left, 2=right
```

Then applies relay configuration using `applySteeringState()`.

| Input | Steering           |
| ----- | ------------------ |
| `A`   | Turn left          |
| `D`   | Turn right         |
| `X`   | Stop turning |

### 🟩 C. ADC Monitoring

Every loop when a character is received:

* Reads filtered output via `analogRead()`
* Prints raw ADC + voltage
* Useful for debugging throttle filtering circuits

---

## ⌨️ 4. Serial Controls (User Commands)

| Key     | Function            |
| ------- | ------------------- |
| `W`     | Increase throttle   |
| `S`     | Decrease throttle   |
| `SPACE` | Stop immediately    |
| `A`     | Turn LEFT           |
| `D`     | Turn RIGHT          |
| `X`     | Stop turning steering |

The serial monitor displays:

```
Throttle = 120 | Steering = Left | Filter ADC = 2048 | Voltage = 1.650
```

---

## 🖥️ 5. Expected Serial Output

You’ll see status logs like:

```
Speed Up
Throttle = 70 | Steering = Straight | Filter ADC = 1800 | Voltage = 1.451
LEFT ACTIVE
Throttle = 90 | Steering = Left | Filter ADC = 2200 | Voltage = 1.771
STOP
Throttle = 0 | Steering = Straight | Filter ADC = 800 | Voltage = 0.645
```

This lets anyone testing the prototype immediately understand:

* Current speed level
* Steering state
* Filtered throttle response

---

## 🧭 6. Why This Architecture?

### ⭐ Separation of Concerns

Throttle and steering are handled **independently**, preventing bugs where turning affects speed.

### ⭐ Real-time manual debugging

Perfect for:

* EV buggy development
* Steering mechanism testing
* Robotics steering systems

### ⭐ Scalable

This control module can later be upgraded to:

* Bluetooth joystick input
* WiFi/MQTT RC control
* PID-based throttle regulation
* Automatic obstacle avoidance
* CAN bus integration

We’re basically laying the foundation for a full-on autonomous vehicle stack.

---

## 🚀 7. Future Improvements 

### 🔹 1. Add Safety Features

* Timeout: stop vehicle if no command is received for 1–2 seconds
* Steering + throttle lockout during errors

### 🔹 2. Replace Relays with MOSFET H-bridges

Relays are slow and bulky; MOSFET drivers are faster and safer.

### 🔹 3. Implement Smoothing on DAC Output

Avoid sudden jumps by using:

```cpp
level = level * 0.7 + newValue * 0.3;
```

### 🔹 4. Add PID for Stable Throttle

Useful for terrains where load varies. currently we are not using PID because buggy's controler module itself stablizing our throttle.

### 🔹 5. Use FreeRTOS Tasks

Split:

* Steering task
* Throttle task
* ADC logging task

---

## 📂 8. Project Folder Structure (Will Update When You Share Path)

When you provide the folder path and more files, I’ll generate:

```
/project-root
│── EVcontrol/
│    └── Throttle_Direction_control/
|        └── Throttle_Direction_control.ino
```
