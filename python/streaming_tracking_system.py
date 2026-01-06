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
                   DEFAULT_DEVICE_IP, DEFAULT_EXTERNAL_URL,
                   DEFAULT_MAX_SAMPLES, DEFAULT_SAVE_INTERVAL)
import sys
import cv2
import numpy as np
import time
import argparse
import signal
import logging
import traceback
from pathlib import Path

# 配置 logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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
                 enable_depth: bool = True,
                 enable_rtsp: bool = False,
                 rtsp_url: str = None,
                 rtsp_bitrate: int = 2000):
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
            enable_rtsp: 是否啟用 RTSP 推流
            rtsp_url: RTSP 推流地址
            rtsp_bitrate: RTSP 視頻碼率 (kbps)
        """
        logger.info("=" * 60)
        logger.info("🦟 蚊子追蹤系統 + 手機串流整合啟動")
        logger.info("=" * 60)

        # 系統配置
        self.dual_camera = dual_camera
        self.stream_mode = stream_mode
        self.camera_id = camera_id
        self.enable_depth = enable_depth and dual_camera  # 深度估計需要雙目攝像頭
        self._running = True  # 運行標誌，用於優雅退出

        # 統計資訊
        self.stats = {
            'total_frames': 0,
            'detections': 0,
            'tracking_active': False,
            'samples_saved': 0,
            'start_time': time.time()
        }

        # 1. 初始化 AI 檢測器（只創建一次！）
        logger.info("[1/5] 初始化 AI 檢測器...")
        self.detector = MosquitoDetector(
            model_path=model_path,
            confidence_threshold=DEFAULT_CONFIDENCE_THRESHOLD,
            imgsz=DEFAULT_IMGSZ,
            save_uncertain_samples=save_samples,
            uncertain_conf_range=sample_conf_range,
            save_dir="uncertain_samples",
            max_samples=DEFAULT_MAX_SAMPLES,
            save_interval=DEFAULT_SAVE_INTERVAL,
            save_annotations=True,
            save_full_frame=False
        )
        logger.info(f"      ✓ 使用 {self.detector.backend.upper()} 後端")
        if save_samples:
            logger.info(f"      ✓ 樣本儲存已啟用 (信心度 {sample_conf_range[0]}-{sample_conf_range[1]})")

        # 2. 初始化雲台控制器
        logger.info("[2/5] 初始化雲台控制器...")
        try:
            self.pt_controller = PT2DController(arduino_port)
            if self.pt_controller.is_connected:
                logger.info(f"      ✓ Arduino 已連接 ({arduino_port})")
                self.has_pt = True
                self.has_laser = True  # 雲台連接成功時啟用雷射功能
            else:
                logger.warning(f"      ⚠ 無法連接 Arduino，僅運行檢測模式")
                self.has_pt = False
                self.has_laser = False
        except Exception as e:
            logger.warning(f"      ⚠ 雲台初始化失敗: {e}")
            self.has_pt = False
            self.has_laser = False
            self.pt_controller = None

        # 3. 初始化追蹤器
        logger.info("[3/5] 初始化追蹤器...")
        if self.has_pt:
            self.tracker = MosquitoTracker(
                detector=self.detector,
                pt_controller=self.pt_controller
            )
            logger.info(f"      ✓ 追蹤器已就緒")
        else:
            self.tracker = None
            logger.warning(f"      ⚠ 追蹤器未啟用（需要雲台連接）")

        # 4. 初始化深度估計器（如果啟用）
        logger.info("[4/6] 初始化深度估計器...")
        if self.enable_depth:
            self.depth_estimator = DepthEstimator(
                focal_length=3.0,        # 鏡頭焦距 3.0mm
                baseline=120.0,          # 雙目基線 12cm
                image_width=1920,        # 單眼解析度
                sensor_width=5.0         # 感光元件寬度
            )
            logger.info(f"      ✓ 深度估計已啟用（測距範圍: 0.5-5m）")
        else:
            self.depth_estimator = None
            logger.info(f"      ⚠ 深度估計未啟用（需要雙目攝像頭）")

        # 5. 初始化串流伺服器
        logger.info("[5/6] 初始化串流伺服器...")
        self.server = StreamingServer(
            http_port=http_port,
            fps=30,
            rtsp_url=rtsp_url if enable_rtsp else None
        )
        self.server.run(threaded=True)
        logger.info(f"      ✓ 串流伺服器已啟動 (端口 {http_port})")

        # 6. 初始化 RTSP 推流（如果啟用）
        self.enable_rtsp = enable_rtsp
        self.rtsp_url = rtsp_url
        self.rtsp_bitrate = rtsp_bitrate
        if enable_rtsp and rtsp_url:
            logger.info("[6/6] 初始化 RTSP 推流...")
            logger.info(f"      ✓ RTSP 已配置")
            logger.info(f"         URL: {rtsp_url}")
            logger.info(f"         碼率: {rtsp_bitrate}kbps")
            logger.info(f"      ⏳ RTSP 推流將在第一幀時啟動...")
            # 稍後在第一幀時啟動 RTSP（需要知道幀尺寸）
            self.rtsp_enabled = False
            self.rtsp_initialized = False
        else:
            if enable_rtsp:
                logger.warning(f"⚠️  RTSP 已啟用但 URL 未設定")
            self.rtsp_enabled = False
            self.rtsp_initialized = True

        # 雙串流模式（僅在 dual_stream 模式）
        self.server_right = None
        if stream_mode == "dual_stream" and dual_camera:
            self.server_right = StreamingServer(http_port=http_port + 1, fps=30)
            self.server_right.run(threaded=True)
            logger.info(f"      ✓ 右側串流已啟動 (端口 {http_port + 1})")

        logger.info("=" * 60)
        logger.info("🎉 系統已完全啟動！")
        logger.info("=" * 60)
        # 生成訪問地址
        device_ip = DEFAULT_DEVICE_IP or "[你的IP]"
        local_url = f"http://{device_ip}:{http_port}"
        logger.info(f"📱 本機訪問: {local_url}")

        # 如果設置了外部 URL，顯示外部訪問方式
        if DEFAULT_EXTERNAL_URL:
            logger.info(f"🌐 遠端訪問: {DEFAULT_EXTERNAL_URL}")

        if self.server_right:
            right_url = f"http://{device_ip}:{http_port + 1}"
            logger.info(f"📱 右側視角（本機）: {right_url}")

        logger.info("ℹ️  系統配置:")
        logger.info(f"   - AI 檢測: ✓ 啟用 ({self.detector.backend.upper()})")
        logger.info(f"   - 雲台追蹤: {'✓ 啟用' if self.has_pt else '✗ 停用'}")
        logger.info(f"   - 雷射標記: {'✓ 啟用' if self.has_laser else '✗ 停用'}")
        logger.info(f"   - 深度估計: {'✓ 啟用' if self.enable_depth else '✗ 停用'}")
        logger.info(f"   - 樣本儲存: {'✓ 啟用' if save_samples else '✗ 停用'}")
        logger.info(f"   - 雙目攝像頭: {'✓ 啟用' if dual_camera else '✗ 停用'}")
        logger.info(f"   - 串流模式: {stream_mode}")

        logger.info("⚡ 性能說明:")
        logger.info(f"   - AI 負載: 每幀只執行一次檢測")
        logger.info(f"   - 記憶體: 單一檢測器實例")
        logger.info(f"   - CPU: 最優化利用")

        logger.info("🎮 控制方式:")
        logger.info("   Ctrl+C - 退出系統")
        logger.info("   (通過瀏覽器訪問 HTTP 串流查看影像)")

    def process_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        處理單幀影像（AI 檢測 + 追蹤 + 標註）

        ⚠️ 重要：此函數每幀只調用一次 AI 檢測，不會重複！
        """
        self.stats['total_frames'] += 1

        # 在第一幀時啟動 RTSP（需要知道幀尺寸）
        if self.enable_rtsp and not self.rtsp_initialized:
            h, w = frame.shape[:2]
            logger.info(f"🔧 正在初始化 RTSP...")
            logger.info(f"   RTSP URL: {self.rtsp_url}")
            logger.info(f"   RTSP 碼率: {self.rtsp_bitrate}kbps")
            logger.info(f"   幀尺寸: {w}x{h}")
            try:
                if self.server.enable_rtsp_push(w, h, bitrate=self.rtsp_bitrate):
                    logger.info("✅ RTSP 推流已啟動")
                    self.rtsp_enabled = True
                else:
                    logger.warning("⚠️  RTSP 推流啟動返回 False")
            except Exception as e:
                logger.error(f"❌ RTSP 初始化失敗: {e}")
                traceback.print_exc()
            finally:
                self.rtsp_initialized = True

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
        # 雙目模式：告知檢測器這是左眼畫面，只過濾上下邊緣
        detections, result_left = self.detector.detect(left_frame, is_dual_left=self.dual_camera)

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

        # 檢測數量
        cv2.putText(frame, f"Detections: {len(detections)}", (10, y_pos),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        y_pos += line_height

        # 追蹤狀態
        if not self.has_pt:
            tracking_text = "NONE"
            tracking_color = (128, 128, 128)
        elif self.stats['tracking_active']:
            tracking_text = "TRACKING"
            tracking_color = (0, 255, 0)
        else:
            tracking_text = "STANDBY"
            tracking_color = (128, 128, 128)

        cv2.putText(frame, f"Status: {tracking_text}", (10, y_pos),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, tracking_color, 2)
        y_pos += line_height

        # FPS
        elapsed = time.time() - self.stats['start_time']
        fps = self.stats['total_frames'] / elapsed if elapsed > 0 else 0
        cv2.putText(frame, f"FPS: {fps:.1f}", (10, y_pos),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

        # 串流資訊（右上角）
        cv2.putText(frame, f"Clients: {self.server.stats['clients']}",
                   (frame.shape[1] - 200, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # 時間（右下角）
        current_time = time.strftime("%H:%M:%S")
        time_font_size = 0.35
        time_thickness = 1
        time_size = cv2.getTextSize(current_time, cv2.FONT_HERSHEY_SIMPLEX, time_font_size, time_thickness)[0]
        time_x = frame.shape[1] - time_size[0] - 10
        time_y = frame.shape[0] - 10
        cv2.putText(frame, current_time, (time_x, time_y),
                   cv2.FONT_HERSHEY_SIMPLEX, time_font_size, (200, 200, 200), time_thickness)

    def run(self):
        """運行主循環"""
        # 設置信號處理器，確保 Ctrl+C 能立即被捕捉
        def signal_handler(signum, frame):
            logger.info("\n\n🛑 用戶中斷 (Ctrl+C)")
            self._running = False
            # 強制退出（如果正在執行阻塞操作）
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)

        # 開啟攝像頭
        cap = cv2.VideoCapture(self.camera_id)

        if self.dual_camera:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 3840)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
            cap.set(cv2.CAP_PROP_FPS, 60)

        if not cap.isOpened():
            logger.error("✗ 無法開啟攝像頭")
            return

        logger.info(f"✓ 攝像頭已開啟 (ID: {self.camera_id})")

        try:
            while self._running:  # 使用執行標誌控制迴圈
                ret, frame = cap.read()
                if not ret:
                    logger.error("✗ 無法讀取影像")
                    break

                # ⚡ 處理影像（每幀只執行一次 AI 檢測）
                result = self.process_frame(frame)

                # 更新串流
                if self.stream_mode == "dual_stream" and isinstance(result, tuple):
                    # 雙串流模式
                    self.server.update_frame(result[0])
                    if self.server_right:
                        self.server_right.update_frame(result[1])
                    # 不需要本地顯示（headless mode）
                else:
                    # 單一串流
                    self.server.update_frame(result)

                # 定期輸出狀態（每 100 幀）
                if self.stats['total_frames'] % 100 == 0:
                    elapsed = time.time() - self.stats['start_time']
                    fps = self.stats['total_frames'] / elapsed if elapsed > 0 else 0
                    avg_detections = self.stats['detections'] / self.stats['total_frames'] if self.stats['total_frames'] > 0 else 0
                    logger.info(f"[狀態] 幀數: {self.stats['total_frames']} | "
                          f"FPS: {fps:.1f} | "
                          f"總檢測: {self.stats['detections']} (平均 {avg_detections:.1f}/幀) | "
                          f"追蹤: {'啟用' if self.stats['tracking_active'] else '停用'}")

                # 簡單延時控制幀率
                time.sleep(0.03)  # ~30 FPS

        except Exception as e:
            logger.error(f"\n❌ 發生錯誤: {e}")

            traceback.print_exc()
            self._running = False

        finally:
            # 清理資源（確保執行）
            logger.info("\n⏳ 正在關閉系統...")
            self._cleanup(cap)

    def _cleanup(self, cap):
        """清理所有資源（優雅關閉）"""
        logger.info("   → 釋放攝像頭...")
        try:
            cap.release()
        except:
            pass

        logger.info("   → 關閉串流伺服器...")
        try:
            if self.server:
                self.server.shutdown()
        except:
            pass

        try:
            if self.server_right:
                self.server_right.shutdown()
        except:
            pass

        logger.info("   → 關閉雲台...")
        try:
            if self.pt_controller:
                self.pt_controller.close()
        except:
            pass

        logger.info("   → 關閉追蹤器...")
        try:
            if self.tracker:
                if hasattr(self.tracker, 'stop'):
                    self.tracker.stop()
        except:
            pass

        logger.info("   → 關閉檢測器...")
        try:
            if self.detector:
                if hasattr(self.detector, 'cleanup'):
                    self.detector.cleanup()
        except:
            pass

        # 顯示統計
        logger.info("=" * 60)
        logger.info("📊 系統統計")
        logger.info("=" * 60)
        logger.info(f"總幀數: {self.stats['total_frames']}")
        logger.info(f"總檢測: {self.stats['detections']}")
        if hasattr(self.detector, 'saved_sample_count'):
            logger.info(f"已儲存樣本: {self.detector.saved_sample_count}")
        elapsed = time.time() - self.stats['start_time']
        if elapsed > 0:
            logger.info(f"運行時間: {elapsed:.1f} 秒")
            logger.info(f"平均 FPS: {self.stats['total_frames'] / elapsed:.1f}")
        logger.info("=" * 60)
        logger.info("✅ 系統已關閉")


def detect_dual_camera(camera_id: int = 0) -> bool:
    """
    自動檢測是否為雙目攝像頭

    Args:
        camera_id: 攝像頭 ID

    Returns:
        True: 雙目攝像頭（寬度 >= 2560）
        False: 單目攝像頭
    """
    cap = cv2.VideoCapture(camera_id)
    if not cap.isOpened():
        logger.warning(f"⚠ 無法開啟攝像頭 {camera_id}，假設為單目")
        return False

    # 讀取一幀來獲取實際解析度
    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        logger.warning(f"⚠ 無法讀取攝像頭畫面，假設為單目")
        return False

    width = frame.shape[1]

    # 判斷邏輯：雙目攝像頭寬度通常 >= 2560 (兩個 1280x720 或更高)
    is_dual = width >= 2560

    logger.info(f"📷 攝像頭解析度: {width}x{frame.shape[0]}")
    logger.info(f"📷 檢測結果: {'雙目' if is_dual else '單目'} 攝像頭")

    return is_dual


def main():
    """主程式入口（參數型）"""
    parser = argparse.ArgumentParser(
        description='🦟 蚊子追蹤系統 + 手機串流',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  # 自動檢測模式（推薦）
  python streaming_tracking_system.py

  # 指定單目模式
  python streaming_tracking_system.py --single

  # 指定雙目模式
  python streaming_tracking_system.py --dual

  # 自定義串口和串流模式
  python streaming_tracking_system.py --port COM3 --mode side_by_side

  # 自定義 RTSP 推流地址
  python streaming_tracking_system.py --rtsp-url rtsp://192.168.1.100:8554/mosquito

  # 停用 RTSP 推流
  python streaming_tracking_system.py --no-rtsp
        """
    )

    # 串口參數
    default_port = 'COM3' if sys.platform.startswith('win') else '/dev/ttyUSB0'
    parser.add_argument('--port', '-p', type=str, default=default_port,
                       help=f'Arduino 串口 (預設: {default_port})')

    # 攝像頭參數
    parser.add_argument('--camera', '-c', type=int, default=0,
                       help='攝像頭 ID (預設: 0)')

    camera_group = parser.add_mutually_exclusive_group()
    camera_group.add_argument('--dual', action='store_true',
                             help='強制使用雙目模式')
    camera_group.add_argument('--single', action='store_true',
                             help='強制使用單目模式')

    # 串流參數
    parser.add_argument('--mode', '-m', type=str,
                       choices=['single', 'side_by_side', 'dual_stream'],
                       default='single',
                       help='串流模式 (預設: single)')

    parser.add_argument('--port-http', type=int, default=5000,
                       help='HTTP 串流端口 (預設: 5000)')

    # 模型參數
    parser.add_argument('--model', type=str, default='models/mosquito',
                       help='AI 模型路徑 (預設: models/mosquito)')

    # 樣本儲存參數
    parser.add_argument('--no-save-samples', action='store_true',
                       help='停用中等信心度樣本儲存')

    # RTSP 推流參數（預設停用）
    parser.add_argument('--rtsp', action='store_true',
                       help='啟用 RTSP 推流（預設停用）')
    parser.add_argument('--rtsp-url', type=str, default='rtsp://0.0.0.0:8554/mosquito',
                       help='RTSP 推流地址 (預設: rtsp://0.0.0.0:8554/mosquito)')
    parser.add_argument('--rtsp-bitrate', type=int, default=2000,
                       help='RTSP 視頻碼率 kbps (預設: 2000，範圍: 1000-3000)')

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("🦟 蚊子追蹤系統 + 手機串流")
    logger.info("=" * 60)

    # 自動檢測或使用指定的攝像頭模式
    if args.dual:
        dual_camera = True
        logger.info("📷 攝像頭模式: 雙目（手動指定）")
    elif args.single:
        dual_camera = False
        logger.info("📷 攝像頭模式: 單目（手動指定）")
    else:
        logger.info("📷 自動檢測攝像頭模式...")
        dual_camera = detect_dual_camera(args.camera)

    # 顯示配置
    logger.info("⚙️  系統配置:")
    logger.info(f"   - Arduino 串口: {args.port}")
    logger.info(f"   - 攝像頭 ID: {args.camera}")
    logger.info(f"   - 攝像頭模式: {'雙目' if dual_camera else '單目'}")
    logger.info(f"   - 串流模式: {args.mode}")
    logger.info(f"   - HTTP 端口: {args.port_http}")
    logger.info(f"   - 樣本儲存: {'停用' if args.no_save_samples else '啟用'}")
    logger.info(f"   - RTSP 推流: {'✓ 啟用' if args.rtsp else '✗ 停用 (預設)'}")
    if args.rtsp:
        logger.info(f"     → 推流地址: {args.rtsp_url}")
        logger.info(f"     → 碼率: {args.rtsp_bitrate} kbps")
    else:
        logger.info(f"     ℹ️  提示: 使用預設 HTTP-MJPEG 串流（若需 RTSP 請加上 --rtsp 參數）")

    # 創建並運行系統
    system = StreamingTrackingSystem(
        arduino_port=args.port,
        camera_id=args.camera,
        model_path=args.model,
        http_port=args.port_http,
        dual_camera=dual_camera,
        stream_mode=args.mode,
        save_samples=not args.no_save_samples,
        enable_rtsp=args.rtsp,
        rtsp_url=args.rtsp_url if args.rtsp else None,
        rtsp_bitrate=args.rtsp_bitrate
    )

    system.run()


if __name__ == "__main__":
    main()
