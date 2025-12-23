"""
雙目 USB 攝像頭模組
支援雙攝像頭影像擷取與基礎處理
"""

import cv2
import numpy as np
from typing import Tuple, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StereoCamera:
    """雙目 USB 攝像頭類"""

    def __init__(self, left_id: int = 0, right_id: int = 1,
                 width: int = 640, height: int = 480, fps: int = 30):
        """
        初始化雙目攝像頭

        Args:
            left_id: 左攝像頭設備 ID
            right_id: 右攝像頭設備 ID
            width: 影像寬度
            height: 影像高度
            fps: 幀率
        """
        self.left_id = left_id
        self.right_id = right_id
        self.width = width
        self.height = height
        self.fps = fps

        self.left_cap = None
        self.right_cap = None
        self.is_opened = False

    def open(self) -> bool:
        """
        開啟雙目攝像頭

        Returns:
            是否成功開啟
        """
        try:
            # 開啟左攝像頭
            self.left_cap = cv2.VideoCapture(self.left_id, cv2.CAP_DSHOW)
            if not self.left_cap.isOpened():
                logger.error(f"無法開啟左攝像頭 (ID: {self.left_id})")
                return False

            # 設定左攝像頭參數
            self.left_cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.left_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.left_cap.set(cv2.CAP_PROP_FPS, self.fps)

            # 開啟右攝像頭
            self.right_cap = cv2.VideoCapture(self.right_id, cv2.CAP_DSHOW)
            if not self.right_cap.isOpened():
                logger.error(f"無法開啟右攝像頭 (ID: {self.right_id})")
                self.left_cap.release()
                return False

            # 設定右攝像頭參數
            self.right_cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.right_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.right_cap.set(cv2.CAP_PROP_FPS, self.fps)

            self.is_opened = True
            logger.info(f"雙目攝像頭已開啟 (左: {self.left_id}, 右: {self.right_id})")
            logger.info(f"解析度: {self.width}x{self.height}, FPS: {self.fps}")
            return True

        except Exception as e:
            logger.error(f"開啟攝像頭失敗: {e}")
            return False

    def read(self) -> Tuple[bool, Optional[np.ndarray], Optional[np.ndarray]]:
        """
        讀取雙目影像

        Returns:
            (成功標誌, 左影像, 右影像)
        """
        if not self.is_opened:
            return False, None, None

        try:
            ret_left, frame_left = self.left_cap.read()
            ret_right, frame_right = self.right_cap.read()

            if ret_left and ret_right:
                return True, frame_left, frame_right
            else:
                logger.warning("讀取影像失敗")
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
        獲取並排拼接的雙目影像

        Returns:
            左右拼接的影像，失敗返回 None
        """
        ret, left, right = self.read()
        if ret:
            return np.hstack((left, right))
        return None

    def release(self):
        """釋放攝像頭資源"""
        if self.left_cap is not None:
            self.left_cap.release()
        if self.right_cap is not None:
            self.right_cap.release()

        self.is_opened = False
        logger.info("雙目攝像頭已釋放")

    def __enter__(self):
        """上下文管理器入口"""
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.release()


def test_stereo_camera():
    """測試雙目攝像頭"""
    print("=== 測試雙目攝像頭 ===")
    print("按 'q' 退出")

    with StereoCamera(left_id=0, right_id=1) as camera:
        if not camera.is_opened:
            print("無法開啟攝像頭，請檢查設備連接")
            return

        while True:
            ret, left, right = camera.read()

            if ret:
                # 顯示左右影像
                cv2.imshow('Left Camera', left)
                cv2.imshow('Right Camera', right)

                # 顯示拼接影像
                stereo_frame = camera.get_stereo_frame()
                if stereo_frame is not None:
                    cv2.imshow('Stereo Camera', stereo_frame)

            # 按 'q' 退出
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cv2.destroyAllWindows()
    print("測試完成")


if __name__ == "__main__":
    test_stereo_camera()
