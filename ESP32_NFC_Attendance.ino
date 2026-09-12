/*
  Smart NFC Attendance System - ESP32
  Hardware:
    ESP32 NodeMCU (CP2102 / ESP32-WROOM-32)
    RC522 RFID/NFC reader

  RC522 -> ESP32
    SDA/SS -> GPIO 5
    SCK    -> GPIO 18
    MOSI   -> GPIO 23
    MISO   -> GPIO 19
    RST    -> GPIO 22
    3.3V   -> 3V3
    GND    -> GND
    IRQ    -> Not connected

  Serial:
    USB connection to laptop
    Baud rate: 115200

  What it does:
    - Waits for an NFC/RFID card
    - Reads its UID
    - Prints the UID to Serial
    - Sends ONLY the UID as one line, ready for the Python attendance program
    - Prevents repeated reads of the same card for a short period

  IMPORTANT:
    The RC522 is a 3.3V device. Do NOT power it from 5V.
*/

#include <SPI.h>
#include <MFRC522.h>

// -------------------- PIN DEFINITIONS --------------------

#define SS_PIN   5
#define RST_PIN  22

// ESP32 VSPI pins
#define SCK_PIN  18
#define MISO_PIN 19
#define MOSI_PIN 23

// -------------------- NFC READER -------------------------

MFRC522 rfid(SS_PIN, RST_PIN);

// Prevent the same card from being read repeatedly
String lastUID = "";
unsigned long lastReadTime = 0;

// Minimum time between accepting the same card
const unsigned long READ_COOLDOWN = 3000;


// -------------------- SETUP ------------------------------

void setup() {

  Serial.begin(115200);

  delay(1000);

  Serial.println();
  Serial.println("=================================");
  Serial.println(" SMART NFC ATTENDANCE SYSTEM");
  Serial.println(" ESP32 + RC522");
  Serial.println("=================================");

  // Start SPI using the ESP32 VSPI pins
  SPI.begin(
    SCK_PIN,
    MISO_PIN,
    MOSI_PIN,
    SS_PIN
  );

  // Start RC522
  rfid.PCD_Init();

  delay(100);

  // Display reader information
  rfid.PCD_DumpVersionToSerial();

  Serial.println();
  Serial.println("NFC reader ready.");
  Serial.println("Scan an NFC/RFID card...");
  Serial.println();
}


// -------------------- MAIN LOOP ---------------------------

void loop() {

  // Check whether a new card is present
  if (!rfid.PICC_IsNewCardPresent()) {
    delay(50);
    return;
  }

  // Read the card serial number
  if (!rfid.PICC_ReadCardSerial()) {
    delay(50);
    return;
  }

  // Build UID string
  String uid = "";

  for (byte i = 0; i < rfid.uid.size; i++) {

    if (rfid.uid.uidByte[i] < 0x10) {
      uid += "0";
    }

    uid += String(
      rfid.uid.uidByte[i],
      HEX
    );

    if (i < rfid.uid.size - 1) {
      uid += " ";
    }
  }

  // Convert UID to uppercase
  uid.toUpperCase();

  unsigned long currentTime = millis();

  // Prevent repeated scans of the same card
  if (
    uid == lastUID &&
    currentTime - lastReadTime < READ_COOLDOWN
  ) {

    rfid.PICC_HaltA();
    rfid.PCD_StopCrypto1();

    delay(200);
    return;
  }

  // Save last UID
  lastUID = uid;
  lastReadTime = currentTime;


  // ---------------- SERIAL OUTPUT ----------------

  Serial.println();
  Serial.println("Card detected!");
  Serial.print("UID: ");
  Serial.println(uid);

  // This line is important:
  // The Python program will eventually read this UID.
  Serial.println(uid);

  Serial.println();


  // Stop communication with the card
  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();

  delay(300);
}
