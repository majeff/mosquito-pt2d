# 蚊子自動追蹤系統 - Python 端說明

## 📋 概述

本專案整合雙目 USB 攝像頭（3840×1080 @ 60fps）、AI 深度學習識別、Arduino 雲台控制與雷射標記系統，實現自動蚊子偵測、追蹤與標記功能。

**硬體平台**: Orange Pi 5 (RK3588, 6 TOPS NPU)
**AI 模型**: YOLOv8 蚊子檢測模型
**檢測方式**: 深度學習物體識別

### 系統架構

```
┌──────────────────────────────────────────┐
│        Orange Pi 5 主控制器               │
│  ┌──────────────────────────────────┐   │
│  │  Python AI 追蹤系統               │   │
│  │  - AI 蚊子辨識 (YOLOv8)           │   │
│  │  - 雙目立體視覺 (深度估計)         │   │
│  │  - 追蹤控制邏輯                   │   │
│  │  - 雷射標記控制                   │   │
│  └──────────────────────────────────┘   │
└──┬────────┬─────────┬────────┬──────────┘
   │ USB    │ USB 3.0 │ USB 3.0│ GPIO
   ▼        ▼         ▼        ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌─────────┐
│Arduino │ │左攝像頭│ │右攝像頭│ │繼電器   │
│雲台控制│ │1920×  │ │1920×  │ │+雷射    │
│        │ │1080   │ │1080   │ │         │
└────────┘ └────────┘ └────────┘ └─────────┘
   │
   ▼ 總線 UART
┌─────────────┐
│Pan/Tilt 舵機│
│(ID=1, ID=2) │
└─────────────┘
```

---

## 🚀 快速開始

### 1. Orange Pi 5 系統準備

```bash
# 更新系統
sudo apt update && sudo apt upgrade -y

# 安裝必要套件
sudo apt install python3-pip python3-opencv git -y
```

### 2. 安裝依賴

```bash
cd python
pip3 install -r requirements.txt

# Orange Pi 5 NPU 支援（可選，用於加速）
# RKNN Toolkit 2 需從官方下載
wget https://github.com/rockchip-linux/rknn-toolkit2/releases/download/v1.5.0/rknn_toolkit2-1.5.0-cp38-cp38-linux_aarch64.whl
pip3 install rknn_toolkit2-1.5.0-cp38-cp38-linux_aarch64.whl
```

**重要套件:**
- `ultralytics`: YOLOv8 AI 模型框架
- `onnxruntime`: ONNX 模型推理引擎（CPU 優化）
- `opencv-python`: 影像處理

### 3. 下載 AI 模型

```bash
# 建立模型目錄
mkdir -p models

# 蚊子檢測模型改進與訓練
# 參見 MOSQUITO_MODELS.md 獲取模型改進指南
# 預設模型已包含在 models/ 目錄中

# 將自訓練的新模型放置到 models/ 目錄
# models/mosquito_yolov8.pt
```

**模型資源:**
- 參見 [MOSQUITO_MODELS.md](MOSQUITO_MODELS.md) - 詳細的模型持續改進與訓練指南
- 參見 [../python/README.md](../python/README.md) - AI 檢測與追蹤整合指南

### 3. 硬體連接

- **Arduino**: 透過 USB 連接至 Orange Pi 5
    - Arduino Nano USB ↔ Orange Pi 5 USB 埠
    - 裝置節點通常為：`/dev/ttyUSB0` 或 `/dev/ttyACM0`
    - 共地：透過 USB 已共地，另需與舵機電源 GND 共地
    - 用 `dmesg | grep tty` 或 `ls /dev/ttyUSB*` 確認裝置節點
- **左/右攝像頭**: USB 3.0 連接（UVC 相容）
- **雷射模組**: 由 Arduino 控制，無需額外 MOSFET

### 3. 運行追蹤系統

```bash
# 方法 1: 直接運行（需 GPIO 權限）
python3 mosquito_tracker.py

# 方法 2: 使用 sudo（如果 GPIO 權限不足）
sudo python3 mosquito_tracker.py

# 方法 3: 停用雷射功能運行（測試用）
# 編輯 mosquito_tracker.py，設置 enable_laser=False
```

