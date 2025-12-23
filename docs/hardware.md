# 硬體連接詳細說明

## 🔌 組件清單

### 必需組件

                                            Orange Pi 5
    - **Arduino Nano**（本專案使用）

        USB 攝像頭 ×2 ───┤ USB 3.0          │
        Arduino Nano ────┤ USB 3.0          │
   - 型號: LewanSoul LX-16A, Feetech SCS15, HTS等
                                        │ GPIO Pin 5 ──────┼──→ 雷射控制（繼電器）
     - 通訊方式: 串口 (UART)
     - 工作電壓: 6V-8.4V
     - 波特率: 9600 或 115200
     - 轉動角度: 0-240°
                                                                            │
                                                        ┌─────────┴──────────┐
                                                        │                    │
                                            Pan 舵機 (ID=1)      Tilt 舵機 (ID=2)
    - 總線舵機 VCC: 應為 6V-8.4V（推薦 7.4V）
    - 負載時電壓降: 不應低於 6V
    - Arduino 5V 引腳: 約 5V (USB 供電)

    | USB (Serial) | 與 Orange Pi 通訊 | Orange Pi USB | 透過 /dev/ttyUSB0 |
### 步驟 1: 總線舵機接線

    ### 總線舵機規格

    | 型號 | 扭矩 | 速度 | 工作電壓 | 通訊方式 |
| 線材顏色 | 功能 | 連接到 |
    | LX-16A | 16kg·cm | 0.1s/60° | 6-8.4V | 串口 (UART) |
    | SCS15 | 15kg·cm | 0.1s/60° | 6-8.4V | 串口 (UART) |
    | HTS-35H | 35kg·cm | 0.16s/60° | 6-8.4V | 串口 (UART) |

**總線舵機串聯連接示意**:

    | 型號 | 數位引腳 | 串口數量 | 記憶體 | 本專案使用 |
                     總線數據線（黃/綠）
    | Nano | 14 個 | 1 | 32KB | ✓ (本專案) |
    | Uno | 14 個 | 1 | 32KB | 可用 |
    | Mega 2560 | 54 個 | 4 | 256KB | 過度規格 |
              │     │     │

電源連接：
外接 7.4V ─┬── 所有舵機 VCC (紅線)
           └── Arduino VIN (可選)
```

#### 方案 B: 使用 LM7805 穩壓模組

```
7-12V 電源
    ↓
LM7805 穩壓模組
    ├── 5V 輸出 → 伺服馬達 VCC
    └── GND → 伺服馬達 GND + Arduino GND
```

#### 方案 C: 使用 Buck 降壓模組

```
12V 電源
    ↓
Buck 降壓模組 (調整到 5V)
    ├── 5V 輸出 → 伺服馬達 VCC
    └── GND → 伺服馬達 GND + Arduino GND
```

### 步驟 3: 串口連接

#### 與電腦連接（USB）

直接使用 USB 線連接 Arduino 和電腦，無需額外接線。

#### 與其他微控制器連接（UART）

```
Arduino TX (Pin 1) ──→ 對方 RX
Arduino RX (Pin 0) ←── 對方 TX
Arduino GND ───────── 對方 GND
```

⚠️ **注意**: 上傳程序時需斷開 TX/RX 連接，否則可能上傳失敗。

### 步驟 4: 添加濾波電容（可選但建議）

在電源端並聯電容以穩定電壓：

```
伺服馬達 VCC ──┬── 電容正極
               │
伺服馬達 GND ──┴── 電容負極

建議使用: 470μF 或 1000μF 電解電容
```

---

## 🖼️ 完整連接圖

### 基本連接圖（Orange Pi 5 ↔ Arduino Nano UART）

```
                   Orange Pi 5（主控制器）
                ┌────────────────────────┐
                │  USB 3.0 ──> 左/右攝像頭 │
                │  GPIO Pin 5 ──> 繼電器IN │
                │  5V/GND ─────> 繼電器VCC/GND │
                │  GPIO UART TXD ───────┐ │
                │  GPIO UART RXD <───┐  │ │
                └─────────────────┬──┴──┘ │
                                  │       │
                          共地 ───┘       │
                                          │（請使用電位轉換: Arduino TX 5V → 3.3V）

                     Arduino Nano（雲台控制）
                ┌────────────────────────┐
                │ D0 (RX0)  <─── TXD     │  ← 來自 Orange Pi
                │ D1 (TX0)  ───> RXD     │  → 接至 Orange Pi（經電位轉換）
                │ GND ───────── 共地     │
                │ D10 (TX) ─┐            │
                │ D11 (RX) ─┤ 總線舵機   │  ←→ LX-16A/SCS15 總線（串聯）
                └───────────┴────────────┘

                     舵機電源（獨立 7.4V）
                ┌────────────────────────┐
                │ VCC ─────────→ 舵機 VCC │
                │ GND ─────────→ 舵機 GND │
                │ (與 Orange Pi/Arduino 共地) │
                └────────────────────────┘
