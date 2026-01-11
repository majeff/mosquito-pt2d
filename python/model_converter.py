"""
模型格式轉換工具 - 將 YOLOv8 模型轉換為多平台格式

支援轉換：
- ONNX (.onnx) - 通用格式，使用 onnxsim 簡化
- RKNN (.rknn) - Orange Pi 5 (RK3588 NPU) 格式

用法:
    python model_converter.py --pt-model ../models/mosquito_yolov8.pt

    自訂路徑:
        python model_converter.py --pt-model /path/to/model.pt --output-dir /path/to/output
"""

import argparse
import shutil
import random
import platform
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# 第三方依賴
try:
    import onnx
    from onnxsim import simplify
except ImportError:
    onnx = None
    simplify = None

try:
    from rknn.api import RKNN
except ImportError:
    RKNN = None


def install_dependencies(verbose: bool = True) -> bool:
    """安裝必要的依賴包"""
    if verbose:
        print("📦 檢查並安裝模型轉換工具...")

    packages_to_install = []

    if onnx is None or simplify is None:
        packages_to_install.append(("onnx onnxsim", "ONNX 相關工具"))

    if RKNN is None:
        packages_to_install.append((
            "rknn-toolkit2 -i https://pypi.tuna.tsinghua.edu.cn/simple",
            "rknn-toolkit2 (Orange Pi 5)"
        ))

    if not packages_to_install:
        if verbose:
            print("✅ 所有依賴已安裝")
        return True

    try:
        import subprocess
        for pkg, name in packages_to_install:
            if verbose:
                print(f"  安裝 {name}...")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", *pkg.split(), "-q"],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                if verbose:
                    print(f"  ⚠️ {name} 安裝失敗")
                    print(result.stderr)
                return False

        if verbose:
            print("✅ 依賴安裝完成")
        return True
    except Exception as e:
        print(f"❌ 安裝失敗: {e}")
        return False


def prepare_calibration_dataset(
    images_dir: Path,
    list_path: Path,
    num_samples: int = 50,
    verbose: bool = True
) -> bool:
    """準備 RKNN 量化校準清單（不複製影像，僅寫入 dataset.txt）"""
    if verbose:
        print(f"\n📸 準備校準數據集清單...")

    images_dir = images_dir.resolve()
    if not images_dir.exists() or not images_dir.is_dir():
        print(f"❌ 錯誤: 校準影像目錄不存在: {images_dir}")
        return False

    # 從確認的蚊子樣本中抽取圖片（白名單副檔名）
    allowed_exts = {'.jpg', '.jpeg', '.png', '.bmp'}
    mosquito_images = [
        p for p in images_dir.iterdir()
        if p.is_file() and p.suffix.lower() in allowed_exts
    ]
    skipped = [
        p for p in images_dir.iterdir()
        if p.is_file() and p.suffix.lower() not in allowed_exts
    ]

    if len(mosquito_images) < 10:
        print(f"❌ 錯誤: 蚊子樣本圖片不足 ({len(mosquito_images)} 張)，至少需要 10 張")
        print(f"   請先在 label_samples.py 中標註更多蚊子樣本")
        return False

    # 隨機抽取
    random.seed(42)
    num_samples = min(num_samples, len(mosquito_images))
    calib_samples = random.sample(mosquito_images, num_samples)

    # 寫入校準清單（RKNN 需要 dataset.txt 格式，每行一個影像路徑）
    list_path.parent.mkdir(parents=True, exist_ok=True)
    with list_path.open('w', encoding='utf-8') as f:
        for img in calib_samples:
            f.write(str(img.resolve()) + "\n")

    if verbose:
        print(f"  ✓ 已建立校準清單: {list_path}")
        print(f"    來源目錄: {images_dir}")
        print(f"    影像數量: {len(calib_samples)} (可用: {len(mosquito_images)}，略過非影像: {len(skipped)})")

    return True


