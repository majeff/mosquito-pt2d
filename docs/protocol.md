# 串口通信協議說明

## 協議概述

Arduino 2D舵機控制系統使用 UART 串口通信，採用簡潔的文本協議，方便調試和擴展。

**版本**: v2.4.0
**更新日期**: 2025-12-28

### 主要特性（v2.4.0）

- **內存優化**: 使用固定大小的 `char[]` 緩衝區代替 `String` 類，消除 heap 碎片風險
- **參數驗證**: 完整的輸入參數驗證，角度範圍檢查，舵機ID整數解析
- **代碼模塊化**: 將350行的 `handlePcLine()` 分割為15個獨立函數，提高可維護性
- **超時保護**: 所有命令增加2秒超時限制，防止系統死鎖
- **看門狗定時器**: 採用2秒周期，系統異常時自動重啟
- **緩衝區保護**: 防止緩衝區溢出，命令長度限制為64字元
- **舵機自動檢測**: 啟動時自動掃描並設置舵機ID
- **GETINFO命令**: 新增查詢系統資訊命令，返回舵機ID和角度限制

### 物理參數

| 參數 | 值 | 說明 |
|------|-----|------|
| 波特率 | 115200 | 標準波特率 |
| 數據位 | 8 | 8位數據位 |
| 停止位 | 1 | 1位停止位 |
| 校驗位 | None | 無校驗位 |
| 流控制 | None | 無流控制 |

### 舵機ID自動設置

系統啟動時自動掃描並檢測舵機ID（掃描ID範圍1-5）：
- **Pan軸舵機ID**：自動檢測，範圍1-5
- **Tilt軸舵機ID**：自動檢測，範圍1-5

**檢測失敗行為**：
- 檢測失敗時（panServoId=0或tiltServoId=0），系統進入**錯誤狀態**
- 系統不啟動，所有舵機控制命令被拒絕
- Arduino持續蜂鳴警示（3聲/秒），每秒輸出錯誤訊息
- Python控制器檢測到錯誤後禁用控制

---

## 啟動訊息格式

### 成功初始化（自動檢測成功）

Arduino會發送啟動訊息到PC串口，包含舵機ID和角度限制：

```json
{"status":"ok","message":"舵機ID已設置","pan_id":1,"tilt_id":2,"pan_min":0,"pan_max":270,"tilt_min":15,"tilt_max":165}
{"status":"ok","message":"看門狗已啟用 (2秒)"}
```

**說明**:
- `pan_id`, `tilt_id`: 自動檢測的舵機ID
- `pan_min`, `pan_max`: Pan軸角度控制範圍（度）
- `tilt_min`, `tilt_max`: Tilt軸角度控制範圍（度）
- Python控制器會自動接收並使用這些限制值於移動命令

### 失敗初始化（自動檢測失敗）

```json
{"status":"error","message":"舵機ID設置失敗","pan_id":0,"tilt_id":0}
{"status":"error","message":"舵機控制已禁用，請檢查硬體連接"}
{"status":"error","message":"開始蜂鳴警示，請檢查舵機連接..."}
{"status":"error","message":"舵機ID未檢測到，請重啟Arduino..."}
```

**說明**：
- `pan_id=0` 或 `tilt_id=0` 表示檢測失敗
- 系統進入錯誤狀態，不啟動看門狗定時器
- 所有舵機控制命令都返回錯誤訊息
- Arduino持續蜂鳴，等待重啟

---

## 命令格式規範

### 命令語法

```
<COMMAND:param1,param2,...>\n
```

- **起始字符**: `<`
- **命令**: 大寫英文字母（命令不區分大小寫）
- **分隔符**: `:` 分隔命令和參數
- **參數分隔**: `,` 分隔多個參數
- **結束字符**: `>` 和 `\n`（換行符）

### 命令規則

1. 命令不區分大小寫（`MOVE` 等同於 `move`）
2. 參數必須是整數
3. 參數之間用逗號分隔，無空格
4. 每條命令末尾必須有 `\n` 換行符
5. 命令超時為2秒

