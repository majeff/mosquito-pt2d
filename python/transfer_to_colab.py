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

"""
轉移至 Colab 訓練環境腳本

用途：將已確認的蚊子樣本轉移到 Colab 訓練環境所需的目錄結構（僅包含蚊子類別）
"""

import os
import shutil
import random
from pathlib import Path
from datetime import datetime
from config_loader import config


def transfer_to_colab():
    """
    將已標註的蚊子樣本轉移到 Colab 訓練環境
    """
    # 使用配置加載器獲取 Colab 目錄
    colab_dir = Path(config.COLAB_NOTEBOOK_DEST_DIR)
    
    # 手動構造正確的路徑
    project_root = Path(__file__).resolve().parent.parent
    mosquito_dir = project_root / "sample_collection" / "confirmed" / "mosquito"

    # 檢查目錄是否存在
    if not os.path.exists(mosquito_dir):
        print(f"❌ 蚊子樣本目錄不存在: {mosquito_dir}")
        return

    # 統計當前蚊子樣本與標籤文件數量
    mosquito_files = [f for f in os.listdir(mosquito_dir) if f.endswith('.jpg') or f.endswith('.jpeg') or f.endswith('.png')]

    # 統計標籤文件
    mosquito_labels = len([f for f in os.listdir(mosquito_dir) if f.endswith('.txt')])

    total_count = len(mosquito_files)

    if total_count == 0:
        print("⚠️  沒有蚊子樣本可轉移")
        return

    print(f"\n📦 準備轉移 {total_count} 張蚊子樣本到 Colab 訓練環境:")
    print(f"   - 蚊子樣本: {len(mosquito_files)} 張 (標籤: {mosquito_labels} 個)")
    print(f"\n⚠️  轉移時將:")
    print(f"   1. 創建訓練數據集結構: training_dataset/images/(train|val)/ + labels/(train|val)/")
    print(f"   2. 進行 80/20 隨機分割")
    print(f"   3. 同步複製所有 YOLO 標籤文件並確保類別 ID 為 0")
    print(f"   4. 生成 dataset.yaml 配置文件")
    print(f"   5. 複製到 Colab 目錄: {colab_dir}/")

    confirm = input("\n確認轉移？(y/n): ").lower().strip()

    if confirm != 'y':
        print("已取消轉移")
        return

    # 建立 Colab 目錄結構
    os.makedirs(colab_dir, exist_ok=True)

    # 訓練數據集目錄結構
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    training_dataset_dir = colab_dir / f"training_dataset_{timestamp}"
    os.makedirs(training_dataset_dir / "images" / "train", exist_ok=True)
    os.makedirs(training_dataset_dir / "images" / "val", exist_ok=True)
    os.makedirs(training_dataset_dir / "labels" / "train", exist_ok=True)
    os.makedirs(training_dataset_dir / "labels" / "val", exist_ok=True)

    # 準備所有蚊子樣本（準備進行 80/20 分割）
    all_mosquito_entries = []
    for img_file in mosquito_files:
        img_base = os.path.splitext(img_file)[0]
        all_mosquito_entries.append({
            'img': img_file,
            'img_src': mosquito_dir / img_file,
            'label_src': mosquito_dir / f"{img_base}.txt",
            'label_exists': (mosquito_dir / f"{img_base}.txt").exists()
        })

    # 隨機分割蚊子樣本：80% train, 20% val
    random.seed(42)  # 固定種子保證可重現性
    random.shuffle(all_mosquito_entries)
    split_idx_mosquito = int(len(all_mosquito_entries) * 0.8)
    train_mosquito_entries = all_mosquito_entries[:split_idx_mosquito]
    val_mosquito_entries = all_mosquito_entries[split_idx_mosquito:]

    # 處理蚊子樣本的訓練集
    train_mosquito_count = 0
    for entry in train_mosquito_entries:
        img_base = os.path.splitext(entry['img'])[0]
        # 複製圖片到訓練目錄
        img_dst = training_dataset_dir / "images" / "train" / entry['img']
        shutil.copy2(entry['img_src'], img_dst)

        # 處理標籤文件
        if entry['label_exists']:
            label_dst = training_dataset_dir / "labels" / "train" / f"{img_base}.txt"
            with open(entry['label_src'], 'r') as f:
                lines = f.readlines()

            # 確保第一碼是 0（蚊子類別 ID）
            fixed_lines = []
            for line in lines:
                parts = line.strip().split()
                if parts:
                    parts[0] = '0'  # 蚊子類別 ID 為 0
                    fixed_lines.append(' '.join(parts) + '\n')

            with open(label_dst, 'w') as f:
                f.writelines(fixed_lines)
        else:
            # 生成預設全圖標籤
            label_dst = training_dataset_dir / "labels" / "train" / f"{img_base}.txt"
            with open(label_dst, 'w') as f:
                f.write('0 0.5 0.5 1.0 1.0\n')

        train_mosquito_count += 1

    # 處理蚊子樣本的驗證集
    val_mosquito_count = 0
    for entry in val_mosquito_entries:
        img_base = os.path.splitext(entry['img'])[0]
        # 複製圖片到驗證目錄
        img_dst = training_dataset_dir / "images" / "val" / entry['img']
        shutil.copy2(entry['img_src'], img_dst)

        # 處理標籤文件
        if entry['label_exists']:
            label_dst = training_dataset_dir / "labels" / "val" / f"{img_base}.txt"
            with open(entry['label_src'], 'r') as f:
                lines = f.readlines()

            # 確保第一碼是 0（蚊子類別 ID）
            fixed_lines = []
            for line in lines:
                parts = line.strip().split()
                if parts:
                    parts[0] = '0'  # 蚊子類別 ID 為 0
                    fixed_lines.append(' '.join(parts) + '\n')

            with open(label_dst, 'w') as f:
                f.writelines(fixed_lines)
        else:
            # 生成預設全圖標籤
            label_dst = training_dataset_dir / "labels" / "val" / f"{img_base}.txt"
            with open(label_dst, 'w') as f:
                f.write('0 0.5 0.5 1.0 1.0\n')

        val_mosquito_count += 1

    # 生成 dataset.yaml（僅包含 mosquito 類別）
    yaml_content = f"""path: {training_dataset_dir}
train: images/train
val: images/val
names:
  0: mosquito
nc: 1
"""
    yaml_path = training_dataset_dir / "dataset.yaml"
    with open(yaml_path, 'w') as f:
        f.write(yaml_content)

    total_train = train_mosquito_count
    total_val = val_mosquito_count

    print(f"\n✓ 成功轉移並準備 Colab 訓練數據集:")
    print(f"   Colab目錄: {colab_dir}/")
    print(f"\n📊 訓練數據分割:")
    print(f"   訓練集: {total_train} 張 (蚊子)")
    print(f"   驗證集: {total_val} 張 (蚊子)")
    print(f"\n📁 訓練數據集位置:")
    print(f"   {training_dataset_dir}/")
    print(f"✓ 已生成 dataset.yaml: {yaml_path}")
    print(f"\n💡 下一步: 訓練數據集已複製到 {colab_dir}，可以上傳到 Google Drive 在 Colab 中進行蚊子檢測訓練")
    print(f"💡 提示: 已保留原始樣本目錄，不會影響已標註數據")


if __name__ == '__main__':
    transfer_to_colab()