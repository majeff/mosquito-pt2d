# 硬體連接詳細說明

## 🔌 組件清單

### 必需組件

#### 1. Orange Pi 5（主控制器）
- **功能**: 執行影像處理、AI 辨識、系統控制
- **連接**:
  - USB 3.0 ×2 → 雙目攝像頭 https://item.taobao.com/item.htm?id=910727946025&mi_id=0000nFsaeV90sZPrGM6jCP_KWumdBYLOADsDcBAyRMf5-Bo&spm=tbpc.boughtlist.suborder_itemtitle.1.a4812e8d4MnjEE&sku_properties=10067151%3A124993
  - USB 3.0 → 二维电动舵机云台 (Arduino Nano) https://item.taobao.com/item.htm?id=632434564398&mi_id=0000XD01TvJHXsWTbF9Gk_Wq8ZI-1Jd9l5IGYdH5RwKuwpQ&spm=tbpc.boughtlist.suborder_itemtitle.1.691a2e8dx4UgQn
  - GPIO Pin 5 → 雷射控制繼電器

#### 2. 雙目 USB 攝像頭 ×2

**型號規格**:
- **解析度**: 3840×1080 (每眼 1920×1080)
- **感光元件**: 1/2.7 inch (16:9)
- **輸出格式**: MJPEG / YUV2
- **幀率**: 支援 3840×1080 @ 60fps (MJPEG)
- **最低照度**: 0.5 lux
- **鏡頭**:
  - 焦距: 3.0mm
  - 光圈: F2.4
  - 視角: 96° (對角)
- **雙目基線**: 12cm (左右攝像頭距離)
- **接口**: USB 3.0
- **用途**: 立體視覺、深度估計、蚊子定位

**連接方式**:
```
左攝像頭 ───→ Orange Pi USB 3.0 Port 1
右攝像頭 ───→ Orange Pi USB 3.0 Port 2
```

#### 3. 二维电动舵机云台(Arduino Nano)（雲台控制器）
- **功能**: 控制總線舵機雲台
- **連接方式**: USB 串口與 Orange Pi 通訊

#### 4. 總線舵機 ×2
   - 型號: LewanSoul LX-16A, Feetech SCS15, HTS 等
                                        │ GPIO Pin 5 ──────┼──→ 雷射控制（繼電器）
   - 通訊方式: 串口 (UART)
   - 工作電壓: 6V-8.4V（推薦 7.4V）
   - 波特率: 9600 或 115200
   - 轉動角度: 0-270°
   - 配置: Pan 舵機 (ID=1) + Tilt 舵機 (ID=2)

#### 5. 雷射模組（可選）
- **功能**: 蚊子標定、射擊
- **控制**: GPIO Pin 5 透過繼電器控制

#### 6. 電源系統
- **二维电动舵机云台**: 7.4V
- **總線舵機電源**: 7.4V / 2A 以上（鋰電池或電源適配器）
- **Orange Pi 5 電源**: 5V / 3A（Type-C 供電）

### 可選組件

- 電平轉換模組（5V ↔ 3.3V）
- 繼電器模組（控制雷射）

---

## 📷 攝像頭規格詳細說明

### 雙目立體視覺系統

本專案使用雙 USB 攝像頭構成立體視覺系統，用於：
1. **深度估計**: 通過雙目視差計算蚊子距離
2. **3D 定位**: 獲取蚊子的 3D 空間座標
3. **AI 辨識**: 使用 YOLO 模型進行蚊子檢測

### 技術參數

| 參數 | 規格 | 說明 |
|------|------|------|
| 解析度 | 3840×1080 | 雙眼各 1920×1080 |
| 感光元件 | 1/2.7 inch | 16:9 比例 |
| 輸出格式 | MJPEG / YUV2 | 支援多種格式 |
| 最高幀率 | 60 fps @ 3840×1080 | MJPEG 格式 |
| 最低照度 | 0.5 lux | 低光環境可用 |
| 鏡頭焦距 | 3.0mm | 固定焦距 |
| 光圈 | F2.4 | 大光圈，適合低光 |
| 視角 | 96° (對角) | 寬視角 |
| 雙目基線 | 12cm | 左右攝像頭距離 |
| 接口類型 | USB 3.0 ×2 | 高速數據傳輸 |

### 深度估計原理

雙目基線 12cm 可用於計算深度：

