#!/usr/bin/env python3
# Copyright 2025 Arduino PT2D Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#!/usr/bin/env python3
"""
模型評估腳本

用途：評估訓練後模型在驗證集上的表現
"""

from ultralytics import YOLO
from pathlib import Path
import json

def evaluate_model(model_path='training_runs/mosquito_finetune/weights/best.pt',
                   dataset_yaml='training_dataset/dataset.yaml'):
    """
    評估模型性能

    Args:
        model_path: 模型檔案路徑
        dataset_yaml: 數據集配置檔案
    """
    # 檢查檔案
    model_path = Path(model_path)
    dataset_yaml = Path(dataset_yaml)

    if not model_path.exists():
        print(f"❌ 找不到模型: {model_path}")
        print("\n可用的模型:")
        for p in Path('training_runs').rglob('*/weights/best.pt'):
            print(f"  - {p}")
        return None

    if not dataset_yaml.exists():
        print(f"❌ 找不到數據集配置: {dataset_yaml}")
        return None

    # 載入模型
    print(f"載入模型: {model_path}")
    model = YOLO(str(model_path))

    # 驗證模型
    print("\n開始評估...")
    results = model.val(
        data=str(dataset_yaml),
        imgsz=320,
        batch=16,
        conf=0.25,           # 信心度閾值
        iou=0.6,             # NMS IoU 閾值
        plots=True,          # 生成評估圖表
        save_json=True,      # 保存 JSON 結果
        verbose=True
    )

    # 顯示結果
    print("\n" + "="*50)
    print("評估結果")
    print("="*50)

    # 基本指標
    print("\n整體性能:")
    print(f"  mAP50: {results.box.map50:.4f}")
    print(f"  mAP50-95: {results.box.map:.4f}")
    print(f"  Precision: {results.box.mp:.4f}")
    print(f"  Recall: {results.box.mr:.4f}")

    # 每類指標
    if hasattr(results.box, 'ap_class_index'):
        print("\n各類別性能:")
        for i, class_idx in enumerate(results.box.ap_class_index):
            class_name = model.names[int(class_idx)]
            ap50 = results.box.ap50[i]
            ap = results.box.ap[i]
            print(f"  {class_name}:")
            print(f"    AP50: {ap50:.4f}")
            print(f"    AP50-95: {ap:.4f}")

    # 速度指標
    print("\n推理速度:")
    print(f"  預處理: {results.speed['preprocess']:.2f} ms")
    print(f"  推理: {results.speed['inference']:.2f} ms")
    print(f"  後處理: {results.speed['postprocess']:.2f} ms")
    total_time = sum(results.speed.values())
    print(f"  總計: {total_time:.2f} ms ({1000/total_time:.1f} FPS)")

    # 保存詳細結果
    results_dir = model_path.parent.parent / 'evaluation'
    results_dir.mkdir(exist_ok=True)

    results_file = results_dir / 'evaluation_results.json'
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump({
            'model': str(model_path),
            'dataset': str(dataset_yaml),
            'metrics': {
                'mAP50': float(results.box.map50),
                'mAP50-95': float(results.box.map),
                'precision': float(results.box.mp),
                'recall': float(results.box.mr),
            },
            'speed': results.speed
        }, f, indent=2, ensure_ascii=False)

    print(f"\n詳細結果已保存到: {results_file}")

    # 建議
    print("\n建議:")
    if results.box.map50 < 0.5:
        print("  ⚠️  mAP50 較低，建議:")
        print("     - 收集更多樣本")
        print("     - 檢查標註品質")
        print("     - 增加訓練輪數")
    elif results.box.map50 > 0.9:
        print("  ✓ 模型性能優秀！")
    else:
        print("  ✓ 模型性能良好")

    if results.box.mp < results.box.mr:
        print("  ⚠️  精確率 < 召回率：模型產生較多誤檢")
        print("     建議提高信心度閾值")
    elif results.box.mp > results.box.mr + 0.1:
        print("  ⚠️  精確率 >> 召回率：模型可能漏檢")
        print("     建議降低信心度閾值或收集更多樣本")

    return results

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='評估 YOLOv8 模型')
    parser.add_argument('--model', type=str,
                       default='training_runs/mosquito_finetune/weights/best.pt',
                       help='模型路徑')
    parser.add_argument('--data', type=str,
                       default='training_dataset/dataset.yaml',
                       help='數據集配置')

    args = parser.parse_args()

    try:
        evaluate_model(args.model, args.data)
    except Exception as e:
        print(f"\n❌ 評估錯誤: {e}")
        import traceback
        traceback.print_exc()