---

## 完整命令列表

### 0a. GETINFO - 查詢系統資訊

**命令**:
```
<GETINFO>
```

**說明**: 查詢Arduino的舵機配置資訊

**返回成功**:
```json
{"status":"ok","pan_id":1,"tilt_id":2,"pan_min":0,"pan_max":270,"tilt_min":15,"tilt_max":165,"firmware_version":"2.4.0"}
```

**返回失敗**:
```json
{"status":"error","message":"舵機未初始化"}
```

**Python用法**:
```python
info = controller.get_info()
# 返回字典: {'pan_id': 1, 'tilt_id': 2, 'pan_min': 0, ...}
```

---

### 1. MOVE - 移動到指定角度

**命令**:
```
<MOVE:pan_angle,tilt_angle>
```

**參數**:
- `pan_angle`: Pan軸目標角度（0-270）
- `tilt_angle`: Tilt軸目標角度（15-165）

**說明**: 同時控制Pan和Tilt軸移動到指定角度

**返回成功**:
```json
{"status":"ok","message":"命令已接受"}
```

**返回失敗**:
```json
{"status":"error","message":"角度超出範圍"}
```

**Python用法**:
```python
controller.move_to(pan=90, tilt=90)  # 移動到Pan 90°，Tilt 90°
```

---

### 2. MOVER/MOVEBY - 相對移動

**命令**:
```
<MOVER:pan_delta,tilt_delta>
或
<MOVEBY:pan_delta,tilt_delta>
```

**參數**:
- `pan_delta`: Pan軸相對移動角度（-270 到 +270）
- `tilt_delta`: Tilt軸相對移動角度（-180 到 +180）

**說明**: 從當前位置相對移動指定角度

**返回成功**:
```json
{"status":"ok","message":"相對移動命令已接受"}
```

**返回失敗**:
```json
{"status":"error","message":"角度超出範圍"}
```

**Python用法**:
```python
controller.move_by(pan=20, tilt=-10)  # Pan向右移20°，Tilt向下移10°
```

---

### 3. LASER - 雷射控制

**命令**:
```
<LASER:state>
```

**參數**:
- `state`: 0 = 關閉，1 = 開啟

**說明**: 控制雷射標記模組

**返回成功**:
```json
{"status":"ok","message":"雷射已開啟"}
```

**Python用法**:
```python
controller.laser_on()   # 開啟雷射
controller.laser_off()  # 關閉雷射
```

---

### 4. LED - LED控制

**命令**:
```
<LED:state>
```

**參數**:
- `state`: 0 = 關閉，1 = 開啟

**說明**: 控制指示LED

**返回成功**:
```json
{"status":"ok","message":"LED已開啟"}
```

---

### 5. SPEED - 速度設置

**命令**:
```
<SPEED:value>
```

**參數**:
- `value`: 移動速度（1-100）

**說明**: 設置舵機運動速度

**返回成功**:
```json
{"status":"ok","message":"速度已設置為 80"}
```

**返回失敗**:
```json
{"status":"error","message":"速度範圍1-100"}
```

---

### 6. CONFIGSERVO - 舵機配置

**命令**:
```
<CONFIGSERVO:pan_id,tilt_id>
```

**參數**:
- `pan_id`: Pan軸舵機ID（1-5）
- `tilt_id`: Tilt軸舵機ID（1-5）

**說明**: 手動設置舵機ID（通常自動檢測，不需使用）

**返回成功**:
```json
{"status":"ok","message":"舵機已配置","pan_id":1,"tilt_id":2}
```

---

### 7. READANGLE - 讀取角度

**命令**:
```
<READANGLE:servo_id>
```

**參數**:
- `servo_id`: 舵機ID（1-5）

**說明**: 讀取指定舵機的當前角度

**返回成功**:
```json
{"status":"ok","servo_id":1,"angle":135}
```

