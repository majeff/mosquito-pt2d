# 專案規範與參考 (REFERENCE)

**此文檔集中管理所有重複的技術規範，各文件應交叉引用而非重複說明。**

---

## 🏗️ 系統架構

### 整體系統架構圖

```
┌──────────────────────────────────────────────┐
│        Orange Pi 5 主控制器 (RK3588)          │
│  ┌──────────────────────────────────────┐   │
│  │  Python AI 追蹤系統                   │   │
│  │  ✓ YOLOv8 蚊子辨識                   │   │
│  │  ✓ 雙目立體視覺 (深度估計)            │   │
│  │  ✓ PID 追蹤控制                      │   │
│  │  ✓ 即時串流系統                      │   │
│  └──────────────────────────────────────┘   │
└──┬──────────┬─────────┬──────────┬──────────┘
   │ USB      │ USB 3.0 │ USB 3.0  │ GPIO
   ▼          ▼         ▼          ▼
┌────────┐  ┌────────┐ ┌────────┐ ┌────────┐
│Arduino │  │左攝像頭│ │右攝像頭│ │繼電器  │
│Nano    │  │1920×  │ │1920×  │ │+雷射   │
│舵機控制│  │1080   │ │1080   │ │        │
└────┬───┘  └────────┘ └────────┘ └────────┘
     │ UART (115200)
     ▼
┌────────────────┐
│Pan/Tilt 舵機 ×2│
│ID=1, ID=2      │
└────────────────┘
```

---

## 💻 硬體規格

### 核心組件清單

| 組件 | 規格 | 數量 | 備註 |
|------|------|------|------|
| **開發板** | Orange Pi 5 (8GB+) / RDK X5 | 1 | AI 加速 NPU/BPU |
| **攝像頭** | 雙目 USB 1080p (3840×1080) | 2 | 基線 12cm, 60fps |
| **舵機控制板** | ZL-KPZ32 (6路舵機控制器) | 1 | 開源控制板，含 Arduino Nano、舵機驅動、雷射驅動 |
| **舵機** | SP-15D/S (15kg·cm) | 2 | Pan/Tilt 軸 |
| **主電源** | 0-24V 20A 可調開關電源 (480W) | 1 | 調至 8V 供給 ZL-KPZ32 |
| **DC-DC 降壓器** | 晒邦 LM2596S (最大 20A) | 1 | 8V → 5V USB Type-C |
| **單一電源供應全系統** | - | - | 無需多個獨立電源 |

### 攝像頭技術參數

| 參數 | 規格 | 說明 |
|------|------|------|
| 解析度 | 3840×1080 | 雙眼各 1920×1080 |
| 幀率 | 60 fps (MJPEG) | @ 3840×1080 |
| 基線距離 | 12cm (120mm) | 左右攝像頭距離 |
| 焦距 | 3.0mm | 固定焦距 |
| 視角 | 96°（對角） | 寬視角設計 |
| 最低照度 | 0.5 lux | 低光環境可用 |
| 接口 | USB 3.0 ×2 | 高速數據傳輸 |
| 有效測距 | 0.5m - 5m | 深度估計範圍 |

### 深度估計公式

```
Z = (f × B) / d

其中:
- Z = 深度 (mm)
- f = 焦距 = 3.0mm
- B = 基線 = 120mm
- d = 視差 (pixels)

轉換為公尺: Z(m) = Z(mm) / 1000
```

### 系統電源配置

**推薦方案：單一可調開關電源 + DC-DC 降壓**

```
開關電源 (0-24V 20A, 480W)
調至 8V 輸出
│
├─ 8V ────────────────────────→ ZL-KPZ32 控制板
│                               ├─ Pan 舵機
│                               ├─ Tilt 舵機
│                               ├─ 內置 Arduino Nano
│                               └─ 雷射驅動
│
└─ 8V ──────→ LM2596S DC-DC ──→ 5V USB Type-C
             降壓電源 (20A)    │
                              ├─ Orange Pi 5/RDK X5
                              ├─ 左攝像頭
                              └─ 右攝像頭

總功耗: ~35W (480W 電源足以應付)
共地: 開關電源負極 ↔ ZL-KPZ32 GND ↔ Orange Pi GND
```

