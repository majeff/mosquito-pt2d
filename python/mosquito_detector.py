"""
蚊子影像識別模組
使用深度學習AI模型（YOLO）偵測蚊子
"""

import cv2
import numpy as np
from typing import Optional, List, Tuple, Dict
import logging
import os
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 嘗試導入 ultralytics YOLO
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    logger.warning("ultralytics 未安裝，請執行: pip install ultralytics")
    YOLO_AVAILABLE = False


class MosquitoDetector:
    """基於AI深度學習的蚊子偵測器類"""

    def __init__(self,
                 model_path: Optional[str] = None,
                 confidence_threshold: float = 0.25,
                 iou_threshold: float = 0.45,
                 imgsz: int = 640,
                 fallback_to_pretrained: bool = True):
        """
        初始化AI蚊子偵測器 (Orange Pi 5 優化)

        Args:
            model_path: YOLO模型路徑（.pt檔案）。如果未提供，會使用預訓練模型
            confidence_threshold: 信心度閾值（0-1）
            iou_threshold: IoU閾值（用於NMS）
            imgsz: 輸入影像大小（320/416/640），較小的值速度較快
            fallback_to_pretrained: 如果找不到自定義模型，是否使用預訓練模型
        """
        if not YOLO_AVAILABLE:
            raise ImportError("需要安裝 ultralytics: pip install ultralytics")

        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.imgsz = imgsz

        # 載入模型
        if model_path and os.path.exists(model_path):
            logger.info(f"載入自定義YOLO模型: {model_path}")
            self.model = YOLO(model_path)
            self.model_type = 'custom'
        elif fallback_to_pretrained:
            logger.info("使用YOLOv8n預訓練模型（通用物體檢測）")
            logger.warning("⚠️ 建議使用蚊子專用模型以獲得更好效果")
            self.model = YOLO('yolov8n.pt')  # 輕量級快速模型
            self.model_type = 'pretrained'
        else:
            raise FileNotFoundError(f"找不到模型檔案: {model_path}")

        # Orange Pi 5 使用 CPU 推理（無 GPU）
        self.device = 'cpu'
        logger.info(f"使用 CPU 運算 (Orange Pi 5)，輸入解析度: {imgsz}x{imgsz}")

        logger.info("AI蚊子偵測器已初始化")


    def detect(self, frame: np.ndarray) -> Tuple[List[Dict], np.ndarray]:
        """
        使用YOLO AI模型偵測蚊子

        Args:
            frame: 輸入影像（BGR格式）

        Returns:
            (偵測結果列表，包含bbox和confidence，處理後的影像)
        """
        # 執行推理
        results = self.model.predict(
            frame,
            conf=self.confidence_threshold,
            iou=self.iou_threshold,
            imgsz=self.imgsz,
            device=self.device,
            verbose=False
        )

        detections = []

        if len(results) > 0:
            result = results[0]

            # 解析檢測結果
            for box in result.boxes:
                # 獲取邊界框座標
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                x, y, w, h = int(x1), int(y1), int(x2 - x1), int(y2 - y1)

                # 獲取信心度和類別
                confidence = float(box.conf[0])
                class_id = int(box.cls[0])
                class_name = self.model.names[class_id]

                detection = {
                    'bbox': (x, y, w, h),
                    'confidence': confidence,
                    'class_id': class_id,
                    'class_name': class_name,
                    'center': (x + w // 2, y + h // 2)
                }

                # 如果是自定義模型，直接使用；如果是預訓練模型，篩選小物體
                if self.model_type == 'custom' or self._is_mosquito_like(detection):
                    detections.append(detection)

        return detections, frame

    def _is_mosquito_like(self, detection: Dict) -> bool:
        """
        判斷檢測到的物體是否可能是蚊子（用於預訓練模型）

        Args:
            detection: 檢測結果字典

        Returns:
            是否可能是蚊子
        """
        # 對於預訓練模型，我們可以篩選某些類別或大小
        bbox = detection['bbox']
        area = bbox[2] * bbox[3]

        # 蚊子通常是小型物體
        if area > 2000:  # 太大的物體不太可能是蚊子
            return False

        # 可以篩選特定類別，例如鳥類、昆蟲等
        # COCO數據集中的類別：bird(14), cat(15), dog(16)等
        mosquito_like_classes = ['bird', 'kite']  # 可能與蚊子相似的類別

        if detection['class_name'] in mosquito_like_classes:
            return True

        return True  # 預設接受所有小物體


    def get_largest_detection(self, detections: List[Dict]) -> Optional[Dict]:
        """
        獲取信心度最高的偵測結果

        Args:
            detections: 偵測結果列表

        Returns:
            信心度最高的偵測結果，若無則返回 None
        """
        if not detections:
            return None

        return max(detections, key=lambda det: det['confidence'])

    def get_center(self, detection: Dict) -> Tuple[int, int]:
        """
        獲取檢測結果的中心點

        Args:
            detection: 檢測結果字典

        Returns:
            中心點座標 (cx, cy)
        """
        return detection['center']

    def draw_detections(self, frame: np.ndarray, detections: List[Dict],
                       color: Tuple[int, int, int] = (0, 255, 0),
                       thickness: int = 2) -> np.ndarray:
        """
        在影像上繪製AI偵測框

        Args:
            frame: 輸入影像
            detections: 偵測結果列表
            color: 邊界框顏色 (B, G, R)
            thickness: 線條粗細

        Returns:
            繪製後的影像
        """
        result = frame.copy()

        for detection in detections:
            x, y, w, h = detection['bbox']
            confidence = detection['confidence']
            class_name = detection['class_name']
            cx, cy = detection['center']

            # 根據信心度選擇顏色
            if confidence > 0.7:
                box_color = (0, 255, 0)  # 綠色：高信心度
            elif confidence > 0.5:
                box_color = (0, 255, 255)  # 黃色：中等信心度
            else:
                box_color = (0, 165, 255)  # 橙色：低信心度

            # 繪製邊界框
            cv2.rectangle(result, (x, y), (x + w, y + h), box_color, thickness)

            # 繪製中心點
            cv2.circle(result, (cx, cy), 3, (0, 0, 255), -1)

            # 標註類別和信心度
            label = f"{class_name}: {confidence:.2f}"
            (label_w, label_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(result, (x, y - label_h - 10), (x + label_w, y), box_color, -1)
            cv2.putText(result, label, (x, y - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

        return result

    def reset(self):
        """重置偵測器狀態（AI模型不需要重置）"""
        logger.info("AI偵測器無需重置")


def test_mosquito_detector():
    """測試AI蚊子偵測器"""
    print("=== 測試AI蚊子偵測器 ===")
    print("按 'q' 退出, 's' 儲存當前幀")
    print("\n提示：首次執行會自動下載YOLOv8n模型（約6MB）")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("無法開啟攝像頭")
        return

    try:
        # 初始化AI偵測器 (Orange Pi 5)
        # 可以指定自定義模型：detector = MosquitoDetector(model_path='models/mosquito_yolov8n.pt')
        detector = MosquitoDetector(
            confidence_threshold=0.3,  # 降低閾值以檢測更多物體
            imgsz=320  # Orange Pi 5 建議使用 320 以提升速度
        )

        frame_count = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1

            # 執行AI偵測
            detections, _ = detector.detect(frame)

            # 繪製偵測結果
            result = detector.draw_detections(frame, detections)

            # 顯示偵測數量和FPS
            cv2.putText(result, f"Detections: {len(detections)} | Frame: {frame_count}",
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(result, f"Device: {detector.device} | Model: {detector.model_type}",
                       (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            # 如果有偵測到，高亮最佳結果
            best = detector.get_largest_detection(detections)
            if best:
                x, y, w, h = best['bbox']
                cv2.rectangle(result, (x, y), (x + w, y + h), (0, 0, 255), 3)
                cx, cy = best['center']
                cv2.putText(result, f"Best: ({cx}, {cy})", (cx - 50, cy - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

                # 顯示詳細資訊
                info = f"Class: {best['class_name']} | Conf: {best['confidence']:.2f}"
                cv2.putText(result, info, (10, 90),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

            # 顯示影像
            cv2.imshow('AI Mosquito Detection', result)

            # 鍵盤控制
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                filename = f"detection_frame_{frame_count}.jpg"
                cv2.imwrite(filename, result)
                print(f"已儲存: {filename}")

    except Exception as e:
        print(f"錯誤: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("測試完成")


if __name__ == "__main__":
    test_mosquito_detector()
