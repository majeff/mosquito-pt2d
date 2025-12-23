# 串口通訊協議說明

## 📡 協議概述

Arduino 2D 雲台控制系統使用 UART 串口進行通訊，採用簡單的文本協議，方便調試和擴展。

### 基本參數

| 參數 | 值 | 說明 |
|-----|-----|-----|
| 波特率 | 115200 | 標準波特率 |
| 數據位 | 8 | 8 位數據 |
| 停止位 | 1 | 1 位停止位 |
| 校驗位 | None | 無校驗 |
| 流控制 | None | 無流控制 |

---

## 📤 命令格式

### 通用格式

```
<COMMAND:param1,param2,...>\n
```

- **起始符**: `<`
- **命令**: 大寫英文字母（不區分大小寫）
- **分隔符**: `:` 分隔命令和參數
- **參數分隔**: `,` 分隔多個參數
- **結束符**: `>` 或 `\n`（換行符）

### 格式規則

1. 命令不區分大小寫（`MOVE` 等同於 `move`）
2. 參數必須是整數
3. 空格會被忽略（建議不使用空格）
4. 允許使用負數（相對移動時）
5. 結束符可以是 `>` 或換行符 `\n`

---

## 📋 命令列表

### 1. MOVE / MOVETO - 絕對位置移動

**功能**: 移動到指定的絕對位置

**格式**:
```
<MOVE:pan,tilt>
<MOVETO:pan,tilt>
```

**參數**:
- `pan`: Pan 軸目標角度（0-270）
- `tilt`: Tilt 軸目標角度（0-180）

**示例**:
```bash
<MOVE:135,90>   # 移動到中心位置
<MOVE:0,45>     # Pan=0°, Tilt=45°
<MOVE:270,180>  # 移動到最大角度
```

**響應**:
```json
{"status":"ok","message":"OK"}
```

---

### 2. MOVER / MOVEBY - 相對位置移動

**功能**: 相對於當前位置移動指定角度

**格式**:
```
<MOVER:pan_delta,tilt_delta>
<MOVEBY:pan_delta,tilt_delta>
```

**參數**:
- `pan_delta`: Pan 軸相對移動角度（-270 到 +270）
- `tilt_delta`: Tilt 軸相對移動角度（-180 到 +180）

**示例**:
```bash
<MOVER:10,0>    # Pan 軸增加 10°
<MOVER:-5,0>    # Pan 軸減少 5°
<MOVER:0,15>    # Tilt 軸增加 15°
<MOVER:10,-10>  # Pan+10°, Tilt-10°
```

**響應**:
```json
{"status":"ok","message":"OK"}
```

**注意**:
- 相對移動會自動限制在角度範圍內（Pan: 0-270°, Tilt: 0-180°）
- 超出範圍的移動會被截斷到邊界值

---

### 3. POS / GETPOS - 獲取當前位置

**功能**: 查詢當前 Pan 和 Tilt 角度

**格式**:
```
<POS>
<GETPOS>
```

**參數**: 無

**示例**:
```bash
<POS>
```

**響應**:
```json
{"pan":135,"tilt":90}
```

---

### 4. SPEED / SETSPEED - 設置移動速度

**功能**: 設置伺服馬達移動速度

**格式**:
```
<SPEED:value>
<SETSPEED:value>
```

**參數**:
- `value`: 速度值（1-100）
  - 1 = 最慢
  - 100 = 最快

**示例**:
```bash
<SPEED:50>   # 設置為中等速度
<SPEED:10>   # 設置為慢速
<SPEED:100>  # 設置為最快速度
```

**響應**:
```json
{"status":"ok","message":"OK"}
```

**速度效果**:
| 速度值 | 移動時間 | 適用場景 |
|-------|---------|---------|
| 1-20 | 5000ms | 慢速精確定位 |
| 50 | 1000ms | 正常速度 |
| 100 | 100ms | 快速移動 |

---

### 5. HOME - 回到初始位置

**功能**: 移動到預設的初始位置（Pan: 135°, Tilt: 90°）

**格式**:
```
<HOME>
```

**參數**: 無

**示例**:
```bash
<HOME>
```

**響應**:
```json
{"status":"ok","message":"OK"}
```

**注意**: 初始位置可在 `config.h` 中修改：
```cpp
#define PAN_INIT_ANGLE   135  // Pan 水平中心 (270°/2)
#define TILT_INIT_ANGLE  90   // Tilt 垂直中心 (180°/2)
```

---

### 6. STOP - 停止移動

**功能**: 立即停止當前移動，保持在當前位置

**格式**:
```
<STOP>
```

**參數**: 無

**示例**:
```bash
<STOP>
```