---

## 📦 模組說明

### 0. `config_loader.py` - 系統配置載入器

負責載入和管理所有系統參數配置。

**主要功能:**
- 集中管理系統所有配置參數
- 提供預設值和類型檢查
- 支援配置覆寫和環境變數

### 1. `stereo_camera.py` - 雙目攝像頭模組

負責雙 1080p USB 攝像頭的影像擷取。

**主要功能:**
- 開啟與設定雙攝像頭
- 同步讀取左右影像
- 支援單獨讀取與拼接顯示

**使用範例:**

```python
from stereo_camera import StereoCamera

with StereoCamera(left_id=0, right_id=1) as camera:
    ret, left_frame, right_frame = camera.read()
    if ret:
        # 處理影像...
        pass
```

**測試:**

```bash
python stereo_camera.py
```

---

### 2. `depth_estimator.py` - 雙目深度估計模組

基於立體視覺原理計算目標的深度（距離）。

**主要功能:**
- 計算視差圖（Stereo SGBM）
- 估計目標深度/距離
- 支援檢測框深度估計
- 深度視覺化彩色圖

**技術參數:**
- 焦距：3.0mm
- 雙目基線：120mm（12cm）
- 有效測距範圍：0.5m - 5m
- 深度公式：`Z = (f × B) / d`

**使用範例:**

```python
from depth_estimator import DepthEstimator
from stereo_camera import StereoCamera

# 初始化深度估計器
estimator = DepthEstimator(
    focal_length=3.0,
    baseline=120.0,
    image_width=1920
)

# 讀取雙目影像
camera = StereoCamera(left_id=0, right_id=1)
ret, left, right = camera.read()

# 估計特定點的深度
point = (960, 540)  # 影像中心
depth = estimator.estimate_depth_at_point(left, right, point)
print(f"距離: {depth:.2f}m ({depth*100:.1f}cm)")

# 估計檢測框的深度
bbox = (100, 100, 200, 200)  # (x1, y1, x2, y2)
depth_info = estimator.estimate_depth_for_detection(left, right, bbox)
if depth_info:
    print(f"目標距離: {depth_info['distance_cm']:.1f}cm")
```

**測試:**

```bash
python depth_estimator.py
# 左鍵點擊測量深度，'d' 切換深度圖，'q' 退出
```

---

### 3. `mosquito_detector.py` - AI 蚊子偵測模組

使用深度學習 AI 模型（YOLOv8）進行蚊子偵測，針對 Orange Pi 5 優化。

**AI 模型:**
- **YOLOv8**: 深度學習物體檢測模型
- **推薦**: 使用蚊子專用訓練模型
- **性能**: 10-20 FPS (CPU, 320x320), 25-35 FPS (NPU 加速)

**主要功能:**
- AI 智能偵測蚊子
- 返回邊界框、信心度、類別
- 計算目標中心座標
- 繪製偵測結果和信心度

**使用範例:**

```python
from mosquito_detector import MosquitoDetector

# 初始化 AI 偵測器
detector = MosquitoDetector(
    model_path='models/mosquito_yolov8.pt',   # 使用蚊子專用模型
    confidence_threshold=0.4,
    imgsz=320  # Orange Pi 5 建議使用 320 提升速度
)

# 在影像中偵測蚊子
detections, _ = detector.detect(frame)

# 取得信心度最高的目標
best = detector.get_largest_detection(detections)
if best:
    bbox = best['bbox']  # (x, y, w, h)
    confidence = best['confidence']
    class_name = best['class_name']
    center = best['center']  # (cx, cy)
```

**測試:**

```bash
python mosquito_detector.py
```

**快捷鍵:**
- `q`: 退出
- `s`: 儲存當前幀

**模型資源:**
- 參見 [MOSQUITO_MODELS.md](MOSQUITO_MODELS.md) 了解模型改進與訓練
- 參見 [../python/README.md](../python/README.md) 了解詳細配置

---

### 4. `pt2d_controller.py` - Arduino 雲台控制模組

