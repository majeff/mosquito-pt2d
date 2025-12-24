# 串口通訊協議說明

## 📡 協議概述

Arduino 2D 雲台控制系統使用 UART 串口進行通訊，採用簡單的文本協議，方便調試和擴展。

**固件版本**: v2.3.0
**更新日期**: 2025-12-25

### 新版本改進 (v2.3.0)

- ✅ **內存優化**: 使用固定大小的 `char[]` 緩衝區取代 `String` 類，消除 heap 碎片化風險
- ✅ **參數驗證**: 完整的輸入參數驗證（角度範圍、舵機 ID、整數解析）
- ✅ **函數模組化**: 將 350行的 `handlePcLine()` 分割為 13 個專用函數，提升可維護性
- ✅ **超時保護**: 聚合命令增加 2 秒超時機制，防止系統卡死
- ✅ **看門狗定時器**: 啟用 2 秒看門狗，系統異常時自動重啟
- ✅ **緩衝區保護**: 防止緩衝區溢出，命令過長會自動拒絕

### 基本參數

| 參數 | 值 | 說明 |
|-----|-----|-----|
| 波特率 | 115200 | 標準波特率 |
| 數據位 | 8 | 8 位數據 |
| 停止位 | 1 | 1 位停止位 |
| 校驗位 | None | 無校驗 |
| 流控制 | None | 無流控制 |

### 舵機 ID 動態配置

系統在啟動時會自動掃描舵機 ID（使用 `#001PID!` 和 `#002PID!` 查詢），並動態設置：
- **Pan 軸舵機 ID**：預設 1（可透過 `<SETID:...>` 修改）
- **Tilt 軸舵機 ID**：預設 2（可透過 `<SETID:...>` 修改）

若自動掃描失敗，系統將使用 `config.h` 中的預設值。

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

### 0. SETID - 設置舵機 ID

**功能**: 動態設置 Pan 和 Tilt 軸的舵機 ID

**格式**:
```
<SETID:pan_id,tilt_id>
```

**參數**:
- `pan_id`: Pan 軸舵機 ID（正整數）
- `tilt_id`: Tilt 軸舵機 ID（正整數）

**示例**:
```bash
<SETID:1,2>      # 設置 Pan=1, Tilt=2
<SETID:3,4>      # 設置 Pan=3, Tilt=4
```

**響應**:
```json
{"status":"ok","message":"Pan ID=1, Tilt ID=2"}
{"status":"error","message":"Invalid parameter"}
```

**說明**:
- 系統啟動時會自動掃描舵機 ID，通常無需手動設置
- 若自動掃描失敗，使用此命令重新配置
- 修改後立即生效（無需重啟）

---

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

### 4. READ / READPOS - 讀取舵機實際位置

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

### 5. SPEED / SETSPEED - 設置移動速度

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

### 6. HOME - 回到初始位置

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

### 7. STOP - 停止移動

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

### 8. CAL / CALIBRATE - 執行校準

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

### 9. TEMP / TEMPERATURE - 讀取舵機溫度

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

### 10. VOLT / VOLTAGE - 讀取舵機電壓

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

### 11. STATUS / INFO - 讀取完整狀態

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

---

## � 進階命令透傳

除了上述高級命令外，系統支援**直接透傳總線指令**，允許訪問舵機的所有功能。

### 兩種透傳方式

#### 方式 1: 直接發送總線指令

格式：`#...!` (直接發送到總線)

```bash
#000P1500T1000!      # Pan 舵機角度控制
#001PRAD!            # 讀取 1 號舵機角度
#002PRTV!            # 讀取 2 號舵機電壓和溫度
#000PDST!            # 停止舵機
#000PDPT!            # 暫停舵機
#000PDCT!            # 繼續舵機
#000PMOD!            # 讀取模式
#000PMOD3!           # 設置模式（180° 順時針）
```

**說明**：
- 第一個 `#` 開頭後為舵機 ID（3 位數字，如 000、001、002）
- 命令直接透傳到總線，Arduino 不進行解析
- 回應透傳回 PC，需自行解析

#### 方式 2: 使用 `<RAW:...>` 包裝

格式：`<RAW:#...!>`

```bash
<RAW:#001P1500T1000!>     # Pan 舵機角度控制
<RAW:#002PRAD!>           # 讀取 Tilt 舵機角度
<RAW:#000PRTV!>           # 讀取電壓和溫度
<RAW:#000PDST!>           # 停止
<RAW:#000PMOD3!>          # 設置為 180° 順時針模式
```

**優點**：統一 `<...>` 格式，便於配置和調試

### 舵機完整指令集參考

本系統使用 **ZL 總線舵機**（ZL-KPZ 控制板），支援以下指令：

