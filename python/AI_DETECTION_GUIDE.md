# AI 蚊子辨識指南 (Orange Pi 5 優化版)

本專案使用深度學習 AI 模型（YOLOv8）來進行蚊子偵測，針對 Orange Pi 5 的 NPU (神經處理單元) 進行優化。

**硬體平台**: Orange Pi 5 (RK3588 SoC, 6 TOPS NPU)
**推理引擎**: RKNN Toolkit / ONNX Runtime
**建議使用**: 預訓練的蚊子檢測模型

## 🚀 快速開始

### 1. 安裝依賴套件 (Orange Pi 5)

#### 步驟 1.1: 安裝系統級依賴

首先安裝編譯工具和開發庫（**必須**）：

```bash
# 更新系統
sudo apt update && sudo apt upgrade -y

# 安裝編譯工具和依賴庫
sudo apt install -y \
    build-essential \
    cmake \
    git \
    libssl-dev \
    libffi-dev \
    python3-dev \
    python3-pip

# 安裝 OpenCV 系統依賴
sudo apt install -y \
    libjasper-dev \
    libtiff5-dev \
    libatlas-base-dev \
    libharfbuzz0b \
    libwebp6

# 驗證 cmake 安裝
cmake --version
```

**重要**: 如果跳過此步驟會導致 `cmake not found` 錯誤！

#### 步驟 1.2: 安裝 Python 套件

```bash
# 基本套件
pip install -r requirements.txt

# Orange Pi 5 NPU 支援 (推薦)
# RKNN Toolkit 2 - 最新版本 2.3.2，可直接通過 pip 安裝
pip install rknn-toolkit2
```

這會安裝以下主要套件：
- `ultralytics`: YOLO AI 模型框架 (CPU 推理)
- `onnxruntime`: ONNX 模型推理引擎
- `opencv-python`: 影像處理
- `numpy`: 數值運算
- `rknn-toolkit2`: (推薦) RK3588 NPU 加速 (v2.3.2+)

**注意**: Orange Pi 5 沒有 GPU，不需要安裝 PyTorch CUDA 版本。

## 🚀 快速開始

### 自動安裝腳本（推薦）

為了簡化安裝過程，使用此一鍵安裝腳本：

```bash
# 建立安裝腳本
cat > install_orangepi5.sh << 'EOF'
#!/bin/bash
set -e

echo "=========================================="
echo "Orange Pi 5 AI 蚊子檢測系統安裝"
echo "=========================================="

# 步驟 1: 更新系統
echo "[1/4] 更新系統..."
sudo apt update && sudo apt upgrade -y

# 步驟 2: 安裝系統依賴
echo "[2/4] 安裝編譯工具和開發庫..."
sudo apt install -y \
    build-essential cmake git \
    libssl-dev libffi-dev python3-dev \
    libjasper-dev libtiff5-dev \
    libatlas-base-dev libharfbuzz0b libwebp6

# 步驟 3: 驗證 cmake
echo "[3/4] 驗證 cmake..."
cmake --version

# 步驟 4: 安裝 Python 套件
echo "[4/4] 安裝 Python 套件..."
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install rknn-toolkit2

echo ""
echo "=========================================="
echo "✓ 安裝完成！"
echo "=========================================="
echo ""
echo "驗證安裝："
echo "  python3 -c \"import ultralytics; print('YOLOv8 OK')\""
echo "  python3 -c \"from rknn.api import RKNN; print('RKNN 2.3.2 OK')\""
echo ""
EOF

# 執行安裝腳本
chmod +x install_orangepi5.sh
./install_orangepi5.sh
```

### 手動安裝步驟

如果自動腳本不可用，按照以下步驟手動安裝：

**步驟 1: 安裝系統依賴** (必須)

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y build-essential cmake git libssl-dev libffi-dev python3-dev
```

**步驟 2: 驗證 cmake**

```bash
cmake --version
# 應該輸出類似：cmake version 3.xx.x
```

**步驟 3: 升級 pip**

```bash
pip install --upgrade pip setuptools wheel
```

**步驟 4: 安裝 Python 套件**

```bash
cd python
pip install -r requirements.txt
```

**步驟 5: 安裝 RKNN Toolkit 2 (推薦)**

```bash
# 直接安裝最新版本 (v2.3.2+)
pip install rknn-toolkit2
```

**驗證安裝：**

```bash
# 驗證 YOLOv8
python3 -c "from ultralytics import YOLO; print('✓ YOLOv8 安裝成功')"

