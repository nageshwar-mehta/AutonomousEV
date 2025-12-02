#include <Arduino.h>

// Define relay pins with readable names
const int R1 = 4;  // Relay 1
const int R2 = 5;  // Relay 2
const int R3 = 6;  // Relay 3
const int R4 = 7;  // Relay 4

// Variables to track left/right presses
int leftCount = 0;
int rightCount = 0;
int lastLeftRightBalance = 0;  // Positive means more rights, negative means more lefts

void allRelaysOff() {
  digitalWrite(R1, HIGH);
  digitalWrite(R2, HIGH);
  digitalWrite(R3, HIGH);
  digitalWrite(R4, HIGH);
}

void setup() {
  Serial.begin(9600);
  while (!Serial); // Ensure Serial is ready on some boards (e.g., Leonardo)

  Serial.println("Send 'L' or 'R' to control relays, 'V' to straighten");

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
      digitalWrite(R4, HIGH); // OFF
      leftCount++;
      lastLeftRightBalance = leftCount - rightCount;
      Serial.println("Left: Relay 1 & 2 ON, 3 & 4 OFF");
      Serial.print("Balance: ");
      Serial.println(lastLeftRightBalance);
      delay(1000);
    } 
    else if (input == 'R' || input == 'r') {
      digitalWrite(R3, LOW);  // ON
      digitalWrite(R4, LOW);  // ON
      digitalWrite(R1, HIGH); // OFF
      digitalWrite(R2, HIGH); // OFF
      rightCount++;
      lastLeftRightBalance = leftCount - rightCount;
      Serial.println("Right: Relay 3 & 4 ON, 1 & 2 OFF");
      Serial.print("Balance: ");
      Serial.println(lastLeftRightBalance);
      delay(1000);
    }
    else if (input == 'V' || input == 'v') {
      // Calculate how many of the opposite direction we need to apply
      int correctionAmount = abs(lastLeftRightBalance);
      
      if (lastLeftRightBalance < 0) {  // More lefts, need to apply rights
        for (int i = 0; i < correctionAmount; i++) {
          digitalWrite(R3, LOW);  // ON
          digitalWrite(R4, LOW);  // ON
          digitalWrite(R1, HIGH); // OFF
          digitalWrite(R2, HIGH); // OFF
          Serial.print("Applying right correction ");
          Serial.println(i+1);
          delay(1000);
          allRelaysOff();
          delay(200);
        }
        rightCount += correctionAmount;
      }
      else if (lastLeftRightBalance > 0) {  // More rights, need to apply lefts
        for (int i = 0; i < correctionAmount; i++) {
          digitalWrite(R1, LOW);  // ON
          digitalWrite(R2, LOW);  // ON
          digitalWrite(R3, HIGH); // OFF
          digitalWrite(R4, HIGH); // OFF
          Serial.print("Applying left correction ");
          Serial.println(i+1);
          delay(1000);
          allRelaysOff();
          delay(200);
        }
        leftCount += correctionAmount;
      }
      
      lastLeftRightBalance = 0;
      Serial.println("System straightened");
      Serial.print("New balance: ");
      Serial.println(leftCount - rightCount);
    }
    else {
      allRelaysOff();
      Serial.println("Invalid input! All relays OFF");
    }

    allRelaysOff(); // Turn off everything after operation
  }
}