#### 設備基本控制

| 指令 | 說明 | 示例 |
|------|------|------|
| `#000PID!` | 讀取舵機 ID | `#000PID!` → `0` |
| `#000PID001!` | 設置舵機 ID（需格外小心） | `#001PID002!` |
| `#000PVER!` | 讀取固件版本 | `#000PVER!` |
| `#000PBD1!` | 設置波特率（1:9600, 5:115200 等） | `#000PBD5!` |
| `#000PCLE!` | 恢復出廠設置（重置 ID） | `#000PCLE!` |

#### 舵機位置控制

| 指令 | 說明 | 示例 | 回應 |
|------|------|------|------|
| `#IDxPyyyyTtttt!` | 角度控制（y:0-1000, t:移動時間ms） | `#001P1500T1000!` | 無 |
| `#IDxPRAD!` | 讀取當前角度 | `#001PRAD!` | `500` |
| `#IDxPDST!` | 停止移動 | `#001PDST!` | 無 |
| `#IDxPDPT!` | 暫停（保持扭力） | `#001PDPT!` | 無 |
| `#IDxPDCT!` | 繼續移動 | `#001PDCT!` | 無 |

#### 舵機狀態讀取

| 指令 | 說明 | 示例 | 回應示例 |
|------|------|------|---------|
| `#IDxPRTV!` | 讀取電壓和溫度 | `#001PRTV!` | `7400,35` (7.4V, 35°C) |
| `#IDxPMOD!` | 讀取運動模式 | `#001PMOD!` | `3` |

#### 舵機模式設置

| 模式 | 說明 | 指令 |
|------|------|------|
| 1 | 270° 順時針 | `#000PMOD1!` |
| 2 | 270° 逆時針 | `#000PMOD2!` |
| 3 | 180° 順時針 | `#000PMOD3!` |
| 4 | 180° 逆時針 | `#000PMOD4!` |
| 5 | 360° 順時針（馬達） | `#000PMOD5!` |
| 6 | 360° 逆時針（馬達） | `#000PMOD6!` |

#### 高級設置

| 指令 | 說明 | 示例 |
|------|------|------|
| `#IDxPCSK!` | 設置偏差值（1500 中點校準） | `#001PCSK!` |
| `#IDxPCSK+050!` | 偏差調整 | `#001PCSK+050!` |
| `#IDxPCSK-050!` | 偏差調整 | `#001PCSK-050!` |
| `#IDxPSTB!` | 讀取保護值 | `#001PSTB!` |
| `#IDxPSTB=60!` | 設置保護值（默認 60，範圍 25-80） | `#001PSTB=60!` |
| `#IDxPPAAA IBBBx!` | 設置 KP/KI（PID 參數） | `#001PP100I050!` |
| `#IDxPULK!` | 釋力（斷電） | `#001PULK!` |
| `#IDxPULR!` | 恢復扭力 | `#001PULR!` |
| `#IDxPULM!` | 釋力（無阻力） | `#001PULM!` |
| `#IDxPLN!` | RGB 燈開啟 | `#001PLN!` |
| `#IDxPLF!` | RGB 燈關閉 | `#001PLF!` |

#### 初始值設置

| 指令 | 說明 | 示例 |
|------|------|------|
| `#IDxPCSD!` | 設置當前位置為開機值 | `#001PCSD!` |
| `#IDxPCSM!` | 開機後釋放扭力 | `#001PCSM!` |
| `#IDxPMIN!` | 設置最小角度 | `#001PMIN!` |
| `#IDxPMAX!` | 設置最大角度 | `#001PMAX!` |

### Python 透傳示例

```python
import serial
import time

ser = serial.Serial('COM3', 115200, timeout=1)
time.sleep(2)

# 方式 1: 直接透傳
ser.write(b'#001P1500T1000!\n')  # 移動 1 號舵機
time.sleep(1.1)  # 等待運動完成

# 方式 2: RAW 封裝
ser.write(b'<RAW:#001PRAD!>\n')  # 讀取 1 號舵機角度
response = ser.readline().decode().strip()
print(f"角度: {response}")

# 方式 3: 使用控制器類
from pt2d_controller import PT2DController

ctrl = PT2DController('COM3')
# 發送透傳指令
ctrl.send_command('RAW:#001PRAD!')

ser.close()
```

---

## �🔄 通訊流程示例

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

### 示例 3: 連續命令

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

