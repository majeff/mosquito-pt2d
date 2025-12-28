# 硬體連接詳細說明

## 📦 核心組件清單

| 組件 | 規格 | 數量 | 備註 |
|------|------|------|------|
| **開發板** | Orange Pi 5 / RDK X5 (8GB+) | 1 | AI 加速 NPU/BPU |
| **攝像頭** | 雙目 USB 1080p (3840×1080) | 2 | 基線 12cm，60fps |
| **舵機控制板** | ZL-KPZ32 (6路舵機控制器) | 1 | 開源控制板，含 Arduino Nano、舵機驅動、雷射驅動 |
| **舵機** | SP-15D/S (15kg·cm) | 2 | Pan/Tilt 軸，連接到 ZL-KPZ32 |
| **舵機電源** | 7.4V/2A | 1 | 連接到 ZL-KPZ32 供電輸入 |
| **開發板電源** | 5V/4A USB-C | 1 | 主控制器供電 |

---

## 📷 攝像頭規格

**雙目 USB 攝像頭**（3840×1080 @ 60fps MJPEG）:
- **單眼解析度**: 1920×1080 @ 60fps
- **基線距離**: 12cm (深度估計用)
- **焦距**: 3.0mm
- **視角**: 96°（對角）
- **最低照度**: 0.5 lux
- **接口**: USB 3.0 ×2
- **有效測距**: 0.5m - 5m

**深度計算**:
```
Z = (焦距 × 基線) / 視差 = (3mm × 120mm) / d_pixels
```

---

## 🔌 硬體連接

### 開發板與周邊接線

```
Orange Pi 5 / RDK X5
├─ USB 3.0 Port 1 ──→ 左攝像頭 (/dev/video0)
├─ USB 3.0 Port 2 ──→ 右攝像頭 (/dev/video1)
└─ USB 3.0 ──────────→ ZL-KPZ32 控制板 (/dev/ttyUSB0)

ZL-KPZ32 控制板
├─ USB ───────────────→ Orange Pi 5/RDK X5 (通訊)
├─ 舵機輸出 1 ────────→ Pan 舵機
├─ 舵機輸出 2 ────────→ Tilt 舵機
├─ 雷射控制輸出 ──────→ 雷射頭
├─ 電源輸入 (7.4V) ──→ 舵機電源
└─ GND ────────────────→ 所有 GND (共地)

舵機電源 (7.4V/2A)
├─ VCC ────→ ZL-KPZ32 電源輸入 (紅線)
└─ GND ────→ 所有 GND (黑/棕線)
```

### 接線步驟

**1. 舵機連接到 ZL-KPZ32**:
- Pan 舵機 → ZL-KPZ32 舵機輸出 1
- Tilt 舵機 → ZL-KPZ32 舵機輸出 2
- 舵機 GND ↔ ZL-KPZ32 GND (黑線)

**2. ZL-KPZ32 與開發板連接**:
- ZL-KPZ32 USB ↔ 開發板 USB 3.0 (自動共地)

**3. 電源連接**:
- 7.4V 電源 VCC → ZL-KPZ32 電源輸入 (紅線)
- GND 連接: 開發板 ↔ ZL-KPZ32 ↔ 舵機 (黑線)

**4. 雷射連接**:
- 雷射頭 VCC → ZL-KPZ32 雷射控制輸出
- GND → ZL-KPZ32 GND

**備註**: 所有 GND 點必須牢固連接，確保電氣共地

---

## ⚡ 電源配置

本系統採用**單一開關電源**設計，通過 DC-DC 降壓為多個電壓等級供電：

```
開關電源 (0-24V 20A, 480W)
調至 8V 輸出
│
├─ 8V ────────────────────────→ ZL-KPZ32 控制板
│                               ├─ Pan 舵機
│                               ├─ Tilt 舵機
│                               ├─ 內置 Arduino Nano
│                               └─ 雷射驅動
│
└─ 8V ──────→ LM2596S DC-DC 降壓電源 ──→ 5V USB Type-C
             (晒邦 LM2596S, 最大 20A)    │
                                       Orange Pi 5/RDK X5
                                       左攝像頭
                                       右攝像頭

系統總功耗: ~35W (單一電源 480W 足以應付)
共地要求: 開關電源負極 ↔ ZL-KPZ32 GND ↔ Orange Pi GND
```

### 電源規格說明

**開關電源 (主電源)**:
- 型號: 0-24V 20A (480W) 可調電源
- 設定值: **8V** (用於 ZL-KPZ32)
- 輸出最大電流: 20A (足以支撐全系統)

