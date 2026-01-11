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
自動蚊子追蹤主程式
整合雙目攝像頭、蚊子偵測與 Arduino 雲台控制
"""

import cv2
import numpy as np
import time
import logging
import threading
from typing import Optional, Tuple

from stereo_camera import StereoCamera
from config_loader import config
from mosquito_detector import MosquitoDetector
from pt2d_controller import PT2DController
from temperature_monitor import TemperatureMonitor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MosquitoTracker:
    """蚊子自動追蹤系統"""

    def __init__(self,
                 arduino_port: str = None,  # 从配置中获取默认值
                 camera_device_id: int = None,  # 从配置中获取默认值，使用单个双目摄像头设备ID
                 camera_width: int = None,  # 从配置中获取默认值
                 camera_height: int = None,  # 从配置中获取默认值
                 streaming_server: Optional[object] = None):
        """
        初始化追蹤系統

        Args:
            arduino_port: Arduino 串口號
            camera_device_id: 双目攝像頭設備 ID
            camera_width: 攝像頭寬度
            camera_height: 攝像頭高度
        """
        # 使用配置值，如果没有传入则使用默认值
        self.arduino_port = arduino_port if arduino_port is not None else config.arduino_port
        self.camera_device_id = camera_device_id if camera_device_id is not None else config.left_camera_id  # 使用配置中的left_camera_id作为设备ID
        self.camera_width = camera_width if camera_width is not None else config.camera_dual_width
        self.camera_height = camera_height if camera_height is not None else config.camera_dual_height

        # 初始化雙目攝像頭（使用單一雙目攝像頭模式）
        logger.info("初始化單一雙目攝像頭...")
        self.camera = StereoCamera(
            camera_id=self.camera_device_id,  # 作為設備ID
            width=self.camera_width,
            height=self.camera_height
        )

        # 初始化蚊子偵測器（AI 檢測）
        logger.info("初始化 AI 蚊子偵測器...")
        self.detector = MosquitoDetector(
            model_path=None,                           # 自動搜尋模型（.rknn → .onnx → .pt）
            confidence_threshold=config.confidence_threshold,  # 使用新配置
            imgsz=config.imgsz                        # 使用新配置
        )

        # 初始化 Arduino 控制器
        logger.info(f"連接 Arduino ({self.arduino_port})...")
        self.controller = PT2DController(self.arduino_port)

        # 追蹤狀態
        self.tracking_active = False
        self.last_detection_time = 0
        self.no_detection_timeout = config.no_detection_timeout  # 使用新配置

        # 目標鎖定機制（多目標時保持追蹤同一目標）
        self.locked_target_position = None  # 上次追蹤的目標位置 (x, y)
        self.target_lock_distance = config.target_lock_distance  # 使用新配置

        # 位置緩存（減少串口讀取頻率）
        self.cached_pan = 135
        self.cached_tilt = 90
        self.last_position_update = 0
        self.position_update_interval = config.position_update_interval  # 使用新配置

        # 蜂鳴器狀態
        self.beep_cooldown = config.beep_cooldown  # 使用新配置
        self.last_beep_time = 0

        # 雷射冷卻時間
        self.laser_cooldown = config.laser_cooldown  # 使用新配置
        self.last_laser_time = 0

        # PID 控制參數（簡化版）
        self.pan_gain = config.pan_gain   # Pan 增益（控制靈敏度）
        self.tilt_gain = config.tilt_gain  # Tilt 增益（控制靈敏度）

        # 串流伺服器（可選）
        self.streaming_server = streaming_server

        # 溫度監控器
        if config.enable_temperature_monitoring:  # 使用新配置
            logger.info("啟用溫度監控...")
            self.temperature_monitor = TemperatureMonitor()
            if not self.temperature_monitor.is_supported:
                logger.warning("溫度監控不支援，已禁用")
                self.temperature_monitor = None
        else:
            self.temperature_monitor = None

        logger.info("追蹤系統初始化完成")

    def _beep_async(self):
        """非同步蜂鳴器方法（在獨立線程中執行）"""
        try:
            self.controller.beep()
            logger.info("🔔 蜂鳴器已觸發")
        except Exception as e:
            logger.warning(f"蜂鳴器觸發失敗: {e}")

    def _home_async(self):
        """非同步回到初始位置方法（在獨立線程中執行）"""
        try:
            self.controller.home()
            self.cached_pan = 135
            self.cached_tilt = 90
            logger.info("雲台已回到初始位置")
        except Exception as e:
            logger.warning(f"雲台歸位失敗: {e}")

    def start(self) -> bool:
        """
        啟動追蹤系統

        Returns:
            是否成功啟動
        """
        # 開啟攝像頭
        if not self.camera.open():
            logger.error("無法開啟攝像頭")
            return False

        # 檢查 Arduino 連接
        if not self.controller.is_connected:
            logger.error("Arduino 未連接")
            return False

        # 設置雲台到初始位置（水平中央 135°，垂直 90°）
        logger.info("設置雲台到中央位置...")
        self.controller.home()
        time.sleep(1.0)  # 等待雲台移動完成
        logger.info("雲台已置中，等待偵測目標...")

        return True

    def calculate_target_angles(self, target_x: int, target_y: int) -> Tuple[int, int]:
        """
        根據影像座標計算目標角度

        Args:
            target_x: 目標在影像中的 X 座標
            target_y: 目標在影像中的 Y 座標

        Returns:
            (pan_delta, tilt_delta) 角度增量
        """
        # 計算目標與影像中心的偏移
        center_x = self.camera_width // 2
        center_y = self.camera_height // 2

        error_x = target_x - center_x
        error_y = target_y - center_y

        # 簡單比例控制計算角度增量
        pan_delta = int(error_x * self.pan_gain)
        tilt_delta = int(-error_y * self.tilt_gain)  # Y 軸反向

        return pan_delta, tilt_delta

    def _find_closest_detection(self, detections, target_position):
        """
        從檢測列表中找到與目標位置最接近的檢測

        Args:
            detections: 檢測結果列表
            target_position: 目標位置 (x, y)

        Returns:
            最接近的檢測結果，或 None
        """
        if not detections or target_position is None:
            return None

        closest_detection = None
        min_distance = float('inf')

        for detection in detections:
            center_x, center_y = detection['center']
            # 計算歐氏距離
            distance = np.sqrt((center_x - target_position[0])**2 +
                             (center_y - target_position[1])**2)

            if distance < min_distance:
                min_distance = distance
                closest_detection = detection

        # 只有在距離小於閾值時才返回（避免鎖定錯誤目標）
        if min_distance < self.target_lock_distance:
            return closest_detection
        return None

    def track_mosquito(self, left_detections, right_detections, left_frame, right_frame):
        """
        追蹤蚊子邏輯（支援多目標，鎖定追蹤單一目標直到失去）

        Args:
            left_detections: 左攝像頭 AI 偵測結果列表
            right_detections: 右攝像頭 AI 偵測結果列表
            left_frame: 左攝像頭影像幀
            right_frame: 右攝像頭影像幀
        """
        current_time = time.time()

        # 選擇目標策略：
        # 1. 如果正在追蹤，優先追蹤最接近上次位置的目標（目標鎖定）
        # 2. 如果沒有追蹤，選擇信心度最高的目標
        best_detection = None
        use_left_camera = True

        if self.tracking_active and self.locked_target_position is not None:
            # 策略 1: 目標鎖定模式 - 優先追蹤最接近的目標
            left_closest = self._find_closest_detection(left_detections, self.locked_target_position)
            right_closest = self._find_closest_detection(right_detections, self.locked_target_position)

            # 選擇距離最近且信心度足夠的目標
            if left_closest and right_closest:
                # 兩邊都有接近的目標，選信心度高的
                if left_closest['confidence'] >= right_closest['confidence']:
                    best_detection = left_closest
                    use_left_camera = True
                else:
                    best_detection = right_closest
                    use_left_camera = False
            elif left_closest:
                best_detection = left_closest
                use_left_camera = True
            elif right_closest:
                best_detection = right_closest
                use_left_camera = False
            else:
                # 沒有找到接近的目標，解除鎖定，重新選擇
                logger.debug("未找到鎖定目標附近的檢測，解除目標鎖定")
                self.locked_target_position = None

        if best_detection is None:
            # 策略 2: 新目標選擇模式 - 選擇信心度最高的目標
            best_confidence = 0

            if left_detections:
                left_best = self.detector.get_largest_detection(left_detections)
                if left_best and left_best['confidence'] > best_confidence:
                    best_detection = left_best
                    best_confidence = left_best['confidence']
                    use_left_camera = True

            if right_detections:
                right_best = self.detector.get_largest_detection(right_detections)
                if right_best and right_best['confidence'] > best_confidence:
                    best_detection = right_best
                    best_confidence = right_best['confidence']
                    use_left_camera = False

        # 選擇使用的幀
        frame = left_frame if use_left_camera else right_frame
        camera_side = "左" if use_left_camera else "右"

        if best_detection:
            # 有偵測到目標
            self.last_detection_time = current_time

            # 解析檢測結果
            x, y, w, h = best_detection['bbox']
            target_x, target_y = best_detection['center']
            confidence = best_detection['confidence']
            class_name = best_detection.get('class_name', 'unknown')

            # 開始追蹤或保持追蹤
            if not self.tracking_active:
                logger.info(f"[{camera_side}攝像頭] AI 偵測到蚊子 (信心度: {confidence:.2f})，鎖定目標開始追蹤")
                self.tracking_active = True
                # 非同步觸發蜂鳴器警報（避免阻塞雲台控制）
                if current_time - self.last_beep_time > self.beep_cooldown:
                    threading.Thread(target=self._beep_async, daemon=True).start()
                    self.last_beep_time = current_time

            # 更新鎖定目標位置（用於下一幀的目標鎖定）
            self.locked_target_position = (target_x, target_y)

            # 計算角度增量
            pan_delta, tilt_delta = self.calculate_target_angles(target_x, target_y)

            # 只有在偏離中心較大時才移動
            if abs(pan_delta) > 2 or abs(tilt_delta) > 2:
                try:
                    self.controller.move_by(pan_delta, tilt_delta)
                    logger.debug(f"[{camera_side}] AI 追蹤移動: Pan={pan_delta}, Tilt={tilt_delta}, 信心度={confidence:.2f}")
                except Exception as e:
                    logger.error(f"雲台移動失敗: {e}")
                    # 串口錯誤不中斷追蹤，繼續處理下一幀

            # 在影像上標註目標（標註在使用的攝像頭畫面上）
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
            cv2.circle(frame, (target_x, target_y), 5, (0, 255, 255), -1)
            cv2.putText(frame, f"[{camera_side}] {class_name} ({target_x}, {target_y})",
                       (target_x - 100, target_y - 15),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            cv2.putText(frame, f"Confidence: {confidence:.2f}",
                       (target_x - 50, target_y + h + 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            # 返回使用的幀用於顯示
            return frame

        else:
            # 沒有偵測到目標（左右攝像頭都沒有高信心度檢測）
            if self.tracking_active:
                # 檢查是否超時（連續一段時間未檢測到目標）
                time_since_last_detection = current_time - self.last_detection_time

                if time_since_last_detection > self.no_detection_timeout:
                    # 超時，判定為失去目標
                    logger.info(f"AI 持續 {time_since_last_detection:.1f}s 未檢測到目標，失去追蹤...")

                    # 非同步回到初始位置繼續監控（避免阻塞主循環）
                    logger.info("雲台回到初始位置繼續監控...")
                    threading.Thread(target=self._home_async, daemon=True).start()
                    self.tracking_active = False
                    self.locked_target_position = None  # 清除目標鎖定
                else:
                    # 未超時，保持追蹤狀態，等待目標重新出現
                    logger.debug(f"暫時失去目標 ({time_since_last_detection:.1f}s)，保持追蹤狀態...")
                    # 在畫面上顯示等待狀態
                    cv2.putText(left_frame, f"Waiting for target... ({time_since_last_detection:.1f}s)",
                               (10, self.camera_height - 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

            # 返回左攝像頭畫面作為預設顯示
            return left_frame

    def run(self):
        """運行主循環"""
        if not self.start():
            logger.error("追蹤系統啟動失敗")
            return

        logger.info("=== 蚊子追蹤系統啟動 ===")
        logger.info("按 'q' 退出")
        logger.info("按 'r' 重置偵測器")
        logger.info("按 'h' 回到初始位置")

        try:
            while True:
                try:
                    # 讀取雙目攝像頭影像
                    ret, left_frame, right_frame = self.camera.read()
                    if not ret:
                        logger.warning("無法讀取雙目影像")
                        continue

                    # 檢查溫度（每幀都檢查，但內部有間隔控制）
                    temp_paused = False
                    temp_info = None
                    if self.temperature_monitor is not None:
                        temp_info = self.temperature_monitor.check_temperature()
                        temp_paused = temp_info.get('is_paused', False)

                        # 如果有狀態變化，顯示訊息
                        status = temp_info.get('status', '')
                        message = temp_info.get('message', '')
                        if message and status in ['paused', 'resumed', 'warning']:
                            logger.info(message)

                    # 分別對左右攝像頭執行 AI 檢測（如果溫度過高則跳過）
                    if temp_paused:
                        # 溫度過高，暫停 AI 偵測
                        left_detections, right_detections = [], []
                        display_frame = left_frame
                        result = display_frame.copy()

                        # 關閉雷射
                        try:
                            self.controller.laser_off()
                        except Exception:
                            pass
                    else:
                        # 溫度正常，執行 AI 偵測
                        try:
                            left_detections, _ = self.detector.detect(left_frame)
                            right_detections, _ = self.detector.detect(right_frame)
                        except Exception as e:
                            logger.error(f"AI 檢測失敗: {e}")
                            left_detections, right_detections = [], []
                            display_frame = left_frame
                            result = display_frame.copy()
                            # 繼續運行，不中斷追蹤
                        else:
                            # AI 追蹤蚊子（自動選擇信心度最高的攝像頭）
                            try:
                                display_frame = self.track_mosquito(left_detections, right_detections,
                                                                    left_frame, right_frame)
                            except Exception as e:
                                logger.error(f"追蹤邏輯失敗: {e}")
                                display_frame = left_frame

                            # 繪製 AI 偵測結果在顯示幀上
                            try:
                                if display_frame is left_frame and left_detections:
                                    result = self.detector.draw_detections(display_frame.copy(), left_detections)
                                elif display_frame is right_frame and right_detections:
                                    result = self.detector.draw_detections(display_frame.copy(), right_detections)
                                else:
                                    result = display_frame.copy()
                            except Exception as e:
                                logger.error(f"繪製檢測結果失敗: {e}")
                                result = display_frame.copy()

                    # 顯示狀態資訊
                    mode_text = "TRACKING" if self.tracking_active else "SCANNING"
                    if temp_paused:
                        mode_text = "PAUSED (Temp)"
                    color = (0, 0, 255) if self.tracking_active else (0, 255, 0)
                    if temp_paused:
                        color = (0, 165, 255)  # 橘色
                    cv2.putText(result, f"Mode: {mode_text}", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
                    cv2.putText(result, f"L: {len(left_detections)} | R: {len(right_detections)}", (10, 60),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

                    # 獲取當前雲台位置（使用緩存減少串口讀取）
                    current_time = time.time()
                    if current_time - self.last_position_update > self.position_update_interval:
                        try:
                            pan, tilt = self.controller.get_position()
                            if pan is not None and tilt is not None:
                                self.cached_pan = pan
                                self.cached_tilt = tilt
                            self.last_position_update = current_time
                        except Exception as e:
                            logger.debug(f"讀取位置失敗，使用緩存值: {e}")
                    pan, tilt = self.cached_pan, self.cached_tilt

                    # 顯示位置資訊
                    cv2.putText(result, f"Pan: {pan} | Tilt: {tilt}", (10, 90),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

                    # 顯示溫度資訊
                    if self.temperature_monitor is not None and temp_info is not None:
                        temp_text = self.temperature_monitor.get_status_text(temp_info)
                        temp_color = (0, 255, 0)  # 綠色
                        if temp_paused:
                            temp_color = (0, 165, 255)  # 橘色
                        elif temp_info.get('status') == 'warning':
                            temp_color = (0, 255, 255)  # 黃色
                        cv2.putText(result, temp_text, (10, 120),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, temp_color, 2)

                    # 顯示偵測模式（分塊/整體）
                    try:
                        mode_text = 'Tiling' if getattr(self.detector, 'detection_mode', 'tiling') == 'tiling' else 'Whole'
                        cv2.putText(result, f"Detection: {mode_text}", (10, 150),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 255, 200), 2)
                    except Exception:
                        pass

                    # 串流輸出（若有提供伺服器）
                    try:
                        if self.streaming_server is not None:
                            self.streaming_server.update_frame(result)
                    except Exception as e:
                        logger.debug(f"更新串流影像失敗: {e}")

                    cv2.imshow('AI 蚊子追蹤系統 (雙目攝像頭)', result)
                    # 可選：顯示左右攝像頭原始畫面
                    # cv2.imshow('左攝像頭', left_frame)
                    # cv2.imshow('右攝像頭', right_frame)

                except Exception as loop_error:
                    logger.error(f"主循環發生異常: {loop_error}")
                    logger.error("嘗試繼續運行...")
                    time.sleep(0.1)
                    continue

                    # 鍵盤控制
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        logger.info("退出追蹤系統")
                        break
                    elif key == ord('r'):
                        logger.info("重置偵測器")
                        self.detector.reset()
                    elif key == ord('h'):
                        logger.info("回到初始位置")
                        threading.Thread(target=self._home_async, daemon=True).start()
                        self.tracking_active = False
                        self.locked_target_position = None  # 清除目標鎖定

        except KeyboardInterrupt:
            logger.info("收到中斷信號")

        finally:
            self.cleanup()

    def cleanup(self):
        """清理資源"""
        logger.info("清理資源...")

        # 釋放攝像頭
        self.camera.release()

        # 關閉 Arduino 連接
        self.controller.close()

        # 關閉所有視窗
        cv2.destroyAllWindows()

        logger.info("系統已關閉")


def main():
    """主程式入口"""
    # 建立並運行追蹤系統
    tracker = MosquitoTracker(
        arduino_port=config.arduino_port,  # 使用配置
        camera_device_id=config.left_camera_id,  # 使用配置中的left_camera_id作为设备ID
        camera_width=config.camera_dual_width,  # 使用配置
        camera_height=config.camera_dual_height  # 使用配置
    )

    tracker.run()


if __name__ == "__main__":
    main()
