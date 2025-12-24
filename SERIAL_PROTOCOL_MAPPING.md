# Serial 通訊格式對照表

## 固件（Arduino）→ Python 通訊格式檢查

### ✅ 已統一為 JSON 格式的訊息

#### 1. 啟動訊息（Startup Messages）

| 固件輸出 | Python 處理 | 狀態 |
|---------|------------|------|
| `{"status":"info","message":"PT2D Bridge Firmware v2.2.0"}` | `pt2d_controller_improved.py` 的 `_read_startup_messages()` 讀取 | ✅ 正常 |
| `{"status":"info","message":"PC <...> / BUS #...!"}` | 同上 | ✅ 正常 |
| `{"status":"info","message":"啟動舵機ID自動掃描"}` | 同上 | ✅ 正常 |
| `{"status":"info","message":"Pan舵機ID","id":1}` | 同上 | ✅ 正常 |
| `{"status":"info","message":"Tilt舵機ID","id":2}` | 同上 | ✅ 正常 |
| `{"status":"info","message":"舵機掃描完成"}` | 同上 | ✅ 正常 |
| `{"status":"info","message":"舵機ID已設置","pan_id":1,"tilt_id":2}` | 同上，解析並記錄 | ✅ 正常 |

**Python 處理邏輯：**
```python
def _read_startup_messages(self, max_lines: int = 20, timeout: float = 3.0):
    # 讀取啟動訊息，嘗試解析 JSON
    # 偵測 pan_id 和 tilt_id
```

---

#### 2. 命令響應（Command Responses）

##### 2.1 成功響應

| 命令 | 固件輸出 | Python 處理 | 狀態 |
|------|---------|------------|------|
| `<LED:ON>` | `{"status":"ok","message":"LED"}` | `send_command()` → `json.loads()` | ✅ 正常 |
| `<BEEP>` | `{"status":"ok","message":"BEEP"}` | 同上 | ✅ 正常 |
| `<SPEED:50>` | `{"status":"ok","message":"OK"}` | 同上 | ✅ 正常 |
| `<MOVE:135,90>` | `{"status":"ok","message":"OK"}` | 同上 | ✅ 正常 |
| `<STOP>` | `{"status":"ok","message":"OK"}` | 同上 | ✅ 正常 |
| `<HOME>` | `{"status":"ok","message":"OK"}` | 同上 | ✅ 正常 |
| `<CAL>` | `{"status":"ok","message":"OK"}` | 同上 | ✅ 正常 |

##### 2.2 錯誤響應

| 命令 | 固件輸出 | Python 處理 | 狀態 |
|------|---------|------------|------|
| `<SETID:invalid>` | `{"status":"error","message":"Invalid parameter"}` | `send_command()` → `json.loads()` | ✅ 正常 |
| `<UNKNOWN>` | `{"status":"error","message":"Unknown command"}` | 同上 | ✅ 正常 |

##### 2.3 SETID 命令特殊格式

| 命令 | 固件輸出 | Python 處理 | 狀態 |
|------|---------|------------|------|
| `<SETID:1,2>` | `{"status":"ok","message":"Pan ID=1, Tilt ID=2"}` | `send_command()` → `json.loads()` | ⚠️ **問題** |

**問題：** message 欄位包含非結構化文字，應改為結構化 JSON
**建議修改：**
```cpp
// 舊版：
Serial.print("{\"status\":\"ok\",\"message\":\"Pan ID=");
Serial.print(panServoId);
// ...

// 新版：
Serial.print("{\"status\":\"ok\",\"pan_id\":");
Serial.print(panServoId);
Serial.print(",\"tilt_id\":");
Serial.print(tiltServoId);
Serial.println("}");
```

---

#### 3. 位置與狀態查詢（Position/Status Queries）

##### 3.1 POS/GETPOS/READ/READPOS

| 命令 | 固件輸出 | Python 處理 | 狀態 |
|------|---------|------------|------|
| `<POS>` | `{"pan":135,"tilt":90}` | `get_position()` 解析 `pan` 和 `tilt` | ✅ 正常 |
| `<READ>` | 同上 | `read_position()` 同樣處理 | ✅ 正常 |

