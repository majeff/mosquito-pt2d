# Arduino 2D 雲台控制系統 + AI 蚊子自動追蹤

![Version](https://img.shields.io/badge/version-2.4.0-blue.svg)
![AI](https://img.shields.io/badge/AI-YOLOv8-brightgreen.svg)
![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)
![Platform](https://img.shields.io/badge/platform-Arduino%20%2B%20Orange%20Pi%205-red.svg)

一個基於 Arduino 的 2D 雲台（Pan-Tilt）控制系統，整合雙目 USB 攝像頭與 **AI 深度學習（OrangePi5+YOLOv8）** 技術，實現智能蚊子辨識、追蹤與雷射標記功能並提供即時觀測。

---

## 🔍 專案版本信息

| 項目 | 版本 | 備註 |
|-----|------|------|
| **整體專案版本** | **v2.4.0** | 2025-12-27 |
| 固件版本 | v2.3.0 | Arduino、Orange Pi 5 |
| Python 環境 | 3.8+ | 支持 YOLOv8 推理 |
| AI 模型 | YOLOv8 | RKNN/ONNX/PyTorch 多後端 |
| 協議版本 | v2.3.0 | UART 串口通訊協議 |
| 開源協議 | Apache 2.0 | - |

---

## 📜 版本歷史

### v2.4.0（2025-12-27）📱 即時觀測升級
- 新增：影像串流系統（HTTP-MJPEG），手機即時觀看
- 新增：整合程式 `streaming_tracking_system.py`（AI+追蹤+串流一體）
- 新增：雙目攝像頭三種串流模式（並排/單一/獨立）
- 新增：Web 介面顯示即時統計資訊
- 文檔：完整串流指南 [docs/STREAMING_GUIDE.md](docs/STREAMING_GUIDE.md)
- 功能：所有 AI 標註（檢測框、信心度）包含在串流中

---

### v2.3.0（2025-12-25）🚀 穩定性升級
- 固件：內存優化（固定緩衝區）、函數模組化（↓75% 代碼量）、看門狗定時器（2秒）、超時保護
- Python：完整異常處理、控制器重試機制、優雅錯誤降級
- 成果：異常保護 ~20% → ~95%，Flash 減少 2-3KB

---

### v2.2.0（2025-12-24）📚 文檔完善
- 文檔與代碼一致性檢查（100/100 分）
- AI 參數標準化（`confidence: 0.4`, `imgsz: 640`）
- 模型自動搜尋機制（RKNN → ONNX → PyTorch）

---

### v2.0.0（2025-12-20）🤖 AI 整合
- YOLOv8 蚊子檢測（RKNN/ONNX/PyTorch 多後端，Orange Pi 5 NPU 加速）
- 智能追蹤系統（信心度過濾、多目標鎖定、PID 控制）
- 雙目視覺（3840×1080 @ 60fps）+ 雷射標記

---

### v1.0.0（2025-12-10）🏗️ 初始版本
- Arduino 2D 雲台控制、UART 通訊（115200）
- 總線舵機支援（LX-16A/SCS15）
- JSON 格式響應、自動 ID 掃描

---

## 📋 目錄

- [版本歷史](#版本歷史)
- [功能特點](#功能特點)
- [系統架構](#系統架構)
- [硬體需求](#硬體需求)
- [軟體需求](#軟體需求)
- [安裝說明](#安裝說明)
- [硬體連接](#硬體連接)
- [使用說明](#使用說明)
- [通訊協議](#通訊協議)
- [專案結構](#專案結構)
- [開發指南](#開發指南)
- [Nginx 反向代理配置](#nginx-反向代理配置)
- [常見問題](#常見問題)
- [完整文檔索引](#-完整文檔索引)

## ✨ 功能特點

### Arduino 雲台控制

- ✅ 雙軸伺服馬達控制（Pan 水平 & Tilt 垂直）
- ✅ UART 串口通訊（115200 波特率）
- ✅ **固件穩定性增強** (v2.3.0):
   - ✅ 內存優化：使用固定緩衝區，無 heap 碎片化
   - ✅ 參數驗證：完整的輸入檢查與錯誤處理
   - ✅ 模組化架構：13 個專用命令處理函數
   - ✅ 超時保護：聚合命令 2 秒超時機制
   - ✅ 看門狗：2 秒自動重啟保護
- ✅ **工作模式**：
   - ✅ **初始靜止**: 垂直固定 90°，水平置中，等待偵測
   - 🎮 **手動追蹤**: 由上位機控制，用於精確追蹤
- ✅ 支援絕對位置和相對位置移動
- ✅ 可調速度控制（1-100）
- ✅ 自動回歸初始位置
- ✅ 校準功能
- ✅ 總線舵機反饋：位置讀取、溫度監控、電壓檢測
- ✅ JSON 格式響應

### Python AI 影像追蹤系統

- 🎥 **雙目 USB 攝像頭支援**: 左右攝像頭同步擷取（3840×1080 @ 60fps）
- 🤖 **AI 蚊子智能辨識** (YOLOv8):
  - 深度學習物體檢測
  - 高準確度蚊子辨識
  - 信心度評分與過濾
  - 支援 CPU/NPU 推理（RKNN NPU 加速優化）
  - 多種模型格式：RKNN（NPU）、ONNX（CPU）、PyTorch
  - **中等信心度樣本自動儲存** (v2.3.1 新增):
    - 自動收集信心度中等（0.35-0.65）的檢測樣本
    - 供後續人工檢驗與模型再訓練使用
    - 磁碟使用率監控（超過 20% 自動暫停）
    - 智能檔名包含時間戳與信心度資訊
- 🎯 **智能追蹤**:
  - AI 偵測到蚊子 → 自動切換至追蹤模式
  - 實時計算偏移並控制雲台對準
  - 信心度過低/失去目標 → 自動切回監控模式
- 📺 **即時影像串流** (v2.4.0 新增):
  - HTTP-MJPEG 串流伺服器，手機瀏覽器即時觀看
  - 完整 AI 標註包含在串流中（檢測框、信心度、追蹤狀態）
  - 支援雙目攝像頭（並排顯示/單一視角/獨立串流）
  - Web 介面顯示即時統計（FPS、檢測數、連線數）
  - 多客戶端同時觀看支援
- 📊 **視覺化顯示**: 實時顯示 AI 偵測結果、邊界框、信心度
- 🔧 **參數可調**: AI 模型路徑、信心度閾值、輸入解析度、追蹤增益

## 🏗️ 系統架構

```
┌──────────────────┐
│  雙目 USB 攝像頭  │ (3840×1080 @ 60fps)
└────────┬─────────┘
         │ 影像擷取
         ▼
┌──────────────────┐
│  AI 蚊子偵測器    │ (YOLOv8 深度學習)
│  mosquito_detector│ (信心度 + 邊界框)
└────────┬─────────┘
         │ 目標座標 + 信心度
         ├─────────────────────┐
         │                     │ AI 標註影像
         ▼                     ▼
┌──────────────────┐  ┌──────────────────┐
│  AI 追蹤控制器    │  │  串流伺服器       │ 📱
│  mosquito_tracker │  │ StreamingServer  │ → 手機/瀏覽器
│ (信心度過濾)      │  │ (HTTP-MJPEG)     │    即時觀看
└────────┬─────────┘  └──────────────────┘
         │ 串口命令 (TX/RX)
         ▼
┌──────────────────┐
│  Arduino 雲台     │ (初始靜止 / AI 追蹤)
│  PT2D Controller  │
└──────────────────┘
```

### AI 工作流程

1. **監控階段**: 雲台保持中央（Pan=中心, Tilt=90°），AI 持續分析影像
2. **AI 辨識階段**: YOLOv8 模型偵測到蚊子，輸出邊界框與信心度
3. **信心度過濾**: 僅追蹤信心度 > 閾值（如 0.4）的高可信度目標
4. **追蹤階段**: 計算偏移量並控制雲台對準，持續追蹤
5. **雷射標記**: 目標接近中心 + 高信心度 → 啟動雷射標記
6. **影像串流**: 標註後的影像即時推送至串流伺服器，手機可觀看
7. **失去目標**: 信心度過低或無檢測 → 返回監控模式

## 🔧 硬體需求

### 主控端

| 組件 | 規格 | 數量 | 備註 |
|-----|------|------|------|
| **ARM 開發板** | 8GB RAM + NPU | 1 | 主控制器，運行 AI 影像識別<br>**推薦選項**：<br>• Orange Pi 5 (RK3588, 6 TOPS NPU)<br>• 地瓜派 RDK X5 (更便宜)<br>• Radxa ROCK 5B<br>**必須支援 RKNN NPU 加速** |
| 電源供應器 | 5V/3-4A USB-C | 1 | 開發板供電（依型號調整） |

### 視覺系統

| 組件 | 規格 | 數量 | 備註 |
|-----|------|------|------|
| **雙目攝像頭** | 1080p USB | 2 | 左右攝像頭，視野偵測 |

### 雲台控制系統

| 組件 | 規格 | 數量 | 備註 |
|-----|------|------|------|
| Arduino 開發板 | Nano | 1 |  |
| **2D 雲台支架** | 金屬或塑膠 | 1 | 含舵機安裝位，承載攝像頭 |
| **總線舵機** | LX-16A/SCS15/HTS | 2 | Pan & Tilt 軸，串口舵機 |
| 舵機電源 | **6V-8.4V / 2A** | 1 | 推薦 7.4V 鋰電池 |

### 雷射標記系統

| 組件 | 規格 | 數量 | 備註 |
|-----|------|------|------|
| **雷射模組** | 1mW 紅光雷射 | 1 | 目標標記用（安全等級）<br>由 Arduino 控制 |

## 💻 軟體需求

### ARM 開發板端

- **作業系統**: Ubuntu 22.04 LTS (ARM64) 或 Armbian
- **Python**: 3.8+ (通常預裝)
- **NPU 支援**: RKNN Toolkit Lite 2.x（用於 NPU 加速）
- **必要套件**:
  - OpenCV (`opencv-python`)
  - PySerial (`pyserial`)
  - NumPy (`numpy`)
  - RKNN Toolkit Lite（NPU 推理）

```bash
# ARM 開發板安裝
sudo apt update
sudo apt install python3-pip python3-opencv
pip3 install -r python/requirements.txt

# 安裝 RKNN Toolkit Lite（依開發板提供的版本）
# Orange Pi 5: 參考官方文檔
# 地瓜派 RDK X5: 參考官方 SDK
```

### Arduino 端

- [PlatformIO IDE](https://platformio.org/) 或 [Arduino IDE](https://www.arduino.cc/en/software)
- USB 驅動程式（CH340/CP2102 等）

### 開發端（可選）

- 用於開發與測試，可使用 Windows/Linux PC
- Python 3.8+
- 相同的 Python 套件

## 📦 安裝說明

### 1. Arduino 韌體上傳

#### 使用 PlatformIO（推薦）

### 2. ARM 開發板系統設置

```bash
# 更新系統
sudo apt update && sudo apt upgrade -y

# 安裝必要套件
sudo apt install python3-pip python3-opencv git -y

# 進入專案目錄
### 4. 硬體連接

參考 [docs/hardware.md](docs/hardware.md)

**關鍵點:**
- **ARM 開發板**（Orange Pi 5 / 地瓜派 RDK X5 等）為主控制器，運行所有 Python 程式
- Arduino Nano 透過 USB 連接至開發板（裝置為 `/dev/ttyUSB*` 或 `/dev/ttyACM*`）
- 雙目 **1080p 攝像頭**透過 USB 3.0 連接至開發板
- 總線舵機透過軟串口連接 Arduino（Nano D10/D11 → 舵機總線）
- **1mW 雷射模組**由 Arduino 控制（透過串口指令）
- 舍機需要獨立供電 (6V-8.4V)
- 所有 GND 必須共地（開發板、Arduino、舍機）
```

### 3. 測試硬體連接

```bash
# 測試攝像頭
python3 stereo_camera.py

# 測試 Arduino 通訊
python3 pt2d_controller.py
```
#### 使用 Arduino IDE

參考 [include/config.h](include/config.h) 與 [docs/protocol.md](docs/protocol.md)

### 2. Python 環境設置

```bash
# 進入 Python 目錄
cd python

# 安裝依賴
pip install -r requirements.txt
```

### 3. 硬體連接

參考 [docs/hardware.md](docs/hardware.md)

**關鍵點:**
- Arduino Nano 透過 USB 連接至 Orange Pi 5（裝置為 `/dev/ttyUSB*` 或 `/dev/ttyACM*`）
- 舵機透過總線連接至 Arduino（Nano D10/D11）
- 攝像頭透過 USB 連接至 Orange Pi 5
- 舵機需要獨立供電 (6V-8.4V)
- 所有 GND 必須共地

---

## 🚀 使用說明

### 快速啟動

1. **上傳 Arduino 韌體**（參考上方安裝說明）

2. **測試各模組**：

```bash
# 測試攝像頭
cd python
python stereo_camera.py

# 測試蚊子偵測
python mosquito_detector.py

# 測試 Arduino 通訊
python pt2d_controller.py
```

3. **運行追蹤系統**：

```bash
# 方案 A: 完整系統（AI + 追蹤 + 串流）⭐ 推薦
python streaming_tracking_system.py
# 手機瀏覽器開啟: http://[Orange_Pi_IP]:5000

# 方案 B: 基本追蹤系統（無串流）
python mosquito_tracker.py
```

### 操作指南

#### 方案 A: 完整系統（streaming_tracking_system.py）⭐ 推薦

```bash
python streaming_tracking_system.py
```

**快捷鍵:**
- `q`: 退出系統
- `t`: 切換追蹤模式
- `s`: 儲存截圖
- `h`: 雲台歸位

**手機觀看:**
1. 確保手機與開發板在同一網路
2. 瀏覽器開啟: `http://[開發板IP]:5000`
3. 即可看到即時 AI 標註影像

**Web 介面顯示:**
- 即時影像（包含 AI 檢測框、信心度）
- FPS、檢測數、追蹤狀態
- 連線客戶端數量

---

#### 方案 B: 基本追蹤系統（mosquito_tracker.py）

運行 `mosquito_tracker.py` 後：

**快捷鍵:**
- `q`: 退出系統
- `r`: 重置偵測器
- `h`: 回到初始位置

**視窗說明:**
- **Mosquito Tracker**: 主視窗，顯示偵測與追蹤結果
- **Detection Mask**: 偵測遮罩視窗，用於調試

**狀態指示:**
- **TRACKING** (紅色): 追蹤模式

### 配置參數

系統參數統一在 [python/config.py](python/config.py) 中管理，方便集中修改：

```python
# ============================================
# AI 檢測參數
# ============================================
DEFAULT_IMGSZ = 640                      # 輸入解析度（320/416/640，預設 640）
DEFAULT_CONFIDENCE_THRESHOLD = 0.4       # 信心度閾值（0.3-0.7）
DEFAULT_IOU_THRESHOLD = 0.45             # IoU 閾值

# ============================================
# 追蹤參數
# ============================================
DEFAULT_PAN_GAIN = 0.15                  # Pan 增益（控制靈敏度）
DEFAULT_TILT_GAIN = 0.15                 # Tilt 增益（控制靈敏度）
DEFAULT_NO_DETECTION_TIMEOUT = 3.0       # 無偵測超時（秒）
DEFAULT_TARGET_LOCK_DISTANCE = 100       # 目標鎖定距離（像素）

# ============================================
# 硬體參數
# ============================================
DEFAULT_ARDUINO_PORT = '/dev/ttyUSB0'    # Linux/Orange Pi
# DEFAULT_ARDUINO_PORT = 'COM3'          # Windows
DEFAULT_LEFT_CAMERA_ID = 0
DEFAULT_RIGHT_CAMERA_ID = 1

# ============================================
# 控制參數
# ============================================
DEFAULT_BEEP_COOLDOWN = 2.0              # 蜂鳴器冷卻時間（秒）
DEFAULT_LASER_COOLDOWN = 0.5             # 雷射冷卻時間（秒）
```

**修改方式**：編輯 `python/config.py` 即可統一調整所有模組的參數。

**常用調整**：
- **提升速度**：將 `DEFAULT_IMGSZ` 改為 `320`（犧牲精度）
- **提升精度**：將 `DEFAULT_IMGSZ` 改為 `800` 或 `1280`（降低速度）
- **調整追蹤靈敏度**：修改 `DEFAULT_PAN_GAIN` 和 `DEFAULT_TILT_GAIN`

---

## ⚙️ 配置舵機

### 1. 確認舵機 ID

使用廠商提供的調試軟件或代碼確認舵機 ID：
- Pan 軸舵機：ID = 1
- Tilt 軸舵機：ID = 2

### 2. 修改 config.h

```cpp
// 串口配置
#define SERIAL_BAUDRATE     115200    // 上位機串口波特率
#define SERVO_BAUDRATE      115200    // 舵機總線波特率（LX-16A: 115200, SCS: 9600/1000000）

// 舵機 ID（系統會自動掃描，也可手動指定）
#define DEFAULT_PAN_SERVO_ID    1     // Pan 軸舵機 ID（預設值）
#define DEFAULT_TILT_SERVO_ID   2     // Tilt 軸舵機 ID（預設值）
#define AUTO_DETECT_SERVO_ID    true  // 啟動時自動掃描舵機 ID

// 舵機角度範圍
#define PAN_MAX_ANGLE       270       // Pan 水平最大角度
#define TILT_MAX_ANGLE      180       // Tilt 垂直最大角度
#define PAN_INIT_ANGLE      135       // Pan 初始角度（水平中心）
#define TILT_INIT_ANGLE     90        // Tilt 初始角度（垂直中心）

// 運動參數
#define DEFAULT_SPEED       50        // 預設移動速度（1-100）
#define MIN_SPEED           1         // 最小速度
#define MAX_SPEED           100       // 最大速度

// 自動掃描配置
#define SERVO_DETECT_TIMEOUT    500   // 舵機掃描超時（毫秒）
#define SERVO_DETECT_INTERVAL   100   // 舵機掃描間隔（毫秒）
```

---

## 🔌 硬體連接

詳細連接圖請參考 [docs/hardware.md](docs/hardware.md)

### 引腳配置

#### ARM 開發板 ↔ Arduino Nano（USB 連接）

```
連接           | 說明
---------------|--------------------------------------
USB            | 開發板 USB ↔ Arduino Nano USB (CH340/ATmega328P)
共地           | 透過 USB 已共地，另需與舵機電源 GND 共地
Nano D10 (TX)  | → 舵機總線 RX（黃線）
Nano D11 (RX)  | ← 舵機總線 TX（綠線）
6V-8.4V        | → 舵機 VCC（外接電源）
```
### 完整系統連接

```
[ARM 開發板] (Orange Pi 5 / 地瓜派 RDK X5 等)
   ├─ USB ─────────> [Arduino Nano] ──(D10/D11)──> [舵機總線] ──> [Pan 舵機 + Tilt 舵機]
   ├─ USB 3.0 ─────> [左攝像頭 1080p]
   └─ USB 3.0 ─────> [右攝像頭 1080p]

[舵機電源 6V-8.4V] ──> [舵機總線 VCC]
                              └─> GND ──(共地)──> [Arduino GND] ──> [開發板 GND]

[Arduino Nano] ──> 雷射控制
   ├─ Arduino 數位輸出 ──> 雷射 VCC (經程式控制)
   └─ GND ──> 雷射 GND
```

**系統架構圖**:（見上方「完整系統連接」與引腳配置）

### ⚠️ 重要注意事項

1. **獨立供電**: 總線舵機需要 **6V-8.4V** 供電（推薦 7.4V 鋰電池）
2. **共地**: 確保 Orange Pi、Arduino、舵機所有 GND 連接在一起
3. **串口連接**: Arduino Nano 透過 **USB** 連接開發板（內部使用 D0/D1 硬體 UART），舵機總線使用 D10/D11（SoftwareSerial）
4. **舵機 ID**: 預設 Pan=ID1, Tilt=ID2，請先確認舵機 ID 設置
5. **攝像頭**: 雙目 1080p 攝像頭透過 USB 3.0 連接至開發板
6. **雷射安全**: 使用 1mW 紅光雷射（Class II），避免直視，安裝時注意方向
7. **USB 供電**: 開發板使用 USB-C 5V/3-4A 供電（依型號調整），確保足夠電流
8. **散熱**: 開發板建議加裝散熱片或風扇
9. **NPU 支援**: 確保開發板支援 RKNN 格式模型（.rknn 文件）以使用 NPU 加速

---

## 📖 通訊協議

### Arduino 命令格式

命令格式: `<CMD:param1,param2,...>\n`

| 命令 | 參數 | 說明 | 範例 |
|------|------|------|------|
| `MOVE` | pan, tilt | 移動到絕對位置 | `<MOVE:135,90>` |
| `MOVER` | delta_pan, delta_tilt | 相對移動 | `<MOVER:20,-10>` |
| `POS` | - | 獲取當前位置 | `<POS>` |
| `SPEED` | value | 設置速度 (1-100) | `<SPEED:80>` |
| `HOME` | - | 回到初始位置 | `<HOME>` |
| `STOP` | - | 停止移動 | `<STOP>` |
| `CAL` | - | 執行校準 | `<CAL>` |

### 響應格式

JSON 格式: `{"key":"value"}\n`

```json
// 成功響應
{"status":"ok","message":"OK"}

// 位置響應
{"pan":135,"tilt":90}

// 模式響應
{"mode":1}

// 錯誤響應
{"status":"error","message":"Unknown command"}
```

### Python API

詳見 [docs/python_README.md](docs/python_README.md)

---

## 📖 基本操作示例

### 1. Orange Pi 5 系統測試

```bash
# 測試攝像頭
cd python
python3 stereo_camera.py

# 測試 Arduino 通訊
python3 pt2d_controller.py
# 測試蚊子偵測
python3 mosquito_detector.py
```

### 2. 運行完整追蹤系統

```bash
# 在 Orange Pi 5 上運行
cd python
sudo python3 streaming_tracking_system.py  # 一體化（AI+追蹤+串流）
# 或僅啟動追蹤（無串流）
sudo python3 mosquito_tracker.py
```

### 3. Arduino 串口測試

透過串口監視器測試 Arduino（波特率 115200）:

```bash
# 移動到絕對位置 (Pan=135°, Tilt=90°)
<MOVE:135,90>

# 相對移動 (Pan+20°, Tilt-10°)
<MOVER:20,-10>

# 獲取當前位置
<POS>

# 設置移動速度為 80
<SPEED:80>

# 回到初始位置
<HOME>

# 停止移動
<STOP>
```

### 4. 系統操作快捷鍵

在追蹤系統運行時：

| 快捷鍵 | 功能 | 說明 |
|--------|------|------|
| `q` | 退出系統 | 安全關閉所有資源 |
| `r` | 重置偵測器 | 清除偵測歷史 |
| `h` | 回到初始位置 | 雲台歸位 |

---

## 🎯 系統工作流程

### 完整 AI 追蹤循環

```
1. [監控階段]
   └─> 雲台保持中央（Pan 中心 / Tilt 90°）
   └─> YOLOv8 AI 持續分析影像

2. [AI 辨識階段]
   └─> YOLOv8 檢測到蚊子（深度學習）
   └─> 輸出邊界框與信心度評分

3. [信心度過濾]
   └─> 檢查信心度 > 閾值（如 0.4）
   └─> 過濾低可信度誤檢

4. [追蹤階段] ⭐ 持續追蹤
   └─> 計算目標偏移量
   └─> PID 控制雲台對準目標
   └─> 持續 AI 追蹤，實時更新目標位置
   └─> **多目標處理**：鎖定單一目標持續追蹤
      ├─ 畫面中有多個蚊子時，選擇信心度最高的目標
      ├─ 鎖定目標後，保持追蹤該目標（不會跳到其他蚊子）
      ├─ 使用位置追蹤（100px 範圍內）確保追蹤同一隻
      └─ 只有失去當前目標後，才會選擇新目標
   └─> 即使暫時失去目標，維持追蹤狀態 3 秒
   └─> 目標重新出現時立即恢復追蹤

5. [標記階段]
   └─> 目標進入中心區域 (±30px) + 高信心度
   └─> 啟動雷射標記
   └─> 綠色圓圈標示中心區域

6. [失去目標] ⚠️ 超時機制
   └─> 連續 3 秒無檢測（防止誤判）
   └─> 關閉雷射
   └─> 返回監控模式（回到中央位置）
```

---

## 🛠️ 故障排除

### Orange Pi 5 相關問題

#### 1. 攝像頭無法開啟

**檢查方法**:
```bash
# 列出設備
ls -l /dev/video*

# 測試攝像頭
v4l2-ctl --list-devices

# 檢查權限
sudo chmod 666 /dev/video0
sudo chmod 666 /dev/video1
```

#### 2. Arduino 無法連接

**檢查方法**:
```bash
# 列出串口設備
ls -l /dev/ttyUSB* /dev/ttyACM*

# 檢查連接
dmesg | grep tty

# 設定權限
sudo chmod 666 /dev/ttyS1   # 依你的實際裝置節點調整
sudo usermod -a -G dialout $USER
```

### AI 偵測效果不佳

**改進建議**:
1. **針對信心度不佳圖片進行再訓練** - 參見 [docs/MOSQUITO_MODELS.md](docs/MOSQUITO_MODELS.md)
2. **增加照明** - 確保環境光線充足（最低 0.5 lux）
3. **調整 AI 參數**:
   ```python
   detector = MosquitoDetector(
    model_path='models/mosquito_yolov8.pt',   # 使用專用模型
       confidence_threshold=0.3,                  # 降低閾值（0.3-0.5）
       imgsz=640                                  # 平衡精度與速度（320/416/640）
   )
   ```
4. **降低解析度** - 提高 AI 推理速度（犧牲精度）
   ```python
   detector = MosquitoDetector(imgsz=320)  # 從預設 640 降到 320 以提升速度
   ```
5. **部署與導出**
     - 推薦使用單一 Python 腳本完成部署與導出：

         ```sh
         python python/deploy_model.py --imgsz 320
         # 預設同時導出 RKNN；Linux 部署機會自動偵測目標。可覆寫：
         python python/deploy_model.py --imgsz 320 --rknn-target rk3588
         ```

                 選項：`--imgsz <int>`（預設取自 config.DEFAULT_IMGSZ）、`--skip-onnx`（略過 ONNX）、`--skip-rknn`（略過 RKNN）、`--export-rknn`（強制 RKNN）、`--rknn-target <str>`（Linux 自動偵測，否則預設 rk3588）、`--rknn-no-quant`、`--onnx-opset <int>`、`--onnx-dynamic`、`--onnx-half`
         - RKNN 量化：
             - 預設自動：導出 RKNN 時，會從已標註樣本自動生成 `dataset.txt`
             - 自訂覆寫：`--rknn-quant-dataset <txt>`（覆寫自動清單；每行為影像路徑）

# 執行校準
<CAL>
```

### Python 控制示例

```python
import serial
import time

# 打開串口
ser = serial.Serial('COM3', 115200, timeout=1)
time.sleep(2)

# 移動到指定位置
ser.write(b'<MOVE:90,45>\n')
response = ser.readline().decode()
print(response)  # {"status":"ok","message":"OK"}

ser.close()
```

## 📡 通訊協議

詳細協議說明請參考 [docs/protocol.md](docs/protocol.md)

### 命令格式

```
<COMMAND:param1,param2,...>\n
```

### 響應格式

```json
{"status":"ok","message":"OK"}
{"status":"error","message":"Unknown command"}
{"pan":90,"tilt":45}
```

### 支援的命令

| 命令 | 格式 | 說明 | 示例 |
|-----|------|------|------|
| MOVE | `<MOVE:pan,tilt>` | 移動到絕對位置 | `<MOVE:90,45>` |
| MOVER | `<MOVER:pan,tilt>` | 相對移動 | `<MOVER:10,-5>` |
| POS | `<POS>` | 獲取當前位置 | `<POS>` |
| SPEED | `<SPEED:value>` | 設置速度 (1-100) | `<SPEED:50>` |
| HOME | `<HOME>` | 回到初始位置 | `<HOME>` |
| STOP | `<STOP>` | 停止移動 | `<STOP>` |
| CAL | `<CAL>` | 執行校準 | `<CAL>` |

## 📁 專案結構

```
mosquito-pt2d/
├── src/
│   └── main.cpp                      # 橋接固件主程序
├── include/
│   └── config.h                      # 配置文件（串口、舵機ID、角度範圍）
├── python/                           # Python AI 追蹤系統
│   ├── config.py                     # ⭐ 系統配置參數（統一管理）
│   ├── streaming_tracking_system.py  # ⭐ 完整系統（AI+追蹤+串流）
│   ├── streaming_server.py           # HTTP-MJPEG 串流伺服器模組
│   ├── mosquito_tracker.py           # AI 追蹤主程序
│   ├── mosquito_detector.py          # YOLOv8 蚊子偵測器
│   ├── pt2d_controller.py            # Arduino 串口控制器
│   ├── stereo_camera.py              # 雙目攝像頭控制
│   └── test_*.py                     # 測試腳本（取代 quick_start）
├── models/                           # AI 模型目錄
│   ├── mosquito_yolov8.rknn          # RKNN 模型（NPU 加速）
│   ├── mosquito_yolov8.onnx          # ONNX 模型（CPU 優化）
│   └── mosquito_yolov8.pt            # PyTorch 模型
├── docs/                             # 文檔目錄
│   ├── STREAMING_GUIDE.md            # 影像串流指南
│   ├── hardware.md                   # 硬體連接說明
│   ├── protocol.md                   # 通訊協議詳細說明
│   └── protocol.md                   # 通訊協議詳細說明
├── platformio.ini                    # PlatformIO 配置
├── .gitignore                        # Git 忽略文件
└── README.md                         # 本文件
```

## 🛠 開發指南

### 修改配置

**Python 系統配置**：

編輯 [python/config.py](python/config.py) 統一管理所有 Python 模組參數：

- AI 檢測參數（解析度、信心度閾值）
- 追蹤參數（增益、超時時間）
- 硬體參數（串口、攝像頭 ID）
- 控制參數（蜂鳴器、雷射冷卻時間）

**Arduino 固件配置**：

編輯 [include/config.h](include/config.h) 文件來修改：

- 引腳定義
- 角度範圍
- 移動速度
- 串口波特率
- 調試選項

### 添加新功能

**固件端（Arduino）**：
1. 在 `src/main.cpp` 的 `handlePcLine()` 函數中添加新命令解析
2. 實現命令邏輯並發送相應的總線指令
3. 更新 `docs/protocol.md` 協議文檔

**Python 端**：
1. 在 `python/pt2d_controller.py` 中添加對應的便利方法
2. 更新 `mosquito_tracker.py` 以使用新功能
3. 更新文檔

### 調試技巧

```cpp
// 在 config.h 中啟用調試模式
#define DEBUG_MODE true

// 使用調試宏
DEBUG_PRINTLN("Current position: ");
DEBUG_PRINT(panAngle);
```

---

## 🌐 Nginx 反向代理配置

系統支援透過 Nginx 反向代理實現外部訪問，提供更好的安全性和靈活性。

### 為什麼使用 Nginx？

- ✅ **統一入口**：單一域名同時處理 HTTP 和 RTSP 串流
- ✅ **SSL/TLS 加密**：HTTPS 安全傳輸（HTTP 串流）
- ✅ **負載均衡**：支援多設備分流（未來擴展）
- ✅ **存取控制**：IP 白名單、基本認證
- ✅ **頻寬優化**：壓縮、緩存策略

### 架構圖

```
外部網路                 防火牆/路由器               內網（Orange Pi 5）
─────────────────────────────────────────────────────────────────────

https://mosquito.ma7.in ──┐
                          │
                          ├──> Nginx (443)  ──┐
                          │    - SSL 卸載     │
rtsp://mosquito.ma7.in ───┤    - 反向代理     ├──> HTTP (5000)
                          │    - 存取控制     │    └─> Flask Server
                          │                   │
                          └──> Nginx (1935) ─┘
                               - RTSP 代理
                                                ──> RTSP (8554)
                                                    └─> MediaMTX
```

### 安裝 Nginx

#### Orange Pi 5 / Ubuntu

```bash
# 安裝 Nginx 及 RTMP 模組
sudo apt update
sudo apt install nginx libnginx-mod-rtmp

# 驗證安裝
nginx -v
```

#### 其他平台

```bash
# Debian/Raspberry Pi
sudo apt install nginx nginx-full

# CentOS/RHEL
sudo yum install nginx
```

### HTTP 串流反向代理配置

創建配置檔 `/etc/nginx/sites-available/mosquito-http`：

```nginx
# HTTP-MJPEG 串流反向代理
upstream mosquito_backend {
    server 127.0.0.1:5000;  # Flask 串流伺服器
    keepalive 32;
}

server {
    listen 80;
    server_name mosquito.ma7.in;  # 修改為你的域名或 IP

    # 如果使用 SSL（推薦）
    # listen 443 ssl http2;
    # ssl_certificate /etc/letsencrypt/live/mosquito.ma7.in/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/mosquito.ma7.in/privkey.pem;

    # 首頁與 Web 介面
    location / {
        proxy_pass http://mosquito_backend;
        proxy_http_version 1.1;

        # WebSocket 支援（未來擴展用）
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # 標準代理頭
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # MJPEG 串流（關鍵配置）
    location /video {
        proxy_pass http://mosquito_backend;
        proxy_http_version 1.1;

        # 禁用緩衝（即時串流必需）
        proxy_buffering off;
        proxy_cache off;
        proxy_request_buffering off;

        # 超時設定
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;

        # 串流頭設定
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Connection "";

        # 關閉壓縮（已壓縮的 JPEG）
        gzip off;
    }

    # API 端點（統計資訊）
    location /stats {
        proxy_pass http://mosquito_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }

    # 存取控制（可選）
    # location / {
    #     auth_basic "Mosquito Tracking System";
    #     auth_basic_user_file /etc/nginx/.htpasswd;
    #     proxy_pass http://mosquito_backend;
    # }

    # IP 白名單（可選）
    # allow 192.168.1.0/24;  # 允許內網
    # deny all;              # 拒絕其他
}
```

### RTSP 串流反向代理配置

創建配置檔 `/etc/nginx/nginx.conf`（添加 RTMP 區塊）：

```nginx
# 在 nginx.conf 最後添加（與 http 區塊同級）
rtmp {
    server {
        listen 1935;           # RTMP/RTSP 端口
        chunk_size 4096;

        application live {
            live on;
            record off;

            # 從 MediaMTX 拉流
            pull rtsp://127.0.0.1:8554/mosquito;

            # 存取控制（可選）
            # allow publish 127.0.0.1;
            # allow play all;

            # 轉碼設定（可選，降低延遲）
            exec ffmpeg -i rtsp://127.0.0.1:8554/mosquito
                -c:v copy
                -f flv rtmp://localhost/live/mosquito;
        }
    }
}
```

**注意**：RTSP 原生不支援 HTTP/HTTPS 代理，需使用 RTMP 協議或直接暴露 RTSP 端口。

### 替代方案：RTSP over HTTP Tunneling

如果需要透過 HTTPS 訪問 RTSP，可使用 WebRTC 或 HTTP-FLV：

```nginx
# 使用 HTTP-FLV 串流（需安裝 nginx-rtmp-module）
location /live {
    flv_live on;
    chunked_transfer_encoding on;
    add_header Access-Control-Allow-Origin *;
}
```

客戶端使用 flv.js 播放：`https://mosquito.ma7.in/live/mosquito.flv`

### 啟用配置

```bash
# 創建符號連結
sudo ln -s /etc/nginx/sites-available/mosquito-http /etc/nginx/sites-enabled/

# 測試配置
sudo nginx -t

# 重新載入 Nginx
sudo systemctl reload nginx

# 設定開機自啟
sudo systemctl enable nginx
```

### 防火牆設定

```bash
# 允許 HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 允許 RTSP（如需外部訪問）
sudo ufw allow 8554/tcp

# 允許 RTMP（如使用 Nginx RTMP）
sudo ufw allow 1935/tcp
```

### SSL/TLS 證書（Let's Encrypt）

```bash
# 安裝 Certbot
sudo apt install certbot python3-certbot-nginx

# 自動配置 SSL
sudo certbot --nginx -d mosquito.ma7.in

# 自動更新證書
sudo certbot renew --dry-run
```

### 配置測試

#### HTTP 串流測試

```bash
# 內部測試
curl http://localhost/

# 外部測試
curl https://mosquito.ma7.in/stats
```

瀏覽器訪問：`https://mosquito.ma7.in`

#### RTSP 串流測試

```bash
# 使用 ffplay 測試
ffplay rtsp://mosquito.ma7.in:8554/mosquito

# 使用 VLC
vlc rtsp://mosquito.ma7.in:8554/mosquito
```

### Python 配置更新

更新 [python/config.py](python/config.py)：

```python
# 網路配置
DEFAULT_DEVICE_IP = "192.168.1.100"              # 內網 IP
DEFAULT_EXTERNAL_URL = "https://mosquito.ma7.in"  # 外部訪問 URL
DEFAULT_RTSP_URL = "rtsp://0.0.0.0:8554/mosquito" # RTSP 推流地址
```

### 效能優化建議

```nginx
# 添加到 http 區塊
http {
    # 緩存設定
    proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=stream_cache:10m max_size=100m;

    # 連接優化
    keepalive_timeout 65;
    keepalive_requests 100;

    # 壓縮（靜態資源）
    gzip on;
    gzip_types text/html text/css application/json;

    # 限流（防止濫用）
    limit_req_zone $binary_remote_addr zone=stream_limit:10m rate=10r/s;

    server {
        # 在 location /video 添加限流
        location /video {
            limit_req zone=stream_limit burst=5;
            # ... 其他配置
        }
    }
}
```

### 監控與日誌

```bash
# 查看訪問日誌
sudo tail -f /var/log/nginx/access.log

# 查看錯誤日誌
sudo tail -f /var/log/nginx/error.log

# 即時連線統計
sudo nginx -V 2>&1 | grep -o with-http_stub_status_module

# 添加狀態頁面（nginx.conf）
location /nginx_status {
    stub_status on;
    access_log off;
    allow 127.0.0.1;
    deny all;
}
```

### 故障排除

| 問題 | 解決方案 |
|------|---------|
| **502 Bad Gateway** | 檢查後端服務是否運行：`netstat -tulpn \| grep 5000` |
| **連線超時** | 確認防火牆規則、proxy_read_timeout 設定 |
| **串流卡頓** | 調整 proxy_buffering off、增加頻寬 |
| **SSL 證書錯誤** | 更新證書：`sudo certbot renew` |
| **RTSP 無法連接** | 檢查 MediaMTX 是否運行、端口是否開放 |

### 完整配置範例

完整的 Nginx 配置範例已包含在文檔中。如需更多細節，請參考：

- [Nginx 官方文檔](https://nginx.org/en/docs/)
- [RTMP 模組文檔](https://github.com/arut/nginx-rtmp-module)
- [Let's Encrypt 指南](https://letsencrypt.org/getting-started/)

---

## 🐛 常見問題

### Q1: 伺服馬達抖動或不穩定

**A**: 檢查電源是否充足，建議使用外接電源並添加濾波電容。

### Q2: 串口無法通訊

**A**: 確認波特率設置為 115200，檢查 TX/RX 連接是否正確。

### Q3: 上傳程序失敗

**A**: 斷開 TX/RX 連接後再上傳，上傳完成後重新連接。

### Q4: 角度範圍不正確

**A**: 執行校準命令 `<CAL>`，或在 `config.h` 中調整角度範圍。

---

## 📚 完整文檔索引

### 📖 核心文檔

| 文檔 | 說明 |
|------|------|
| [README.md](README.md) | 專案主文檔（本文件） |
| [CONSISTENCY_CHECK.md](CONSISTENCY_CHECK.md) | 文件與程式一致性檢查報告 |
| [docs/SERIAL_CHECK_SUMMARY.md](docs/SERIAL_CHECK_SUMMARY.md) | 串口通訊格式檢查與對照摘要 |
| [LICENSE](LICENSE) | Apache 2.0 授權條款 |
| [NOTICE](NOTICE) | 版權與第三方相依標註 |

### 🔧 硬體與配置文檔

| 文檔 | 說明 |
|------|------|
| [docs/hardware.md](docs/hardware.md) | 硬體連接詳細說明（含接線圖） |
| [docs/orangepi5_hardware.md](docs/orangepi5_hardware.md) | Orange Pi 5 硬體配置指南 |
| [docs/protocol.md](docs/protocol.md) | 串口通訊協議技術規格 |
| [include/config.h](include/config.h) | 固件參數與引腳設定 |

### 🤖 AI 與 Python 文檔

| 文檔 | 說明 |
|------|------|
| [python/README.md](python/README.md) | AI 檢測與追蹤整合指南 |
| [docs/STREAMING_GUIDE.md](docs/STREAMING_GUIDE.md) | ⭐ 影像串流指南（手機觀看） |
| [docs/MOSQUITO_MODELS.md](docs/MOSQUITO_MODELS.md) | ⭐ 蚊子檢測模型持續改進指南（樣本收集→訓練） |
| [docs/python_README.md](docs/python_README.md) | Python 模塊導航文檔 |
| [python/README.md](python/README.md) | Python 程式目錄說明 |

### 🧪 測試與驗證文檔

| 文檔 | 說明 |
|------|------|
| [docs/SERIAL_CHECK_SUMMARY.md](docs/SERIAL_CHECK_SUMMARY.md) | 串口通訊格式檢查總結 |
| [python/test_serial_protocol.py](python/test_serial_protocol.py) | 串口協議測試腳本 |
| [python/test_tracking_logic.py](python/test_tracking_logic.py) | 追蹤邏輯驗證腳本 |
| [python/test_multi_target_tracking.py](python/test_multi_target_tracking.py) | 多目標追蹤測試腳本 |

### 📁 代碼文件

| 檔案 | 說明 |
|------|------|
| [include/config.h](include/config.h) | Arduino 固件配置參數 |
| [src/main.cpp](src/main.cpp) | Arduino 橋接固件主程式 |
| [python/config.py](python/config.py) | ⭐ Python 系統配置參數（統一管理） |
| [python/streaming_tracking_system.py](python/streaming_tracking_system.py) | ⭐ 完整整合系統（推薦使用） |
| [python/streaming_server.py](python/streaming_server.py) | HTTP-MJPEG 串流伺服器模組 |
| [python/mosquito_tracker.py](python/mosquito_tracker.py) | 主追蹤系統 |
| [python/mosquito_detector.py](python/mosquito_detector.py) | AI 檢測器模組 |
| [python/pt2d_controller.py](python/pt2d_controller.py) | Arduino 控制器介面 |
| [python/stereo_camera.py](python/stereo_camera.py) | 雙目相機模組 |

**提示**: 所有文檔均以 Markdown 格式編寫，可直接在 GitHub 或任何 Markdown 編輯器中閱讀。

---

## 📄 授權

本專案採用 Apache 2.0 授權 - 詳見 [LICENSE](LICENSE) 與 [NOTICE](NOTICE) 文件

## 👥 貢獻

歡迎提交 Issue 和 Pull Request！

## 📧 聯繫方式

如有問題或建議，請通過以下方式聯繫：

- Email: jeff@ma7.in
- GitHub Issues: [提交問題](https://github.com/majeff/mosquito-pt2d/issues)

## 🙏 致謝

感謝所有為本專案做出貢獻的開發者！

---

**Built with ❤️ for Arduino Community**
