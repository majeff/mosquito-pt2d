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
部署新模型（簡化版：僅複製已轉換模型）

功能：
1) 備份現有 models/ 中的舊模型（如存在）
2) 從 Google Drive 同步目錄複製所有已轉換模型到 models/
   - mosquito_yolov8.pt (PyTorch)
   - mosquito_yolov8.onnx (通用)
   - mosquito_yolov8.rknn (Orange Pi 5)
   - mosquito_yolov8.bin (RDK X5)

說明：
- 所有模型格式已在 Colab 中生成，此腳本僅負責複製
- 來源模型位置：Google Drive/Colab Notebooks/mosquito-training/models/
- 系統會自動選擇對應平台的模型格式進行推理
"""

import os
import sys
import shutil
from pathlib import Path
from datetime import datetime
import argparse

try:
     from config_loader import config  # 使用新的配置加载模块
except Exception as e:
    print(f"[ERROR] 無法載入 config_loader.py: {e}")
    sys.exit(1)


def backup_existing_models(local_models_dir: Path):
    """備份現有的模型文件"""
    backup_files = [
        "mosquito_yolov8.pt",
        "mosquito_yolov8.onnx",
        "mosquito_yolov8.rknn",
        "mosquito_yolov8.bin"
    ]

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = local_models_dir / f"backup_{timestamp}"
    backed_up = False

    for filename in backup_files:
        src = local_models_dir / filename
        if src.exists():
            if not backed_up:
                backup_dir.mkdir(parents=True, exist_ok=True)
                backed_up = True
            dst = backup_dir / filename
            shutil.copy2(str(src), str(dst))
            size_mb = src.stat().st_size / 1024 / 1024
            print(f"[BACKUP] {filename} → {backup_dir.name}/ ({size_mb:.2f} MB)")

    if backed_up:
        print(f"✅ 舊模型已備份至: {backup_dir}\n")
    else:
        print("[INFO] 無現有模型需要備份\n")


def copy_all_models_from_drive(local_models_dir: Path) -> dict:
    """複製所有已轉換的模型格式到本地 models/ 目錄"""
    # 以 RELOCATION_BASE_DIR 的父層作為 mosquito-training 根目錄
    reloc_base = Path(config.RELOCATION_BASE_DIR)
    training_root = reloc_base.parent  # .../Colab Notebooks/mosquito-training
    training_models = training_root / "models"

    if not training_models.exists():
        raise FileNotFoundError(f"找不到訓練模型目錄: {training_models}\n請確認 Google Drive 已同步")

    local_models_dir.mkdir(parents=True, exist_ok=True)

    # 定義要複製的模型文件（來源檔名 -> 目標檔名）
    model_files = {
        "mosquito_yolov8_new.pt": "mosquito_yolov8.pt",
        "mosquito_yolov8.onnx": "mosquito_yolov8.onnx",
        "mosquito_yolov8.rknn": "mosquito_yolov8.rknn",
        "mosquito_yolov8.bin": "mosquito_yolov8.bin",
    }

    copied = {}
    for src_name, dst_name in model_files.items():
        src = training_models / src_name
        dst = local_models_dir / dst_name

        if src.exists():
            shutil.copy2(str(src), str(dst))
            size_mb = dst.stat().st_size / 1024 / 1024
            print(f"[OK] 已複製 {dst_name} ({size_mb:.2f} MB)")
            copied[dst_name] = dst
        else:
            print(f"[SKIP] {src_name} 不存在，跳過")

    if not copied:
        raise FileNotFoundError(f"未找到任何模型文件在 {training_models}\n請確認 Colab 已完成訓練並生成模型")

    return copied, training_models

def main():
    parser = argparse.ArgumentParser(description="部署新模型：從 Google Drive 複製所有已轉換模型到專案目錄")
    parser.add_argument("--dry-run", action="store_true", help="僅檢查來源模型，不實際複製")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent

    # 優先使用標準結構 (project_root/models/)，如果不存在則使用 python/models/
    standard_models_dir = project_root / "models"
    local_models_dir = script_dir / "models"

    # 如果標準目錄不存在但 python/models/ 存在，使用 python/models/
    if not standard_models_dir.exists() and local_models_dir.exists():
        target_models_dir = local_models_dir
        print("⚠️  注意：使用非標準結構 python/models/")
        print(f"   建議：將 {local_models_dir} 移動到 {standard_models_dir}")
    else:
        target_models_dir = standard_models_dir

    try:
        print("="*60)
        print("模型部署工具 - 簡化版")
        print("="*60)
        print(f"專案目錄: {project_root}")
        print(f"目標模型目錄: {target_models_dir}")
        print()

        # 備份現有模型
        backup_existing_models(target_models_dir)

        copied_models, training_models = copy_all_models_from_drive(target_models_dir)

        print()
        print("="*60)
        print("✅ 部署完成")
        print("="*60)
        print("\n已部署的模型格式:")
        for name in copied_models:
            print(f"  • {name}")

        print("\n系統會自動選擇對應平台的模型:")
        print("  - Orange Pi 5 (RK3588) → mosquito_yolov8.rknn")
        print("  - RDK X5 (Bayes-e) → mosquito_yolov8.bin")
        print("  - 其他平台 → mosquito_yolov8.onnx (CPU)")

    except Exception as e:
        print(f"\n[ERROR] 部署失敗: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()