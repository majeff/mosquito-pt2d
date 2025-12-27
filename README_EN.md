# Arduino 2D Pan-Tilt Control System + AI Mosquito Auto-Tracking

![Version](https://img.shields.io/badge/version-2.4.0-blue.svg)
![AI](https://img.shields.io/badge/AI-YOLOv8-brightgreen.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-Arduino%20%2B%20Orange%20Pi%205-red.svg)

An Arduino-based 2D Pan-Tilt control system integrated with dual USB cameras and **AI deep learning (OrangePi5+YOLOv8)** technology for intelligent mosquito detection, tracking, and laser marking with real-time monitoring.

## 📜 Version History

### v2.4.0 (2025-12-27) 📱 Real-time Monitoring Upgrade
- New: Video streaming system (HTTP-MJPEG) for real-time mobile viewing
- New: Integrated program `streaming_tracking_system.py` (AI+tracking+streaming in one)
- New: Three dual-camera streaming modes (side-by-side/single/independent)
- New: Web interface with real-time statistics
- Documentation: Complete streaming guide `STREAMING_GUIDE.md`
- Features: All AI annotations (detection boxes, confidence) included in stream

---

### v2.3.0 (2025-12-25) 🚀 Stability Upgrade
- Firmware: Memory optimization (fixed buffers), function modularization (↓75% code), watchdog timer (2s), timeout protection
- Python: Complete exception handling, controller retry mechanism, graceful error degradation
- Results: Exception protection ~20% → ~95%, Flash reduced by 2-3KB

---

### v2.2.0 (2025-12-24) 📚 Documentation Enhancement
- Document-code consistency check (100/100 score)
- AI parameter standardization (`confidence: 0.4`, `imgsz: 640`)
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
- [Nginx Reverse Proxy Configuration](#nginx-reverse-proxy-configuration)
- [Common Issues](#common-issues)
- [Complete Documentation Index](#complete-documentation-index)

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
  - **Automatic uncertain sample saving** (v2.3.1 new):
    - Automatically collects detection samples with medium confidence (0.35-0.65)
    - For subsequent manual review and model retraining
    - Disk usage monitoring (auto-pause when exceeds 20%)
    - Smart filenames with timestamp and confidence information
- 🎯 **Intelligent tracking**:
  - AI detects mosquito → Automatically switches to tracking mode
  - Real-time offset calculation and pan-tilt control for target alignment
  - Low confidence/target lost → Automatically switches back to monitoring mode
- � **Real-time Video Streaming** (v2.4.0 new):
  - HTTP-MJPEG streaming server for real-time mobile browser viewing
  - Complete AI annotations included in stream (detection boxes, confidence, tracking status)
  - Dual camera support (side-by-side display/single view/independent streams)
  - Web interface with real-time statistics (FPS, detections, connections)
  - Multi-client simultaneous viewing support
- �📊 **Visual display**: Real-time display of AI detection results, bounding boxes, confidence scores
- 🔧 **Adjustable parameters**: AI model path, confidence threshold, input resolution, tracking gain

## 🏗️ System Architecture

```
┌──────────────────┐
│  Dual USB Cameras│ (3840×1080 @ 60fps)
└────────┬─────────┘
         │ Image Capture
         ▼
┌──────────────────┐
│  AI Detector      │ (YOLOv8 Deep Learning)
│  mosquito_detector│ (Confidence + Bounding Box)
└────────┬─────────┘
         │ Target Coordinates + Confidence
         ├─────────────────────┐
         │                     │ AI Annotated Image
         ▼                     ▼
┌──────────────────┐  ┌──────────────────┐
│  AI Tracker       │  │  Streaming Server │ 📱
│  mosquito_tracker │  │ StreamingServer  │ → Mobile/Browser
│ (Confidence Filter)│  │ (HTTP-MJPEG)     │    Real-time View
└────────┬─────────┘  └──────────────────┘
         │ Serial Commands (TX/RX)
         ▼
┌──────────────────┐
│  Arduino Pan-Tilt │ (Initial Static / AI Tracking)
│  PT2D Controller  │
└──────────────────┘
```
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
6. **Video Streaming**: Annotated images pushed to streaming server in real-time for mobile viewing
7. **Target Lost**: Low confidence or no detection → Returns to monitoring mode

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
| **Laser Module** | 1mW Red Laser | 1 | Target marking (safety class)<br>Controlled by Arduino |

## 💻 Software Requirements

### Orange Pi 5

- **OS**: Ubuntu 22.04 LTS (ARM64) or Armbian
- **Python**: 3.8+ (usually pre-installed)
- **Required Packages**:
  - OpenCV (`opencv-python`)
  - PySerial (`pyserial`)
  - NumPy (`numpy`)


```bash
# Orange Pi 5 Installation
sudo apt update
sudo apt install python3-pip python3-opencv
pip3 install -r python/requirements.txt

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
```

### 3. Hardware Connection

Refer to [docs/hardware.md](docs/hardware.md)

**Key Points:**
- **Orange Pi 5** is the main controller, runs all Python programs
- Arduino Nano connects to Orange Pi 5 via USB (device is `/dev/ttyUSB*` or `/dev/ttyACM*`)
- Dual **1080p cameras** connect to Orange Pi 5 via USB 3.0
- Bus servos connect to Arduino via software serial (Nano D10/D11 → Servo bus)
- **1mW laser module** is controlled by Arduino, no external MOSFET needed
- Servos need independent power (6V-8.4V)
- All GND must be common (Orange Pi, Arduino, servo, laser)

### 4. Test Hardware Connection

```bash
# Test camera
python3 stereo_camera.py

# Test Arduino communication
python3 pt2d_controller.py

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
# Option A: Complete system (AI + tracking + streaming) ⭐ Recommended
python3 streaming_tracking_system.py
# Open in mobile browser: http://[Orange_Pi_IP]:5000

# Option B: Basic tracking system (no streaming)
python3 mosquito_tracker.py
```

### Operation Guide

#### Option A: Complete System (streaming_tracking_system.py) ⭐ Recommended

```bash
python3 streaming_tracking_system.py
```

**Hotkeys:**
- `q`: Exit system
- `t`: Toggle tracking mode
- `s`: Save screenshot
- `h`: Home pan-tilt

**Mobile Viewing:**
1. Ensure mobile and Orange Pi 5 are on same network
2. Open in browser: `http://[Orange_Pi_IP]:5000`
3. View real-time AI annotated video

**Web Interface Shows:**
- Real-time video (with AI detection boxes, confidence)
- FPS, detection count, tracking status
- Connected client count

---

#### Option B: Basic Tracking System (mosquito_tracker.py)

After running `mosquito_tracker.py`:

**Hotkeys:**
- `q`: Exit system
- `r`: Reset detector
- `h`: Return to home position

**Windows:**
- **Mosquito Tracker**: Main window, displays detection and tracking results
- **Detection Mask**: Detection mask window for debugging

**Status Indicators:**
- **TRACKING** (red): Tracking mode

### Configuration Parameters

System parameters are centrally managed in [python/config.py](python/config.py) for easy modification:

```python
# ============================================
# AI Detection Parameters
# ============================================
DEFAULT_IMGSZ = 640                      # Input resolution (320/416/640, default 640)
DEFAULT_CONFIDENCE_THRESHOLD = 0.4       # Confidence threshold (0.3-0.7)
DEFAULT_IOU_THRESHOLD = 0.45             # IoU threshold

# ============================================
# Tracking Parameters
# ============================================
DEFAULT_PAN_GAIN = 0.15                  # Pan gain (control sensitivity)
DEFAULT_TILT_GAIN = 0.15                 # Tilt gain (control sensitivity)
DEFAULT_NO_DETECTION_TIMEOUT = 3.0       # No detection timeout (seconds)
DEFAULT_TARGET_LOCK_DISTANCE = 100       # Target lock distance (pixels)

# ============================================
# Hardware Parameters
# ============================================
DEFAULT_ARDUINO_PORT = '/dev/ttyUSB0'    # Linux/Orange Pi
# DEFAULT_ARDUINO_PORT = 'COM3'          # Windows
DEFAULT_LEFT_CAMERA_ID = 0
DEFAULT_RIGHT_CAMERA_ID = 1

# ============================================
# Control Parameters
# ============================================
DEFAULT_BEEP_COOLDOWN = 2.0              # Beep cooldown time (seconds)
DEFAULT_LASER_COOLDOWN = 0.5             # Laser cooldown time (seconds)
```

**How to Modify**: Edit `python/config.py` to adjust parameters for all modules.

**Common Adjustments**:
- **Increase Speed**: Set `DEFAULT_IMGSZ` to `320` (sacrifice accuracy)
- **Increase Accuracy**: Set `DEFAULT_IMGSZ` to `800` or `1280` (reduce speed)
- **Adjust Tracking Sensitivity**: Modify `DEFAULT_PAN_GAIN` and `DEFAULT_TILT_GAIN`

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

#### Orange Pi 5 ↔ Arduino Nano (USB Connection)

```
Connection         | Description
-------------------|--------------------------------------
USB                | Orange Pi USB ↔ Arduino Nano USB (CH340/ATmega328P)
Common Ground      | Via USB, also needs common with Servo Power GND
Nano D10 (TX)      | → Servo Bus RX (yellow wire)
Nano D11 (RX)      | ← Servo Bus TX (green wire)
6V-8.4V            | → Servo VCC (external power)
```

### Complete System Connection

```
[Orange Pi 5]
   ├─ USB ─────────> [Arduino Nano] ──(D10/D11)──> [Servo Bus] ──> [Pan Servo + Tilt Servo]
   ├─ USB 3.0 ─────> [Left Camera 1080p]
   └─ USB 3.0 ─────> [Right Camera 1080p]

[Servo Power 6V-8.4V] ──> [Servo Bus VCC]
                              └─> GND ──(common)──> [Arduino GND] ──> [Orange Pi GND]

[Arduino Nano] ──> Laser Control
   ├─ Arduino Digital Output ──> Laser VCC (controlled by program)
   └─ GND ──> Laser GND
```

**System Architecture Diagram**: (See "Complete System Connection" and pin configuration above)

**Note**: Laser is controlled by Arduino, no GPIO or MOSFET needed on Orange Pi side

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
- Laser is now controlled by Arduino via serial commands
- Check Arduino firmware includes laser control functions
- Test laser using streaming_tracking_system.py

#### 2. Laser Always On Cannot Turn Off

**Note**: Laser is now controlled by Arduino. Use Arduino commands to control laser state.

### AI Detection Poor Performance

**Improvement suggestions**:
1. **Use mosquito-specific model** - See [docs/MOSQUITO_MODELS.md](docs/MOSQUITO_MODELS.md)
2. **Increase lighting** - Ensure sufficient ambient light (minimum 0.5 lux)
3. **Adjust AI parameters**:
   ```python
   detector = MosquitoDetector(
       model_path='models/mosquito_yolov8n.pt',  # Use specific model
       confidence_threshold=0.3,                  # Lower threshold (0.3-0.5)
       imgsz=640                                  # Balance accuracy & speed (320/416/640)
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
├── python/                           # Python AI tracking system
│   ├── config.py                     # ⭐ System configuration parameters (centralized)
│   ├── streaming_tracking_system.py  # ⭐ Complete system (AI+tracking+streaming)
│   ├── streaming_server.py           # HTTP-MJPEG streaming server module
│   ├── mosquito_tracker.py           # AI tracking main program
│   ├── mosquito_detector.py          # YOLOv8 mosquito detector
│   ├── pt2d_controller.py            # Arduino serial controller
│   ├── stereo_camera.py              # Stereo camera control
│   ├── quick_start.py                # Quick start script
│   └── test_*.py                     # Test scripts
├── models/                           # AI model directory
│   ├── mosquito.rknn                 # RKNN model (NPU acceleration)
│   ├── mosquito.onnx                 # ONNX model (CPU optimized)
│   └── mosquito.pt                   # PyTorch model
├── docs/                             # Documentation directory
│   ├── STREAMING_GUIDE.md            # Video streaming guide ⭐ New
│   ├── hardware.md                   # Hardware connection guide
│   ├── protocol.md                   # Communication protocol details
│   └── arduino_ide_guide.md          # Arduino IDE usage guide
├── platformio.ini            # PlatformIO configuration
├── .gitignore               # Git ignore file
└── README.md                # This file (Chinese version)
```

## 🛠 Development Guide

### Modify Configuration

**Python System Configuration**:

Edit [python/config.py](python/config.py) to centrally manage all Python module parameters:

- AI detection parameters (resolution, confidence threshold)
- Tracking parameters (gain, timeout)
- Hardware parameters (serial port, camera IDs)
- Control parameters (beep, laser cooldown)

**Arduino Firmware Configuration**:

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

---

## 🌐 Nginx Reverse Proxy Configuration

The system supports external access through Nginx reverse proxy for better security and flexibility.

### Why Use Nginx?

- ✅ **Unified Entry Point**: Single domain for both HTTP and RTSP streaming
- ✅ **SSL/TLS Encryption**: HTTPS secure transmission (HTTP streaming)
- ✅ **Load Balancing**: Multi-device distribution support (future expansion)
- ✅ **Access Control**: IP whitelist, basic authentication
- ✅ **Bandwidth Optimization**: Compression, caching strategies

### Architecture Diagram

```
External Network          Firewall/Router             Internal Network (Orange Pi 5)
─────────────────────────────────────────────────────────────────────────────────

https://mosquito.ma7.in ──┐
                          │
                          ├──> Nginx (443)  ──┐
                          │    - SSL Offload  │
rtsp://mosquito.ma7.in ───┤    - Reverse Proxy├──> HTTP (5000)
                          │    - Access Control│    └─> Flask Server
                          │                   │
                          └──> Nginx (1935) ─┘
                               - RTSP Proxy
                                                ──> RTSP (8554)
                                                    └─> MediaMTX
```

### Install Nginx

#### Orange Pi 5 / Ubuntu

```bash
# Install Nginx with RTMP module
sudo apt update
sudo apt install nginx libnginx-mod-rtmp

# Verify installation
nginx -v
```

#### Other Platforms

```bash
# Debian/Raspberry Pi
sudo apt install nginx nginx-full

# CentOS/RHEL
sudo yum install nginx
```

### HTTP Streaming Reverse Proxy Configuration

Create config file `/etc/nginx/sites-available/mosquito-http`:

```nginx
# HTTP-MJPEG Streaming Reverse Proxy
upstream mosquito_backend {
    server 127.0.0.1:5000;  # Flask streaming server
    keepalive 32;
}

server {
    listen 80;
    server_name mosquito.ma7.in;  # Change to your domain or IP

    # If using SSL (recommended)
    # listen 443 ssl http2;
    # ssl_certificate /etc/letsencrypt/live/mosquito.ma7.in/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/mosquito.ma7.in/privkey.pem;

    # Homepage and Web Interface
    location / {
        proxy_pass http://mosquito_backend;
        proxy_http_version 1.1;

        # WebSocket support (for future expansion)
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Standard proxy headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # MJPEG Streaming (Critical Configuration)
    location /video {
        proxy_pass http://mosquito_backend;
        proxy_http_version 1.1;

        # Disable buffering (required for real-time streaming)
        proxy_buffering off;
        proxy_cache off;
        proxy_request_buffering off;

        # Timeout settings
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;

        # Streaming headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Connection "";

        # Disable compression (already compressed JPEG)
        gzip off;
    }

    # API Endpoint (Statistics)
    location /stats {
        proxy_pass http://mosquito_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }

    # Access Control (Optional)
    # location / {
    #     auth_basic "Mosquito Tracking System";
    #     auth_basic_user_file /etc/nginx/.htpasswd;
    #     proxy_pass http://mosquito_backend;
    # }

    # IP Whitelist (Optional)
    # allow 192.168.1.0/24;  # Allow internal network
    # deny all;              # Deny others
}
```

### RTSP Streaming Reverse Proxy Configuration

Create config file `/etc/nginx/nginx.conf` (add RTMP block):

```nginx
# Add to end of nginx.conf (same level as http block)
rtmp {
    server {
        listen 1935;           # RTMP/RTSP port
        chunk_size 4096;

        application live {
            live on;
            record off;

            # Pull from MediaMTX
            pull rtsp://127.0.0.1:8554/mosquito;

            # Access Control (Optional)
            # allow publish 127.0.0.1;
            # allow play all;

            # Transcoding settings (optional, reduce latency)
            exec ffmpeg -i rtsp://127.0.0.1:8554/mosquito
                -c:v copy
                -f flv rtmp://localhost/live/mosquito;
        }
    }
}
```

**Note**: RTSP natively doesn't support HTTP/HTTPS proxy, need to use RTMP protocol or directly expose RTSP port.

### Alternative: RTSP over HTTP Tunneling

If you need HTTPS access to RTSP, use WebRTC or HTTP-FLV:

```nginx
# Use HTTP-FLV streaming (requires nginx-rtmp-module)
location /live {
    flv_live on;
    chunked_transfer_encoding on;
    add_header Access-Control-Allow-Origin *;
}
```

Client uses flv.js to play: `https://mosquito.ma7.in/live/mosquito.flv`

### Enable Configuration

```bash
# Create symbolic link
sudo ln -s /etc/nginx/sites-available/mosquito-http /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx

# Enable auto-start on boot
sudo systemctl enable nginx
```

### Firewall Settings

```bash
# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow RTSP (if external access needed)
sudo ufw allow 8554/tcp

# Allow RTMP (if using Nginx RTMP)
sudo ufw allow 1935/tcp
```

### SSL/TLS Certificate (Let's Encrypt)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Auto-configure SSL
sudo certbot --nginx -d mosquito.ma7.in

# Auto-renew certificate
sudo certbot renew --dry-run
```

### Configuration Testing

#### HTTP Streaming Test

```bash
# Internal test
curl http://localhost/

# External test
curl https://mosquito.ma7.in/stats
```

Browser access: `https://mosquito.ma7.in`

#### RTSP Streaming Test

```bash
# Test with ffplay
ffplay rtsp://mosquito.ma7.in:8554/mosquito

# Test with VLC
vlc rtsp://mosquito.ma7.in:8554/mosquito
```

### Python Configuration Update

Update [python/config.py](python/config.py):

```python
# Network configuration
DEFAULT_DEVICE_IP = "192.168.1.100"              # Internal IP
DEFAULT_EXTERNAL_URL = "https://mosquito.ma7.in"  # External access URL
DEFAULT_RTSP_URL = "rtsp://0.0.0.0:8554/mosquito" # RTSP push address
```

### Performance Optimization

```nginx
# Add to http block
http {
    # Cache settings
    proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=stream_cache:10m max_size=100m;

    # Connection optimization
    keepalive_timeout 65;
    keepalive_requests 100;

    # Compression (static resources)
    gzip on;
    gzip_types text/html text/css application/json;

    # Rate limiting (prevent abuse)
    limit_req_zone $binary_remote_addr zone=stream_limit:10m rate=10r/s;

    server {
        # Add rate limiting to location /video
        location /video {
            limit_req zone=stream_limit burst=5;
            # ... other config
        }
    }
}
```

### Monitoring and Logs

```bash
# View access logs
sudo tail -f /var/log/nginx/access.log

# View error logs
sudo tail -f /var/log/nginx/error.log

# Real-time connection statistics
sudo nginx -V 2>&1 | grep -o with-http_stub_status_module

# Add status page (nginx.conf)
location /nginx_status {
    stub_status on;
    access_log off;
    allow 127.0.0.1;
    deny all;
}
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| **502 Bad Gateway** | Check if backend service is running: `netstat -tulpn \| grep 5000` |
| **Connection Timeout** | Confirm firewall rules, proxy_read_timeout settings |
| **Streaming Lag** | Adjust proxy_buffering off, increase bandwidth |
| **SSL Certificate Error** | Update certificate: `sudo certbot renew` |
| **RTSP Connection Failed** | Check if MediaMTX is running, port is open |

### Complete Configuration Examples

Complete Nginx configuration examples are included in the documentation. For more details, refer to:

- [Nginx Official Documentation](https://nginx.org/en/docs/)
- [RTMP Module Documentation](https://github.com/arut/nginx-rtmp-module)
- [Let's Encrypt Guide](https://letsencrypt.org/getting-started/)

---

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
| [docs/STREAMING_GUIDE.md](docs/STREAMING_GUIDE.md) | ⭐ Video streaming guide (mobile viewing) |
| [docs/MOSQUITO_MODELS.md](docs/MOSQUITO_MODELS.md) | Mosquito detection model description and download |
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
| [python/config.py](python/config.py) | ⭐ Python system configuration parameters (centralized) |
| [python/streaming_tracking_system.py](python/streaming_tracking_system.py) | ⭐ Complete integrated system (recommended) |
| [python/streaming_server.py](python/streaming_server.py) | HTTP-MJPEG streaming server module |
| [python/mosquito_tracker.py](python/mosquito_tracker.py) | Main tracking system |
| [python/mosquito_detector.py](python/mosquito_detector.py) | AI detector module |
| [python/pt2d_controller.py](python/pt2d_controller.py) | Arduino controller interface |
| [python/stereo_camera.py](python/stereo_camera.py) | Dual camera module |
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
