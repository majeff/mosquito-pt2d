"""
設置 Google Drive Colab 目錄結構

執行此腳本以在 Google Drive 同步資料夾中創建正確的目錄結構，
使 Colab Notebook 可以正確運行。

用法:
    python setup_colab_structure.py
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

# Google Drive 同步根目錄
GOOGLE_DRIVE_BASE = Path(r"D:\Users\jeffma\Sync\Google\我的雲端硬碟")
COLAB_TRAINING_BASE = GOOGLE_DRIVE_BASE / "Colab Notebooks" / "mosquito-training"

# 本機專案根目錄
PROJECT_ROOT = Path(__file__).resolve().parent.parent

def setup_directory_structure():
    """創建 Colab 所需的目錄結構"""

    print("=" * 60)
    print("🔧 設置 Google Drive Colab 目錄結構")
    print("=" * 60)

    # 1. 檢查 Google Drive 是否存在
    if not GOOGLE_DRIVE_BASE.exists():
        print(f"\n❌ 錯誤: Google Drive 同步資料夾不存在")
        print(f"   預期路徑: {GOOGLE_DRIVE_BASE}")
        print(f"\n請確認:")
        print(f"  1. Google Drive 已安裝並登入")
        print(f"  2. 同步路徑正確")
        return False

    print(f"\n✓ Google Drive 根目錄存在: {GOOGLE_DRIVE_BASE}")

    # 2. 創建基礎目錄結構
    print(f"\n📁 創建基礎目錄...")

    directories = [
        COLAB_TRAINING_BASE,
        COLAB_TRAINING_BASE / "relocated_samples",
        COLAB_TRAINING_BASE / "models",
        COLAB_TRAINING_BASE / "calibration_images",
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"   ✓ {directory.relative_to(GOOGLE_DRIVE_BASE)}")

    # 3. 檢查本機是否有 relocated_samples
    local_relocated = PROJECT_ROOT / "python" / "relocated_samples"

    if local_relocated.exists():
        print(f"\n📦 發現本機 relocated_samples 目錄")

        # 找到最新的時間戳目錄
        timestamp_dirs = sorted([d for d in local_relocated.iterdir() if d.is_dir()])

        if timestamp_dirs:
            latest = timestamp_dirs[-1]
            training_dataset = latest / "training_dataset"

            if training_dataset.exists():
                print(f"   最新樣本: {latest.name}")

                # 檢查是否已複製
                target_dir = COLAB_TRAINING_BASE / "relocated_samples" / latest.name

                if target_dir.exists():
                    print(f"   ⚠️  目標目錄已存在，跳過複製")
                else:
                    print(f"\n🚀 複製訓練數據集到 Google Drive...")
                    print(f"   來源: {training_dataset}")
                    print(f"   目標: {target_dir}")

                    # 複製整個時間戳目錄
                    shutil.copytree(latest, target_dir)

                    # 驗證結構
                    train_imgs = list((target_dir / "training_dataset" / "images" / "train").glob("*.jpg"))
                    val_imgs = list((target_dir / "training_dataset" / "images" / "val").glob("*.jpg"))

                    print(f"\n✓ 複製完成!")
                    print(f"   訓練集: {len(train_imgs)} 張")
                    print(f"   驗證集: {len(val_imgs)} 張")
            else:
                print(f"   ⚠️  找不到 training_dataset 子目錄")
        else:
            print(f"   ⚠️  relocated_samples 目錄為空")
    else:
        print(f"\n⚠️  本機尚未生成 relocated_samples")
        print(f"   請先執行: python label_samples.py")
        print(f"   然後選擇「4. 搬遷已標註樣本」")

    # 4. 複製 Colab Notebook
    print(f"\n📓 複製 Colab Notebook...")
    notebook_src = PROJECT_ROOT / "mosquito_training_colab.ipynb"
    notebook_dst = COLAB_TRAINING_BASE / "mosquito_training_colab.ipynb"

    if notebook_src.exists():
        shutil.copy2(notebook_src, notebook_dst)
        print(f"   ✓ {notebook_dst.name}")
    else:
        print(f"   ⚠️  找不到 Notebook: {notebook_src}")

    # 5. 顯示最終結構
    print(f"\n" + "=" * 60)
    print(f"📊 目錄結構檢查")
    print(f"=" * 60)

    print(f"\n✅ Colab 訓練基礎目錄:")
    print(f"   {COLAB_TRAINING_BASE}")

    print(f"\n📁 目錄內容:")
    for item in sorted(COLAB_TRAINING_BASE.iterdir()):
        if item.is_dir():
            # 統計子目錄內容
            if item.name == "relocated_samples":
                subdirs = list(item.iterdir())
                print(f"   📂 {item.name}/ ({len(subdirs)} 個時間戳目錄)")
                for subdir in sorted(subdirs):
                    if (subdir / "training_dataset").exists():
                        train_imgs = len(list((subdir / "training_dataset" / "images" / "train").glob("*.jpg")))
                        val_imgs = len(list((subdir / "training_dataset" / "images" / "val").glob("*.jpg")))
                        print(f"      └─ {subdir.name}/ (train: {train_imgs}, val: {val_imgs})")
            elif item.name == "models":
                models = list(item.glob("*.pt")) + list(item.glob("*.onnx")) + list(item.glob("*.rknn"))
                print(f"   📂 {item.name}/ ({len(models)} 個模型檔)")
            else:
                files = list(item.iterdir())
                print(f"   📂 {item.name}/ ({len(files)} 項)")
        else:
            size_mb = item.stat().st_size / 1024 / 1024
            print(f"   📄 {item.name} ({size_mb:.1f} MB)")

    print(f"\n" + "=" * 60)
    print(f"✅ 設置完成！")
    print(f"=" * 60)

    print(f"\n📥 下一步:")
    print(f"  1. 等待 Google Drive 同步完成（右下角檢查同步狀態）")
    print(f"  2. 前往 Colab: https://colab.research.google.com/")
    print(f"  3. 開啟: Colab Notebooks/mosquito-training/mosquito_training_colab.ipynb")
    print(f"  4. 執行所有 cells 開始訓練")

    return True

if __name__ == "__main__":
    try:
        success = setup_directory_structure()
        if not success:
            exit(1)
    except KeyboardInterrupt:
        print("\n\n⊗ 用戶中斷")
        exit(1)
    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