---

### 8. READVOLTTEMP - 讀取電壓溫度

**命令**:
```
<READVOLTTEMP:servo_id>
```

**參數**:
- `servo_id`: 舵機ID（1-5）

**說明**: 讀取舵機的電壓和溫度

**返回成功**:
```json
{"status":"ok","servo_id":1,"voltage":7.2,"temperature":35}
```

---

### 9. POS - 查詢當前位置

**命令**:
```
<POS>
```

**說明**: 查詢Pan和Tilt軸的當前角度

**返回成功**:
```json
{"status":"ok","pan":135,"tilt":90}
```

**返回失敗**:
```json
{"status":"error","message":"舵機未初始化"}
```

**Python用法**:
```python
pan_angle, tilt_angle = controller.get_position()
```

---

### 10. BEEP - 蜂鳴控制

**命令**:
```
<BEEP>
```

**說明**: 控制蜂鳴器發出3聲短蜂鳴（100ms每聲）

**返回**:
```json
{"status":"ok","message":"蜂鳴已執行"}
```

**Python用法**:
```python
controller.beep()
```

---

### 11. HOME - 歸位

**命令**:
```
<HOME>
```

**說明**: 將兩個軸同時移動到中位（Pan 135°，Tilt 90°）

**返回成功**:
```json
{"status":"ok","message":"舵機已歸位"}
```

**Python用法**:
```python
controller.home()
```

---

### 12. STOP - 停止運動

**命令**:
```
<STOP>
```

**說明**: 立即停止舵機運動

**返回**:
```json
{"status":"ok","message":"舵機已停止"}
```

---

### 13. STATUS - 查詢系統狀態

**命令**:
```
<STATUS>
```

**說明**: 查詢舵機電壓和溫度

**返回成功**:
```json
{"status":"ok","pan_volt":7.2,"pan_temp":35,"tilt_volt":7.2,"tilt_temp":34}
```

---

### 14. HELP - 幫助信息

**命令**:
```
<HELP>
```

**說明**: 顯示所有支持的命令列表

**返回**:
```json
{"status":"ok","message":"支持的命令: GETINFO, MOVE, MOVER, POS, STATUS, BEEP, LASER, LED, SPEED, CONFIGSERVO, STOP, HOME, READANGLE, READVOLTTEMP, HELP"}
```

---

## 錯誤處理

### 錯誤類型

| 錯誤 | 原因 | 解決方案 |
|------|------|--------|
| 舵機未初始化 | 啟動時檢測失敗 | 檢查電源和連接，重啟Arduino |
| 角度超出範圍 | 角度值不在有效範圍 | 確認角度在Pan 0-270°，Tilt 15-165° |
| 命令格式錯誤 | 命令語法不正確 | 檢查命令格式，參數用逗號分隔 |
| 超時 | 命令執行超過2秒 | 檢查舵機電源和連接，可能需要重啟 |

---

## 完整的初始化和驗證工作流程

### 第1階段：Arduino舵機ID檢測
1. Arduino上電，延遲SERVO_STARTUP_DELAY（預設1000ms）讓舵機初始化
2. 自動掃描舵機ID：
   - 對每個舵機（ID1-5），發送`#xxxPID!`命令
   - 最多重試SERVO_DETECT_RETRIES（預設3）次，間隔SERVO_DETECT_RETRY_DELAY（預設500ms）
   - 如果收到回應，設置panServoId或tiltServoId
3. 檢查檢測結果：
   - ✅若panServoId和tiltServoId都有效：輸出成功訊息，進入第2階段
   - ❌若任何ID=0或相同：**持續蜂鳴警示（3聲/秒），每秒輸出錯誤訊息，等待重啟**

### 第2階段：上位機連接和初始化驗證
1. 上位機透過USB連接到Arduino
2. 解析Arduino啟動訊息（JSON格式）
3. 檢查servo_enabled狀態：
   - ✅若為true：繼續第3階段
   - ❌若為false：提示使用者重啟Arduino，並重試