# 驗證 RKNN (v2.3.2+)
python3 -c "from rknn.api import RKNN; print('✓ RKNN 2.3.2 安裝成功')"

# 驗證 OpenCV
python3 -c "import cv2; print(f'✓ OpenCV {cv2.__version__} 安裝成功')"
```

### 2. 執行測試

```bash
python mosquito_detector.py
```

首次執行時會自動下載 YOLOv8n 預訓練模型（約 6MB）。

## 📝 使用方法

### 基本使用

```python
from mosquito_detector import MosquitoDetector
import cv2

# 初始化 AI 偵測器 (Orange Pi 5 優化)
detector = MosquitoDetector(
    model_path='mosquito_yolov8n.pt',  # 使用蚊子專用模型
    confidence_threshold=0.3,           # 信心度閾值
    imgsz=320                           # Orange Pi 5 建議使用 320
)

# 讀取影像
frame = cv2.imread('test_image.jpg')

# 執行偵測
detections, _ = detector.detect(frame)

# 繪製結果
result = detector.draw_detections(frame, detections)
cv2.imshow('Result', result)
cv2.waitKey(0)
```

### 使用自定義訓練模型

如果你有自己訓練的蚊子檢測模型：

```python
detector = MosquitoDetector(
    model_path='path/to/your/mosquito_model.pt',
    confidence_threshold=0.5
)
```

### 整合到追蹤系統

```python
from mosquito_detector import MosquitoDetector
from mosquito_tracker import MosquitoTracker

detector = MosquitoDetector()
tracker = MosquitoTracker()

while True:
    ret, frame = cap.read()

    # AI 偵測
    detections, _ = detector.detect(frame)

    # 獲取最佳目標
    best = detector.get_largest_detection(detections)

    if best:
        cx, cy = best['center']
        # 使用追蹤器計算雲台角度
        angles = tracker.calculate_angles(frame, (cx, cy))
```

## 🎯 模型說明

### Orange Pi 5 性能考量

- **CPU**: RK3588 8核心 (4×A76 + 4×A55)
- **NPU**: 6 TOPS 算力
- **推薦策略**: 使用輕量級模型 + NPU 加速
- **目標幀率**: 10-20 FPS (CPU), 20-30 FPS (NPU)

### 模型選項

#### 1. 預設模型（YOLOv8n）- 不推薦

- **類型**: 通用物體檢測模型
- **大小**: 6MB
- **速度**: 慢（約 5-10 FPS 在 Orange Pi 5 CPU）
- **用途**: 檢測小型移動物體
- **限制**: 未專門訓練、效能差、誤檢多

#### 2. 蚊子專用模型（強烈推薦）

為了獲得最佳效果，請使用現有的蚊子檢測模型：

##### 🔍 線上可用的蚊子檢測模型

**A. Roboflow 蚊子數據集**

Roboflow 平台有多個公開的蚊子檢測數據集和預訓練模型：

1. **Mosquito Detection Dataset** - [Roboflow Universe](https://universe.roboflow.com/)
   - 搜尋關鍵字: "mosquito detection"
   - 提供已標註數據集和預訓練模型
   - 可直接下載 YOLOv8 格式

```bash
# 從 Roboflow 下載範例
pip install roboflow

python << EOF
from roboflow import Roboflow
rf = Roboflow(api_key="YOUR_API_KEY")
project = rf.workspace("workspace-name").project("mosquito-detection")
dataset = project.version(1).download("yolov8")
EOF
```

**B. GitHub 開源模型**

搜尋以下 GitHub 專案：
- 關鍵字: "mosquito detection yolo"
- 關鍵字: "insect detection model"
- 關鍵字: "flying insect tracking"

推薦專案：
```bash
# 範例專案（需要自行搜尋最新的）
git clone https://github.com/[username]/mosquito-detection
cd mosquito-detection
# 使用其預訓練模型
```

**C. Kaggle 數據集**

- 搜尋: "mosquito dataset" on Kaggle
- 下載已訓練的模型權重 (.pt 檔案)
- 範例: https://www.kaggle.com/datasets/[dataset-name]

**D. 自己訓練輕量級模型（適合 Orange Pi 5）**

```bash
# 使用 YOLOv8n-nano 訓練（最輕量）
yolo train data=mosquito.yaml model=yolov8n.pt epochs=100 imgsz=416