**響應**:
```json
{"status":"ok","message":"OK"}
```

---

### 7. CAL / CALIBRATE - 執行校準

**功能**: 執行完整的校準程序，測試所有運動範圍

**格式**:
```
<CAL>
<CALIBRATE>
```

**參數**: 無

**示例**:
```bash
<CAL>
```

**校準流程**:
1. 移動到中心位置（Pan:135°, Tilt:90°）- 停留 2 秒
2. Pan 軸移動到最小角度 (0°) - 停留 2 秒
3. Pan 軸移動到最大角度 (270°) - 停留 2 秒
4. Tilt 軸移動到最小角度 (0°) - 停留 2 秒
5. Tilt 軸移動到最大角度 (180°) - 停留 2 秒
6. 回到初始位置

**響應**:
```json
{"status":"ok","message":"OK"}
```

---

### 8. READ / READPOS - 讀取舵機實際位置

**功能**: 從總線舵機讀取實際位置（非緩存值）

**格式**:
```
<READ>
<READPOS>
```

**參數**: 無

**示例**:
```bash
<READ>
```

**響應**:
```json
{"pan":135,"tilt":90}
```

**注意**: 此命令會實際讀取舵機反饋位置，比 `<POS>` 更準確但稍慢

---

### 9. MODE / SETMODE - 設置工作模式

**功能**: 切換雲台工作模式

**格式**:
```
<MODE:value>
<SETMODE:value>
```

**參數**:
- `value`: 模式值
  - 0 = 手動模式（Manual Mode）
  - 1 = 自動掃描模式（Auto Scan Mode）

**示例**:
```bash
<MODE:0>     # 切換到手動模式
<MODE:1>     # 切換到自動掃描模式
```

**響應**:
```json
{"status":"ok","message":"Manual mode"}
{"status":"ok","message":"Auto scan mode"}
```

**模式說明**:

#### 手動模式 (MODE:0)
- 默認模式
- 完全由上位機控制
- 支持所有移動命令
- 位置不受限制（在最大範圍內）

#### 自動掃描模式 (MODE:1)
- 垂直角度固定在 20°
- 水平左右掃描 120° 範圍（75° - 195°）
- 慢速平滑掃描
- 自動模式下，移動命令會被拒絕
- 可隨時用 `<STOP>` 停止或 `<MODE:0>` 切回手動

**注意**:
- 切換到自動掃描模式時，系統會自動設置慢速並移動到掃描起始位置
- 在自動模式下，`MOVE`、`HOME`、`CAL` 等命令會返回錯誤

---

### 10. GETMODE - 獲取當前模式

**功能**: 查詢當前工作模式

**格式**:
```
<GETMODE>
```

**參數**: 無

**示例**:
```bash
<GETMODE>
```

**響應**:
```json
{"mode":0,"name":"MANUAL"}
{"mode":1,"name":"AUTO_SCAN"}
```

---

### 11. TEMP / TEMPERATURE - 讀取舵機溫度

**功能**: 讀取兩個舵機的當前溫度

**格式**:
```
<TEMP>
<TEMPERATURE>
```

**參數**: 無

**示例**:
```bash
<TEMP>
```

**響應**:
```json
{"pan_temp":35,"tilt_temp":38}
```

**說明**:
- 溫度單位：攝氏度 (°C)
- 正常工作溫度：20°C - 60°C
- 過熱警告：> 70°C
- 讀取失敗返回 -1

---

### 12. VOLT / VOLTAGE - 讀取舵機電壓

**功能**: 讀取兩個舵機的當前電壓

**格式**:
```
<VOLT>
<VOLTAGE>
```

**參數**: 無

**示例**:
```bash
<VOLT>
```

**響應**:
```json
{"pan_voltage":7400,"tilt_voltage":7380}
```

**說明**:
- 電壓單位：毫伏 (mV)
- 正常工作電壓：6000mV - 8400mV (6V - 8.4V)
- 7400mV = 7.4V
- 低電壓警告：< 6500mV
- 讀取失敗返回 -1

---

### 13. STATUS / INFO - 讀取完整狀態

**功能**: 一次性讀取位置、溫度、電壓所有信息

**格式**:
```
<STATUS>
<INFO>
```

**參數**: 無

**示例**:
```bash
<STATUS>
```

**響應**:
```json
{
  "pan":135,
  "tilt":90,
  "pan_temp":36,
  "tilt_temp":38,
  "pan_voltage":7400,
  "tilt_voltage":7380
}
```

**說明**:
- 一次讀取所有舵機狀態
- 適合監控和診斷
- 讀取時間較長（約 300-500ms）
- 建議不要頻繁調用（最多 1 秒 1 次）

