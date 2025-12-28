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
部署新模型（單一 Python 腳本）

功能：
1) 備份現有 models/mosquito_yolov8.pt（如存在）
2) 從本機 Google Drive 同步的訓練目錄複製最新模型到 models/
3) 以 Ultralytics 導出 ONNX（可調 imgsz）

說明：
- 來源模型位置自動推導自 config.RELOCATION_BASE_DIR 的父層（mosquito-training）下的 models/
- RKNN 轉換依環境與工具而定，建議在部署機依 docs 指南執行
"""

import os
import sys
import shutil
from pathlib import Path
from datetime import datetime
import argparse
import platform

try:
    import config  # 專案內 python/config.py
except Exception as e:
    print(f"[ERROR] 無法載入 config.py: {e}")
    sys.exit(1)


def backup_existing_model(models_dir: Path) -> None:
    target = models_dir / "mosquito_yolov8.pt"
    if target.exists():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = models_dir / f"mosquito_yolov8_backup_{ts}.pt"
        try:
            shutil.copy2(str(target), str(backup))
            print(f"[OK] 已備份舊模型到: {backup}")
        except Exception as e:
            print(f"[WARN] 備份失敗: {e}")
    else:
        print("[INFO] 無既有模型，略過備份")


def copy_new_model_from_drive(local_models_dir: Path) -> Path:
    # 以 RELOCATION_BASE_DIR 的父層作為 mosquito-training 根目錄
    reloc_base = Path(config.RELOCATION_BASE_DIR)
    training_root = reloc_base.parent  # .../Colab Notebooks/mosquito-training
    training_models = training_root / "models"
    src = training_models / "mosquito_yolov8_new.pt"
    dst = local_models_dir / "mosquito_yolov8.pt"

    if not src.exists():
        raise FileNotFoundError(f"找不到來源模型: {src}\n請確認 Google Drive 已同步，且 Colab Notebook 已將模型輸出到 mosquito-training/models/")

    local_models_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(src), str(dst))
    print(f"[OK] 已複製新模型到: {dst}")
    return dst

def export_onnx(model_path: Path, imgsz: int, opset: int | None = None, dynamic: bool = False, half: bool = False) -> Path:
    try:
        from ultralytics import YOLO
    except Exception as e:
        raise RuntimeError(f"Ultralytics 未安裝或載入失敗: {e}\n請先執行: pip install ultralytics")

    print(f"[INFO] 導出 ONNX，imgsz={imgsz}，opset={opset or 'default'}，dynamic={dynamic}，half={half}…")
    m = YOLO(str(model_path))
    export_kwargs = {"format": "onnx", "imgsz": imgsz, "simplify": True}
    if opset is not None:
        export_kwargs["opset"] = opset
    if dynamic:
        export_kwargs["dynamic"] = True
    if half:
        export_kwargs["half"] = True
    m.export(**export_kwargs)
    onnx_out = model_path.with_suffix(".onnx")
    print(f"[OK] ONNX 導出完成: {onnx_out}")
    return onnx_out

from typing import Optional

def export_rknn(onnx_path: Path, out_path: Path, target: str, dataset_txt: Optional[str]) -> Path:
    try:
        from rknn.api import RKNN
    except Exception as e:
        raise RuntimeError(
            f"RKNN Toolkit 未安裝或載入失敗: {e}\n"
            "請先安裝 rknn-toolkit2，並於可用的環境（如開發機/部署機）執行 RKNN 導出。"
        )

    if not onnx_path.exists():
        raise FileNotFoundError(f"未找到 ONNX 檔: {onnx_path}")

    rknn = RKNN(verbose=False)
    print(f"[INFO] RKNN config: target={target}, quantized={'yes' if dataset_txt else 'no'}")
    rknn.config(target_platform=target, quantized_dtype='asymmetric_quantized-u8')

    print(f"[INFO] 載入 ONNX: {onnx_path}")
    ret = rknn.load_onnx(model=str(onnx_path))
    if ret != 0:
        rknn.release()
        raise RuntimeError("載入 ONNX 失敗，請檢查模型與依賴")

    print("[INFO] 建置 RKNN 模型…")
    if dataset_txt:
        ret = rknn.build(do_quantization=True, dataset=dataset_txt)
    else:
        ret = rknn.build(do_quantization=False)
    if ret != 0:
        rknn.release()
        raise RuntimeError("建置 RKNN 失敗，請檢查資料集或環境設定")

    out_path = Path(out_path)
    print(f"[INFO] 導出 RKNN: {out_path}")
    ret = rknn.export_rknn(str(out_path))
    rknn.release()
    if ret != 0:
        raise RuntimeError("導出 RKNN 失敗")
    print(f"[OK] RKNN 導出完成: {out_path}")
    return out_path


def generate_rknn_dataset_txt(output_path: Path, max_images: int = 1000) -> Optional[str]:
    """
    從已標註樣本自動生成 RKNN 量化資料集清單（dataset.txt）。
    來源：config.CONFIRMED_MOSQUITO_DIR 與 config.CONFIRMED_NOT_MOSQUITO_DIR。
    回傳 dataset.txt 路徑；若沒有可用影像則回傳 None（改用非量化）。
    """
    confirmed_mosquito_dir = Path(getattr(config, "CONFIRMED_MOSQUITO_DIR", "sample_collection/confirmed/mosquito"))
    confirmed_not_mosquito_dir = Path(getattr(config, "CONFIRMED_NOT_MOSQUITO_DIR", "sample_collection/confirmed/not_mosquito"))

    images: list[Path] = []
    for ext in ("*.jpg", "*.jpeg", "*.png"):
        images += list(confirmed_mosquito_dir.glob(ext))
        images += list(confirmed_not_mosquito_dir.glob(ext))

    if not images:
        print("[WARN] 未找到可用的已標註樣本，RKNN 將以非量化方式建置")
        return None

    images = images[:max_images]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for p in images:
            f.write(str(p.resolve()))
            f.write("\n")

    print(f"[OK] 已生成 RKNN 量化資料集清單: {output_path}（{len(images)} 張）")
    return str(output_path)


def auto_detect_rknn_target() -> Optional[str]:
    """在部署機上自動偵測 RKNN 目標平台（僅 Linux）。"""
    try:
        if platform.system().lower() != 'linux':
            return None
        # 嘗試從裝置資訊判斷 SoC 型號
        candidates = []
        for p in ('/proc/device-tree/model', '/proc/cpuinfo'):
            try:
                text = Path(p).read_text(encoding='utf-8', errors='ignore').lower()
                candidates.append(text)
            except Exception:
                pass
        blob = "\n".join(candidates)
        if 'rk3588' in blob:
            return 'rk3588'
        if 'rk3568' in blob or 'rk3566' in blob or 'rk356x' in blob:
            return 'rk3568'
        if 'rk3399pro' in blob:
            return 'rk3399pro'
        if 'rk3576' in blob:
            return 'rk3576'  # 可能的 RDK X5 SoC
    except Exception:
        return None
    return None


def target_default_onnx_params(target: Optional[str]) -> tuple[int | None, bool, bool]:
    """依目標平台給出保守的 ONNX 導出預設（可再被 CLI 覆寫）。"""
    # 保守配置：rk3588 -> opset 12；rk3568 -> opset 11；其他使用 None 交給 Ultralytics 預設
    if target == 'rk3588':
        return 12, False, False
    if target in ('rk3568', 'rk3566', 'rk356x'):
        return 11, False, False
    if target == 'rk3399pro':
        return 11, False, False
    if target == 'rk3576':
        return 12, False, False
    return None, False, False


def main():
    parser = argparse.ArgumentParser(description="部署新模型：備份、複製、導出 ONNX/RKNN（預設同時導出）")
    parser.add_argument("--imgsz", type=int, default=getattr(config, "DEFAULT_IMGSZ", 320), help="ONNX 導出解析度（預設取自 config.DEFAULT_IMGSZ）")
    parser.add_argument("--skip-onnx", action="store_true", help="略過 ONNX 導出")
    parser.add_argument("--export-rknn", action="store_true", help="強制導出 RKNN（即使提供了 --skip-rknn）")
    parser.add_argument("--skip-rknn", action="store_true", help="略過 RKNN 導出（預設會導出）")
    parser.add_argument("--rknn-target", type=str, default=None, help="RKNN 目標平台（未提供則嘗試自動偵測；否則預設 rk3588）")
    parser.add_argument("--rknn-quant-dataset", type=str, default=None, help="覆寫量化資料集 txt（選填，提供則使用該檔）")
    parser.add_argument("--rknn-no-quant", action="store_true", help="禁用 RKNN 量化（不生成 dataset.txt）")
    parser.add_argument("--rknn-out", type=str, default=None, help="RKNN 輸出路徑（預設為同名 .rknn）")
    parser.add_argument("--onnx-opset", type=int, default=None, help="覆寫 ONNX opset（依目標平台預設，通常 rk3588=12、rk3568=11）")
    parser.add_argument("--onnx-dynamic", action="store_true", help="啟用 ONNX 動態 shape（預設關閉）")
    parser.add_argument("--onnx-half", action="store_true", help="使用半精度 FP16（預設關閉）")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    local_models_dir = project_root / "models"

    try:
        backup_existing_model(local_models_dir)
        model_path = copy_new_model_from_drive(local_models_dir)

        onnx_out: Optional[Path] = None
        if not args.skip_onnx:
            # 依目標平台決定 ONNX 預設參數（可被 CLI 覆寫）
            target_for_defaults = args.rknn_target or auto_detect_rknn_target() or 'rk3588'
            default_opset, default_dynamic, default_half = target_default_onnx_params(target_for_defaults)
            opset = args.onnx_opset if args.onnx_opset is not None else default_opset
            dynamic = args.onnx_dynamic or default_dynamic
            half = args.onnx_half or default_half
            onnx_out = export_onnx(model_path, imgsz=args.imgsz, opset=opset, dynamic=dynamic, half=half)
        else:
            print("[INFO] 已略過 ONNX 導出")

        if args.export_rknn or not args.skip_rknn:
            # 若略過 ONNX，嘗試使用現有同名 .onnx；否則需先導出
            if onnx_out is None:
                candidate = model_path.with_suffix('.onnx')
                if candidate.exists():
                    onnx_out = candidate
                else:
                    raise RuntimeError("需先提供 ONNX 檔才能導出 RKNN（請移除 --skip-onnx 或先行導出）")

            rknn_out = Path(args.rknn_out) if args.rknn_out else onnx_out.with_suffix('.rknn')

            # 決定量化資料集：優先使用傳入，其次自動生成；如禁用量化則為 None
            if args.rknn_no_quant:
                dataset_txt = None
                print("[INFO] 已禁用 RKNN 量化")
            elif args.rknn_quant_dataset:
                dataset_txt = args.rknn_quant_dataset
                print(f"[INFO] 使用自訂量化資料集: {dataset_txt}")
            else:
                # 自動生成 dataset.txt（預設寫入 models/rknn_dataset.txt）
                auto_dataset_path = (local_models_dir / "rknn_dataset.txt")
                dataset_txt = generate_rknn_dataset_txt(auto_dataset_path)

            # 決定 RKNN 目標平台：CLI > 自動偵測 > 預設 rk3588
            rknn_target = args.rknn_target or auto_detect_rknn_target() or 'rk3588'
            export_rknn(onnx_out, rknn_out, target=rknn_target, dataset_txt=dataset_txt)

    except Exception as e:
        print(f"[ERROR] 部署失敗: {e}")
        sys.exit(1)

    print("\n[DONE] 部署流程完成。RKNN 轉換可選；預設自動生成量化資料集（dataset.txt）。")


if __name__ == "__main__":
    main()
