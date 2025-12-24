# Arduino 2D Pan-Tilt Control System + AI Mosquito Auto-Tracking

![Version](https://img.shields.io/badge/version-2.3.0-blue.svg)
![AI](https://img.shields.io/badge/AI-YOLOv8-brightgreen.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-Arduino%20%2B%20Orange%20Pi%205-red.svg)

An Arduino-based 2D Pan-Tilt control system integrated with dual USB cameras and **AI deep learning (YOLOv8)** technology for intelligent mosquito detection, tracking, and laser marking.

## 📜 Version History

### v2.3.0 (2025-12-25) 🚀 Stability Upgrade
- Firmware: Memory optimization (fixed buffers), function modularization (↓75% code), watchdog timer (2s), timeout protection
- Python: Complete exception handling, controller retry mechanism, graceful error degradation
- Results: Exception protection ~20% → ~95%, Flash reduced by 2-3KB

---

### v2.2.0 (2025-12-24) 📚 Documentation Enhancement
- Document-code consistency check (100/100 score)
- AI parameter standardization (`confidence: 0.4`, `imgsz: 320`)
- Automatic model search mechanism (RKNN → ONNX → PyTorch)

---

### v2.0.0 (2025-12-20) 🤖 AI Integration
- YOLOv8 mosquito detection (RKNN/ONNX/PyTorch multi-backend, Orange Pi 5 NPU acceleration)
- Intelligent tracking system (confidence filtering, multi-target locking, PID control)
- Stereo vision (3840×1080 @ 60fps) + laser marking

---

### v1.0.0 (2025-12-10) 🏗️ Initial Release
- Arduino 2D pan-tilt control, UART communication (115200)
- Bus servo support (LX-16A/SCS15)
- JSON format response, automatic ID scanning

---

## 📋 Table of Contents

- [Version History](#version-history)
- [Features](#features)
- [System Architecture](#system-architecture)
- [Hardware Requirements](#hardware-requirements)
- [Software Requirements](#software-requirements)
- [Installation](#installation)
- [Hardware Connection](#hardware-connection)
- [Usage](#usage)
- [Communication Protocol](#communication-protocol)
- [Project Structure](#project-structure)
- [Development Guide](#development-guide)

## ✨ Features

### Arduino Pan-Tilt Control

- ✅ Dual-axis servo control (Pan horizontal & Tilt vertical)
- ✅ UART serial communication (115200 baud)
- ✅ **Firmware stability enhancements** (v2.3.0):
   - ✅ Memory optimization: Fixed buffers, no heap fragmentation
   - ✅ Parameter validation: Complete input checking and error handling
   - ✅ Modular architecture: 13 dedicated command handler functions
   - ✅ Timeout protection: 2-second timeout for aggregate commands
   - ✅ Watchdog: 2-second automatic restart protection
- ✅ **Operating modes**:
   - ✅ **Initial static**: Tilt fixed at 90°, pan centered, waiting for detection
   - 🎮 **Manual tracking**: Controlled by host computer for precise tracking
- ✅ Absolute and relative position movement
- ✅ Adjustable speed control (1-100)
- ✅ Auto return to home position
- ✅ Calibration function
- ✅ Bus servo feedback: Position reading, temperature monitoring, voltage detection
- ✅ JSON format response

### Python AI Vision Tracking System

- 🎥 **Dual USB camera support**: Left and right camera synchronized capture (3840×1080 @ 60fps)
- 🤖 **AI mosquito intelligent recognition** (YOLOv8):
  - Deep learning object detection
  - High accuracy mosquito identification
  - Confidence scoring and filtering
  - CPU/NPU inference support (Orange Pi 5 optimized)
- 🎯 **Intelligent tracking**:
  - AI detects mosquito → Automatically switches to tracking mode
  - Real-time offset calculation and pan-tilt control for target alignment
  - Low confidence/target lost → Automatically switches back to monitoring mode
- 📊 **Visual display**: Real-time display of AI detection results, bounding boxes, confidence scores
- 🔧 **Adjustable parameters**: AI model path, confidence threshold, input resolution, tracking gain

## 🏗️ System Architecture

```
┌──────────────────┐
│  Dual USB Cameras│ (3840×1080 @ 60fps)
└────────┬─────────┘
         │ Image Capture
         ▼
┌──────────────────┐
│  AI Mosquito     │ (YOLOv8 Deep Learning)
│  Detector        │ (Confidence + Bounding Box)
└────────┬─────────┘
         │ Target Coordinates + Confidence
         ▼
┌──────────────────┐
│  AI Tracking     │ (Intelligent Tracking + PID Control)
│  Controller      │ (Confidence Filtering)
└────────┬─────────┘
         │ Serial Commands (TX/RX)
         ▼
┌──────────────────┐
│  Arduino Pan-Tilt│ (Initial Static / AI Tracking)
│  PT2D Controller │
└──────────────────┘
```

### AI Workflow

1. **Monitoring Phase**: Pan-tilt stays centered (Pan=center, Tilt=90°), AI continuously analyzes images
2. **AI Recognition Phase**: YOLOv8 model detects mosquito, outputs bounding box and confidence
3. **Confidence Filtering**: Only tracks high-confidence targets > threshold (e.g., 0.4)
4. **Tracking Phase**: Calculates offset and controls pan-tilt for alignment, continuous tracking
5. **Laser Marking**: Target near center + high confidence → Activates laser marking
6. **Target Lost**: Low confidence or no detection → Returns to monitoring mode

## 🔧 Hardware Requirements

### Main Controller

| Component | Specification | Quantity | Note |
|-----------|---------------|----------|------|
| **Orange Pi 5** | 8GB RAM | 1 | Main controller, runs vision recognition |
| Power Supply | 5V/4A USB-C | 1 | Orange Pi 5 power |

### Vision System

| Component | Specification | Quantity | Note |
|-----------|---------------|----------|------|
| **Dual Cameras** | 1080p USB | 2 | Left and right cameras, field detection |

### Pan-Tilt Control System

| Component | Specification | Quantity | Note |
|-----------|---------------|----------|------|
| Arduino Board | Nano | 1 |  |
| **2D Pan-Tilt** | Metal/Plastic | 1 | With servo mounts, camera support |
| **Bus Servos** | LX-16A/SCS15/HTS | 2 | Pan & Tilt axis, serial servos |
| Servo Power | **6V-8.4V / 2A** | 1 | Recommended 7.4V Li-Po battery |

### Laser Marking System

| Component | Specification | Quantity | Note |
|-----------|---------------|----------|------|
| **Laser Module** | 1mW Red Laser | 1 | Target marking (safety class) |
| Dupont Wires | Male-Female | Several | GPIO connection |

## 💻 Software Requirements

### Orange Pi 5

- **OS**: Ubuntu 22.04 LTS (ARM64) or Armbian
- **Python**: 3.8+ (usually pre-installed)
- **Required Packages**:
  - OpenCV (`opencv-python`)
  - PySerial (`pyserial`)
  - NumPy (`numpy`)
  - RPi.GPIO or OrangePi.GPIO (GPIO control)

```bash
# Orange Pi 5 Installation
sudo apt update
sudo apt install python3-pip python3-opencv
pip3 install -r python/requirements.txt
pip3 install OrangePi.GPIO  # GPIO control for laser
```

### Arduino

- [PlatformIO IDE](https://platformio.org/) or [Arduino IDE](https://www.arduino.cc/en/software)
- USB driver (CH340/CP2102, etc.)

### Development (Optional)

- For development and testing, Windows/Linux PC can be used
- Python 3.8+
- Same Python packages

## 📦 Installation

### 1. Upload Arduino Firmware

#### Using PlatformIO (Recommended)

```bash
# Clone repository
git clone https://github.com/majeff/mosquito-pt2d.git
cd mosquito-pt2d

# Upload firmware
platformio run --target upload
```

#### Using Arduino IDE

Refer to [docs/arduino_ide_guide.md](docs/arduino_ide_guide.md)

### 2. Orange Pi 5 System Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install python3-pip python3-opencv git -y

# Clone project
git clone https://github.com/majeff/mosquito-pt2d.git
cd mosquito-pt2d/python

# Install Python dependencies
pip3 install -r requirements.txt
pip3 install OrangePi.GPIO
```

### 3. Hardware Connection

Refer to [docs/hardware.md](docs/hardware.md)

**Key Points:**
- **Orange Pi 5** is the main controller, runs all Python programs
- Orange Pi 5 connects to Arduino Nano via GPIO UART (TXD→D0(RX), RXD←D1(TX, needs level conversion 5V→3.3V))
- Dual **1080p cameras** connect to Orange Pi 5 via USB 3.0
- Bus servos connect to Arduino via software serial (Nano D10/D11 → Servo bus)
- **1mW laser module** is 2-wire (VCC/GND) type: Default controlled by MOSFET/driver via GPIO;
   If module is 3.3V and measured steady current ≤8~10mA, direct GPIO power can be considered (assess risk), otherwise use MOSFET
- Servos need independent power (6V-8.4V)
- All GND must be common (Orange Pi, Arduino, servo, laser)
- Alternative connection: If Arduino's USB connects to Orange Pi, no level conversion needed (device is `/dev/ttyUSB*`/`/dev/ttyACM*`)
- Controller board note: When using "6-channel robot arm servo controller board", UART is usually 5V TTL; if no 3.3/5V jumper or level conversion, use USB connection or add level conversion on Arduino TX→Orange Pi RX path

### 4. Test Hardware Connection

```bash
# Test camera
python3 stereo_camera.py

# Test Arduino communication
python3 pt2d_controller.py

# Test GPIO laser control (needs sudo)
sudo python3 laser_controller.py

# Test mosquito detection
python3 mosquito_detector.py
```

---

## 🚀 Usage

### Quick Start

1. **Upload Arduino firmware** (refer to installation instructions above)

2. **Test each module**:

```bash
cd python

# Test camera
python3 stereo_camera.py

# Test mosquito detection
python3 mosquito_detector.py

# Test Arduino communication
python3 pt2d_controller.py
```

3. **Run tracking system**:

```bash
sudo python3 mosquito_tracker.py
```

### Operation Guide

After running `mosquito_tracker.py`:

**Hotkeys:**
- `q`: Exit system
- `r`: Reset detector
- `h`: Return to home position
- `l`: Toggle laser
- `SPACE`: Laser pulse (0.2s marking pulse)

**Windows:**
- **Mosquito Tracker**: Main window, displays detection and tracking results
- **Detection Mask**: Detection mask window for debugging

**Status Indicators:**
- **TRACKING** (red): Tracking mode

### Configuration Parameters

Edit `python/mosquito_tracker.py`:

```python
# Arduino serial port
ARDUINO_PORT = 'COM3'  # Windows
# For Orange Pi 5 (GPIO UART direct), use /dev/ttyS*, e.g.:
# ARDUINO_PORT = '/dev/ttyS1'  # Linux (confirm actual node with dmesg/ls)

# Camera IDs
LEFT_CAMERA_ID = 0
RIGHT_CAMERA_ID = 1

# AI detection parameters
detector = MosquitoDetector(
    model_path=None,                           # Auto-search model (.rknn → .onnx → .pt)
    confidence_threshold=0.4,                  # Confidence threshold (recommended 0.3-0.7)
    imgsz=320                                  # Input resolution (320/416/640)
)

# Tracking parameters
self.pan_gain = 0.15                # Pan gain (control sensitivity)
self.tilt_gain = 0.15               # Tilt gain (control sensitivity)
self.no_detection_timeout = 3.0     # No detection timeout (seconds)
self.target_lock_distance = 100     # Target lock distance (pixels)
self.beep_cooldown = 2.0            # Beep cooldown time (seconds)
self.laser_cooldown = 0.5           # Laser cooldown time (seconds)
self.position_update_interval = 0.5 # Position update interval (seconds)
```

---

## ⚙️ Servo Configuration

### 1. Confirm Servo IDs

Use manufacturer's debugging software or code to confirm servo IDs:
- Pan axis servo: ID = 1
- Tilt axis servo: ID = 2

### 2. Modify config.h

```cpp
// Serial configuration
#define SERIAL_BAUDRATE     115200    // Host serial baud rate
#define SERVO_BAUDRATE      115200    // Servo bus baud rate (LX-16A: 115200, SCS: 9600/1000000)

// Servo IDs (system auto-scans, can also be manually specified)
#define DEFAULT_PAN_SERVO_ID    1     // Pan axis servo ID (default)
#define DEFAULT_TILT_SERVO_ID   2     // Tilt axis servo ID (default)
#define AUTO_DETECT_SERVO_ID    true  // Auto-scan servo IDs on startup

// Servo angle ranges
#define PAN_MAX_ANGLE       270       // Pan horizontal max angle
#define TILT_MAX_ANGLE      180       // Tilt vertical max angle
#define PAN_INIT_ANGLE      135       // Pan initial angle (horizontal center)
#define TILT_INIT_ANGLE     90        // Tilt initial angle (vertical center)

// Movement parameters
#define DEFAULT_SPEED       50        // Default movement speed (1-100)
#define MIN_SPEED           1         // Minimum speed
#define MAX_SPEED           100       // Maximum speed

// Auto-scan configuration
#define SERVO_DETECT_TIMEOUT    500   // Servo scan timeout (milliseconds)
#define SERVO_DETECT_INTERVAL   100   // Servo scan interval (milliseconds)
```

---

## 🔌 Hardware Connection

Detailed connection diagram: [docs/hardware.md](docs/hardware.md)

### Pin Configuration

#### Orange Pi 5 ↔ Arduino Nano (UART Direct)

```
Connection         | Description
-------------------|--------------------------------------
Orange Pi TXD      | → Arduino D0 (RX0)
Orange Pi RXD      | ← Arduino D1 (TX0, with level conversion 5V→3.3V)
Common Ground      | Orange Pi GND ↔ Arduino GND ↔ Servo Power GND
Nano D10 (TX)      | → Servo Bus RX (yellow wire)
Nano D11 (RX)      | ← Servo Bus TX (green wire)
6V-8.4V            | → Servo VCC (external power)
```

### Complete System Connection

```
[Orange Pi 5]
   ├─ UART (GPIO) ──> [Arduino Nano] ──(D10/D11)──> [Servo Bus] ──> [Pan Servo + Tilt Servo]
   ├─ USB 3.0 ─────> [Left Camera 1080p]
   ├─ USB 3.0 ─────> [Right Camera 1080p]
   └─ GPIO Pin 5 ──> [MOSFET Gate] (GPIO controls laser power)

[Servo Power 6V-8.4V] ──> [Servo Bus VCC]
                              └─> GND ──(common)──> [Arduino GND] ──> [Orange Pi GND]

[2-wire laser (no EN)]:
   3.3V (Pin 1) or 5V (Pin 2/4) ──> Laser VCC (via MOSFET-controlled power path)
   GPIO Pin 5  ───> MOSFET Gate (100Ω series, 10k pull-down to ground)
   GND (Pin 6/9) ─> MOSFET Source and system common ground; Laser GND connects to MOSFET Drain (low-side switch)
```

**System Architecture Diagram**: (See "Complete System Connection" and pin configuration above)

**GPIO Mapping (OrangePi.GPIO library)**:
- Physical Pin 5 = GPIO 3 = Use Pin 5 in program with `GPIO.setmode(GPIO.BOARD)`

Note:
- 2-wire laser needs MOSFET in power path; GPIO only for logic control, not direct power.
- If laser is 5V or high current, must use MOSFET/driver; ensure common ground and add gate pull-down and protection resistor.

### ⚠️ Important Notes

1. **Independent Power**: Bus servos need **6V-8.4V** power (recommended 7.4V Li-Po battery)
2. **Common Ground**: Ensure Orange Pi, Arduino, servo, laser module all GND connected together
3. **Serial Selection**: Nano host communication uses D0/D1 (hardware UART), servo bus uses D10/D11 (SoftwareSerial)
4. **Servo IDs**: Default Pan=ID1, Tilt=ID2, confirm servo ID settings first
5. **Cameras**: Dual 1080p cameras connect to Orange Pi 5 via USB 3.0
6. **Laser Safety**: Use 1mW red laser (Class II), avoid direct viewing, pay attention to direction during installation
7. **USB Power**: Orange Pi 5 uses USB-C 5V/4A power, ensure sufficient current
8. **Cooling**: Orange Pi 5 recommended to add heatsink or fan

---

## 📖 Communication Protocol

### Arduino Command Format

Command format: `<CMD:param1,param2,...>\n`

| Command | Parameters | Description | Example |
|---------|------------|-------------|---------|
| `MOVE` | pan, tilt | Move to absolute position | `<MOVE:135,90>` |
| `MOVER` | delta_pan, delta_tilt | Relative movement | `<MOVER:20,-10>` |
| `POS` | - | Get current position | `<POS>` |
| `SPEED` | value | Set speed (1-100) | `<SPEED:80>` |
| `HOME` | - | Return to home position | `<HOME>` |
| `STOP` | - | Stop movement | `<STOP>` |
| `CAL` | - | Execute calibration | `<CAL>` |

### Response Format

JSON format: `{"key":"value"}\n`

```json
// Success response
{"status":"ok","message":"OK"}

// Position response
{"pan":135,"tilt":90}

// Error response
{"status":"error","message":"Unknown command"}
```

### Python API

See [docs/python_README.md](docs/python_README.md)

---

## 📖 Basic Operation Examples

### 1. Orange Pi 5 System Test

```bash
# Test camera
cd python
python3 stereo_camera.py

# Test Arduino communication
python3 pt2d_controller.py

# Test laser control (needs sudo)
sudo python3 laser_controller.py

# Test mosquito detection
python3 mosquito_detector.py
```

### 2. Run Complete Tracking System

```bash
# On Orange Pi 5
cd python
sudo python3 mosquito_tracker.py

# Or use quick start script
sudo python3 quick_start.py
```

### 3. Arduino Serial Test

Test Arduino via serial monitor (baud rate 115200):

```bash
# Move to absolute position (Pan=135°, Tilt=90°)
<MOVE:135,90>

# Relative movement (Pan+20°, Tilt-10°)
<MOVER:20,-10>

# Get current position
<POS>

# Set movement speed to 80
<SPEED:80>

# Return to home position
<HOME>

# Stop movement
<STOP>

# Execute calibration
<CAL>
```

### 4. System Operation Hotkeys

While tracking system is running:

| Hotkey | Function | Description |
|--------|----------|-------------|
| `q` | Exit system | Safely close all resources |
| `r` | Reset detector | Clear detection history |
| `h` | Return to home | Pan-tilt home position |
| `l` | Toggle laser | Manual laser on/off |
| `SPACE` | Laser pulse | 0.2s marking pulse |

---

## 🎯 System Workflow

### Complete AI Tracking Loop

```
1. [Monitoring Phase]
   └─> Pan-tilt stays centered (Pan center / Tilt 90°)
   └─> YOLOv8 AI continuously analyzes images

2. [AI Recognition Phase]
   └─> YOLOv8 detects mosquito (deep learning)
   └─> Outputs bounding box and confidence score

3. [Confidence Filtering]
   └─> Check confidence > threshold (e.g., 0.4)
   └─> Filter low-confidence false positives

4. [Tracking Phase] ⭐ Continuous tracking
   └─> Calculate target offset
   └─> PID control pan-tilt for target alignment
   └─> Continuous AI tracking, real-time target position update
   └─> **Multi-target handling**: Lock onto single target for continuous tracking
      ├─ When multiple mosquitoes in frame, select highest confidence target
      ├─ After locking target, maintain tracking that target (won't jump to others)
      ├─ Use position tracking (100px range) to ensure tracking same mosquito
      └─ Only after losing current target will select new target
   └─> Even if temporarily lose target, maintain tracking state for 3s
   └─> When target reappears, immediately resume tracking

5. [Marking Phase]
   └─> Target enters center area (±30px) + high confidence
   └─> Activate laser marking
   └─> Green circle marks center area

6. [Target Lost] ⚠️ Timeout mechanism
   └─> 3 seconds continuous no detection (prevent false positives)
   └─> Turn off laser
   └─> Return to monitoring mode (return to center position)
```

---

## 🛠️ Troubleshooting

### Orange Pi 5 Related Issues

#### 1. GPIO Permission Denied

**Error**: `PermissionError: [Errno 13] Permission denied`

**Solutions**:
```bash
# Method 1: Use sudo
sudo python3 mosquito_tracker.py

# Method 2: Add to gpio group
sudo usermod -a -G gpio $USER
# Logout and login again

# Method 3: Set GPIO permission rules
sudo nano /etc/udev/rules.d/99-gpio.rules
# Add: SUBSYSTEM=="gpio", MODE="0660", GROUP="gpio"
sudo udevadm control --reload-rules
```

#### 2. Camera Cannot Open

**Check methods**:
```bash
# List devices
ls -l /dev/video*

# Test camera
v4l2-ctl --list-devices

# Check permissions
sudo chmod 666 /dev/video0
sudo chmod 666 /dev/video1
```

#### 3. Arduino Cannot Connect

**Check methods**:
```bash
# List serial devices
ls -l /dev/ttyUSB* /dev/ttyACM*

# Check connection
dmesg | grep tty

# Set permissions
sudo chmod 666 /dev/ttyS1   # Adjust to your actual device node
sudo usermod -a -G dialout $USER
```

### Laser Related Issues

#### 1. Laser Cannot Start

**Check items**:
- Check GPIO pin is correct (physical Pin 5, BOARD mode)
- Confirm laser module is 3.3V, low current type (recommended ≤10mA), and common ground
- Use multimeter to measure Pin 5 voltage switching on ON/OFF
- If module needs 5V or high current, use MOSFET/driver, do not connect directly to GPIO

**Test command**:
```bash
sudo python3 laser_controller.py
```

#### 2. Laser Always On Cannot Turn Off

**Emergency procedure**:
```bash
# Immediately close all GPIO
sudo python3 -c "import OPi.GPIO as GPIO; GPIO.setmode(GPIO.BOARD); GPIO.setup(5, GPIO.OUT); GPIO.output(5, GPIO.LOW); GPIO.cleanup()"
```

### AI Detection Poor Performance

**Improvement suggestions**:
1. **Use mosquito-specific model** - See [docs/MOSQUITO_MODELS.md](docs/MOSQUITO_MODELS.md)
2. **Increase lighting** - Ensure sufficient ambient light (minimum 0.5 lux)
3. **Adjust AI parameters**:
   ```python
   detector = MosquitoDetector(
       model_path='models/mosquito_yolov8n.pt',  # Use specific model
       confidence_threshold=0.3,                  # Lower threshold (0.3-0.5)
       imgsz=320                                  # Optimize speed (320/416/640)
   )
   ```
4. **Reduce resolution** - Improve AI inference speed
   ```python
   detector = MosquitoDetector(imgsz=320)  # From 640 down to 320
   ```
5. **Convert to ONNX/RKNN** - See [docs/AI_DETECTION_GUIDE.md](docs/AI_DETECTION_GUIDE.md)

---

## 📁 Project Structure

```
mosquito-pt2d/
├── src/
│   └── main.cpp              # Bridge firmware main program
├── include/
│   └── config.h              # Configuration file (serial, servo IDs, angle ranges)
├── python/                   # Python AI tracking system
│   ├── pt2d_controller.py    # Arduino serial controller
│   ├── mosquito_tracker.py   # AI tracking main program
│   ├── mosquito_detector.py  # YOLOv8 mosquito detector
│   ├── stereo_camera.py      # Dual camera control
│   ├── laser_controller.py   # Laser control (GPIO)
│   └── quick_start.py        # Quick start script
├── models/                   # AI model directory
│   └── mosquito.pt           # YOLOv8 mosquito detection model
├── docs/                     # Documentation directory
│   ├── hardware.md           # Hardware connection instructions
│   ├── protocol.md           # Communication protocol details
│   ├── python_example.md     # Python control examples
│   └── arduino_ide_guide.md  # Arduino IDE usage guide
├── platformio.ini            # PlatformIO configuration
├── .gitignore               # Git ignore file
└── README.md                # This file (Chinese version)
```

## 🛠 Development Guide

### Modify Configuration

Edit [include/config.h](include/config.h) file to modify:

- Pin definitions
- Angle ranges
- Movement speed
- Serial baud rate
- Debug options

### Add New Features

**Firmware side (Arduino)**:
1. Add new command parsing in `handlePcLine()` function in `src/main.cpp`
2. Implement command logic and send corresponding bus commands
3. Update `docs/protocol.md` protocol documentation

**Python side**:
1. Add corresponding convenience methods in `python/pt2d_controller.py`
2. Update `mosquito_tracker.py` to use new features
3. Update documentation

### Debugging Tips

```cpp
// Enable debug mode in config.h
#define DEBUG_MODE true

// Use debug macros
DEBUG_PRINTLN("Current position: ");
DEBUG_PRINT(panAngle);
```

## 🐛 Common Issues

### Q1: Servo shaking or unstable

**A**: Check if power supply is sufficient, recommend using external power supply and add filter capacitor.

### Q2: Serial communication fails

**A**: Confirm baud rate is set to 115200, check if TX/RX connection is correct.

### Q3: Program upload fails

**A**: Disconnect TX/RX connection before upload, reconnect after upload complete.

### Q4: Angle range incorrect

**A**: Execute calibration command `<CAL>`, or adjust angle range in `config.h`.

---

## 📚 Complete Documentation Index

### 📖 Core Documents

| Document | Description |
|----------|-------------|
| [README.md](README.md) | Project main documentation (Chinese) |
| [README_EN.md](README_EN.md) | Project main documentation (English, this file) |
| [CONSISTENCY_CHECK.md](CONSISTENCY_CHECK.md) | Document-code consistency check report |
| [LICENSE](LICENSE) | MIT License |

### 🔧 Hardware & Configuration Documents

| Document | Description |
|----------|-------------|
| [docs/hardware.md](docs/hardware.md) | Hardware connection detailed instructions (with wiring diagrams) |
| [docs/orangepi5_hardware.md](docs/orangepi5_hardware.md) | Orange Pi 5 hardware configuration guide |
| [docs/protocol.md](docs/protocol.md) | Serial communication protocol technical specifications |
| [docs/arduino_ide_guide.md](docs/arduino_ide_guide.md) | Arduino IDE compilation and upload guide |

### 🤖 AI & Python Documents

| Document | Description |
|----------|-------------|
| [docs/AI_DETECTION_GUIDE.md](docs/AI_DETECTION_GUIDE.md) | AI detection system detailed guide |
| [docs/MOSQUITO_MODELS.md](docs/MOSQUITO_MODELS.md) | Mosquito detection model description and download |
| [docs/python_example.md](docs/python_example.md) | Python example programs and usage tutorial |
| [docs/python_README.md](docs/python_README.md) | Python module navigation documentation |
| [python/README.md](python/README.md) | Python program directory description |

### 🧪 Test & Validation Documents

| Document | Description |
|----------|-------------|
| [python/test_serial_protocol.py](python/test_serial_protocol.py) | Serial protocol test script |
| [python/test_tracking_logic.py](python/test_tracking_logic.py) | Tracking logic validation script |
| [python/test_multi_target_tracking.py](python/test_multi_target_tracking.py) | Multi-target tracking test script |

### 📁 Code Files

| File | Description |
|------|-------------|
| [include/config.h](include/config.h) | Arduino firmware configuration parameters |
| [src/main.cpp](src/main.cpp) | Arduino bridge firmware main program |
| [python/mosquito_tracker.py](python/mosquito_tracker.py) | Main tracking system |
| [python/mosquito_detector.py](python/mosquito_detector.py) | AI detector module |
| [python/pt2d_controller.py](python/pt2d_controller.py) | Arduino controller interface |
| [python/stereo_camera.py](python/stereo_camera.py) | Dual camera module |
| [python/laser_controller.py](python/laser_controller.py) | Laser control module |
| [python/quick_start.py](python/quick_start.py) | Quick start script |

**Tip**: All documents are written in Markdown format and can be read directly on GitHub or any Markdown editor.

---

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file

## 👥 Contributing

Issues and Pull Requests are welcome!

## 📧 Contact

For questions or suggestions, please contact via:

- Email: jeff@ma7.in
- GitHub Issues: [Submit Issue](https://github.com/majeff/mosquito-pt2d/issues)

## 🙏 Acknowledgments

Thanks to all developers who contributed to this project!

---

**Built with ❤️ for Arduino Community**
