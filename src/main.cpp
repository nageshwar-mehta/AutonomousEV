#include <Arduino.h>

// Define relay pins with readable names
const int R1 = 4;  // Relay 1
const int R2 = 5;  // Relay 2
const int R3 = 6;  // Relay 3
const int R4 = 7;  // Relay 4

void allRelaysOff() {
  digitalWrite(R1, HIGH);
  digitalWrite(R2, HIGH);
  digitalWrite(R3, HIGH);
  digitalWrite(R4, HIGH);
}

void setup() {
  Serial.begin(9600);
  while (!Serial); // Ensure Serial is ready on some boards (e.g., Leonardo)

  Serial.println("Send 'L' or 'R' to control relays");

  // Set all relay pins as OUTPUT and turn them OFF (HIGH = OFF for active LOW relay)
  pinMode(R1, OUTPUT);
  pinMode(R2, OUTPUT);
  pinMode(R3, OUTPUT);
  pinMode(R4, OUTPUT);

  allRelaysOff();
}

void loop() {
  if (Serial.available() > 0) {
    char input = Serial.read();

    allRelaysOff(); // Always start clean

    if (input == 'L' || input == 'l') {
      digitalWrite(R1, LOW);  // ON
      digitalWrite(R2, LOW);  // ON
      digitalWrite(R3, HIGH); // OFF
      digitalWrite(R4, HIGH);  // OFF
      Serial.println("Relay 1 & 2 ON, 3 & 4 OFF");
      delay(1000);
    } 
    else if (input == 'R' || input == 'r') {
      digitalWrite(R3, LOW);  // ON
      digitalWrite(R4, LOW);  // ON
      digitalWrite(R1, HIGH); // OFF
      digitalWrite(R2, HIGH);  // OFF
      Serial.println("Relay 3 & 4 ON, 1 & 2 OFF");
      delay(1000);
    } 
    else {
      allRelaysOff();
      Serial.println("Invalid input! All relays OFF");
    }

    allRelaysOff(); // Turn off everything after 1s or invalid
  }
}
