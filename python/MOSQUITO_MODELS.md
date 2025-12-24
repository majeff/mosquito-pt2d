# 蚊子檢測模型資源指南

本文檔提供現有蚊子檢測模型的下載來源和使用方法。

## 🔍 快速搜尋指南

### 1. Roboflow Universe（推薦）

**網址**: https://universe.roboflow.com/

**搜尋關鍵字**:
- `mosquito detection`
- `mosquito identification`
- `aedes mosquito`
- `insect detection`

**操作步驟**:
```bash
# 1. 註冊 Roboflow 帳號（免費）
# 2. 搜尋 "mosquito detection"
# 3. 選擇合適的數據集
# 4. 點擊 "Download Dataset" 選擇 YOLOv8 格式
# 5. 使用 API 下載或手動下載

# 使用 Python API 下載
pip install roboflow

python << 'EOF'
from roboflow import Roboflow
rf = Roboflow(api_key="YOUR_API_KEY")  # 從網站獲取
project = rf.workspace("workspace-name").project("project-name")
dataset = project.version(1).download("yolov8")
print(f"數據集已下載到: {dataset.location}")
EOF
```

**推薦項目範例**:
- "Mosquito Detection" by various users
- "Flying Insect Detection"
- "Pest Detection"

---

### 2. Kaggle Datasets

**網址**: https://www.kaggle.com/datasets

**搜尋關鍵字**:
- `mosquito detection dataset`
- `mosquito classification`
- `insect detection yolo`

**操作步驟**:
```bash
# 安裝 Kaggle CLI
pip install kaggle

# 設定 API Token（從 Kaggle 網站下載 kaggle.json）
mkdir -p ~/.kaggle
mv kaggle.json ~/.kaggle/
chmod 600 ~/.kaggle/kaggle.json

# 下載數據集
kaggle datasets download -d [dataset-name]
unzip [dataset-name].zip -d mosquito_data/

# 如果有預訓練模型，直接使用
# 尋找 .pt 或 .onnx 檔案
```

**已知數據集**（需要自行搜尋最新版本）:
- "Mosquito Species Detection Dataset"
- "Aedes Mosquito Detection"
- 搜尋時加上 "yolo" 可找到已訓練的模型

---

### 3. GitHub 開源專案

**網址**: https://github.com/search

**搜尋查詢**:
```
mosquito detection yolo
mosquito tracking deep learning
insect detection pytorch
flying insect recognition
```

**操作步驟**:
```bash
# 範例（需要替換為實際專案）
git clone https://github.com/[username]/mosquito-detection
cd mosquito-detection

# 查看 README 了解如何使用預訓練模型
# 通常在 weights/ 或 models/ 目錄

# 如果提供預訓練模型
cp models/mosquito_yolov8.pt ~/mosquito-pt2d/python/models/
```

**尋找提示**:
- 查看專案的 Stars 數量（> 50 較可靠）
- 檢查最後更新時間（越新越好）
- 閱讀 README 確認是否提供預訓練模型
- 查看 Issues 了解使用問題

---

### 4. Hugging Face Model Hub

**網址**: https://huggingface.co/models

**搜尋關鍵字**:
- `mosquito detection`
- `insect classification`
- `object detection yolo`

**操作步驟**:
```bash
# 安裝 Hugging Face CLI
pip install huggingface_hub

# 下載模型
python << 'EOF'
from huggingface_hub import hf_hub_download

# 下載模型檔案（需要替換為實際模型 ID）
model_path = hf_hub_download(
    repo_id="username/mosquito-detection",
    filename="mosquito_yolov8n.pt"
)
print(f"模型已下載到: {model_path}")
EOF
```

#### 🔄 Adapter 模型轉換（LoRA/Safetensors → RKNN）

如果下載的是 **adapter_model.safetensors**（LoRA 適配器模型），需要額外步驟：

**步驟 1: 合併 Adapter 到基礎模型**