**DC-DC 降壓電源**:
- 型號: 晒邦 LM2596S DC-DC 直流降壓電源
- 輸入: 8V (來自開關電源)
- 輸出: **5V USB Type-C**
- 最大電流: 20A
- 用途: 供電給 Orange Pi 5 / RDK X5 及雙目攝像頭

**功耗分析**:

| 組件 | 電壓 | 電流 | 功率 |
|------|------|------|------|
| ZL-KPZ32 + 舵機 ×2 | 8V | 2.5A | ~20W |
| Orange Pi 5 (滿載) | 5V | 3.5A | 17.5W |
| 雙目攝像頭 | 5V | 1.0A | 5W |
| DC-DC 轉換效率損耗 (假設 90%) | - | - | ~2.5W |
| **系統總計** | - | **~7A@8V** | **~35W** |

### 穩定性措施

- **電源濾波**: 開關電源輸出端並聯 1000μF 電解電容，穩定 8V
- **DC-DC 輸出濾波**: 並聯 1000μF 電解電容，穩定 5V
- **所有 GND 連接**: 開關電源負極 ↔ ZL-KPZ32 GND ↔ Orange Pi GND，確保共地
- **電源線**: 使用 ≥1.5mm² 銅線（支援 20A 電流）
- **驗證**: 用萬用電表檢查 GND 導通性 (<0.1Ω)

---

## 🔧 系統檢查與故障排除

### 上電前檢查清單

- [ ] 所有接線牢固，無鬆動
- [ ] 電源極性正確 (紅=+, 黑/棕=GND)
- [ ] 用萬用電表測 GND 導通性
- [ ] 確認無短路

### 常見問題

| 問題 | 解決方案 |
|------|---------|
| **Arduino 無連接** | `ls -l /dev/tty*` 查看設備; `chmod 666 /dev/ttyUSB*` |
| **攝像頭無法開啟** | `ls /dev/video*` 檢查; `chmod 666 /dev/video*` |
| **舵機無響應** | 執行 `python configure_servo_id.py` 檢查舵機 ID |
| **電源不穩定** | 並聯電容; 檢查接線牢固度 |
| **過熱** | 添加散熱片/風扇; 檢查電源電壓 (≤8.4V) |

---

## 🛡️ 安全與驗證

### 電源安全

- **主電源**: 開關電源可調至 8V，具內置過流保護（20A）
- **DC-DC 轉換器**: LM2596S 具內置短路保護，最大輸出 20A
- **穩壓濾波**: 8V 和 5V 輸出端都並聯大容量電解電容 (1000μF)
- **低電源波紋**: 開關電源 <100mV，DC-DC 輸出 <200mV

### 機械安全

- 確保 ZL-KPZ32 控制板固定牢固
- 活動範圍內無障礙物
- 避免手指接近運動舵機

### 雷射安全

- 避免直視光束 (Class 3A)
- 不要讓兒童接觸

---

## 📊 支援的 ARM 開發板

| 平台 | AI 加速器 | 算力 | 推理引擎 | 模型格式 | 典型 FPS |
|------|----------|------|---------|---------|---------|
| **RDK X5** | BPU (Bayes-e) | 10 TOPS | `hobot_dnn` | `.bin` | 30-60 ⭐⭐⭐ |
| **Orange Pi 5** | NPU (RK3588) | 6 TOPS | `rknnlite` | `.rknn` | 25-50 ⭐⭐ |

**詳細部署** → 見 [MOSQUITO_MODELS.md](MOSQUITO_MODELS.md)

---

## ✅ 啟動與測試

### 系統初始化

```bash
# 1. 配置舵機 ID
python configure_servo_id.py

# 2. 測試硬體連接
python test_serial_protocol.py

# 3. 驗證攝像頭
python -c "import cv2; print('✓ OK' if cv2.VideoCapture(0).isOpened() else '✗ Error')"

# 4. 啟動完整系統
python streaming_tracking_system.py
```

### 驗證檢查

```bash
# 檢查裝置
ls /dev/video*
ls /dev/ttyUSB*

# 查看 USB 設備
lsusb | grep -E "Arduino|Camera"

# 測試雲台
python pt2d_controller.py
```

---

## 📚 相關文件

- [MOSQUITO_MODELS.md](MOSQUITO_MODELS.md) - AI 模型部署
- [protocol.md](protocol.md) - 通訊協議細節
- [python/README.md](python_README.md) - Python 系統説明

---

**最後更新**: 2025年12月
**適用硬體**: Orange Pi 5 / RDK X5 + Arduino Nano