---

## 📥 響應格式

### 成功響應

```json
{"status":"ok","message":"OK"}
```

### 錯誤響應

```json
{"status":"error","message":"Unknown command"}
{"status":"error","message":"Invalid parameter"}
```

### 位置響應

```json
{"pan":90,"tilt":45}
```

### 狀態響應

```json
{"status":"moving"}
{"status":"idle"}
```

---

## 🔄 通訊流程示例

### 示例 1: 基本移動

```
PC  → Arduino: <MOVE:135,90>\n
PC  ← Arduino: {"status":"ok","message":"OK"}
```

### 示例 2: 查詢狀態信息

```
# 查詢位置
PC  → Arduino: <POS>\n
PC  ← Arduino: {"pan":135,"tilt":90}

# 查詢溫度
PC  → Arduino: <TEMP>\n
PC  ← Arduino: {"pan_temp":36,"tilt_temp":38}

# 查詢電壓
PC  → Arduino: <VOLT>\n
PC  ← Arduino: {"pan_voltage":7400,"tilt_voltage":7380}

# 查詢完整狀態
PC  → Arduino: <STATUS>\n
PC  ← Arduino: {"pan":135,"tilt":90,"pan_temp":36,"tilt_temp":38,"pan_voltage":7400,"tilt_voltage":7380}
```

### 示例 3: 模式切換

```
# 切換到自動掃描模式
PC  → Arduino: <MODE:1>\n
PC  ← Arduino: {"status":"ok","message":"Auto scan mode"}

# 系統開始自動掃描（垂直20°，水平75°-195°）

# 查詢當前模式
PC  → Arduino: <GETMODE>\n
PC  ← Arduino: {"mode":1,"name":"AUTO_SCAN"}

# 嘗試手動移動（會被拒絕）
PC  → Arduino: <MOVE:100,100>\n
PC  ← Arduino: {"status":"error","message":"Not in manual mode"}

# 停止掃描
PC  → A5duino: <STOP>\n
PC  ← Arduino: {"status":"ok","message":"OK"}

# 切回手動模式
PC  → Arduino: <MODE:0>\n
PC  ← Arduino: {"status":"ok","message":"Manual mode"}

# 現在可以手動控制
PC  → Arduino: <MOVE:100,100>\n
PC  ← Arduino: {"status":"ok","message":"OK"}
```

### 示例 4: 連續命令

```
PC  → Arduino: <SPEED:50>\n
PC  ← Arduino: {"status":"ok","message":"OK"}

PC  → Arduino: <MOVE:270,90>\n
PC  ← Arduino: {"status":"ok","message":"OK"}

PC  → Arduino: <POS>\n
PC  ← Arduino: {"pan":200,"tilt":90}  # 移動中

等待移動完成...

PC  → Arduino: <POS>\n
PC  ← Arduino: {"pan":270,"tilt":90}  # 到達目標
```

### 示例 4: 錯誤處理

```
PC  → Arduino: <INVALID>\n
PC  ← Arduino: {"status":"error","message":"Unknown command"}

PC  → Arduino: <MOVE:999,999>\n
PC  ← Arduino: {"status":"ok","message":"OK"}  # 自動限制（Pan:270°, Tilt:180°）

PC  → Arduino: <POS>\n
PC  ← Arduino: {"pan":270,"tilt":180}  # 實際位置被限制到最大值
```

---

## 🐍 Python 通訊示例

### 基礎版本

```python
import serial
import time

# 打開串口
ser = serial.Serial('COM3', 115200, timeout=1)
time.sleep(2)  # 等待 Arduino 重啟

# 發送命令
def send_command(cmd):
    ser.write(f'{cmd}\n'.encode())
    time.sleep(0.1)
    response = ser.readline().decode().strip()
    print(f'CMD: {cmd} → {response}')
    return response

# 測試命令
send_command('<MOVE:135,90>')  # 移動到中心
send_command('<POS>')          # 查詢位置
send_command('<SPEED:50>')     # 設置速度
send_command('<HOME>')         # 回初始位置

ser.close()
```

### 進階類封裝

