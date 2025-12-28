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
溫度監控測試腳本
測試本機溫度監控功能
"""

import sys
import os

# 添加 python 目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from temperature_monitor import TemperatureMonitor
import time

def main():
    print("=" * 60)
    print("溫度監控測試")
    print("=" * 60)
    print()

    # 創建溫度監控器
    monitor = TemperatureMonitor()

    if not monitor.is_supported:
        print("❌ 當前平台不支援溫度監控")
        print()
        print("支援的平台：")
        print("  - Linux (Orange Pi 5, Raspberry Pi 等)")
        print("  - Windows (需安裝 psutil 套件)")
        print()
        return 1

    print("✓ 溫度監控已啟用")
    print(f"  警告閾值: {monitor.warning_threshold}°C")
    print(f"  暫停閾值: {monitor.pause_threshold}°C")
    print(f"  恢復閾值: {monitor.resume_threshold}°C")
    print()
    print("開始監控（按 Ctrl+C 退出）...")
    print("-" * 60)

    try:
        while True:
            temp_info = monitor.check_temperature()
            temp = temp_info.get('temperature')
            status = temp_info.get('status')
            message = temp_info.get('message')
            is_paused = temp_info.get('is_paused', False)

            if temp is not None:
                # 顯示溫度
                status_text = monitor.get_status_text(temp_info)

                # 顯示狀態指示
                if is_paused:
                    indicator = "🔴 PAUSED"
                elif status == 'warning':
                    indicator = "⚠️  WARNING"
                else:
                    indicator = "✓  NORMAL"

                print(f"\r{indicator} | {status_text}    ", end='', flush=True)

                # 如果有訊息，換行顯示
                if message:
                    print(f"\n{message}")
                    print("-" * 60)

            time.sleep(2)

    except KeyboardInterrupt:
        print("\n\n測試結束")
        return 0

if __name__ == "__main__":
    exit(main())
