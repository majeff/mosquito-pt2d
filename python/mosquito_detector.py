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
蚊子影像識別模組
使用深度學習AI模型（YOLO）偵測蚊子
支援硬體加速推理引擎：hobot_dnn (BPU) / rknnlite (NPU)
注意：ONNX/PyTorch 僅用於訓練和模型轉換，不用於實際偵測
"""

import cv2
import numpy as np
from typing import Optional, List, Tuple, Dict
import logging
import os
import time
import datetime
import hashlib
import traceback
from pathlib import Path
from config import (
    DEFAULT_IMGSZ,
    DEFAULT_CONFIDENCE_THRESHOLD,
    DEFAULT_IOU_THRESHOLD,
    DEFAULT_DETECTION_MODE,
    DEFAULT_TILE_OVERLAP,
    DEFAULT_DETECTION_MARGIN,
    DEFAULT_MAX_SAMPLES,
    DEFAULT_SAVE_INTERVAL,
    ENABLE_ILLUMINATION_MONITORING,
    ILLUMINATION_WARNING_THRESHOLD,
    ILLUMINATION_PAUSE_THRESHOLD,
    ILLUMINATION_RESUME_THRESHOLD,
    ILLUMINATION_CHECK_INTERVAL,
)

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
    from hobot_dnn import pyeasy_dnn as dnn
    HOBOT_DNN_AVAILABLE = True
except ImportError:
    HOBOT_DNN_AVAILABLE = False
    logger.debug("hobot_dnn 未安裝（僅 RDK X5 需要）")

# ONNX 和 PyTorch 僅用於訓練和模型轉換，不用於實際偵測
# 實際部署時請使用硬體加速格式：.bin (RDK X5) 或 .rknn (Orange Pi 5)


class MosquitoDetector:
    """基於AI深度學習的蚊子偵測器類（支援 RKNN/ONNX/PyTorch）"""

    def __init__(self,
                 model_path: Optional[str] = None,
                 confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
                 iou_threshold: float = DEFAULT_IOU_THRESHOLD,
                 imgsz: int = DEFAULT_IMGSZ,
                 detection_mode: str = DEFAULT_DETECTION_MODE,  # 'tiling' 或 'whole'
                 tile_overlap: float = DEFAULT_TILE_OVERLAP,
                 detection_margin: float = DEFAULT_DETECTION_MARGIN,
                 fallback_to_pretrained: bool = True,
                 save_uncertain_samples: bool = False,
                 uncertain_conf_range: Tuple[float, float] = (0.35, 0.65),
                 save_dir: str = "uncertain_samples",
                 max_samples: int = DEFAULT_MAX_SAMPLES,
                 save_interval: float = DEFAULT_SAVE_INTERVAL,
                 save_annotations: bool = True,
                 save_full_frame: bool = False):
        """
        初始化AI蚊子偵測器 (硬體加速專用)
        自動選擇硬體加速推理引擎：
        - RDK X5: .bin (hobot_dnn BPU)
        - Orange Pi 5: .rknn (rknnlite NPU)

        Args:
            model_path: 模型路徑（可不含副檔名），或 models/ 目錄下的基本名稱
                       例如: "mosquito_yolov8" 會自動搜尋
                       mosquito_yolov8.bin → mosquito_yolov8.rknn
            confidence_threshold: 信心度閾值（0-1），預設 0.4（推薦範圍 0.3-0.7）
            iou_threshold: IoU閾值（用於NMS），預設 0.45
            imgsz: 輸入影像大小，預設 640（推薦值）
                   - 320: 快速推理，適合低效能設備
                   - 640: 標準精度，推薦使用（Orange Pi 5 可流暢運行）
            detection_margin: 檢測邊界邊距（0.0-0.5），排除邊緣區域，預設 0.1
            fallback_to_pretrained: 如果找不到自定義模型，是否使用預訓練模型
            save_uncertain_samples: 是否儲存信心度中等的樣本圖片以便後續檢驗與再訓練
            uncertain_conf_range: 中等信心度範圍 (min, max)，預設 (0.35, 0.65)
            save_dir: 儲存中等信心度樣本的目錄
            max_samples: 最大存儲照片數量，預設 1000 張
            save_interval: 儲存時間間隔（秒），避免頻繁存同一位置的照片，預設 3.0 秒
            save_annotations: 是否自動生成 YOLO 格式標註文件 (.txt)，預設 True
            save_full_frame: 是否儲存完整畫面（True）或僅裁剪檢測區域（False），預設 False
        """
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.imgsz = imgsz
        self.model = None
        self.backend = None  # 'rknn', 'onnx', 'pytorch'

        # 偵測模式
        self.detection_mode = detection_mode.lower() if isinstance(detection_mode, str) else 'tiling'
        if self.detection_mode not in ('tiling', 'whole'):
            logger.warning(f"未知的偵測模式: {self.detection_mode}，改用 'tiling'")
            self.detection_mode = 'tiling'
        # 平鋪重疊比例
        try:
            self.tile_overlap = float(tile_overlap)
        except Exception:
            self.tile_overlap = DEFAULT_TILE_OVERLAP
        self.tile_overlap = max(0.0, min(0.5, self.tile_overlap))

        # 檢測邊界邊距
        try:
            self.detection_margin = float(detection_margin)
        except Exception:
            self.detection_margin = DEFAULT_DETECTION_MARGIN
        self.detection_margin = max(0.0, min(0.5, self.detection_margin))

        # 儲存功能配置
        self.save_uncertain_samples = save_uncertain_samples
        self.uncertain_conf_range = uncertain_conf_range
        self.save_dir = Path(save_dir)
        self.max_samples = max_samples
        self.save_interval = save_interval
        self.save_annotations = save_annotations
        self.save_full_frame = save_full_frame
        self.save_counter = 0
        self.last_save_time = 0.0  # 上次儲存時間戳
        self.last_saved_hash = None  # 上次儲存照片的雜湊值

        # 創建儲存目錄
        if self.save_uncertain_samples:
            self.save_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"中等信心度樣本儲存目錄: {self.save_dir}")
            logger.info(f"信心度範圍: {uncertain_conf_range[0]:.2f} - {uncertain_conf_range[1]:.2f}")
            logger.info(f"最大存儲數量: {max_samples} 張")
            logger.info(f"儲存時間間隔: {save_interval} 秒")
            logger.info(f"自動標註: {'啟用' if save_annotations else '停用'}")
            logger.info(f"儲存模式: {'完整畫面' if save_full_frame else '裁剪區域'}")

        # 光照度監控配置
        self.enable_illumination_monitoring = ENABLE_ILLUMINATION_MONITORING
        self.illumination_warning_threshold = ILLUMINATION_WARNING_THRESHOLD
        self.illumination_pause_threshold = ILLUMINATION_PAUSE_THRESHOLD
        self.illumination_resume_threshold = ILLUMINATION_RESUME_THRESHOLD
        self.illumination_check_interval = ILLUMINATION_CHECK_INTERVAL
        self.last_illumination_check = 0.0
        self.current_illumination = 0
        self.illumination_paused = False

        if self.enable_illumination_monitoring:
            logger.info(f"光照度監控已啟用")
            logger.info(f"  - 警告閾值: {self.illumination_warning_threshold}")
            logger.info(f"  - 暫停閾值: {self.illumination_pause_threshold}")
            logger.info(f"  - 恢復閾值: {self.illumination_resume_threshold}")

        # 自動選擇模型
        actual_model_path = self._auto_select_model(model_path, fallback_to_pretrained)

        if actual_model_path is None:
            raise FileNotFoundError("找不到任何可用的模型檔案")

        # 根據副檔名載入對應的推理引擎
        ext = Path(actual_model_path).suffix.lower()

        if ext == '.bin':
            if not HOBOT_DNN_AVAILABLE:
                raise RuntimeError(
                    f"找到 BIN 模型但 hobot_dnn 庫未安裝\n"
                    f"請在 RDK X5 上安裝: pip install hobot_dnn"
                )
            self._load_hobot_model(actual_model_path)
        elif ext == '.rknn':
            if not RKNN_AVAILABLE:
                raise RuntimeError(
                    f"找到 RKNN 模型但 rknnlite 庫未安裝\n"
                    f"請在 Orange Pi 5 上安裝:\n"
                    f"  sudo apt update\n"
                    f"  sudo apt install python3-rknnlite2"
                )
            self._load_rknn_model(actual_model_path)
        elif ext in ['.onnx', '.pt']:
            raise RuntimeError(f"偵測不支援 {ext} 格式（僅用於訓練）。請使用 deploy_model.py 轉換為 .bin (RDK X5) 或 .rknn (Orange Pi 5)")
        else:
            raise RuntimeError(f"不支援的模型格式: {ext}。請使用 .bin (RDK X5) 或 .rknn (Orange Pi 5)")

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

        # 獲取腳本目錄和專案根目錄
        script_dir = Path(__file__).resolve().parent
        project_root = script_dir.parent

        if model_path:
            # 用戶指定了基本名稱（無副檔名）
            base_path = Path(model_path)
            base_name = base_path.stem if base_path.suffix else str(base_path)

            # 如果指定了目錄，使用該目錄
            if base_path.parent.name:
                base_dir = base_path.parent
                search_paths.extend([
                    base_dir / f"{base_name}.bin",
                    base_dir / f"{base_name}.rknn"
                ])

        # 支援兩種目錄結構，按優先順序搜尋
        models_dirs = [
            script_dir / 'models',        # python/models/ (當前目錄下)
            project_root / 'models',      # ../models/ (專案根目錄)
        ]

        for models_dir in models_dirs:
            if models_dir.exists():
                for default_name in ['mosquito_yolov8', 'mosquito', 'yolov8n']:
                    search_paths.extend([
                        models_dir / f"{default_name}.bin",
                        models_dir / f"{default_name}.rknn"
                    ])

        # 嘗試找到第一個存在的模型
        for path in search_paths:
            if path.exists():
                logger.info(f"✓ 找到模型: {path}")
                return str(path)

        # 未找到硬體加速模型
        logger.error("未找到硬體加速模型 (.bin 或 .rknn)")
        logger.error(f"搜尋的目錄: {', '.join(str(d) for d in models_dirs if d.exists())}")
        logger.error(f"預期的檔名: mosquito_yolov8.{{bin,rknn}} 或 mosquito.{{bin,rknn}}")
        logger.error("請使用 deploy_model.py 將訓練好的模型轉換為對應格式")
        return None

    def _load_hobot_model(self, model_path: str):
        """載入 RDK X5 BIN 模型（BPU 加速）"""
        logger.info(f"載入 RDK X5 BIN 模型: {model_path}")

        # 載入模型
        self.hobot_models = dnn.load(model_path)

        # 獲取輸入輸出信息
        logger.info(f"BPU 模型已載入，輸入數量: {len(self.hobot_models[0].inputs)}")
        logger.info(f"BPU 模型輸出數量: {len(self.hobot_models[0].outputs)}")

        self.backend = 'hobot_dnn'
        logger.info("✓ RDK X5 BPU 加速已啟用")

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

    def _check_sample_count(self) -> bool:
        """
        檢查已儲存樣本數是否達到上限

        Returns:
            True: 可以繼續儲存
            False: 已達到最大數量限制，應暫停儲存
        """
        try:
            # 計算已儲存的樣本數（.jpg 檔案數）
            sample_count = len(list(self.save_dir.glob("*.jpg")))

            if sample_count >= self.max_samples:
                logger.warning(f"⚠ 已儲存樣本數已達上限 ({sample_count}/{self.max_samples})，暫停儲存")
                return False

            return True
        except Exception as e:
            logger.error(f"無法檢查樣本數: {e}")
            return False

    def _is_frame_duplicate(self, frame: np.ndarray) -> bool:
        """
        檢查當前畫面是否與上次儲存的畫面重複

        Args:
            frame: 當前影像

        Returns:
            True: 畫面重複
            False: 畫面不重複
        """

        # 檢查時間間隔，距離上次儲存是否超過 save_interval
        current_time = time.time()
        if current_time - self.last_save_time < self.save_interval:
            return True  # 時間間隔未達到，視為重複

        # 計算當前畫面的雜湊值
        frame_hash = hashlib.md5(frame.tobytes()).hexdigest()

        # 與上次儲存畫面比較
        if self.last_saved_hash == frame_hash:
            return True  # 內容重複

        self.last_saved_hash = frame_hash
        self.last_save_time = current_time
        return False

    def estimate_illumination(self, frame: np.ndarray) -> int:
        """
        估計影像光照度（亮度值 0-255）

        Args:
            frame: 輸入影像（BGR 格式）

        Returns:
            估計的亮度值（0-255 範圍）
        """
        # 轉換為灰度圖
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # 計算平均亮度值
        brightness = int(np.mean(gray))

        # 更新當前亮度值
        self.current_illumination = brightness

        return brightness

    def check_illumination_status(self, frame: np.ndarray) -> Dict[str, any]:
        """
        檢查光照度狀態，並根據閾值決定是否暫停 AI 辨識

        Args:
            frame: 輸入影像

        Returns:
            包含光照度資訊和狀態的字典
        """
        if not self.enable_illumination_monitoring:
            return {
                'illumination': 0,
                'status': 'disabled',
                'paused': False,
                'message': ''
            }

        current_time = time.time()

        # 檢查是否需要更新光照度（避免每幀都計算）
        if current_time - self.last_illumination_check < self.illumination_check_interval:
            return {
                'illumination': self.current_illumination,
                'status': 'ok' if not self.illumination_paused else 'paused',
                'paused': self.illumination_paused,
                'message': ''
            }

        # 估計光照度
        illumination = self.estimate_illumination(frame)
        self.last_illumination_check = current_time

        # 判斷光照度狀態
        status = 'ok'
        message = ''

        if illumination < self.illumination_pause_threshold:
            # 光線太暗，暫停 AI 辨識
            self.illumination_paused = True
            status = 'paused'
            message = f'光線太暗 ({illumination}/255)，已暫停 AI 辨識'
        elif illumination < self.illumination_resume_threshold and self.illumination_paused:
            # 仍未達到恢復閾值，保持暫停
            status = 'paused'
            message = f'光線仍不足 ({illumination}/255)，保持暫停'
        elif illumination >= self.illumination_resume_threshold and self.illumination_paused:
            # 光照度已恢復，重新啟用 AI 辨識
            self.illumination_paused = False
            status = 'resumed'
            message = f'光照度已恢復 ({illumination}/255)，重新啟用 AI 辨識'
        elif illumination < self.illumination_warning_threshold:
            # 光照度稍低，但未達暫停閾值
            status = 'warning'
            message = f'光線較暗 ({illumination}/255)，可能影響檢測準確度'
        else:
            status = 'ok'
            message = f'光照度正常 ({illumination}/255)'

        return {
            'illumination': illumination,
            'status': status,
            'paused': self.illumination_paused,
            'message': message
        }

    def _save_uncertain_sample(self, frame: np.ndarray, detection: Dict):
        """
        儲存信心度中等的樣本圖片，並可選生成 YOLO 格式標註文件

        Args:
            frame: 原始影像
            detection: 檢測結果（含 bbox, confidence 等資訊）
        """
        # 檢查樣本數是否達到上限
        if not self._check_sample_count():
            return

        # 檢查時間間隔和內容重複
        if self._is_frame_duplicate(frame):
            return

        try:
            confidence = detection['confidence']
            x, y, w, h = detection['bbox']
            class_id = detection.get('class_id', 0)

            # 生成基礎檔名：時間戳_信心度
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            base_filename = f"mosquito_{timestamp}_conf{confidence:.3f}"

            # 決定儲存的圖片內容
            if self.save_full_frame:
                # 儲存完整畫面
                image_to_save = frame.copy()
                # 在完整畫面上繪製邊界框
                cv2.rectangle(image_to_save, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(image_to_save, f"{confidence:.2f}", (x, y - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            else:
                # 僅裁剪檢測區域（帶安全邊界）
                margin = 10
                img_h, img_w = frame.shape[:2]
                y1 = max(0, y - margin)
                y2 = min(img_h, y + h + margin)
                x1 = max(0, x - margin)
                x2 = min(img_w, x + w + margin)
                image_to_save = frame[y1:y2, x1:x2].copy()

            # 儲存圖片
            image_path = self.save_dir / f"{base_filename}.jpg"
            cv2.imwrite(str(image_path), image_to_save)

            # 生成並儲存 YOLO 格式標註文件
            if self.save_annotations:
                annotation_path = self.save_dir / f"{base_filename}.txt"
                self._save_yolo_annotation(annotation_path, frame.shape, detection)

            self.save_counter += 1

            if self.save_counter % 10 == 0:
                logger.info(f"已儲存 {self.save_counter} 張中等信心度樣本{'（含標註）' if self.save_annotations else ''}")

        except Exception as e:
            logger.error(f"儲存樣本失敗: {e}")

    def _save_yolo_annotation(self, annotation_path: Path, frame_shape: Tuple[int, int, int], detection: Dict):
        """
        生成並儲存 YOLO 格式標註文件

        YOLO 格式：class_id x_center y_center width height（歸一化座標 0-1）

        Args:
            annotation_path: 標註文件路徑
            frame_shape: 原始影像尺寸 (height, width, channels)
            detection: 檢測結果
        """
        try:
            img_h, img_w = frame_shape[:2]
            x, y, w, h = detection['bbox']
            class_id = detection.get('class_id', 0)

            # 計算中心點和尺寸（歸一化到 0-1）
            x_center = (x + w / 2) / img_w
            y_center = (y + h / 2) / img_h
            width_norm = w / img_w
            height_norm = h / img_h

            # 確保座標在有效範圍內
            x_center = max(0.0, min(1.0, x_center))
            y_center = max(0.0, min(1.0, y_center))
            width_norm = max(0.0, min(1.0, width_norm))
            height_norm = max(0.0, min(1.0, height_norm))

            # 寫入 YOLO 格式標註（一行一個目標）
            with open(annotation_path, 'w') as f:
                f.write(f"{class_id} {x_center:.6f} {y_center:.6f} {width_norm:.6f} {height_norm:.6f}\n")

        except Exception as e:
            logger.error(f"生成標註文件失敗: {e}")


    def detect(self, frame: np.ndarray, is_dual_left: bool = False) -> Tuple[List[Dict], np.ndarray, Dict]:
        """
        使用 AI 模型偵測蚊子（自動選擇 RKNN/ONNX/PyTorch）

        Args:
            frame: 輸入影像（BGR格式）
            is_dual_left: 是否為雙目左眼畫面（只過濾上下邊緣）

        Returns:
            (偵測結果列表，包含bbox和confidence，處理後的影像，光照度資訊)
        """
        try:
            # 檢查光照度狀態
            illumination_info = self.check_illumination_status(frame)

            # 如果光照度過低，暫停 AI 辨識
            if illumination_info['paused']:
                return [], frame, illumination_info

            if self.detection_mode == 'tiling':
                detections, result_frame = self._detect_tiled(frame)
            else:
                if self.backend == 'hobot_dnn':
                    detections, result_frame = self._detect_hobot(frame)
                elif self.backend == 'rknn':
                    detections, result_frame = self._detect_rknn(frame)
                else:
                    raise RuntimeError(f"未知的推理後端: {self.backend}")

            # 過濾邊界區域的檢測結果
            if self.detection_margin > 0 and detections:
                detections = self._filter_margin_detections(detections, frame.shape[:2], is_dual_left)

            # 儲存信心度中等的樣本
            if self.save_uncertain_samples and detections:
                for detection in detections:
                    conf = detection['confidence']
                    if self.uncertain_conf_range[0] <= conf <= self.uncertain_conf_range[1]:
                        self._save_uncertain_sample(frame, detection)

            return detections, result_frame, illumination_info

        except KeyboardInterrupt:
            # 讓 KeyboardInterrupt 正常傳播，觸發優雅關閉
            raise
        except RuntimeError as e:
            logger.error(f"AI 推理失敗 (Runtime): {e}")
            illumination_info = self.check_illumination_status(frame)
            return [], frame, illumination_info
        except MemoryError as e:
            logger.error(f"記憶體不足無法執行推理: {e}")
            illumination_info = self.check_illumination_status(frame)
            return [], frame, illumination_info
        except Exception as e:
            logger.error(f"AI 偵測發生未預期錯誤: {e}")
            illumination_info = self.check_illumination_status(frame)
            return [], frame, illumination_info

    def _filter_margin_detections(self, detections: List[Dict], frame_shape: Tuple[int, int], is_dual_left: bool = False) -> List[Dict]:
        """
        過濾掉位於畫面邊緣區域的檢測結果

        Args:
            detections: 檢測結果列表
            frame_shape: 影像尺寸 (height, width)
            is_dual_left: 是否為雙目左眼（True 時只過濾上下邊緣）

        Returns:
            過濾後的檢測結果列表
        """
        if self.detection_margin <= 0:
            return detections

        h, w = frame_shape
        margin_y = int(h * self.detection_margin)

        filtered = []
        for det in detections:
            cx, cy = det['center']

            # 雙目左眼：只檢查上下邊界（左右邊界不是真正的邊緣）
            if is_dual_left:
                if margin_y <= cy < h - margin_y:
                    filtered.append(det)
            else:
                # 單目：檢查四邊
                margin_x = int(w * self.detection_margin)
                if (margin_x <= cx < w - margin_x) and (margin_y <= cy < h - margin_y):
                    filtered.append(det)

        return filtered

    def _run_backend_once(self, img: np.ndarray) -> List[Dict]:
        """
        使用目前後端在單張影像上推理（回傳偵測結果，座標相對於 img）。
        """
        if self.backend == 'hobot_dnn':
            dets, _ = self._detect_hobot(img)
            return dets
        elif self.backend == 'rknn':
            dets, _ = self._detect_rknn(img)
            return dets
        else:
            raise RuntimeError(f"未知的推理後端: {self.backend}")

    def _detect_tiled(self, frame: np.ndarray) -> Tuple[List[Dict], np.ndarray]:
        """
        平鋪(tiling)推理：
        - 以 imgsz 為方形視窗對原圖滑動，視窗間有一定重疊
        - 各視窗內獨立推理，轉換回全域座標
        - 以全域 NMS 合併重疊框，避免重複計數
        """
        h, w = frame.shape[:2]
        tile = int(self.imgsz)
        # 重疊比例轉為步長（像素）
        stride = max(1, int(tile * (1.0 - self.tile_overlap)))

        merged: List[Dict] = []

        # 產生滑動視窗的起點（確保覆蓋到邊界）
        xs = list(range(0, max(1, w - tile + 1), stride))
        ys = list(range(0, max(1, h - tile + 1), stride))
        if len(xs) == 0:
            xs = [0]
        if len(ys) == 0:
            ys = [0]
        if xs[-1] != max(0, w - tile):
            xs.append(max(0, w - tile))
        if ys[-1] != max(0, h - tile):
            ys.append(max(0, h - tile))

        for y0 in ys:
            for x0 in xs:
                x1 = min(w, x0 + tile)
                y1 = min(h, y0 + tile)
                patch = frame[y0:y1, x0:x1]

                # 在子影像上推理（座標相對於 patch）
                dets = self._run_backend_once(patch)

                # 轉為全域座標並暫存
                for d in dets:
                    bx, by, bw, bh = d['bbox']
                    cx, cy = d['center']
                    nd = d.copy()
                    nd['bbox'] = (bx + x0, by + y0, bw, bh)
                    nd['center'] = (cx + x0, cy + y0)
                    merged.append(nd)

        # 全域 NMS 合併
        merged = self._nms(merged, self.iou_threshold)
        return merged, frame

    def _nms(self, detections: List[Dict], iou_thresh: float) -> List[Dict]:
        """簡單的全域 NMS（按信心度排序，移除 IoU 過高的重疊框）"""
        if not detections:
            return []

        # 轉為 (x1,y1,x2,y2,conf,idx)
        boxes = []
        for i, d in enumerate(detections):
            x, y, w, h = d['bbox']
            boxes.append((x, y, x + w, y + h, d['confidence'], i))

        # 依信心度由高到低排序
        boxes.sort(key=lambda b: b[4], reverse=True)

        keep = []
        suppressed = set()
        for i in range(len(boxes)):
            if i in suppressed:
                continue
            keep.append(detections[boxes[i][5]])
            xi1, yi1, xi2, yi2, ci, _ = boxes[i]
            for j in range(i + 1, len(boxes)):
                if j in suppressed:
                    continue
                xj1, yj1, xj2, yj2, cj, _ = boxes[j]
                if self._iou((xi1, yi1, xi2, yi2), (xj1, yj1, xj2, yj2)) > iou_thresh:
                    suppressed.add(j)

        return keep

    @staticmethod
    def _iou(a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]) -> float:
        """計算兩個框的 IoU，框格式為 (x1,y1,x2,y2)"""
        ax1, ay1, ax2, ay2 = a
        bx1, by1, bx2, by2 = b
        inter_x1 = max(ax1, bx1)
        inter_y1 = max(ay1, by1)
        inter_x2 = min(ax2, bx2)
        inter_y2 = min(ay2, by2)
        inter_w = max(0, inter_x2 - inter_x1)
        inter_h = max(0, inter_y2 - inter_y1)
        inter = inter_w * inter_h
        area_a = max(0, ax2 - ax1) * max(0, ay2 - ay1)
        area_b = max(0, bx2 - bx1) * max(0, by2 - by1)
        union = area_a + area_b - inter
        if union <= 0:
            return 0.0
        return inter / union

    def _detect_hobot(self, frame: np.ndarray) -> Tuple[List[Dict], np.ndarray]:
        """使用 RDK X5 BPU (hobot_dnn) 推理"""
        # 預處理：調整大小並轉換為 NV12 格式（RDK X5 BPU 專用）
        img = cv2.resize(frame, (self.imgsz, self.imgsz))

        # 將 BGR 轉為 NV12 (BPU 原生格式)
        nv12_data = dnn.pyimg_to_nv12(img)

        # BPU 推理
        outputs = self.hobot_models[0].forward(nv12_data)

        # 取得輸出數據（假設第一個輸出是檢測結果）
        output_data = outputs[0].buffer

        # 後處理（YOLO 格式）
        detections = self._parse_yolo_output(output_data, frame.shape[:2])

        return detections, frame

    def _detect_rknn(self, frame: np.ndarray) -> Tuple[List[Dict], np.ndarray]:
        """使用 RKNN NPU 推理"""
        # 預處理
        img = cv2.resize(frame, (self.imgsz, self.imgsz))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # 添加 batch 維度：(H, W, C) -> (1, H, W, C)
        img = np.expand_dims(img, axis=0)

        # NPU 推理
        try:
            outputs = self.rknn.inference(inputs=[img])
        except KeyboardInterrupt:
            # 讓 KeyboardInterrupt 正常傳播，觸發優雅關閉
            raise
        except Exception as e:
            logger.error(f"RKNN 推理失敗: {e}")
            return [], frame

        if outputs is None or len(outputs) == 0:
            logger.warning("RKNN 推理返回空結果")
            return [], frame

        # 檢查輸出是否有效
        try:
            if len(outputs[0].shape) == 0 or outputs[0].size == 0:
                logger.warning("RKNN 推理輸出為空張量")
                return [], frame
        except KeyboardInterrupt:
            # 讓 KeyboardInterrupt 正常傳播
            raise
        except Exception as e:
            logger.warning(f"檢查 RKNN 輸出失敗: {e}")
            return [], frame

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

    def cleanup(self):
        """優雅關閉偵測器，釋放硬體加速資源"""
        logger.info("正在清理偵測器資源...")
        try:
            if self.backend == 'rknn' and hasattr(self, 'rknn'):
                logger.info("正在釋放 RKNN 模型...")
                if hasattr(self.rknn, 'release'):
                    self.rknn.release()
                logger.info("✓ RKNN 資源已釋放")
        except Exception as e:
            logger.error(f"RKNN 清理失敗: {e}")

        try:
            if self.backend == 'hobot_dnn' and hasattr(self, 'hobot_models'):
                logger.info("正在釋放 BPU 模型...")
                # hobot_dnn 的模型在垃圾回收時自動釋放
                logger.info("✓ BPU 資源已釋放")
        except Exception as e:
            logger.error(f"BPU 清理失敗: {e}")

        try:
            if self.backend == 'onnx' and hasattr(self, 'model'):
                logger.info("正在釋放 ONNX 模型...")
                if hasattr(self.model, 'close'):
                    self.model.close()
                logger.info("✓ ONNX 資源已釋放")
        except Exception as e:
            logger.error(f"ONNX 清理失敗: {e}")

        logger.info("✓ 偵測器已清理完成")


def test_mosquito_detector():
    """測試AI蚊子偵測器（硬體加速專用）"""
    logger.info("=== 測試AI蚊子偵測器 ===")
    logger.info("硬體加速推理：hobot_dnn (BPU) / rknnlite (NPU)")
    logger.info("按 'q' 退出, 's' 儲存當前幀")
    logger.info("\n注意：請確保已使用 deploy_model.py 轉換模型為 .bin 或 .rknn 格式")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        logger.error("無法開啟攝像頭")
        return

    try:
        # 初始化AI偵測器（硬體加速專用）
        # 指定基本名稱，會自動搜尋 models/mosquito.{bin,rknn}
        detector = MosquitoDetector(
            model_path='models/mosquito',  # 自動選擇硬體加速格式
            confidence_threshold=0.3,
            imgsz=DEFAULT_IMGSZ  # 從 config.py 讀取，可統一修改
        )

        frame_count = 0
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

            # 顯示偵測數量和FPS（偵測數/低信心偵測數）
            cv2.putText(result, f"Detections: {len(detections)}/{detector.save_counter} | FPS: {fps:.1f}",
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            mode_text = 'TILING' if detector.detection_mode == 'tiling' else 'WHOLE'
            cv2.putText(result, f"Backend: {detector.backend.upper()} | ImgSz: {detector.imgsz} | Mode: {mode_text}",
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
                logger.info(f"已儲存: {filename}")

    except Exception as e:
        logger.error(f"錯誤: {e}")
        traceback.print_exc()
    finally:
        cap.release()
        cv2.destroyAllWindows()
        logger.info("測試完成")


if __name__ == "__main__":
    test_mosquito_detector()