##### 3.2 READANGLE（單軸）

| 命令 | 固件輸出 | Python 處理 | 狀態 |
|------|---------|------------|------|
| `<READANGLE:1>` | `{"id":1,"angle":135}` | `read_angle(1)` 解析 JSON | ✅ 正常 |

##### 3.3 READVOLTEMP（單軸）

| 命令 | 固件輸出 | Python 處理 | 狀態 |
|------|---------|------------|------|
| `<READVOLTEMP:1>` | `{"id":1,"voltage":750,"temp":32}` | `read_voltage_temp(1)` 解析 JSON | ✅ 正常 |

##### 3.4 STATUS/INFO（雙軸完整狀態）

| 命令 | 固件輸出 | Python 處理 | 狀態 |
|------|---------|------------|------|
| `<STATUS>` | `{"pan":135,"tilt":90,"pan_temp":32,"tilt_temp":35,"pan_voltage":750,"tilt_voltage":755}` | `read_status()` 解析全部欄位 | ✅ 正常 |

##### 3.5 TEMP/TEMPERATURE（雙軸溫度）

| 命令 | 固件輸出 | Python 處理 | 狀態 |
|------|---------|------------|------|
| `<TEMP>` | 同 STATUS 格式 | `read_temperature()` | ⚠️ **問題** |

**問題：** 固件目前復用 STATUS 流程，會返回完整狀態，但 Python 只期望溫度
**建議：** 固件應該只返回溫度欄位，或 Python 需要適配

##### 3.6 VOLT/VOLTAGE（雙軸電壓）

| 命令 | 固件輸出 | Python 處理 | 狀態 |
|------|---------|------------|------|
| `<VOLT>` | 同 STATUS 格式 | `read_voltage()` | ⚠️ **問題** |

**問題：** 同 TEMP 命令

---

#### 4. 總線指令透傳（Bus Command Passthrough）

##### 4.1 直接透傳 #...!

| 命令 | 固件行為 | Python 處理 | 狀態 |
|------|---------|------------|------|
| `#001P1500T1000!` | 轉發到總線，透傳舵機回覆 | `send_bus_command()` 返回 `{'raw': response}` | ✅ 正常 |

##### 4.2 RAW 命令

| 命令 | 固件行為 | Python 處理 | 狀態 |
|------|---------|------------|------|
| `<RAW:#001P1500T1000!>` | 提取 params，轉發到總線 | Python 側不直接使用此格式 | ✅ 正常 |

---

## 問題彙總與修復建議

### ⚠️ 問題 1：SETID 回應格式不統一

