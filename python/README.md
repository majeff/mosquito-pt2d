# Python 模組

這個目錄包含蚊子追蹤系統的 Python 控制代碼和模型改進工具。

## 📂 目錄結構

### 主要模組
- `quick_start.py` - 快速啟動腳本
- `mosquito_detector.py` - AI 蚊子檢測模組
- `mosquito_tracker.py` - 蚊子追蹤邏輯
- `pt2d_controller.py` - PT2D 雲台控制器
- `laser_controller.py` - 雷射控制模組
- `stereo_camera.py` - 雙目相機模組

### 模型改進工具
- `label_samples.py` - 互動式樣本標註工具
- `prepare_dataset.py` - YOLO 數據集準備腳本
- `train_model.py` - 模型微調訓練腳本
- `evaluate_model.py` - 模型性能評估工具
- `compare_models.py` - 新舊模型比較工具

### 測試腳本
- `test_serial_protocol.py` - Serial 通訊測試
- `test_tracking_logic.py` - 追蹤邏輯測試
- `test_multi_target_tracking.py` - 多目標追蹤測試

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
    max_disk_usage_percent=20.0,         # 最大磁碟使用率 20%
    save_annotations=True,                # 自動生成 YOLO 標註文件
    save_full_frame=False                 # 僅儲存裁剪區域
)

# 檢測時會自動儲存中等信心度的樣本
detections, result = detector.detect(frame)
```

**功能說明**：
- 自動儲存信心度在 0.35-0.65 範圍內的檢測結果
- **自動生成 YOLO 格式標註文件**（.txt），可直接用於再訓練
- 同步檢查磁碟使用率，超過 20% 自動暫停儲存
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

### 4. 模型改進工作流程

系統會自動收集中等信心度的檢測樣本（0.35-0.65），用於持續改進模型。完整工作流程：

#### 步驟 1：人工標註樣本

```bash
# 互動式標註工具，逐一審核樣本
python label_samples.py
```

功能：
- 自動顯示每張圖片
- 提供互動式選項（是蚊子/不是蚊子/跳過/退出）
- 自動分類到對應目錄
- 顯示標註統計

#### 步驟 2：準備訓練數據集

```bash
# 將標註好的樣本轉換為 YOLO 格式
python prepare_dataset.py
```

功能：
- 從 `sample_collection/confirmed/` 讀取樣本
- 建立訓練/驗證集（80/20 分割）
- 生成 YOLO 格式標籤檔案
- 創建 `dataset.yaml` 配置檔

#### 步驟 3：訓練模型

```bash
# 使用收集的樣本微調模型
python train_model.py
```

功能：
- 載入預訓練模型 `models/mosquito_yolov8.pt`
- 自動配置訓練參數（學習率、數據增強）
- 支援 GPU 加速（自動檢測）
- 保存最佳模型和訓練圖表

#### 步驟 4：評估模型

```bash
# 評估訓練後的模型性能
python evaluate_model.py

# 指定模型路徑（可選）
python evaluate_model.py --model training_runs/mosquito_finetune/weights/best.pt
```

功能：
- 計算 mAP、Precision、Recall 等指標
- 測試實際圖片的檢測效果
- 生成詳細評估報告
- 提供改進建議

#### 步驟 5：比較新舊模型

```bash
# 比較舊模型和新訓練模型
python compare_models.py

# 指定模型路徑（可選）
python compare_models.py --old models/mosquito_yolov8.pt --new training_runs/mosquito_finetune/weights/best.pt
```

功能：
- 同時評估兩個模型
- 計算各項指標的改進百分比
- 比較推理速度
- 提供是否部署的建議

**詳細說明**：參見 [蚊子檢測模型資源](../docs/MOSQUITO_MODELS.md)

### 5. 快速啟動

```bash
# 執行完整追蹤系統
python quick_start.py
```

## 📂 模組說明

| 檔案 | 說明 |
|------|------|
| `pt2d_controller.py` | 雲台控制器（含重試機制） |
| `mosquito_detector.py` | AI 蚊子檢測器 |
| `mosquito_tracker.py` | 蚊子追蹤邏輯 |
| `stereo_camera.py` | 立體相機處理 |
| `streaming_server.py` | 影像串流伺服器（HTTP-MJPEG） |
| `quick_start.py` | 快速啟動腳本 |
| `test_serial_protocol.py` | Serial 通訊測試腳本 |
| `test_tracking_logic.py` | 追蹤邏輯測試腳本 |
| `test_multi_target_tracking.py` | 多目標追蹤測試腳本 |

## 🔗 更多資訊

- [項目根目錄 README](../README.md)
- [硬體連接說明](../docs/hardware.md)
- [Orange Pi 5 配置](../docs/orangepi5_hardware.md)
- [通訊協議說明](../docs/protocol.md)
- [影像串流指南](../docs/STREAMING_GUIDE.md) - 讓手機觀看即時影像