4. 發送`<GETINFO>`命令查詢舵機資訊：
   - 取得pan_id、tilt_id、角度範圍
   - 更新上位機的舵機配置記錄

### 第3階段：舵機運動測試和驗證
1. 執行舵機運動測試序列：
   - **左轉**：Pan移動到最小角度（pan_min）
   - **右轉**：Pan移動到最大角度（pan_max）
   - **向上**：Tilt移動到最大角度（tilt_max）
   - **向下**：Tilt移動到最小角度（tilt_min）
   - **歸位**：Pan和Tilt都回到中位（(min+max)/2）
2. 每次運動後驗證：
   - 等待1-2秒讓舵機到達目標位置
   - 發送`<POS>`查詢當前位置
   - 驗證位置誤差是否在允許範圍內（±5度）
3. 測試結果：
   - ✅所有運動都在誤差範圍內：系統初始化驗證完成，可用於實際應用
   - ❌任何運動失敗或誤差超出範圍：舵機可能故障，需要檢查或維修

### 故障排除指南
| 症狀 | 原因 | 解決方案 |
|------|------|--------|
| Arduino持續蜂鳴，輸出錯誤訊息 | 舵機ID檢測失敗 | 1. 檢查舵機電源 2. 檢查舵機信號線連接 3. 重啟Arduino |
| 無法連接到Arduino | USB連線問題 | 1. 檢查USB線 2. 檢查Arduino驅動 3. 重新插拔USB |
| GETINFO查詢失敗或超時 | Arduino未完成初始化 | 1. 確認Arduino沒有蜂鳴 2. 等待3-4秒 3. 重啟上位機程式 |
| 舵機不動或運動異常 | 舵機故障或供電不足 | 1. 檢查舵機供電 2. 測試單個舵機響應 3. 可能需要更換舵機 |
| 位置誤差超過±5度 | 舵機校準偏差 | 1. 執行舵機校準程序 2. 檢查機械安裝 |

---

## Python控制範例

### 基本使用

```python
from pt2d_controller import PT2DController

# 連接Arduino
controller = PT2DController(port='COM3')

# 蜂鳴測試
controller.beep()

# 移動到指定角度
controller.move_to(pan=90, tilt=90)

# 查詢當前位置
pan_pos, tilt_pos = controller.get_position()
print(f"Pan: {pan_pos}°, Tilt: {tilt_pos}°")

# 查詢舵機信息
info = controller.get_info()
print(f"Pan ID: {info['pan_id']}, Tilt ID: {info['tilt_id']}")
```

### 運動序列

```python
# 掃描運動
for angle in range(0, 270, 30):
    controller.set_pan(angle)
    time.sleep(0.5)

# 歸位
controller.home()
```

---

## 常見問題

### Q: Arduino無法自動檢測到舵機
**A**: 檢查：
1. 舵機電源是否連接（紅線5V+，黑線GND）
2. 舵機信號線是否連接到RX/TX引腳
3. 電源是否足夠（建議3A+）
4. 重啟Arduino（斷電3秒後重新供電）

### Q: 舵機位置誤差大
**A**: 可能原因：
1. 舵機校準偏差 - 需要重新校準
2. 機械磨損 - 檢查齒輪和軸承
3. 供電不足 - 增加電源容量

### Q: Python連接超時
**A**: 檢查：
1. Arduino是否完成初始化（無蜂鳴）
2. USB驅動是否安裝正確
3. COM埠編號是否正確
4. 串口是否被其他程式佔用

---

## 版本歷史

- **v2.4.0** (2025-12-28): 添加初始化流程文檔和故障排除指南
- **v2.3.0** (2025-12-25): 添加GETINFO命令，改進舵機檢測
- **v2.2.0**: 添加看門狗定時器
- **v2.1.0**: 初始版本

![GA Tracking](https://ga4.ma7.in/ga/github/protocol/串口通信協議說明)