透過串口與 Arduino 通訊，控制 2D 雲台。

**支援命令:**
- `move_to(pan, tilt)`: 移動到絕對位置
- `move_by(delta_pan, delta_tilt)`: 相對移動
- `get_position()`: 獲取當前角度
- `home()`: 回到初始位置
- `stop()`: 停止移動

**使用範例:**

```python
from pt2d_controller import PT2DController

with PT2DController('COM3') as pt:
    # 設置到中央位置
    pt.home()

    # 移動到指定位置
    pt.move_to(135, 90)

    # 獲取當前位置
    pan, tilt = pt.get_position()
    print(f"位置: {pan}°, {tilt}°")
```

**測試:**

```bash
python3 pt2d_controller.py
```

---

### 5. `mosquito_tracker.py` - AI 主追蹤系統

整合所有模組，實現基於 AI 的自動蚊子追蹤。

**工作流程:**

```
1. 系統啟動 → 載入 AI 模型 → 雲台回到中心位置
2. AI 持續分析影像（YOLOv8）
3. 檢測到蚊子 → 獲取位置和信心度
4. 信心度 > 閾值 → 進入追蹤模式
5. 計算偏移量 → PID 控制雲台對準
6. 目標接近中心 (±30px) + 高信心度 → 啟動雷射標記
7. 失去目標或信心度過低 → 回到監控模式
```

**AI 增強特性:**
- ✅ 精確識別蚊子（減少誤報）
- ✅ 信心度評分（只追蹤高可信度目標）
- ✅ 多目標處理（選擇最佳目標）
- ✅ 類別過濾（排除非蚊子物體）

**操作說明:**

```bash
# Orange Pi 5 運行 AI 追蹤系統
sudo python3 mosquito_tracker.py

# 如果沒有 AI 模型，會使用預訓練模型（效果較差）
# 建議先下載蚊子專用模型到 models/ 目錄
```

**快捷鍵:**
- `q`: 退出系統
- `h`: 回到初始位置
- `l`: 手動切換雷射開關
- `SPACE`: 手動標記（短脈衝 0.2 秒）
- `+/-`: 調整信心度閾值

**視窗說明:**
- **AI Mosquito Tracker**: 主視窗，顯示 AI 檢測框和信心度
- **左側資訊**: 檢測數量、FPS、信心度、追蹤狀態

**狀態指示:**
- **TRACKING** (紅色): AI 追蹤中
- **CONFIDENCE: 0.85** (綠色): 當前目標信心度
- **LASER: ON** (綠色): 雷射已啟動
- **FPS**: 系統處理幀率

---

## ⚙️ 配置參數

### Orange Pi 5 AI 系統設定

在 `mosquito_tracker.py` 中修改:

```python
# Arduino 串口
ARDUINO_PORT = '/dev/ttyUSB0'  # Orange Pi / Linux
# ARDUINO_PORT = 'COM3'  # Windows（開發測試用）

# 雙目攝像頭設定
LEFT_CAMERA_ID = 0
RIGHT_CAMERA_ID = 1
CAMERA_WIDTH = 1920   # 每個攝像頭 1920x1080
CAMERA_HEIGHT = 1080
CAMERA_FPS = 60       # 支援最高 60fps

# AI 檢測設定
AI_MODEL_PATH = 'models/mosquito_yolov8.pt'   # 蚊子專用模型
CONFIDENCE_THRESHOLD = 0.4    # 信心度閾值（0.3-0.6）
DETECTION_IMGSZ = 320         # 輸入解析度（320/416/640）

# 追蹤參數
CENTER_THRESHOLD = 30  # 中心容差（像素）
PID_KP = 0.05         # PID 比例係數
PID_KI = 0.01         # PID 積分係數
PID_KD = 0.02         # PID 微分係數

# 雷射控制
ENABLE_LASER = True      # 啟用雷射標記
LASER_GPIO_PIN = 5       # GPIO 引腳（實體 Pin 5）
LASER_PULSE_DURATION = 0.2  # 脈衝時長（秒）

# 光照度智能監測
ENABLE_ILLUMINATION_MONITORING = True      # 啟用光照監測
ILLUMINATION_WARNING_THRESHOLD = 60        # 警告光照值（0-255）
ILLUMINATION_PAUSE_THRESHOLD = 40          # 暫停/恢復 AI 檢測光照值
ILLUMINATION_CHECK_INTERVAL = 5.0          # 光照檢測間隔（秒）

```

