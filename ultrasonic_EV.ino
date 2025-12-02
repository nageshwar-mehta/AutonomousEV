#define TRIG_PIN 5
#define ECHO_PIN 18

long duration;
float distance;

void setup() {
  Serial.begin(115200);

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
}

void loop() {
  // Send trigger pulse
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(1);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(5);
  digitalWrite(TRIG_PIN, LOW);

  // Read echo pulse width
  duration = pulseIn(ECHO_PIN, HIGH, 30000); // timeout 30ms

  // Convert to distance (SR04M = sound speed ~340 m/s)
  distance = duration * 0.0343 / 2;

  // If no valid reading
  if (duration == 0) {
    Serial.println("No echo");
  } else {
    Serial.print("Distance: ");
    Serial.print(distance);
    Serial.println(" cm");
  }

  delay(20);
}
