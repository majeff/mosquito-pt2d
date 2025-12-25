# Orange Pi 5 硬體連接指南（含 UART 與雷射）

本文件補充說明 Orange Pi 5、雙目 1080p 攝像頭與雷射標記系統的詳細連接方式。

請同時參考主要硬體文件：[hardware.md](hardware.md)

---

│  [影像處理] 雙目攝像頭 -> 蚊子偵測 -> 追蹤   │
│  [控制邏輯] 靜止等待 -> 發現目標 -> 雲台移動  │
│  [雷射標記] 目標居中 (±30px) -> 啟動雷射    │
│                                              │
## 📋 Orange Pi 5 系統組件清單

| 組件 | 規格 | 數量 | 備註 |
|-----|------|------|------|
| Orange Pi 5 | 8GB/16GB RAM | 1 | 主控制器，運行影像識別 |
| microSD 卡 | 64GB+ Class 10 | 1 | 系統儲存 |
| Orange Pi 電源 | 5V/4A USB-C | 1 | 主控供電 |
| 雙目攝像頭 | 1080p USB | 2 | 左右攝像頭 |
| 雷射模組 | 1mW 紅光 | 1 | 目標標記（Class II，5V 模組） |
| 杜邦線 | 公對母 | 10+ | GPIO 連接 |
| 散熱片/風扇 | - | 1 | Orange Pi 5 散熱（建議） |

---
    │   Nano      │              │  7.4V       │
## 🔌 Orange Pi 5 GPIO 接線詳解

### 40-Pin GPIO 引腳圖

```
Orange Pi 5 (實體引腳編號 - BOARD 模式)

    │ Pin 10/11    │              │ LX-16A       │
    3.3V  [ 1] [ 2]  5V      ← 5V 供電輸出
   GPIO3  [ 3] [ 4]  5V      ← 5V 供電輸出
   GPIO5  [ 5] [ 6]  GND     ← 雷射控制 & 共地
  GPIO11  [ 7] [ 8]  GPIO14
     GND  [ 9] [10]  GPIO15
  GPIO17  [11] [12]  GPIO18
  GPIO27  [13] [14]  GND
  GPIO22  [15] [16]  GPIO23
  GPIO10  [19] [20]  GND
   GPIO9  [21] [22]  GPIO25
  GPIO11  [23] [24]  GPIO8
     GND  [25] [26]  GPIO7
   ...以下省略...
```

## 連線方式總覽

本系統使用 USB 連接 Arduino：

**USB-Serial 連接（推薦）**
- 使用 Arduino Nano 的 USB（CH340/ATmega328P）與 Orange Pi 的 USB 直連
- 優點：簡單方便、穩定可靠、無需電位轉換
- 系統節點：`/dev/ttyUSB*` 或 `/dev/ttyACM*`
- 注意：仍需與舵機電源共地（透過 USB 已與 Arduino 共地）
- 線材固定避免鬆動

### Arduino USB 連接

| Orange Pi 埠 | 功能 | 連接至 |
|--------------|------|--------|
| **USB** | Arduino Nano USB | Arduino Nano USB 埠（CH340/ATmega328P） |
| **Pin 6/9** | GND | Arduino GND / 系統共地 |

> 注意：USB 連接無需電位轉換，裝置節點通常為 `/dev/ttyUSB0` 或 `/dev/ttyACM0`。
> 雷射模組由 Arduino 控制，無需在 Orange Pi 這邊做任何連接。

---

## 🔋 完整系統接線圖（示意）

```
┌──────────────────────────────────────────────┐
│            Orange Pi 5 主控制器               │
├──────────────────────────────────────────────┤
│                                              │
│  USB Port ─────────────> Arduino Nano        │
│  USB 3.0 Port 2 ──────> 左攝像頭 (1080p)     │
│  USB 3.0 Port 3 ──────> 右攝像頭 (1080p)     │
│                                              │
│                         │                    │
└─────────────────────────┼────────────────────┘
                          │
                          │ 系統共地
           ┌──────────────┴──────────────┐
           │                             │
    ┌──────▼──────┐              ┌──────▼──────┐
    │  Arduino    │              │  舵機電源    │
    │             │              │  6-8.4V     │
    └──────┬──────┘              └──────┬──────┘
           │                             │
           │ Serial                      │ Power
           ▼                             ▼
    ┌──────────────┐              ┌──────────────┐
    │ 舵機總線      │◄────────────│ Pan & Tilt   │
    │ (TX/RX)      │              │ 舵機 ×2      │
    └──────────────┘              └──────────────┘

          ┌────────────┐
GPIO/MOSFET → │ 雷射模組   │
EN/VCC      │ 1mW 紅光   │
          └────────────┘
```