### AI 模型優化設定

**性能 vs 準確度權衡:**

| 解析度 | FPS (CPU) | FPS (NPU) | 準確度 | 建議用途 |
|--------|-----------|-----------|--------|---------|
| 320x320 | 15-20 | 25-35 | 中 | **推薦**（速度優先） |
| 416x416 | 10-15 | 20-25 | 中高 | 平衡模式 |
| 640x640 | 5-8 | 15-20 | 高 | 準確度優先（較慢） |

**信心度閾值建議:**
- `0.3-0.4`: 檢測更多目標，可能有誤報
- `0.4-0.5`: **推薦設定**，平衡
- `0.5-0.7`: 只追蹤高信心度目標，減少誤報

### 檢查串口設備

```bash
# 列出所有 USB 設備
ls -l /dev/ttyUSB*
ls -l /dev/ttyACM*

# 查看設備資訊
dmesg | grep tty

# 給予串口權限
sudo chmod 666 /dev/ttyUSB0
# 或加入 dialout 群組
sudo usermod -a -G dialout $USER
```

### 檢查攝像頭

```bash
# 列出所有視訊設備
ls -l /dev/video*

# 查看攝像頭資訊
v4l2-ctl --list-devices

# 測試攝像頭
python3 -c "import cv2; cap = cv2.VideoCapture(0); print('Camera 0:', cap.isOpened())"
```

### 檢查 GPIO

```bash
# 查看 GPIO 狀態
sudo cat /sys/kernel/debug/gpio

# 測試 GPIO（Pin 5）
sudo python3 -c "import OPi.GPIO as GPIO; GPIO.setmode(GPIO.BOARD); GPIO.setup(5, GPIO.OUT); GPIO.output(5, GPIO.HIGH); print('GPIO Test OK')"
```

### 光照度智能監測參數

在 `mosquito.ini` 中調整光照度監測設定:

``ini
[ILLUMINATION_MONITORING]
# 是否啟用光照度監控
enable_illumination_monitoring = true

# 光照度警告閾值（亮度值 0-255 範圍）
# 低於此值時在螢幕提示光照不足
illumination_warning_threshold = 60

# 光照度暫停閾值（亮度值 0-255 範圍）
# 低於此值時暫停 AI 檢測，高於此值時恢復 AI 檢測
illumination_pause_threshold = 40

# 光照度檢查間隔（秒）- 每 N 秒檢查一次亮度
illumination_check_interval = 5.0
```

**光照度監測工作原理：**

1. **光照估算**: 將每幀影像轉換為灰階，計算平均像素值（0-255）
2. **狀態判斷**:
   - `亮度 >= 60`: 正常運行（綠色）
   - `40 <= 亮度 < 60`: 警告狀態（橙色）
   - `亮度 <= ILLUMINATION_PAUSE_THRESHOLD`: 暫停 AI 檢測（紅色）
3. **自動暫停**: 光照過低時，AI 檢測自動暫停，減少計算浪費和誤報

**建議參數設定：**

| 環境 | WARNING | PAUSE | RESUME | 說明 |
|------|---------|-------|--------|------|
| 室內亮光 | 30 | 15 | 25 | 預設設定，適合大多數場景 |
| 室外陽光 | 60 | 40 | 50 | 提高閾值，適應高亮度 |
| 暗室/夜間 | 20 | 10 | 18 | 降低閾值，提高檢測敏感度 |

**UI 顯示說明：**
- 🟢 **綠色**: 正常運行，光照充足
- 🟠 **橙色**: 光照警告，接近暫停
- 🔴 **紅色**: AI 檢測已暫停，光照過低
- 🟡 **黃色**: AI 檢測已恢復，光照改善

### AI 模型參數調整

在 `MosquitoDetector` 初始化時調整:

```python
detector = MosquitoDetector(
    model_path='models/mosquito_yolov8.pt',   # 模型路徑
    confidence_threshold=0.4,                  # 信心度閾值（0.3-0.7）
    iou_threshold=0.45,                        # IoU 閾值（NMS）
    imgsz=320                                  # 輸入解析度（320/416/640）
)
```

### 追蹤控制參數

在 `MosquitoTracker` 中調整:

```python
self.pan_gain = 0.15              # Pan 軸增益
self.tilt_gain = 0.15             # Tilt 軸增益
self.confidence_min = 0.4         # 最低信心度要求
self.center_threshold = 30        # 中心容差（像素）
```

---

## 🔧 故障排除

### 1. AI 模型相關問題

**問題: 找不到模型檔案**
```bash
# 檢查模型檔案
ls -l models/