```
深度 (Z) = (焦距 × 基線距離) / 視差 (d)
Z = (f × B) / d

其中:
- f = 鏡頭焦距 = 3.0mm
- B = 雙目基線 = 120mm
- d = 左右圖像視差（像素）
```

**有效測距範圍**: 約 0.5m - 5m（取決於視差精度）

---

## 🔧 總線舵機規格

### 支援型號對照表

| 型號 | 扭矩 | 速度 | 工作電壓 | 通訊方式 | 本專案使用 |
|------|------|------|----------|---------|---------|
| ZD361D | 15kg·cm | 0.16s/60° | 6-8.4V | 串口 (UART) | |
| LX-16A | 16kg·cm | 0.1s/60° | 6-8.4V | 串口 (UART) | |
| SCS15 | 15kg·cm | 0.1s/60° | 6-8.4V | 串口 (UART) | |
| HTS-35H | 35kg·cm | 0.16s/60° | 6-8.4V | 串口 (UART) | ✓ (本專案) |

### Arduino 開發板選擇

| 型號 | 數位引腳 | 串口數量 | 記憶體 | 本專案使用 |
|------|---------|---------|--------|-----------|
| Nano | 14 個 | 1 | 32KB | ✓ (本專案) |
| Uno | 14 個 | 1 | 32KB | 可用 |
| Mega 2560 | 54 個 | 4 | 256KB | 過度規格 |

---

## 🔌 硬體連接步驟

### 步驟 1: 總線舵機接線

**總線舵機串聯連接示意**:

```
Arduino Nano D10 (TX) ──→ Pan 舵機 (ID=1) ──→ Tilt 舵機 (ID=2)
Arduino Nano D11 (RX) ←── 總線數據線（黃/綠）
                  │     │     │
                  └─────┴─────┘
                      共同 GND
```

**線材連接**:

| 線材顏色 | 功能 | 連接到 |
|---------|------|--------|
| 紅色 | VCC (7.4V) | 外接電源正極 |
| 黑/棕色 | GND | 共地（Arduino + 電源） |
| 黃/綠色 | 數據線 | Arduino D10 (TX) |

**電源連接**:

```
外接 7.4V ─┬── 所有舵機 VCC (紅線)
           └── Arduino VIN (可選)

共地 ──────┬── 舵機 GND
           ├── Arduino GND
           └── 外接電源 GND
```

### 步驟 2: 攝像頭連接

```
左攝像頭 USB 3.0 ──→ Orange Pi 5 USB Port 1
右攝像頭 USB 3.0 ──→ Orange Pi 5 USB Port 2
```

**設備識別** (在 Orange Pi 上執行):
```bash
ls /dev/video*
# 應顯示: /dev/video0 /dev/video1
```

### 步驟 3: Arduino 與 Orange Pi 連接

**方案 A: USB 串口連接（推薦）**

```
Arduino Nano USB ──→ Orange Pi 5 USB 3.0
```

設備路徑: `/dev/ttyUSB0`

**方案 B: UART GPIO 連接（進階）**

需要電平轉換（5V ↔ 3.3V）:

```
Arduino TX (5V) ──→ [電平轉換] ──→ Orange Pi RX (3.3V)
Arduino RX (5V) ←── [電平轉換] ←── Orange Pi TX (3.3V)
Arduino GND ─────────────────────── Orange Pi GND
```

⚠️ **警告**: 直接連接會損壞 Orange Pi GPIO（3.3V 邏輯）

### 步驟 4: 電源系統配置
**推薦配置**:

```
7.4V 鋰電池 (2S, 2000mAh+)
    ├── 總線舵機 ×2 (VCC)
    └── (可選) Arduino VIN

5V / 3A USB-C 電源
    └── Orange Pi 5

USB 供電 (由 Orange Pi)
    └── Arduino Nano
```

#### 電容穩壓（強烈建議）

在舵機電源端並聯大電容：

```
7.4V 電源 ──┬── 470μF-1000μF 電解電容 ──┬── 舵機 VCC
            │                          │
          GND ────────────────────── GND
```

---

## 🖼️ 完整系統連接圖

### 系統架構圖

