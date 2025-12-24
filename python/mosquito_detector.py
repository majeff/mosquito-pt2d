"""
蚊子影像識別模組
使用深度學習AI模型（YOLO）偵測蚊子
支援多種推理引擎：RKNN (NPU) → ONNX (CPU優化) → PyTorch (CPU)
"""

import cv2
import numpy as np
from typing import Optional, List, Tuple, Dict
import logging
import os
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 嘗試導入各種推理引擎
try:
    from rknnlite.api import RKNNLite
    RKNN_AVAILABLE = True
except ImportError:
    RKNN_AVAILABLE = False
    logger.debug("rknnlite 未安裝（僅 Orange Pi 5 需要）")

try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False
    logger.debug("onnxruntime 未安裝")

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    logger.warning("ultralytics 未安裝，請執行: pip install ultralytics")
    YOLO_AVAILABLE = False


class MosquitoDetector:
    """基於AI深度學習的蚊子偵測器類（支援 RKNN/ONNX/PyTorch）"""

    def __init__(self,
                 model_path: Optional[str] = None,
                 confidence_threshold: float = 0.4,
                 iou_threshold: float = 0.45,
                 imgsz: int = 320,
                 fallback_to_pretrained: bool = True):
        """
        初始化AI蚊子偵測器 (Orange Pi 5 優化)
        自動選擇最佳推理引擎：RKNN (NPU) → ONNX (CPU優化) → PyTorch (CPU)

        Args:
            model_path: 模型路徑（可不含副檔名），或 models/ 目錄下的基本名稱
                       例如: "mosquito" 會自動搜尋 mosquito.rknn → mosquito.onnx → mosquito.pt
            confidence_threshold: 信心度閾值（0-1），預設 0.4（推薦範圍 0.3-0.7）
            iou_threshold: IoU閾值（用於NMS），預設 0.45
            imgsz: 輸入影像大小，預設 320（Orange Pi 5 推薦）
                   - 320: 快速推理，適合 Orange Pi 5 / 嵌入式設備
                   - 640: 高精度，適合 PC 開發環境
            fallback_to_pretrained: 如果找不到自定義模型，是否使用預訓練模型
        """
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.imgsz = imgsz
        self.model = None
        self.backend = None  # 'rknn', 'onnx', 'pytorch'

        # 自動選擇模型
        actual_model_path = self._auto_select_model(model_path, fallback_to_pretrained)

        if actual_model_path is None:
            raise FileNotFoundError("找不到任何可用的模型檔案")

        # 根據副檔名載入對應的推理引擎
        ext = Path(actual_model_path).suffix.lower()

        if ext == '.rknn' and RKNN_AVAILABLE:
            self._load_rknn_model(actual_model_path)
        elif ext == '.onnx' and ONNX_AVAILABLE:
            self._load_onnx_model(actual_model_path)
        elif ext == '.pt' and YOLO_AVAILABLE:
            self._load_pytorch_model(actual_model_path)
        else:
            raise RuntimeError(f"不支援的模型格式或缺少對應的推理引擎: {ext}")

        logger.info(f"AI蚊子偵測器已初始化，使用 {self.backend.upper()} 後端")

    def _auto_select_model(self, model_path: Optional[str], fallback: bool) -> Optional[str]:
        """
        自動選擇最佳模型（RKNN → ONNX → PyTorch）

        Args:
            model_path: 用戶指定的模型路徑
            fallback: 是否允許回退到預訓練模型

        Returns:
            選中的模型完整路徑，或 None
        """
        # 如果用戶指定了完整路徑且存在，直接使用
        if model_path and os.path.exists(model_path):
            logger.info(f"使用指定的模型: {model_path}")
            return model_path

        # 建立搜尋路徑列表
        search_paths = []

        if model_path:
            # 用戶指定了基本名稱（無副檔名）
            base_path = Path(model_path)
            base_name = base_path.stem if base_path.suffix else str(base_path)
            base_dir = base_path.parent if base_path.parent.name else Path('models')

            # 優先順序：RKNN → ONNX → PyTorch
            search_paths.extend([
                base_dir / f"{base_name}.rknn",
                base_dir / f"{base_name}.onnx",
                base_dir / f"{base_name}.pt"
            ])

        # 在 models/ 目錄搜尋預設名稱
        models_dir = Path('models')
        if models_dir.exists():
            for default_name in ['mosquito_yolov8', 'mosquito', 'yolov8n']:
                search_paths.extend([
                    models_dir / f"{default_name}.rknn",
                    models_dir / f"{default_name}.onnx",
                    models_dir / f"{default_name}.pt"
                ])

        # 嘗試找到第一個存在的模型
        for path in search_paths:
            if path.exists():
                logger.info(f"✓ 找到模型: {path}")
                return str(path)

        # 如果允許回退，使用預訓練模型
        if fallback and YOLO_AVAILABLE:
            logger.info("使用 YOLOv8n 預訓練模型（通用物體檢測）")
            logger.warning("⚠️ 建議下載蚊子專用模型以獲得更好效果")
            return 'yolov8n.pt'

        return None

    def _load_rknn_model(self, model_path: str):
        """載入 RKNN 模型（NPU 加速）"""
        logger.info(f"載入 RKNN 模型: {model_path}")
        self.rknn = RKNNLite()

        ret = self.rknn.load_rknn(model_path)
        if ret != 0:
            raise RuntimeError(f'載入 RKNN 模型失敗: {ret}')

        ret = self.rknn.init_runtime(core_mask=RKNNLite.NPU_CORE_0)
        if ret != 0:
            raise RuntimeError(f'初始化 RKNN 執行環境失敗: {ret}')

        self.backend = 'rknn'
        logger.info("✓ RKNN NPU 加速已啟用")

    def _load_onnx_model(self, model_path: str):
        """載入 ONNX 模型（CPU 優化）"""
        logger.info(f"載入 ONNX 模型: {model_path}")
        providers = ['CPUExecutionProvider']
        self.onnx_session = ort.InferenceSession(model_path, providers=providers)

        # 獲取輸入輸出名稱
        self.onnx_input_name = self.onnx_session.get_inputs()[0].name
        self.onnx_output_names = [o.name for o in self.onnx_session.get_outputs()]

        self.backend = 'onnx'
        logger.info("✓ ONNX CPU 優化推理已啟用")

    def _load_pytorch_model(self, model_path: str):
        """載入 PyTorch 模型（Ultralytics YOLO）"""
        logger.info(f"載入 PyTorch 模型: {model_path}")
        self.model = YOLO(model_path)
        self.backend = 'pytorch'
        self.device = 'cpu'
        logger.info(f"✓ PyTorch CPU 推理已啟用，輸入解析度: {self.imgsz}x{self.imgsz}")


    def detect(self, frame: np.ndarray) -> Tuple[List[Dict], np.ndarray]:
        """
        使用 AI 模型偵測蚊子（自動選擇 RKNN/ONNX/PyTorch）

        Args:
            frame: 輸入影像（BGR格式）

        Returns:
            (偵測結果列表，包含bbox和confidence，處理後的影像)
        """
        if self.backend == 'rknn':
            return self._detect_rknn(frame)
        elif self.backend == 'onnx':
            return self._detect_onnx(frame)
        elif self.backend == 'pytorch':
            return self._detect_pytorch(frame)
        else:
            raise RuntimeError(f"未知的推理後端: {self.backend}")

    def _detect_pytorch(self, frame: np.ndarray) -> Tuple[List[Dict], np.ndarray]:
        """使用 PyTorch (Ultralytics YOLO) 推理"""
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

                detections.append(detection)

        return detections, frame

    def _detect_onnx(self, frame: np.ndarray) -> Tuple[List[Dict], np.ndarray]:
        """使用 ONNX Runtime 推理"""
        # 預處理
        img = cv2.resize(frame, (self.imgsz, self.imgsz))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = img.transpose(2, 0, 1).astype(np.float32) / 255.0
        img = np.expand_dims(img, axis=0)

        # 推理
        outputs = self.onnx_session.run(self.onnx_output_names, {self.onnx_input_name: img})

        # 後處理（假設 YOLO 輸出格式）
        detections = self._parse_yolo_output(outputs[0], frame.shape[:2])

        return detections, frame

    def _detect_rknn(self, frame: np.ndarray) -> Tuple[List[Dict], np.ndarray]:
        """使用 RKNN NPU 推理"""
        # 預處理
        img = cv2.resize(frame, (self.imgsz, self.imgsz))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # NPU 推理
        outputs = self.rknn.inference(inputs=[img])

        # 後處理（假設 YOLO 輸出格式）
        detections = self._parse_yolo_output(outputs[0], frame.shape[:2])

        return detections, frame

    def _parse_yolo_output(self, output: np.ndarray, original_shape: Tuple[int, int]) -> List[Dict]:
        """
        解析 YOLO 輸出（ONNX/RKNN 通用）

        Args:
            output: 模型輸出張量
            original_shape: 原始影像尺寸 (height, width)

        Returns:
            偵測結果列表
        """
        detections = []
        h_orig, w_orig = original_shape

        # YOLO 輸出格式: [batch, num_boxes, 85] 或 [batch, 85, num_boxes]
        # 85 = x_center, y_center, width, height, objectness, 80 classes

        # 調整輸出形狀
        if len(output.shape) == 3:
            if output.shape[2] == 85:
                pass  # [1, num_boxes, 85]
            elif output.shape[1] == 85:
                output = output.transpose(0, 2, 1)  # [1, 85, num_boxes] → [1, num_boxes, 85]

        output = output[0]  # 移除 batch 維度

        for detection in output:
            objectness = detection[4]

            if objectness < self.confidence_threshold:
                continue

            # 解析座標
            x_center, y_center, width, height = detection[:4]

            # 轉換為原始影像座標
            x_center = x_center / self.imgsz * w_orig
            y_center = y_center / self.imgsz * h_orig
            width = width / self.imgsz * w_orig
            height = height / self.imgsz * h_orig

            x1 = int(x_center - width / 2)
            y1 = int(y_center - height / 2)
            w = int(width)
            h = int(height)

            # 類別概率
            class_scores = detection[5:]
            class_id = int(np.argmax(class_scores))
            confidence = float(objectness * class_scores[class_id])

            if confidence >= self.confidence_threshold:
                detections.append({
                    'bbox': (x1, y1, w, h),
                    'confidence': confidence,
                    'class_id': class_id,
                    'class_name': f'class_{class_id}',
                    'center': (int(x_center), int(y_center))
                })

        return detections


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
    """測試AI蚊子偵測器（支援 RKNN/ONNX/PyTorch）"""
    print("=== 測試AI蚊子偵測器 ===")
    print("自動選擇最佳推理引擎：RKNN (NPU) → ONNX (CPU優化) → PyTorch (CPU)")
    print("按 'q' 退出, 's' 儲存當前幀")
    print("\n提示：首次執行會自動下載YOLOv8n模型（約6MB）")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("無法開啟攝像頭")
        return

    try:
        # 初始化AI偵測器（自動選擇 RKNN → ONNX → PyTorch）
        # 指定基本名稱，會自動搜尋 models/mosquito.{rknn,onnx,pt}
        detector = MosquitoDetector(
            model_path='models/mosquito',  # 自動選擇最佳格式
            confidence_threshold=0.3,
            imgsz=320  # Orange Pi 5 建議使用 320
        )

        frame_count = 0
        import time
        fps_start = time.time()
        fps_counter = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            fps_counter += 1

            # 執行AI偵測
            detections, _ = detector.detect(frame)

            # 繪製偵測結果
            result = detector.draw_detections(frame, detections)

            # 計算 FPS
            if fps_counter >= 30:
                fps_elapsed = time.time() - fps_start
                fps = fps_counter / fps_elapsed
                fps_start = time.time()
                fps_counter = 0
            else:
                fps = 0

            # 顯示偵測數量和FPS
            cv2.putText(result, f"Detections: {len(detections)} | FPS: {fps:.1f}",
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(result, f"Backend: {detector.backend.upper()} | ImgSz: {detector.imgsz}",
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