**位置：** [main.cpp:220-224](main.cpp#L220-L224)

**現狀：**
```cpp
Serial.print("{\"status\":\"ok\",\"message\":\"Pan ID=");
Serial.print(panServoId);
Serial.print(", Tilt ID=");
Serial.print(tiltServoId);
Serial.println("\"}");
```

**輸出：** `{"status":"ok","message":"Pan ID=1, Tilt ID=2"}`

**問題：** message 包含動態數據，不利於解析

**建議修改：**
```cpp
Serial.print("{\"status\":\"ok\",\"pan_id\":");
Serial.print(panServoId);
Serial.print(",\"tilt_id\":");
Serial.print(tiltServoId);
Serial.println("}");
```

**修改後輸出：** `{"status":"ok","pan_id":1,"tilt_id":2}`

---

### ⚠️ 問題 2：TEMP/VOLT 命令邏輯不完整

**位置：** [main.cpp:385-410](main.cpp#L385-L410)

**現狀：** 復用 AGG_STATUS_BOTH 流程，返回完整狀態

**問題：**
1. 固件返回完整 STATUS 格式（6 個欄位）
2. Python 的 `read_temperature()` 和 `read_voltage()` 期望簡化格式
3. 但實際上 Python 只調用 `send_command()` 並直接返回字典，所以不影響功能

**建議：**
- **選項 A（推薦）：** 保持現狀，在 Python 文檔中說明這兩個命令返回完整 STATUS
- **選項 B：** 修改固件，為 TEMP 和 VOLT 單獨處理，只返回相關欄位

---

### ⚠️ 問題 3：原版 pt2d_controller.py 不處理啟動訊息

**位置：** `python/pt2d_controller.py`

**問題：**
- 連接時會收到多行啟動訊息
- `send_command()` 可能讀到啟動訊息而非命令響應
- 導致 JSON 解析失敗

**解決方案：** 使用 `pt2d_controller_improved.py`，包含：
1. `_read_startup_messages()` - 初始化時讀取啟動訊息
2. `_read_response()` - 跳過非 JSON 行，只返回有效響應
3. 重試機制

---

## Python 代碼適配建議

### 修復 pt2d_controller.py 的 __init__ 方法

```python
def __init__(self, port: str, baudrate: int = 115200, timeout: float = 1.0):
    # ... 現有代碼 ...

    try:
        self.ser = serial.Serial(port, baudrate, timeout=timeout)
        time.sleep(2)
        logger.info(f"已連接至 {port}，波特率 {baudrate}")

        # ✅ 新增：讀取並清空啟動訊息
        self._clear_startup_messages()

        self.is_connected = True
    # ...

def _clear_startup_messages(self, timeout: float = 3.0):
    """清空啟動時的訊息"""
    start_time = time.time()
    while (time.time() - start_time) < timeout:
        if self.ser.in_waiting > 0:
            line = self.ser.readline().decode('utf-8', errors='ignore').strip()
            if line:
                logger.debug(f"啟動訊息: {line}")
                # 如果收到舵機ID訊息，可以記錄下來
                try:
                    data = json.loads(line)
                    if 'pan_id' in data and 'tilt_id' in data:
                        logger.info(f"偵測到舵機 ID: Pan={data['pan_id']}, Tilt={data['tilt_id']}")
                except:
                    pass
        else:
            break
    self.ser.flushInput()
    self.ser.flushOutput()
```

---

## 完整格式總覽

### 所有 JSON 格式

```json
// 1. 啟動訊息
{"status":"info","message":"<文字訊息>"}
{"status":"info","message":"<訊息>","id":<數字>}
{"status":"info","message":"舵機ID已設置","pan_id":<數字>,"tilt_id":<數字>}

// 2. 成功響應
{"status":"ok","message":"OK"}
{"status":"ok","message":"<特定訊息>"}

// 3. 錯誤響應
{"status":"error","message":"<錯誤訊息>"}

// 4. 位置數據
{"pan":<角度>,"tilt":<角度>}

// 5. 單軸數據
{"id":<ID>,"angle":<角度>}
{"id":<ID>,"voltage":<電壓>,"temp":<溫度>}

// 6. 完整狀態
{"pan":<角度>,"tilt":<角度>,"pan_temp":<溫度>,"tilt_temp":<溫度>,"pan_voltage":<電壓>,"tilt_voltage":<電壓>}
```

### 非 JSON 格式（總線透傳）

```
// 總線原始回覆（通過 forwardBusResponse() 直接透傳）
<總線舵機的原始回覆>
```

---

## 測試檢查清單

- [x] 啟動訊息格式統一為 JSON
- [x] 所有命令響應為 JSON 格式
- [ ] **需修復：** SETID 回應格式
- [x] POS/STATUS 等查詢命令返回結構化 JSON
- [x] Python improved 版本處理啟動訊息
- [ ] **需改進：** Python 原版需加入啟動訊息處理
- [x] 總線透傳功能正常

---

## 建議執行步驟

1. ✅ **已完成：** 修改固件啟動訊息為 JSON 格式
2. ✅ **已完成：** 創建 Python improved 版本處理啟動訊息
3. ⏳ **待執行：** 修復 SETID 命令響應格式（見下方）
4. ⏳ **可選：** 更新原版 pt2d_controller.py 或統一使用 improved 版本
5. ⏳ **測試：** 實際硬件測試所有命令