```
                   Orange Pi 5（主控制器 + AI 運算）
                ┌──────────────────────────────────┐
                │  ┌─────────────────────────────┐ │
                │  │   AI 蚊子辨識 (YOLOv8)      │ │
                │  │   深度估計 (雙目視覺)        │ │
                │  │   追蹤控制邏輯              │ │
                │  └─────────────────────────────┘ │
                │                                   │
左攝像頭 ────────┤ USB 3.0 Port 1                  │
右攝像頭 ────────┤ USB 3.0 Port 2                  │
Arduino ─────────┤ USB 3.0 (/dev/ttyUSB0)          │
雷射繼電器 ──────┤ GPIO Pin 5                      │
                └───────────────────────────────────┘
                                │
                        USB 串口協議
                                │
                     Arduino Nano（雲台控制）
                ┌────────────────────────────┐
                │ D0 (RX) ← USB 串口         │
                │ D1 (TX) → USB 串口         │
                │ D10 (TX) ─┐                │
                │ D11 (RX) ─┤ 總線舵機 UART  │
                │ GND ───────┘                │
                └────────────────────────────┘
                         │     │
                    ┌────┴─────┴────┐
                    │                │
            Pan 舵機 (ID=1)   Tilt 舵機 (ID=2)
                 (水平)          (俯仰)

                     電源系統
        ┌────────────────────────────┐
        │ 7.4V 鋰電池 (2S)           │
        │   ├──→ Pan 舵機 VCC        │
        │   ├──→ Tilt 舵機 VCC       │
        │   └──→ 共地                │
        │                            │
        │ 5V USB-C                   │
        │   └──→ Orange Pi 5         │
        └────────────────────────────┘
```

### 詳細接線圖

```
┌─────────────────────────────────────────────────────────────┐
│                        Orange Pi 5                          │
│                                                             │
│  USB 3.0 Port 1 ──→ 左攝像頭 (3840×1080@60fps)            │
│  USB 3.0 Port 2 ──→ 右攝像頭 (3840×1080@60fps)            │
│  USB 3.0 Port 3 ──→ Arduino Nano (/dev/ttyUSB0)           │
│  GPIO Pin 5 ─────→ 繼電器 IN (雷射控制)                    │
│  5V / GND ───────→ 繼電器 VCC / GND                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                            │
                    Serial @ 115200
                            │
┌─────────────────────────────────────────────────────────────┐
│                      Arduino Nano                           │
│                                                             │
│  D0 (RX) ←── USB Serial (接收指令)                         │
│  D1 (TX) ──→ USB Serial (回傳狀態)                         │
│  D10 ───────→ 總線舵機數據線 (TX)                          │
│  D11 ←────── 總線舵機數據線 (RX)                           │
│  GND ────────┬─→ 舵機 GND                                  │
│  VIN (選用) ─┘   (7.4V 供電，如需要)                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
            │                           │
            │ UART 總線                 │
            │                           │
    ┌───────┴──────┐          ┌────────┴────────┐
    │  Pan 舵機    │          │  Tilt 舵機      │
    │  (ID=1)      │───串聯───│  (ID=2)         │
    │              │          │                 │
    │ VCC: 7.4V    │          │ VCC: 7.4V       │
    │ GND: 共地    │          │ GND: 共地       │
    │ DATA: 總線   │          │ DATA: 總線      │
    └──────────────┘          └─────────────────┘
            │                           │
            └───────────┬───────────────┘
                        │
                  7.4V 電源系統
            ┌───────────────────────┐
            │  7.4V 鋰電池 (2S)     │
            │  容量: 2000mAh+       │
            │  + ──→ 舵機 VCC       │
            │  - ──→ 舵機 GND       │
            │       (並聯 470μF)    │
            └───────────────────────┘
```

---

## ⚠️ 注意事項和常見問題

### 1. 攝像頭問題

**問題**: 無法檢測到攝像頭或幀率低

**檢查項目**:
- 確認使用 USB 3.0 端口（藍色接口）
- 檢查設備: `ls /dev/video*`
- 測試幀率: `v4l2-ctl --device=/dev/video0 --list-formats-ext`

**解決方案**:
```bash
# 安裝 v4l-utils
sudo apt install v4l-utils

# 查看攝像頭支援格式
v4l2-ctl -d /dev/video0 --list-formats-ext

# 設定解析度和幀率
v4l2-ctl -d /dev/video0 --set-fmt-video=width=1920,height=1080,pixelformat=MJPG
```

### 2. 電源問題

**問題**: 總線舵機抖動、Arduino 重啟、USB 斷開

**原因**:
- 總線舵機工作電流較大（每個 200-800mA）
- 必須使用外接電源供電

**解決方案**:
1. 使用外接 6V-8.4V / 2A 以上電源（推薦 7.4V 鋰電池）
2. 添加大容量電解電容（470μF-1000μF）
3. 將 Arduino 和舵機分開供電

