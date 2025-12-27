#!/usr/bin/env python3
"""
模型比較腳本

用途：比較舊模型與新訓練模型的性能差異
"""

from ultralytics import YOLO
from pathlib import Path
import json

def compare_models(old_model='models/mosquito_yolov8.pt',
                   new_model='training_runs/mosquito_finetune/weights/best.pt',
                   dataset_yaml='training_dataset/dataset.yaml'):
    """
    比較兩個模型的性能

    Args:
        old_model: 舊模型路徑
        new_model: 新模型路徑
        dataset_yaml: 測試數據集配置
    """
    old_model = Path(old_model)
    new_model = Path(new_model)
    dataset_yaml = Path(dataset_yaml)

    # 檢查檔案
    if not old_model.exists():
        print(f"❌ 找不到舊模型: {old_model}")
        return
    if not new_model.exists():
        print(f"❌ 找不到新模型: {new_model}")
        return
    if not dataset_yaml.exists():
        print(f"❌ 找不到數據集: {dataset_yaml}")
        return

    print("="*60)
    print("模型性能比較")
    print("="*60)

    results = {}

    # 評估兩個模型
    for name, model_path in [('舊模型', old_model), ('新模型', new_model)]:
        print(f"\n評估 {name}: {model_path}")
        print("-"*60)

        model = YOLO(str(model_path))
        val_results = model.val(
            data=str(dataset_yaml),
            imgsz=320,
            batch=16,
            conf=0.25,
            iou=0.6,
            verbose=False
        )

        results[name] = {
            'mAP50': val_results.box.map50,
            'mAP50-95': val_results.box.map,
            'precision': val_results.box.mp,
            'recall': val_results.box.mr,
            'speed': sum(val_results.speed.values())
        }

        print(f"  mAP50: {results[name]['mAP50']:.4f}")
        print(f"  mAP50-95: {results[name]['mAP50-95']:.4f}")
        print(f"  Precision: {results[name]['precision']:.4f}")
        print(f"  Recall: {results[name]['recall']:.4f}")
        print(f"  速度: {results[name]['speed']:.2f} ms/image")

    # 計算改善
    print("\n" + "="*60)
    print("改善情況")
    print("="*60)

    improvements = {}
    for metric in ['mAP50', 'mAP50-95', 'precision', 'recall']:
        old_val = results['舊模型'][metric]
        new_val = results['新模型'][metric]
        diff = new_val - old_val
        pct = (diff / old_val * 100) if old_val > 0 else 0
        improvements[metric] = {'diff': diff, 'pct': pct}

        symbol = '↑' if diff > 0 else '↓' if diff < 0 else '='
        color = '✓' if diff > 0 else '✗' if diff < 0 else '•'
        print(f"{color} {metric:12s}: {diff:+.4f} ({pct:+.2f}%) {symbol}")

    # 速度比較
    old_speed = results['舊模型']['speed']
    new_speed = results['新模型']['speed']
    speed_diff = new_speed - old_speed
    speed_pct = (speed_diff / old_speed * 100) if old_speed > 0 else 0
    symbol = '↓' if speed_diff < 0 else '↑' if speed_diff > 0 else '='
    color = '✓' if speed_diff < 0 else '✗' if speed_diff > 0 else '•'
    print(f"{color} 推理時間    : {speed_diff:+.2f} ms ({speed_pct:+.2f}%) {symbol}")

    # 總體建議
    print("\n" + "="*60)
    print("建議")
    print("="*60)

    overall_improvement = (
        improvements['mAP50']['pct'] +
        improvements['precision']['pct'] +
        improvements['recall']['pct']
    ) / 3

    if overall_improvement > 5:
        print("✓ 新模型顯著優於舊模型，建議部署！")
        print("\n部署步驟:")
        print(f"  1. 備份舊模型:")
        print(f"     cp {old_model} {old_model}.backup")
        print(f"  2. 部署新模型:")
        print(f"     cp {new_model} {old_model}")
        print(f"  3. 轉換為 RKNN 格式:")
        print(f"     python convert_to_rknn.py --input {old_model}")
    elif overall_improvement > 0:
        print("• 新模型略優於舊模型")
        print("  建議繼續收集樣本後再訓練")
    elif overall_improvement > -5:
        print("• 新模型與舊模型性能相近")
        print("  建議:")
        print("    - 檢查訓練參數")
        print("    - 收集更多多樣化樣本")
        print("    - 增加訓練輪數")
    else:
        print("✗ 新模型劣於舊模型")
        print("  不建議部署，建議:")
        print("    - 檢查數據集品質")
        print("    - 檢查標註是否正確")
        print("    - 檢查訓練參數設定")

    # 保存比較結果
    comparison_file = Path('model_comparison.json')
    with open(comparison_file, 'w', encoding='utf-8') as f:
        json.dump({
            'old_model': str(old_model),
            'new_model': str(new_model),
            'results': {k: {kk: float(vv) for kk, vv in v.items()}
                       for k, v in results.items()},
            'improvements': {k: {kk: float(vv) for kk, vv in v.items()}
                           for k, v in improvements.items()},
            'overall_improvement': float(overall_improvement)
        }, f, indent=2, ensure_ascii=False)

    print(f"\n比較結果已保存到: {comparison_file}")

    return results, improvements

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='比較兩個模型')
    parser.add_argument('--old', type=str,
                       default='models/mosquito_yolov8.pt',
                       help='舊模型路徑')
    parser.add_argument('--new', type=str,
                       default='training_runs/mosquito_finetune/weights/best.pt',
                       help='新模型路徑')
    parser.add_argument('--data', type=str,
                       default='training_dataset/dataset.yaml',
                       help='數據集配置')

    args = parser.parse_args()

    try:
        compare_models(args.old, args.new, args.data)
    except Exception as e:
        print(f"\n❌ 比較錯誤: {e}")
        import traceback
        traceback.print_exc()
