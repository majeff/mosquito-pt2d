# 硬體連接詳細說明

## 📦 核心組件清單

| 組件 | 規格 | 數量 | 備註 |
|------|------|------|------|
| **開發板** | Orange Pi 5 / RDK X5 (8GB+) | 1 | AI 加速 NPU/BPU |
| **攝像頭** | 雙目 USB 1080p (3840×1080) | 2 | 基線 12cm，60fps |
| **Arduino** | Arduino Nano | 1 | 舵機和雷射控制 |
| **舵機** | SP-15D/S (15kg·cm) | 2 | Pan/Tilt 軸 |
| **雷射** | 5V 紅光 1mW | 1 | 目標標記 |
| **舵機電源** | 7.4V/2A | 1 | 獨立供電 |
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
└─ USB 3.0 ──────────→ Arduino Nano (/dev/ttyUSB0)

Arduino Nano
├─ D10 (TX) ──→ 總線舵機數據線 (黃)
├─ D11 (RX) ←── 總線舵機數據線 (黃)
├─ D6 ─────────→ 雷射控制 (HIGH=開, LOW=關)
└─ GND (共地) ←→ 舵機電源 GND, 開發板 GND

舵機電源 (7.4V/2A)
├─ VCC ────→ Pan 舵機 (紅線)
├─ VCC ────→ Tilt 舵機 (紅線)
└─ GND ────→ 所有 GND (黑/棕線)
```

### 接線步驟

**1. 舵機與 Arduino 連接**:
- Arduino D10 (TX) → 舵機 TX (黃)
- Arduino D11 (RX) ← 舵機 RX (黃)
- Arduino GND ↔ 舵機 GND (黑)

**2. Arduino 與開發板連接**:
- USB Nano ↔ 開發板 USB 3.0 (自動共地)

**3. 電源連接**:
- 7.4V 電源 → 舵機 VCC (紅)
- GND 連接: 開發板 ↔ Arduino ↔ 舵機

**4. 雷射連接** (可選):
- Arduino D6 → 雷射頭 VCC
- GND → 雷射頭 GND

---

## ⚡ 電源配置

```
5V/4A USB-C 電源               7.4V/2A 舵機電源
│                              │
├─ Orange Pi 5/RDK X5         ├─ Pan 舵機
├─ Arduino (USB)              ├─ Tilt 舵機
├─ 左攝像頭 (USB)             └─ (共地)
└─ 右攝像頭 (USB)

系統總功耗: ~34W (推薦 50W)
共地要求: 所有 GND 必須連接
```

**功耗分析**:

| 組件 | 電壓 | 電流 | 功率 |
|------|------|------|------|
| Orange Pi 5 (滿載) | 5V | 3.5A | 17.5W |
| 雙目攝像頭 | 5V | 1.0A | 5W |
| Arduino Nano | 5V | 0.2A | 1W |
| 舵機 ×2 (工作) | 7.4V | 1.6A | ~12W |
| **總計** | - | - | **~35W** |

**穩定性措施**:
- 舵機電源並聯 100μF-1000μF 電解電容
- 所有 GND 點必須連接（共地）
- 電源線使用 ≥1mm² 銅線
- 測試: 用萬用電表確認 GND 導通性 (<1Ω)

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

- **高壓**: 舵機 7.4V，接線時必須斷電
- **過流保護**: 舵機電源建議加 3A 保險絲
- **穩壓濾波**: 並聯大容量電解電容 (470-1000μF)

### 機械安全

- 確保雲台固定牢固
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
