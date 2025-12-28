# 蚊子檢測模型持續改進指南

本專案在 `models/` 目錄已提供預訓練模型。本文檔說明如何利用系統自動收集的**中低信心度樣本**進行人工篩選和模型增強訓練，持續提升檢測準確度。

##  目錄

- [系統運作流程](#系統運作流程)
- [模型改進三步驟](#模型改進三步驟)
  - [步驟 1: 人工標註樣本](#步驟-1-人工標註樣本)
  - [步驟 2: Google Colab 訓練](#步驟-2-google-colab-訓練)
  - [步驟 3: 部署新模型](#步驟-3-部署新模型)
- [預期改進效果](#預期改進效果)
- [故障排除](#故障排除)

---

##  系統運作流程

### 自動樣本收集（系統內建）

系統在運行時會自動收集**中低信心度檢測樣本**，用於後續人工審核和模型改進：

**觸發條件**（見 `python/mosquito_tracker.py`）：
```python
# 信心度在 0.35-0.65 之間的檢測會被自動保存
MEDIUM_CONFIDENCE_MIN = 0.35
MEDIUM_CONFIDENCE_MAX = 0.65
```

**保存位置**：
```
sample_collection/
 medium_confidence/          # 中等信心度樣本（待審核）
    20250127_143022_conf0.42.jpg
    ...
 confirmed/                  # 人工確認後的樣本（用於訓練）
     mosquito/               # 確認是蚊子
     not_mosquito/           # 確認不是蚊子（負樣本）
```

**建議樣本數量**（開始訓練前）：
- 蚊子樣本：至少 **50-100 張**
- 非蚊子樣本：至少 **30-50 張**（降低誤報率）

---

##  模型改進三步驟

### 步驟 1: 人工標註樣本

使用互動式標註工具審核收集的樣本：

```bash
# 在本地電腦執行
python python/label_samples.py
```

**功能**：
- 自動顯示每張圖片
- 提供互動式選項：
  - `y` - 確認是蚊子
  - `n` - 確認不是蚊子
  - `d` - 刪除此樣本
  - `s` - 📊 顯示統計資訊（隨時查看樣本數量）
  - `m` - 📦 搬遷已標註樣本（訓練完成後清理用）
  - `q` - 退出
- 自動將檔案移動到對應目錄

---

### 步驟 2: Google Colab 訓練

**為什麼使用 Google Colab？**
-  **完全免費**：每次可使用 12 小時 T4 GPU
-  **速度快**：T4 GPU 比 Orange Pi 5 CPU 快 **50-100 倍**
-  **訓練時間**：50 epochs 只需 **15-30 分鐘**（Orange Pi 5 需 12-24 小時）

**操作步驟**：
1. 在 Google Colab 開啟「我的雲端硬碟/Colab Notebooks/mosquito_training_colab.ipynb」
2. 選擇 GPU 執行階段：**執行階段**  **變更執行階段類型**  **T4 GPU**
3. 依序執行每個 Cell（共 7 個步驟）
4. 等待訓練完成（約 15-30 分鐘）
5. 訓練完成後，新模型會自動保存到 Google Drive

**Notebook 包含的步驟**：
- 掛載 Google Drive
- 安裝訓練環境
- 準備數據集（80/20 分割）
- 訓練模型（50 epochs）
- 評估結果（mAP/精確率/召回率）
- 保存模型到 Google Drive
- 查看訓練曲線
---

### 步驟 3: 部署新模型

等待 Google Drive 本地同步完成後，執行單一 Python 腳本（預設同時導出 ONNX 與 RKNN）：

```sh
python python/deploy_model.py
# 預設目標由系統自動判斷（Linux 部署機）；可覆寫：
python python/deploy_model.py --imgsz 320 --rknn-target rk3588
# 預設自動量化（從已標註樣本生成 dataset.txt）；如需停用量化：
python python/deploy_model.py --imgsz 320 --rknn-no-quant
# 自訂量化清單（覆寫自動生成）：
python python/deploy_model.py --imgsz 320 --rknn-quant-dataset path/to/dataset.txt
```

選項：
- `--imgsz <int>`：ONNX 導出解析度（預設取自 config.DEFAULT_IMGSZ）
- `--skip-onnx`：略過 ONNX 導出（僅複製模型）
 - `--export-rknn`：強制導出 RKNN（一般不需使用）
 - `--skip-rknn`：略過 RKNN 導出（預設會導出）
  - `--rknn-target <str>`：RKNN 目標平台（未提供則自動偵測，否則預設 rk3588）
  - `--onnx-opset <int>` / `--onnx-dynamic` / `--onnx-half`：覆寫 ONNX 導出參數（依目標平台帶入保守預設）
 - `--rknn-quant-dataset <txt>`：覆寫量化資料集清單（選填）
 - `--rknn-no-quant`：禁用 RKNN 量化（不生成 dataset.txt）

**部署檢查清單**：
- [ ] 已備份舊模型
- [ ] 新模型已複製到 `models/` 目錄
- [ ] 已轉換 ONNX 格式
- [ ] 已轉換 RKNN 格式（可選）
- [ ] 測試新模型效果

---

##  完整工作流程圖

```
Orange Pi 5 自動收集樣本

本地電腦: python label_samples.py（標註）

Google Drive 本地同步（上傳樣本 + 模型）

Google Colab: 訓練模型（15-30 分鐘）

Google Drive 本地同步（下載新模型）

本地電腦: 轉換格式（ONNX/RKNN）

Orange Pi 5: 部署測試
```

---

##  預期改進效果

根據經驗，持續改進訓練可帶來以下效果：

| 訓練輪次 | 樣本數 | mAP50 | 精確率 | 召回率 | 備註 |
|---------|-------|-------|--------|--------|------|
| **初始模型** | 0 | 0.65 | 0.70 | 0.60 | 預訓練模型 |
| **第 1 輪** | 100 | 0.72 | 0.75 | 0.68 | +7% mAP |
| **第 2 輪** | 200 | 0.78 | 0.80 | 0.75 | +6% mAP |
| **第 3 輪** | 300 | 0.82 | 0.83 | 0.80 | +4% mAP |
| **第 4 輪+** | 500+ | 0.85+ | 0.87+ | 0.83+ | 逐漸飽和 |

**改進建議**：
- 每收集 50-100 張新樣本就進行一次訓練
- 重點收集**誤報案例**（降低假陽性）
- 關注**漏檢場景**（提高召回率）

---

##  故障排除

### Q: Google Colab 訓練時記憶體不足？
**A**:
```python
# 減少批次大小
batch=8  # 或更小

# 降低解析度
imgsz=224  # 從 320 降到 224
```

### Q: Google Drive 同步太慢？
**A**:
1. 只同步必要的資料夾
2. 壓縮樣本後再上傳
3. 使用 rclone 等工具加速同步

### Q: 新模型效果反而變差？
**A**:
1. 檢查數據集品質（是否有錯誤標註）
2. 增加訓練輪數（epochs=100）
3. 調整學習率（lr0=0.0001 更小）
4. 使用早停（patience=10）

### Q: 找不到 CUDA 裝置？
**A**:
確認 Colab 已選擇 GPU 執行階段：
- 點擊「執行階段」「變更執行階段類型」
- 選擇「T4 GPU」或「V100 GPU」

---

##  參考資源

- [Google Colab 官方文檔](https://colab.research.google.com/)
- [Ultralytics YOLOv8 文檔](https://docs.ultralytics.com/)
- [Google Drive 同步設定](https://support.google.com/drive/answer/2374987)

---

**最後更新**: 2025年12月27日