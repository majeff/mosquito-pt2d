# 蚊子自動追蹤系統 - Python 端說明

## 📋 概述

本專案整合雙目 1080p USB 攝像頭、影像識別、Arduino 雲台控制與雷射標記系統，實現自動蚊子偵測、追蹤與標記功能。

**硬體平台**: Orange Pi 5

### 系統架構

```
┌─────────────────────────────────────┐
│        Orange Pi 5 主控制器          │
│  ┌─────────────────────────────┐   │
│  │  Python 追蹤系統             │   │
│  │  - 雙目影像識別              │   │
│  │  - 蚊子偵測                  │   │
│  │  - 追蹤控制                  │   │
│  │  - 雷射標記                  │   │
│  └─────────────────────────────┘   │
└──┬────────┬────────┬────────┬──────┘
   │ USB    │ USB    │ USB    │ GPIO
   ▼        ▼        ▼        ▼
┌────────┐ ┌────┐ ┌────┐  ┌─────────┐
│Arduino │ │左攝│ │右攝│  │繼電器   │
│雲台控制│ │1080p│ │1080p│ │+雷射    │
└────────┘ └────┘ └────┘  └─────────┘
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

# 安裝 GPIO 控制庫（雷射控制）
pip3 install OrangePi.GPIO

# 設定 GPIO 權限
sudo usermod -a -G gpio $USER
# 需登出後重新登入生效
```

### 3. 硬體連接

- **Arduino**: 透過 GPIO UART（杜邦線）連接至 Orange Pi 5
    - Orange Pi TXD → Arduino `RX0` (D0)
    - Orange Pi RXD ← Arduino `TX0` (D1)（需電位轉換 5V→3.3V）
    - 共地：Orange Pi GND ↔ Arduino GND ↔ 舵機電源 GND
    - 可能的裝置節點：`/dev/ttyS1`、`/dev/ttyS3`（用 `dmesg | grep tty` 確認）
    - 若改用 USB 轉接線，裝置節點通常為 `/dev/ttyUSB0`
- **左/右攝像頭**: USB 3.0 連接（UVC 相容）
- **雷射模組**: GPIO Pin 5 (BOARD 實體引腳 5) 經繼電器控制

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

### 2. `mosquito_detector.py` - 蚊子偵測模組

使用運動檢測技術偵測蚊子。

**偵測方法:**
- **背景減法 (Background Subtraction)**: 適合靜態背景
- **幀差法 (Frame Difference)**: 適合動態背景

**主要功能:**
- 偵測移動物體
- 篩選合適大小的目標
- 計算目標中心座標
- 繪製偵測結果

**使用範例:**

```python
from mosquito_detector import MosquitoDetector

detector = MosquitoDetector(min_area=20, max_area=800)

# 在影像中偵測蚊子
detections, mask = detector.detect(frame, method='background')

# 取得最大目標
largest = detector.get_largest_detection(detections)
if largest:
    x, y, w, h = largest
    center = detector.get_center(largest)
```

**測試:**

```bash
python mosquito_detector.py
```

**快捷鍵:**
- `q`: 退出
- `r`: 重置偵測器
- `m`: 切換偵測方法

---

### 3. `pt2d_controller.py` - Arduino 雲台控制模組

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
**測試:**

```bash
python3 pt2d_controller.py
```

---

### 4. `laser_controller.py` - 雷射標記控制模組

透過 Orange Pi 5 GPIO 控制繼電器來啟動/關閉雷射模組。

**支援功能:**
- `on()`: 開啟雷射
- `off()`: 關閉雷射
- `pulse(duration)`: 發出脈衝
- `blink(count, on_time, off_time)`: 閃爍
- `get_state()`: 獲取當前狀態

**使用範例:**

```python
from laser_controller import LaserController

with LaserController(gpio_pin=5) as laser:
    # 開啟雷射
    laser.on()
    time.sleep(1)

    # 關閉雷射
    laser.off()

    # 脈衝標記
    laser.pulse(duration=0.2)

    # 閃爍
    laser.blink(count=3, on_time=0.1, off_time=0.1)
```

**測試:**

```bash
# 需要 GPIO 權限
sudo python3 laser_controller.py
```

**安全提醒:**
- ⚠️ 使用 1mW 紅光雷射（Class II 安全等級）
- ⚠️ 請勿直視雷射光
- ⚠️ 確保雷射指向安全方向

---

### 4. `mosquito_tracker.py` - 主追蹤系統

整合所有模組，實現自動蚊子追蹤。

**工作流程:**

```
1. 系統啟動 → 雲台保持中央靜止（Pan 中心 / Tilt 90°）
2. 持續監控影像
3. 偵測到蚊子 → 進入手動追蹤（Python 控制移動）
4. 計算偏移量 → 控制雲台對準目標
5. 目標接近中心 (±30px) → 啟動雷射標記
6. 失去目標 → 停止移動，保持中央等待，關閉雷射
```

