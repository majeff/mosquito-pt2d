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
                   DEFAULT_MAX_SAMPLES, DEFAULT_SAVE_INTERVAL,
                   DEFAULT_SAVE_UNCERTAIN_SAMPLES, DEFAULT_UNCERTAIN_CONF_RANGE,
                   SAMPLE_COLLECTION_DIR,
                   CAMERA_DUAL_WIDTH, CAMERA_DUAL_HEIGHT, CAMERA_DUAL_FPS,
                   FRAME_DELAY)
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
                 save_samples: bool = DEFAULT_SAVE_UNCERTAIN_SAMPLES,
                 sample_conf_range: tuple = DEFAULT_UNCERTAIN_CONF_RANGE,
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

        # 攝像頭解析度配置（預設值，會在 main() 中被覆蓋）
        self.camera_width = CAMERA_DUAL_WIDTH if dual_camera else 1920
        self.camera_height = CAMERA_DUAL_HEIGHT if dual_camera else 1080
        self.camera_fps = CAMERA_DUAL_FPS if dual_camera else 60

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
        from collections import deque

        # 1. 初始化 AI 檢測器（只創建一次！）
        logger.info("[1/5] 初始化 AI 檢測器...")
        self.detector = MosquitoDetector(
            model_path=model_path,
            confidence_threshold=DEFAULT_CONFIDENCE_THRESHOLD,
            imgsz=DEFAULT_IMGSZ,
            save_uncertain_samples=save_samples,
            uncertain_conf_range=sample_conf_range,
            save_dir=SAMPLE_COLLECTION_DIR,
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
            # 深度估計器將在 run() 中根據實際解析度初始化
            self.depth_estimator = None
            logger.info(f"      ⏳ 深度估計器將在首幀時初始化（根據實際解析度）")
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
                            from config import MIN_MOSQUITO_SIZE_MM, MAX_MOSQUITO_SIZE_MM
                            obj_size = depth_info.get('object_size_mm', 0)
                            if MIN_MOSQUITO_SIZE_MM <= obj_size <= MAX_MOSQUITO_SIZE_MM:
                                valid_detections.append(detection)
                            else:
                                logger.debug(f"尺寸過濾: {obj_size:.1f}mm 不在 {MIN_MOSQUITO_SIZE_MM}-{MAX_MOSQUITO_SIZE_MM}mm 範圍")
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
        from config import (ENABLE_BBOX_SIZE_FILTER, MIN_BBOX_SIZE_PX, MAX_BBOX_SIZE_PX,
                           ENABLE_ASPECT_RATIO_FILTER, MIN_ASPECT_RATIO, MAX_ASPECT_RATIO,
                           ENABLE_TEMPORAL_FILTER, MIN_CONSECUTIVE_FRAMES,
                           ENABLE_MOTION_FILTER, MAX_MOVEMENT_PX_PER_FRAME,
                           MAX_STATIC_FRAMES, STATIC_THRESHOLD_PX)
        from collections import deque

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
                        'positions': deque(maxlen=10),
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
        from config import (MIN_MOSQUITO_SIZE_MM, MAX_MOSQUITO_SIZE_MM,
                           MIN_BBOX_SIZE_PX, MAX_BBOX_SIZE_PX,
                           MIN_ASPECT_RATIO, MAX_ASPECT_RATIO)

        for detection in detections:
            track_id = detection.get('track_id', 'N/A')
            confidence = detection.get('confidence', 0)
            bbox = detection.get('bbox')

            if not bbox:
                continue

            x1, y1, x2, y2 = bbox
            width = x2 - x1
            height = y2 - y1
            bbox_size = max(width, height)
            aspect_ratio = width / max(height, 1)

            # 物理尺寸與距離資訊
            distance_cm = detection.get('distance_cm', 0)
            obj_size_mm = detection.get('object_size_mm', 0)

            # 運動資訊
            speed_info = ""
            if track_id != 'N/A' and track_id in self.detection_history:
                history = self.detection_history[track_id]
                positions = history['positions']
                if len(positions) >= 2:
                    prev_pos = positions[-2]
                    curr_pos = positions[-1]
                    movement = np.sqrt((curr_pos[0] - prev_pos[0])**2 + (curr_pos[1] - prev_pos[1])**2)
                    speed_info = f"| 速度: {movement:.1f}px/幀"

                static_frames = history.get('static_frames', 0)
                if static_frames > 0:
                    speed_info += f" (靜止{static_frames}幀)"

            # 過濾器資訊
            filter_info = []
            filter_info.append(f"框: {bbox_size}px/{MIN_BBOX_SIZE_PX}-{MAX_BBOX_SIZE_PX}px")
            filter_info.append(f"寬高比: {aspect_ratio:.2f}/{MIN_ASPECT_RATIO}-{MAX_ASPECT_RATIO}")

            if distance_cm > 0 and obj_size_mm > 0:
                filter_info.append(f"距離: {distance_cm:.1f}cm")
                filter_info.append(f"尺寸: {obj_size_mm:.1f}mm/{MIN_MOSQUITO_SIZE_MM}-{MAX_MOSQUITO_SIZE_MM}mm")

            # 輸出詳細日誌
            logger.info(f"[檢測] ID:{track_id} | 信心: {confidence:.3f} | {' | '.join(filter_info)} {speed_info}")

    def _draw_system_info(self, frame: np.ndarray, detections: list, illumination_info: dict):
        """在畫面上繪製系統資訊"""
        y_pos = 30
        line_height = 35

        # 唯一目標數
        cv2.putText(frame, f"Unique Targets: {self.stats['unique_targets']}", (10, y_pos),
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

        # 系統資訊（右下角）
        line_height = 20
        info_y = frame.shape[0] - 80

        # 時間（右下角最下方）
        current_time = time.strftime("%H:%M:%S")
        time_font_size = 0.35
        time_thickness = 1
        time_size = cv2.getTextSize(current_time, cv2.FONT_HERSHEY_SIMPLEX, time_font_size, time_thickness)[0]
        time_x = frame.shape[1] - time_size[0] - 10
        time_y = frame.shape[0] - 10
        cv2.putText(frame, current_time, (time_x, time_y),
                   cv2.FONT_HERSHEY_SIMPLEX, time_font_size, (200, 200, 200), time_thickness)

        # 光照度（右下角向上）
        # Debug: 輸出光照度狀態
        if illumination_info['illumination'] < 50:  # 只在光線較暗時輸出
            logger.debug(f"Illumination: {illumination_info['illumination']}, Status: {illumination_info['status']}")

        illumination_color = (0, 255, 0)  # 綠色：正常
        if illumination_info['status'] == 'paused':
            illumination_color = (0, 0, 255)  # 紅色：暫停
        elif illumination_info['status'] == 'warning':
            illumination_color = (0, 165, 255)  # 橙色：警告
        elif illumination_info['status'] == 'resumed':
            illumination_color = (0, 255, 255)  # 黃色：已恢復

        illumination_text = f"Lux: {illumination_info['illumination']}"
        illumination_size = cv2.getTextSize(illumination_text, cv2.FONT_HERSHEY_SIMPLEX, 0.35, 1)[0]
        illumination_x = frame.shape[1] - illumination_size[0] - 10
        illumination_y = frame.shape[0] - 30
        cv2.putText(frame, illumination_text, (illumination_x, illumination_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.35, illumination_color, 1)

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

        # 設置攝像頭解析度（使用檢測到的最佳配置）
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.camera_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.camera_height)
        cap.set(cv2.CAP_PROP_FPS, self.camera_fps)

        if not cap.isOpened():
            logger.error("✗ 無法開啟攝像頭")
            return

        logger.info(f"✓ 攝像頭已開啟 (ID: {self.camera_id})")
        logger.info(f"✓ 解析度: {self.camera_width}×{self.camera_height}@{self.camera_fps}fps")

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

                # 定期輸出狀態（每 500 幀）
                if self.stats['total_frames'] % 500 == 0:
                    elapsed = time.time() - self.stats['start_time']
                    fps = self.stats['total_frames'] / elapsed if elapsed > 0 else 0

                    # 獲取光照度資訊
                    illum_info = self.stats.get('last_illumination_info', {})
                    lux = illum_info.get('illumination', 0)
                    lux_status = illum_info.get('status', 'unknown')
                    ai_paused = illum_info.get('paused', False)

                    # 獲取弱信心存檔數
                    saved_samples = getattr(self.detector, 'saved_sample_count', 0)

                    logger.info(f"[狀態] FPS: {fps:.1f} | "
                          f"唯一目標: {self.stats['unique_targets']} | "
                          f"存檔: {saved_samples} | "
                          f"追蹤: {'啟用' if self.stats['tracking_active'] else '停用'} | "
                          f"辨識: {'停用' if ai_paused else '啟用'} | "
                          f"Lux: {lux} ({lux_status})")

                # 簡單延時控制幀率
                time.sleep(FRAME_DELAY)  # 幀延時

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
        logger.info(f"唯一目標: {self.stats['unique_targets']}")
        if hasattr(self.detector, 'saved_sample_count'):
            logger.info(f"已儲存樣本: {self.detector.saved_sample_count}")
        elapsed = time.time() - self.stats['start_time']
        if elapsed > 0:
            logger.info(f"運行時間: {elapsed:.1f} 秒")
            logger.info(f"平均 FPS: {self.stats['total_frames'] / elapsed:.1f}")
        logger.info("=" * 60)
        logger.info("✅ 系統已關閉")


def detect_best_camera_config(camera_id: int = 0) -> dict:
    """
    自動檢測攝像頭並選擇最佳配置

    嘗試常見解析度（從高到低），選擇相機支援的最高解析度：
    - 3840×1080 @ 60fps (雙目 Full HD)
    - 1920×1080 @ 60fps (單目 Full HD)
    - 1280×720 @ 60fps (HD)
    - 640×480 @ 30fps (VGA, fallback)

    Args:
        camera_id: 攝像頭 ID

    Returns:
        dict: {
            'width': int,
            'height': int,
            'fps': int,
            'is_dual': bool,
            'resolution_name': str
        }
    """
    # 常見解析度配置（從高到低優先級）
    resolutions = [
        {'width': 3840, 'height': 1080, 'fps': 60, 'name': '雙目 Full HD (3840×1080@60fps)', 'is_dual': True},
        {'width': 1920, 'height': 1080, 'fps': 60, 'name': '單目 Full HD (1920×1080@60fps)', 'is_dual': False},
        {'width': 1280, 'height': 720, 'fps': 60, 'name': 'HD (1280×720@60fps)', 'is_dual': False},
        {'width': 1280, 'height': 720, 'fps': 30, 'name': 'HD (1280×720@30fps)', 'is_dual': False},
        {'width': 640, 'height': 480, 'fps': 30, 'name': 'VGA (640×480@30fps)', 'is_dual': False},
    ]

    logger.info(f"🔍 正在檢測攝像頭 {camera_id} 的最佳配置...")

    best_config = None

    for config in resolutions:
        cap = cv2.VideoCapture(camera_id)
        if not cap.isOpened():
            continue

        # 嘗試設置解析度
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, config['width'])
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config['height'])
        cap.set(cv2.CAP_PROP_FPS, config['fps'])

        # 讀取一幀驗證
        ret, frame = cap.read()
        cap.release()

        if ret and frame is not None:
            actual_width = frame.shape[1]
            actual_height = frame.shape[0]

            # 檢查是否成功設置為目標解析度（容許小幅偏差）
            width_match = abs(actual_width - config['width']) <= 10
            height_match = abs(actual_height - config['height']) <= 10

            if width_match and height_match:
                best_config = {
                    'width': actual_width,
                    'height': actual_height,
                    'fps': config['fps'],
                    'is_dual': config['is_dual'],
                    'resolution_name': config['name']
                }
                logger.info(f"✅ 找到支援的解析度: {config['name']}")
                logger.info(f"   實際解析度: {actual_width}×{actual_height}")
                break
            else:
                logger.debug(f"⚠️  {config['name']} 不支援 (實際: {actual_width}×{actual_height})")

    # 如果沒有找到任何支援的解析度，使用預設值
    if best_config is None:
        logger.warning(f"⚠️  無法檢測到支援的解析度，使用預設配置")
        best_config = {
            'width': 640,
            'height': 480,
            'fps': 30,
            'is_dual': False,
            'resolution_name': 'VGA (640×480@30fps) - 預設'
        }

    return best_config