```python
# 安裝必要套件
pip install transformers peft safetensors torch onnx

# merge_adapter.py
import torch
from transformers import AutoModel
from peft import PeftModel
from safetensors.torch import load_file

# 1. 載入基礎模型
base_model_name = "yolov8n"  # 或其他基礎模型
base_model = AutoModel.from_pretrained(base_model_name)

# 2. 載入 adapter 權重
adapter_weights = load_file("models/mosquito.pt")

# 3. 如果是 PEFT/LoRA adapter，合併到基礎模型
if "peft" in str(type(adapter_weights)):
    model = PeftModel.from_pretrained(base_model, "path/to/adapter")
    merged_model = model.merge_and_unload()
else:
    # 手動合併權重
    merged_model = base_model
    merged_model.load_state_dict(adapter_weights, strict=False)

# 4. 儲存完整模型
merged_model.save_pretrained("merged_model")
torch.save(merged_model.state_dict(), "merged_model.pt")
print("✓ Adapter 已合併到基礎模型")
```

**步驟 2: 轉換為 ONNX**

```python
# convert_to_onnx.py
import torch
import torch.onnx
from ultralytics import YOLO

# 方法 1: 如果是 YOLO 模型（推薦）
try:
    model = YOLO("mosquito_yolov8.pt")
    model.export(
        format='onnx',
        imgsz=320,
        opset=12,
        simplify=True,
        dynamic=False  # RKNN 需要固定輸入
    )
    print("✓ 已使用 Ultralytics 轉換為 ONNX")
except Exception as e:
    print(f"Ultralytics 轉換失敗: {e}")
    print("嘗試通用 PyTorch 轉換方法...")

    # 方法 2: 通用 PyTorch 模型轉 ONNX
    # 注意: torch.load() 可能返回 state_dict 或完整模型
    checkpoint = torch.load("models/mosquito.pt", map_location='cpu')

    # 檢查載入的類型
    if isinstance(checkpoint, dict):
        # 如果是字典，需要模型結構
        if 'model' in checkpoint:
            model = checkpoint['model']
        else:
            # 需要先定義模型結構，然後載入權重
            print("✗ 錯誤: 只有權重字典，需要模型結構定義")
            print("建議使用 Ultralytics YOLO 或提供完整的模型文件")
            exit(1)
    else:
        # 直接是模型對象
        model = checkpoint

    model.eval()
    dummy_input = torch.randn(1, 3, 320, 320)

    torch.onnx.export(
        model,
        dummy_input,
        "mosquito.onnx",
        export_params=True,
        opset_version=12,
        do_constant_folding=True,
        input_names=['input'],
        output_names=['output'],
        dynamic_axes=None  # RKNN 需要固定維度
    )
    print("✓ 已轉換為 ONNX")
```

**快速轉換命令（推薦）**:

```python
# 最簡單的方式：使用 Ultralytics YOLO
from ultralytics import YOLO

model = YOLO("models/mosquito.pt")
model.export(format='onnx', imgsz=320)
# 會生成 mosquito.onnx
```

**步驟 3: 轉換為 RKNN**

