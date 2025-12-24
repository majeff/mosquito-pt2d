# Serial 通訊格式檢查結果

## 📋 檢查日期
2025-12-24

## ✅ 已完成的改進

### 1. 固件端（main.cpp）
- [x] 啟動訊息統一為 JSON 格式
- [x] SETID 響應改為結構化 JSON：`{"status":"ok","pan_id":1,"tilt_id":2}`
- [x] 所有命令響應保持 JSON 格式
- [x] 位置和狀態查詢返回結構化 JSON

### 2. Python 端（pt2d_controller.py）
- [x] 加入 `_clear_startup_messages()` 方法處理啟動訊息
- [x] 自動偵測並記錄舵機 ID
- [x] 改進錯誤處理

### 3. 文檔
- [x] 創建 `SERIAL_PROTOCOL_MAPPING.md` - 完整通訊格式對照表
- [x] 創建 `test_serial_protocol.py` - 自動化測試腳本

## 📊 通訊格式總覽

### Arduino → Python 的所有輸出格式

| 類型 | 格式 | 範例 |
|------|------|------|
| 啟動訊息 | `{"status":"info","message":"..."}` | `{"status":"info","message":"PT2D Bridge Firmware v2.2.0"}` |
| 舵機ID | `{"status":"info","message":"...","pan_id":N,"tilt_id":M}` | `{"status":"info","message":"舵機ID已設置","pan_id":1,"tilt_id":2}` |
| 成功響應 | `{"status":"ok","message":"..."}` | `{"status":"ok","message":"OK"}` |
| 錯誤響應 | `{"status":"error","message":"..."}` | `{"status":"error","message":"Invalid parameter"}` |
| 位置數據 | `{"pan":N,"tilt":M}` | `{"pan":135,"tilt":90}` |
| 單軸角度 | `{"id":N,"angle":M}` | `{"id":1,"angle":135}` |
| 單軸狀態 | `{"id":N,"voltage":V,"temp":T}` | `{"id":1,"voltage":750,"temp":32}` |
| 完整狀態 | `{"pan":N,"tilt":M,"pan_temp":T1,...}` | 見下方 |
| SETID響應 | `{"status":"ok","pan_id":N,"tilt_id":M}` | `{"status":"ok","pan_id":1,"tilt_id":2}` |
| 總線透傳 | `{'raw': <字串>}` | `{'raw': '#001PRAD135!'}` |

### 完整狀態格式（STATUS/TEMP/VOLT）
```json
{
  "pan": 135,
  "tilt": 90,
  "pan_temp": 32,
  "tilt_temp": 35,
  "pan_voltage": 750,
  "tilt_voltage": 755
}
```

## 🔍 命令與響應對照

### 基本控制命令

| 命令 | 固件響應 | Python 方法 |
|------|---------|------------|
| `<LED:ON>` | `{"status":"ok","message":"LED"}` | `send_command('LED:ON')` |
| `<BEEP>` | `{"status":"ok","message":"BEEP"}` | `send_command('BEEP')` 或 `beep()` |
| `<SPEED:50>` | `{"status":"ok","message":"OK"}` | `set_speed(50)` |
| `<SETID:1,2>` | `{"status":"ok","pan_id":1,"tilt_id":2}` | `send_command('SETID:1,2')` |

### 移動命令

| 命令 | 固件響應 | Python 方法 |
|------|---------|------------|
| `<MOVE:135,90>` | `{"status":"ok","message":"OK"}` | `move_to(135, 90)` |
| `<MOVER:10,5>` | `{"status":"ok","message":"OK"}` | `move_by(10, 5)` |
| `<HOME>` | `{"status":"ok","message":"OK"}` | `home()` |
| `<STOP>` | `{"status":"ok","message":"OK"}` | `stop()` |
| `<CAL>` | `{"status":"ok","message":"OK"}` | `calibrate()` |

### 查詢命令

| 命令 | 固件響應 | Python 方法 | 響應欄位 |
|------|---------|------------|---------|
| `<POS>` | `{"pan":135,"tilt":90}` | `get_position()` | 返回 `(pan, tilt)` |
| `<READ>` | `{"pan":135,"tilt":90}` | `read_position()` | 返回 `(pan, tilt)` |
| `<READANGLE:1>` | `{"id":1,"angle":135}` | `read_angle(1)` | 返回字典 |
| `<READVOLTEMP:1>` | `{"id":1,"voltage":750,"temp":32}` | `read_voltage_temp(1)` | 返回字典 |
| `<STATUS>` | 完整狀態 JSON | `read_status()` | 返回字典 |
| `<TEMP>` | 完整狀態 JSON | `read_temperature()` | 返回字典 |
| `<VOLT>` | 完整狀態 JSON | `read_voltage()` | 返回字典 |

