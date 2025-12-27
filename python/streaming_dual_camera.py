"""
雙目攝像頭串流範例（含 AI 即時標註）
支援三種模式：並排顯示、單一視角、獨立串流

⚠️ 重要說明：
1. 本程式已完整整合 AI 檢測器 (mosquito_detector) 和串流伺服器 (streaming_server)
2. 只需運行此程式即可，無需分別啟動其他程式
3. AI 負載不會加倍：
   - 僅創建一個 MosquitoDetector 實例
   - 每幀只執行一次 AI 檢測
   - 檢測結果用於串流顯示
4. 記憶體和 CPU 使用最優化

使用方式：
    python streaming_dual_camera.py
"""

from streaming_server import StreamingServer
from mosquito_detector import MosquitoDetector
import cv2
import numpy as np
import sys
import time


def mode_1_side_by_side():
    """
    模式 1: 並排顯示（推薦）
    左側顯示 AI 標註，右側顯示原始畫面
    """
    print("=" * 60)
    print("模式 1: 雙目並排顯示（AI 標註 + 原始畫面）")
    print("=" * 60)

    # 初始化 AI 檢測器
    print("初始化 AI 檢測器...")
    detector = MosquitoDetector(
        model_path="models/mosquito",
        confidence_threshold=0.4
    )

    # 初始化串流伺服器
    server = StreamingServer(http_port=5000, fps=30)
    server.run(threaded=True)

    print(f"\n✓ 串流伺服器已啟動")
    print(f"✓ 模式：雙目並排（左側 AI 標註 + 右側原始）")
    print(f"\n📱 手機觀看: http://[你的IP]:5000")
    print(f"\n按 'q' 退出, 's' 儲存截圖")
    print()

    # 開啟雙目攝像頭（3840×1080）
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 3840)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    cap.set(cv2.CAP_PROP_FPS, 60)

    if not cap.isOpened():
        print("無法開啟攝像頭")
        return

    frame_count = 0
    fps_time = time.time()
    fps = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1

            # 分離左右畫面
            height, width = frame.shape[:2]
            mid = width // 2
            left_frame = frame[:, :mid]     # 左側：用於 AI 檢測
            right_frame = frame[:, mid:]    # 右側：原始畫面

            # AI 檢測與標註（左側畫面）
            detections, result_left = detector.detect(left_frame)
            result_left = detector.draw_detections(result_left, detections)

            # 添加資訊文字（左側）
            cv2.putText(result_left, "AI Detection (Left)", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(result_left, f"Detections: {len(detections)}", (10, 70),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

            # 添加資訊文字（右側）
            cv2.putText(right_frame, "Original (Right)", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

            # 計算 FPS
            if frame_count % 30 == 0:
                fps = 30 / (time.time() - fps_time)
                fps_time = time.time()

            cv2.putText(result_left, f"FPS: {fps:.1f}", (10, 110),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

            # 並排拼接
            combined = np.hstack([result_left, right_frame])

            # 添加分隔線
            mid_line = combined.shape[1] // 2
            cv2.line(combined, (mid_line, 0), (mid_line, combined.shape[0]),
                    (0, 255, 255), 2)

            # 更新串流
            server.update_frame(combined)

            # 本地預覽（可選）
            cv2.imshow('Dual Camera Stream - Side by Side', combined)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                filename = f"dual_stream_{frame_count}.jpg"
                cv2.imwrite(filename, combined)
                print(f"已儲存: {filename}")

    except KeyboardInterrupt:
        print("\n用戶中斷")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("串流已停止")


def mode_2_single_view():
    """
    模式 2: 單一視角（僅 AI 標註）
    僅串流左側攝像頭的 AI 標註結果
    """
    print("=" * 60)
    print("模式 2: 單一視角（僅 AI 標註）")
    print("=" * 60)

    # 初始化
    detector = MosquitoDetector(model_path="models/mosquito")
    server = StreamingServer(http_port=5000, fps=30)
    server.run(threaded=True)

    print(f"\n✓ 串流伺服器已啟動")
    print(f"✓ 模式：單一視角（左側 AI 標註）")
    print(f"\n📱 手機觀看: http://[你的IP]:5000")
    print()

    # 開啟攝像頭
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 3840)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # 僅使用左側畫面
            left_frame = frame[:, :1920]

            # AI 檢測與標註
            detections, result = detector.detect(left_frame)
            result = detector.draw_detections(result, detections)

            # 添加資訊
            cv2.putText(result, f"AI Mosquito Detection", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(result, f"Detections: {len(detections)}", (10, 70),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

            # 更新串流
            server.update_frame(result)

            # 本地預覽
            cv2.imshow('Single View - AI Detection', result)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        print("\n用戶中斷")
    finally:
        cap.release()
        cv2.destroyAllWindows()


def mode_3_dual_independent():
    """
    模式 3: 獨立雙串流
    左右攝像頭各自獨立串流
    """
    print("=" * 60)
    print("模式 3: 獨立雙串流")
    print("=" * 60)

    # 初始化
    detector = MosquitoDetector(model_path="models/mosquito")

    # 創建兩個串流伺服器
    server_left = StreamingServer(http_port=5000, fps=30)
    server_right = StreamingServer(http_port=5001, fps=30)

    server_left.run(threaded=True)
    server_right.run(threaded=True)

    print(f"\n✓ 左側串流（AI 標註）: http://[你的IP]:5000")
    print(f"✓ 右側串流（原始畫面）: http://[你的IP]:5001")
    print(f"\n按 'q' 退出")
    print()

    # 開啟攝像頭
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 3840)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # 分離左右畫面
            left_frame = frame[:, :1920]
            right_frame = frame[:, 1920:]

            # 左側：AI 檢測與標註
            detections, result_left = detector.detect(left_frame)
            result_left = detector.draw_detections(result_left, detections)
            cv2.putText(result_left, "Left - AI Detection", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            # 右側：原始畫面
            cv2.putText(right_frame, "Right - Original", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

            # 更新兩個串流
            server_left.update_frame(result_left)
            server_right.update_frame(right_frame)

            # 本地預覽
            preview = np.hstack([
                cv2.resize(result_left, (960, 540)),
                cv2.resize(right_frame, (960, 540))
            ])
            cv2.imshow('Dual Independent Streams', preview)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        print("\n用戶中斷")
    finally:
        cap.release()
        cv2.destroyAllWindows()


def main():
    """主程式"""
    print("=" * 60)
    print("雙目攝像頭串流系統（含 AI 即時標註）")
    print("=" * 60)
    print()
    print("請選擇串流模式：")
    print()
    print("1. 並排顯示（推薦）")
    print("   - 左側：AI 標註畫面")
    print("   - 右側：原始畫面")
    print("   - 一個串流地址")
    print()
    print("2. 單一視角")
    print("   - 僅顯示 AI 標註畫面")
    print("   - 帶寬消耗最低")
    print()
    print("3. 獨立雙串流")
    print("   - 左右攝像頭分別串流")
    print("   - 兩個串流地址")
    print()

    choice = input("請輸入選項 (1/2/3) [預設 1]: ").strip() or "1"
    print()

    if choice == "1":
        mode_1_side_by_side()
    elif choice == "2":
        mode_2_single_view()
    elif choice == "3":
        mode_3_dual_independent()
    else:
        print("無效選項，使用預設模式 1")
        mode_1_side_by_side()


if __name__ == "__main__":
    main()
