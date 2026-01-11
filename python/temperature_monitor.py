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
本機溫度監控模組
監控系統溫度，當溫度過高時觸發保護機制
"""

import os
import time
import logging
import platform
from typing import Optional

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from pathlib import Path
import time
import logging
from config_loader import config  # 使用新的配置加载模块

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TemperatureMonitor:
    """系統溫度監控器"""

    def __init__(self,
                 warning_threshold: float = TEMPERATURE_WARNING_THRESHOLD,
                 pause_threshold: float = TEMPERATURE_PAUSE_THRESHOLD,
                 resume_threshold: float = TEMPERATURE_RESUME_THRESHOLD,
                 check_interval: float = TEMPERATURE_CHECK_INTERVAL,
                 sensor_path: str = TEMPERATURE_SENSOR_PATH):
        """
        初始化溫度監控器

        Args:
            warning_threshold: 警告溫度閾值（°C）
            pause_threshold: 暫停辨識溫度閾值（°C）
            resume_threshold: 恢復辨識溫度閾值（°C）
            check_interval: 檢查間隔（秒）
            sensor_path: 溫度感測器路徑
        """
        # 從配置加載溫度監控參數
        self.warning_threshold = config.temperature_warning_threshold
        self.pause_threshold = config.temperature_pause_threshold
        self.resume_threshold = config.temperature_resume_threshold
        self.check_interval = config.temperature_check_interval
        self.sensor_path = Path(config.temperature_sensor_path)

        self.is_paused = False
        self.last_temperature = 0.0
        self.last_check_time = 0.0
        self.warning_shown = False

        # 檢查是否為支援的平台
        self.is_supported = self._check_platform_support()

        if not self.is_supported:
            logger.warning("溫度監控不支援當前平台，已禁用")
        else:
            logger.info(f"溫度監控已啟用 - 警告: {warning_threshold}°C, 暫停: {pause_threshold}°C, 恢復: {resume_threshold}°C")

    def _check_platform_support(self) -> bool:
        """
        檢查平台是否支援溫度監控

        Returns:
            是否支援
        """
        if not ENABLE_TEMPERATURE_MONITORING:
            return False

        system = platform.system()

        if system == "Linux":
            # 檢查溫度感測器是否存在
            return os.path.exists(self.sensor_path)
        elif system == "Windows":
            # Windows 需要額外套件 (如 psutil, wmi)
            if PSUTIL_AVAILABLE:
                try:
                    # 嘗試讀取溫度
                    temps = psutil.sensors_temperatures()
                    return len(temps) > 0
                except AttributeError:
                    logger.warning("Windows 溫度監控需要安裝 psutil 套件")
                    return False
            else:
                logger.warning("Windows 溫度監控需要安裝 psutil 套件")
                return False
        else:
            return False

    def get_temperature(self) -> Optional[float]:
        """
        讀取當前系統溫度

        Returns:
            溫度值（°C），如果讀取失敗則返回 None
        """
        if not self.is_supported:
            return None

        try:
            system = platform.system()

            if system == "Linux":
                # 從 Linux thermal_zone 讀取溫度
                with open(self.sensor_path, 'r') as f:
                    temp_str = f.read().strip()
                    # thermal_zone 通常以毫度為單位
                    temp = float(temp_str) / 1000.0
                    return temp

            elif system == "Windows":
                # 使用 psutil 讀取溫度
                if PSUTIL_AVAILABLE:
                    temps = psutil.sensors_temperatures()
                    if temps:
                        # 取第一個可用的溫度感測器
                        for name, entries in temps.items():
                            if entries:
                                return entries[0].current
                return None

        except Exception as e:
            logger.error(f"讀取溫度失敗: {e}")
            return None

    def check_temperature(self) -> dict:
        """
        檢查溫度並返回狀態

        Returns:
            字典包含:
            - temperature: 當前溫度
            - is_paused: 是否需要暫停
            - status: 狀態訊息 ('normal', 'warning', 'paused', 'resumed')
            - message: 詳細訊息
        """
        current_time = time.time()

        # 檢查是否需要更新
        if current_time - self.last_check_time < self.check_interval:
            return {
                'temperature': self.last_temperature,
                'is_paused': self.is_paused,
                'status': 'cached',
                'message': ''
            }

        self.last_check_time = current_time
        temp = self.get_temperature()

        if temp is None:
            return {
                'temperature': None,
                'is_paused': self.is_paused,
                'status': 'unavailable',
                'message': '無法讀取溫度'
            }

        self.last_temperature = temp
        status = 'normal'
        message = ''

        # 檢查是否需要暫停
        if not self.is_paused and temp >= self.pause_threshold:
            self.is_paused = True
            status = 'paused'
            message = f'⚠️ 溫度過高 ({temp:.1f}°C)，已暫停 AI 辨識'
            logger.warning(message)

        # 檢查是否可以恢復
        elif self.is_paused and temp <= self.resume_threshold:
            self.is_paused = False
            status = 'resumed'
            message = f'✓ 溫度已降低 ({temp:.1f}°C)，恢復 AI 辨識'
            logger.info(message)
            self.warning_shown = False

        # 檢查是否需要警告
        elif not self.is_paused and temp >= self.warning_threshold:
            if not self.warning_shown:
                status = 'warning'
                message = f'⚠ 溫度警告 ({temp:.1f}°C)，接近暫停閾值'
                logger.warning(message)
                self.warning_shown = True
        else:
            # 溫度正常，重置警告標記
            if self.warning_shown and temp < self.warning_threshold:
                self.warning_shown = False

        return {
            'temperature': temp,
            'is_paused': self.is_paused,
            'status': status,
            'message': message
        }

    def get_status_text(self, temp_info: dict) -> str:
        """
        生成溫度狀態顯示文本

        Args:
            temp_info: check_temperature() 返回的字典

        Returns:
            格式化的狀態文本
        """
        temp = temp_info.get('temperature')
        if temp is None:
            return "溫度: N/A"

        is_paused = temp_info.get('is_paused', False)
        status = temp_info.get('status', 'normal')

        # 根據狀態選擇顏色標記
        if is_paused:
            status_mark = "[已暫停]"
        elif status == 'warning':
            status_mark = "[警告]"
        else:
            status_mark = ""

        return f"溫度: {temp:.1f}°C {status_mark}"


if __name__ == "__main__":
    """測試溫度監控"""
    print("=" * 50)
    print("溫度監控測試")
    print("=" * 50)

    monitor = TemperatureMonitor()

    if not monitor.is_supported:
        print("❌ 當前平台不支援溫度監控")
        exit(1)

    print(f"✓ 溫度監控已啟用")
    print(f"  警告閾值: {monitor.warning_threshold}°C")
    print(f"  暫停閾值: {monitor.pause_threshold}°C")
    print(f"  恢復閾值: {monitor.resume_threshold}°C")
    print()

    try:
        while True:
            temp_info = monitor.check_temperature()
            temp = temp_info.get('temperature')
            status = temp_info.get('status')
            message = temp_info.get('message')

            if temp is not None:
                status_text = monitor.get_status_text(temp_info)
                print(f"\r{status_text}", end='', flush=True)

                if message:
                    print(f"\n{message}")

            time.sleep(2)

    except KeyboardInterrupt:
        print("\n\n測試結束")