**優點**:
- ✅ 單一主電源，安裝簡單
- ✅ 功率充足 (480W)
- ✅ 內置過流保護 (20A)
- ✅ 成本更低
- ✅ 無需多條電源線

**功耗分析**:

| 組件 | 電壓 | 電流 | 功率 |
|------|------|------|------|
| ZL-KPZ32 + 舵機 ×2 | 8V | 2.5A | ~20W |
| Orange Pi 5 (滿載) | 5V | 3.5A | 17.5W |
| 雙目攝像頭 | 5V | 1.0A | 5W |
| DC-DC 轉換效率損耗 (90%) | - | - | ~2.5W |
| **總計** | - | **~7A@8V** | **~35W** |

---

## 🤖 AI 模型與推理

### YOLOv8 蚊子檢測

**模型特性**:
- 架構: YOLOv8
- 訓練框架: PyTorch
- 推理支援: 多後端 (ONNX, PyTorch, RKNN, .bin)
- 默認參數:
  - 信心度閾值: 0.4
  - NMS IOU: 0.45
  - 輸入尺寸: 640×640 (imgsz)
  - 批次大小: 1

### 多平台推理引擎

| 平台 | AI 加速器 | 算力 | 推理引擎 | 模型格式 | 典型 FPS |
|------|----------|------|---------|---------|---------|
| **Orange Pi 5** | NPU (RK3588) | 6 TOPS | `rknnlite` | `.rknn` | 25-50 ⭐⭐ |
| **RDK X5** | BPU (Bayes-e) | 10 TOPS | `hobot_dnn` | `.bin` | 30-60 ⭐⭐⭐ |
| **CPU (通用)** | CPU 推理 | - | `onnxruntime`/PyTorch | `.onnx`/`.pt` | 1-5 ⚠️ |

**推薦**: 生產部署使用 **RDK X5 (10 TOPS BPU)** 或 **Orange Pi 5 (6 TOPS NPU)**

### 模型搜尋優先順序

```python
# mosquito_detector.py 自動模型搜尋邏輯
優先順序:
1. .bin (RDK X5 BPU) ← 最快
2. .rknn (Orange Pi 5 NPU) ← 次快
3. .onnx (CPU) ← 備用
4. .pt (PyTorch) ← 最慢 (訓練使用)

CPU 推理不建議在生產環境使用 (太慢)
```

---

## 🔌 硬體連接標準

### USB 連接配置

| 設備 | 連接 | 設備路徑 | 波特率 |
|------|------|---------|--------|
| **Arduino Nano** | USB 3.0 | `/dev/ttyUSB0` 或 `/dev/ttyACM0` | 115200 bps |
| **左攝像頭** | USB 3.0 | `/dev/video0` | - |
| **右攝像頭** | USB 3.0 | `/dev/video1` | - |

### 舵機總線連接 (Arduino)

```
Arduino Pin D10 (TX) ──→ 舵機 RX (黃)
Arduino Pin D11 (RX) ←── 舵機 TX (黃)
Arduino GND ↔ 舵機 GND (黑/棕)

波特率: 115200 bps
舵機 ID: Pan=1, Tilt=2
```

### 雷射控制 (可選)

```
Arduino Pin D6 ──→ 雷射頭 VCC
Arduino GND ──→ 雷射頭 GND

控制邏輯:
- digitalWrite(LASER_PIN, HIGH) → 雷射開啟
- digitalWrite(LASER_PIN, LOW) → 雷射關閉
```

---

## 📡 通訊協議

**詳見**: [protocol.md](protocol.md)

### 主要命令

| 命令 | 參數 | 說明 | 返回值 |
|------|------|------|--------|
| `GET_ANGLE` | - | 獲取舵機角度 | `[pan_angle, tilt_angle]` |
| `MOVE_TO` | `pan, tilt` | 移動至絕對位置 | `{"status": "success"}` |
| `MOVE_BY` | `pan_offset, tilt_offset` | 相對移動 | `{"status": "success"}` |
| `SET_SPEED` | `speed (1-100)` | 設定舵機速度 | `{"status": "success"}` |
| `SET_LED` | `state (0/1)` | 控制 LED | `{"status": "success"}` |
| `SET_LASER` | `state (0/1)` | 控制雷射 | `{"status": "success"}` |

