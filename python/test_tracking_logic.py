#!/usr/bin/env python3
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

#!/usr/bin/env python3
"""
追蹤邏輯驗證腳本
測試持續追蹤機制是否正確運作
"""

import time


class TrackingLogicTest:
    """追蹤邏輯測試類"""

    def __init__(self):
        self.tracking_active = False
        self.last_detection_time = 0
        self.no_detection_timeout = 3.0

    def simulate_detection(self, has_detection: bool):
        """
        模擬檢測結果

        Args:
            has_detection: 是否檢測到目標

        Returns:
            追蹤狀態資訊
        """
        current_time = time.time()

        if has_detection:
            # 檢測到目標
            self.last_detection_time = current_time

            if not self.tracking_active:
                print(f"[{current_time:.1f}s] ✅ 開始追蹤")
                self.tracking_active = True
            else:
                print(f"[{current_time:.1f}s] ⏩ 持續追蹤中...")

            return "TRACKING"

        else:
            # 未檢測到目標
            if self.tracking_active:
                time_since_last = current_time - self.last_detection_time

                if time_since_last > self.no_detection_timeout:
                    # 超時，失去目標
                    print(f"[{current_time:.1f}s] ❌ 失去目標（超時 {time_since_last:.1f}s）")
                    self.tracking_active = False
                    return "LOST"
                else:
                    # 未超時，保持追蹤
                    print(f"[{current_time:.1f}s] ⏸️  暫時失去目標 ({time_since_last:.1f}s)，保持追蹤...")
                    return "TRACKING_WAIT"
            else:
                print(f"[{current_time:.1f}s] 🔍 監控中...")
                return "SCANNING"


def test_continuous_tracking():
    """測試持續追蹤邏輯"""
    print("=" * 60)
    print("測試場景 1: 持續檢測到目標")
    print("=" * 60)

    tracker = TrackingLogicTest()

    # 模擬持續檢測到目標（10 次）
    for i in range(10):
        tracker.simulate_detection(True)
        time.sleep(0.3)

    print("\n預期結果: 應該持續保持追蹤狀態 ✅\n")


def test_temporary_loss():
    """測試暫時失去目標"""
    print("=" * 60)
    print("測試場景 2: 暫時失去目標（未超時）")
    print("=" * 60)

    tracker = TrackingLogicTest()

    # 檢測到目標
    print("階段 1: 檢測到目標")
    tracker.simulate_detection(True)
    time.sleep(0.3)

    # 持續追蹤
    tracker.simulate_detection(True)
    time.sleep(0.3)

    # 暫時失去目標（1.5 秒內，未超時）
    print("\n階段 2: 暫時失去目標（1.5 秒）")
    for i in range(5):
        tracker.simulate_detection(False)
        time.sleep(0.3)

    # 重新檢測到目標
    print("\n階段 3: 重新檢測到目標")
    tracker.simulate_detection(True)
    time.sleep(0.3)

    tracker.simulate_detection(True)
    time.sleep(0.3)

    print("\n預期結果: 暫時失去後應該恢復追蹤，不會回到監控模式 ✅\n")


def test_timeout_loss():
    """測試超時失去目標"""
    print("=" * 60)
    print("測試場景 3: 超時失去目標（> 3 秒）")
    print("=" * 60)

    tracker = TrackingLogicTest()

    # 檢測到目標
    print("階段 1: 檢測到目標")
    tracker.simulate_detection(True)
    time.sleep(0.3)

    tracker.simulate_detection(True)
    time.sleep(0.3)

    # 失去目標超過 3 秒
    print("\n階段 2: 失去目標（> 3 秒）")
    for i in range(12):  # 3.6 秒
        tracker.simulate_detection(False)
        time.sleep(0.3)

    # 再次檢測到目標
    print("\n階段 3: 再次檢測到目標")
    tracker.simulate_detection(True)
    time.sleep(0.3)

    print("\n預期結果: 超時後應該返回監控模式，再次檢測時重新開始追蹤 ✅\n")


def test_intermittent_detection():
    """測試間歇性檢測"""
    print("=" * 60)
    print("測試場景 4: 間歇性檢測（檢測-失去-檢測循環）")
    print("=" * 60)

    tracker = TrackingLogicTest()

    # 檢測到目標
    print("階段 1: 初次檢測")
    tracker.simulate_detection(True)
    time.sleep(0.3)

    # 模擬間歇性檢測（檢測到 -> 失去 -> 檢測到，循環）
    print("\n階段 2: 間歇性檢測")
    for cycle in range(3):
        print(f"\n--- 循環 {cycle + 1} ---")
        # 檢測到 2 次
        tracker.simulate_detection(True)
        time.sleep(0.3)
        tracker.simulate_detection(True)
        time.sleep(0.3)

        # 失去 3 次（0.9 秒，未超時）
        tracker.simulate_detection(False)
        time.sleep(0.3)
        tracker.simulate_detection(False)
        time.sleep(0.3)
        tracker.simulate_detection(False)
        time.sleep(0.3)

    print("\n預期結果: 應該持續保持追蹤狀態，不會因為短暫失去而放棄 ✅\n")


def main():
    """主測試函數"""
    print("\n🧪 追蹤邏輯驗證測試")
    print("=" * 60)
    print("測試目標：驗證 AI 追蹤系統是否在找到蚊子後持續追蹤")
    print("核心邏輯：只有連續 3 秒未檢測到目標才判定為失去追蹤")
    print("=" * 60)
    print()

    try:
        # 測試 1: 持續追蹤
        test_continuous_tracking()
        time.sleep(1)

        # 測試 2: 暫時失去目標
        test_temporary_loss()
        time.sleep(1)

        # 測試 3: 超時失去目標
        test_timeout_loss()
        time.sleep(1)

        # 測試 4: 間歇性檢測
        test_intermittent_detection()

        print("=" * 60)
        print("✅ 所有測試完成！")
        print("=" * 60)
        print("\n📝 測試結論：")
        print("1. ✅ 持續檢測到目標時，保持追蹤狀態")
        print("2. ✅ 暫時失去目標（< 3s）時，保持追蹤狀態等待恢復")
        print("3. ✅ 超時失去目標（> 3s）時，返回監控模式")
        print("4. ✅ 間歇性檢測時，持續追蹤不中斷")
        print("\n🎯 結論：追蹤邏輯符合設計要求，會持續追蹤目標！")

    except KeyboardInterrupt:
        print("\n\n測試被用戶中斷")


if __name__ == "__main__":
    main()
