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
模型訓練腳本

用途：使用收集的樣本微調現有蚊子檢測模型
"""

from ultralytics import YOLO
import torch
from pathlib import Path

def fine_tune_model():
    """
    使用收集的樣本微調現有模型
    """
    # 檢查數據集
    dataset_yaml = Path('training_dataset/dataset.yaml')
    if not dataset_yaml.exists():
        print("❌ 找不到數據集配置: training_dataset/dataset.yaml")
        print("請先執行 prepare_dataset.py")
        return None

    # 檢查模型
    model_path = Path('models/mosquito_yolov8.pt')
    if not model_path.exists():
        print("❌ 找不到預訓練模型: models/mosquito_yolov8.pt")
        return None

    # 載入現有模型
    print(f"載入預訓練模型: {model_path}")
    model = YOLO(str(model_path))

    # 訓練配置
    print("\n開始訓練...")
    results = model.train(
        data=str(dataset_yaml),       # 數據集配置
        epochs=50,                    # 訓練輪數（樣本少用 50-100）
        imgsz=320,                    # 輸入解析度
        batch=16,                     # 批次大小（依 GPU 記憶體調整）
        device=0 if torch.cuda.is_available() else 'cpu',  # GPU/CPU

        # 微調參數
        lr0=0.001,                    # 初始學習率（較小，避免過度調整）
        lrf=0.01,                     # 最終學習率
        momentum=0.937,               # 動量
        weight_decay=0.0005,          # 權重衰減

        # 數據增強（增加樣本多樣性）
        hsv_h=0.015,                  # 色調增強
        hsv_s=0.7,                    # 飽和度增強
        hsv_v=0.4,                    # 明度增強
        degrees=10.0,                 # 旋轉角度
        translate=0.1,                # 平移
        scale=0.5,                    # 縮放
        flipud=0.5,                   # 垂直翻轉機率
        fliplr=0.5,                   # 水平翻轉機率
        mosaic=1.0,                   # Mosaic 增強

        # 其他設定
        patience=20,                  # 早停耐心值
        save=True,                    # 保存最佳模型
        save_period=10,               # 每 N 輪保存一次
        project='training_runs',      # 專案目錄
        name='mosquito_finetune',     # 訓練名稱
        exist_ok=True,                # 覆蓋現有專案

        # 驗證
        val=True,                     # 啟用驗證
        plots=True,                   # 生成訓練圖表
        verbose=True                  # 詳細輸出
    )

    # 訓練結果
    print("\n" + "="*50)
    print("訓練完成！")
    print("="*50)
    print(f"最佳模型: {results.save_dir / 'weights' / 'best.pt'}")
    print(f"最終模型: {results.save_dir / 'weights' / 'last.pt'}")
    print(f"訓練圖表: {results.save_dir}")

    # 顯示關鍵指標
    if hasattr(results, 'results_dict'):
        metrics = results.results_dict
        print("\n關鍵指標:")
        print(f"  mAP50: {metrics.get('metrics/mAP50(B)', 'N/A')}")
        print(f"  mAP50-95: {metrics.get('metrics/mAP50-95(B)', 'N/A')}")
        print(f"  Precision: {metrics.get('metrics/precision(B)', 'N/A')}")
        print(f"  Recall: {metrics.get('metrics/recall(B)', 'N/A')}")

    print("\n下一步:")
    print("  1. 執行 evaluate_model.py 評估新模型")
    print("  2. 執行 compare_models.py 比較新舊模型")

    return results

if __name__ == '__main__':
    # 檢查 GPU
    if torch.cuda.is_available():
        print(f"✓ 使用 GPU: {torch.cuda.get_device_name(0)}")
        print(f"  GPU 記憶體: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
    else:
        print("⚠️  使用 CPU 訓練（速度較慢）")
        print("建議使用 GPU 以加快訓練速度")

    try:
        # 開始訓練
        results = fine_tune_model()

        if results is None:
            print("\n❌ 訓練失敗")
            exit(1)

    except KeyboardInterrupt:
        print("\n\n⊗ 訓練被中斷")
    except Exception as e:
        print(f"\n❌ 訓練錯誤: {e}")
        import traceback
        traceback.print_exc()
