#define NUM_SENSORS 4

int trigPins[NUM_SENSORS] = {5, 16, 17, 27};
int echoPins[NUM_SENSORS] = {18, 4, 15, 14};

long duration[NUM_SENSORS];
float distanceCM[NUM_SENSORS];

void setup() {
  Serial.begin(115200);

  for (int i = 0; i < NUM_SENSORS; i++) {
    pinMode(trigPins[i], OUTPUT);
    pinMode(echoPins[i], INPUT);
  }
}

float readUltrasonic(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);

  digitalWrite(trigPin, HIGH);
  delayMicroseconds(5);
  digitalWrite(trigPin, LOW);

  long dur = pulseIn(echoPin, HIGH, 30000); // 30ms timeout

  if (dur == 0) return -1;  // no echo
  
  return (dur * 0.0343 / 2.0); // convert to CM
}

void loop() {
  for (int i = 0; i < NUM_SENSORS; i++) {
    distanceCM[i] = readUltrasonic(trigPins[i], echoPins[i]);

    Serial.print("Sensor ");
    Serial.print(i + 1);
    Serial.print(": ");

    if (distanceCM[i] < 0)
      Serial.println("No Echo");
    else {
      Serial.print(distanceCM[i]);
      Serial.println(" cm");
    }
  }

  Serial.println("----------------------------");
  delay(50);
}