```python
# convert_safetensors_to_rknn.py
from rknn.api import RKNN
import cv2
import numpy as np

def convert_to_rknn(onnx_path, output_path, calibration_dataset=None):
    """
    將 ONNX 模型轉換為 RKNN (RK3588 NPU)

    Args:
        onnx_path: ONNX 模型路徑
        output_path: 輸出 RKNN 模型路徑
        calibration_dataset: 校準數據集路徑列表檔案
    """
    rknn = RKNN(verbose=True)

    # 1. 配置 RKNN
    print('→ 配置 RKNN...')
    rknn.config(
        mean_values=[[0, 0, 0]],
        std_values=[[255, 255, 255]],
        target_platform='rk3588',
        quantized_dtype='asymmetric_quantized-8',  # INT8 量化
        optimization_level=3,
        output_optimize=1
    )

    # 2. 載入 ONNX
    print(f'→ 載入 ONNX: {onnx_path}')
    ret = rknn.load_onnx(model=onnx_path)
    if ret != 0:
        print('✗ 載入 ONNX 失敗!')
        return False

    # 3. 建立模型（含量化）
    print('→ 建立 RKNN 模型（INT8 量化）...')

    if calibration_dataset:
        # 使用校準數據集進行量化
        ret = rknn.build(
            do_quantization=True,
            dataset=calibration_dataset
        )
    else:
        # 不進行量化（較快但精度可能較低）
        ret = rknn.build(do_quantization=False)

    if ret != 0:
        print('✗ 建立失敗!')
        return False

    # 4. 匯出 RKNN
    print(f'→ 匯出 RKNN: {output_path}')
    ret = rknn.export_rknn("mosquito_yolov8.rknn")
    if ret != 0:
        print('✗ 匯出失敗!')
        return False

    # 5. 測試推理
    print('→ 測試推理速度...')
    ret = rknn.init_runtime()
    if ret != 0:
        print('✗ 初始化執行環境失敗!')
        return False

    # 測試圖片
    test_img = np.random.randint(0, 255, (320, 320, 3), dtype=np.uint8)

    import time
    times = []
    for i in range(10):
        start = time.time()
        outputs = rknn.inference(inputs=[test_img])
        elapsed = time.time() - start
        times.append(elapsed)

    avg_time = np.mean(times[1:])  # 排除第一次
    fps = 1.0 / avg_time

    print(f'✓ 平均推理時間: {avg_time*1000:.2f}ms ({fps:.1f} FPS)')
    print(f'✓ 輸出形狀: {[out.shape for out in outputs]}')

    rknn.release()
    print(f'\n✓ RKNN 模型已準備就緒: {output_path}')
    return True

# 執行轉換
if __name__ == "__main__":
    # 準備校準數據集（可選但建議）
    import glob
    calibration_images = glob.glob("calibration_images/*.jpg")[:100]

    if calibration_images:
        with open("calibration_dataset.txt", "w") as f:
            for img in calibration_images:
                f.write(f"{img}\n")
        calibration_dataset = "calibration_dataset.txt"
    else:
        print("⚠️  未提供校準數據集，將不進行 INT8 量化")
        calibration_dataset = None

    # 轉換
    success = convert_to_rknn(
        onnx_path="merged_model.onnx",
        output_path="mosquito_yolov8n.rknn",
        calibration_dataset=calibration_dataset
    )

    if success:
        print("\n🎉 轉換完成！")
        print("使用方法: 在 Python 中使用 rknnlite 載入此模型")
```

**完整轉換流程**:

```bash
# 1. 下載 Hugging Face 模型
python << 'EOF'
from huggingface_hub import hf_hub_download
adapter_path = hf_hub_download(
    repo_id="username/mosquito-model",
    filename="adapter_model.safetensors"
)
print(f"下載至: {adapter_path}")
EOF

# 2. 合併 adapter 到基礎模型
python merge_adapter.py

# 3. 轉換為 ONNX
python convert_to_onnx.py

# 4. (可選) 準備校準數據集
mkdir -p calibration_images
# 複製 100-200 張蚊子圖片到此目錄

# 5. 轉換為 RKNN
python convert_safetensors_to_rknn.py

# 6. 測試 RKNN 模型
python test_rknn_model.py
```

**使用 RKNN 模型**:

```python
# 在 mosquito_detector.py 中使用 RKNN
from rknnlite.api import RKNNLite

class MosquitoDetectorRKNN:
    def __init__(self, rknn_model_path='mosquito_yolov8n.rknn'):
        self.rknn = RKNNLite()

        # 載入 RKNN 模型
        ret = self.rknn.load_rknn(rknn_model_path)
        if ret != 0:
            raise RuntimeError('載入 RKNN 模型失敗')

        # 初始化執行環境（使用 NPU）
        ret = self.rknn.init_runtime(core_mask=RKNNLite.NPU_CORE_0)
        if ret != 0:
            raise RuntimeError('初始化 RKNN 執行環境失敗')

        print('✓ RKNN NPU 模型已載入')

    def detect(self, frame):
        # 預處理
        img = cv2.resize(frame, (320, 320))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # NPU 推理
        outputs = self.rknn.inference(inputs=[img])

        # 後處理（解析 YOLO 輸出）
        detections = self.parse_yolo_outputs(outputs)

        return detections
```

