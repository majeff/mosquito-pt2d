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
樣本標註輔助腳本

用途：輔助人工標註中等信心度樣本，將樣本分類為「蚊子」或「非蚊子」
支援功能：標註、統計、搬遷備份
"""

import os
import shutil
from PIL import Image
from pathlib import Path
from datetime import datetime
from config_loader import config

def label_samples():
    """
    互動式標註樣本（同時處理中/高信心度來源）
    """
    # 從 config 讀取目錄設定
    medium_dir = config.MEDIUM_CONFIDENCE_DIR
    high_dir = config.HIGH_CONFIDENCE_DIR
    mosquito_dir = config.CONFIRMED_MOSQUITO_DIR
    not_mosquito_dir = config.CONFIRMED_NOT_MOSQUITO_DIR

    # 確保來源目錄存在（若不存在則建立並提示）
    created = []
    for d in [medium_dir, high_dir]:
        if not os.path.exists(d):
            os.makedirs(d, exist_ok=True)
            created.append(d)
    if created:
        print(f"📂 已建立目錄: {', '.join(created)}，請放入待標註樣本（.jpg）")

    # 建立目錄
    os.makedirs(mosquito_dir, exist_ok=True)
    os.makedirs(not_mosquito_dir, exist_ok=True)

    # 彙整來源目錄（存在者）
    sources = []
    if os.path.exists(medium_dir):
        sources.append(medium_dir)
    if os.path.exists(high_dir):
        sources.append(high_dir)

    if not sources:
        print(f"❌ 找不到樣本目錄: {medium_dir} 或 {high_dir}")
        return

    # 獲取所有圖片（來源 + 檔名）
    images = []  # [(src_dir, filename)]
    for src in sources:
        for f in os.listdir(src):
            if f.endswith('.jpg'):
                images.append((src, f))

    if not images:
        print("⚠️  沒有待標註的樣本")
        return

    print(f"找到 {len(images)} 張待標註樣本（來源: {', '.join(sources)}）\n")
    print("操作說明:")
    print("  y - 確認是蚊子")
    print("  n - 確認不是蚊子")
    print("  d - 刪除此樣本")
    print("  s - 顯示統計資訊")
    print("  m - 搬遷已標註樣本")
    print("  q - 退出標註\n")

    # 逐一標註
    labeled_count = 0
    deleted_count = 0

    for idx, item in enumerate(images, 1):
        src_dir, img_file = item
        img_path = os.path.join(src_dir, img_file)

        rel = os.path.relpath(img_path, start=os.path.commonprefix(sources))
        print(f"\n[{idx}/{len(images)}] {rel}")

        # 顯示圖片
        try:
            img = Image.open(img_path)
            img.show()
        except Exception as e:
            print(f"⚠️  無法顯示圖片: {e}")

        # 詢問用戶
        while True:
            choice = input("是蚊子嗎？(y/n/d/s/m/q): ").lower().strip()

            if choice == 'y':
                # 移動圖片並同步移動對應的 YOLO 標籤文件
                shutil.move(img_path, os.path.join(mosquito_dir, img_file))
                _move_label_file(src_dir, img_file, mosquito_dir)
                print(f"✓ 移動到 mosquito/")
                labeled_count += 1
                break
            elif choice == 'n':
                shutil.move(img_path, os.path.join(not_mosquito_dir, img_file))
                _move_label_file(src_dir, img_file, not_mosquito_dir)
                print(f"✓ 移動到 not_mosquito/")
                labeled_count += 1
                break
            elif choice == 'd':
                os.remove(img_path)
                _delete_label_file(src_dir, img_file)
                print(f"🗑️ 已刪除")
                deleted_count += 1
                break
            elif choice == 's':
                print_statistics(mosquito_dir, not_mosquito_dir, sources)
                continue  # 顯示統計後繼續當前圖片
            elif choice == 'm':
                relocate_samples()
                continue  # 搬遷後繼續當前圖片
            elif choice == 'q':
                print("\n退出標註")
                print_statistics(mosquito_dir, not_mosquito_dir, sources)
                return
            else:
                print("無效輸入，請輸入 y/n/d/s/m/q")

    print("\n✓ 標註完成！")
    print_statistics(mosquito_dir, not_mosquito_dir, sources)

def _move_label_file(src_dir, img_file, dst_dir):
    """
    同步移動 YOLO 標籤文件 (.txt) 並驗證類別 ID
    """
    img_base = os.path.splitext(img_file)[0]
    label_src = os.path.join(src_dir, img_base + '.txt')
    label_dst = os.path.join(dst_dir, img_base + '.txt')

    if os.path.exists(label_src):
        # 讀取並驗證標籤內容
        try:
            with open(label_src, 'r') as f:
                lines = f.readlines()

            # 確保第一碼是 0（蚊子類別 ID）
            fixed_lines = []
            for line in lines:
                parts = line.strip().split()
                if parts:
                    parts[0] = '0'  # 確保類別 ID 為 0
                    fixed_lines.append(' '.join(parts) + '\n')

            # 寫入目標位置
            os.makedirs(dst_dir, exist_ok=True)
            with open(label_dst, 'w') as f:
                f.writelines(fixed_lines)
            print(f"  ✓ 標籤文件已同步 ({img_base}.txt)")
        except Exception as e:
            print(f"  ⚠️ 標籤文件處理失敗: {e}")
    else:
        print(f"  ⚠️ 找不到標籤文件: {img_base}.txt")

def _delete_label_file(src_dir, img_file):
    """
    刪除對應的 YOLO 標籤文件
    """
    img_base = os.path.splitext(img_file)[0]
    label_src = os.path.join(src_dir, img_base + '.txt')

    if os.path.exists(label_src):
        try:
            os.remove(label_src)
        except Exception as e:
            print(f"  ⚠️ 標籤文件刪除失敗: {e}")

def print_statistics(mosquito_dir, not_mosquito_dir, sources):
    """
    顯示統計資訊（來源可為多個目錄）
    """
    mosquito_count = len([f for f in os.listdir(mosquito_dir) if f.endswith('.jpg')]) if os.path.exists(mosquito_dir) else 0
    not_mosquito_count = len([f for f in os.listdir(not_mosquito_dir) if f.endswith('.jpg')]) if os.path.exists(not_mosquito_dir) else 0
    remaining_count = 0
    for src in sources:
        if os.path.exists(src):
            remaining_count += len([f for f in os.listdir(src) if f.endswith('.jpg')])

    print("\n" + "="*50)
    print("📊 樣本統計")
    print("="*50)
    print(f"✓ 蚊子樣本: {mosquito_count} 張")
    print(f"✗ 非蚊子樣本: {not_mosquito_count} 張")
    print(f"⏳ 待標註樣本: {remaining_count} 張（來源: {', '.join(sources)}）")
    print(f"📦 總計: {mosquito_count + not_mosquito_count + remaining_count} 張")
    print("="*50)

def relocate_samples():
    """
    搬遷已標註樣本到備份目錄
    用於訓練完成後清理樣本或備份歷史數據
    """
    mosquito_dir = config.CONFIRMED_MOSQUITO_DIR
    not_mosquito_dir = config.CONFIRMED_NOT_MOSQUITO_DIR
    reloc_mosquito_dir = config.RELOCATION_MOSQUITO_DIR
    reloc_not_mosquito_dir = config.RELOCATION_NOT_MOSQUITO_DIR

    # 統計當前樣本與標籤文件數量
    mosquito_files = [f for f in os.listdir(mosquito_dir) if f.endswith('.jpg')] if os.path.exists(mosquito_dir) else []
    not_mosquito_files = [f for f in os.listdir(not_mosquito_dir) if f.endswith('.jpg')] if os.path.exists(not_mosquito_dir) else []

    # 統計標籤文件
    mosquito_labels = len([f for f in os.listdir(mosquito_dir) if f.endswith('.txt')]) if os.path.exists(mosquito_dir) else 0
    not_mosquito_labels = len([f for f in os.listdir(not_mosquito_dir) if f.endswith('.txt')]) if os.path.exists(not_mosquito_dir) else 0

    total_count = len(mosquito_files) + len(not_mosquito_files)

    if total_count == 0:
        print("⚠️  沒有已標註的樣本可搬遷")
        return

    print(f"\n📦 準備搬遷 {total_count} 張已標註樣本到 Colab 訓練環境:")
    print(f"   - 蚊子樣本: {len(mosquito_files)} 張 (標籤: {mosquito_labels} 個)")
    print(f"   - 非蚊子樣本: {len(not_mosquito_files)} 張 (標籤: {not_mosquito_labels} 個)")
    print(f"\n⚠️  搬遷時將:")
    print(f"   1. 創建訓練數據集結構: training_dataset/images/(train|val)/ + labels/(train|val)/")
    print(f"   2. 進行 80/20 隨機分割")
    print(f"   3. 同步移動所有 YOLO 標籤文件並驗證類別 ID")
    print(f"   4. 生成 dataset.yaml 配置文件")
    print(f"   5. 備份到時間戳記目錄: {config.RELOCATION_BASE_DIR}/<TIMESTAMP>/")

    confirm = input("\n確認搬遷？(y/n): ").lower().strip()

    if confirm != 'y':
        print("已取消搬遷")
        return

    import random

    # 建立搬遷目錄（使用時間戳記）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # 基底目錄：sample_collection/relocated/<timestamp>
    reloc_base_timestamped = os.path.join(config.RELOCATION_BASE_DIR, timestamp)
    os.makedirs(reloc_base_timestamped, exist_ok=True)

    # 訓練數據集目錄結構
    training_dataset_dir = os.path.join(reloc_base_timestamped, "training_dataset")
    os.makedirs(os.path.join(training_dataset_dir, "images", "train"), exist_ok=True)
    os.makedirs(os.path.join(training_dataset_dir, "images", "val"), exist_ok=True)
    os.makedirs(os.path.join(training_dataset_dir, "labels", "train"), exist_ok=True)
    os.makedirs(os.path.join(training_dataset_dir, "labels", "val"), exist_ok=True)

    # 備份目錄（歷史記錄）
    reloc_mosquito_timestamped = os.path.join(reloc_base_timestamped, "backup", "mosquito")
    reloc_not_mosquito_timestamped = os.path.join(reloc_base_timestamped, "backup", "not_mosquito")
    os.makedirs(reloc_mosquito_timestamped, exist_ok=True)
    os.makedirs(reloc_not_mosquito_timestamped, exist_ok=True)

    # 準備所有蚊子樣本（準備進行 80/20 分割）
    all_mosquito_entries = []
    for img_file in mosquito_files:
        img_base = os.path.splitext(img_file)[0]
        all_mosquito_entries.append({
            'img': img_file,
            'img_src': os.path.join(mosquito_dir, img_file),
            'label_src': os.path.join(mosquito_dir, img_base + '.txt'),
            'label_exists': os.path.exists(os.path.join(mosquito_dir, img_base + '.txt'))
        })

    # 隨機分割：80% train, 20% val
    random.seed(42)  # 固定種子保證可重現性
    random.shuffle(all_mosquito_entries)
    split_idx = int(len(all_mosquito_entries) * 0.8)
    train_entries = all_mosquito_entries[:split_idx]
    val_entries = all_mosquito_entries[split_idx:]

    # 處理訓練集樣本
    train_count = 0
    for entry in train_entries:
        img_base = os.path.splitext(entry['img'])[0]
        # 複製圖片到訓練目錄
        img_dst = os.path.join(training_dataset_dir, "images", "train", entry['img'])
        shutil.copy2(entry['img_src'], img_dst)

        # 處理標籤文件
        if entry['label_exists']:
            label_dst = os.path.join(training_dataset_dir, "labels", "train", img_base + '.txt')
            with open(entry['label_src'], 'r') as f:
                lines = f.readlines()

            # 確保第一碼是 0（蚊子類別 ID）
            fixed_lines = []
            for line in lines:
                parts = line.strip().split()
                if parts:
                    parts[0] = '0'
                    fixed_lines.append(' '.join(parts) + '\n')

            with open(label_dst, 'w') as f:
                f.writelines(fixed_lines)
        else:
            # 生成預設全圖標籤
            label_dst = os.path.join(training_dataset_dir, "labels", "train", img_base + '.txt')
            with open(label_dst, 'w') as f:
                f.write('0 0.5 0.5 1.0 1.0\n')

        train_count += 1
        # 備份原始文件
        shutil.copy2(entry['img_src'], os.path.join(reloc_mosquito_timestamped, entry['img']))
        if entry['label_exists']:
            shutil.copy2(entry['label_src'], os.path.join(reloc_mosquito_timestamped, img_base + '.txt'))

    # 處理驗證集樣本
    val_count = 0
    for entry in val_entries:
        img_base = os.path.splitext(entry['img'])[0]
        # 複製圖片到驗證目錄
        img_dst = os.path.join(training_dataset_dir, "images", "val", entry['img'])
        shutil.copy2(entry['img_src'], img_dst)

        # 處理標籤文件
        if entry['label_exists']:
            label_dst = os.path.join(training_dataset_dir, "labels", "val", img_base + '.txt')
            with open(entry['label_src'], 'r') as f:
                lines = f.readlines()

            # 確保第一碼是 0（蚊子類別 ID）
            fixed_lines = []
            for line in lines:
                parts = line.strip().split()
                if parts:
                    parts[0] = '0'
                    fixed_lines.append(' '.join(parts) + '\n')

            with open(label_dst, 'w') as f:
                f.writelines(fixed_lines)
        else:
            # 生成預設全圖標籤
            label_dst = os.path.join(training_dataset_dir, "labels", "val", img_base + '.txt')
            with open(label_dst, 'w') as f:
                f.write('0 0.5 0.5 1.0 1.0\n')

        val_count += 1
        # 備份原始文件
        shutil.copy2(entry['img_src'], os.path.join(reloc_mosquito_timestamped, entry['img']))
        if entry['label_exists']:
            shutil.copy2(entry['label_src'], os.path.join(reloc_mosquito_timestamped, img_base + '.txt'))

    # 移動非蚊子樣本備份
    for img_file in not_mosquito_files:
        img_base = os.path.splitext(img_file)[0]
        img_src = os.path.join(not_mosquito_dir, img_file)
        img_dst = os.path.join(reloc_not_mosquito_timestamped, img_file)
        shutil.copy2(img_src, img_dst)

        label_src = os.path.join(not_mosquito_dir, img_base + '.txt')
        if os.path.exists(label_src):
            label_dst = os.path.join(reloc_not_mosquito_timestamped, img_base + '.txt')
            shutil.copy2(label_src, label_dst)

    # 刪除原始標註目錄中的檔案
    for img_file in mosquito_files:
        img_src = os.path.join(mosquito_dir, img_file)
        if os.path.exists(img_src):
            os.remove(img_src)
        img_base = os.path.splitext(img_file)[0]
        label_src = os.path.join(mosquito_dir, img_base + '.txt')
        if os.path.exists(label_src):
            os.remove(label_src)

    for img_file in not_mosquito_files:
        img_src = os.path.join(not_mosquito_dir, img_file)
        if os.path.exists(img_src):
            os.remove(img_src)
        img_base = os.path.splitext(img_file)[0]
        label_src = os.path.join(not_mosquito_dir, img_base + '.txt')
        if os.path.exists(label_src):
            os.remove(label_src)

    moved_count = train_count + val_count

    # 併存目前使用的主模型到搬遷目錄（根目錄下）
    model_src = os.path.join("models", "mosquito_yolov8.pt")
    if os.path.exists(model_src):
        model_dst = os.path.join(reloc_base_timestamped, "mosquito_yolov8.pt")
        try:
            shutil.copy2(model_src, model_dst)
            model_message = "並已備份模型 mosquito_yolov8.pt"
        except Exception as e:
            model_message = f"但模型備份失敗: {e}"
    else:
        model_message = "（注意：未找到 models/mosquito_yolov8.pt，跳過模型備份）"

    # 同步複製 Colab Notebook 到 Google Drive Colab 目錄
    try:
        project_root = Path(__file__).resolve().parent.parent
        notebook_src = str(project_root / "mosquito_training_colab.ipynb")
        if os.path.exists(notebook_src):
            os.makedirs(config.COLAB_NOTEBOOK_DEST_DIR, exist_ok=True)
            notebook_dst = os.path.join(config.COLAB_NOTEBOOK_DEST_DIR, "mosquito_training_colab.ipynb")
            shutil.copy2(notebook_src, notebook_dst)
            notebook_message = "並已同步 Notebook 到 Colab Notebooks"
        else:
            notebook_message = "（注意：未找到 mosquito_training_colab.ipynb，跳過 Notebook 同步）"
    except Exception as e:
        notebook_message = f"（Notebook 同步失敗: {e}）"

    # 生成 dataset.yaml
    yaml_content = f"""path: {training_dataset_dir}
