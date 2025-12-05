#include <Arduino.h>

/* =======================
      DAC CONTROL SETUP
   ======================= */
int dacPin = 25;
int level = 50;        // throttle value
int filterOutPin = 34; // ADC pin


/* =======================
      RELAY SETUP (Option B)
   ======================= */
const int R1 = 4;    
const int R2 = 5;    
const int R3 = 13;   
const int R4 = 14;   

// Steering state: 0=straight, 1=left, 2=right
int steeringState = 0;


void applySteeringState() {
  if (steeringState == 0) {
    // STRAIGHT
    digitalWrite(R1, HIGH);
    digitalWrite(R2, HIGH);
    digitalWrite(R3, HIGH);
    digitalWrite(R4, HIGH);
  }
  else if (steeringState == 1) {
    // LEFT
    digitalWrite(R1, LOW);
    digitalWrite(R2, LOW);
    digitalWrite(R3, HIGH);
    digitalWrite(R4, HIGH);
  }
  else if (steeringState == 2) {
    // RIGHT
    digitalWrite(R1, HIGH);
    digitalWrite(R2, HIGH);
    digitalWrite(R3, LOW);
    digitalWrite(R4, LOW);
  }
}


/* =======================
           SETUP
   ======================= */
void setup() {
  Serial.begin(115200);

  pinMode(R1, OUTPUT);
  pinMode(R2, OUTPUT);
  pinMode(R3, OUTPUT);
  pinMode(R4, OUTPUT);

  applySteeringState();  // start straight
  dacWrite(dacPin, level);

  Serial.println("Controls: W/S = throttle, A/D = steering, X = straighten");
}


/* =======================
           LOOP
   ======================= */
void loop() {

  if (Serial.available() > 0) {
    char input = Serial.read();

    /* =======================
         THROTTLE CONTROL
       ======================= */
    if (input == 'w' || input == 'W') {
      if (level < 50) level = 50;
      else level = min(level + 10, 255);
      dacWrite(dacPin, level);
      Serial.println("Speed Up");
    }

    else if (input == 's' || input == 'S') {
      level = max(level - 30, 0);
      dacWrite(dacPin, level);
      Serial.println("Speed Down");
    }

    else if (input == ' ') {
      level = 0;
      dacWrite(dacPin, 0);
      Serial.println("STOP");
    }


    /* =======================
         STEERING CONTROL
       ======================= */
    else if (input == 'A' || input == 'a') {
      steeringState = 1;      // LEFT
      applySteeringState();
      Serial.println("LEFT ACTIVE");
    }

    else if (input == 'D' || input == 'd') {
      steeringState = 2;      // RIGHT
      applySteeringState();
      Serial.println("RIGHT ACTIVE");
    }

    else if (input == 'X' || input == 'x') {
      steeringState = 0;      // STRAIGHT
      applySteeringState();
      Serial.println("STRAIGHT");
    }


    /* =======================
         FILTER READ
       ======================= */
    int rawADC = analogRead(filterOutPin);
    float voltage = (rawADC / 4095.0) * 3.3;

    Serial.print("Throttle = ");
    Serial.print(level);
    Serial.print(" | Steering = ");
    Serial.print(steeringState == 0 ? "Straight" : (steeringState == 1 ? "Left" : "Right"));
    Serial.print(" | Filter ADC = ");
    Serial.print(rawADC);
    Serial.print(" | Voltage = ");
    Serial.println(voltage, 3);
  }
}
