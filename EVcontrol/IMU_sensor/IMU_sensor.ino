#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BNO055.h>
#include <utility/imumaths.h>

Adafruit_BNO055 bno = Adafruit_BNO055(55, 0x28);

void setup() {
  Serial.begin(115200);
  delay(1000);

  if (!bno.begin()) {
    Serial.println("BNO055 NOT detected. Check wiring!");
    while (1);
  }

  Serial.println("BNO055 detected!");
  bno.setExtCrystalUse(true);   // improves accuracy
}

void loop() {
  // Orientation - Euler Angles
  imu::Vector<3> euler = bno.getVector(Adafruit_BNO055::VECTOR_EULER);

  // Linear acceleration (world-frame)
  imu::Vector<3> linAcc = bno.getVector(Adafruit_BNO055::VECTOR_LINEARACCEL);

  // Gravity vector
  imu::Vector<3> gravity = bno.getVector(Adafruit_BNO055::VECTOR_GRAVITY);

  // Quaternion output
  imu::Quaternion quat = bno.getQuat();

  // Calibration status
  uint8_t sys, gyro, accel, mag;
  bno.getCalibration(&sys, &gyro, &accel, &mag);

  Serial.println("\n--- BNO055 OUTPUT ---");

  Serial.print("Euler (deg)     : ");
  Serial.print(euler.x()); Serial.print(", ");
  Serial.print(euler.y()); Serial.print(", ");
  Serial.println(euler.z());

  Serial.print("Lin Acc (m/s2)  : ");
  Serial.print(linAcc.x()); Serial.print(", ");
  Serial.print(linAcc.y()); Serial.print(", ");
  Serial.println(linAcc.z());

  Serial.print("Gravity (m/s2)  : ");
  Serial.print(gravity.x()); Serial.print(", ");
  Serial.print(gravity.y()); Serial.print(", ");
  Serial.println(gravity.z());

  Serial.print("Quat (w,x,y,z)  : ");
  Serial.print(quat.w()); Serial.print(", ");
  Serial.print(quat.x()); Serial.print(", ");
  Serial.print(quat.y()); Serial.print(", ");
  Serial.println(quat.z());

  Serial.print("Calibration     : SYS=");
  Serial.print(sys); Serial.print(" GYRO=");
  Serial.print(gyro); Serial.print(" ACC=");
  Serial.print(accel); Serial.print(" MAG=");
  Serial.println(mag);

  delay(200);
}