---

## 🔧 接線步驟

### Step 1: 準備工作

1. **斷開所有電源**
2. 準備工具：螺絲刀、尖嘴鉗、萬用電表
3. 準備材料：杜邦線、繼電器、雷射模組

### Step 2: 繼電器接線

```bash
# 控制端（低壓側）
1. VCC  接  Orange Pi Pin 2 (5V)
2. GND  接  Orange Pi Pin 6 (GND)
3. IN   接  Orange Pi Pin 5 (GPIO 3)

# 輸出端（負載側）
4. COM  接  5V 電源正極（獨立或共用）
5. NO   接  雷射模組 VCC (紅線)
6. NC   不接（常閉端不使用）
```

### Step 3: 雷射模組接線

```bash
1. 雷射 VCC (紅線) 接 繼電器 NO
2. 雷射 GND (黑線) 接 系統共地
   (與 Orange Pi GND、Arduino GND 相連)
```

### Step 4: 確認共地

使用萬用電表確認以下所有 GND 導通：
- Orange Pi GND
- Arduino GND
- 舵機電源 GND
- 繼電器 GND
- 雷射模組 GND

### Step 5: 測試

```bash
# 1. 上電前最後檢查
- 檢查所有接線
- 確認電源極性
- 確認共地連接

# 2. 分階段上電
- 先接 Orange Pi 5 電源
- 觀察系統啟動
- 登入系統

# 3. 測試雷射控制
cd /path/to/mosquito-pt2d/python
sudo python3 laser_controller.py

# 4. 觀察繼電器
- 聽到「喀嗒」聲 → 繼電器正常
- 雷射亮起 → 接線正確
```

---

## 📷 攝像頭配置

### 雙目 1080p 攝像頭

**規格要求**:
- 解析度: 1920×1080 @ 30fps
- 介面: USB 2.0 或 3.0
- 支援 UVC (USB Video Class)
- 視角: 60°-90°

**連接方式**:
```
Orange Pi 5
├─ USB 3.0 Port 2 ──> 左攝像頭 (/dev/video0)
└─ USB 3.0 Port 3 ──> 右攝像頭 (/dev/video1)
```

**檢查攝像頭**:
```bash
# 列出視訊設備
ls -l /dev/video*

# 查看設備資訊
v4l2-ctl --list-devices

# 測試攝像頭
python3 -c "import cv2; cap = cv2.VideoCapture(0); print('Left:', cap.isOpened()); cap.release()"
python3 -c "import cv2; cap = cv2.VideoCapture(1); print('Right:', cap.isOpened()); cap.release()"
```

### 攝像頭安裝位置

```
        [左攝像頭]     [右攝像頭]
             │             │
             └─────┬───────┘
                   │
           ┌───────▼────────┐
           │   Tilt 軸舵機   │
           └────────────────┘
                   │
           ┌───────▼────────┐
           │   Pan 軸舵機    │
           └────────────────┘

[雷射模組] ← 固定在雲台上，與攝像頭平行
```

**建議**:
- 攝像頭間距: 6-10 cm（模擬人眼間距）
- 雷射位置: 與攝像頭中心線對齊
- 固定方式: 使用 3D 列印支架或鋁合金支架

---

## ⚡ 電源規劃

### Orange Pi 5 電源需求

```
Orange Pi 5: 5V/4A (20W)
├─ 系統運行: ~5W
├─ USB 設備: ~5W (Arduino + 攝像頭 ×2)
├─ GPIO 外設: ~1W (雷射控制/MOSFET 門極)
└─ 餘量: ~9W
```