```python
import serial
import json
import time

class PT2DController:
    def __init__(self, port, baudrate=115200):
        self.ser = serial.Serial(port, baudrate, timeout=1)
        time.sleep(2)  # 等待初始化

    def send_command(self, cmd):
        """發送命令並返回響應"""
        self.ser.write(f'{cmd}\n'.encode())
        time.sleep(0.05)
        response = self.ser.readline().decode().strip()
        try:
            return json.loads(response)
        except:
            return {'raw': response}

    def move_to(self, pan, tilt):
        """移動到絕對位置"""
        return self.send_command(f'<MOVE:{pan},{tilt}>')

    def move_by(self, pan_delta, tilt_delta):
        """相對移動"""
        return self.send_command(f'<MOVER:{pan_delta},{tilt_delta}>')

| MODE | SETMODE | 0=手動, 1=自動掃描 | 設置模式 | JSON |
| GETMODE | - | - | 查詢模式 | JSON |
    def get_position(self):
        """獲取當前位置"""
        return self.send_command('<POS>')

    def set_speed(self, speed):
        """設置速度 (1-100)"""
        return self.send_command(f'<SPEED:{speed}>')

    def home(self):
        """回到初始位置"""
        return self.send_command('<HOME>')

    def stop(self):
        """停止移動"""
        return self.send_command('<STOP>')

    def calibrate(self):
        """執行校準"""
        return self.send_command('<CAL>')

    def close(self):
        """關閉串口"""
        self.ser.close()

# 使用示例
if __name__ == '__main__':
    pt = PT2DController('COM3')

    # 移動測試
    print(pt.move_to(135, 90))
    time.sleep(2)

    # 獲取位置
    pos = pt.get_position()
    print(f"Current position: Pan={pos['pan']}, Tilt={pos['tilt']}")

    # 設置速度並移動
    pt.set_speed(30)
    pt.move_to(270, 90)
    time.sleep(5)

    # 回到初始位置
    pt.home()

    pt.close()
```

---

## 🧪 測試工具

### 串口終端工具

推薦工具：
- **Arduino IDE Serial Monitor**
- **PuTTY** (Windows)
- **CoolTerm** (跨平台)
- **screen** (Linux/Mac)

### Linux/Mac 測試命令

```bash
# 使用 screen
screen /dev/ttyUSB0 115200

# 使用 echo 和 cat
echo "<MOVE:90,90>" > /dev/ttyUSB0
cat /dev/ttyUSB0

# 使用 Python 單行命令
python3 -c "import serial; s=serial.Serial('/dev/ttyUSB0', 115200); s.write(b'<POS>\n'); print(s.readline())"
```

### Windows 測試命令

```powershell
# 使用 PowerShell
$port = new-Object System.IO.Ports.SerialPort COM3,115200,None,8,one
$port.open()
$port.WriteLine("<MOVE:90,90>")
$port.ReadLine()
$port.Close()
```

---

## 📊 命令速查表

| 命令 | 簡寫 | 參數 | 功能 | 響應 |
|-----|------|------|------|------|
| MOVE | MOVETO | pan(0-270), tilt(0-180) | 絕對移動 | JSON |
| MOVER | MOVEBY | Δpan, Δtilt | 相對移動 | JSON |
| POS | GETPOS | - | 查詢位置 | JSON |
| SPEED | SETSPEED | value(1-100) | 設置速度 | JSON |
| HOME | - | - | 回初始位(135,90) | JSON |
| STOP | - | - | 停止 | JSON |
| CAL | CALIBRATE | - | 校準 | JSON |
| READ | READPOS | - | 讀取實際位置 | JSON |

---

## ⚠️ 注意事項

### 1. 命令緩衝

- 接收緩衝區大小為 64 字節
- 超長命令會被截斷
- 建議單條命令不超過 32 字節

### 2. 命令速率

- 建議命令間隔 > 50ms
- 連續發送過快可能導致丟失
- 移動命令執行時間視速度設置而定

### 3. 錯誤處理

- 解析失敗會返回錯誤響應
- 超範圍參數會自動限制
- 未知命令會被忽略

### 4. 串口占用

- 上傳程序時需斷開串口連接
- 同一時間只能有一個程序打開串口
- 使用完畢後記得關閉串口

---

## 🔧 協議擴展

### 添加新命令

1. 在 `SerialProtocol.h` 中添加命令類型：

```cpp
enum CommandType {
  // ... 現有命令
  CMD_NEW_COMMAND  // 新命令
};
```

2. 在 `SerialProtocol.cpp` 的 `parseCommand()` 中添加解析：

```cpp
else if (cmdType == "NEWCMD") {
  lastCommand.type = CMD_NEW_COMMAND;
  // 解析參數...
  return true;
}
```

3. 在 `main.cpp` 的 `loop()` 中處理命令：

```cpp
case CMD_NEW_COMMAND:
  // 執行新命令...
  serialProtocol.sendResponse(true, "OK");
  break;
```

---

## 📚 相關文檔

- [硬體連接說明](hardware.md)
- [Python 控制示例](python_example.md)
- [主程序說明](../README.md)

---

**更新日期**: 2025-12-23
**版本**: 1.0.0
