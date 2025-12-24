# Arduino IDE 使用說明

## 📥 Arduino IDE 安裝

### 下載與安裝

1. 前往 [Arduino 官網](https://www.arduino.cc/en/software) 下載最新版本
2. 安裝完成後打開 Arduino IDE

## 📂 專案結構說明

本專案使用 **PlatformIO**（推薦），也支援 Arduino IDE。

### 當前架構（橋接固件）

```
mosquito-pt2d/
├── src/
│   └── main.cpp              # 橋接固件主程序
├── include/
│   └── config.h              # 配置文件
├── platformio.ini            # PlatformIO 配置
└── python/                   # Python 控制程序
    ├── pt2d_controller.py    # Arduino 控制器
    └── mosquito_tracker.py   # AI 追蹤系統
```

**說明**:
- 固件採用橋接模式，將 PC 端 `<...>` 命令轉換為總線舵機 `#...!` 指令
- 不再使用獨立的控制器類，所有邏輯整合在 `main.cpp` 中
- Arduino IDE 用戶可直接打開 `src/main.cpp` 編譯上傳

---

## 🔧 使用 Arduino IDE

### 步驟 1: 準備文件

**方式 A: 直接使用 PlatformIO（推薦）**
1. 使用 VS Code + PlatformIO 擴展
2. 打開專案資料夾
3. 點擊「上傳」即可

**方式 B: 使用 Arduino IDE**
1. 打開 `src/main.cpp`
2. 將文件另存為 `.ino` 格式（例如 `pt2d_bridge.ino`）
3. 將 `include/config.h` 複製到同一資料夾
4. 修改 `#include "config.h"` 為 `#include "config.h"`（Arduino IDE 會自動處理）

### 步驟 2: 配置舵機參數

編輯 `config.h`：

```cpp
// 根據你的舵機型號修改波特率
#define SERVO_BAUDRATE      115200    // LX-16A 常用 115200
                                      // SCS 系列可能用 9600 或 1000000

// 修改舵機 ID（確保與實際設置一致）
#define PAN_SERVO_ID        1         // Pan 軸舵機 ID
#define TILT_SERVO_ID       2         // Tilt 軸舵機 ID

// Arduino Uno/Nano 用戶需要取消軟串口配置的註釋
```

### 步驟 3: 添加 SoftwareSerial（僅 Uno/Nano）

如果使用 Arduino Uno 或 Nano，需在主程式文件最上方確認已有：

```cpp
#include <SoftwareSerial.h>
SoftwareSerial BUS_SERIAL(SERVO_TX_PIN, SERVO_RX_PIN);
```

**注意**: `src/main.cpp` 已包含此配置，無需額外修改。

### 步驟 4: 編譯與上傳

1. 打開 `src/main.cpp`（或另存為 `.ino` 格式）
2. 選擇開發板：**工具 → 開發板 → Arduino Uno** (或 Nano/Mega)
3. 選擇端口：**工具 → 端口 → COM3** (根據實際情況)
4. 點擊「✓」驗證編譯
5. 點擊「→」上傳到開發板

### 步驟 5: 測試

1. 打開串口監視器：**工具 → 串口監視器**
2. 設置波特率為 **115200**
3. 選擇「換行」模式
4. 發送測試命令：
   ```
   <MOVE:135,90>
   <POS>
   <HOME>
   ```

---

## 🐛 常見問題

### Q1: 編譯錯誤 "BUS_SERIAL was not declared"

**解決方案**（Uno/Nano 用戶）:

確認 `src/main.cpp` 開頭包含：

```cpp
#if !defined(__AVR_ATmega2560__)
#include <SoftwareSerial.h>
SoftwareSerial BUS_SERIAL(SERVO_TX_PIN, SERVO_RX_PIN);
#else
#define BUS_SERIAL Serial1
#endif
```

### Q2: 上傳失敗 "avrdude: stk500_recv(): programmer is not responding"

**解決方案**:
1. 確認選擇正確的開發板和端口
2. 嘗試按住開發板上的 RESET 按鈕，點擊上傳，在進度條出現時釋放 RESET
3. 檢查 USB 線是否正常
4. 嘗試其他 USB 端口

### Q3: 舵機不動

**檢查清單**:
- [ ] 舵機電源是否連接（6V-8.4V）
- [ ] 所有 GND 是否共地
- [ ] 舵機 ID 是否正確（預設 1 和 2）
- [ ] 波特率是否匹配（115200 或 9600）
- [ ] 總線接線是否正確（TX→RX, RX→TX）

### Q4: 無法讀取舵機位置

**可能原因**:
- 舵機不支持位置反饋（檢查舵機型號）
- 波特率不匹配
- 舵機 ID 錯誤

---

## 📝 修改舵機 ID

如果你的舵機 ID 不是 1 和 2，需要修改：

### 方法 1: 使用調試工具

大多數總線舵機廠商提供 PC 軟件修改 ID：
- LewanSoul: LX-16A Bus Servo Terminal
- Feetech: FD software

### 方法 2: 使用 Arduino 代碼

創建一個臨時程序修改 ID：

```cpp
#include <SoftwareSerial.h>
SoftwareSerial servoSerial(11, 10);

void setup() {
  Serial.begin(115200);
  servoSerial.begin(115200);

  delay(1000);

  // 修改 ID: 原 ID=1 改為 ID=3
  changeServoID(1, 3);

  Serial.println("ID changed!");
}

void changeServoID(uint8_t oldID, uint8_t newID) {
  uint8_t buf[7];
  buf[0] = 0x55;
  buf[1] = 0x55;
  buf[2] = oldID;
  buf[3] = 4;
  buf[4] = 13;  // ID_WRITE 命令
  buf[5] = newID;
  buf[6] = ~(buf[2] + buf[3] + buf[4] + buf[5]);

  servoSerial.write(buf, 7);
  delay(100);
}

void loop() {}
```

---

## 📚 相關文檔

- [README.md](../README.md) - 專案說明
- [hardware.md](hardware.md) - 硬體連接
- [protocol.md](protocol.md) - 通訊協議
- [python_example.md](python_example.md) - Python 控制

---

**更新日期**: 2025-12-23
**版本**: 1.0.0
