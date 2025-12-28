"""
完整蚊子追蹤系統 + 手機串流
整合 AI 檢測、雲台追蹤、影像串流於一體

⚠️ 這是唯一需要運行的程式！
- ✅ 包含 AI 檢測 (MosquitoDetector)
- ✅ 包含雲台控制 (PT2DController)
- ✅ 包含追蹤邏輯 (MosquitoTracker)
- ✅ 包含影像串流 (StreamingServer)
- ✅ AI 負載不會重複（每幀只檢測一次）
- ✅ 支援雙目攝像頭

使用方式：
    python streaming_tracking_system.py
"""

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

from streaming_server import StreamingServer
from mosquito_detector import MosquitoDetector
from mosquito_tracker import MosquitoTracker
from pt2d_controller import PT2DController
from depth_estimator import DepthEstimator
from config import (DEFAULT_CONFIDENCE_THRESHOLD, DEFAULT_IMGSZ,
                   DEFAULT_DEVICE_IP, DEFAULT_EXTERNAL_URL)
import cv2
import numpy as np
import sys
import time
from pathlib import Path


class StreamingTrackingSystem:
    """整合的蚊子追蹤與串流系統"""

    def __init__(self,
                 arduino_port: str = '/dev/ttyUSB0',
                 camera_id: int = 0,
                 model_path: str = "models/mosquito",
                 http_port: int = 5000,
                 dual_camera: bool = True,
                 stream_mode: str = "single",
                 save_samples: bool = True,
                 sample_conf_range: tuple = (0.35, 0.65),
                 enable_depth: bool = True):
        """
        初始化完整系統

        Args:
            arduino_port: Arduino 串口
            camera_id: 攝像頭 ID
            model_path: AI 模型路徑
            http_port: HTTP 串流端口
            dual_camera: 是否為雙目攝像頭
            stream_mode: 串流模式 ("side_by_side", "single", "dual_stream")
            save_samples: 是否儲存中等信心度樣本
            sample_conf_range: 樣本信心度範圍 (min, max)
            enable_depth: 是否啟用深度估計
        """
        print("=" * 60)
        print("🦟 蚊子追蹤系統 + 手機串流整合啟動")
        print("=" * 60)
        print()

        # 系統配置
        self.dual_camera = dual_camera
        self.stream_mode = stream_mode
        self.camera_id = camera_id
        self.enable_depth = enable_depth and dual_camera  # 深度估計需要雙目攝像頭

        # 統計資訊
        self.stats = {
            'total_frames': 0,
            'detections': 0,
            'tracking_active': False,
            'samples_saved': 0,
            'start_time': time.time()
        }

        # 1. 初始化 AI 檢測器（只創建一次！）
        print("[1/5] 初始化 AI 檢測器...")
        self.detector = MosquitoDetector(
            model_path=model_path,
            confidence_threshold=DEFAULT_CONFIDENCE_THRESHOLD,
            imgsz=DEFAULT_IMGSZ,
            save_uncertain_samples=save_samples,
            uncertain_conf_range=sample_conf_range,
            save_dir="uncertain_samples",
            max_disk_usage_percent=20.0,
            save_annotations=True,
            save_full_frame=False
        )
        print(f"      ✓ 使用 {self.detector.backend.upper()} 後端")
        if save_samples:
            print(f"      ✓ 樣本儲存已啟用 (信心度 {sample_conf_range[0]}-{sample_conf_range[1]})")

        # 2. 初始化雲台控制器
        print("[2/5] 初始化雲台控制器...")
        try:
            self.pt_controller = PT2DController(arduino_port)
            if self.pt_controller.is_connected:
                print(f"      ✓ Arduino 已連接 ({arduino_port})")
                self.has_pt = True
            else:
                print(f"      ⚠ 無法連接 Arduino，僅運行檢測模式")
                self.has_pt = False
        except Exception as e:
            print(f"      ⚠ 雲台初始化失敗: {e}")
            self.has_pt = False
            self.pt_controller = None

        # 3. 初始化追蹤器
        print("[3/5] 初始化追蹤器...")
        if self.has_pt:
            self.tracker = MosquitoTracker(
                detector=self.detector,
                pt_controller=self.pt_controller
            )
            print(f"      ✓ 追蹤器已就緒")
        else:
            self.tracker = None
            print(f"      ⚠ 追蹤器未啟用（需要雲台連接）")

        # 4. 初始化深度估計器（如果啟用）
        print("[4/6] 初始化深度估計器...")
        if self.enable_depth:
            self.depth_estimator = DepthEstimator(
                focal_length=3.0,        # 鏡頭焦距 3.0mm
                baseline=120.0,          # 雙目基線 12cm
                image_width=1920,        # 單眼解析度
                sensor_width=5.0         # 感光元件寬度
            )
            print(f"      ✓ 深度估計已啟用（測距範圍: 0.5-5m）")
        else:
            self.depth_estimator = None
            print(f"      ⚠ 深度估計未啟用（需要雙目攝像頭）")

        # 5. 初始化串流伺服器
        print("[5/6] 初始化串流伺服器...")
        self.server = StreamingServer(http_port=http_port, fps=30)
        self.server.run(threaded=True)
        print(f"      ✓ 串流伺服器已啟動 (端口 {http_port})")

        # 雙串流模式（僅在 dual_stream 模式）
        self.server_right = None
        if stream_mode == "dual_stream" and dual_camera:
            self.server_right = StreamingServer(http_port=http_port + 1, fps=30)
            self.server_right.run(threaded=True)
            print(f"      ✓ 右側串流已啟動 (端口 {http_port + 1})")

        print()
        print("=" * 60)
        print("🎉 系統已完全啟動！")
        print("=" * 60)
        print()
        # 生成訪問地址
        device_ip = DEFAULT_DEVICE_IP or "[你的IP]"
        local_url = f"http://{device_ip}:{http_port}"
        print(f"📱 本機訪問: {local_url}")

        # 如果設置了外部 URL，顯示外部訪問方式
        if DEFAULT_EXTERNAL_URL:
            print(f"🌐 遠端訪問: {DEFAULT_EXTERNAL_URL}")

        if self.server_right:
            right_url = f"http://{device_ip}:{http_port + 1}"
            print(f"📱 右側視角（本機）: {right_url}")
        print()
        print("ℹ️  系統配置:")
        print(f"   - AI 檢測: ✓ 啟用 ({self.detector.backend.upper()})")
        print(f"   - 雲台追蹤: {'✓ 啟用' if self.has_pt else '✗ 停用'}")
        print(f"   - 雷射標記: {'✓ 啟用' if self.has_laser else '✗ 停用'}")
        print(f"   - 深度估計: {'✓ 啟用' if self.enable_depth else '✗ 停用'}")
        print(f"   - 樣本儲存: {'✓ 啟用' if save_samples else '✗ 停用'}")
        print(f"   - 雙目攝像頭: {'✓ 啟用' if dual_camera else '✗ 停用'}")
        print(f"   - 串流模式: {stream_mode}")
        print()
        print("⚡ 性能說明:")
        print(f"   - AI 負載: 每幀只執行一次檢測")
        print(f"   - 記憶體: 單一檢測器實例")
        print(f"   - CPU: 最優化利用")
        print()
        print("按鍵操作:")
        print("   'q' - 退出系統")
        print("   't' - 切換追蹤模式")
        print("   's' - 儲存截圖")
        print("   'l' - 切換雷射" + (" (已啟用)" if self.has_laser else " (未啟用)"))
        print("   'h' - 雲台歸位")
        print()

    def process_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        處理單幀影像（AI 檢測 + 追蹤 + 標註）

        ⚠️ 重要：此函數每幀只調用一次 AI 檢測，不會重複！
        """
        self.stats['total_frames'] += 1

        # 分離左右畫面（如果是雙目）
        if self.dual_camera:
            height, width = frame.shape[:2]
            mid = width // 2
            left_frame = frame[:, :mid]
            right_frame = frame[:, mid:]
        else:
            left_frame = frame
            right_frame = None

        # ⚡ AI 檢測（每幀只執行一次！）
        detections, result_left = self.detector.detect(left_frame)

        # 記錄檢測數量
        if detections:
            self.stats['detections'] += len(detections)
            
            # 🎯 深度估計（如果啟用且有右眼影像）
            if self.depth_estimator and right_frame is not None:
                for detection in detections:
                    bbox = detection.get('bbox')
                    if bbox:
                        x1, y1, x2, y2 = bbox
                        # 估計深度
                        depth_info = self.depth_estimator.estimate_depth_for_detection(
                            left_frame, right_frame, (x1, y1, x2, y2)
                        )
                        if depth_info:
                            detection['depth'] = depth_info['depth']
                            detection['distance_cm'] = depth_info['distance_cm']

        # 追蹤控制（如果啟用）
        if self.tracker and detections:
            self.tracker.update(detections)
            self.stats['tracking_active'] = True
        else:
            self.stats['tracking_active'] = False

        # 繪製 AI 標註（包含深度資訊）
        result_left = self._draw_detections_with_depth(result_left, detections)

        # 添加系統資訊
        self._draw_system_info(result_left, detections)

        # 根據串流模式組合畫面
        if self.stream_mode == "side_by_side" and right_frame is not None:
            # 並排顯示
            cv2.putText(right_frame, "Original (Right)", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            combined = np.hstack([result_left, right_frame])
            # 添加分隔線
            mid = combined.shape[1] // 2
            cv2.line(combined, (mid, 0), (mid, combined.shape[0]),
                    (0, 255, 255), 2)
            return combined

        elif self.stream_mode == "dual_stream" and right_frame is not None:
            # 雙串流模式
            cv2.putText(right_frame, "Original (Right)", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            return result_left, right_frame

        else:
            # 單一視角
            return result_left

    def _draw_detections_with_depth(self, frame: np.ndarray, detections: list) -> np.ndarray:
        """
        繪製檢測結果（包含深度資訊）

        Args:
            frame: 影像幀
            detections: 檢測結果列表

        Returns:
            標註後的影像
        """
        # 先繪製基本檢測框
        frame = self.detector.draw_detections(frame, detections)

        # 如果啟用深度估計，添加深度資訊
        if self.depth_estimator and detections:
            for detection in detections:
                bbox = detection.get('bbox')
                depth = detection.get('depth')
                distance_cm = detection.get('distance_cm')

                if bbox and distance_cm:
                    x1, y1, x2, y2 = bbox
                    
                    # 在檢測框下方顯示距離資訊
                    distance_text = f"{distance_cm:.1f}cm"
                    text_size = cv2.getTextSize(distance_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
                    text_x = x1
                    text_y = y2 + 25
                    
                    # 繪製背景
                    cv2.rectangle(frame,
                                (text_x, text_y - text_size[1] - 5),
                                (text_x + text_size[0] + 5, text_y + 5),
                                (0, 0, 0), -1)
                    
                    # 繪製距離文字（橙色）
                    cv2.putText(frame, distance_text,
                              (text_x + 2, text_y),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)

        return frame

    def _draw_system_info(self, frame: np.ndarray, detections: list):
        """在畫面上繪製系統資訊"""
        y_pos = 30
        line_height = 35

        # 標題
        cv2.putText(frame, "AI 蚊子追蹤", (10, y_pos),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        y_pos += line_height

        # 檢測數量
        cv2.putText(frame, f"檢測數: {len(detections)}", (10, y_pos),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        y_pos += line_height

        # 追蹤狀態
        tracking_color = (0, 255, 0) if self.stats['tracking_active'] else (128, 128, 128)
        tracking_text = "追蹤中" if self.stats['tracking_active'] else "待命"
        cv2.putText(frame, f"狀態: {tracking_text}", (10, y_pos),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, tracking_color, 2)
        y_pos += line_height

        # FPS
        elapsed = time.time() - self.stats['start_time']
        fps = self.stats['total_frames'] / elapsed if elapsed > 0 else 0
        cv2.putText(frame, f"幀率: {fps:.1f}", (10, y_pos),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

        # 串流資訊（右上角）
        cv2.putText(frame, f"客户端: {self.server.stats['clients']}",
                   (frame.shape[1] - 200, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    def run(self):
        """運行主循環"""
        # 開啟攝像頭
        cap = cv2.VideoCapture(self.camera_id)

        if self.dual_camera:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 3840)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
            cap.set(cv2.CAP_PROP_FPS, 60)

        if not cap.isOpened():
            print("✗ 無法開啟攝像頭")
            return

        print(f"✓ 攝像頭已開啟 (ID: {self.camera_id})")
        print()

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    print("✗ 無法讀取影像")
                    break

                # ⚡ 處理影像（每幀只執行一次 AI 檢測）
                result = self.process_frame(frame)

                # 更新串流
                if self.stream_mode == "dual_stream" and isinstance(result, tuple):
                    # 雙串流模式
                    self.server.update_frame(result[0])
                    if self.server_right:
                        self.server_right.update_frame(result[1])
                    display = np.hstack([
                        cv2.resize(result[0], (960, 540)),
                        cv2.resize(result[1], (960, 540))
                    ])
                else:
                    # 單一串流
                    self.server.update_frame(result)
                    display = result

                # 本地預覽
                cv2.imshow('蚊子追蹤系統', display)

                # 鍵盤控制
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("\n退出中...")
                    break
                elif key == ord('t'):
                    if self.tracker:
                        print(f"追蹤模式: {'啟用' if not self.stats['tracking_active'] else '停用'}")
                elif key == ord('s'):
                    filename = f"capture_{int(time.time())}.jpg"
                    cv2.imwrite(filename, display)
                    print(f"已儲存: {filename}")
                elif key == ord('h'):
                    if self.pt_controller:
                        self.pt_controller.home()
                        print("雲台歸位中...")
                    else:
                        print("雲台未連接")

        except KeyboardInterrupt:
            print("\n\n用戶中斷 (Ctrl+C)")

        finally:
            # 清理資源
            cap.release()
            cv2.destroyAllWindows()
            if self.pt_controller:
                self.pt_controller.close()

            # 顯示統計
            print()
            print("=" * 60)
            print("系統統計")
            print("=" * 60)
            print(f"總幀數: {self.stats['total_frames']}")
            print(f"總檢測: {self.stats['detections']}")
            if hasattr(self.detector, 'saved_sample_count'):
                print(f"已儲存樣本: {self.detector.saved_sample_count}")
            elapsed = time.time() - self.stats['start_time']
            print(f"運行時間: {elapsed:.1f} 秒")
            print(f"平均 FPS: {self.stats['total_frames'] / elapsed:.1f}")
            print()


def main():
    """主程式入口"""
    print()
    print("=" * 60)
    print("🦟 蚊子追蹤系統 + 手機串流")
    print("=" * 60)
    print()

    # 檢查是否使用 Windows（可能需要調整串口）
    default_port = 'COM3' if sys.platform.startswith('win') else '/dev/ttyUSB0'

    # 簡單配置
    print("系統配置:")
    print()
    arduino_port = input(f"Arduino 串口 [{default_port}]: ").strip() or default_port

    print()
    print("串流模式:")
    print("1. 並排顯示 - 左側 AI 標註 + 右側原始")
    print("2. 單一視角（預設）- 僅 AI 標註")
    print("3. 獨立雙串流 - 左右分別串流")
    mode_choice = input("選擇模式 [2]: ").strip() or "2"

    mode_map = {
        "1": "side_by_side",
        "2": "single",
        "3": "dual_stream"
    }
    stream_mode = mode_map.get(mode_choice, "single")

    print()

    # 創建並運行系統
    system = StreamingTrackingSystem(
        arduino_port=arduino_port,
        camera_id=0,
        model_path="models/mosquito",
        http_port=5000,
        dual_camera=True,
        stream_mode=stream_mode
    )

    system.run()


if __name__ == "__main__":
    main()