參考 `python/pt2d_controller.py` 中的 `PT2DController` 類實現。

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
| SETID | - | pan_id, tilt_id | 設置舵機ID | JSON |
| MOVE | MOVETO | pan(0-270), tilt(0-180) | 絕對移動 | JSON |
| MOVER | MOVEBY | Δpan, Δtilt | 相對移動 | JSON |
| POS | GETPOS | - | 查詢位置 | JSON |
| READ | READPOS | - | 讀取實際位置 | JSON |
| SPEED | SETSPEED | value(1-100) | 設置速度 | JSON |
| HOME | - | - | 回初始位(135,90) | JSON |
| STOP | - | - | 停止 | JSON |
| CAL | CALIBRATE | - | 校準 | JSON |
| TEMP | TEMPERATURE | - | 讀取溫度 | JSON |
| VOLT | VOLTAGE | - | 讀取電壓 | JSON |
| STATUS | INFO | - | 讀取完整狀態 | JSON |

---

## 🔧 舵機 ID 配置指南

### 自動掃描機制

系統啟動時會自動掃描舵機：

```
啟動序列：
1. 初始化 LED / BEEP
2. 初始化 PC 串口 (115200 baud)
3. 初始化總線串口 (115200 baud)
4. 列印歡迎訊息
5. 等待 500ms（舵機啟動）
6. 發送 #001PID! 查詢 1 號舵機
7. 發送 #002PID! 查詢 2 號舵機
8. 發送 #003PID!, #004PID!, #005PID! 查詢其他舵機
9. 輸出掃描結果到 PC 串口
10. 系統準備好接收命令
```

### 故障排查

#### 問題 1：自動掃描失敗，舵機 ID 為 0

**症狀**：
```
[INFO] 啟動舵機ID自動掃描...
[INFO] 舵機掃描完成
[SERVO] Pan ID=0 Tilt ID=0
```

**原因**：
- 舵機總線未連接或接線不當
- 舵機未通電或已損壞
- 舵機波特率設置不正確（預設 115200）
- 舵機已被設置為其他 ID

**解決方案**：
1. 檢查舵機接線
   ```
   Arduino D10 (TX) → 舵機數據線
   Arduino D11 (RX) → 舵機數據線
   GND → 舵機 GND
   ```

2. 確認舵機波特率（使用下位機軟件或 ZL_KPZAR.ino 範例）

3. 手動設置 ID：
   ```
   <SETID:1,2>
   ```

4. 驗證舵機響應：
   ```
   <READANGLE:1>     # 讀取 1 號舵機角度
   <READVOLTEMP:2>   # 讀取 2 號舵機溫度
   ```

#### 問題 2：某個舵機無響應

**症狀**：
```
<MOVE:135,90>
{"status":"ok","message":"OK"}   # Pan 正常，Tilt 無反應
```

**原因**：
- Tilt 舵機 ID 不正確
- Tilt 舵機未通電或故障
- Tilt 舵機接線不良

**解決方案**：
1. 檢查單個舵機 ID：
   ```
   <READVOLTEMP:2>   # 檢查 Tilt (ID=2)
   ```
   若無回應，嘗試其他 ID：
   ```
   <READVOLTEMP:3>
   <READVOLTEMP:4>
   <READVOLTEMP:5>
   ```

2. 找到正確 ID 後，更新配置：
   ```
   <SETID:1,3>       # Pan=1, Tilt=3
   ```

#### 問題 3：舵機 ID 衝突（兩個舵機使用相同 ID）

**症狀**：
```
<MOVE:90,90>
<POS>
{"pan":90,"tilt":-1}   # Tilt 讀取失敗
```

**解決方案**：
1. 使用下位機軟件（ZL_KPZAR.ino）重新設置舵機 ID
2. 或 斷開其中一個舵機，單獨配置

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

1. 在 `src/main.cpp` 的 `handlePcLine()` 中添加解析：

```cpp
if (cmdType == "NEWCMD") {
  // 執行新命令...
  Serial.println("{\"status\":\"ok\",\"message\":\"OK\"}");
  return;
}
```

2. 在 `python/pt2d_controller.py` 中添加便利方法：

```cpp
def new_command(self, param1):
    """新命令說明"""
    return self.send_command(f'NEWCMD:{param1}')
```

---

## 📚 相關文檔

- [硬體連接說明](hardware.md)
- [Python 控制示例](python_example.md)
- [主程序說明](../README.md)
- [ZL 舵機基礎範例](pt2d_sample/basic/ZL_KPZAR.ino) - 總線舵機指令參考
- [舵機指令詳表](pt2d_sample/总线串行舵机指令表.pdf)
- [控制板簡介](pt2d_sample/控制板简介.pdf)

---

**更新日期**: 2025-12-24
**版本**: 2.2.0
**變更**: 實現舵機ID動態配置；新增 SETID 命令；啟動時自動掃描舵機ID；添加舵機ID配置故障排查指南
