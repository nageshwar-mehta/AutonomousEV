
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

## 📂 8. Project Folder Structure 

```
/project-root
│── EVcontrol/
│    └── Throttle_Direction_control/
|        └── Throttle_Direction_control.ino
```
---






# 📘 IMU Sensor Overview (BNO055)

An **IMU (Inertial Measurement Unit)** is a sensor module that measures:

* **Acceleration (accelerometers)**
* **Angular velocity (gyroscopes)**
* **Magnetic field (magnetometers)**

Typically these 3 sensors are fused using a **sensor fusion algorithm** (like a Kalman filter or Madgwick filter) to output:

* **Orientation** (yaw, pitch, roll)
* **Linear acceleration**
* **Quaternion rotation**
* **Gravity vector**

### ⭐ Why BNO055 Is Special

Most IMUs give only raw sensor data.
**BNO055 has a built-in ARM Cortex-M0 processor** that performs **sensor fusion internally**, meaning:

* No complex filtering needed
* Direct, stable Euler angles
* Calibrations handled inside
* Low drift orientation output

This makes it ideal for robotics, drones, and autonomous EVs.

---

# 🧠 Code Explanation (Line-by-Line Purpose)

## ✔ 1. Library Imports & Object Creation

```cpp
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BNO055.h>
#include <utility/imumaths.h>
```

These libraries provide:

* I²C communication
* Sensor abstraction
* Math utilities for vectors & quaternions

```cpp
Adafruit_BNO055 bno = Adafruit_BNO055(55, 0x28);
```

Creates a BNO055 sensor object on **I2C address 0x28**.

---

## ✔ 2. Setup()

```cpp
Serial.begin(115200);
```

Starts communication so sensor values can be printed.

```cpp
if (!bno.begin()) { ... }
```

Checks whether the IMU is connected properly.
If not, it halts the program.

```cpp
bno.setExtCrystalUse(true);
```

Uses the external 32 kHz crystal → **more accurate + stable orientation**.

---

## ✔ 3. Loop() — Reading All IMU Outputs

### 🔹 Euler Angles (Heading, Roll, Pitch)

```cpp
imu::Vector<3> euler = bno.getVector(Adafruit_BNO055::VECTOR_EULER);
```

Gives orientation in **degrees**.

* `x` → Heading / Yaw
* `y` → Roll
* `z` → Pitch

Used heavily in steering, tilt correction, stabilization.

---

### 🔹 Linear Acceleration (m/s²)

```cpp
imu::Vector<3> linAcc = bno.getVector(Adafruit_BNO055::VECTOR_LINEARACCEL);
```

Acceleration **without gravity**.
Meaning if the EV is stationary, values ≈ 0.

Used for:

* Detecting movement
* Start/stop detection
* Estimating jerk
* Part of odometry (when fused with wheel sensors)

---

### 🔹 Gravity Vector

```cpp
imu::Vector<3> gravity = bno.getVector(Adafruit_BNO055::VECTOR_GRAVITY);
```

Outputs the direction of gravity.
The EV can use this to:

* Identify road bank angle
* Adjust for tilt on slopes
* Stabilize attitude during turns

---

### 🔹 Quaternion Orientation

```cpp
imu::Quaternion quat = bno.getQuat();
```

Quaternions = rotation in 4D space
Benefits:

* No gimbal lock
* Smooth math for rotation
* Ideal for 3D mapping & robotics

---

### 🔹 Calibration Status

```cpp
bno.getCalibration(&sys, &gyro, &accel, &mag);
```

Each value (0–3):

| Sensor | Meaning                 |
| ------ | ----------------------- |
| 0      | Uncalibrated (bad data) |
| 1      | Partial                 |
| 2      | Good                    |
| 3      | Fully calibrated        |

---

# 📊 Output Meaning

When the code prints:

```
Euler (deg)     : 45.12, -2.33, 178.55
Lin Acc (m/s2)  : 0.12, -0.03, 9.71
Gravity (m/s2)  : 0.01, 0.22, 9.80
Quat (w,x,y,z)  : 0.99, 0.02, 0.03, 0.05
Calibration     : SYS=3 GYRO=3 ACC=3 MAG=2
```

Here’s what each means:

### ✔ Euler

Orientation of the vehicle with respect to the world.

### ✔ Linear Acceleration

How fast the vehicle is accelerating in X, Y, Z axes.
Great for detecting:

* Hard braking
* Quick acceleration
* Turning forces

### ✔ Gravity Vector

How much of your orientation is caused by tilt (useful on slopes).

### ✔ Quaternion

Mathematically stable orientation representation.

### ✔ Calibration

Shows whether data is reliable.

---
## 📂  Project Folder Structure 

```
/project-root
│── EVcontrol/
│    └── IMU_sensor/
|        └── IMU_sensor.ino
```
---

# 🚘 Using IMU Data in Autonomous Electric Vehicles (Use Cases)

IMUs are **mandatory** components in autonomous driving systems.
Here’s what your IMU data can power:

---

## 🟦 1. Vehicle Attitude Estimation (Yaw, Pitch, Roll)

Autonomous EVs must know their orientation:

* Is the vehicle turning left or right?
* Is it climbing a slope?
* Is the chassis tilting dangerously?

Euler + quaternion solve this.

---

## 🟩 2. Dead Reckoning / Short-term Navigation

When GPS is unavailable (under tunnels, near buildings), IMUs help estimate movement.

BNO055 provides:

* Linear acceleration → velocity estimation
* Orientation → direction of movement

While not perfect, when fused with:

* Wheel encoders
* GPS
* Odometry

It becomes a robust solution.

---

## 🟧 3. Sensor Fusion With GPS, Wheel Encoders, Lidar

IMU is one of the core sensors in:

* EKF (Extended Kalman Filter)
* UKF (Unscented Kalman Filter)
* Visual-Inertial SLAM

These combine IMU + other sensors to provide:

* Accurate localization
* Real-time pose estimation
* Predictive movement tracking

---

## 🟥 4. Stability & Control Systems

IMU data feeds into controllers for:

* Traction control
* Anti-rollover algorithms
* Slip detection
* Acceleration limiting
* Adaptive cruise control

Example:
If linear acceleration spikes sideways → system detects potential skid.

---

## 🟪 5. Path Planning & Motion Prediction

Orientation + acceleration are used to:

* Predict where the vehicle will be next
* Smooth out driving paths
* Maintain lane stability

Quaternions especially help in 3D path simulation.

---

## 🟫 6. Safety Systems

The IMU can detect:

* Sudden impacts (accident sensors)
* Rollovers
* Hard braking
* High jerk (unsafe driving conditions)

IMUs enable the EV to respond before the driver even notices.

---

# 🧭 Summary

| Feature             | Why It Matters                             |
| ------------------- | ------------------------------------------ |
| Euler angles        | Steering, tilt, balancing                  |
| Linear acceleration | Velocity estimation, safety detection      |
| Gravity vector      | Slope detection, tilt correction           |
| Quaternion          | Smooth, lock-free orientation for robotics |
| Calibration         | Ensures reliable autonomous data           |

Your IMU code is basically a **full vehicle state estimator** — one of the building blocks of autonomous driving architecture.

---




