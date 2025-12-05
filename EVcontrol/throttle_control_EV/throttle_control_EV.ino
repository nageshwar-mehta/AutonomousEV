int dacPin = 25;        // DAC output pin
int level = 0;

int filterOutPin = 34;  // ADC pin where filter output is connected

void setup() {
  Serial.begin(115200);
  Serial.println("Controls: W=up, S=down, SPACE=0");

  dacWrite(dacPin, 0);              // initialize DAC
  analogReadResolution(12);         // ESP32 ADC resolution: 0–4095
}

void loop() {

  if (Serial.available()) {
    char c = Serial.read();

    // Increase value
    if (c == 'w' || c == 'W') {
      if (level < 100) {
        level += 10;
      } else {
        level += 30;
        if (level > 255) level = 255;
      }
    }

    // Decrease value
    if (c == 's' || c == 'S') {
      level -= 30;
      if (level < 0) level = 0;
    }

    // Reset
    if (c == ' ') {
      level = 0;
    }

    // Write to DAC
    dacWrite(dacPin, level);

    // Read filter output using ADC
    int filterOutRaw = analogRead(filterOutPin);

    // Convert ADC (0–4095) → voltage (0–3.3V)
    float filterVoltage = (filterOutRaw / 4095.0) * 3.3;

    // Print everything
    Serial.print("DAC value: ");
    Serial.print(level);
    Serial.print(" | Filter ADC: ");
    Serial.print(filterOutRaw);
    Serial.print(" | Filter Voltage: ");
    Serial.println(filterVoltage, 3);
  }
}