def export_onnx_model(
    pt_model_path: Path,
    onnx_output_dir: Path,
    verbose: bool = True
) -> Optional[Path]:
    """導出 ONNX 模型"""
    if verbose:
        print(f"\n📦 導出 ONNX 模型...")

    if not pt_model_path.exists():
        print(f"❌ 錯誤: PyTorch 模型不存在: {pt_model_path}")
        return None

    if onnx is None or simplify is None:
        print("❌ 錯誤: ONNX 工具未安裝")
        return None

    try:
        from ultralytics import YOLO

        # 導出 ONNX
        if verbose:
            print("  導出為 ONNX 格式...")

        model = YOLO(str(pt_model_path))
        export_result = model.export(format='onnx', imgsz=640, opset=12, simplify=False)

        # 找到導出的 ONNX 檔案
        onnx_exported = Path(export_result).parent / 'best.onnx'
        if not onnx_exported.exists():
            # 嘗試其他可能的位置
            possible_paths = list(Path(export_result).parent.glob('*.onnx'))
            if not possible_paths:
                print(f"❌ 錯誤: ONNX 導出失敗")
                return None
            onnx_exported = possible_paths[0]

        # 簡化模型
        if verbose:
            print("  簡化 ONNX 模型（使用 onnxsim）...")

        onnx_model = onnx.load(str(onnx_exported))
        model_simplified, check = simplify(onnx_model)

        if not check:
            print("  ⚠️ 簡化失敗，但繼續使用未簡化版本...")
            model_simplified = onnx_model

        # 保存簡化後的模型
        onnx_output_dir.mkdir(parents=True, exist_ok=True)
        onnx_output_path = onnx_output_dir / 'mosquito_yolov8.onnx'
        onnx.save(model_simplified, str(onnx_output_path))

        # 同時複製一份到 models/ 目錄（如果不同）
        if onnx_output_dir != Path('models'):
            models_dir = Path('models')
            models_dir.mkdir(exist_ok=True)
            shutil.copy2(onnx_output_path, models_dir / 'mosquito_yolov8.onnx')

        if verbose:
            size_mb = onnx_output_path.stat().st_size / 1024 / 1024
            print(f"  ✓ ONNX 模型已保存: {onnx_output_path.name} ({size_mb:.2f} MB)")

        return onnx_output_path

    except Exception as e:
        print(f"❌ ONNX 導出失敗: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_rknn_model(
    onnx_model_path: Path,
    dataset_list_path: Path,
    rknn_output_dir: Path,
    verbose: bool = True
) -> Optional[Path]:
    """生成 RKNN 模型（Orange Pi 5），使用 dataset.txt 清單"""
    if verbose:
        print(f"\n🔧 生成 Orange Pi 5 RKNN 模型...")

    if not onnx_model_path.exists():
        print(f"❌ 錯誤: ONNX 模型不存在: {onnx_model_path}")
        return None

    if not dataset_list_path.exists() or not dataset_list_path.is_file():
        print(f"❌ 錯誤: 校準清單不存在: {dataset_list_path}")
        return None

    if RKNN is None:
        print("❌ 錯誤: rknn-toolkit2 未安裝")
        return None

    try:
        if verbose:
            print("  初始化 RKNN...")

        rknn = RKNN(verbose=False)

        # 配置參數
        rknn.config(
            mean_values=[[0, 0, 0]],
            std_values=[[255, 255, 255]],
            target_platform='rk3588'
        )

        # 載入 ONNX
        if verbose:
            print("  載入 ONNX 模型...")
        ret = rknn.load_onnx(model=str(onnx_model_path))
        if ret != 0:
            print("❌ 載入 ONNX 失敗")
            return None

        # 執行量化
        if verbose:
            print("  執行量化（預計需要 2-5 分鐘）...")
        ret = rknn.build(do_quantization=True, dataset=str(dataset_list_path))
        if ret != 0:
            print("❌ 量化失敗")
            rknn.release()
            return None

        # 導出
        if verbose:
            print("  導出 RKNN 模型...")

        rknn_output_dir.mkdir(parents=True, exist_ok=True)
        rknn_output_path = rknn_output_dir / 'mosquito_yolov8.rknn'
        ret = rknn.export_rknn(str(rknn_output_path))

        rknn.release()

        if ret != 0:
            print("❌ RKNN 導出失敗")
            return None

        # 同時複製一份到 models/ 目錄（如果不同）
        if rknn_output_dir != Path('models'):
            models_dir = Path('models')
            models_dir.mkdir(exist_ok=True)
            shutil.copy2(rknn_output_path, models_dir / 'mosquito_yolov8.rknn')

        if verbose:
            size_mb = rknn_output_path.stat().st_size / 1024 / 1024
            print(f"  ✓ RKNN 模型已保存: {rknn_output_path.name} ({size_mb:.2f} MB)")

        return rknn_output_path

    except Exception as e:
        print(f"❌ RKNN 生成失敗: {e}")
        import traceback
        traceback.print_exc()
        return None


def backup_pytorch_model(
    pt_model_path: Path,
    output_dir: Path,
    verbose: bool = True
) -> Optional[Path]:
    """備份 PyTorch 模型"""
    if not pt_model_path.exists():
        print(f"❌ 錯誤: PyTorch 模型不存在: {pt_model_path}")
        return None

    output_dir.mkdir(parents=True, exist_ok=True)

    # 保存為 mosquito_yolov8_new.pt
    pt_new_path = output_dir / 'mosquito_yolov8_new.pt'
    shutil.copy2(pt_model_path, pt_new_path)

    # 備份帶日期戳記的版本
    date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    pt_backup_path = output_dir / f'mosquito_yolov8_backup_{date_str}.pt'
    shutil.copy2(pt_model_path, pt_backup_path)

    if verbose:
        print(f"✓ PyTorch 模型已備份")
        print(f"  新版本: {pt_new_path.name}")
        print(f"  備份版: {pt_backup_path.name}")

    return pt_new_path


