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
RTSP 串流範例
需要先安裝並啟動 MediaMTX: ./mediamtx

使用方式:
    python rtsp_example.py
"""

from streaming_server import StreamingServer
from mosquito_detector import MosquitoDetector
import cv2
import sys

def main():
    print("=" * 70)
    print("🦟 蚊子追蹤系統 - RTSP 串流示範")
    print("=" * 70)
    print()
    print("⚠️  前置準備：")
    print("   1. 安裝 MediaMTX (RTSP 伺服器):")
    print("      wget https://github.com/bluenviron/mediamtx/releases/download/v1.5.0/mediamtx_v1.5.0_linux_arm64v8.tar.gz")
    print("      tar -xzf mediamtx_v1.5.0_linux_arm64v8.tar.gz")
    print()
    print("   2. 啟動 MediaMTX（在另一個終端）:")
    print("      ./mediamtx")
    print()
    print("   3. 確認 FFmpeg 已安裝:")
    print("      sudo apt install ffmpeg")
    print()

    input("✓ 確認完成後按 Enter 繼續...")
    print()

    # 初始化 AI 檢測器
    print("[1/4] 初始化 AI 檢測器...")
    detector = MosquitoDetector(model_path="models/mosquito")
    print(f"      ✓ 使用 {detector.backend.upper()} 後端")

    # 初始化串流伺服器（HTTP + RTSP）
    print("[2/4] 初始化串流伺服器...")
    server = StreamingServer(
        http_port=5000,
        fps=30,
        rtsp_url="rtsp://0.0.0.0:8554/mosquito"
    )
    server.run(threaded=True)
    print("      ✓ HTTP 伺服器已啟動")

    # 開啟攝像頭
    print("[3/4] 開啟攝像頭...")
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("      ✗ 無法開啟攝像頭")
        sys.exit(1)

    # 獲取影像尺寸並啟動 RTSP 推流
    ret, frame = cap.read()
    if not ret:
        print("      ✗ 無法讀取影像")
        sys.exit(1)

    height, width = frame.shape[:2]
    print(f"      ✓ 攝像頭已開啟 ({width}x{height})")

    # 啟動 RTSP 推流
    print("[4/4] 啟動 RTSP 推流...")
    if server.enable_rtsp_push(width, height, bitrate=2000):
        print("      ✓ RTSP 推流已啟動")
    else:
        print("      ⚠ RTSP 推流啟動失敗，僅使用 HTTP-MJPEG")

    print()
    print("=" * 70)
    print("🎉 系統已完全啟動！")
    print("=" * 70)
    print()
    print("📱 觀看方式:")
    print(f"   HTTP-MJPEG: http://[你的IP]:5000")
    print(f"   RTSP:       rtsp://[你的IP]:8554/mosquito")
    print()
    print("🎬 RTSP 播放器:")
    print("   - PC: VLC Media Player")
    print("   - 手機: VLC for Mobile, RTSP Player")
    print()
    print("✨ 特色:")
    print("   ✓ 包含完整 AI 標註（檢測框、信心度、類別）")
    print("   ✓ HTTP + RTSP 雙串流同時運行")
    print("   ✓ 低延遲 (< 0.5s)")
    print()
    print("⌨️  按鍵操作:")
    print("   'q' - 退出系統")
    print("   's' - 儲存截圖")
    print()

    frame_count = 0
    detection_count = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("✗ 無法讀取影像")
                break

            frame_count += 1

            # AI 檢測與標註
            detections, result = detector.detect(frame)
            result = detector.draw_detections(result, detections)

            if detections:
                detection_count += len(detections)

            # 添加狀態資訊
            cv2.putText(result, f"Frame: {frame_count}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.putText(result, f"Detections: {len(detections)}", (10, 65),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.putText(result, f"HTTP Clients: {server.stats['clients']}", (10, 100),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            # RTSP 狀態指示
            rtsp_text = "RTSP: ON" if server.stats['rtsp_enabled'] else "RTSP: OFF"
            rtsp_color = (0, 255, 0) if server.stats['rtsp_enabled'] else (0, 0, 255)
            cv2.putText(result, rtsp_text, (10, 130),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, rtsp_color, 2)

            # 更新串流（同時推送到 HTTP 和 RTSP）
            server.update_frame(result)

            # 本地顯示
            cv2.imshow('RTSP Streaming with AI Detection', result)

            # 鍵盤控制
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("\n退出中...")
                break
            elif key == ord('s'):
                filename = f"capture_{frame_count}.jpg"
                cv2.imwrite(filename, result)
                print(f"✓ 已儲存: {filename}")

    except KeyboardInterrupt:
        print("\n\n用戶中斷 (Ctrl+C)")

    finally:
        # 清理資源
        print("\n清理資源...")
        server.cleanup()
        cap.release()
        cv2.destroyAllWindows()

        # 顯示統計
        print()
        print("=" * 70)
        print("統計資訊")
        print("=" * 70)
        print(f"總幀數: {frame_count}")
        print(f"總檢測: {detection_count}")
        print(f"HTTP 連線峰值: {server.stats['clients']}")
        print()
        print("系統已關閉")


if __name__ == "__main__":
    main()
