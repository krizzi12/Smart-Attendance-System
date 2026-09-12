# Smart NFC Attendance System

ESP32 + RC522 + Python + SQLite

## Overview

The Smart NFC Attendance System is an end-to-end attendance platform that uses an RC522 RFID/NFC reader to identify a supported card/tag, an ESP32 microcontroller to read its UID, and a Python desktop application to register students, record attendance, search records, and export attendance data to CSV.

### Data flow

```text
NFC/RFID Card
     ↓
RC522
     ↓ SPI
ESP32
     ↓ USB Serial
Python
     ↓
SQLite
     ↓
GUI / CSV
```

## Hardware

- ESP32 NodeMCU / ESP32-WROOM-32 with CP2102
- RC522 RFID/NFC reader
- Supported 13.56 MHz RFID/NFC card or tag
- Breadboard
- Jumper wires
- USB data cable
- Windows PC/laptop

> **Important:** The RC522 is a 3.3 V device. Do not power it from 5 V.

## RC522 → ESP32 Wiring

| RC522 | ESP32 |
|---|---|
| 3.3V | 3V3 |
| GND | GND |
| SDA / SS | GPIO 5 |
| SCK | GPIO 18 |
| MOSI | GPIO 23 |
| MISO | GPIO 19 |
| RST | GPIO 22 |
| IRQ | Not connected |

## Arduino IDE Setup

### 1. Install Arduino IDE

Download Arduino IDE for Windows from the official Arduino website and install it using the normal installer.

### 2. Add ESP32 support

Open:

**File → Preferences**

Under **Additional boards manager URLs**, add:

```text
https://espressif.github.io/arduino-esp32/package_esp32_index.json
```

Click OK.

Then:

**Tools → Board → Boards Manager**

Search for:

```text
esp32
```

Install:

**esp32 by Espressif Systems**

### 3. Install MFRC522

Open:

**Tools → Manage Libraries**

Search:

```text
MFRC522
```

Install the commonly used MFRC522 library.

### 4. Connect the CP2102 ESP32

Connect the ESP32 using a USB **data** cable.

Open:

**Tools → Port**

Select the new COM port belonging to the ESP32.

The CP2102 is the USB-to-serial bridge; it is not the board name.

### 5. Select the board

For a common ESP32-WROOM-32 / NodeMCU-style board:

**Tools → Board → ESP32 Arduino → ESP32 Dev Module**

## Uploading the ESP32 Sketch

1. Open `ESP32_NFC_Attendance.ino`.
2. Select **ESP32 Dev Module**.
3. Select the correct COM port.
4. Click **Verify** (checkmark).
5. If compilation succeeds, click **Upload**.
6. If it stays at `Connecting...`, hold the **BOOT** button during the connection stage and release when writing starts.
7. Wait for `Done uploading`.

## Serial Monitor

Open:

**Tools → Serial Monitor**

Set the baud rate to:

```text
115200
```

The sketch should show startup information and wait for a card.

Close Serial Monitor before the Python program connects to the same COM port.

## Python Application

The desktop application uses:

- `tkinter` — GUI
- `sqlite3` — database
- `csv` — CSV export
- `datetime` — attendance timestamps
- `pyserial` — ESP32 USB serial communication

### Install Python

Check:

```bash
python --version
```

Install pyserial:

```bash
python -m pip install pyserial
```

The database is stored in:

```text
attendance.db
```

## Application Features

- Student registration
- Manual UID attendance testing
- ESP32 COM port selection
- USB serial connection
- Automatic attendance marking
- Duplicate prevention per day
- Attendance search
- CSV export
- SQLite persistence

## Project Structure

```text
NFC-Attendance-System/
├── ESP32_NFC_Attendance.ino
├── main.py
├── attendance.db
├── attendance.csv
└── README.md
```

`attendance.db` and `attendance.csv` are generated/used by the application and do not necessarily need to be committed to GitHub.

## Software Architecture

```text
                ┌───────────────┐
                │  NFC/RFID Tag │
                └───────┬───────┘
                        │
                        ▼
                ┌───────────────┐
                │     RC522     │
                └───────┬───────┘
                        │ SPI
                        ▼
                ┌───────────────┐
                │     ESP32     │
                └───────┬───────┘
                        │ USB Serial
                        ▼
                ┌───────────────┐
                │ Python / GUI  │
                └───────┬───────┘
                        │
                        ▼
                ┌───────────────┐
                │    SQLite     │
                └───────┬───────┘
                        │
                ┌───────┴────────┐
                ▼                ▼
          Attendance GUI     CSV Export
```

## Database

The system has two main logical data groups:

### Students

Stores information such as:

- UID
- Name
- Roll number
- Class
- Division

### Attendance

Stores:

- Student/UID
- Date
- Attendance timestamp or related attendance information

The application prevents the same student from being marked present repeatedly on the same day.

## Serial Integration

The final ESP32/Python integration should use a machine-readable serial format.

Recommended:

```text
UID:A3 7F 21 9C
```

Python should process only lines beginning with:

```text
UID:
```

This prevents debug messages such as `Card detected!` from being interpreted as attendance IDs.

## Testing Plan

| Test | Expected result |
|---|---|
| ESP32 connects | COM port appears |
| Sketch compiles | No errors |
| Sketch uploads | Upload completes |
| Serial monitor | Startup messages appear |
| RC522 wiring | Reader initializes |
| Card scan | UID is detected |
| Student registration | Student stored |
| Attendance scan | Attendance created |
| Second scan same day | Duplicate prevented |
| Search | Matching records displayed |
| CSV export | Attendance exported |

## Troubleshooting

### COM port not visible

- Try another USB data cable.
- Try another USB port.
- Check Windows Device Manager.
- Check whether the CP2102 driver is available/installed.

### Upload stuck at `Connecting...`

- Confirm the board is `ESP32 Dev Module`.
- Confirm the COM port.
- Hold the BOOT button during the connection stage.

### MFRC522 compile error

- Confirm the MFRC522 library is installed.
- Confirm the correct library is being included.

### RC522 does not work

Recheck:

- 3.3 V
- GND
- SDA/SS
- SCK
- MOSI
- MISO
- RST

Do not power the RC522 from 5 V.

### Python cannot open COM port

Close Arduino Serial Monitor and any other application using the ESP32 COM port.

### Wrong attendance records

Make sure the ESP32 serial protocol and Python parser agree on what constitutes a UID. Use the `UID:` prefix approach described above.

## Development Roadmap

### V1 — Basic reader

RC522 + ESP32 reads UID.

### V2 — Computer integration

ESP32 sends UID to Python over USB serial.

### V3 — Complete attendance system

Add:

- Student registration
- SQLite
- Duplicate prevention
- Search
- CSV export

### V4 — Connected system

Add:

- Wi-Fi
- Web dashboard
- Offline storage
- Synchronization

### V5 — Engineering prototype

Add:

- Custom PCB
- Enclosure
- Polished UI
- Reliability testing
- Better validation
- Full engineering documentation


