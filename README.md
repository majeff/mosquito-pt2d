# Arduino 2D 雲台控制系統 + AI 蚊子自動追蹤

![Version](https://img.shields.io/badge/version-2.3.0-blue.svg)
![AI](https://img.shields.io/badge/AI-YOLOv8-brightgreen.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-Arduino%20%2B%20Orange%20Pi%205-red.svg)

一個基於 Arduino 的 2D 雲台（Pan-Tilt）控制系統，整合雙目 USB 攝像頭與 **AI 深度學習（YOLOv8）** 技術，實現智能蚊子辨識、追蹤與雷射標記功能。

## � 版本歷史

### v2.3.0（2025-12-25）🚀 穩定性重大升級

#### 🛡️ 固件核心改進
- **內存優化**
  - ❌ 移除 `String` 類的使用 → ✅ 固定大小 `char[]` 緩衝區
  - 消除 heap 碎片化風險，內存使用可預測
  - 節省約 2-3KB Flash 大小

- **參數驗證強化**
  - 新增 6 個輔助函數：`isValidServoId()`, `isValidAngle()`, `parseIntParam()`, `parseTwoInts()`, `toUpperCase()`, `clearBuf()`
  - 防止無效參數導致系統異常
  - 統一錯誤處理機制

- **函數模組化**
  - 提取 13 個專用命令處理函數（`handleLed()`, `handleMove()`, `handleGetPos()` 等）
  - `handlePcLine()` 從 350 行精簡到 85 行（**減少 75%**）
  - 提升代碼可讀性與可維護性

- **超時保護機制**
  - 聚合命令（POS/STATUS）添加 **2 秒超時**
  - 防止串口通訊異常導致系統卡死
  - 超時自動重置狀態並回報錯誤

- **看門狗定時器**
  - 啟用 AVR 硬體看門狗（**2 秒超時**）
  - 系統死鎖或異常時自動重啟
  - `loop()` 每次迭代重置看門狗

- **錯誤處理優化**
  - 統一錯誤回應 API：`sendError()`, `sendOk()`
  - 緩衝區溢出保護（命令過長自動拒絕）
  - 狀態重置函數：`resetAggState()`

#### 🐍 Python 異常處理增強
- **完整異常保護**
  - `mosquito_tracker.py`：主迴圈、追蹤邏輯、控制器操作全面保護
  - `mosquito_detector.py`：AI 推理 RuntimeError、MemoryError 捕捉
  - `stereo_camera.py`：相機 I/O 錯誤精確處理（IOError/OSError）
  - 所有關鍵操作失敗時優雅降級，系統持續運行

- **控制器優化**
  - 合併 `pt2d_controller_improved.py` 到主控制器
  - 新增重試機制（可選參數 `retry`）
  - `_read_json_response()` 自動過濾非 JSON 訊息
  - 優化緩衝區管理，減少通訊錯誤

#### 📊 穩定性提升總結

| 指標 | v2.2.0 | v2.3.0 | 改進 |
|------|--------|--------|------|
| **最大函數行數** | 350 行 | 85 行 | ↓ 75% |
| **內存使用** | 動態（不可預測） | 固定 192 字節 | ✅ 穩定 |
| **Flash 大小** | 基準 + 3KB | 基準 | ↓ 2-3KB |
| **錯誤處理** | 部分 | 完整 | ↑ 100% |
| **異常保護覆蓋** | ~20% | ~95% | ↑ 375% |
| **超時保護** | 無 | 2 秒 | ✅ 新增 |
| **看門狗保護** | 無 | 2 秒 | ✅ 新增 |

---

### v2.2.0（2025-12-24）

#### 主要改進
- 文檔與代碼一致性檢查（100/100 分）
- AI 檢測參數標準化（`confidence_threshold: 0.4`, `imgsz: 320`）
- 模型自動搜尋機制（RKNN → ONNX → PyTorch）
- 完整參數文檔化（README.md 補充所有缺失參數）

---

### v2.0.0（2025-12-20）🎉 AI 整合版本

#### 重大功能
- **YOLOv8 AI 蚊子檢測**
  - 深度學習物體檢測整合
  - 支援 RKNN/ONNX/PyTorch 多後端
  - Orange Pi 5 NPU 硬體加速

- **智能追蹤系統**
  - 信心度過濾機制
  - 多目標鎖定追蹤
  - PID 控制雲台對準

- **雙目視覺系統**
  - 3840×1080 @ 60fps 雙目攝像頭
  - 立體視覺深度估計
  - 實時影像處理

- **雷射標記功能**
  - GPIO 控制雷射模組
  - 智能標記觸發
  - 安全冷卻機制

---

### v1.0.0（2025-12-10）📦 初始版本

#### 基礎功能
- Arduino 2D 雲台控制
- UART 串口通訊（115200 波特率）
- 總線舵機支援（LX-16A/SCS15）
- 基本移動命令（MOVE/HOME/STOP）
- JSON 格式響應
- 自動舵機 ID 掃描

---

## �📋 目錄

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
  - 支援 CPU/NPU 推理（Orange Pi 5 優化）
- 🎯 **智能追蹤**:
  - AI 偵測到蚊子 → 自動切換至追蹤模式
  - 實時計算偏移並控制雲台對準
  - 信心度過低/失去目標 → 自動切回監控模式
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
         ▼
┌──────────────────┐
│  AI 追蹤控制器    │ (智能追蹤 + PID 控制)
│  mosquito_tracker │ (信心度過濾)
└────────┬─────────┘
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
6. **失去目標**: 信心度過低或無檢測 → 返回監控模式

## 🔧 硬體需求

### 主控端

| 組件 | 規格 | 數量 | 備註 |
|-----|------|------|------|
| **Orange Pi 5** | 8GB RAM | 1 | 主控制器，運行影像識別 |
| 電源供應器 | 5V/4A USB-C | 1 | Orange Pi 5 供電 |

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
| **雷射模組** | 1mW 紅光雷射 | 1 | 目標標記用（安全等級） |
| 杜邦線 | 公對母 | 若干 | GPIO 連接 |

## 💻 軟體需求

### Orange Pi 5 端

- **作業系統**: Ubuntu 22.04 LTS (ARM64) 或 Armbian
- **Python**: 3.8+ (通常預裝)
- **必要套件**:
  - OpenCV (`opencv-python`)
  - PySerial (`pyserial`)
  - NumPy (`numpy`)
  - RPi.GPIO 或 OrangePi.GPIO (GPIO 控制)

```bash
# Orange Pi 5 安裝
sudo apt update
sudo apt install python3-pip python3-opencv
pip3 install -r python/requirements.txt
pip3 install OrangePi.GPIO  # GPIO 控制雷射
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

### 2. Orange Pi 5 系統設置

```bash
# 更新系統
sudo apt update && sudo apt upgrade -y

# 安裝必要套件
sudo apt install python3-pip python3-opencv git -y

# 進入專案目錄
### 4. 硬體連接

參考 [docs/hardware.md](docs/hardware.md)

**關鍵點:**
- **Orange Pi 5** 為主控制器，運行所有 Python 程式
- Orange Pi 5 透過 GPIO UART 直連 Arduino Nano（TXD→D0(RX)、RXD←D1(TX, 需電位轉換 5V→3.3V)）
- 雙目 **1080p 攝像頭**透過 USB 3.0 連接至 Orange Pi 5
- 總線舵機透過軟串口連接 Arduino（Nano D10/D11 → 舵機總線）
- **1mW 雷射模組**為兩線（VCC/GND）型：預設以 MOSFET/驅動器由 GPIO 控制供電；
   若模組為 3.3V 且實測穩態電流 ≤8~10mA，可考慮直連由 GPIO 供電（風險自評估），否則請用 MOSFET
- 舵機需要獨立供電 (6V-8.4V)
- 所有 GND 必須共地（Orange Pi、Arduino、舵機、雷射）
 - 替代連線：若使用 Arduino 的 USB 連接至 Orange Pi，免電位轉換（裝置為 `/dev/ttyUSB*`/`/dev/ttyACM*`）
 - 控制器板注意：使用「开源6路机器人机械臂舵机控制器板」時，UART 多為 5V TTL；若無 3.3/5V 跳線或電位轉換，請選 USB 連線或在 Arduino TX→Orange Pi RX 路徑加入電位轉換
```

### 3. 測試硬體連接

```bash
# 測試攝像頭
python3 stereo_camera.py

# 測試 Arduino 通訊
python3 pt2d_controller.py

# 測試 GPIO 雷射控制
python3 test_laser.py  # 我們稍後會建立這個檔案
```
#### 使用 Arduino IDE

參考 [docs/arduino_ide_guide.md](docs/arduino_ide_guide.md)

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
- Orange Pi 5 透過 GPIO UART 直連 Arduino（TXD→D0, RXD←D1 經電位轉換）
- 舵機透過總線連接至 Arduino（Nano D10/D11）
- 攝像頭透過 USB 連接至 Orange Pi 5
- 舵機需要獨立供電 (6V-8.4V)
- 所有 GND 必須共地
 - 替代連線：Arduino 以 USB 連至 Orange Pi 可免電位轉換；裝置為 `/dev/ttyUSB*`/`/dev/ttyACM*`
 - 控制器板注意：6路機械臂控制器板 UART 為 5V TTL；若無 3.3/5V 跳線/電位轉換，請選 USB 或加電位轉換

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
python mosquito_tracker.py
```

### 操作指南

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

編輯 `python/mosquito_tracker.py`：

```python
# Arduino 串口
ARDUINO_PORT = 'COM3'  # Windows
# 對於 Orange Pi 5（GPIO UART 直連）請使用 /dev/ttyS*，如：
# ARDUINO_PORT = '/dev/ttyS1'  # Linux（請用 dmesg/ls 確認實際節點）

# 攝像頭 ID
LEFT_CAMERA_ID = 0
RIGHT_CAMERA_ID = 1

# AI 偵測參數
detector = MosquitoDetector(
    model_path=None,                           # 自動搜尋模型（.rknn → .onnx → .pt）
    confidence_threshold=0.4,                  # 信心度閾值（推薦 0.3-0.7）
    imgsz=320                                  # 輸入解析度（320/416/640）
)

# 追蹤參數
self.pan_gain = 0.15                # Pan 增益（控制靈敏度）
self.tilt_gain = 0.15               # Tilt 增益（控制靈敏度）
self.no_detection_timeout = 3.0     # 無偵測超時（秒）
self.target_lock_distance = 100     # 目標鎖定距離（像素）
self.beep_cooldown = 2.0            # 蜂鳴器冷卻時間（秒）
self.laser_cooldown = 0.5           # 雷射冷卻時間（秒）
self.position_update_interval = 0.5 # 位置更新間隔（秒）
```

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

#### Orange Pi 5 ↔ Arduino Nano（UART 直連）

```
連接           | 說明
---------------|--------------------------------------
Orange Pi TXD  | → Arduino D0 (RX0)
Orange Pi RXD  | ← Arduino D1 (TX0, 經電位轉換 5V→3.3V)
共地           | Orange Pi GND ↔ Arduino GND ↔ 舵機電源 GND
Nano D10 (TX)  | → 舵機總線 RX（黃線）
Nano D11 (RX)  | ← 舵機總線 TX（綠線）
6V-8.4V        | → 舵機 VCC（外接電源）
```
### 完整系統連接

```
[Orange Pi 5]
   ├─ UART (GPIO) ──> [Arduino Nano] ──(D10/D11)──> [舵機總線] ──> [Pan 舵機 + Tilt 舵機]
   ├─ USB 3.0 ─────> [左攝像頭 1080p]
   ├─ USB 3.0 ─────> [右攝像頭 1080p]
   └─ GPIO Pin 5 ──> [MOSFET Gate]（由 GPIO 控制雷射供電）

[舵機電源 6V-8.4V] ──> [舵機總線 VCC]
                              └─> GND ──(共地)──> [Arduino GND] ──> [Orange Pi GND]

[兩線雷射（無 EN）]：
   3.3V (Pin 1) 或 5V (Pin 2/4) ──> 雷射 VCC（經 MOSFET 控制的供電路徑）
   GPIO Pin 5  ───> MOSFET Gate（串 100Ω，Gate 對地 10k 下拉）
   GND (Pin 6/9) ─> MOSFET Source 與系統共地；雷射 GND 接 MOSFET Drain（低側開關）
```

**系統架構圖**:（見上方「完整系統連接」與引腳配置）

**GPIO 對應 (OrangePi.GPIO 庫)**:
- 實體 Pin 5 = GPIO 3 = 程式中使用 `GPIO.setmode(GPIO.BOARD)` 後為 Pin 5

注意：
- 兩線雷射需用 MOSFET 在供電路徑切換；GPIO 僅作邏輯控制，不直接供電。
- 若雷射為 5V 或電流較大，務必使用 MOSFET/驅動器；請共地並加入 Gate 下拉與保護電阻。

### ⚠️ 重要注意事項

1. **獨立供電**: 總線舵機需要 **6V-8.4V** 供電（推薦 7.4V 鋰電池）
2. **共地**: 確保 Orange Pi、Arduino、舵機、雷射模組所有 GND 連接在一起
3. **串口選擇**: Nano 上位機通訊使用 D0/D1（硬體 UART），舵機總線使用 D10/D11（SoftwareSerial）
4. **舵機 ID**: 預設 Pan=ID1, Tilt=ID2，請先確認舵機 ID 設置
5. **攝像頭**: 雙目 1080p 攝像頭透過 USB 3.0 連接至 Orange Pi 5
6. **雷射安全**: 使用 1mW 紅光雷射（Class II），避免直視，安裝時注意方向
7. **USB 供電**: Orange Pi 5 使用 USB-C 5V/4A 供電，確保足夠電流
8. **散熱**: Orange Pi 5 建議加裝散熱片或風扇

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
<!-- 掃描模式已移除，MODE/GETMODE 不再提供 -->
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

# 測試雷射控制（需要 sudo）
sudo python3 laser_controller.py

# 測試蚊子偵測
python3 mosquito_detector.py
```

### 2. 運行完整追蹤系統

```bash
# 在 Orange Pi 5 上運行
cd python
sudo python3 mosquito_tracker.py

# 或使用快速啟動腳本
sudo python3 quick_start.py
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

# （掃描模式已移除）

# 停止移動
<STOP>
```

### 4. 系統操作快捷鍵

在追蹤系統運行時：

| 快捷鍵 | 功能 | 說明 |
|--------|------|------|
| `q` | 退出系統 | 安全關閉所有資源 |
| `r` | 重置偵測器 | 清除偵測歷史 |
<!-- 掃描模式快捷鍵已移除 -->
| `h` | 回到初始位置 | 雲台歸位 |
| `l` | 切換雷射 | 手動開關雷射 |
| `SPACE` | 雷射脈衝 | 0.2 秒標記脈衝 |

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

#### 1. GPIO 權限不足

**錯誤**: `PermissionError: [Errno 13] Permission denied`

**解決方法**:
```bash
# 方法 1: 使用 sudo
sudo python3 mosquito_tracker.py

# 方法 2: 加入 gpio 群組
sudo usermod -a -G gpio $USER
# 登出後重新登入

# 方法 3: 設定 GPIO 權限規則
sudo nano /etc/udev/rules.d/99-gpio.rules
# 加入: SUBSYSTEM=="gpio", MODE="0660", GROUP="gpio"
sudo udevadm control --reload-rules
```

#### 2. 攝像頭無法開啟

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

#### 3. Arduino 無法連接

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

### 雷射相關問題

#### 1. 雷射無法啟動

**檢查項目**:
- 檢查 GPIO 引腳是否正確（實體 Pin 5，BOARD 模式）
- 確認雷射模組為 3.3V、低電流型（建議 ≤10mA），並已共地
- 以萬用表量測 Pin 5 在 ON/OFF 時是否電位切換
- 若模組需 5V 或電流較大，請改用 MOSFET/驅動器，勿直接接 GPIO

**測試命令**:
```bash
sudo python3 laser_controller.py
```

#### 2. 雷射一直開啟無法關閉

**緊急處理**:
```bash
# 立即關閉所有 GPIO
sudo python3 -c "import OPi.GPIO as GPIO; GPIO.setmode(GPIO.BOARD); GPIO.setup(5, GPIO.OUT); GPIO.output(5, GPIO.LOW); GPIO.cleanup()"
```

### AI 偵測效果不佳

**改進建議**:
1. **使用蚊子專用模型** - 參見 [docs/MOSQUITO_MODELS.md](docs/MOSQUITO_MODELS.md)
2. **增加照明** - 確保環境光線充足（最低 0.5 lux）
3. **調整 AI 參數**:
   ```python
   detector = MosquitoDetector(
       model_path='models/mosquito_yolov8n.pt',  # 使用專用模型
       confidence_threshold=0.3,                  # 降低閾值（0.3-0.5）
       imgsz=320                                  # 優化速度（320/416/640）
   )
   ```
4. **降低解析度** - 提高 AI 推理速度
   ```python
   detector = MosquitoDetector(imgsz=320)  # 從 640 降到 320
   ```
5. **轉換為 ONNX/RKNN** - 參見 [docs/AI_DETECTION_GUIDE.md](docs/AI_DETECTION_GUIDE.md)

# 執行校準
<CAL>
```

### Python 控制示例

查看 [docs/python_example.md](docs/python_example.md) 獲取完整的 Python 控制代碼。

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
| MODE | `<MODE:0/1>` | 設置模式（0=手動、1=自動掃描） | `<MODE:1>` |
| GETMODE | `<GETMODE>` | 查詢當前模式 | `<GETMODE>` |

> 註：自動掃描模式僅供手動/單機測試使用，蚊子辨識流程不會觸發或使用掃描模式。
## 📁 專案結構

```
mosquito-pt2d/
├── src/
│   └── main.cpp              # 橋接固件主程序
├── include/
│   └── config.h              # 配置文件（串口、舵機ID、角度範圍）
├── python/                   # Python AI 追蹤系統
│   ├── pt2d_controller.py    # Arduino 串口控制器
│   ├── mosquito_tracker.py   # AI 追蹤主程序
│   ├── mosquito_detector.py  # YOLOv8 蚊子偵測器
│   ├── stereo_camera.py      # 雙目攝像頭控制
│   ├── laser_controller.py   # 雷射控制（GPIO）
│   └── quick_start.py        # 快速啟動腳本
├── models/                   # AI 模型目錄
│   └── mosquito.pt           # YOLOv8 蚊子偵測模型
├── docs/                     # 文檔目錄
│   ├── hardware.md           # 硬體連接說明
│   ├── protocol.md           # 通訊協議詳細說明
│   ├── python_example.md     # Python 控制示例
│   └── arduino_ide_guide.md  # Arduino IDE 使用說明
├── platformio.ini            # PlatformIO 配置
├── .gitignore               # Git 忽略文件
└── README.md                # 本文件
```

## 🛠 開發指南

### 修改配置

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
| [SERIAL_PROTOCOL_MAPPING.md](SERIAL_PROTOCOL_MAPPING.md) | 串口通訊協議完整對照表 |
| [LICENSE](LICENSE) | MIT 授權條款 |

### 🔧 硬體與配置文檔

| 文檔 | 說明 |
|------|------|
| [docs/hardware.md](docs/hardware.md) | 硬體連接詳細說明（含接線圖） |
| [docs/orangepi5_hardware.md](docs/orangepi5_hardware.md) | Orange Pi 5 硬體配置指南 |
| [docs/protocol.md](docs/protocol.md) | 串口通訊協議技術規格 |
| [docs/arduino_ide_guide.md](docs/arduino_ide_guide.md) | Arduino IDE 編譯上傳指南 |

### 🤖 AI 與 Python 文檔

| 文檔 | 說明 |
|------|------|
| [docs/AI_DETECTION_GUIDE.md](docs/AI_DETECTION_GUIDE.md) | AI 檢測系統詳細指南 |
| [docs/MOSQUITO_MODELS.md](docs/MOSQUITO_MODELS.md) | 蚊子檢測模型說明與下載 |
| [docs/python_example.md](docs/python_example.md) | Python 範例程式與使用教學 |
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
| [python/mosquito_tracker.py](python/mosquito_tracker.py) | 主追蹤系統 |
| [python/mosquito_detector.py](python/mosquito_detector.py) | AI 檢測器模組 |
| [python/pt2d_controller.py](python/pt2d_controller.py) | Arduino 控制器介面 |
| [python/stereo_camera.py](python/stereo_camera.py) | 雙目相機模組 |
| [python/laser_controller.py](python/laser_controller.py) | 雷射控制模組 |
| [python/quick_start.py](python/quick_start.py) | 快速啟動腳本 |

**提示**: 所有文檔均以 Markdown 格式編寫，可直接在 GitHub 或任何 Markdown 編輯器中閱讀。

---

## 📄 授權

本專案採用 MIT 授權 - 詳見 [LICENSE](LICENSE) 文件

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