**操作說明:**

運行系統後，雲台保持中央等待：

```bash
# Orange Pi 5 運行
sudo python3 mosquito_tracker.py
```

**快捷鍵:**
- `q`: 退出系統
- `r`: 重置偵測器
- `h`: 回到初始位置
- `l`: 手動切換雷射開關
- `SPACE`: 手動標記（短脈衝 0.2 秒）

**視窗說明:**
- **Mosquito Tracker**: 主視窗，顯示偵測與追蹤結果
- **Detection Mask**: 偵測遮罩視窗，用於調試

**狀態指示:**
- **TRACKING** (紅色): 追蹤中
- **LASER: ON** (綠色): 雷射已啟動
- **LASER: OFF** (灰色): 雷射關閉

---

## ⚙️ 配置參數

### Orange Pi 5 設定

在 `mosquito_tracker.py` 中修改:

```python
ARDUINO_PORT = '/dev/ttyUSB0'  # Orange Pi / Linux
# ARDUINO_PORT = 'COM3'  # Windows（開發測試用）

# 攝像頭設定（1080p）
LEFT_CAMERA_ID = 0
RIGHT_CAMERA_ID = 1
camera_width = 1920
camera_height = 1080

# 雷射控制
enable_laser = True      # 啟用雷射標記
laser_gpio_pin = 5       # GPIO 引腳（實體 Pin 5）
```

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

### 偵測參數調整

在 `MosquitoDetector` 初始化時調整:

```python
detector = MosquitoDetector(
    min_area=20,          # 最小偵測面積 (像素)
    max_area=800,         # 最大偵測面積
    motion_threshold=25,  # 運動閾值
    blur_kernel=5         # 模糊核心大小
)
```

### 追蹤控制參數

在 `MosquitoTracker` 中調整:

```python
self.pan_gain = 0.15              # Pan 軸增益
self.tilt_gain = 0.15             # Tilt 軸增益
self.no_detection_timeout = 3.0   # 無偵測超時 (秒)
```

---

## 🔧 故障排除

### 1. 無法開啟攝像頭

**檢查項目:**
- 確認攝像頭已正確連接
- 檢查設備 ID 是否正確
- 確認沒有其他程式占用攝像頭

**解決方法:**
```python
# 測試攝像頭 ID
import cv2
for i in range(5):
    cap = cv2.VideoCapture(i)
    if cap.isOpened():
        print(f"攝像頭 ID {i} 可用")
        cap.release()
```

### 2. Arduino 無法連接

**檢查項目:**
- 確認串口號正確（Windows 裝置管理員查看）
- 檢查 Arduino 是否已上傳韌體
- 確認波特率設定為 `115200`

**解決方法:**
```python
# 列出可用串口
import serial.tools.list_ports
ports = serial.tools.list_ports.comports()
for port in ports:
    print(f"可用串口: {port.device}")
```

### 3. 偵測效果不佳

**調整建議:**
- 增加照明，確保環境光線充足
- 使用純色背景，避免複雜紋理
- 調整 `min_area` 與 `max_area` 參數
- 嘗試不同的偵測方法 (`background` 或 `frame_diff`)
- 降低 `motion_threshold` 以提高靈敏度

### 4. 追蹤反應過慢或過快

**調整建議:**
- 增加 `pan_gain` 和 `tilt_gain` 以加快反應
- 減少增益以獲得更平滑的追蹤
- 調整攝像頭幀率與解析度

---

## 📊 效能優化

### 降低延遲

```python
# 降低攝像頭解析度
camera = StereoCamera(width=320, height=240)

# 提高處理速度
detector = MosquitoDetector(blur_kernel=3)
```

### 提高穩定性

```python
# 增加偵測面積範圍
detector = MosquitoDetector(min_area=50, max_area=1000)

# 增加無偵測超時時間
tracker.no_detection_timeout = 5.0
```

---

## 🎯 進階功能

### 使用單一攝像頭

如果只有一個攝像頭，可修改 `mosquito_tracker.py`:

```python
# 使用單一攝像頭
ret, frame = self.camera.read_left()  # 保持不變
```

並將 `camera_right_id` 設為 `-1` 或與左攝像頭相同。

### 記錄追蹤資料

```python
import csv

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

- [Arduino 韌體說明](../docs/protocol.md)
- [硬體連接指南](../docs/hardware.md)
- [通訊協議](../docs/protocol.md)

---

## 📝 授權

本專案採用 MIT 授權，詳見 [LICENSE](../LICENSE)。

---

## 🤝 貢獻

歡迎提交 Issue 或 Pull Request！
