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
配置加載模組
從 mosquito.ini 文件加載配置參數
"""

import os
import configparser
import socket
from pathlib import Path


class ConfigLoader:
    """配置加載器"""

    def __init__(self, config_path: str | None = None):
        """
        初始化配置加載器

        Args:
            config_path: 配置文件路徑，若為 None 則自動搜尋
        """
        self.config = configparser.ConfigParser()

        # 構建候選路徑（依優先順序）
        candidates: list[Path] = []

        # 1) 環境變數指定
        env_path = os.environ.get("MOSQUITO_CONFIG")
        if env_path:
            candidates.append(Path(env_path))

        # 2) 參數指定
        if config_path:
            candidates.append(Path(config_path))

        # 3) 模組所在目錄（python/）
        module_dir = Path(__file__).resolve().parent
        candidates.append(module_dir / "mosquito.ini")

        # 4) 當前工作目錄
        candidates.append(Path.cwd() / "mosquito.ini")

        # 選擇首個存在的配置文件
        chosen: Path | None = None
        for p in candidates:
            if p.exists():
                chosen = p
                break

        if not chosen:
            # 提示候選路徑，方便除錯
            hint = " | ".join(str(p) for p in candidates)
            raise FileNotFoundError(f"配置文件不存在（已嘗試）：{hint}")

        self.config_path = chosen

        # 讀取配置文件
        self.config.read(self.config_path, encoding='utf-8')
        # 基準目錄（用於解析相對路徑）
        self._config_base_dir = self.config_path.parent

    def _get_local_ip(self):
        """自動偵測本機 IP 地址"""
        try:
            # 連接到外部伺服器以獲取本機實際 IP（不會真正發送數據）
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            # 備用方案：嘗試獲取主機名稱對應的 IP
            try:
                return socket.gethostbyname(socket.gethostname())
            except Exception:
                return "127.0.0.1"

    # 內部工具：將相對路徑解析到 sample_collection_dir 之下
    def _resolve_under_sample_base(self, value: str) -> str:
        # 取樣本根目錄（已保證為絕對路徑）
        base = Path(self.sample_collection_dir)
        p = Path(value)
        if p.is_absolute():
            return str(p)
        return str((base / p).resolve())

    # AI檢測相關配置
    @property
    def imgsz(self):
        return self.config.getint('AI_DETECTION', 'imgsz', fallback=640)

    @property
    def confidence_threshold(self):
        return self.config.getfloat('AI_DETECTION', 'confidence_threshold', fallback=0.4)

    @property
    def iou_threshold(self):
        return self.config.getfloat('AI_DETECTION', 'iou_threshold', fallback=0.45)

    @property
    def detection_mode(self):
        return self.config.get('AI_DETECTION', 'detection_mode', fallback='tiling')

    @property
    def tile_overlap(self):
        return self.config.getfloat('AI_DETECTION', 'tile_overlap', fallback=0.25)

    @property
    def detection_margin(self):
        return self.config.getfloat('AI_DETECTION', 'detection_margin', fallback=0.0)

    @property
    def min_mosquito_size_mm(self):
        return self.config.getint('AI_DETECTION', 'min_mosquito_size_mm', fallback=3)

    @property
    def max_mosquito_size_mm(self):
        return self.config.getint('AI_DETECTION', 'max_mosquito_size_mm', fallback=15)

    @property
    def enable_white_pixel_filter(self):
        return self.config.getboolean('AI_DETECTION', 'enable_white_pixel_filter', fallback=True)

    @property
    def white_pixel_threshold(self):
        return self.config.getint('AI_DETECTION', 'white_pixel_threshold', fallback=240)

    @property
    def white_pixel_ratio_threshold(self):
        return self.config.getfloat('AI_DETECTION', 'white_pixel_ratio_threshold', fallback=0.7)

    # 單目過濾器相關配置
    @property
    def enable_bbox_size_filter(self):
        return self.config.getboolean('SINGLE_CAMERA_FILTER', 'enable_bbox_size_filter', fallback=True)

    @property
    def min_bbox_size_px(self):
        return self.config.getint('SINGLE_CAMERA_FILTER', 'min_bbox_size_px', fallback=10)

    @property
    def max_bbox_size_px(self):
        return self.config.getint('SINGLE_CAMERA_FILTER', 'max_bbox_size_px', fallback=200)

    @property
    def enable_aspect_ratio_filter(self):
        return self.config.getboolean('SINGLE_CAMERA_FILTER', 'enable_aspect_ratio_filter', fallback=True)

    @property
    def min_aspect_ratio(self):
        return self.config.getfloat('SINGLE_CAMERA_FILTER', 'min_aspect_ratio', fallback=0.3)

    @property
    def max_aspect_ratio(self):
        return self.config.getfloat('SINGLE_CAMERA_FILTER', 'max_aspect_ratio', fallback=3.0)

    @property
    def enable_temporal_filter(self):
        return self.config.getboolean('SINGLE_CAMERA_FILTER', 'enable_temporal_filter', fallback=True)

    @property
    def min_consecutive_frames(self):
        return self.config.getint('SINGLE_CAMERA_FILTER', 'min_consecutive_frames', fallback=3)

    @property
    def enable_motion_filter(self):
        return self.config.getboolean('SINGLE_CAMERA_FILTER', 'enable_motion_filter', fallback=True)

    @property
    def max_movement_px_per_frame(self):
        return self.config.getint('SINGLE_CAMERA_FILTER', 'max_movement_px_per_frame', fallback=150)

    @property
    def max_static_frames(self):
        return self.config.getint('SINGLE_CAMERA_FILTER', 'max_static_frames', fallback=60)

    @property
    def static_threshold_px(self):
        return self.config.getint('SINGLE_CAMERA_FILTER', 'static_threshold_px', fallback=5)

    # 追蹤相關配置
    @property
    def pan_gain(self):
        return self.config.getfloat('TRACKING', 'pan_gain', fallback=0.15)

    @property
    def tilt_gain(self):
        return self.config.getfloat('TRACKING', 'tilt_gain', fallback=0.15)

    @property
    def no_detection_timeout(self):
        return self.config.getfloat('TRACKING', 'no_detection_timeout', fallback=3.0)

    @property
    def target_lock_distance(self):
        return self.config.getint('TRACKING', 'target_lock_distance', fallback=100)

    # 硬體相關配置
    @property
    def arduino_port(self):
        return self.config.get('HARDWARE', 'arduino_port', fallback='/dev/ttyUSB0')

    @property
    def left_camera_id(self):
        return self.config.getint('HARDWARE', 'left_camera_id', fallback=0)

    @property
    def pan_servo_id(self):
        return self.config.getint('HARDWARE', 'pan_servo_id', fallback=1)

    @property
    def tilt_servo_id(self):
        return self.config.getint('HARDWARE', 'tilt_servo_id', fallback=2)

    # 這裏移除了 right_camera_id 屬性，因為我們不再支援獨立攝像頭模式

    # 警報相關配置
    @property
    def beep_cooldown(self):
        return self.config.getfloat('ALERTS', 'beep_cooldown', fallback=2.0)

    @property
    def laser_cooldown(self):
        return self.config.getfloat('ALERTS', 'laser_cooldown', fallback=0.5)

    # 樣本收集相關配置
    @property
    def save_high_confidence_samples(self):
        return self.config.getboolean('SAMPLE_COLLECTION', 'save_high_confidence_samples', fallback=False)

    @property
    def save_uncertain_samples(self):
        return self.config.getboolean('SAMPLE_COLLECTION', 'save_uncertain_samples', fallback=True)

    @property
    def uncertain_conf_range(self):
        min_val = self.config.getfloat('SAMPLE_COLLECTION', 'uncertain_conf_range_min', fallback=0.4)
        max_val = self.config.getfloat('SAMPLE_COLLECTION', 'uncertain_conf_range_max', fallback=0.7)
        return (min_val, max_val)

    @property
    def max_samples(self):
        return self.config.getint('SAMPLE_COLLECTION', 'max_samples', fallback=1000)

    @property
    def save_interval(self):
        return self.config.getfloat('SAMPLE_COLLECTION', 'save_interval', fallback=3.0)

    @property
    def save_annotations(self):
        return self.config.getboolean('SAMPLE_COLLECTION', 'save_annotations', fallback=True)

    @property
    def save_full_frame(self):
        return self.config.getboolean('SAMPLE_COLLECTION', 'save_full_frame', fallback=False)

    # 樣本標註相關配置
    @property
    def sample_collection_dir(self):
        raw = self.config.get('SAMPLE_ANNOTATION', 'sample_collection_dir', fallback="sample_collection")
        p = Path(raw)
        # 將相對路徑錨定到配置檔所在目錄，避免 CWD 影響
        if not p.is_absolute():
            p = (self._config_base_dir / p).resolve()
        return str(p)

    @property
    def medium_confidence_dir(self):
        raw = self.config.get('SAMPLE_ANNOTATION', 'medium_confidence_dir', fallback="medium_confidence")
        return self._resolve_under_sample_base(raw)

    @property
    def high_confidence_dir(self):
        raw = self.config.get('SAMPLE_ANNOTATION', 'high_confidence_dir', fallback="high_confidence")
        return self._resolve_under_sample_base(raw)

    @property
    def confirmed_mosquito_dir(self):
        raw = self.config.get('SAMPLE_ANNOTATION', 'confirmed_mosquito_dir', fallback="confirmed/mosquito")
        return self._resolve_under_sample_base(raw)

    @property
    def confirmed_not_mosquito_dir(self):
        raw = self.config.get('SAMPLE_ANNOTATION', 'confirmed_not_mosquito_dir', fallback="confirmed/not_mosquito")
        return self._resolve_under_sample_base(raw)

    # 樣本標註相關配置 (用於 label_samples.py)
    @property
    def RELOCATION_BASE_DIR(self):
        return self.config.get('SAMPLE_ANNOTATION', 'relocation_base_dir', fallback="./relocated_samples")

    @property
    def RELOCATION_MOSQUITO_DIR(self):
        return self.config.get('SAMPLE_ANNOTATION', 'relocation_mosquito_dir', fallback="relocated_samples/mosquito")

    @property
    def RELOCATION_NOT_MOSQUITO_DIR(self):
        return self.config.get('SAMPLE_ANNOTATION', 'relocation_not_mosquito_dir', fallback="relocated_samples/not_mosquito")

    @property
    def COLAB_NOTEBOOK_DEST_DIR(self):
        return self.config.get('SAMPLE_ANNOTATION', 'colab_notebook_dest_dir', fallback="./colab_notebooks")

    @property
    def MEDIUM_CONFIDENCE_DIR(self):
        raw = self.config.get('SAMPLE_ANNOTATION', 'medium_confidence_dir', fallback="medium_confidence")
        return self._resolve_under_sample_base(raw)

    @property
    def HIGH_CONFIDENCE_DIR(self):
        raw = self.config.get('SAMPLE_ANNOTATION', 'high_confidence_dir', fallback="high_confidence")
        return self._resolve_under_sample_base(raw)

    @property
    def CONFIRMED_MOSQUITO_DIR(self):
        raw = self.config.get('SAMPLE_ANNOTATION', 'confirmed_mosquito_dir', fallback="confirmed/mosquito")
        return self._resolve_under_sample_base(raw)

    @property
    def CONFIRMED_NOT_MOSQUITO_DIR(self):
        raw = self.config.get('SAMPLE_ANNOTATION', 'confirmed_not_mosquito_dir', fallback="confirmed/not_mosquito")
        return self._resolve_under_sample_base(raw)

    # 網路相關配置
    @property
    def device_ip(self):
        configured_ip = self.config.get('NETWORK', 'device_ip', fallback=None)
        if configured_ip is None or configured_ip == "127.0.0.1":
            return self._get_local_ip()
        return configured_ip

    @property
    def external_url(self):
        url = self.config.get('NETWORK', 'external_url', fallback=None)
        return url if url else None

    # 串流伺服器相關配置
    @property
    def stream_port(self):
        return self.config.getint('STREAMING_SERVER', 'stream_port', fallback=5000)

    @property
    def stream_quality(self):
        return self.config.getint('STREAMING_SERVER', 'stream_quality', fallback=80)

    @property
    def stream_fps(self):
        return self.config.getint('STREAMING_SERVER', 'stream_fps', fallback=15)

    @property
    def rtsp_url(self):
        return self.config.get('STREAMING_SERVER', 'rtsp_url', fallback="rtsp://0.0.0.0:8554/mosquito")

    @property
    def rtsp_bitrate(self):
        return self.config.getint('STREAMING_SERVER', 'rtsp_bitrate', fallback=2000)

    @property
    def rtsp_preset(self):
        return self.config.get('STREAMING_SERVER', 'rtsp_preset', fallback="ultrafast")

    # 溫度監控相關配置
    @property
    def enable_temperature_monitoring(self):
        return self.config.getboolean('TEMPERATURE_MONITORING', 'enable_temperature_monitoring', fallback=True)

    @property
    def temperature_warning_threshold(self):
        return self.config.getfloat('TEMPERATURE_MONITORING', 'temperature_warning_threshold', fallback=75.0)

    @property
    def temperature_pause_threshold(self):
        return self.config.getfloat('TEMPERATURE_MONITORING', 'temperature_pause_threshold', fallback=80.0)

    @property
    def temperature_resume_threshold(self):
        return self.config.getfloat('TEMPERATURE_MONITORING', 'temperature_resume_threshold', fallback=70.0)

    @property
    def temperature_check_interval(self):
        return self.config.getfloat('TEMPERATURE_MONITORING', 'temperature_check_interval', fallback=60.0)

    @property
    def temperature_sensor_path(self):
        return self.config.get('TEMPERATURE_MONITORING', 'temperature_sensor_path', fallback="/sys/class/thermal/thermal_zone0/temp")

    # 光照度監控相關配置
    @property
    def enable_illumination_monitoring(self):
        return self.config.getboolean('ILLUMINATION_MONITORING', 'enable_illumination_monitoring', fallback=True)

    @property
    def illumination_warning_threshold(self):
        return self.config.getint('ILLUMINATION_MONITORING', 'illumination_warning_threshold', fallback=60)

    @property
    def illumination_pause_threshold(self):
        return self.config.getint('ILLUMINATION_MONITORING', 'illumination_pause_threshold', fallback=40)

    @property
    def illumination_check_interval(self):
        return self.config.getfloat('ILLUMINATION_MONITORING', 'illumination_check_interval', fallback=5.0)

    # 攝像頭相關配置
    @property
    def camera_dual_width(self):
        return self.config.getint('CAMERA', 'camera_dual_width', fallback=3840)

    @property
    def camera_dual_height(self):
        return self.config.getint('CAMERA', 'camera_dual_height', fallback=1080)

    @property
    def camera_dual_fps(self):
        return self.config.getint('CAMERA', 'camera_dual_fps', fallback=60)

    @property
    def frame_delay(self):
        return self.config.getfloat('CAMERA', 'frame_delay', fallback=0.03)

    # 串口相關配置
    @property
    def arduino_baudrate(self):
        return self.config.getint('SERIAL', 'arduino_baudrate', fallback=115200)

    @property
    def arduino_timeout(self):
        return self.config.getfloat('SERIAL', 'arduino_timeout', fallback=1.0)

    # 深度估計相關配置
    @property
    def depth_focal_length(self):
        return self.config.getfloat('DEPTH_ESTIMATION', 'depth_focal_length', fallback=3.0)

    @property
    def depth_baseline(self):
        return self.config.getfloat('DEPTH_ESTIMATION', 'depth_baseline', fallback=120.0)

    @property
    def depth_sensor_width(self):
        return self.config.getfloat('DEPTH_ESTIMATION', 'depth_sensor_width', fallback=5.0)

    # 追蹤相關配置
    @property
    def position_update_interval(self):
        return self.config.getfloat('TRACKER', 'position_update_interval', fallback=0.5)


# 創建全局配置實例
config = ConfigLoader()