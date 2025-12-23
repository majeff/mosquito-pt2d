"""
蚊子影像識別模組
使用運動檢測與形狀識別技術偵測蚊子
"""

import cv2
import numpy as np
from typing import Optional, List, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MosquitoDetector:
    """蚊子偵測器類"""

    def __init__(self,
                 min_area: int = 10,
                 max_area: int = 500,
                 motion_threshold: int = 25,
                 blur_kernel: int = 5):
        """
        初始化蚊子偵測器

        Args:
            min_area: 最小偵測區域面積（像素）
            max_area: 最大偵測區域面積（像素）
            motion_threshold: 運動檢測閾值
            blur_kernel: 高斯模糊核心大小
        """
        self.min_area = min_area
        self.max_area = max_area
        self.motion_threshold = motion_threshold
        self.blur_kernel = blur_kernel

        # 背景減法器
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500,
            varThreshold=16,
            detectShadows=False
        )

        # 前一幀（用於幀差法）
        self.prev_frame = None

        logger.info("蚊子偵測器已初始化")

    def detect_motion(self, frame: np.ndarray) -> Tuple[List[Tuple[int, int, int, int]], np.ndarray]:
        """
        使用背景減法檢測運動物體

        Args:
            frame: 輸入影像（BGR格式）

        Returns:
            (偵測到的邊界框列表 [(x, y, w, h)], 前景遮罩)
        """
        # 應用背景減法
        fg_mask = self.bg_subtractor.apply(frame)

        # 降噪處理
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)

        # 尋找輪廓
        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # 篩選合適大小的輪廓
        detections = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if self.min_area <= area <= self.max_area:
                x, y, w, h = cv2.boundingRect(contour)
                detections.append((x, y, w, h))

        return detections, fg_mask

    def detect_frame_diff(self, frame: np.ndarray) -> Tuple[List[Tuple[int, int, int, int]], np.ndarray]:
        """
        使用幀差法檢測運動物體

        Args:
            frame: 輸入影像（BGR格式）

        Returns:
            (偵測到的邊界框列表 [(x, y, w, h)], 差分影像)
        """
        # 轉換為灰度
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (self.blur_kernel, self.blur_kernel), 0)

        if self.prev_frame is None:
            self.prev_frame = gray
            return [], np.zeros_like(gray)

        # 計算幀差
        frame_diff = cv2.absdiff(self.prev_frame, gray)
        _, thresh = cv2.threshold(frame_diff, self.motion_threshold, 255, cv2.THRESH_BINARY)

        # 形態學處理
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
        thresh = cv2.dilate(thresh, kernel, iterations=2)

        # 尋找輪廓
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # 篩選合適大小的輪廓
        detections = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if self.min_area <= area <= self.max_area:
                x, y, w, h = cv2.boundingRect(contour)
                detections.append((x, y, w, h))

        # 更新前一幀
        self.prev_frame = gray

        return detections, thresh

    def detect(self, frame: np.ndarray, method: str = 'background') -> Tuple[List[Tuple[int, int, int, int]], np.ndarray]:
        """
        偵測蚊子

        Args:
            frame: 輸入影像（BGR格式）
            method: 偵測方法 ('background' 或 'frame_diff')

        Returns:
            (偵測到的邊界框列表 [(x, y, w, h)], 處理後的遮罩)
        """
        if method == 'background':
            return self.detect_motion(frame)
        elif method == 'frame_diff':
            return self.detect_frame_diff(frame)
        else:
            logger.error(f"未知的偵測方法: {method}")
            return [], np.zeros_like(frame)

    def get_largest_detection(self, detections: List[Tuple[int, int, int, int]]) -> Optional[Tuple[int, int, int, int]]:
        """
        獲取最大的偵測框（假設最大的是蚊子）

        Args:
            detections: 偵測框列表

        Returns:
            最大的偵測框，若無則返回 None
        """
        if not detections:
            return None

        return max(detections, key=lambda bbox: bbox[2] * bbox[3])

    def get_center(self, bbox: Tuple[int, int, int, int]) -> Tuple[int, int]:
        """
        計算邊界框中心點

        Args:
            bbox: 邊界框 (x, y, w, h)

        Returns:
            中心點座標 (cx, cy)
        """
        x, y, w, h = bbox
        return (x + w // 2, y + h // 2)

    def draw_detections(self, frame: np.ndarray, detections: List[Tuple[int, int, int, int]],
                       color: Tuple[int, int, int] = (0, 255, 0),
                       thickness: int = 2) -> np.ndarray:
        """
        在影像上繪製偵測框

        Args:
            frame: 輸入影像
            detections: 偵測框列表
            color: 邊界框顏色 (B, G, R)
            thickness: 線條粗細

        Returns:
            繪製後的影像
        """
        result = frame.copy()

        for (x, y, w, h) in detections:
            # 繪製邊界框
            cv2.rectangle(result, (x, y), (x + w, y + h), color, thickness)

            # 繪製中心點
            cx, cy = self.get_center((x, y, w, h))
            cv2.circle(result, (cx, cy), 3, (0, 0, 255), -1)

            # 標註面積
            area = w * h
            cv2.putText(result, f"{area}px", (x, y - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

        return result

    def reset(self):
        """重置偵測器狀態"""
        self.prev_frame = None
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500,
            varThreshold=16,
            detectShadows=False
        )
        logger.info("偵測器已重置")


def test_mosquito_detector():
    """測試蚊子偵測器"""
    print("=== 測試蚊子偵測器 ===")
    print("按 'q' 退出, 'r' 重置偵測器, 'm' 切換偵測方法")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("無法開啟攝像頭")
        return

    detector = MosquitoDetector(min_area=20, max_area=1000)
    method = 'background'

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # 執行偵測
        detections, mask = detector.detect(frame, method=method)

        # 繪製偵測結果
        result = detector.draw_detections(frame, detections)

        # 顯示偵測數量
        cv2.putText(result, f"Detections: {len(detections)} | Method: {method}",
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # 如果有偵測到，標註最大的
        largest = detector.get_largest_detection(detections)
        if largest:
            x, y, w, h = largest
            cv2.rectangle(result, (x, y), (x + w, y + h), (0, 0, 255), 3)
            cx, cy = detector.get_center(largest)
            cv2.putText(result, f"Target: ({cx}, {cy})", (cx - 50, cy - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

        # 顯示影像
        cv2.imshow('Mosquito Detection', result)
        cv2.imshow('Mask', mask)

        # 鍵盤控制
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('r'):
            detector.reset()
            print("偵測器已重置")
        elif key == ord('m'):
            method = 'frame_diff' if method == 'background' else 'background'
            print(f"切換至偵測方法: {method}")

    cap.release()
    cv2.destroyAllWindows()
    print("測試完成")


if __name__ == "__main__":
    test_mosquito_detector()
