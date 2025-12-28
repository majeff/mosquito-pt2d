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
測試中等信心度樣本儲存功能
演示如何啟用自動樣本收集功能
"""

import cv2
import sys
from pathlib import Path
from mosquito_detector import MosquitoDetector

def test_uncertain_sample_saving():
    """測試中等信心度樣本儲存功能"""

    print("=" * 60)
    print("中等信心度樣本儲存功能測試")
    print("=" * 60)
    print()

    # 配置參數
    camera_id = 0  # 攝像頭 ID
    save_dir = "uncertain_samples"
    uncertain_range = (0.35, 0.65)  # 信心度範圍
    max_disk_usage = 20.0  # 最大磁碟使用率 20%

    print(f"攝像頭 ID: {camera_id}")
    print(f"儲存目錄: {save_dir}")
    print(f"信心度範圍: {uncertain_range[0]:.2f} - {uncertain_range[1]:.2f}")
    print(f"最大磁碟使用率: {max_disk_usage}%")
    print()

    # 初始化檢測器（啟用樣本儲存）
    try:
        print("初始化 AI 檢測器...")
        detector = MosquitoDetector(
            model_path="models/mosquito",
            confidence_threshold=0.3,  # 降低閾值以檢測更多目標
            save_uncertain_samples=True,
            uncertain_conf_range=uncertain_range,
            save_dir=save_dir,
            max_disk_usage_percent=max_disk_usage,
            save_annotations=True,      # 自動生成 YOLO 標註文件
            save_full_frame=False       # 僅儲存裁剪區域
        )
        print(f"✓ 檢測器已初始化，使用 {detector.backend.upper()} 後端")
        print(f"✓ 自動標註: 啟用")
        print(f"✓ 儲存模式: {'完整畫面' if detector.save_full_frame else '裁剪區域'}")
        print()
    except Exception as e:
        print(f"✗ 檢測器初始化失敗: {e}")
        return

    # 開啟攝像頭
    cap = cv2.VideoCapture(camera_id)
    if not cap.isOpened():
        print(f"✗ 無法開啟攝像頭 {camera_id}")
        return

    print("✓ 攝像頭已開啟")
    print()
    print("按鍵說明:")
    print("  q - 退出程式")
    print("  s - 顯示儲存統計")
    print("  p - 暫停/恢復樣本儲存")
    print()

    frame_count = 0
    paused = False

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("無法讀取影像")
                break

            frame_count += 1

            # AI 檢測（會自動儲存中等信心度樣本）
            detections, result = detector.detect(frame)

            # 在影像上繪製資訊
            info_y = 30
            cv2.putText(result, f"Frame: {frame_count}", (10, info_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            info_y += 30
            cv2.putText(result, f"Detections: {len(detections)}", (10, info_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            info_y += 30
            cv2.putText(result, f"Saved: {detector.save_counter}", (10, info_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            info_y += 30
            status = "PAUSED" if detector.storage_paused else "ACTIVE"
            color = (0, 0, 255) if detector.storage_paused else (0, 255, 0)
            cv2.putText(result, f"Storage: {status}", (10, info_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            # 標記檢測結果
            for det in detections:
                x, y, w, h = det['bbox']
                conf = det['confidence']

                # 根據信心度選擇顏色
                if uncertain_range[0] <= conf <= uncertain_range[1]:
                    color = (0, 255, 255)  # 黃色 - 會被儲存
                    label = f"SAVED: {conf:.2f}"
                elif conf > uncertain_range[1]:
                    color = (0, 255, 0)  # 綠色 - 高信心度
                    label = f"HIGH: {conf:.2f}"
                else:
                    color = (255, 0, 0)  # 藍色 - 低信心度
                    label = f"LOW: {conf:.2f}"

                cv2.rectangle(result, (x, y), (x + w, y + h), color, 2)
                cv2.putText(result, label, (x, y - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            # 顯示影像
            cv2.imshow('Uncertain Sample Saving Test', result)

            # 鍵盤控制
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("\n用戶中斷，退出...")
                break
            elif key == ord('s'):
                print(f"\n=== 儲存統計 ===")
                print(f"已儲存樣本數: {detector.save_counter}")
                print(f"儲存目錄: {detector.save_dir}")
                print(f"儲存狀態: {'暫停' if detector.storage_paused else '啟用'}")
                if Path(save_dir).exists():
                    files = list(Path(save_dir).glob("*.jpg"))
                    print(f"目錄中檔案數: {len(files)}")
                print()
            elif key == ord('p'):
                detector.storage_paused = not detector.storage_paused
                status = "已暫停" if detector.storage_paused else "已恢復"
                print(f"樣本儲存 {status}")

    except KeyboardInterrupt:
        print("\n\n用戶中斷（Ctrl+C）")
    except Exception as e:
        print(f"\n錯誤: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cap.release()
        cv2.destroyAllWindows()

        # 最終統計
        print()
        print("=" * 60)
        print("測試完成")
        print("=" * 60)
        print(f"總幀數: {frame_count}")
        print(f"已儲存樣本: {detector.save_counter}")
        print(f"儲存目錄: {detector.save_dir}")

        if Path(save_dir).exists():
            files = list(Path(save_dir).glob("*.jpg"))
            print(f"儲存檔案數: {len(files)}")
            if files:
                print(f"\n範例檔名:")
                for f in files[:5]:
                    print(f"  {f.name}")
                if len(files) > 5:
                    print(f"  ... 還有 {len(files) - 5} 個檔案")


if __name__ == "__main__":
    test_uncertain_sample_saving()
