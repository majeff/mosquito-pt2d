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
數據集準備腳本

用途：將收集並標註的樣本轉換為 YOLO 訓練格式
"""

import os
import shutil
import cv2
from pathlib import Path

def prepare_yolo_dataset():
    """
    將收集的樣本轉換為 YOLO 訓練格式
    """
    # 來源目錄
    mosquito_dir = Path('sample_collection/confirmed/mosquito')
    not_mosquito_dir = Path('sample_collection/confirmed/not_mosquito')

    # 目標目錄
    train_img_dir = Path('training_dataset/images/train')
    val_img_dir = Path('training_dataset/images/val')
    train_label_dir = Path('training_dataset/labels/train')
    val_label_dir = Path('training_dataset/labels/val')

    # 建立目錄
    for dir_path in [train_img_dir, val_img_dir, train_label_dir, val_label_dir]:
        dir_path.mkdir(parents=True, exist_ok=True)

    # 檢查來源目錄
    if not mosquito_dir.exists():
        print(f"❌ 找不到蚊子樣本目錄: {mosquito_dir}")
        print("請先執行 label_samples.py 標註樣本")
        return False

    # 處理蚊子樣本
    mosquito_images = list(mosquito_dir.glob('*.jpg'))
    print(f"找到 {len(mosquito_images)} 張蚊子樣本")

    if len(mosquito_images) == 0:
        print("⚠️  沒有蚊子樣本，無法準備數據集")
        return False

    for idx, img_path in enumerate(mosquito_images):
        img = cv2.imread(str(img_path))
        if img is None:
            print(f"⚠️  無法讀取圖片: {img_path}")
            continue

        h, w = img.shape[:2]

        # 80% 訓練，20% 驗證
        is_train = idx < len(mosquito_images) * 0.8
        img_dir = train_img_dir if is_train else val_img_dir
        label_dir = train_label_dir if is_train else val_label_dir

        # 複製圖片
        new_img_name = f"mosquito_{idx:04d}.jpg"
        shutil.copy(img_path, img_dir / new_img_name)

        # 建立標籤檔案（YOLO 格式：class x_center y_center width height）
        # 假設蚊子在圖片中央佔 80% 區域
        label_path = label_dir / f"mosquito_{idx:04d}.txt"
        with open(label_path, 'w') as f:
            # class_id x_center y_center width height（歸一化 0-1）
            f.write("0 0.5 0.5 0.8 0.8\n")  # class 0 = mosquito

    # 處理非蚊子樣本（負樣本）
    not_mosquito_images = list(not_mosquito_dir.glob('*.jpg')) if not_mosquito_dir.exists() else []
    print(f"找到 {len(not_mosquito_images)} 張非蚊子樣本")

    for idx, img_path in enumerate(not_mosquito_images):
        is_train = idx < len(not_mosquito_images) * 0.8
        img_dir = train_img_dir if is_train else val_img_dir
        label_dir = train_label_dir if is_train else val_label_dir

        # 複製圖片
        new_img_name = f"background_{idx:04d}.jpg"
        shutil.copy(img_path, img_dir / new_img_name)

        # 空標籤檔案（背景圖，無物體）
        label_path = label_dir / f"background_{idx:04d}.txt"
        label_path.touch()  # 建立空檔案

    print(f"\n✓ 數據集準備完成！")
    print(f"  訓練集: {len(list(train_img_dir.glob('*.jpg')))} 張")
    print(f"  驗證集: {len(list(val_img_dir.glob('*.jpg')))} 張")

    # 建立數據集配置檔
    create_dataset_yaml()

    return True

def create_dataset_yaml():
    """
    建立 YOLO 數據集配置檔
    """
    yaml_content = """# 蚊子檢測數據集配置
path: training_dataset  # 數據集根目錄
train: images/train     # 訓練圖片目錄（相對路徑）
val: images/val         # 驗證圖片目錄（相對路徑）

# 類別定義
names:
  0: mosquito           # class 0 = 蚊子

# 類別數量
nc: 1
"""

    yaml_path = Path('training_dataset/dataset.yaml')
    with open(yaml_path, 'w', encoding='utf-8') as f:
        f.write(yaml_content)

    print(f"✓ 數據集配置檔已建立: {yaml_path}")

if __name__ == '__main__':
    try:
        success = prepare_yolo_dataset()
        if success:
            print("\n下一步: 執行 train_model.py 開始訓練")
        else:
            print("\n請先收集並標註足夠的樣本")
    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
