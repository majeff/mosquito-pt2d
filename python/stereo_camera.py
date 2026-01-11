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
單一雙目 USB 攝像頭模組
僅支援單一雙目攝像頭（左右影像並排）影像擷取與基礎處理
"""

import cv2
import numpy as np
from typing import Tuple, Optional, List
import logging
import os
import sys
import platform

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def list_available_cameras(max_test: int = 5) -> List[dict]:
    """
    列出可用的攝像頭設備

    Args:
        max_test: 最多測試的攝像頭數量

    Returns:
        可用的攝像頭信息列表，每個元素包含 id 和 backend
    """
    available = []

    # 根據操作系統選擇合適的後端
    system = platform.system()
    if system == "Windows":
        backends = [
            (cv2.CAP_DSHOW, "DirectShow"),
            (cv2.CAP_MSMF, "Media Foundation"),
        ]
    elif system == "Linux":
        backends = [
            (cv2.CAP_V4L2, "Video4Linux2"),
            (cv2.CAP_ANY, "Default"),
        ]
    else:  # macOS or others
        backends = [
            (cv2.CAP_ANY, "Default"),
        ]

    # 臨時抑制 OpenCV 錯誤輸出
    original_stderr = sys.stderr
    sys.stderr = open(os.devnull, 'w')

    try:
        for i in range(max_test):
            for backend, backend_name in backends:
                try:
                    cap = cv2.VideoCapture(i, backend)
                    if cap.isOpened():
                        # 嘗試讀取一幀來確認攝像頭真的可用
                        ret, frame = cap.read()
                        if ret:
                            # 檢查是否為雙目攝像頭（寬度是高度的2倍左右）
                            if frame is not None and frame.shape[1] > frame.shape[0]:
                                logger.info(f"攝像頭 {i} 可能是雙目攝像頭 (分辨率: {frame.shape[1]}x{frame.shape[0]})")
                            available.append({
                                'id': i,
                                'backend': backend,
                                'backend_name': backend_name,
                                'is_stereo': frame is not None and frame.shape[1] > frame.shape[0]
                            })
                            cap.release()
                            break  # 找到可用的後端就停止
                    cap.release()
                except:
                    pass
    finally:
        # 恢復錯誤輸出
        sys.stderr.close()
        sys.stderr = original_stderr

    return available


class SingleStereoCamera:
    """單一雙目 USB 攝像頭類"""

    def __init__(self, camera_id: int = 0, width: int = 3840, height: int = 1080, fps: int = 60):
        """
        初始化單一雙目攝像頭
        單一雙目攝像頭拍攝的圖像是左右並排的，此類別會將其分割成左右兩部分

        Args:
            camera_id: 雙目攝像頭設備 ID
            width: 影像總寬度（雙目模式時為左+右的總寬度，例如 3840=1920+1920）
            height: 影像高度（預設 1080）
            fps: 幀率（預設 60）
        """
        self.camera_id = camera_id
        self.width = width
        self.height = height
        self.fps = fps

        self.cap = None  # 單一雙目攝像頭設備
        self.is_opened = False

    def open(self) -> bool:
        """
        開啟雙目攝像頭

        Returns:
            是否成功開啟
        """
        try:
            # 根據操作系統選擇合適的後端
            system = platform.system()
            if system == "Windows":
                backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
                backend_names = {cv2.CAP_DSHOW: "DSHOW", cv2.CAP_MSMF: "MSMF", cv2.CAP_ANY: "ANY"}
            elif system == "Linux":
                backends = [cv2.CAP_V4L2, cv2.CAP_ANY]
                backend_names = {cv2.CAP_V4L2: "V4L2", cv2.CAP_ANY: "ANY"}
            else:
                backends = [cv2.CAP_ANY]
                backend_names = {cv2.CAP_ANY: "ANY"}

            self.cap = None

            for backend in backends:
                self.cap = cv2.VideoCapture(self.camera_id, backend)
                if self.cap.isOpened():
                    logger.info(f"使用 {backend_names.get(backend, 'UNKNOWN')} 後端開啟單一雙目攝像頭")
                    break
                else:
                    if self.cap:
                        self.cap.release()

            if not self.cap or not self.cap.isOpened():
                logger.error(f"無法開啟單一雙目攝像頭 (ID: {self.camera_id})")
                logger.info("嘗試運行 list_cameras() 查看可用攝像頭")
                return False

            # 設定攝像頭參數
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            
            self.is_opened = True
            logger.info(f"單一雙目攝像頭已開啟 (ID: {self.camera_id}, 分辨率: {self.width}x{self.height})")
            logger.info(f"解析度: {self.width}x{self.height}, FPS: {self.fps}")
            return True

        except (IOError, OSError) as e:
            logger.error(f"攝像頭設備錯誤: {e}")
            return False
        except Exception as e:
            logger.error(f"開啟攝像頭失敗: {e}")
            return False

    def read(self) -> Tuple[bool, Optional[np.ndarray], Optional[np.ndarray]]:
        """
        讀取影像並分割為左右兩部分

        Returns:
            (成功標誌, 左影像, 右影像)
        """
        if not self.is_opened:
            return False, None, None

        try:
            # 從單一攝像頭讀取整個幀
            ret, frame = self.cap.read()
            if ret and frame is not None:
                # 將圖像分成左右兩半
                mid_point = frame.shape[1] // 2
                left_frame = frame[:, :mid_point]
                right_frame = frame[:, mid_point:]
                return True, left_frame, right_frame
            else:
                logger.warning("讀取單一雙目攝像頭影像失敗")
                return False, None, None

        except (IOError, OSError) as e:
            logger.error(f"攝像頭 I/O 錯誤: {e}")
            return False, None, None
        except Exception as e:
            logger.error(f"讀取影像異常: {e}")
            return False, None, None

    def read_left(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        僅讀取左攝像頭影像（從整個幀中分割）

        Returns:
            (成功標誌, 左影像)
        """
        if not self.is_opened or self.cap is None:
            return False, None

        ret, frame = self.cap.read()
        if ret and frame is not None:
            mid_point = frame.shape[1] // 2
            left_frame = frame[:, :mid_point]
            return True, left_frame
        else:
            return False, None

    def read_right(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        僅讀取右攝像頭影像（從整個幀中分割）

        Returns:
            (成功標誌, 右影像)
        """
        if not self.is_opened or self.cap is None:
            return False, None

        ret, frame = self.cap.read()
        if ret and frame is not None:
            mid_point = frame.shape[1] // 2
            right_frame = frame[:, mid_point:]
            return True, right_frame
        else:
            return False, None

    def get_stereo_frame(self) -> Optional[np.ndarray]:
        """
        獲取原始的雙目影像（未分割）

        Returns:
            原始影像（左右並排），失敗返回 None
        """
        if not self.is_opened or self.cap is None:
            return None

        ret, frame = self.cap.read()
        if ret:
            return frame
        return None

    def release(self):
        """釋放攝像頭資源"""
        if self.cap is not None:
            self.cap.release()

        self.is_opened = False
        logger.info("單一雙目攝像頭已釋放")

    def __enter__(self):
        """上下文管理器入口"""
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.release()