"""
自動蚊子追蹤主程式
整合雙目攝像頭、蚊子偵測與 Arduino 雲台控制
"""

import cv2
import numpy as np
import time
import logging
from typing import Optional, Tuple

from stereo_camera import StereoCamera
from mosquito_detector import MosquitoDetector
from pt2d_controller import PT2DController
from laser_controller import LaserController

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MosquitoTracker:
    """蚊子自動追蹤系統"""

    def __init__(self,
                 arduino_port: str = 'COM3',
                 camera_left_id: int = 0,
                 camera_right_id: int = 1,
                 camera_width: int = 640,
                 camera_height: int = 480,
                 enable_laser: bool = True,
                 laser_gpio_pin: int = 5):
        """
        初始化追蹤系統

        Args:
            arduino_port: Arduino 串口號
            camera_left_id: 左攝像頭 ID
            camera_right_id: 右攝像頭 ID
            camera_width: 攝像頭寬度
            camera_height: 攝像頭高度
            enable_laser: 是否啟用雷射標記
            laser_gpio_pin: 雷射控制 GPIO 引腳
        """
        self.camera_width = camera_width
        self.camera_height = camera_height
        self.enable_laser = enable_laser

        # 初始化雙目攝像頭
        logger.info("初始化雙目攝像頭...")
        self.camera = StereoCamera(
            left_id=camera_left_id,
            right_id=camera_right_id,
            width=camera_width,
            height=camera_height
        )

        # 初始化蚊子偵測器（AI 檢測）
        logger.info("初始化 AI 蚊子偵測器...")
        self.detector = MosquitoDetector(
            model_path='models/mosquito_yolov8n.pt',  # 可選：使用自定義模型
            confidence_threshold=0.4,                  # 信心度閾值
            imgsz=320                                  # Orange Pi 5 建議使用 320
        )

        # 初始化 Arduino 控制器
        logger.info(f"連接 Arduino ({arduino_port})...")
        self.controller = PT2DController(arduino_port)

        # 初始化雷射控制器
        if self.enable_laser:
            logger.info("初始化雷射控制器...")
            self.laser = LaserController(gpio_pin=laser_gpio_pin)
            if not self.laser.is_initialized:
                logger.warning("雷射控制器初始化失敗，雷射標記功能將被停用")
                self.enable_laser = False
        else:
            self.laser = None
            logger.info("雷射標記功能已停用")

        # 追蹤狀態
        self.tracking_active = False
        self.last_detection_time = 0

        # 雷射標記狀態
        self.laser_marking = False
        self.last_laser_time = 0
        self.laser_cooldown = 0.5  # 雷射冷卻時間（秒）

        # PID 控制參數（簡化版）
        self.pan_gain = 0.15   # Pan 軸增益
        self.tilt_gain = 0.15  # Tilt 軸增益

        logger.info("追蹤系統初始化完成")

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

    def track_mosquito(self, left_detections, right_detections, left_frame, right_frame):
        """
        追蹤蚊子邏輯（雙目 AI 檢測，任一邊檢測到高信心度即可）

        Args:
            left_detections: 左攝像頭 AI 偵測結果列表
            right_detections: 右攝像頭 AI 偵測結果列表
            left_frame: 左攝像頭影像幀
            right_frame: 右攝像頭影像幀
        """
        current_time = time.time()

        # 合併左右攝像頭的 AI 檢測結果（任一邊檢測到高信心度即可）
        best_detection = None
        best_confidence = 0
        use_left_camera = True

        # 從左攝像頭尋找最佳檢測
        if left_detections:
            left_best = self.detector.get_largest_detection(left_detections)
            if left_best and left_best['confidence'] > best_confidence:
                best_detection = left_best
                best_confidence = left_best['confidence']
                use_left_camera = True

        # 從右攝像頭尋找最佳檢測
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

            # 開始追蹤
            if not self.tracking_active:
                logger.info(f"[{camera_side}攝像頭] AI 偵測到蚊子 (信心度: {confidence:.2f})，開始追蹤")
                self.tracking_active = True

            # 計算角度增量
            pan_delta, tilt_delta = self.calculate_target_angles(target_x, target_y)

            # 只有在偏離中心較大時才移動
            if abs(pan_delta) > 2 or abs(tilt_delta) > 2:
                self.controller.move_by(pan_delta, tilt_delta)
                logger.debug(f"[{camera_side}] AI 追蹤移動: Pan={pan_delta}, Tilt={tilt_delta}, 信心度={confidence:.2f}")

            # 在影像上標註目標（標註在使用的攝像頭畫面上）
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
            cv2.circle(frame, (target_x, target_y), 5, (0, 255, 255), -1)
            cv2.putText(frame, f"[{camera_side}] {class_name} ({target_x}, {target_y})",
                       (target_x - 100, target_y - 15),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            cv2.putText(frame, f"Conf: {confidence:.2f}",
                       (target_x - 50, target_y + h + 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            # 雷射標記：當目標接近中心且信心度足夠高時啟動雷射
            if self.enable_laser and self.laser.is_initialized:
                current_time = time.time()
                # 檢查目標是否在中心區域（±30 像素）且信心度 > 0.5
                center_threshold = 30
                confidence_threshold = 0.5
                error_x = abs(target_x - self.camera_width // 2)
                error_y = abs(target_y - self.camera_height // 2)

                if (error_x < center_threshold and error_y < center_threshold
                    and confidence > confidence_threshold):
                    # 目標在中心且信心度高，啟動雷射標記
                    if not self.laser_marking and (current_time - self.last_laser_time > self.laser_cooldown):
                        self.laser.on()
                        self.laser_marking = True
                        self.last_laser_time = current_time
                        logger.info(f"🎯 雷射標記啟動 [{camera_side}] 信心度: {confidence:.2f}")

                    # 標記中心區域
                    cv2.circle(frame, (self.camera_width // 2, self.camera_height // 2),
                             center_threshold, (0, 255, 0), 2)
                    cv2.putText(frame, f"LASER ON [{camera_side}]", (target_x - 60, target_y + h + 40),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                else:
                    # 目標偏離中心或信心度不足，關閉雷射
                    if self.laser_marking:
                        self.laser.off()
                        self.laser_marking = False
                        logger.info("雷射標記關閉（目標偏離或信心度不足）")

            # 返回使用的幀用於顯示
            return frame

        else:
            # 沒有偵測到目標（左右攝像頭都沒有高信心度檢測）
            if self.tracking_active:
                # 關閉雷射
                if self.enable_laser and self.laser_marking:
                    self.laser.off()
                    self.laser_marking = False

                # 回到初始位置繼續監控
                logger.info("AI 失去目標，雲台回到初始位置繼續監控...")
                self.controller.home()
                self.tracking_active = False

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
        logger.info("按 'l' 手動切換雷射" if self.enable_laser else "")
        logger.info("按 'SPACE' 手動標記（短脈衝）" if self.enable_laser else "")

        try:
            while True:
                # 讀取雙目攝像頭影像
                ret, left_frame, right_frame = self.camera.read()
                if not ret:
                    logger.warning("無法讀取雙目影像")
                    continue

                # 分別對左右攝像頭執行 AI 檢測
                left_detections, _ = self.detector.detect(left_frame)
                right_detections, _ = self.detector.detect(right_frame)

                # AI 追蹤蚊子（自動選擇信心度最高的攝像頭）
                display_frame = self.track_mosquito(left_detections, right_detections,
                                                    left_frame, right_frame)

                # 繪製 AI 偵測結果在顯示幀上
                if display_frame is left_frame and left_detections:
                    result = self.detector.draw_detections(display_frame.copy(), left_detections)
                elif display_frame is right_frame and right_detections:
                    result = self.detector.draw_detections(display_frame.copy(), right_detections)
                else:
                    result = display_frame.copy()

                # 顯示狀態資訊
                mode_text = "AI TRACKING" if self.tracking_active else "AI SCANNING"
                color = (0, 0, 255) if self.tracking_active else (0, 255, 0)
                cv2.putText(result, f"Mode: {mode_text}", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
                cv2.putText(result, f"左: {len(left_detections)} | 右: {len(right_detections)}", (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

                # 獲取當前雲台位置
                try:
                    pan, tilt = self.controller.get_position()
                except:
                    pan, tilt = 0, 0

                # 顯示雷射狀態
                if self.enable_laser:
                    laser_status = "LASER: ON" if self.laser_marking else "LASER: OFF"
                    laser_color = (0, 255, 0) if self.laser_marking else (128, 128, 128)
                    cv2.putText(result, laser_status, (10, 90),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, laser_color, 2)
                    cv2.putText(result, f"Pan: {pan} | Tilt: {tilt}", (10, 120),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                else:
                    cv2.putText(result, f"Pan: {pan} | Tilt: {tilt}", (10, 90),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

                # 顯示影像
                cv2.imshow('AI Mosquito Tracker (Dual Camera)', result)
                # 可選：顯示左右攝像頭原始畫面
                # cv2.imshow('Left Camera', left_frame)
                # cv2.imshow('Right Camera', right_frame)

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
                    self.controller.home()
                    self.tracking_active = False
                    if self.enable_laser and self.laser_marking:
                        self.laser.off()
                        self.laser_marking = False
                elif key == ord('l') and self.enable_laser:
                    # 手動切換雷射
                    if self.laser_marking:
                        self.laser.off()
                        self.laser_marking = False
                        logger.info("手動關閉雷射")
                    else:
                        self.laser.on()
                        self.laser_marking = True
                        logger.info("手動開啟雷射")
                elif key == ord(' ') and self.enable_laser:
                    # 空白鍵：短脈衝標記
                    logger.info("手動標記脈衝")
                    self.laser.pulse(duration=0.2)

        except KeyboardInterrupt:
            logger.info("收到中斷信號")

        finally:
            self.cleanup()

    def cleanup(self):
        """清理資源"""
        logger.info("清理資源...")

        # 關閉雷射
        if self.enable_laser and self.laser is not None:
            if self.laser_marking:
                self.laser.off()
            self.laser.cleanup()

        # 釋放攝像頭
        self.camera.release()

        # 關閉 Arduino 連接
        self.controller.close()

        # 關閉所有視窗
        cv2.destroyAllWindows()

        logger.info("系統已關閉")


def main():
    """主程式入口"""
    # 配置參數（根據實際情況修改）
    ARDUINO_PORT = '/dev/ttyUSB0'  # Orange Pi / Linux
    # ARDUINO_PORT = 'COM3'  # Windows（開發測試用）

    LEFT_CAMERA_ID = 0
    RIGHT_CAMERA_ID = 1

    # 建立並運行追蹤系統
    tracker = MosquitoTracker(
        arduino_port=ARDUINO_PORT,
        camera_left_id=LEFT_CAMERA_ID,
        camera_right_id=RIGHT_CAMERA_ID,
        camera_width=1920,  # 1080p
        camera_height=1080,
        enable_laser=True,  # 啟用雷射標記
        laser_gpio_pin=5    # Orange Pi 5 Pin 5 (GPIO 3)
    )

    tracker.run()


if __name__ == "__main__":
    main()