# 轉換為 ONNX 格式（Orange Pi 5 優化）
yolo export model=best.pt format=onnx opset=12 simplify=True

# 進一步轉換為 RKNN 格式（NPU 加速）
# 需要使用 RKNN Toolkit 2
```

##### 📦 模型下載和使用

**步驟 1: 下載模型**

```bash
# 建立模型目錄
mkdir -p models

# 下載預訓練蚊子模型（範例連結，需要替換為實際來源）
wget -O models/mosquito_yolov8n.pt https://example.com/mosquito_model.pt

# 或從 Google Drive / Dropbox 下載
# gdown --id FILE_ID -O models/mosquito_yolov8n.pt
```

**步驟 2: 使用模型**

```python
detector = MosquitoDetector(model_path='models/mosquito_yolov8n.pt')
```

#### 3. NPU 加速模型（Orange Pi 5 最佳性能）

使用 RKNN 格式在 NPU 上運行：

```bash
# 轉換 PyTorch 模型到 ONNX
python << EOF
from ultralytics import YOLO
model = YOLO('mosquito_yolov8n.pt')
model.export(format='onnx', opset=12)
EOF

# 使用 RKNN Toolkit 轉換 ONNX 到 RKNN
python convert_onnx_to_rknn.py \
    --onnx mosquito_yolov8n.onnx \
    --rknn mosquito_yolov8n.rknn \
    --target-platform rk3588
```

**convert_onnx_to_rknn.py** 範例：
```python
from rknn.api import RKNN

def convert_to_rknn(onnx_path, rknn_path):
    rknn = RKNN()

    # 配置
    rknn.config(
        mean_values=[[0, 0, 0]],
        std_values=[[255, 255, 255]],
        target_platform='rk3588'
    )

    # 載入 ONNX
    print(f'載入 {onnx_path}')
    ret = rknn.load_onnx(model=onnx_path)
    if ret != 0:
        print('載入失敗!')
        return

    # 建立 RKNN 模型
    print('建立 RKNN 模型')
    ret = rknn.build(do_quantization=True, dataset='./calibration_dataset.txt')
    if ret != 0:
        print('建立失敗!')
        return

    # 匯出 RKNN 模型
    print(f'匯出到 {rknn_path}')
    ret = rknn.export_rknn(rknn_path)

    rknn.release()
    print('轉換完成!')

if __name__ == '__main__':
    convert_to_rknn('mosquito_yolov8n.onnx', 'mosquito_yolov8n.rknn')
```

---

## 🌐 線上資源和模型來源

### 數據集和模型平台

| 平台 | 連結 | 說明 |
|------|------|------|
| **Roboflow Universe** | https://universe.roboflow.com/ | 搜尋 "mosquito" 或 "insect" |
| **Kaggle** | https://www.kaggle.com/datasets | 搜尋 "mosquito detection" |
| **GitHub** | https://github.com/search | 搜尋 "mosquito detection yolo" |
| **Hugging Face** | https://huggingface.co/models | 搜尋 "mosquito" 或 "insect" |
| **Papers with Code** | https://paperswithcode.com/ | 學術論文 + 程式碼 |

### 搜尋關鍵字建議

在上述平台搜尋時使用：
- `mosquito detection`
- `mosquito tracking`
- `insect detection yolo`
- `flying insect recognition`
- `aedes mosquito detection`
- `病媒蚊偵測`

### 模型評估標準

選擇模型時考慮：
1. **模型大小**: < 10MB（適合嵌入式裝置）
2. **輸入解析度**: 320x320 或 416x416（平衡速度和精度）
3. **框架**: YOLOv8, YOLOv5, YOLO-NAS
4. **格式**: .pt (PyTorch), .onnx (ONNX), .rknn (NPU)
5. **準確度**: mAP > 0.7（在測試集上）
6. **速度**: > 10 FPS on Orange Pi 5



## ⚙️ 參數調整 (Orange Pi 5 優化)

### confidence_threshold（信心度閾值）

- **範圍**: 0.0 - 1.0
- **建議**: 0.3-0.4（針對蚊子檢測）
- **說明**:
  - 較低值（0.2-0.3）：檢測更多物體，但可能有誤檢
  - 較高值（0.5-0.7）：只檢測高信心度物體，減少誤檢
  - Orange Pi 5 建議使用較高閾值以減少運算負擔

### iou_threshold（IoU 閾值）

- **範圍**: 0.0 - 1.0
- **預設**: 0.45
- **說明**: 用於非極大值抑制（NMS），控制重疊框的過濾

### 輸入解析度優化

```python
# 降低輸入解析度以提升速度（Orange Pi 5 建議）
detector = MosquitoDetector(
    model_path='mosquito_yolov8n.pt',
    imgsz=320  # 或 416，預設是 640
)