**注意事項**:

1. **Adapter 類型**: 確認是 LoRA、QLoRA 還是其他類型的 adapter
2. **基礎模型**: 必須知道 adapter 對應的基礎模型版本
3. **輸入形狀**: RKNN 需要固定輸入維度，不支援 dynamic axes
4. **量化**: INT8 量化需要校準數據集（100+ 張圖片）
5. **NPU 限制**: 某些操作可能不支援，需要回退到 CPU

**故障排除**:

```bash
# 檢查 ONNX 模型
pip install onnx
python -c "import onnx; model = onnx.load('merged_model.onnx'); onnx.checker.check_model(model); print('✓ ONNX 模型有效')"

# 檢查 RKNN Toolkit 版本
python -c "from rknn.api import RKNN; print(RKNN().get_sdk_version())"

# 測試 NPU 可用性
python -c "from rknnlite.api import RKNNLite; rknn = RKNNLite(); print('✓ NPU 可用')"
```

---

### 5. Papers with Code

**網址**: https://paperswithcode.com/

**搜尋關鍵字**:
- `mosquito detection`
- `insect detection`

**特點**:
- 學術論文 + 開源實作
- 可以找到最新研究成果
- 通常包含 GitHub 連結和模型下載

---

## 📥 模型下載檢查清單

下載模型時確認以下資訊：

### ✅ 必要資訊
- [ ] 模型格式: `.pt` (PyTorch), `.onnx` (ONNX), `.rknn` (NPU)
- [ ] 輸入解析度: 建議 320x320 或 416x416
- [ ] 類別數量: 確認是否只檢測蚊子
- [ ] 模型大小: < 20MB 適合 Orange Pi 5

### ✅ 性能指標
- [ ] mAP (Mean Average Precision): > 0.6
- [ ] FPS 資訊（在類似硬體上）
- [ ] 訓練數據集大小: > 500 張圖片

### ✅ 相容性
- [ ] 框架版本: YOLOv5, YOLOv8, YOLOv9
- [ ] 是否可轉換為 ONNX
- [ ] 是否提供轉換腳本

---

## 🔧 下載後的使用方法

### 方法 1: 直接使用 PyTorch 模型

```python
from mosquito_detector import MosquitoDetector

# 使用下載的模型
detector = MosquitoDetector(
    model_path='models/mosquito_yolov8n.pt',
    confidence_threshold=0.3,
    imgsz=320  # Orange Pi 5 建議使用 320
)

# 測試
import cv2
frame = cv2.imread('test_image.jpg')
detections, _ = detector.detect(frame)
print(f"檢測到 {len(detections)} 隻蚊子")
```

### 方法 2: 轉換為 ONNX（提升速度）

```bash
# 安裝轉換工具
pip install ultralytics

# 轉換模型
python << 'EOF'
from ultralytics import YOLO

# 載入 PyTorch 模型
model = YOLO('models/mosquito_yolov8n.pt')

# 匯出為 ONNX
model.export(
    format='onnx',
    imgsz=320,  # 輸入解析度
    opset=12,
    simplify=True
)
print("ONNX 模型已生成")
EOF

# 使用 ONNX 模型
# 修改 mosquito_detector.py 以支援 ONNX Runtime
```

### 方法 3: 轉換為 RKNN（NPU 加速）

```bash
# 需要 RKNN Toolkit 2
# 從官方下載: https://github.com/rockchip-linux/rknn-toolkit2

# 1. 先轉換為 ONNX（見方法 2）

# 2. 準備校準數據集
mkdir -p calibration_images
# 複製 100 張蚊子圖片到此目錄

# 3. 建立校準列表
ls calibration_images/*.jpg > calibration_dataset.txt

# 4. 轉換為 RKNN
python convert_to_rknn.py
```

