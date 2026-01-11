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
標籤轉移測試腳本

用途：根據txt標註文件中的標籤值進行批量處理和轉移
- 若txt標註為1，則將圖片和txt轉移到confirmed/mosquito，並將txt中的1改為0
- 若txt標註為0，則將圖片和txt轉移到confirmed/not_mosquito，並將txt中的0改為1
"""

import os
import shutil
from pathlib import Path
from config_loader import config


def transfer_labeled_samples():
    """
    根據標籤值批量轉移樣本
    """
    # 手動構造正確的路徑
    project_root = Path(__file__).resolve().parent.parent
    source_dir = project_root / "sample_collection" / "medium_confidence"
    mosquito_dir = project_root / "sample_collection" / "confirmed" / "mosquito"
    not_mosquito_dir = project_root / "sample_collection" / "confirmed" / "not_mosquito"

    # 確保來源目錄存在
    if not os.path.exists(source_dir):
        print(f"❌ 來源目錄不存在: {source_dir}")
        return

    # 建立目標目錄
    os.makedirs(mosquito_dir, exist_ok=True)
    os.makedirs(not_mosquito_dir, exist_ok=True)

    # 獲取所有圖片文件
    image_files = []
    for f in os.listdir(source_dir):
        if f.lower().endswith(('.jpg', '.jpeg', '.png')):
            image_files.append(f)

    if not image_files:
        print("⚠️  來源目錄中沒有圖片文件")
        return

    print(f"找到 {len(image_files)} 個圖片文件")

    # 統計計數
    mosquito_count = 0
    not_mosquito_count = 0
    error_count = 0

    for img_file in image_files:
        img_path = os.path.join(source_dir, img_file)
        base_name = os.path.splitext(img_file)[0]
        txt_file = base_name + '.txt'
        txt_path = os.path.join(source_dir, txt_file)

        # 檢查是否有對應的txt文件
        if not os.path.exists(txt_path):
            print(f"⚠️  缺少標籤文件: {txt_file}")
            continue

        # 讀取txt文件的第一行第一個數字來判斷標籤
        try:
            with open(txt_path, 'r') as f:
                line = f.readline().strip()
                if not line:
                    print(f"⚠️  標籤文件為空: {txt_file}")
                    continue

                parts = line.split()
                if not parts:
                    print(f"⚠️  標籤文件格式錯誤: {txt_file}")
                    continue

                label = parts[0]

                # 根據標籤值決定移動位置和修改後的標籤
                if label == '1':
                    # 移動到 mosquito 目錄，並將標籤從 1 改為 0
                    new_txt_content = _modify_labels(line, '0')
                    target_img_path = os.path.join(mosquito_dir, img_file)
                    target_txt_path = os.path.join(mosquito_dir, txt_file)
                    mosquito_count += 1
                elif label == '0':
                    # 移動到 not_mosquito 目錄，並將標籤從 0 改為 1
                    new_txt_content = _modify_labels(line, '1')
                    target_img_path = os.path.join(not_mosquito_dir, img_file)
                    target_txt_path = os.path.join(not_mosquito_dir, txt_file)
                    not_mosquito_count += 1
                else:
                    print(f"⚠️  標籤值非0或1: {txt_file} (標籤: {label})")
                    continue

                # 移動圖片文件
                shutil.move(img_path, target_img_path)

                # 修改並保存標籤文件
                with open(target_txt_path, 'w') as tf:
                    tf.write(new_txt_content)

                print(f"✓ 已處理: {img_file} -> {'mosquito' if label == '1' else 'not_mosquito'} (標籤: {label} -> {new_txt_content.split()[0]})")

        except Exception as e:
            print(f"❌ 處理文件時出錯 {img_file}: {e}")
            error_count += 1

    print(f"\n📊 處理完成:")
    print(f"- 移動到 mosquito 目錄: {mosquito_count} 個")
    print(f"- 移動到 not_mosquito 目錄: {not_mosquito_count} 個")
    print(f"- 錯誤數量: {error_count} 個")


def _modify_labels(line, new_label):
    """
    修改標籤行的第一個值為新的標籤
    """
    parts = line.split()
    if parts:
        parts[0] = new_label
        return ' '.join(parts) + '\n'
    return line


if __name__ == '__main__':
    transfer_labeled_samples()