# 在推理時調整
results = model.predict(frame, imgsz=320)
```

### 幀率控制

```python
import cv2
import time

cap = cv2.VideoCapture(0)
frame_interval = 0.1  # 每 100ms 處理一幀 (10 FPS)

last_time = time.time()
while True:
    ret, frame = cap.read()

    current_time = time.time()
    if current_time - last_time >= frame_interval:
        # 只在間隔時間後才進行檢測
        detections, _ = detector.detect(frame)
        last_time = current_time
```

## 🔧 故障排除 (Orange Pi 5 專用)

### Orange Pi 5 特定問題

**問題 1: 推理速度太慢（< 5 FPS）**

解決方案：
```bash
# 1. 使用更小的模型
yolo export model=yolov8n.pt format=onnx imgsz=320

# 2. 降低解析度
# 在代碼中設置 imgsz=320 或 imgsz=416

# 3. 使用 ONNX Runtime
pip install onnxruntime
```

**問題 2: 記憶體不足**

```bash
# 檢查記憶體使用
free -h

# 增加 swap 空間
sudo dd if=/dev/zero of=/swapfile bs=1G count=4
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

**問題 3: NPU 無法使用**

```bash
# 檢查 NPU 驅動
dmesg | grep -i npu

# 安裝 RKNN Toolkit 2
# 從官方下載對應 Python 版本的 wheel 檔案
pip install rknn_toolkit2-*.whl

# 測試 NPU
python -c "from rknn.api import RKNN; print('NPU OK')"
```


### 錯誤: "Could not find cmake executable"

**症狀**:
```
AssertionError: Could not find "cmake" executable!
```

**原因**: 系統缺少 cmake 和編譯工具

**解決方案**:
```bash
# 安裝編譯工具
sudo apt update
sudo apt install -y build-essential cmake git libssl-dev libffi-dev python3-dev

# 驗證安裝
cmake --version

# 重新安裝 RKNN Toolkit 2
pip install rknn-toolkit2
```

**注意**: 如果仍然失敗，可以先不安裝 RKNN，使用 CPU 版本（見下方）

### 錯誤: "Failed to build 'onnxoptimizer'"

**症狀**:
```
ERROR: Failed to build 'onnxoptimizer' when getting requirements to build wheel
```

**原因**: RKNN Toolkit 2 v2.3.2+ 已修復此問題，通常不會再出現

**解決方案**:
如果升級後仍出現此錯誤，嘗試以下步驟：

```bash
# 升級到最新版本
pip install --upgrade rknn-toolkit2

# 如果仍然失敗，使用 CPU 版本（無 NPU 加速）
pip install onnxruntime
```

### 錯誤: "fatal: not a git repository"

**症狀**:
```
fatal: not a git repository (or any parent up to mount point /)
Stopping at filesystem boundary (GIT_DISCOVERY_ACROSS_FILESYSTEM not set).
```

**原因**: 套件安裝過程中尋找 git 版本信息，但系統不在 git 倉庫中

**解決方案**: 通常可以忽略此警告，它不會影響安裝。如果安裝失敗，執行：

```bash
# 初始化 git（可選）
git init

# 或直接忽略，繼續下一步
pip install rknn_toolkit2-*.whl --no-build-isolation
```

### 錯誤: "No module named 'onnxruntime'"

```bash
pip install ultralytics
```

### 錯誤: "No module named 'torch'"

```bash
# Orange Pi 5 安裝 PyTorch (CPU 版本)
pip install torch torchvision --extra-index-url https://download.pytorch.org/whl/cpu
```

### 攝像頭卡頓或延遲

**原因**: CPU 運算能力不足

