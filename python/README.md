# Python 模組

這個目錄包含蚊子追蹤系統的 Python 控制代碼和模型改進工具。

## 📂 目錄結構

### 主要模組
- `mosquito_detector.py` - AI 蚊子檢測模組
- `mosquito_tracker.py` - 蚊子追蹤邏輯
- `pt2d_controller.py` - PT2D 雲台控制器
- `laser_controller.py` - 雷射控制模組
- `stereo_camera.py` - 雙目相機模組
- `streaming_tracking_system.py` - 一體化系統（AI+追蹤+串流，推薦主程式）

### 模型改進工具（簡化流程）
- `label_samples.py` - 互動式樣本標註與「搬遷到雲端」
- `../mosquito_training_colab.ipynb` - Google Colab 訓練 Notebook（GPU）
- `deploy_model.py` - 一鍵部署（自動導出 ONNX/RKNN）

### 測試腳本
- `test_serial_protocol.py` - Serial 通訊測試
- `test_tracking_logic.py` - 追蹤邏輯測試
- `test_multi_target_tracking.py` - 多目標追蹤測試

## 📚 完整文檔

詳細文檔已移至 `docs` 目錄：

- **[Python 完整使用說明](../docs/python_README.md)** - Python 端完整使用指南
- **[AI 檢測與追蹤整合指南](README.md)** - 本目錄文件（取代 AI_DETECTION_GUIDE）
- **[蚊子檢測模型資源](../docs/MOSQUITO_MODELS.md)** - 模型持續改進與訓練指南
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

### 3. AI 檢測器進階功能

#### 儲存中等信心度樣本

啟用自動儲存功能，收集信心度中等的樣本圖片供後續檢驗與再訓練：

```python
from mosquito_detector import MosquitoDetector

# 啟用中等信心度樣本儲存
detector = MosquitoDetector(
    model_path="models/mosquito",
    save_uncertain_samples=True,          # 啟用儲存功能
    uncertain_conf_range=(0.35, 0.65),   # 信心度範圍
    save_dir="uncertain_samples",         # 儲存目錄
    max_samples=1000,                     # 最多存 1000 張照片
    save_interval=3.0,                    # 每 3 秒最多存一次
    save_annotations=True,                # 自動生成 YOLO 標註文件
    save_full_frame=False                 # 僅儲存裁剪區域
)

# 檢測時會自動儲存中等信心度的樣本
detections, result = detector.detect(frame)
```

**功能說明**：
- 自動儲存信心度在 0.35-0.65 範圍內的檢測結果
- **自動生成 YOLO 格式標註文件**（.txt），可直接用於再訓練
- 最多儲存 1000 張照片，超過自動停止
- 避免頻繁存同一位置的照片（3 秒內只存一次）
- 每 10 張圖片輸出一次統計資訊
- 圖片命名格式：`mosquito_時間戳_conf信心度.jpg`
- 標註檔案格式：`mosquito_時間戳_conf信心度.txt`（YOLO 格式）

**YOLO 標註格式**：
```
class_id x_center y_center width height
```
所有座標值均歸一化到 0-1 範圍，可直接用於 YOLO 訓練。

**儲存模式選項**：
- `save_full_frame=False`：僅儲存裁剪區域（適合快速檢視）
- `save_full_frame=True`：儲存完整畫面並標記檢測框（適合再標註）

### 4. 模型改進工作流程（新版）

系統會自動收集中等信心度的檢測樣本（0.35-0.65），用於持續改進模型。新版流程：

#### 步驟 1：人工標註與搬遷到雲端

```bash
# 互動式標註工具；內建統計與搬遷到 Google Drive
python label_samples.py
```

完成一輪標註後，執行選項 `m` 可將 `confirmed/` 內樣本搬遷到 Google Drive 指定資料夾（見 `python/config.py` 的 `RELOCATION_BASE_DIR`）。

#### 步驟 2：Google Colab 訓練

在雲端開啟並執行 Notebook：

- 檔案：專案根目錄的 `mosquito_training_colab.ipynb`
- 開啟位置：Google Drive「我的雲端硬碟/Colab Notebooks/」
- 內容：自動掛載 Drive、建立資料集（使用 `relocated/` 最新一批樣本）、訓練、評估、將新模型存入 `MyDrive/mosquito-training/models/mosquito_yolov8_new.pt`

#### 步驟 3：部署新模型

```bash
# 從 Google Drive 同步的新模型部署到本機 models/ 並導出 ONNX/RKNN
python deploy_model.py --imgsz 320
```

進階參數與詳細說明請參見 [蚊子檢測模型資源](../docs/MOSQUITO_MODELS.md)。

### 5. 執行系統

```bash
# 一體化系統（AI+追蹤+串流）
# 基本執行（自動檢測單目/雙目）
python streaming_tracking_system.py

# 指定單目模式
python streaming_tracking_system.py --single

# 查看所有參數
python streaming_tracking_system.py --help

# 或僅啟動追蹤（無串流）
python mosquito_tracker.py
```

**主要參數：**
- `--single/--dual`: 指定攝像頭模式（不指定則自動檢測）
- `--port`: Arduino 串口
- `--mode`: 串流模式（single/side_by_side/dual_stream）
- `--no-save-samples`: 停用中等信心度樣本儲存

## 📂 模組說明

| 檔案 | 說明 |
|------|------|
| `pt2d_controller.py` | 雲台控制器（含重試機制） |
| `mosquito_detector.py` | AI 蚊子檢測器 |
| `mosquito_tracker.py` | 蚊子追蹤邏輯 |
| `stereo_camera.py` | 立體相機處理 |
| `streaming_server.py` | 影像串流伺服器（HTTP-MJPEG） |
| `test_serial_protocol.py` | Serial 通訊測試腳本 |
| `test_tracking_logic.py` | 追蹤邏輯測試腳本 |
| `test_multi_target_tracking.py` | 多目標追蹤測試腳本 |

## 🔗 更多資訊

- [項目根目錄 README](../README.md)
- [硬體連接說明（包含 RDK X5 配置）](../docs/hardware.md)
- [蚊子模型訓練與部署（包含 RDK X5 流程）](../docs/MOSQUITO_MODELS.md)
- [通訊協議說明](../docs/protocol.md)
- [影像串流指南](../docs/STREAMING_GUIDE.md) - 讓手機觀看即時影像