### 3. 共地問題

**問題**: 總線舵機不工作或工作不正常

**原因**: Orange Pi 5、Arduino 和舵機電源沒有共地

**解決方案**:
- 確保 Orange Pi GND、Arduino GND 和舵機電源 GND 連接在一起
- 所有地線必須連接到同一個公共地點

### 4. 雙目同步問題

**問題**: 左右攝像頭影像不同步

**解決方案**:
- 使用相同的攝像頭型號和設定
- 在代碼中確保同時捕獲兩個攝像頭的幀
- 檢查 USB 頻寬是否足夠（使用 USB 3.0）

### 5. 深度估計不準確

**問題**: 雙目測距誤差大

**檢查項目**:
- 攝像頭是否平行安裝（不應有角度偏差）
- 雙目基線距離是否為 12cm
- 是否進行了相機標定

**解決方案**:
```python
# 使用 OpenCV 進行相機標定
import cv2
# 標定左右攝像頭
# 計算立體校正參數
# 應用去畸變和校正
```

### 6. 上傳失敗

**問題**: Arduino IDE 或 PlatformIO 上傳程序失敗

**原因**: USB 串口被占用

**解決方案**:
- 關閉 Python 追蹤程式
- 上傳完成後重新啟動追蹤程式

### 7. 過熱問題

**問題**: 總線舵機發熱

**解決方案**:
- 檢查電源電壓是否過高（不要超過 8.4V）
- 添加散熱片
- 避免舵機長時間堵轉
- 減少負載或使用更大扭矩的舵機

---

## 🧪 測試步驟

### 1. 攝像頭測試

**檢查攝像頭連接**:
```bash
# 列出所有攝像頭設備
ls /dev/video*

# 檢查攝像頭資訊
v4l2-ctl --device=/dev/video0 --all
v4l2-ctl --device=/dev/video1 --all

# 測試捕獲影像
ffmpeg -f v4l2 -i /dev/video0 -frames:v 1 test_left.jpg
ffmpeg -f v4l2 -i /dev/video1 -frames:v 1 test_right.jpg
```

**使用 Python 測試**:
```python
import cv2

# 測試左攝像頭
cap_left = cv2.VideoCapture(0)
cap_left.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap_left.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
cap_left.set(cv2.CAP_PROP_FPS, 60)

# 測試右攝像頭
cap_right = cv2.VideoCapture(1)
cap_right.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap_right.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
cap_right.set(cv2.CAP_PROP_FPS, 60)

# 捕獲並顯示
ret_l, frame_l = cap_left.read()
ret_r, frame_r = cap_right.read()

if ret_l and ret_r:
    print(f"左攝像頭: {frame_l.shape}")
    print(f"右攝像頭: {frame_r.shape}")
    cv2.imshow('Left', frame_l)
    cv2.imshow('Right', frame_r)
    cv2.waitKey(0)

cap_left.release()
cap_right.release()
cv2.destroyAllWindows()
```

### 2. 雲台控制測試

在 Orange Pi 5 上運行：

```bash
cd python
python3 pt2d_controller.py
```

使用 Python 控制器測試：

```python
from pt2d_controller import PT2DController

controller = PT2DController('/dev/ttyUSB0')

# 基本移動測試
controller.move_to(90, 90)    # 回到中心位置
controller.move_to(0, 0)      # 移動到最小角度
controller.move_to(180, 180)  # 移動到最大角度

# 相對移動測試
controller.move_by(10, 0)     # Pan 軸增加 10°
controller.move_by(-10, 0)    # Pan 軸減少 10°
controller.move_by(0, 10)     # Tilt 軸增加 10°

# 速度測試
controller.set_speed(10)      # 設置慢速
controller.move_to(180, 90)   # 觀察緩慢移動
controller.set_speed(100)     # 設置快速
controller.move_to(0, 90)     # 觀察快速移動

controller.close()
```

或使用快速測試腳本：

```bash
cd python
python3 quick_start.py
```

### 3. 雙目立體視覺測試

```python
from stereo_camera import StereoCamera

# 初始化雙目攝像頭
stereo = StereoCamera(
    left_id=0,
    right_id=1,
    width=1920,
    height=1080,
    fps=60
)

# 捕獲立體影像對
left_frame, right_frame = stereo.capture()

# 計算視差圖
disparity = stereo.compute_disparity(left_frame, right_frame)

# 估計深度
depth_map = stereo.compute_depth(disparity, baseline=120, focal_length=3.0)

print(f"深度範圍: {depth_map.min():.2f}mm - {depth_map.max():.2f}mm")
```