**解決方案**:
1. 降低攝像頭解析度到 640x480
2. 降低檢測頻率（不是每幀都檢測）
3. 使用 ONNX 或 RKNN 格式模型

```python
# 降低解析度
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# 跳幀檢測
frame_count = 0
while True:
    ret, frame = cap.read()
    frame_count += 1

    # 每 3 幀才檢測一次
    if frame_count % 3 == 0:
        detections, _ = detector.detect(frame)
```

### 檢測效果不佳

1. **使用蚊子專用模型**: 不要用通用 COCO 模型
2. **改善光線條件**: 確保攝像頭有良好照明（最低 0.5 lux）
3. **調整信心度閾值**: 降低到 0.2-0.3
4. **收集自己的數據**: 在實際環境拍攝並微調模型

---

## 📊 性能比較 (Orange Pi 5)

| 方法 | FPS | 準確度 | NPU | 備註 |
|------|-----|--------|-----|------|
| 運動檢測 | 60+ | 低 | 無 | 舊方法，誤檢多 |
| YOLOv8n (CPU, 640) | 5-8 | 中 | 無 | 太慢 |
| YOLOv8n (CPU, 416) | 10-15 | 中 | 無 | 可接受 |
| YOLOv8n (CPU, 320) | 15-20 | 中 | 無 | **推薦 CPU 方案** |
| YOLOv8n (ONNX, 320) | 18-25 | 中 | 無 | 較快 |
| YOLOv8n (RKNN, 320) | 25-35 | 中 | 是 | **最佳性能** |
| 蚊子專用模型 (RKNN) | 25-35 | 高 | 是 | **最佳方案** |

---

## 🎓 進階主題

### 在 Orange Pi 5 上訓練模型

**不建議**：Orange Pi 5 不適合訓練深度學習模型

**建議方案**：
1. 在有 GPU 的電腦上訓練（NVIDIA GPU）
2. 使用 Google Colab 免費 GPU
3. 使用雲端訓練服務（AWS, GCP, Azure）

### 模型優化流程

```
原始模型 (YOLOv8n PyTorch)
    ↓
剪枝和量化
    ↓
導出為 ONNX (FP16 或 INT8)
    ↓
轉換為 RKNN (INT8 量化)
    ↓
在 Orange Pi 5 NPU 上運行
```

### RKNN 量化範例

```python
from rknn.api import RKNN

# 準備校準數據集
with open('calibration_dataset.txt', 'w') as f:
    for i in range(100):  # 100 張校準圖片
        f.write(f'./calibration_images/img_{i}.jpg\n')

# 轉換和量化
rknn = RKNN()
rknn.config(
    mean_values=[[0, 0, 0]],
    std_values=[[255, 255, 255]],
    target_platform='rk3588',
    quantized_dtype='asymmetric_quantized-8'
)

rknn.load_onnx(model='mosquito_yolov8n.onnx')
rknn.build(do_quantization=True, dataset='./calibration_dataset.txt')
rknn.export_rknn('mosquito_yolov8n_int8.rknn')
rknn.release()
```

### 多執行緒優化

```python
import threading
import queue

detection_queue = queue.Queue(maxsize=2)

def detection_thread():
    """獨立執行緒進行 AI 檢測"""
    while True:
        frame = detection_queue.get()
        if frame is None:
            break
        detections, _ = detector.detect(frame)

thread = threading.Thread(target=detection_thread)
thread.start()
```

---

## 📞 支援和資源

### 官方文檔
- [Orange Pi 5 官方網站](http://www.orangepi.org/)
- [RKNN Toolkit 2 文檔](https://github.com/rockchip-linux/rknn-toolkit2)
- [Ultralytics YOLOv8](https://docs.ultralytics.com/)

### 模型下載站點
- **Roboflow Universe**: https://universe.roboflow.com/
- **Kaggle Datasets**: https://www.kaggle.com/datasets
- **Hugging Face**: https://huggingface.co/models
- **GitHub**: 搜尋 "mosquito detection yolo"

---

## 📄 授權

MIT License

---

**最後更新**: 2025年12月24日
**版本**: 2.2.0 (RKNN Toolkit 2.3.2 版本更新)
**更新內容**: 更新 RKNN Toolkit 2 到 v2.3.2；簡化安裝步驟，改用 `pip install rknn-toolkit2`；移除手動 wheel 下載；更新故障排查指南