def detect_dual_camera(camera_id: int = 0) -> bool:
    """
    自動檢測是否為雙目攝像頭（舊版相容函數）

    建議使用 detect_best_camera_config() 來獲取完整配置

    Args:
        camera_id: 攝像頭 ID

    Returns:
        True: 雙目攝像頭（寬度 >= 2560）
        False: 單目攝像頭
    """
    config = detect_best_camera_config(camera_id)
    return config['is_dual']


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
    camera_config = None
    if args.dual:
        dual_camera = True
        camera_width = CAMERA_DUAL_WIDTH
        camera_height = CAMERA_DUAL_HEIGHT
        camera_fps = CAMERA_DUAL_FPS
        logger.info("📷 攝像頭模式: 雙目（手動指定）")
        logger.info(f"   使用配置: {camera_width}×{camera_height}@{camera_fps}fps")
    elif args.single:
        dual_camera = False
        camera_width = 1920
        camera_height = 1080
        camera_fps = 60
        logger.info("📷 攝像頭模式: 單目（手動指定）")
        logger.info(f"   使用配置: {camera_width}×{camera_height}@{camera_fps}fps")
    else:
        logger.info("📷 自動檢測攝像頭最佳配置...")
        camera_config = detect_best_camera_config(args.camera)
        dual_camera = camera_config['is_dual']
        camera_width = camera_config['width']
        camera_height = camera_config['height']
        camera_fps = camera_config['fps']
        logger.info(f"   最佳配置: {camera_config['resolution_name']}")

    # 顯示配置
    logger.info("⚙️  系統配置:")
    logger.info(f"   - Arduino 串口: {args.port}")
    logger.info(f"   - 攝像頭 ID: {args.camera}")
    logger.info(f"   - 攝像頭模式: {'雙目' if dual_camera else '單目'}")
    logger.info(f"   - 攝像頭解析度: {camera_width}×{camera_height}@{camera_fps}fps")
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

    # 將檢測到的解析度配置應用到系統
    system.camera_width = camera_width
    system.camera_height = camera_height
    system.camera_fps = camera_fps

    system.run()


if __name__ == "__main__":
    main()