**波特率**: 115200 bps
**格式**: JSON
**編碼**: UTF-8

---

## 🔍 Python 模組架構

### 核心模組

| 模組 | 功能 | 主要類 |
|------|------|--------|
| **stereo_camera.py** | 雙目攝像頭擷取 | `StereoCamera` |
| **depth_estimator.py** | 雙目深度估計 | `DepthEstimator` |
| **mosquito_detector.py** | AI 蚊子檢測 | `MosquitoDetector` |
| **mosquito_tracker.py** | 目標追蹤 | `MosquitoTracker` |
| **pt2d_controller.py** | Arduino 雲台控制 | `PT2DController` |
| **streaming_tracking_system.py** | 一體化系統 | `StreamingTrackingSystem` |
| **streaming_server.py** | 網頁串流伺服器 | `StreamingServer` |

**詳見**: [docs/python_README.md](docs/python_README.md)

---

## 📚 文檔導航

| 文檔 | 內容 | 適用對象 |
|------|------|---------|
| **README.md** | 總體說明、版本歷史、功能特點 | 所有用戶 |
| **hardware.md** | 硬體規格、接線步驟、故障排除 | 硬體工程師 |
| **protocol.md** | UART 通訊協議、命令格式 | 固件/驅動開發 |
| **python_README.md** | Python 系統架構、模組說明、API | Python 開發者 |
| **MOSQUITO_MODELS.md** | AI 模型訓練、部署、改進流程 | ML 工程師 |
| **STREAMING_GUIDE.md** | 即時串流配置、Web 介面使用 | 最終用戶 |
| **REFERENCE.md** | 規範集中管理、參數標準化 | 所有開發者 ⬅️ **本文** |

---

## ✅ 標準參數

### 系統配置參數

```python
# 所有模組應使用統一參數

# 攝像頭
CAMERA_WIDTH = 1920
CAMERA_HEIGHT = 1080
CAMERA_FPS = 60

# AI 檢測
AI_CONFIDENCE_THRESHOLD = 0.4
AI_IMGSZ = 640
AI_CONF_RANGE_LOW = 0.35
AI_CONF_RANGE_HIGH = 0.65

# 深度估計
FOCAL_LENGTH_MM = 3.0
BASELINE_MM = 120.0
STEREO_IMAGE_WIDTH = 1920

# Arduino 通訊
ARDUINO_BAUDRATE = 115200
ARDUINO_TIMEOUT_MS = 1000
DEFAULT_ARDUINO_PORT = '/dev/ttyUSB0'  # Linux
# DEFAULT_ARDUINO_PORT = 'COM3'         # Windows

# 舵機配置
SERVO_ID_PAN = 1
SERVO_ID_TILT = 2
SERVO_MIN_ANGLE = 0
SERVO_MAX_ANGLE = 180
SERVO_CENTER = 90
```

---

## 🔗 交叉引用最佳實踐

在各文檔中遇到重複內容時，應使用以下格式進行交叉引用：

### 格式 1: 簡短參考
```markdown
攝像頭規格: 詳見 [REFERENCE.md - 攝像頭技術參數](#攝像頭技術參數)
```

### 格式 2: 詳細說明 + 參考
```markdown
### AI 推理

本系統使用 YOLOv8 進行蚊子檢測。

**核心參數** (統一規範見 [REFERENCE.md](REFERENCE.md#-ai-模型與推理)):
- 信心度閾值: 0.4
- 輸入尺寸: 640×640
```

### 格式 3: 指向明確文檔章節
```markdown
詳見 [硬體連接標準](#硬體連接標準) 或閱讀完整 [hardware.md](docs/hardware.md)
```

---

**最後更新**: 2025年12月28日
**版本**: v1.0.0
**維護者**: Mosquito PT2D 專案團隊