### 4. AI 檢測測試

```bash
cd python
python mosquito_detector.py
```

### 5. 完整系統測試

```bash
cd python
python quick_start.py
```

觀察：
- 攝像頭是否正常捕獲影像
- AI 是否能檢測到移動物體
- 雲台是否能追蹤目標
- 系統延遲是否可接受

### 6. 電源測試

使用萬用表測量：
- 舵機 VCC: 應為 7.0V-7.8V（7.4V 標稱值）
- 負載時電壓降: 不應低於 6.5V
- Orange Pi 5V: 約 5V
- Arduino 5V: 約 5V（USB 供電）

---

## 📊 硬體規格對照表

### 攝像頭規格總結

| 參數 | 左攝像頭 | 右攝像頭 | 備註 |
|------|---------|---------|------|
| 解析度 | 1920×1080 | 1920×1080 | 合併為 3840×1080 |
| 幀率 | 60 fps | 60 fps | MJPEG 格式 |
| 接口 | USB 3.0 | USB 3.0 | /dev/video0, /dev/video1 |
| 視角 | 96° | 96° | 對角視角 |
| 基線距離 | - | 12cm | 用於深度估計 |

### 總線舵機規格對照

| 型號 | 扭矩 | 速度 | 電流 | 工作電壓 | 適用場景 |
|------|------|------|------|---------|---------|
| LX-16A | 16kg·cm | 0.1s/60° | 200-800mA | 6-8.4V | 推薦 ✓ |
| SCS15 | 15kg·cm | 0.1s/60° | 200-750mA | 6-8.4V | 推薦 ✓ |
| HTS-35H | 35kg·cm | 0.16s/60° | 300-1200mA | 6-8.4V | 重負載 ✓✓ |

### 電源需求總表

| 組件 | 電壓 | 電流 | 功率 | 備註 |
|------|------|------|------|------|
| Orange Pi 5 | 5V | 3A | 15W | Type-C 供電 |
| Arduino Nano | 5V | 100mA | 0.5W | USB 供電 |
| 總線舵機 ×2 | 7.4V | 1.6A (峰值) | ~12W | 獨立供電 |
| 左攝像頭 | 5V | 500mA | 2.5W | USB 供電 |
| 右攝像頭 | 5V | 500mA | 2.5W | USB 供電 |
| 雷射模組 | 5V | 200mA | 1W | GPIO 控制 |
| **總計** | - | - | **~34W** | 推薦 50W 電源 |

---

## 🔗 相關資源

### 官方文檔
- [Orange Pi 5 技術手冊](http://www.orangepi.org/html/hardWare/computerAndMicrocontrollers/details/Orange-Pi-5.html)
- [Arduino Nano 規格](https://docs.arduino.cc/hardware/nano)
- [OpenCV 雙目視覺教學](https://docs.opencv.org/4.x/dd/d53/tutorial_py_depthmap.html)
- [YOLO 物體檢測](https://docs.ultralytics.com/)

### 總線舵機相關
- [LewanSoul LX-16A 說明](https://www.lewansoul.com/)
- [Feetech SCS15 規格](https://www.feetechrc.com/)
- [總線舵機通訊協議](https://github.com/lewansoul/lewansoul-lx16a)

### 雙目視覺資源
- [立體視覺原理](https://en.wikipedia.org/wiki/Stereopsis)
- [相機標定教學](https://docs.opencv.org/4.x/dc/dbb/tutorial_py_calibration.html)
- [深度估計算法](https://docs.opencv.org/4.x/dd/d53/tutorial_py_depthmap.html)

### 專案相關
- [本專案 GitHub](https://github.com/yourusername/mosquito-pt2d)
- [Arduino IDE](https://www.arduino.cc/en/software)
- [PlatformIO](https://platformio.org/)

---

## 📝 版本歷史

| 版本 | 日期 | 變更內容 |
|------|------|---------|
| 1.1.0 | 2025-12-23 | 新增雙目攝像頭詳細規格、AI 檢測說明 |
| 1.0.0 | 2025-12-20 | 初始版本 |

---

**最後更新**: 2025年12月23日
**維護者**: Mosquito PT2D 專案團隊
**授權**: MIT License
