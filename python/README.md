# Python 模組

這個目錄包含蚊子追蹤系統的 Python 控制代碼和模型改進工具。

## 📂 目錄結構

### 主要模組
- `mosquito_detector.py` - AI 蚊子檢測模組
- `mosquito_tracker.py` - 蚊子追蹤邏輯
- `pt2d_controller.py` - PT2D 雲台控制器
- `laser_controller.py` - 雷射控制模組
- `stereo_camera.py` - 單一雙目攝像頭模組
- `streaming_tracking_system.py` - 一體化系統（AI+追蹤+串流，推薦主程式）

### 配置檔案
- `mosquito.ini` - 系統主要配置文件（實際運行時的配置）
- `mosquito_sample.ini` - 配置檔案範本（包含詳細參數說明）

### 模型改進工具（簡化流程）
- `label_samples.py` - 互動式樣本標註與「搬遷到雲端」
- `../mosquito_training_colab.ipynb` - Google Colab 訓練 Notebook（GPU）
- `deploy_model.py` - 一鍵部署（自動導出 ONNX/RKNN）

### 測試腳本
- `test_serial_protocol.py` - Serial 通訊測試
- `test_tracking_logic.py` - 追蹤邏輯測試
- `test_multi_target_tracking.py` - 多目標追蹤測試

## ⚙️ 配置管理系統

系統現在使用 INI 格式的配置檔案來管理所有參數，替代了之前的 Python 常量檔案。

### 配置檔案結構

- **mosquito_sample.ini**：包含所有配置參數及其詳細說明的範本檔案
- **mosquito.ini**：實際運行時的配置檔案（此檔案已加入 `.gitignore`，不會被提交到版本控制）

### 如何使用配置

1. 初始設置時，複製 `mosquito_sample.ini` 為 `mosquito.ini`：
   ```bash
   cp mosquito_sample.ini mosquito.ini
   ```

2. 根據實際環境修改 `mosquito.ini` 中的參數

3. 系統會自動從 `mosquito.ini` 加載配置參數

### 主要配置區塊

- **AI_DETECTION**：AI 檢測相關參數（影像大小、信心度閾值、IoU 閾值等）
- **SINGLE_CAMERA_FILTER**：相機過濾器參數
- **TRACKING**：追蹤系統參數（雲台增益、超時時間等）
- **HARDWARE**：硬體相關參數（串口、攝像頭 ID 等）
- **ALERTS**：警報系統參數（蜂鳴器、雷射冷卻時間）
- **SAMPLE_COLLECTION**：樣本收集參數
- **TEMPERATURE_MONITORING**：溫度監控參數
- **ILLUMINATION_MONITORING**：光照度監控參數