**建議電源**: 5V/4A 或 5V/5A USB-C 電源供應器

### 完整系統電源配置

```
┌─────────────────┐
│ 5V/4A 電源      │──> Orange Pi 5
└─────────────────┘      │
                         ├─ USB ──> Arduino
                         ├─ USB ──> 左攝像頭
                         ├─ USB ──> 右攝像頭
                         └─ GPIO ──> 繼電器 ──> 雷射

┌─────────────────┐
│ 7.4V/2A 電源    │──> 舵機總線 ──> Pan & Tilt 舵機
└─────────────────┘
         │
         └─ GND ──> 系統共地
```

---

## 🛡️ 安全措施

### 電氣安全

1. **絕緣保護**: 使用絕緣膠帶包覆裸露接點
2. **防短路**: 確認接線無短路後再上電
3. **過流保護**: 舵機電源加裝保險絲（3A）
4. **穩壓濾波**: 舵機電源並聯 100μF-1000μF 電容

### 雷射安全

1. **等級標示**: 確認使用 Class II (1mW) 雷射
2. **警告標誌**: 在操作區域張貼雷射警告標誌
3. **防護措施**:
   - 避免直視雷射光束
   - 不要將雷射對準人或動物
   - 在封閉安全區域內測試
   - 兒童使用需成人監督
4. **緊急關閉**: 編寫緊急關閉腳本
   ```bash
   # emergency_stop.sh
   sudo python3 -c "import OPi.GPIO as GPIO; GPIO.setmode(GPIO.BOARD); GPIO.setup(5, GPIO.OUT); GPIO.output(5, GPIO.LOW); GPIO.cleanup()"
   ```

### 機械安全

1. 確保雲台固定牢固
2. 活動範圍內無障礙物
3. 避免手指接近運動中的舵機

---

## 🔍 故障排除

### GPIO 無法控制雷射

**可能原因**:
1. 權限不足
2. GPIO 引腳設定錯誤
3. MOSFET/雷射模組規格不符（電壓/電流）
4. 接線錯誤或未共地

**解決步驟**:
```bash
# 1. 檢查權限
sudo python3 laser_controller.py

# 2. 手動測試 GPIO
sudo python3 << EOF
import OPi.GPIO as GPIO
GPIO.setmode(GPIO.BOARD)
GPIO.setup(5, GPIO.OUT)
GPIO.output(5, GPIO.HIGH)
print("GPIO Pin 5 HIGH")
input("按 Enter 關閉...")
GPIO.output(5, GPIO.LOW)
GPIO.cleanup()
EOF

# 3. 檢查 MOSFET/雷射
# 以萬用電表測 Gate/Drain/Source 電位與雷射 VCC/GND

# 4. 檢查接線
# 使用萬用電表測量電壓
```

### 攝像頭無法開啟

```bash
# 檢查設備
ls -l /dev/video*

# 檢查權限
sudo chmod 666 /dev/video0
sudo chmod 666 /dev/video1

# 測試攝像頭
v4l2-ctl --device=/dev/video0 --all
v4l2-ctl --device=/dev/video1 --all

# 調整解析度
# 編輯 mosquito_tracker.py
camera_width = 1280  # 降為 720p
camera_height = 720
```

---

## 📚 相關文件

- [主 README](../README.md) - 專案總覽
- [hardware.md](hardware.md) - Arduino 硬體連接
- [protocol.md](protocol.md) - 通訊協議
- [Python README](python_README.md) - Python 端說明

---

## 🧩 控制器板注意事項（开源6路机器人机械臂舵机控制器板）

- 多數此類開源 6 路機械臂控制器板以 5V TTL UART 與外部通信。
- **建議使用 USB 連接方式**（Arduino Nano USB ↔ Orange Pi 5 USB）：
   - 簡單穩定，無需電位轉換
   - 裝置為 `/dev/ttyUSB*`/`/dev/ttyACM*`
- 舵機與控制板電源通常為 6V-8.4V（視總線舵機要求），務必與 Orange Pi 共地。

---

**版本**: 1.0.0
**更新日期**: 2025-12-23
**適用硬體**: Orange Pi 5 + Arduino Nano/控制板 + 雷射標記系統
