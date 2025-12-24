# Python 模組

這個目錄包含蚊子追蹤系統的 Python 控制代碼。

## 📚 完整文檔

詳細文檔已移至 `docs` 目錄：

- **[Python 完整使用說明](../docs/python_README.md)** - Python 端完整使用指南
- **[AI 檢測配置指南](../docs/AI_DETECTION_GUIDE.md)** - AI 蚊子辨識完整指南
- **[蚊子檢測模型資源](../docs/MOSQUITO_MODELS.md)** - 模型下載和訓練指南
- **[Serial 通訊檢查](../docs/SERIAL_CHECK_SUMMARY.md)** - Serial 通訊格式檢查結果

## 📦 快速開始

### 1. 安裝依賴

```bash
pip install -r requirements.txt
```

### 2. 基本使用

```python
from pt2d_controller import PT2DController

# 連接雲台控制器
with PT2DController('/dev/ttyUSB0') as pt:
    # 移動到指定位置
    pt.move_to(135, 90)

    # 獲取當前位置
    pan, tilt = pt.get_position()
    print(f"位置: {pan}°, {tilt}°")
```

### 3. 快速啟動

```bash
# 執行完整追蹤系統
python quick_start.py
```

## 📂 模組說明

| 檔案 | 說明 |
|------|------|
| `pt2d_controller.py` | 雲台控制器（標準版） |
| `pt2d_controller_improved.py` | 雲台控制器（增強版，帶重試機制） |
| `mosquito_detector.py` | AI 蚊子檢測器 |
| `mosquito_tracker.py` | 蚊子追蹤邏輯 |
| `laser_controller.py` | 雷射控制器 |
| `stereo_camera.py` | 立體相機處理 |
| `quick_start.py` | 快速啟動腳本 |
| `test_serial_protocol.py` | Serial 通訊測試腳本 |
| `download_model.py` | 模型下載工具 |

## 🔗 更多資訊

- [項目根目錄 README](../README.md)
- [硬體連接說明](../docs/hardware.md)
- [Orange Pi 5 配置](../docs/orangepi5_hardware.md)
- [通訊協議說明](../docs/protocol.md)