# 下載預訓練模型（首次會自動下載）
python3 -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
```

**問題: 推理速度太慢（< 10 FPS）**
```python
# 降低輸入解析度
detector = MosquitoDetector(imgsz=320)  # 從 640 降到 320

# 或轉換為 ONNX 格式
# 參見 ../python/README.md
```

**問題: 檢測效果不佳**
- 使用蚊子專用模型（參見 MOSQUITO_MODELS.md）
- 調整信心度閾值（降低到 0.3）
- 改善照明條件（最低 0.5 lux）
- 確保攝像頭清晰對焦

### 2. 無法開啟攝像頭

**檢查項目:**
- 確認攝像頭已正確連接到 USB 3.0
- 檢查設備 ID 是否正確
- 確認沒有其他程式占用攝像頭

**解決方法:**
```bash
# 列出視訊設備
ls -l /dev/video*

# 查看攝像頭資訊
v4l2-ctl --list-devices

# 測試雙目攝像頭
python3 -c "import cv2; \
cap0 = cv2.VideoCapture(0); \
cap1 = cv2.VideoCapture(1); \
print('Left:', cap0.isOpened(), 'Right:', cap1.isOpened())"
```

### 3. Arduino 無法連接

**檢查項目:**
- 確認串口號正確 (`/dev/ttyUSB0` 或 `/dev/ttyACM0`)
- 檢查 Arduino 是否已上傳韌體
- 確認波特率設定為 `115200`

**解決方法:**
```bash
# 列出串口設備
ls -l /dev/tty* | grep -E "(USB|ACM)"

# 查看設備訊息
dmesg | grep tty

# 測試串口通訊
python3 -c "import serial; ser = serial.Serial('/dev/ttyUSB0', 115200); print('Serial OK')"
```

### 4. GPIO 權限問題

**問題: 無法控制雷射（權限錯誤）**
```bash
# 添加用戶到 gpio 群組
sudo usermod -a -G gpio $USER

# 或使用 sudo 運行
sudo python3 mosquito_tracker.py
```

### 5. 追蹤反應過慢或過快

**調整建議:**
- 增加 `pan_gain` 和 `tilt_gain` 以加快反應
- 減少增益以獲得更平滑的追蹤
- 調整攝像頭幀率與解析度

---

## 📊 效能優化

### Orange Pi 5 效能調整

**提升 AI 推理速度:**

```python
# 1. 降低輸入解析度（最有效）
detector = MosquitoDetector(imgsz=320)  # 從 640 降到 320

# 2. 使用 ONNX 格式模型
# 參見 ../python/README.md 的轉換方法

# 3. 跳幀處理（不是每幀都檢測）
frame_count = 0
while True:
    ret, frame = cap.read()
    frame_count += 1
    if frame_count % 2 == 0:  # 每 2 幀才檢測
        detections, _ = detector.detect(frame)
```

**降低攝像頭解析度:**

```python
# 如果不需要高解析度，可降低到 720p 或 480p
camera = StereoCamera(
    width=1280,   # 從 1920 降到 1280
    height=720,   # 從 1080 降到 720
    fps=30        # 從 60 降到 30
)
```

**系統資源監控:**

```bash
# 查看 CPU 使用率
htop

# 查看記憶體使用
free -h