```

> 提醒：不要將 Arduino TX(5V) 直接接 Orange Pi RX(3.3V)。請使用雙向電平轉換器或分壓（1k:2k）。

---

## ⚠️ 注意事項和常見問題

### 1. 電源問題

**問題**: 總線舵機抖動、Arduino 重啟、USB 斷開

**原因**:
- 總線舵機工作電流較大（每個 200-800mA）
- 必須使用外接電源供電

**解決方案**:
1. 使用外接 6V-8.4V / 2A 以上電源（推薦 7.4V 鋰電池）
2. 添加大容量電解電容（470μF-1000μF）
3. 將 Arduino 和舵機分開供電

### 2. 共地問題

**問題**: 總線舵機不工作或工作不正常

**原因**: Orange Pi 5、Arduino 和舵機電源沒有共地

**解決方案**:
- 確保 Orange Pi GND、Arduino GND 和舵機電源 GND 連接在一起
- 所有地線必須連接到同一個公共地點

### 3. 信號線干擾

**問題**: 伺服馬達抖動、位置不準確

**解決方案**:
- 信號線盡量短
- 遠離電源線
- 使用雙絞線或屏蔽線
- 添加 1kΩ 電阻串聯在信號線上

### 4. 上傳失敗

**問題**: Arduino IDE 或 PlatformIO 上傳程序失敗

**原因**: USB 串口被占用

**解決方案**:
- 關閉 Python 追蹤程式
- 上傳完成後重新啟動追蹤程式

### 5. 過熱問題

**問題**: 總線舵機或穩壓模組發熱

**解決方案**:
- 檢查電源電壓是否過高（不要超過 8.4V）
- 添加散熱片
- 避免舵機長時間堵轉
- 使用更大功率的穩壓模組

---

## 🧪 測試步驟

### 1. 基本測試
1. 在 Orange Pi 5 上運行 Python 測試程式
2. 觀察終端輸出
3. 雲台應移動到初始位置（Pan: 90°, Tilt: 90°）
1. 打開串口監視器（115200 波特率）
2. 觀察啟動信息
3. 伺服馬達應移動到初始位置（90°, 90°）
使用 Python 控制器測試：

```python
from pt2d_controller import PT2DController

controller = PT2DController('/dev/ttyUSB0')

### 2. 功能測試
controller.move_to(90, 90)    # 回到中心位置
controller.move_to(0, 0)      # 移動到最小角度
controller.move_to(180, 180)  # 移動到最大角度
<MOVE:90,90>    # 應該回到中心位置
<MOVE:0,0>      # 移動到最小角度
controller.move_by(10, 0)     # Pan 軸增加 10°
controller.move_by(-10, 0)    # Pan 軸減少 10°
controller.move_by(0, 10)     # Tilt 軸增加 10°
<MOVER:10,0>    # Pan 軸增加 10°
<MOVER:-10,0>   # Pan 軸減少 10°
controller.set_speed(10)      # 設置慢速
controller.move_to(180, 90)   # 觀察緩慢移動
controller.set_speed(100)     # 設置快速

controller.close()
```
<SPEED:10>      # 設置慢速
或使用快速測試腳本：

```bash
cd python
python3 quick_start.py
```
<MOVE:180,90>   # 觀察緩慢移動
<SPEED:100>     # 設置快速
<MOVE:0,90>     # 觀察快速移動

# 4. 測試其他功能
<POS>           # 獲取當前位置
<HOME>          # 回到初始位置
<CAL>           # 執行校準
```

### 3. 電源測試

使用萬用表測量：
- 伺服馬達 VCC: 應為 4.8V-5.2V
- 負載時電壓降: 不應低於 4.5V
- Arduino 5V 引腳: 約 5V

---

## 📊 硬體規格對照表

### 伺服馬達對照

| 型號 | 扭矩 | 速度 | 電流 | 適用場景 |
|------|------|------|------|---------|
| SG90 | 1.8kg·cm | 0.1s/60° | 100-800mA | 小型輕負載 |
| MG90S | 2.2kg·cm | 0.1s/60° | 100-900mA | 小型金屬齒輪 |
| MG995 | 10kg·cm | 0.2s/60° | 500-2000mA | 中型負載 |
| MG996R | 11kg·cm | 0.19s/60° | 500-2600mA | 重負載 |

### Arduino 開發板對照

| 型號 | PWM 引腳 | 串口數量 | 記憶體 | 適用性 |
|------|---------|---------|--------|--------|
| Uno | 6 個 | 1 | 32KB | 基本應用 ✓ |
| Nano | 6 個 | 1 | 32KB | 基本應用 ✓ |
| Mega 2560 | 15 個 | 4 | 256KB | 進階應用 ✓✓ |
| Due | 12 個 | 4 | 512KB | 高性能 ✓✓✓ |

---

## 🔗 相關資源

- [伺服馬達工作原理](https://www.arduino.cc/en/Tutorial/Knob)
- [PWM 信號說明](https://docs.arduino.cc/learn/microcontrollers/analog-output)
- [Arduino 電源管理](https://www.arduino.cc/en/Tutorial/Foundations/Power)

---

**更新日期**: 2025-12-23
**版本**: 1.0.0
