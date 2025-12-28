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
import config

def label_samples():
    """
    互動式標註樣本
    """
    # 從 config 讀取目錄設定
    medium_dir = config.MEDIUM_CONFIDENCE_DIR
    mosquito_dir = config.CONFIRMED_MOSQUITO_DIR
    not_mosquito_dir = config.CONFIRMED_NOT_MOSQUITO_DIR

    # 建立目錄
    os.makedirs(mosquito_dir, exist_ok=True)
    os.makedirs(not_mosquito_dir, exist_ok=True)

    # 檢查樣本目錄
    if not os.path.exists(medium_dir):
        print(f"❌ 找不到樣本目錄: {medium_dir}")
        return

    # 獲取所有圖片
    images = [f for f in os.listdir(medium_dir) if f.endswith('.jpg')]

    if not images:
        print("⚠️  沒有待標註的樣本")
        return

    print(f"找到 {len(images)} 張待標註樣本\n")
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

    for idx, img_file in enumerate(images, 1):
        img_path = os.path.join(medium_dir, img_file)

        print(f"\n[{idx}/{len(images)}] {img_file}")

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
                shutil.move(img_path, os.path.join(mosquito_dir, img_file))
                print(f"✓ 移動到 mosquito/")
                labeled_count += 1
                break
            elif choice == 'n':
                shutil.move(img_path, os.path.join(not_mosquito_dir, img_file))
                print(f"✓ 移動到 not_mosquito/")
                labeled_count += 1
                break
            elif choice == 'd':
                os.remove(img_path)
                print(f"🗑️ 已刪除")
                deleted_count += 1
                break
            elif choice == 's':
                print_statistics(mosquito_dir, not_mosquito_dir, medium_dir)
                continue  # 顯示統計後繼續當前圖片
            elif choice == 'm':
                relocate_samples()
                continue  # 搬遷後繼續當前圖片
            elif choice == 'q':
                print("\n退出標註")
                print_statistics(mosquito_dir, not_mosquito_dir, medium_dir)
                return
            else:
                print("無效輸入，請輸入 y/n/d/s/m/q")

    print("\n✓ 標註完成！")
    print_statistics(mosquito_dir, not_mosquito_dir, medium_dir)

def print_statistics(mosquito_dir, not_mosquito_dir, medium_dir):
    """
    顯示統計資訊
    """
    mosquito_count = len([f for f in os.listdir(mosquito_dir) if f.endswith('.jpg')]) if os.path.exists(mosquito_dir) else 0
    not_mosquito_count = len([f for f in os.listdir(not_mosquito_dir) if f.endswith('.jpg')]) if os.path.exists(not_mosquito_dir) else 0
    remaining_count = len([f for f in os.listdir(medium_dir) if f.endswith('.jpg')]) if os.path.exists(medium_dir) else 0

    print("\n" + "="*50)
    print("📊 樣本統計")
    print("="*50)
    print(f"✓ 蚊子樣本: {mosquito_count} 張")
    print(f"✗ 非蚊子樣本: {not_mosquito_count} 張")
    print(f"⏳ 待標註樣本: {remaining_count} 張")
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

    # 統計當前樣本數量
    mosquito_files = [f for f in os.listdir(mosquito_dir) if f.endswith('.jpg')] if os.path.exists(mosquito_dir) else []
    not_mosquito_files = [f for f in os.listdir(not_mosquito_dir) if f.endswith('.jpg')] if os.path.exists(not_mosquito_dir) else []

    total_count = len(mosquito_files) + len(not_mosquito_files)

    if total_count == 0:
        print("⚠️  沒有已標註的樣本可搬遷")
        return

    print(f"\n📦 準備搬遷 {total_count} 張已標註樣本:")
    print(f"   - 蚊子樣本: {len(mosquito_files)} 張")
    print(f"   - 非蚊子樣本: {len(not_mosquito_files)} 張")

    confirm = input("\n確認搬遷？(y/n): ").lower().strip()

    if confirm != 'y':
        print("已取消搬遷")
        return

    # 建立搬遷目錄（使用時間戳記）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # 基底目錄：sample_collection/relocated/<timestamp>
    reloc_base_timestamped = os.path.join(config.RELOCATION_BASE_DIR, timestamp)
    os.makedirs(reloc_base_timestamped, exist_ok=True)
    # 類別子目錄：mosquito 與 not_mosquito
    reloc_mosquito_timestamped = os.path.join(reloc_base_timestamped, "mosquito")
    reloc_not_mosquito_timestamped = os.path.join(reloc_base_timestamped, "not_mosquito")

    os.makedirs(reloc_mosquito_timestamped, exist_ok=True)
    os.makedirs(reloc_not_mosquito_timestamped, exist_ok=True)

    # 搬遷蚊子樣本
    moved_count = 0
    for img_file in mosquito_files:
        src = os.path.join(mosquito_dir, img_file)
        dst = os.path.join(reloc_mosquito_timestamped, img_file)
        shutil.move(src, dst)
        moved_count += 1

    # 搬遷非蚊子樣本
    for img_file in not_mosquito_files:
        src = os.path.join(not_mosquito_dir, img_file)
        dst = os.path.join(reloc_not_mosquito_timestamped, img_file)
        shutil.move(src, dst)
        moved_count += 1

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

    print(f"\n✓ 成功搬遷 {moved_count} 張樣本到:")
    print(f"   {config.RELOCATION_BASE_DIR}/{timestamp}/ {model_message} {notebook_message}")
    print(f"\n💡 提示: confirmed/ 目錄已清空，可以開始新一輪標註")

if __name__ == '__main__':
    try:
        label_samples()
    except KeyboardInterrupt:
        print("\n\n⊗ 用戶中斷")
    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