# 監控溫度
cat /sys/class/thermal/thermal_zone0/temp
```

### 提高檢測準確度

```python
# 1. 使用蚊子專用模型（最重要）
detector = MosquitoDetector(
    model_path='models/mosquito_yolov8.pt'
)

# 2. 提高信心度閾值
detector = MosquitoDetector(confidence_threshold=0.5)

# 3. 改善環境照明
# 確保至少 0.5 lux 照度（攝像頭規格最低需求）
```

---

## 🎯 進階功能

### 使用 RKNN NPU 加速

```bash
# 1. 轉換模型為 RKNN 格式
python convert_to_rknn.py

# 2. 使用 RKNN 模型
# 需要修改 mosquito_detector.py 支援 RKNN Runtime
# 參見 ../python/README.md
```

### 雙目深度估計

```python
# 使用雙目視覺估計蚊子距離
from depth_estimator import DepthEstimator
from stereo_camera import StereoCamera

# 初始化（image_width 應傳入實際單眼解析度）
estimator = DepthEstimator(
    focal_length=3.0,     # 焦距 3.0mm
    baseline=120.0,       # 雙目基線 12cm
    image_width=1920      # 單眼解析度（根據實際攝像頭配置）
)
camera = StereoCamera(left_id=0, right_id=1)

# 讀取影像
ret, left, right = camera.read()

# AI 檢測蚊子
from mosquito_detector import MosquitoDetector
detector = MosquitoDetector()
detections, _ = detector.detect(left)

# 計算每個蚊子的距離
for detection in detections:
    bbox = detection['bbox']  # (x1, y1, x2, y2)
    depth_info = estimator.estimate_depth_for_detection(left, right, bbox)
    if depth_info:
        distance = depth_info['distance_cm']
        print(f"蚊子距離: {distance:.1f}cm")
```

### 記錄追蹤資料

```python
import csv
import time

# 在 track_mosquito 中記錄
with open('tracking_log.csv', 'a', newline='') as f:
    writer = csv.writer(f)
    writer.writerow([time.time(), target_x, target_y, pan, tilt])
```

### 視覺化軌跡

```python
# 在追蹤器中保存軌跡點
self.trajectory = []

# 在 track_mosquito 中記錄
self.trajectory.append((target_x, target_y))

# 繪製軌跡
for i in range(1, len(self.trajectory)):
    cv2.line(frame, self.trajectory[i-1], self.trajectory[i], (255, 0, 0), 2)
```

---

## 📖 相關文件

### 主要文檔
- **[../python/README.md](../python/README.md)** - AI 蚊子偵測與追蹤整合指南（取代 AI_DETECTION_GUIDE）
- **[MOSQUITO_MODELS.md](MOSQUITO_MODELS.md)** - 蚊子檢測模型持續改進指南
- **[../docs/hardware.md](../docs/hardware.md)** - 硬體連接詳細說明（含雙目攝像頭規格）
- **[../docs/protocol.md](../docs/protocol.md)** - Arduino 通訊協議

### 快速參考
- **AI 模型**: 預設模型已包含在 models/ 目錄中
- **性能優化**: 使用 640x640 解析度，ONNX/RKNN 格式
- **雙目攝像頭**: 3840×1080 @ 60fps，12cm 基線距離
- **NPU 加速**: RKNN Toolkit 2 轉換和使用指南

### 技術規格
| 項目 | 規格 |
|------|------|
| **平台** | Orange Pi 5 (RK3588) |
| **NPU** | 6 TOPS |
| **攝像頭** | 雙目 1920×1080 @ 60fps |
| **AI 模型** | YOLOv8n (6MB) |
| **推理速度** | 15-35 FPS |
| **雲台** | 總線舵機 2 軸 |

---

## 📝 授權

本專案採用 Apache 2.0 授權，詳見 [LICENSE](../LICENSE)。

---

## 🤝 貢獻

歡迎提交 Issue 或 Pull Request！

---

**版本**: 2.0.0 (AI 檢測版)
**更新日期**: 2025年12月23日
**硬體平台**: Orange Pi 5

![GA Tracking](https://ga4.ma7.in/ga/github/python_README/Python端說明)
