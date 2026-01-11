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
from config_loader import config
import sys
import cv2
import numpy as np
import time
import argparse
import signal
import logging
import traceback
from pathlib import Path
from collections import deque

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
                 save_samples: bool = None,
                 sample_conf_range: tuple = None,
                 enable_depth: bool = True,
                 enable_rtsp: bool = False,
                 rtsp_url: str = None,
                 rtsp_bitrate: int = 2000):
        """初始化完整系統"""
        logger.info("=" * 60)
        logger.info("🦟 蚊子追蹤系統 + 手機串流整合啟動")
        logger.info("=" * 60)

        # 系統配置
        self.dual_camera = dual_camera
        self.stream_mode = stream_mode
        self.camera_id = camera_id
        self.enable_depth = enable_depth and dual_camera  # 深度估計需要雙目攝像頭
        self._running = True  # 運行標誌，用於優雅退出
        self.has_pt = False
        self.has_laser = False

        # 攝像頭解析度配置（從 config_loader 讀取）
        self.camera_width = config.camera_dual_width if dual_camera else 1920
        self.camera_height = config.camera_dual_height if dual_camera else 1080
        self.camera_fps = config.camera_dual_fps if dual_camera else 60

        # 統計資訊
        self.stats = {
            'total_frames': 0,
            'unique_targets': 0,          # 唯一目標數（去重後）
            'tracking_active': False,
            'samples_saved': 0,
            'start_time': time.time(),
            'last_illumination_info': {}
        }

        # 唯一目標追蹤（簡單去重機制）
        self.active_tracks = {}           # {track_id: {'last_seen': time, 'center': (x,y), 'lost_frames': int}}
        self.next_track_id = 1
        self.track_distance_threshold = 100  # 像素距離閾值（<100認為是同一目標）
        self.track_lost_frames_max = 30     # 超過30幀未見視為消失

        # 單目過濾器追蹤數據（用於時間連續性和運動合理性檢查）
        self.detection_history = {}       # {track_id: {'frames': int, 'positions': deque, 'static_frames': int}}
        self._deque_cls = deque

        # 1. 初始化 AI 檢測器（只創建一次！）
        logger.info("[1/5] 初始化 AI 檢測器...")

        if save_samples is None:
            save_samples = config.save_uncertain_samples
        if sample_conf_range is None:
            sample_conf_range = config.uncertain_conf_range

        self.detector = MosquitoDetector(
            model_path=model_path,
            confidence_threshold=config.confidence_threshold,
            imgsz=config.imgsz,
            save_uncertain_samples=save_samples,
            uncertain_conf_range=sample_conf_range,
            save_dir=config.sample_collection_dir,
            max_samples=config.max_samples,
            save_interval=config.save_interval,
            save_annotations=True,
            save_full_frame=False
        )
        logger.info(f"      ✓ 使用 {self.detector.backend.upper()} 後端")
        if save_samples:
            logger.info(f"      ✓ 樣本儲存已啟用 (信心度 {sample_conf_range[0]}-{sample_conf_range[1]})")

        # 2. 初始化雲台控制器與追蹤器
        logger.info("[2/5] 初始化雲台控制器...")
        try:
            self.pt_controller = PT2DController(config.arduino_port)
            if self.pt_controller.is_connected:
                logger.info(f"      ✓ Arduino 已連接 ({config.arduino_port})")
                self.has_pt = True
                self.has_laser = True  # 雲台連接成功時啟用雷射功能
                logger.info("[3/5] 初始化追蹤器...")
                self.tracker = MosquitoTracker(
                    arduino_port=config.arduino_port,
                    camera_left_id=config.left_camera_id,
                    camera_right_id=config.right_camera_id,
                    camera_width=self.camera_width,
                    camera_height=self.camera_height
                )
                logger.info("      ✓ 追蹤器已就緒")
            else:
                logger.warning("      ⚠ 無法連接 Arduino，僅運行檢測模式")
                self.has_pt = False
                self.has_laser = False
                self.tracker = None
        except Exception as e:
            logger.warning(f"      ⚠ 雲台初始化失敗: {e}")
            self.has_pt = False
            self.has_laser = False
            self.tracker = None
            self.pt_controller = None

        # 4. 初始化深度估計器（如果啟用）
        logger.info("[4/6] 初始化深度估計器...")
        if self.enable_depth:
            self.depth_estimator = None  # 將在首幀時根據實際解析度初始化
            logger.info("      ⏳ 深度估計器將在首幀時初始化（根據實際解析度）")
        else:
            self.depth_estimator = None
            logger.info("      ⚠ 深度估計未啟用（需要雙目攝像頭）")

        # 5. 初始化串流伺服器
        logger.info("[5/6] 初始化串流伺服器...")
        self.server = StreamingServer(
            http_port=http_port,
            fps=config.stream_fps,
            rtsp_url=config.rtsp_url if enable_rtsp else None
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
            logger.info("      ⏳ RTSP 推流將在第一幀時啟動...")
            self.rtsp_enabled = False
            self.rtsp_initialized = False
        else:
            if enable_rtsp:
                logger.warning("⚠️  RTSP 已啟用但 URL 未設定")
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
        device_ip = config.device_ip or "[你的IP]"
        local_url = f"http://{device_ip}:{http_port}"
        logger.info(f"📱 本機訪問: {local_url}")
        if config.external_url:
            logger.info(f"🌐 遠端訪問: {config.external_url}")
        if self.server_right:
            logger.info(f"📱 右側視角（本機）: http://{device_ip}:{http_port + 1}")

        logger.info("ℹ️  系統配置:")
        logger.info(f"   - AI 檢測: ✓ 啟用 ({self.detector.backend.upper()})")
        logger.info(f"   - 雲台追蹤: {'✓ 啟用' if self.has_pt else '✗ 停用'}")
        logger.info(f"   - 雷射標記: {'✓ 啟用' if self.has_laser else '✗ 停用'}")
        logger.info(f"   - 深度估計: {'✓ 啟用' if self.enable_depth else '✗ 停用'}")
        logger.info(f"   - 樣本儲存: {'✓ 啟用' if save_samples else '✗ 停用'}")
        logger.info(f"   - 雙目攝像頭: {'✓ 啟用' if dual_camera else '✗ 停用'}")
        logger.info(f"   - 串流模式: {stream_mode}")

        logger.info("⚡ 性能說明:")
        logger.info("   - AI 負載: 每幀只執行一次檢測")
        logger.info("   - 記憶體: 單一檢測器實例")
        logger.info("   - CPU: 最優化利用")

        logger.info("🎮 控制方式:")
        logger.info("   Ctrl+C - 退出系統")
        logger.info("   (通過瀏覽器訪問 HTTP 串流查看影像)")

    def process_frame(self, frame: np.ndarray) -> np.ndarray:
        """處理單幀影像（AI 檢測 + 追蹤 + 標註）"""
        self.stats['total_frames'] += 1

        if self.enable_rtsp and not self.rtsp_initialized:
            h, w = frame.shape[:2]
            logger.info("🔧 正在初始化 RTSP...")
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

        if self.dual_camera:
            height, width = frame.shape[:2]
            mid = width // 2
            left_frame = frame[:, :mid]
            right_frame = frame[:, mid:]

            if self.enable_depth and self.depth_estimator is None:
                single_width = left_frame.shape[1]
                logger.info(f"🔧 初始化深度估計器（單眼解析度: {single_width}×{left_frame.shape[0]}）")
                self.depth_estimator = DepthEstimator(
                    focal_length=3.0,
                    baseline=120.0,
                    image_width=single_width,
                    sensor_width=5.0
                )
                logger.info("      ✓ 深度估計已啟用（測距範圍: 0.5-5m）")
        else:
            left_frame = frame
            right_frame = None

        detections, result_left, illumination_info = self.detector.detect(left_frame, is_dual_left=self.dual_camera)

        if detections:
            detections = [d for d in detections if d.get('confidence', 0) < 1.0]
            if len([d for d in detections if d.get('confidence', 0) >= 1.0]) > 0:
                logger.debug(f"已過濾 {len([d for d in detections if d.get('confidence', 0) >= 1.0])} 個信心度=1.0的異常檢測")

        if detections:
            self._update_unique_targets(detections)

            if self.depth_estimator and right_frame is not None:
                valid_detections = []
                for detection in detections:
                    bbox = detection.get('bbox')
                    if bbox:
                        x1, y1, x2, y2 = bbox
                        depth_info = self.depth_estimator.estimate_depth_for_detection(
                            left_frame, right_frame, (x1, y1, x2, y2)
                        )
                        if depth_info:
                            detection['depth'] = depth_info['depth']
                            detection['distance_cm'] = depth_info['distance_cm']
                            detection['object_size_mm'] = depth_info.get('object_size_mm', 0)
                            from config_loader import config
                            obj_size = depth_info.get('object_size_mm', 0)
                            if config.min_mosquito_size_mm <= obj_size <= config.max_mosquito_size_mm:
                                valid_detections.append(detection)
                        else:
                            valid_detections.append(detection)
                    else:
                        valid_detections.append(detection)
                detections = valid_detections
            else:
                detections = self._apply_monocular_filters(detections)

        if self.tracker and detections:
            self.tracker.update(detections)
            self.stats['tracking_active'] = True
        else:
            self.stats['tracking_active'] = False

        self.stats['last_illumination_info'] = illumination_info

        if detections:
            self._log_detection_details(detections)

        result_left = self._draw_detections_with_depth(result_left, detections)
        self._draw_system_info(result_left, detections, illumination_info)

        if self.stream_mode == "side_by_side" and right_frame is not None:
            cv2.putText(right_frame, "Original (Right)", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            combined = np.hstack([result_left, right_frame])
            mid = combined.shape[1] // 2
            cv2.line(combined, (mid, 0), (mid, combined.shape[0]), (0, 255, 255), 2)
            return combined

        if self.stream_mode == "dual_stream" and right_frame is not None:
            cv2.putText(right_frame, "Original (Right)", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            return result_left, right_frame

        return result_left

    def _draw_detections_with_depth(self, frame: np.ndarray, detections: list) -> np.ndarray:
        frame = self.detector.draw_detections(frame, detections)
        if self.depth_estimator and detections:
            for detection in detections:
                bbox = detection.get('bbox')
                depth = detection.get('depth')
                distance_cm = detection.get('distance_cm')
                if bbox and distance_cm:
                    x1, y1, x2, y2 = bbox
                    obj_size = detection.get('object_size_mm', 0)
                    distance_text = f"{distance_cm:.1f}cm | {obj_size:.1f}mm" if obj_size > 0 else f"{distance_cm:.1f}cm"
                    text_size = cv2.getTextSize(distance_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
                    text_x = x1
                    text_y = y2 + 25
                    cv2.rectangle(frame,
                                  (text_x, text_y - text_size[1] - 5),
                                  (text_x + text_size[0] + 5, text_y + 5),
                                  (0, 0, 0), -1)
                    cv2.putText(frame, distance_text,
                                (text_x + 2, text_y),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
        return frame

    def _update_unique_targets(self, detections: list):
        current_time = time.time()
        for track_id in self.active_tracks:
            self.active_tracks[track_id]['lost_frames'] += 1

        for detection in detections:
            center = detection.get('center', (0, 0))
            matched_track_id = None
            min_distance = self.track_distance_threshold
            for track_id, track_info in self.active_tracks.items():
                if track_info['lost_frames'] > self.track_lost_frames_max:
                    continue
                track_center = track_info['center']
                distance = np.sqrt((center[0] - track_center[0])**2 + (center[1] - track_center[1])**2)
                if distance < min_distance:
                    min_distance = distance
                    matched_track_id = track_id
            if matched_track_id is not None:
                self.active_tracks[matched_track_id]['center'] = center
                self.active_tracks[matched_track_id]['last_seen'] = current_time
                self.active_tracks[matched_track_id]['lost_frames'] = 0
                detection['track_id'] = matched_track_id
            else:
                new_track_id = self.next_track_id
                self.next_track_id += 1
                self.active_tracks[new_track_id] = {
                    'center': center,
                    'last_seen': current_time,
                    'lost_frames': 0
                }
                self.stats['unique_targets'] += 1
                detection['track_id'] = new_track_id

        tracks_to_remove = [
            track_id for track_id, track_info in self.active_tracks.items()
            if track_info['lost_frames'] > self.track_lost_frames_max
        ]
        for track_id in tracks_to_remove:
            del self.active_tracks[track_id]
            if track_id in self.detection_history:
                del self.detection_history[track_id]

    def _apply_monocular_filters(self, detections: list) -> list:
        try:
            from config_loader import config
            ENABLE_BBOX_SIZE_FILTER = config.enable_bbox_size_filter
            MIN_BBOX_SIZE_PX = config.min_bbox_size_px
            MAX_BBOX_SIZE_PX = config.max_bbox_size_px
            ENABLE_ASPECT_RATIO_FILTER = config.enable_aspect_ratio_filter
            MIN_ASPECT_RATIO = config.min_aspect_ratio
            MAX_ASPECT_RATIO = config.max_aspect_ratio
            ENABLE_TEMPORAL_FILTER = config.enable_temporal_filter
            MIN_CONSECUTIVE_FRAMES = config.min_consecutive_frames
            ENABLE_MOTION_FILTER = config.enable_motion_filter
            MAX_MOVEMENT_PX_PER_FRAME = config.max_movement_px_per_frame
            MAX_STATIC_FRAMES = config.max_static_frames
            STATIC_THRESHOLD_PX = config.static_threshold_px
        except ImportError:
            ENABLE_BBOX_SIZE_FILTER = True
            MIN_BBOX_SIZE_PX = 10
            MAX_BBOX_SIZE_PX = 200
            ENABLE_ASPECT_RATIO_FILTER = True
            MIN_ASPECT_RATIO = 0.3
            MAX_ASPECT_RATIO = 3.0
            ENABLE_TEMPORAL_FILTER = True
            MIN_CONSECUTIVE_FRAMES = 3
            ENABLE_MOTION_FILTER = True
            MAX_MOVEMENT_PX_PER_FRAME = 150
            MAX_STATIC_FRAMES = 60
            STATIC_THRESHOLD_PX = 5

        valid_detections = []
        for detection in detections:
            bbox = detection.get('bbox')
            if not bbox:
                continue

            x1, y1, x2, y2 = bbox
            width = x2 - x1
            height = y2 - y1
            center = detection.get('center', ((x1 + x2) // 2, (y1 + y2) // 2))
            track_id = detection.get('track_id')

            if ENABLE_BBOX_SIZE_FILTER:
                size = max(width, height)
                if size < MIN_BBOX_SIZE_PX or size > MAX_BBOX_SIZE_PX:
                    logger.debug(f"框大小過濾: {size}px 不在 {MIN_BBOX_SIZE_PX}-{MAX_BBOX_SIZE_PX}px 範圍")
                    continue

            if ENABLE_ASPECT_RATIO_FILTER:
                aspect_ratio = width / max(height, 1)
                if aspect_ratio < MIN_ASPECT_RATIO or aspect_ratio > MAX_ASPECT_RATIO:
                    logger.debug(f"寬高比過濾: {aspect_ratio:.2f} 不在 {MIN_ASPECT_RATIO}-{MAX_ASPECT_RATIO} 範圍")
                    continue

            if ENABLE_TEMPORAL_FILTER and track_id is not None:
                if track_id not in self.detection_history:
                    self.detection_history[track_id] = {
                        'frames': 1,
                        'positions': self._deque_cls(maxlen=10),
                        'static_frames': 0
                    }
                    self.detection_history[track_id]['positions'].append(center)
                else:
                    self.detection_history[track_id]['frames'] += 1
                    self.detection_history[track_id]['positions'].append(center)

                if self.detection_history[track_id]['frames'] < MIN_CONSECUTIVE_FRAMES:
                    logger.debug(f"時間連續性過濾: track_{track_id} 僅出現 {self.detection_history[track_id]['frames']} 幀")
                    continue

            if ENABLE_MOTION_FILTER and track_id is not None and track_id in self.detection_history:
                history = self.detection_history[track_id]
                positions = history['positions']

                if len(positions) >= 2:
                    prev_pos = positions[-2]
                    curr_pos = center
                    movement = np.sqrt((curr_pos[0] - prev_pos[0])**2 + (curr_pos[1] - prev_pos[1])**2)

                    if movement > MAX_MOVEMENT_PX_PER_FRAME:
                        logger.debug(f"運動過快過濾: track_{track_id} 移動 {movement:.1f}px > {MAX_MOVEMENT_PX_PER_FRAME}px")
                        continue

                    if movement < STATIC_THRESHOLD_PX:
                        history['static_frames'] += 1
                        if history['static_frames'] > MAX_STATIC_FRAMES:
                            logger.debug(f"靜止過久過濾: track_{track_id} 靜止 {history['static_frames']} 幀")
                            continue
                    else:
                        history['static_frames'] = 0

            valid_detections.append(detection)

        return valid_detections

    def _log_detection_details(self, detections: list):
        try:
            from config_loader import config
            MIN_MOSQUITO_SIZE_MM = config.min_mosquito_size_mm
            MAX_MOSQUITO_SIZE_MM = config.max_mosquito_size_mm
            MIN_BBOX_SIZE_PX = config.min_bbox_size_px
            MAX_BBOX_SIZE_PX = config.max_bbox_size_px
            MIN_ASPECT_RATIO = config.min_aspect_ratio
            MAX_ASPECT_RATIO = config.max_aspect_ratio
        except ImportError:
            MIN_MOSQUITO_SIZE_MM = 3
            MAX_MOSQUITO_SIZE_MM = 15
        # 詳細日誌留空（維持原行為）

    def run(self):
        cap = cv2.VideoCapture(self.camera_id)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.camera_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.camera_height)
        cap.set(cv2.CAP_PROP_FPS, self.camera_fps)

        if not cap.isOpened():
            logger.error(f"❌ 無法打開攝像頭 {self.camera_id}")
            return

        logger.info(f"🎥 攝像頭已打開: {self.camera_width}x{self.camera_height}@{self.camera_fps}fps")

        try:
            frame_count = 0
            start_time = time.time()

            while self._running:
                ret, frame = cap.read()
                if not ret:
                    logger.error("❌ 無法讀取攝像頭畫面")
                    break

                processed_frame = self.process_frame(frame)

                if self.stream_mode == "dual_stream" and isinstance(processed_frame, tuple):
                    left_frame, right_frame = processed_frame
                    self.server.push_frame(left_frame)
                    if self.server_right:
                        self.server_right.push_frame(right_frame)
                else:
                    self.server.push_frame(processed_frame)

                frame_count += 1

                if frame_count % 100 == 0:
                    elapsed_time = time.time() - start_time
                    fps = 100 / elapsed_time if elapsed_time > 0 else 0
                    logger.info(f"📊 統計資訊: {fps:.1f} FPS, "
                               f"總幀數: {frame_count}, "
                               f"唯一目標: {self.stats['unique_targets']}, "
                               f"追蹤狀態: {'🟢' if self.stats['tracking_active'] else '🔴'}")
                    start_time = time.time()

        except Exception as e:
            logger.error(f"❌ 系統運行異常: {e}")
            traceback.print_exc()
        finally:
            cap.release()
            logger.info("📹 攝像頭已釋放")

    def stop(self):
        logger.info("🛑 停止系統...")
        self._running = False
        try:
            if getattr(self, 'server', None):
                self.server.stop()
            if getattr(self, 'server_right', None):
                self.server_right.stop()
            if getattr(self, 'pt_controller', None):
                self.pt_controller.disconnect()
            if getattr(self, 'detector', None):
                self.detector.cleanup()
        except Exception as e:
            logger.error(f"停止系統時發生錯誤: {e}")


def signal_handler(sig, frame):
    global system
    logger.info('\n👋 收到退出信號，正在關閉系統...')
    if system:
        system.stop()


def main():
    global system
    parser = argparse.ArgumentParser(description='🦟 蚊子追蹤系統 + 手機串流整合')
    parser.add_argument('--port', '-p', type=str, default=config.arduino_port,
                       help='Arduino 串口 (預設: config.arduino_port)')
    parser.add_argument('--camera', '-c', type=int, default=config.left_camera_id,
                       help='攝像頭 ID (預設: config.left_camera_id)')
    parser.add_argument('--model', type=str, default="models/mosquito",
                       help='AI 模型路徑 (預設: models/mosquito)')
    parser.add_argument('--single', action='store_true',
                       help='強制單目攝像頭模式')
    parser.add_argument('--dual', action='store_true',
                       help='強制雙目攝像頭模式')
    parser.add_argument('--mode', '-m', type=str, default="single",
                       choices=["single", "side_by_side", "dual_stream"],
                       help='串流模式 (預設: single)')
    parser.add_argument('--port-http', type=int, default=config.stream_port,
                       help='HTTP 串流端口 (預設: config.stream_port)')
    parser.add_argument('--save-samples', action='store_true',
                       help='儲存中等信心度樣本')
    parser.add_argument('--no-save-samples', dest='save_samples', action='store_false',
                       help='不儲存中等信心度樣本')
    parser.set_defaults(save_samples=config.save_uncertain_samples)
    parser.add_argument('--rtsp', action='store_true',
                       help='啟用 RTSP 推流')
    parser.add_argument('--rtsp-url', type=str, default=config.rtsp_url,
                       help='RTSP 推流地址')
    parser.add_argument('--rtsp-bitrate', type=int, default=2000,
                       help='RTSP 碼率 (kbps, 預設: 2000)')

    args = parser.parse_args()

    dual_camera = args.dual or (not args.single and config.camera_dual_width > 1920)
    if args.single:
        logger.info("📷 強制使用單目攝像頭模式")
    elif args.dual:
        logger.info("📷 強制使用雙目攝像頭模式")
    else:
        logger.info(f"📷 自動檢測攝像頭模式: {'雙目' if dual_camera else '單目'}")

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    system = StreamingTrackingSystem(
        arduino_port=args.port,
        camera_id=args.camera,
        model_path=args.model,
        http_port=args.port_http,
        dual_camera=dual_camera,
        stream_mode=args.mode,
        save_samples=args.save_samples,
        enable_depth=dual_camera,
        enable_rtsp=args.rtsp,
        rtsp_url=args.rtsp_url,
        rtsp_bitrate=args.rtsp_bitrate
    )

    logger.info("🚀 系統開始運行... 按 Ctrl+C 退出")
    try:
        system.run()
    except KeyboardInterrupt:
        logger.info("👋 使用者中斷，正在關閉系統...")
    except Exception as e:
        logger.error(f"系統運行錯誤: {e}")
        traceback.print_exc()
    finally:
        system.stop()
        logger.info("✅ 系統已關閉")


if __name__ == "__main__":
    system = None
    main()

        self.track_lost_frames_max = 30     # 超過30幀未見視為消失

        # 單目過濾器追蹤數據（用於時間連續性和運動合理性檢查）
        self.detection_history = {}       # {track_id: {'frames': int, 'positions': deque, 'static_frames': int}}
        from collections import deque
        self._deque_cls = deque  # 供後續方法使用，避免未定義

        # 1. 初始化 AI 檢測器（只創建一次！）
        logger.info("[1/5] 初始化 AI 檢測器...")

        # 如果未指定參數，則使用配置文件中的值
        if save_samples is None:
            save_samples = config.save_uncertain_samples
        if sample_conf_range is None:
            sample_conf_range = config.uncertain_conf_range

        self.detector = MosquitoDetector(
            model_path=model_path,
            confidence_threshold=config.confidence_threshold,  # 使用新配置
            imgsz=config.imgsz,  # 使用新配置
            save_uncertain_samples=save_samples,
            uncertain_conf_range=sample_conf_range,  # 使用傳入的參數
            save_dir=config.sample_collection_dir,  # 與收集/標註路徑一致
            max_samples=config.max_samples,  # 使用新配置
            save_interval=config.save_interval,  # 使用新配置
            save_annotations=True,
            save_full_frame=False
        )
        logger.info(f"      ✓ 使用 {self.detector.backend.upper()} 後端")
        if save_samples:
            logger.info(f"      ✓ 樣本儲存已啟用 (信心度 {sample_conf_range[0]}-{sample_conf_range[1]})")

        # 2. 初始化雲台控制器與追蹤器（單一路徑，避免未定義狀態）
        logger.info("[2/5] 初始化雲台控制器...")
        try:
            self.pt_controller = PT2DController(config.arduino_port)
            if self.pt_controller.is_connected:
                logger.info(f"      ✓ Arduino 已連接 ({config.arduino_port})")
                self.has_pt = True
                self.has_laser = True  # 雲台連接成功時啟用雷射功能
                # 3. 初始化追蹤器（依賴雲台連線）
                logger.info("[3/5] 初始化追蹤器...")
                self.tracker = MosquitoTracker(
                    arduino_port=config.arduino_port,
                    camera_left_id=config.left_camera_id,
                    camera_right_id=config.right_camera_id,
                    camera_width=self.camera_width,
                    camera_height=self.camera_height
                )
                logger.info(f"      ✓ 追蹤器已就緒")
            else:
                logger.warning(f"      ⚠ 無法連接 Arduino，僅運行檢測模式")
                self.has_pt = False
                self.has_laser = False
                self.tracker = None
        except Exception as e:
            logger.warning(f"      ⚠ 雲台初始化失敗: {e}")
            self.has_pt = False
            self.has_laser = False
            self.tracker = None
            self.pt_controller = None

        # 4. 初始化深度估計器（如果啟用）
        logger.info("[4/6] 初始化深度估計器...")
        if self.enable_depth:
            # 深度估計器將在 run() 中根據實際解析度初始化
            self.depth_estimator = None
            logger.info(f"      ⏳ 深度估計器將在首幀時初始化（根據實際解析度）")
        else:
            self.depth_estimator = None
            logger.info(f"      ⚠ 深度估計未啟用（需要雙目攝像頭）")

        # 5. 初始化串流伺服器
        logger.info("[5/6] 初始化串流伺服器...")
        self.server = StreamingServer(
            http_port=config.stream_port,  # 使用新配置
            fps=config.stream_fps,  # 使用新配置
            rtsp_url=config.rtsp_url if enable_rtsp else None  # 使用新配置
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
        device_ip = config.device_ip or "[你的IP]"
        local_url = f"http://{device_ip}:{http_port}"
        logger.info(f"📱 本機訪問: {local_url}")

        # 如果設置了外部 URL，顯示外部訪問方式
        if config.external_url:
            logger.info(f"🌐 遠端訪問: {config.external_url}")

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

            # 首次運行時初始化深度估計器（使用實際解析度）
            if self.enable_depth and self.depth_estimator is None:
                single_width = left_frame.shape[1]
                logger.info(f"🔧 初始化深度估計器（單眼解析度: {single_width}×{left_frame.shape[0]}）")
                self.depth_estimator = DepthEstimator(
                    focal_length=3.0,        # 鏡頭焦距 3.0mm
                    baseline=120.0,          # 雙目基線 12cm
                    image_width=single_width,  # 使用實際單眼解析度
                    sensor_width=5.0         # 感光元件寬度
                )
                logger.info(f"      ✓ 深度估計已啟用（測距範圍: 0.5-5m）")
        else:
            left_frame = frame
            right_frame = None

        # ⚡ AI 檢測（每幀只執行一次！）
        # 雙目模式：告知檢測器這是左眼畫面，只過濾上下邊緣
        detections, result_left, illumination_info = self.detector.detect(left_frame, is_dual_left=self.dual_camera)

        # 過濾異常信心度值（排除 confidence == 1.0 的異常檢測）
        if detections:
            detections = [d for d in detections if d.get('confidence', 0) < 1.0]
            if len([d for d in detections if d.get('confidence', 0) >= 1.0]) > 0:
                logger.debug(f"已過濾 {len([d for d in detections if d.get('confidence', 0) >= 1.0])} 個信心度=1.0的異常檢測")

        # 追蹤唯一目標
        if detections:
            self._update_unique_targets(detections)

            # 🎯 深度估計與尺寸過濾（如果啟用且有右眼影像）
            if self.depth_estimator and right_frame is not None:
                valid_detections = []
                for detection in detections:
                    bbox = detection.get('bbox')
                    if bbox:
                        x1, y1, x2, y2 = bbox
                        # 估計深度與實際尺寸
                        depth_info = self.depth_estimator.estimate_depth_for_detection(
                            left_frame, right_frame, (x1, y1, x2, y2)
                        )
                        if depth_info:
                            detection['depth'] = depth_info['depth']
                            detection['distance_cm'] = depth_info['distance_cm']
                            detection['object_size_mm'] = depth_info.get('object_size_mm', 0)

                            # 尺寸過濾：只保留合理尺寸的檢測
                            from config_loader import config  # 使用新的配置加載模組
                            obj_size = depth_info.get('object_size_mm', 0)
                            if config.min_mosquito_size_mm <= obj_size <= config.max_mosquito_size_mm:
                                valid_detections.append(detection)

                        else:
                            # 無法估計深度時保留（避免過度過濾）
                            valid_detections.append(detection)
                    else:
                        valid_detections.append(detection)

                # 更新為過濾後的檢測結果
                detections = valid_detections
            else:
                # 單目模式或無深度估計：使用像素級過濾
                detections = self._apply_monocular_filters(detections)

        # 追蹤控制（如果啟用）
        if self.tracker and detections:
            self.tracker.update(detections)
            self.stats['tracking_active'] = True
        else:
            self.stats['tracking_active'] = False

        # 儲存光照度資訊
        self.stats['last_illumination_info'] = illumination_info

        # 輸出檢測物件詳細資訊
        if detections:
            self._log_detection_details(detections)

        # 繪製 AI 標註（包含深度資訊）
        result_left = self._draw_detections_with_depth(result_left, detections)

        # 添加系統資訊
        self._draw_system_info(result_left, detections, illumination_info)

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
                    obj_size = detection.get('object_size_mm', 0)

                    # 在檢測框下方顯示距離與尺寸資訊
                    if obj_size > 0:
                        distance_text = f"{distance_cm:.1f}cm | {obj_size:.1f}mm"
                    else:
                        distance_text = f"{distance_cm:.1f}cm"
                    text_size = cv2.getTextSize(distance_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
                    text_x = x1
                    text_y = y2 + 25

                    # 繪製背景
                    cv2.rectangle(frame,
                                (text_x, text_y - text_size[1] - 5),
                                (text_x + text_size[0] + 5, text_y + 5),
                                (0, 0, 0), -1)

                    # 繪製距離與尺寸文字（橙色）
                    cv2.putText(frame, distance_text,
                              (text_x + 2, text_y),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)

        return frame

    def _update_unique_targets(self, detections: list):
        """更新唯一目標追蹤（簡單去重機制）"""
        current_time = time.time()

        # 標記所有追蹤為「可能消失」
        for track_id in self.active_tracks:
            self.active_tracks[track_id]['lost_frames'] += 1

        # 為每個檢測分配或匹配追蹤ID
        for detection in detections:
            center = detection.get('center', (0, 0))
            matched_track_id = None
            min_distance = self.track_distance_threshold

            # 尋找最近的現有追蹤
            for track_id, track_info in self.active_tracks.items():
                if track_info['lost_frames'] > self.track_lost_frames_max:
                    continue  # 已消失的追蹤不匹配

                track_center = track_info['center']
                distance = np.sqrt((center[0] - track_center[0])**2 +
                                 (center[1] - track_center[1])**2)

                if distance < min_distance:
                    min_distance = distance
                    matched_track_id = track_id

            # 更新或創建追蹤
            if matched_track_id is not None:
                # 匹配到現有追蹤
                self.active_tracks[matched_track_id]['center'] = center
                self.active_tracks[matched_track_id]['last_seen'] = current_time
                self.active_tracks[matched_track_id]['lost_frames'] = 0
                detection['track_id'] = matched_track_id
            else:
                # 新目標
                new_track_id = self.next_track_id
                self.next_track_id += 1
                self.active_tracks[new_track_id] = {
                    'center': center,
                    'last_seen': current_time,
                    'lost_frames': 0
                }
                self.stats['unique_targets'] += 1
                detection['track_id'] = new_track_id

        # 清理長時間未見的追蹤
        tracks_to_remove = [
            track_id for track_id, track_info in self.active_tracks.items()
            if track_info['lost_frames'] > self.track_lost_frames_max
        ]
        for track_id in tracks_to_remove:
            del self.active_tracks[track_id]
            # 清理單目過濾器歷史數據
            if track_id in self.detection_history:
                del self.detection_history[track_id]

    def _apply_monocular_filters(self, detections: list) -> list:
        """
        單目模式過濾器（無深度資訊時使用）
        包含：檢測框大小、寬高比、時間連續性、運動合理性
        """
        # 從配置加載篩選參數
        try:
            from config_loader import config  # 使用新的配置加載模組
            ENABLE_BBOX_SIZE_FILTER = config.enable_bbox_size_filter
            MIN_BBOX_SIZE_PX = config.min_bbox_size_px
            MAX_BBOX_SIZE_PX = config.max_bbox_size_px
            ENABLE_ASPECT_RATIO_FILTER = config.enable_aspect_ratio_filter
            MIN_ASPECT_RATIO = config.min_aspect_ratio
            MAX_ASPECT_RATIO = config.max_aspect_ratio
            ENABLE_TEMPORAL_FILTER = config.enable_temporal_filter
            MIN_CONSECUTIVE_FRAMES = config.min_consecutive_frames
            ENABLE_MOTION_FILTER = config.enable_motion_filter
            MAX_MOVEMENT_PX_PER_FRAME = config.max_movement_px_per_frame
            MAX_STATIC_FRAMES = config.max_static_frames
            STATIC_THRESHOLD_PX = config.static_threshold_px
        except ImportError:
            # 默認值
            ENABLE_BBOX_SIZE_FILTER = True
            MIN_BBOX_SIZE_PX = 10
            MAX_BBOX_SIZE_PX = 200
            ENABLE_ASPECT_RATIO_FILTER = True
            MIN_ASPECT_RATIO = 0.3
            MAX_ASPECT_RATIO = 3.0
            ENABLE_TEMPORAL_FILTER = True
            MIN_CONSECUTIVE_FRAMES = 3
            ENABLE_MOTION_FILTER = True
            MAX_MOVEMENT_PX_PER_FRAME = 150
            MAX_STATIC_FRAMES = 60
            STATIC_THRESHOLD_PX = 5

        valid_detections = []

        for detection in detections:
            bbox = detection.get('bbox')
            if not bbox:
                continue

            x1, y1, x2, y2 = bbox
            width = x2 - x1
            height = y2 - y1
            center = detection.get('center', ((x1+x2)//2, (y1+y2)//2))
            track_id = detection.get('track_id')

            # 1. 檢測框大小過濾
            if ENABLE_BBOX_SIZE_FILTER:
                size = max(width, height)
                if size < MIN_BBOX_SIZE_PX or size > MAX_BBOX_SIZE_PX:
                    logger.debug(f"框大小過濾: {size}px 不在 {MIN_BBOX_SIZE_PX}-{MAX_BBOX_SIZE_PX}px 範圍")
                    continue

            # 2. 寬高比過濾
            if ENABLE_ASPECT_RATIO_FILTER:
                aspect_ratio = width / max(height, 1)
                if aspect_ratio < MIN_ASPECT_RATIO or aspect_ratio > MAX_ASPECT_RATIO:
                    logger.debug(f"寬高比過濾: {aspect_ratio:.2f} 不在 {MIN_ASPECT_RATIO}-{MAX_ASPECT_RATIO} 範圍")
                    continue

            # 3. 時間連續性過濾
            if ENABLE_TEMPORAL_FILTER and track_id is not None:
                if track_id not in self.detection_history:
                    self.detection_history[track_id] = {
                        'frames': 1,
                        'positions': self._deque_cls(maxlen=10),
                        'static_frames': 0
                    }
                    self.detection_history[track_id]['positions'].append(center)
                else:
                    self.detection_history[track_id]['frames'] += 1
                    self.detection_history[track_id]['positions'].append(center)

                # 檢查是否達到最少幀數
                if self.detection_history[track_id]['frames'] < MIN_CONSECUTIVE_FRAMES:
                    logger.debug(f"時間連續性過濾: track_{track_id} 僅出現 {self.detection_history[track_id]['frames']} 幀")
                    continue

            # 4. 運動合理性過濾
            if ENABLE_MOTION_FILTER and track_id is not None and track_id in self.detection_history:
                history = self.detection_history[track_id]
                positions = history['positions']

                if len(positions) >= 2:
                    prev_pos = positions[-2]
                    curr_pos = center
                    movement = np.sqrt((curr_pos[0] - prev_pos[0])**2 + (curr_pos[1] - prev_pos[1])**2)

                    # 移動過快過濾
                    if movement > MAX_MOVEMENT_PX_PER_FRAME:
                        logger.debug(f"運動過快過濾: track_{track_id} 移動 {movement:.1f}px > {MAX_MOVEMENT_PX_PER_FRAME}px")
                        continue

                    # 靜止過久過濾
                    if movement < STATIC_THRESHOLD_PX:
                        history['static_frames'] += 1
                        if history['static_frames'] > MAX_STATIC_FRAMES:
                            logger.debug(f"靜止過久過濾: track_{track_id} 靜止 {history['static_frames']} 幀")
                            continue
                    else:
                        history['static_frames'] = 0

            # 通過所有過濾器
            valid_detections.append(detection)

        return valid_detections

    def _log_detection_details(self, detections: list):
        """輸出檢測物件的詳細資訊"""
        # 從配置加載物理參數
        try:
            from config_loader import config  # 使用新的配置加載模組
            MIN_MOSQUITO_SIZE_MM = config.min_mosquito_size_mm
            MAX_MOSQUITO_SIZE_MM = config.max_mosquito_size_mm
            MIN_BBOX_SIZE_PX = config.min_bbox_size_px
            MAX_BBOX_SIZE_PX = config.max_bbox_size_px
            MIN_ASPECT_RATIO = config.min_aspect_ratio
            MAX_ASPECT_RATIO = config.max_aspect_ratio
        except ImportError:
            # 默認值
            MIN_MOSQUITO_SIZE_MM = 3
            MAX_MOSQUITO_SIZE_MM = 15


    def run(self):
        """運行系統主循環"""
        # 初始化攝像頭
        cap = cv2.VideoCapture(self.camera_id)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.camera_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.camera_height)
        cap.set(cv2.CAP_PROP_FPS, self.camera_fps)

        if not cap.isOpened():
            logger.error(f"❌ 無法打開攝像頭 {self.camera_id}")
            return

        logger.info(f"🎥 攝像頭已打開: {self.camera_width}x{self.camera_height}@{self.camera_fps}fps")

        try:
            frame_count = 0
            start_time = time.time()

            while self._running:
                ret, frame = cap.read()
                if not ret:
                    logger.error("❌ 無法讀取攝像頭畫面")
                    break

                # 處理影像幀
                processed_frame = self.process_frame(frame)

                # 發送到串流伺服器
                if self.stream_mode == "dual_stream" and isinstance(processed_frame, tuple):
                    left_frame, right_frame = processed_frame
                    self.server.push_frame(left_frame)
                    if self.server_right:
                        self.server_right.push_frame(right_frame)
                else:
                    # 統一處理所有非 dual_stream 模式的情況
                    self.server.push_frame(processed_frame)

                frame_count += 1

                # 每100幀輸出一次統計資訊
                if frame_count % 100 == 0:
                    elapsed_time = time.time() - start_time
                    fps = 100 / elapsed_time if elapsed_time > 0 else 0
                    logger.info(f"📊 統計資訊: {fps:.1f} FPS, "
                               f"總幀數: {frame_count}, "
                               f"唯一目標: {self.stats['unique_targets']}, "
                               f"追蹤狀態: {'🟢' if self.stats['tracking_active'] else '🔴'}")
                    start_time = time.time()

        except Exception as e:
            logger.error(f"❌ 系統運行異常: {e}")
            traceback.print_exc()
        finally:
            cap.release()
            logger.info("📹 攝像頭已釋放")


    def stop(self):
        """停止系統"""
        logger.info("🛑 停止系統...")
        self._running = False


def signal_handler(sig, frame):
    """信號處理器，用於優雅退出"""
    logger.info('\n👋 收到退出信號，正在關閉系統...')
    if 'system' in locals():
        system.stop()


def main():
    parser = argparse.ArgumentParser(description='🦟 蚊子追蹤系統 + 手機串流整合')
    parser.add_argument('--port', '-p', type=str, default=config.arduino_port,
                       help='Arduino 串口 (預設: config.arduino_port)')
    parser.add_argument('--camera', '-c', type=int, default=config.left_camera_id,
                       help='攝像頭 ID (預設: config.left_camera_id)')
    parser.add_argument('--model', type=str, default="models/mosquito",
                       help='AI 模型路徑 (預設: models/mosquito)')
    parser.add_argument('--single', action='store_true',
                       help='強制單目攝像頭模式')
    parser.add_argument('--dual', action='store_true',
                       help='強制雙目攝像頭模式')
    parser.add_argument('--mode', '-m', type=str, default="single",
                       choices=["single", "side_by_side", "dual_stream"],
                       help='串流模式 (預設: single)')
    parser.add_argument('--port-http', type=int, default=config.stream_port,
                       help='HTTP 串流端口 (預設: config.stream_port)')
    parser.add_argument('--save-samples', action='store_true',
                       help='儲存中等信心度樣本')
    parser.add_argument('--no-save-samples', dest='save_samples', action='store_false',
                       help='不儲存中等信心度樣本')
    parser.set_defaults(save_samples=config.save_uncertain_samples)
    parser.add_argument('--rtsp', action='store_true',
                       help='啟用 RTSP 推流')
    parser.add_argument('--rtsp-url', type=str, default=config.rtsp_url,
                       help='RTSP 推流地址')
    parser.add_argument('--rtsp-bitrate', type=int, default=2000,
                       help='RTSP 碼率 (kbps, 預設: 2000)')

    args = parser.parse_args()

    # 確定攝像頭模式
    dual_camera = args.dual or (not args.single and config.camera_dual_width > 1920)
    if args.single:
        logger.info(f"📷 強制使用單目攝像頭模式")
    elif args.dual:
        logger.info(f"📷 強制使用雙目攝像頭模式")
    else:
        logger.info(f"📷 自動檢測攝像頭模式: {'雙目' if dual_camera else '單目'}")

    # 設置信號處理器以優雅退出
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 初始化系統
    system = StreamingTrackingSystem(
        arduino_port=args.port,
        camera_id=args.camera,
        model_path=args.model,
        http_port=args.port_http,
        dual_camera=dual_camera,
        stream_mode=args.mode,
        save_samples=args.save_samples,
        enable_depth=dual_camera,  # 深度估計需要雙目攝像頭
        enable_rtsp=args.rtsp,
        rtsp_url=args.rtsp_url,
        rtsp_bitrate=args.rtsp_bitrate
    )

    # 運行系統
    logger.info("🚀 系統開始運行... 按 Ctrl+C 退出")
    try:
        system.run()
    except KeyboardInterrupt:
        logger.info("👋 使用者中斷，正在關閉系統...")
    except Exception as e:
        logger.error(f"系統運行錯誤: {e}")
        traceback.print_exc()
    finally:
        system.stop()
        logger.info("✅ 系統已關閉")


if __name__ == "__main__":
    main()