def create_backup_zip(
    model_dir: Path,
    verbose: bool = True
) -> Optional[Path]:
    """建立備份壓縮檔"""
    import zipfile

    # 收集所有模型檔
    model_files = []
    for ext in ['*.pt', '*.onnx', '*.rknn', '*.bin']:
        model_files.extend(model_dir.glob(ext))

    # 排除已有的 zip 檔
    model_files = [f for f in model_files if not f.suffix == '.zip']

    if not model_files:
        if verbose:
            print("⚠️ 沒有模型檔案可備份")
        return None

    date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    zip_path = model_dir / f'mosquito_models_backup_{date_str}.zip'

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for model_file in model_files:
            zipf.write(model_file, model_file.name)
            if verbose:
                print(f"  ✓ 已加入: {model_file.name}")

    if verbose:
        size_mb = zip_path.stat().st_size / 1024 / 1024
        print(f"✓ 備份壓縮檔已建立: {zip_path.name} ({size_mb:.2f} MB)")

    return zip_path


def print_summary(
    output_dir: Path,
    pt_path: Optional[Path] = None,
    onnx_path: Optional[Path] = None,
    rknn_path: Optional[Path] = None,
    bin_path: Optional[Path] = None
):
    """顯示轉換摘要"""
    print("\n" + "="*60)
    print("📊 模型轉換摘要")
    print("="*60)

    print("\n✅ 已生成的模型:")
    if onnx_path and onnx_path.exists():
        size = onnx_path.stat().st_size / 1024 / 1024
        print(f"  📄 ONNX: {onnx_path.name} ({size:.2f} MB)")
    if rknn_path and rknn_path.exists():
        size = rknn_path.stat().st_size / 1024 / 1024
        print(f"  📄 RKNN (Orange Pi 5): {rknn_path.name} ({size:.2f} MB)")

    print(f"\n📁 輸出目錄: {output_dir}")

    print("\n📥 下一步:")
    print("  在目標平台上運行追蹤系統:")
    if rknn_path and rknn_path.exists():
        print("     - Orange Pi 5: python streaming_tracking_system.py")

    print("\n" + "="*60)


def main():
    """主程式"""
    parser = argparse.ArgumentParser(
        description="YOLOv8 模型多平台轉換工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  # 使用預設路徑
  python model_converter.py

  # 自訂模型路徑
  python model_converter.py --pt-model /path/to/model.pt

  # 自訂輸出目錄
  python model_converter.py --output-dir /path/to/output

  # 跳過特定轉換
  python model_converter.py --skip-onnx --skip-rknn
        """
    )

    parser.add_argument(
        '--pt-model',
        type=Path,
        default=None,
        help="PyTorch 模型路徑 (必須指定)"
    )

    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('../models').resolve(),
        help="輸出目錄（預設: ../models）"
    )

    parser.add_argument(
        '--training-dataset',
        type=Path,
        help="訓練數據集目錄（已棄用，校準圖像現在來自 sample_collection/confirmed/mosquito）"
    )

    parser.add_argument(
        '--calib-dir',
        type=Path,
        help="校準數據集目錄"
    )

    parser.add_argument(
        '--skip-onnx',
        action='store_true',
        help="跳過 ONNX 轉換"
    )

    parser.add_argument(
        '--skip-rknn',
        action='store_true',
        help="跳過 RKNN 轉換"
    )

    args = parser.parse_args()

    # 本地模式
    if args.pt_model is None:
        print("❌ 錯誤: 必須指定 PyTorch 模型路徑 (--pt-model)")
        return False

    pt_model = Path(args.pt_model).resolve()
    output_dir = Path(args.output_dir).resolve()
    # 校準影像來源目錄（不複製，只建立清單）
    images_dir = Path(args.calib_dir).resolve() if args.calib_dir else Path('../sample_collection/confirmed/mosquito').resolve()
    # 校準清單檔案位置（放在輸出目錄中）
    dataset_list_path = output_dir / 'rknn_calibration_list.txt'

    # 驗證模型檔案存在
    if not pt_model.exists():
        print(f"❌ 錯誤: PyTorch 模型不存在: {pt_model}")
        print(f"   請確認模型路徑正確，或使用 --pt-model 指定")
        return False

    output_dir.mkdir(parents=True, exist_ok=True)

    print("="*60)
    print("🚀 開始模型轉換")
    print("="*60)
    print(f"\n📁 輸入模型: {pt_model}")
    print(f"📁 輸出目錄: {output_dir}")

    # 1. 安裝依賴
    if not install_dependencies():
        print("⚠️ 部分依賴安裝失敗，部分功能可能不可用")

    # 2. 準備校準清單（不複製影像）
    if not args.skip_rknn:
        if not prepare_calibration_dataset(images_dir, dataset_list_path):
            print("❌ 準備校準清單失敗，無法進行 RKNN 量化")
            args.skip_rknn = True

    # 3. 導出 ONNX
    onnx_path = None
    if not args.skip_onnx:
        onnx_path = export_onnx_model(pt_model, output_dir)

    # 4. 生成 RKNN
    rknn_path = None
    if not args.skip_rknn and onnx_path:
        rknn_path = generate_rknn_model(onnx_path, dataset_list_path, output_dir)

    # 5. 顯示摘要
    print_summary(output_dir, None, onnx_path, rknn_path)

    return True


if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⊗ 用戶中斷")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 程式錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
