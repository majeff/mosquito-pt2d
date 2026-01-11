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
雙目深度估計模組
基於立體視覺原理計算蚊子的深度（距離）
"""

from typing import List, Dict, Tuple, Optional
import numpy as np
import cv2
import logging
from config_loader import config  # 使用新的配置加载模块

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DepthEstimator:
    """雙目深度估計器"""

    def __init__(self,
                 focal_length: float = config.depth_focal_length,          # 鏡頭焦距 (mm)
                 baseline: float = config.depth_baseline,             # 雙目基線距離 (mm)
                 image_width: int = 1920,                      # 單眼影像寬度 (pixels)，應傳入實際解析度
                 sensor_width: float = config.depth_sensor_width,           # 感光元件寬度 (mm)
                 min_disparity: int = 0,              # 最小視差
                 num_disparities: int = 64,           # 視差搜索範圍（必須是16的倍數）
                 block_size: int = 15):               # SAD窗口大小（奇數）
        """
        初始化深度估計器

        Args:
            focal_length: 鏡頭焦距 (mm)
            baseline: 雙目基線距離 (mm)，左右攝像頭之間的距離
            image_width: 單眼影像寬度 (pixels)
            sensor_width: 感光元件寬度 (mm)
            min_disparity: 最小視差
            num_disparities: 視差搜索範圍
            block_size: SAD窗口大小
        """
        self.focal_length = focal_length
        self.baseline = baseline
        self.image_width = image_width
        self.sensor_width = sensor_width

        # 計算焦距（以像素為單位）
        self.focal_length_px = (focal_length * image_width) / sensor_width

        # 創建立體匹配器（使用Semi-Global Block Matching）
        self.stereo = cv2.StereoSGBM_create(
            minDisparity=min_disparity,
            numDisparities=num_disparities,
            blockSize=block_size,
            P1=8 * 3 * block_size ** 2,     # 控制視差平滑度
            P2=32 * 3 * block_size ** 2,    # 控制視差平滑度
            disp12MaxDiff=1,                # 左右一致性檢查
            uniquenessRatio=10,             # 唯一性比率
            speckleWindowSize=100,          # 斑點過濾窗口大小
            speckleRange=32,                # 斑點過濾範圍
            mode=cv2.STEREO_SGBM_MODE_SGBM_3WAY
        )

        logger.info(f"深度估計器初始化完成")
        logger.info(f"焦距: {focal_length}mm ({self.focal_length_px:.1f}px)")
        logger.info(f"基線: {baseline}mm")
        logger.info(f"理論測距範圍: {self._calc_min_depth():.2f}m - {self._calc_max_depth():.2f}m")
        logger.info(f"⚠️  實際測距受場景特徵影響（均勻區域可能無法測距）")

    def _calc_min_depth(self) -> float:
        """計算最小可測深度 (m)"""
        max_disparity = self.stereo.getNumDisparities()
        if max_disparity > 0:
            return (self.focal_length_px * self.baseline) / max_disparity / 1000
        return 0.5

    def _calc_max_depth(self) -> float:
        """計算最大可測深度 (m)"""
        min_disparity = max(self.stereo.getMinDisparity(), 1)
        return (self.focal_length_px * self.baseline) / min_disparity / 1000

    def compute_disparity(self,
                          left_frame: np.ndarray,
                          right_frame: np.ndarray) -> Optional[np.ndarray]:
        """
        計算視差圖

        Args:
            left_frame: 左眼影像（灰度或彩色）
            right_frame: 右眼影像（灰度或彩色）

        Returns:
            視差圖（float32），失敗返回 None
        """
        try:
            # 轉換為灰度圖
            if len(left_frame.shape) == 3:
                left_gray = cv2.cvtColor(left_frame, cv2.COLOR_BGR2GRAY)
            else:
                left_gray = left_frame

            if len(right_frame.shape) == 3:
                right_gray = cv2.cvtColor(right_frame, cv2.COLOR_BGR2GRAY)
            else:
                right_gray = right_frame

            # 計算視差
            disparity = self.stereo.compute(left_gray, right_gray).astype(np.float32) / 16.0

            return disparity

        except Exception as e:
            logger.error(f"計算視差失敗: {e}")
            return None

    def estimate_depth(self, disparity: float) -> Optional[float]:
        """
        根據視差估計深度

        Args:
            disparity: 視差值（像素）

        Returns:
            深度（公尺），失敗返回 None

        公式: Z = (f × B) / d
        其中:
            Z = 深度 (mm)
            f = 焦距 (pixels)
            B = 基線距離 (mm)
            d = 視差 (pixels)
        """
        if disparity <= 0:
            return None

        try:
            # 計算深度（mm）
            depth_mm = (self.focal_length_px * self.baseline) / disparity
            # 轉換為公尺
            depth_m = depth_mm / 1000.0

            return depth_m

        except Exception as e:
            logger.error(f"估計深度失敗: {e}")
            return None

    def estimate_depth_at_point(self,
                                 left_frame: np.ndarray,
                                 right_frame: np.ndarray,
                                 point: Tuple[int, int],
                                 window_size: int = 5) -> Optional[float]:
        """
        估計特定點的深度

        Args:
            left_frame: 左眼影像
            right_frame: 右眼影像
            point: 目標點座標 (x, y)
            window_size: 取樣窗口大小

        Returns:
            深度（公尺），失敗返回 None
        """
        # 計算視差圖
        disparity_map = self.compute_disparity(left_frame, right_frame)
        if disparity_map is None:
            return None

        x, y = point
        h, w = disparity_map.shape

        # 確保點在影像範圍內
        if x < 0 or x >= w or y < 0 or y >= h:
            logger.warning(f"點 ({x}, {y}) 超出影像範圍")
            return None

        # 取窗口內的平均視差（減少噪聲）
        half_window = window_size // 2
        y_min = max(0, y - half_window)
        y_max = min(h, y + half_window + 1)
        x_min = max(0, x - half_window)
        x_max = min(w, x + half_window + 1)

        window_disparity = disparity_map[y_min:y_max, x_min:x_max]
        valid_disparities = window_disparity[window_disparity > 0]

        if len(valid_disparities) == 0:
            # 降低日誌等級，這是常見情況（均勻區域、遮擋等）
            logger.debug(f"點 ({x}, {y}) 處無有效視差 (可能原因: 均勻區域/遮擋/光照不足)")
            return None

        # 檢查有效視差的比例
        valid_ratio = len(valid_disparities) / window_disparity.size
        if valid_ratio < 0.3:  # 少於30%的有效視差
            logger.debug(f"點 ({x}, {y}) 視差質量較低 ({valid_ratio:.1%} 有效)")

        # 使用中位數（比平均值更魯棒）
        median_disparity = np.median(valid_disparities)

        # 估計深度
        return self.estimate_depth(median_disparity)

    def estimate_depth_for_detection(self,
                                      left_frame: np.ndarray,
                                      right_frame: np.ndarray,
                                      bbox: Tuple[int, int, int, int]) -> Optional[Dict]:
        """
        估計檢測框內目標的深度

        Args:
            left_frame: 左眼影像
            right_frame: 右眼影像
            bbox: 邊界框 (x1, y1, x2, y2)

        Returns:
            包含深度資訊的字典，失敗返回 None
            {
                'depth': 深度(m),
                'center': 中心點座標,
                'disparity': 視差值
            }
        """
        x1, y1, x2, y2 = bbox

        # 計算檢測框中心點
        center_x = (x1 + x2) // 2
        center_y = (y1 + y2) // 2

        # 估計中心點深度
        depth = self.estimate_depth_at_point(
            left_frame, right_frame,
            (center_x, center_y),
            window_size=min(x2 - x1, y2 - y1) // 2  # 使用bbox的一半作為窗口
        )

        if depth is None:
            return None

        # 計算物件實際尺寸（寬度和高度）
        # 公式：實際尺寸 = (像素尺寸 × 深度) / 焦距
        bbox_width_px = x2 - x1
        bbox_height_px = y2 - y1

        # 計算實際寬度和高度（毫米）
        real_width_mm = (bbox_width_px * depth * 10000) / self.focal_length_px  # m -> mm
        real_height_mm = (bbox_height_px * depth * 10000) / self.focal_length_px

        # 使用較大的邊作為物件尺寸（蚊子可能是橫向或縱向）
        object_size_mm = max(real_width_mm, real_height_mm)

        return {
            'depth': depth,
            'center': (center_x, center_y),
            'distance_cm': depth * 100,  # 轉換為公分
            'real_width_mm': real_width_mm,
            'real_height_mm': real_height_mm,
            'object_size_mm': object_size_mm
        }

    def create_depth_colormap(self, disparity_map: np.ndarray) -> np.ndarray:
        """
        創建深度視覺化彩色圖

        Args:
            disparity_map: 視差圖

        Returns:
            彩色深度圖
        """
        # 正規化視差
        disparity_normalized = cv2.normalize(
            disparity_map, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U
        )

        # 應用彩色映射
        depth_colormap = cv2.applyColorMap(disparity_normalized, cv2.COLORMAP_JET)

        return depth_colormap


def test_depth_estimation():
    """測試深度估計"""
    from stereo_camera import StereoCamera

    logger.info("=== 測試深度估計 ===")
    logger.info("說明:")
    logger.info("  - 左鍵點擊：測量點擊位置的深度")
    logger.info("  - 'd' 鍵：切換深度圖顯示")
    logger.info("  - 'q' 鍵：退出")

    # 初始化攝像頭和深度估計器
    camera = StereoCamera(left_id=0, right_id=1, width=1920, height=1080)
    estimator = DepthEstimator(
        focal_length=3.0,
        baseline=120.0,
        image_width=1920
    )

    show_depth_map = False
    clicked_point = None

    def mouse_callback(event, x, y, flags, param):
        nonlocal clicked_point
        if event == cv2.EVENT_LBUTTONDOWN:
            clicked_point = (x, y)

    if not camera.open():
        print("無法開啟攝像頭")
        return

    cv2.namedWindow('Stereo Vision')
    cv2.setMouseCallback('Stereo Vision', mouse_callback)

    try:
        while True:
            ret, left, right = camera.read()
            if not ret:
                continue

            # 顯示影像
            if show_depth_map:
                # 計算並顯示深度圖
                disparity = estimator.compute_disparity(left, right)
                if disparity is not None:
                    depth_colormap = estimator.create_depth_colormap(disparity)
                    display = depth_colormap
                else:
                    display = left
            else:
                display = left

            # 如果有點擊，測量深度
            if clicked_point is not None:
                depth = estimator.estimate_depth_at_point(left, right, clicked_point)
                if depth is not None:
                    # 繪製點和深度資訊
                    cv2.circle(display, clicked_point, 5, (0, 255, 0), -1)
                    text = f"Depth: {depth:.2f}m ({depth*100:.1f}cm)"
                    cv2.putText(display, text, (clicked_point[0] + 10, clicked_point[1] - 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            # 顯示
            cv2.imshow('Stereo Vision', display)

            # 鍵盤控制
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('d'):
                show_depth_map = not show_depth_map
                logger.info(f"深度圖顯示: {'開啟' if show_depth_map else '關閉'}")

    finally:
        camera.release()
        cv2.destroyAllWindows()

    print("測試完成")


if __name__ == "__main__":
    test_depth_estimation()