### 總線透傳

| 命令 | 固件行為 | Python 方法 |
|------|---------|------------|
| `#001P1500T1000!` | 轉發到總線，透傳回覆 | `send_bus_command('#001P1500T1000!')` |
| `<RAW:#001PRAD!>` | 提取並轉發到總線 | `send_command('RAW:#001PRAD!')` |

## ⚠️ 注意事項

### 1. TEMP/VOLT 命令行為
- **現狀：** 返回完整 STATUS 格式（包含所有 6 個欄位）
- **原因：** 固件復用 `AGG_STATUS_BOTH` 流程
- **影響：** Python 方法仍可正常使用，只是返回的數據比預期多
- **建議：** 保持現狀，在文檔中說明即可

### 2. 啟動訊息處理
- **重要：** 連接後會收到 4-7 行啟動訊息
- **處理：** Python 端已加入 `_clear_startup_messages()` 方法
- **建議：** 使用更新後的 `pt2d_controller.py` 或 `pt2d_controller_improved.py`

### 3. JSON 解析失敗處理
- **現象：** 如果收到非 JSON 格式，會返回 `{'raw': <字串>, 'error': 'Failed to parse JSON'}`
- **原因：** 總線透傳或意外訊息
- **處理：** Python 已實作容錯機制

## 🧪 測試方法

### 自動化測試
```bash
cd python
python test_serial_protocol.py COM3         # Windows
python test_serial_protocol.py /dev/ttyUSB0 # Linux
```

### 手動測試
```python
from pt2d_controller import PT2DController

with PT2DController('COM3') as pt:
    # 測試基本命令
    print(pt.send_command('BEEP'))

    # 測試移動
    print(pt.move_to(135, 90))

    # 測試查詢
    pan, tilt = pt.get_position()
    print(f"位置: {pan}, {tilt}")

    # 測試狀態
    status = pt.read_status()
    print(status)
```

## ✅ 驗證檢查清單

- [x] 所有 Serial.print 輸出為有效 JSON（除了總線透傳）
- [x] Python 能正確解析所有響應
- [x] 啟動訊息不會干擾命令響應
- [x] SETID 使用結構化 JSON 格式
- [x] 位置和狀態查詢返回完整數據
- [x] 錯誤響應統一格式
- [ ] **待測試：** 實際硬件測試所有命令

## 📝 後續改進建議

### 可選改進（低優先級）

1. **分離 TEMP/VOLT 命令邏輯**
   - 讓 TEMP 只返回 `{"pan_temp":N,"tilt_temp":M}`
   - 讓 VOLT 只返回 `{"pan_voltage":N,"tilt_voltage":M}`
   - 需要修改固件邏輯，增加新的聚合類型

2. **增加命令版本號**
   - 在啟動訊息中加入協議版本
   - 例如：`{"status":"info","version":"2.2.0","protocol":"1.0"}`

3. **增加 CRC 校驗**
   - 對關鍵命令加入 CRC 校驗
   - 提高通訊可靠性

4. **增加批量命令**
   - 支援一次發送多個命令
   - 減少通訊往返次數

## 📚 相關文件

- [SERIAL_PROTOCOL_MAPPING.md](../SERIAL_PROTOCOL_MAPPING.md) - 詳細通訊格式對照
- [src/main.cpp](../src/main.cpp) - 固件代碼
- [python/pt2d_controller.py](../python/pt2d_controller.py) - Python 控制器（已更新）
- [python/pt2d_controller_improved.py](../python/pt2d_controller_improved.py) - 增強版控制器
- [python/test_serial_protocol.py](../python/test_serial_protocol.py) - 自動化測試腳本

## 🎯 總結

### 優點
✅ 所有通訊統一使用 JSON 格式
✅ 結構清晰，易於解析
✅ 錯誤處理完善
✅ 支援總線透傳
✅ Python 端健壯性強

### 已修復的問題
✅ 啟動訊息格式化
✅ SETID 響應結構化
✅ Python 端處理啟動訊息

### 狀態
🟢 **所有 Serial 通訊格式已檢查完畢，並完成必要修復**
