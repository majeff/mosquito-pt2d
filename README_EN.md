## 🛠 Development Guide

### Modify Configuration

**Python System Configuration**:

Edit [python/mosquito.ini](python/mosquito.ini) to manage all Python module parameters:

- AI detection parameters (resolution, confidence threshold)
- Tracking parameters (gains, timeout)
- Hardware parameters (serial port, camera IDs)
- Control parameters (beeper, laser cooldown time)
- Illumination monitoring parameters (thresholds, check intervals)

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