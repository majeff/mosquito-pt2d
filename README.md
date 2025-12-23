# Arduino 2D 雲台控制系統

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-Arduino-red.svg)

一個基於 Arduino 的 2D 雲台（Pan-Tilt）控制系統，通過 UART (TX/RX) 與上位機通訊，實現雙軸伺服馬達的精確控制。

## 📋 目錄

- [功能特點](#功能特點)
- [硬體需求](#硬體需求)
- [軟體需求](#軟體需求)
- [安裝說明](#安裝說明)
- [硬體連接](#硬體連接)
- [使用說明](#使用說明)
- [通訊協議](#通訊協議)
- [專案結構](#專案結構)
- [開發指南](#開發指南)

## ✨ 功能特點

- ✅ 雙軸伺服馬達控制（Pan 水平 & Tilt 垂直）
- ✅ UART 串口通訊（115200 波特率）
- ✅ **兩種工作模式**：
  - 🎮 **手動模式**: 完全由上位機控制
  - 🔄 **自動掃描模式**: 垂直固定 20°，水平慢速掃描 120° (75°-195°)
- ✅ 支援絕對位置和相對位置移動
- ✅ 可調速度控制（1-100）
- ✅ 自動回歸初始位置
- ✅ 校準功能
- ✅ 總線舵機反饋：
  - 📍 位置讀取
  - 🌡️ 溫度監控
  - ⚡ 電壓檢測
- ✅ JSON 格式響應
- ✅ 完整的錯誤處理

## 🔧 硬體需求

### 必需組件

| 組件 | 規格 | 數量 | 備註 |
|-----|------|------|------|
| Arduino 開發板 | Uno/Nano/Mega | 1 | **推薦 Mega** (有硬體 Serial1) |
| **總線舵機** | LX-16A/SCS15/HTS | 2 | **串口舵機，非 PWM** |
| 2D 雲台支架 | 金屬或塑膠 | 1 | 含舵機安裝位 |
| 電源供應器 | **6V-8.4V / 2A** | 1 | 推薦 7.4V 鋰電池 |

### 總線舵機特點

- ✅ 串口控制（UART），非 PWM
- ✅ 可串聯多個舵機（總線）
- ✅ 支持位置反饋
- ✅ 精度高（0.24°）
- ✅ 可設置舵機 ID
- ✅ Pan 水平 270°，Tilt 垂直 180°

## 💻 軟體需求

- [PlatformIO IDE](https://platformio.org/) 或 [Arduino IDE](https://www.arduino.cc/en/software)
- USB 驅動程式（CH340/CP2102 等，視開發板而定）

### PlatformIO 安裝（推薦）

```bash
# 使用 VS Code 安裝 PlatformIO 擴展
# 或使用命令行
pip install platformio
```

## 📦 安裝說明

### 方法 1: 使用 Arduino IDE

```bash
# 1. 將以下文件放在同一文件夾 arduino-pt2d/
arduino-pt2d.ino
BusServoController.h
BusServoController.cpp
SerialProtocol.h (從 include/ 複製)
SerialProtocol.cpp (從 src/ 複製)
config.h (從 include/ 複製)

# 2. 打開 arduino-pt2d.ino
# 3. 選擇開發板和端口
# 4. 上傳
```

**詳細說明**: 參考 [docs/arduino_ide_guide.md](docs/arduino_ide_guide.md)
PlatformIO（推薦）

```bash
# 1. 克隆專案
git clone https://github.com/yourusername/arduino-pt2d.git
cd arduino-pt2d

# 2. 使用 PlatformIO 編譯
pio run

# 3. 上傳到開發板
pio run --target upload

# 4. 監控串口輸出
pio device monitor
```

---

## ⚙️ 配置舵機

### 1. 確認舵機 ID

使用廠商提供的調試軟件或代碼確認舵機 ID：
- Pan 軸舵機：ID = 1
- Tilt 軸舵機：ID = 2

### 2. 修改 config.h

```cpp
// 根據你的舵機調整
#define SERVO_BAUDRATE      115200    // LX-16A: 115200, SCS: 9600 或 1000000
#define PAN_SERVO_ID        1         // Pan 軸舵機 ID
#define TILT_SERVO_ID       2         // Tilt 軸舵機 ID
#define PAN_MAX_ANGLE       270       // Pan 水平最大角度
#define TILT_MAX_ANGLE      180       // Tilt 垂直最大角度
```

---
# 2. 使用 PlatformIO 編譯
pio run

# 3. 上傳到開發板
pio run --target upload

# 4. 監控串口輸出
pio device monitor
```

### 方法 2: 使用 Arduino IDE

1. 下載本專案
2. 將 `include/` 中的 `.h` 文件複製到 Arduino 庫目錄
3. 打開 `src/main.cpp`（重命名為 `.ino`）
4. 編譯並上傳

## 🔌 硬體連接

### 引腳配置

#### Arduino Mega 2560（推薦）

```
Arduino Pin    |  Component
---------------|------------------
TX1 (Pin 18)   |  舵機總線 RX (黃線)
RX1 (Pin 19)   |  舵機總線 TX (綠線)
USB Serial     |  上位機通訊
6V-8.4V        |  舵機 VCC (外接電源)
GND            |  舵機 GND 和電源 GND（共地）
```

#### Arduino Uno/Nano

```
Arduino Pin    |  Component
---------------|------------------
Pin 10         |  舵機總線 RX (黃線，軟串口)
Pin 11         |  舵機總線 TX (綠線，軟串口)
USB Serial     |  上位機通訊
6V-8.4V        |  舵機 VCC (外接電源)
GND            |  舵機 GND 和電源 GND（共地）
```

### 總線舵機串聯

```
Arduino TX1 ──┬──── 舵機1 (ID=1, Pan) ──┬──── 舵機2 (ID=2, Tilt)
              │                          │
Arduino RX1 ─總線舵機需要 **6V-8.4V** 供電（推薦 7.4V 鋰電池）
2. **共地**: 確保 Arduino、舵機、外接電源的 GND 連接在一起
3. **串口選擇**:
   - Mega 使用 Serial1（TX1/RX1）
   - Uno/Nano 使用 SoftwareSerial（需配置）
4. **舵機 ID**: 預設 Pan=ID1, Tilt=ID2，請先確認舵機 ID 設置
5. **波特率**: 預設 115200，LX-16A 常用此波特率，SCS 可能需要調整
```

### ⚠️ 重要注意事項

1. **電源問題**: 伺服馬達耗電較大，建議使用外接 5V 電源，避免 USB 供電不足
2. **共地**: 確保 Arduino、伺服馬達、外接電源的 GND 連接在一起
3. **訊號線**: 伺服馬達的信號線（通常為橙色或白色）接到指定的 PWM 引腳
4. **濾波**: 建議在電源端並聯電容（100μF-1000μF）以減少電壓波動

## 📖 使用說明

### 基本操作

1. **連接硬體**: 按照上述連接圖連接所有組件
2. **上傳程序**: 使用 PlatformIO 或 Arduino IDE 上傳程序
3. **打開串口監視器**: 設置波特率為 115200
4. **發送命令**: 通過串口發送控制命令

### 命令示例

```bash
# 移動到絕對位置 (Pan=135°, Tilt=90°)
<MOVE:135,90>

# 相對移動 (Pan+20°, Tilt-10°)
<MOVER:20,-10>

# 獲取當前位置
<POS>

# 設置移動速度為 80
<SPEED:80>

# 回到初始位置 (Pan:135°, Tilt:90°)
<HOME>

# 停止移動
<STOP>

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
| CAL | `<CAL>` | 執行校準 | `<CAL>` || READ | `<READ>` | 讀取實際位置 | `<READ>` |
| **MODE** | `<MODE:0/1>` | **設置模式** | `<MODE:1>` |
| **GETMODE** | `<GETMODE>` | **查詢模式** | `<GETMODE>` |
| **TEMP** | `<TEMP>` | **讀取溫度** | `<TEMP>` |
| **VOLT** | `<VOLT>` | **讀取電壓** | `<VOLT>` |
| **STATUS** | `<STATUS>` | **完整狀態** | `<STATUS>` |

### 工作模式

#### 手動模式 (MODE:0)
- 默認模式，完全由上位機控制
- 支持所有移動命令
- 適合：目標追蹤、精確定位

#### 自動掃描模式 (MODE:1)
- **垂直固定**: 20°
- **水平掃描**: 75° - 195° (120° 範圍)
- **速度**: 慢速平滑掃描
- 自動來回掃描，無需上位機控制
- 適合：區域監控、自動巡邏
## 📁 專案結構

```
arduino-pt2d/
├── src/
│   ├── main.cpp              # 主程序
│   ├── ServoController.cpp   # 伺服馬達控制實現
│   └── SerialProtocol.cpp    # 串口協議實現
├── include/
│   ├── config.h              # 配置文件
│   ├── ServoController.h     # 伺服馬達控制器頭文件
│   └── SerialProtocol.h      # 串口協議頭文件
├── lib/                      # 自定義庫目錄
├── docs/                     # 文檔目錄
│   ├── hardware.md           # 硬體連接說明
│   ├── protocol.md           # 通訊協議詳細說明
│   └── python_example.md     # Python 控制示例
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

1. 在 `ServoController` 類中添加新方法
2. 在 `SerialProtocol` 中添加新命令類型
3. 在 `main.cpp` 的 `loop()` 中處理新命令
4. 更新文檔

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

## 📄 授權

本專案採用 MIT 授權 - 詳見 [LICENSE](LICENSE) 文件

## 👥 貢獻

歡迎提交 Issue 和 Pull Request！

## 📧 聯繫方式

如有問題或建議，請通過以下方式聯繫：

- Email: your.email@example.com
- GitHub Issues: [提交問題](https://github.com/yourusername/arduino-pt2d/issues)

## 🙏 致謝

感謝所有為本專案做出貢獻的開發者！

---

**Built with ❤️ for Arduino Community**