train: images/train
val: images/val
names:
  0: mosquito
nc: 1
"""
    yaml_path = os.path.join(training_dataset_dir, "dataset.yaml")
    with open(yaml_path, 'w') as f:
        f.write(yaml_content)

    print(f"\n✓ 成功搬遷並準備訓練數據集:")
    print(f"   基礎目錄: {config.RELOCATION_BASE_DIR}/{timestamp}/")
    print(f"\n📊 訓練數據分割:")
    print(f"   訓練集: {train_count} 張 (80%)")
    print(f"   驗證集: {val_count} 張 (20%)")
    print(f"   備份蚊子樣本: {len(mosquito_files)} 張")
    print(f"   備份非蚊子樣本: {len(not_mosquito_files)} 張")
    print(f"\n📁 訓練數據集位置:")
    print(f"   {training_dataset_dir}/")
    print(f"✓ 已生成 dataset.yaml: {yaml_path}")
    if model_message:
        print(f"✓ {model_message}")
    if notebook_message:
        print(f"✓ {notebook_message}")
    print(f"\n💡 下一步: 複製此訓練數據集到 Google Drive，Colab 可直接進行訓練")
    print(f"💡 提示: confirmed/ 目錄已清空，可以開始新一輪標註")

if __name__ == '__main__':
    try:
        label_samples()
    except KeyboardInterrupt:
        print("\n\n⊗ 用戶中斷")
    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
