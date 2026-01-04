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
雙目 USB 攝像頭模組
支援雙攝像頭影像擷取與基礎處理
"""

import cv2
import numpy as np
from typing import Tuple, Optional, List
import logging
import os
import sys
import time
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
                        ret, _ = cap.read()
                        if ret:
                            available.append({
                                'id': i,
                                'backend': backend,
                                'backend_name': backend_name
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


class StereoCamera:
    """雙目/單目 USB 攝像頭類"""

    def __init__(self, left_id: int = 0, right_id: Optional[int] = None,
                 width: int = 640, height: int = 480, fps: int = 30):
        """
        初始化攝像頭（支援單目/雙目模式）

        Args:
            left_id: 左攝像頭設備 ID（單目模式時為主攝像頭 ID）
            right_id: 右攝像頭設備 ID（設為 None 時啟用單目模式）
            width: 影像寬度
            height: 影像高度
            fps: 幀率
        """
        self.left_id = left_id
        self.right_id = right_id
        self.width = width
        self.height = height
        self.fps = fps
        self.is_stereo = right_id is not None  # 判斷是否為雙目模式

        self.left_cap = None
        self.right_cap = None
        self.is_opened = False

    def open(self) -> bool:
        """
        開啟攝像頭（單目/雙目）

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

            self.left_cap = None

            for backend in backends:
                self.left_cap = cv2.VideoCapture(self.left_id, backend)
                if self.left_cap.isOpened():
                    logger.info(f"使用 {backend_names.get(backend, 'UNKNOWN')} 後端開啟攝像頭")
                    break
                else:
                    self.left_cap.release()

            if not self.left_cap or not self.left_cap.isOpened():
                logger.error(f"無法開啟{'左' if self.is_stereo else ''}攝像頭 (ID: {self.left_id})")
                logger.info("嘗試運行 list_cameras() 查看可用攝像頭")
                return False

            # 設定左攝像頭參數
            self.left_cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.left_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.left_cap.set(cv2.CAP_PROP_FPS, self.fps)

            # 如果是雙目模式，開啟右攝像頭
            if self.is_stereo:
                self.right_cap = None
                for backend in backends:
                    self.right_cap = cv2.VideoCapture(self.right_id, backend)
                    if self.right_cap.isOpened():
                        break
                    else:
                        self.right_cap.release()

                if not self.right_cap or not self.right_cap.isOpened():
                    logger.error(f"無法開啟右攝像頭 (ID: {self.right_id})")
                    self.left_cap.release()
                    return False

                # 設定右攝像頭參數
                self.right_cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self.right_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                self.right_cap.set(cv2.CAP_PROP_FPS, self.fps)

            self.is_opened = True
            if self.is_stereo:
                logger.info(f"雙目攝像頭已開啟 (左: {self.left_id}, 右: {self.right_id})")
            else:
                logger.info(f"單目攝像頭已開啟 (ID: {self.left_id})")
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
        讀取影像（單目/雙目）

        Returns:
            (成功標誌, 左影像, 右影像)
            單目模式下右影像為 None
        """
        if not self.is_opened:
            return False, None, None

        try:
            ret_left, frame_left = self.left_cap.read()

            if self.is_stereo:
                ret_right, frame_right = self.right_cap.read()
                if ret_left and ret_right:
                    return True, frame_left, frame_right
                else:
                    logger.warning("讀取影像失敗")
                    return False, None, None
            else:
                # 單目模式
                if ret_left:
                    return True, frame_left, None
                else:
                    logger.warning("讀取影像失敗")
                    return False, None, None

        except (IOError, OSError) as e:
            logger.error(f"攝像頭 I/O 錯誤: {e}")
            return False, None, None
        except Exception as e:
            logger.error(f"讀取影像異常: {e}")
            return False, None, None

    def read_left(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        僅讀取左攝像頭影像

        Returns:
            (成功標誌, 左影像)
        """
        if not self.is_opened or self.left_cap is None:
            return False, None

        return self.left_cap.read()

    def read_right(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        僅讀取右攝像頭影像

        Returns:
            (成功標誌, 右影像)
        """
        if not self.is_opened or self.right_cap is None:
            return False, None

        return self.right_cap.read()

    def get_stereo_frame(self) -> Optional[np.ndarray]:
        """
        獲取並排拼接的雙目影像（單目模式下返回單一影像）

        Returns:
            左右拼接的影像（雙目），或單一影像（單目），失敗返回 None
        """
        ret, left, right = self.read()
        if ret:
            if self.is_stereo and right is not None:
                return np.hstack((left, right))
            else:
                return left
        return None

    def release(self):
        """釋放攝像頭資源"""
        if self.left_cap is not None:
            self.left_cap.release()
        if self.right_cap is not None:
            self.right_cap.release()

        self.is_opened = False
        logger.info(f"{'雙目' if self.is_stereo else '單目'}攝像頭已釋放")

    def __enter__(self):
        """上下文管理器入口"""
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.release()


def list_cameras():
    """列出並顯示所有可用的攝像頭"""
    print("=== 檢測可用攝像頭 ===")
    print("正在掃描...")
    available = list_available_cameras()

    if available:
        print(f"\n找到 {len(available)} 個可用攝像頭:")
        for cam in available:
            print(f"  - 攝像頭 ID: {cam['id']} (後端: {cam['backend_name']})")
    else:
        print("\n未找到可用的攝像頭")
        print("\n可能的原因和解決方法：")
        print("  1. 攝像頭未連接")
        print("     → 請檢查 USB 連接")
        print("  2. 攝像頭被其他程式占用")
        print("     → 關閉其他使用攝像頭的應用程式（如 Skype、Teams、瀏覽器等）")
        print("  3. 攝像頭驅動問題")
        print("     → 在裝置管理員中檢查攝像頭狀態")
        print("  4. 權限問題")
        print("     → 確認應用程式有訪問攝像頭的權限（設定 > 隱私 > 相機）")
        print("\n建議：")
        print("  - 嘗試用 Windows 內建的「相機」應用測試攝像頭")
        print("  - 重新插拔 USB 攝像頭")

    return available


def test_stereo_camera():
    """測試雙目/單目攝像頭（無本機顯示，適合遠端執行）"""
    print("=== 測試攝像頭（遠端模式）===\n")

    # 先檢測可用攝像頭
    available = list_cameras()
    if not available:
        return

    print("\n按 Ctrl+C 退出\n")

    # 使用第一個可用的攝像頭
    cam_info = available[0]
    camera_id = cam_info['id']
    print(f"使用攝像頭 ID: {camera_id}")
    print(f"後端: {cam_info['backend_name']}\n")

    # 如果有多個攝像頭，提示雙目模式
    if len(available) > 1:
        print(f"提示：檢測到 {len(available)} 個攝像頭，可使用雙目模式")
        print(f"      StereoCamera(left_id={available[0]['id']}, right_id={available[1]['id']})\n")

    # 預設測試單目模式
    with StereoCamera(left_id=camera_id) as camera:
        if not camera.is_opened:
            print("無法開啟攝像頭，請檢查設備連接")
            return

        mode = "雙目" if camera.is_stereo else "單目"
        print(f"當前模式：{mode}")
        print("攝像頭正在運行，每 100 幀輸出一次狀態...")
        print()

        frame_count = 0

        try:
            while True:
                ret, left, right = camera.read()

                if ret:
                    frame_count += 1

                    # 每 100 幀輸出一次狀態
                    if frame_count % 100 == 0:
                        print(f"已處理 {frame_count} 幀影像")

                # 短暫休眠以避免過度占用 CPU
                time.sleep(0.01)

        except KeyboardInterrupt:
            print(f"\n用戶中斷，共處理 {frame_count} 幀")

    print("測試完成")


if __name__ == "__main__":
    test_stereo_camera()