**convert_to_rknn.py**:
```python
from rknn.api import RKNN

rknn = RKNN()

# 配置
print('配置 RKNN...')
rknn.config(
    mean_values=[[0, 0, 0]],
    std_values=[[255, 255, 255]],
    target_platform='rk3588',
    quantized_dtype='asymmetric_quantized-8',
    optimization_level=3
)

# 載入 ONNX
print('載入 ONNX 模型...')
ret = rknn.load_onnx(model='mosquito_yolov8n.onnx')
if ret != 0:
    print('載入失敗!')
    exit(ret)

# 建立並量化
print('建立 RKNN 模型（含 INT8 量化）...')
ret = rknn.build(
    do_quantization=True,
    dataset='calibration_dataset.txt'
)
if ret != 0:
    print('建立失敗!')
    exit(ret)

# 匯出
print('匯出 RKNN 模型...')
ret = rknn.export_rknn('mosquito_yolov8n.rknn')

# 測試推理速度
print('初始化執行環境...')
ret = rknn.init_runtime()
if ret != 0:
    print('初始化失敗!')
    exit(ret)

# 測試推理
import cv2
import numpy as np

img = cv2.imread('test_image.jpg')
img = cv2.resize(img, (320, 320))
img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

print('執行推理測試...')
outputs = rknn.inference(inputs=[img])
print(f'輸出形狀: {[out.shape for out in outputs]}')

rknn.release()
print('✓ RKNN 模型已準備就緒！')
```

---

## 📊 模型評估

下載模型後，建議進行評估：

```python
import cv2
from mosquito_detector import MosquitoDetector
import time

detector = MosquitoDetector(model_path='models/mosquito_yolov8n.pt')

# 測試圖片
test_images = ['test1.jpg', 'test2.jpg', 'test3.jpg']

total_time = 0
total_detections = 0

for img_path in test_images:
    frame = cv2.imread(img_path)

    start = time.time()
    detections, _ = detector.detect(frame)
    elapsed = time.time() - start

    total_time += elapsed
    total_detections += len(detections)

    print(f"{img_path}: {len(detections)} 檢測, {elapsed*1000:.1f}ms")

avg_time = total_time / len(test_images)
fps = 1.0 / avg_time

print(f"\n平均: {avg_time*1000:.1f}ms, {fps:.1f} FPS")
print(f"總檢測數: {total_detections}")
```

---

## 🎯 模型選擇建議

### 初學者
1. 從 Roboflow 下載公開數據集
2. 使用其預訓練的 YOLOv8n 模型
3. 直接測試效果

### 進階使用者
1. 收集自己環境的蚊子影像
2. 使用公開數據集做預訓練
3. 在自己的數據上微調（Fine-tune）
4. 轉換為 ONNX/RKNN 優化性能

### Orange Pi 5 最佳化
1. 使用 YOLOv8n（最小版本）
2. 輸入解析度設為 320x320
3. 轉換為 RKNN 使用 NPU
4. 目標：25-30 FPS

---

## 🆘 常見問題

### Q: 找不到蚊子專用模型？
**A**: 可以使用 "insect detection" 模型，然後篩選小型物體

### Q: 模型檔案太大（> 50MB）？
**A**: 使用 YOLOv8n 而非 YOLOv8m/l/x，或進行模型剪枝

### Q: 下載的模型格式不相容？
**A**: 使用 YOLO export 功能轉換格式

### Q: 模型準確度不佳？
**A**: 收集實際環境照片，進行遷移學習（Transfer Learning）

### Q: 推理速度太慢？
**A**:
1. 降低輸入解析度到 320x320
2. 轉換為 ONNX 格式
3. 使用 RKNN NPU 加速
4. 每 N 幀才檢測一次

---

## 📞 需要幫助？

如果無法找到合適的模型：

1. **在專案 GitHub 開 Issue**
2. **社群論壇**: Orange Pi 論壇、Reddit r/computervision
3. **自己訓練**: 使用 Google Colab 免費 GPU

---

**最後更新**: 2025年12月23日
