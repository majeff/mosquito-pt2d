# Arduino 2D Pan-Tilt Control System + AI Mosquito Auto Tracking

![Version](https://img.shields.io/badge/version-2.5.2-blue.svg)
![AI](https://img.shields.io/badge/AI-YOLOv8-brightgreen.svg)
![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)
![Platform](https://img.shields.io/badge/platform-Arduino%20%2B%20RDK%20X5%20%2F%20Orange%20Pi%205-red.svg)
![GA Tracking](https://ga4.ma7.in/ga/github/README/README)

An Arduino-based 2D pan-tilt control system integrating dual-eye USB cameras with **AI deep learning (RDK X5 / Orange Pi 5 + YOLOv8)** technology for intelligent mosquito identification, tracking, and laser marking with live observation capabilities.

---

## 🔍 Project Version Info

| Item | Version | Notes |
|-----|------|------|
| **Overall Project Version** | **v2.5.2** | 2026-01-11 Single Dual-Eye Camera Optimization |
| Firmware Version (w/ Protocol) | v2.4.0 | Arduino firmware and UART serial communication protocol |
| Python Environment | 3.8+ | Supports YOLOv8 inference |
| AI Model | YOLOv8 | BIN (RDK X5 BPU) / RKNN (Orange Pi 5 NPU) / ONNX / PyTorch |
| License | Apache 2.0 | - |

---

## 📜 Version History

### v2.5.2 (2026-01-11) 🛠️ Single Dual-Eye Camera Optimization
- New: Single dual-eye camera support (auto-split image into left/right parts)
- New: Configuration file structure for better management
- New: Configuration sections for AI detection, tracking, hardware, temperature monitoring, and illumination monitoring
- New: Template configuration file `mosquito_sample.ini` with detailed explanations
- New: Runtime configuration file `mosquito.ini` (added to `.gitignore`)
- New: Single camera filter parameters (bounding box size filtering)
- New: Temperature monitoring parameters (pause AI recognition based on temperature)
- New: Illumination monitoring parameters (pause AI recognition based on light level)
- Optimization: Improved single dual-eye camera handling
- Optimization: Enhanced configuration management

```

```
