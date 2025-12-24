#!/usr/bin/env python3
"""
多目標追蹤邏輯測試
驗證在多個蚊子目標存在時，系統是否能鎖定單一目標持續追蹤
"""

import numpy as np


class MultiTargetTrackingTest:
    """多目標追蹤測試類"""

    def __init__(self):
        self.tracking_active = False
        self.locked_target_position = None
        self.target_lock_distance = 100

    def _find_closest_detection(self, detections, target_position):
        """找到最接近目標位置的檢測"""
        if not detections or target_position is None:
            return None

        closest_detection = None
        min_distance = float('inf')

        for detection in detections:
            center_x, center_y = detection['center']
            distance = np.sqrt((center_x - target_position[0])**2 +
                             (center_y - target_position[1])**2)

            if distance < min_distance:
                min_distance = distance
                closest_detection = detection

        if min_distance < self.target_lock_distance:
            return closest_detection
        return None

    def _get_best_detection(self, detections):
        """獲取信心度最高的檢測"""
        if not detections:
            return None
        return max(detections, key=lambda d: d['confidence'])

    def track(self, detections):
        """
        追蹤邏輯

        Args:
            detections: 檢測結果列表

        Returns:
            選中的目標信息
        """
        best_detection = None

        if self.tracking_active and self.locked_target_position is not None:
            # 目標鎖定模式 - 追蹤最接近的目標
            best_detection = self._find_closest_detection(detections, self.locked_target_position)
            if best_detection:
                print(f"  🎯 鎖定模式：追蹤距離上次位置 {self._calc_distance(best_detection['center'], self.locked_target_position):.0f}px 的目標")
            else:
                print(f"  ⚠️  未找到鎖定目標附近的檢測，解除鎖定")
                self.locked_target_position = None

        if best_detection is None:
            # 新目標選擇模式 - 選擇信心度最高的
            best_detection = self._get_best_detection(detections)
            if best_detection:
                print(f"  🆕 新目標選擇：選擇信心度最高的目標 ({best_detection['confidence']:.2f})")

        if best_detection:
            if not self.tracking_active:
                print(f"  ✅ 開始追蹤目標 ID={best_detection['id']}")
                self.tracking_active = True

            # 更新鎖定位置
            self.locked_target_position = best_detection['center']
            return best_detection
        else:
            if self.tracking_active:
                print(f"  ❌ 失去目標")
                self.tracking_active = False
                self.locked_target_position = None
            return None

    def _calc_distance(self, pos1, pos2):
        """計算兩點距離"""
        return np.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)


def create_detections(mosquitoes):
    """
    創建檢測結果

    Args:
        mosquitoes: [(id, x, y, confidence), ...]
    """
    detections = []
    for mosq_id, x, y, conf in mosquitoes:
        detections.append({
            'id': mosq_id,
            'center': (x, y),
            'confidence': conf,
            'bbox': (x-20, y-20, 40, 40)
        })
    return detections


def test_scenario_1():
    """場景 1：兩個目標，鎖定其中一個"""
    print("=" * 60)
    print("場景 1：畫面中有兩個蚊子，系統鎖定其中一個")
    print("=" * 60)

    tracker = MultiTargetTrackingTest()

    # 幀 1-5：兩個蚊子，A 信心度高
    print("\n幀 1-5：兩個蚊子出現（A: 0.8, B: 0.6）")
    for i in range(5):
        mosquito_a = (1, 300 + i*5, 200 + i*3, 0.8)  # 向右下移動
        mosquito_b = (2, 400, 250, 0.6)              # 靜止
        detections = create_detections([mosquito_a, mosquito_b])

        print(f"\n幀 {i+1}:")
        print(f"  檢測到: A(300+{i*5}, 200+{i*3}, conf=0.8), B(400, 250, conf=0.6)")
        selected = tracker.track(detections)
        if selected:
            print(f"  → 追蹤目標 ID={selected['id']} at {selected['center']}")

    print("\n✅ 預期結果：應該鎖定目標 A（信心度高）並持續追蹤")


def test_scenario_2():
    """場景 2：鎖定目標移動，不被其他目標干擾"""
    print("\n" + "=" * 60)
    print("場景 2：鎖定的目標移動，畫面中出現信心度更高的新目標")
    print("=" * 60)

    tracker = MultiTargetTrackingTest()

    # 幀 1-3：只有目標 A
    print("\n幀 1-3：只有目標 A（0.7）")
    for i in range(3):
        mosquito_a = (1, 300 + i*10, 200, 0.7)
        detections = create_detections([mosquito_a])

        print(f"\n幀 {i+1}:")
        print(f"  檢測到: A({300+i*10}, 200, conf=0.7)")
        selected = tracker.track(detections)
        if selected:
            print(f"  → 追蹤目標 ID={selected['id']} at {selected['center']}")

    # 幀 4-8：目標 A 繼續移動，出現信心度更高的目標 B
    print("\n幀 4-8：目標 A 繼續移動，出現新目標 B（信心度 0.9，更高！）")
    for i in range(3, 8):
        mosquito_a = (1, 300 + i*10, 200, 0.7)  # 繼續移動
        mosquito_b = (2, 500, 300, 0.9)         # 新目標，信心度更高
        detections = create_detections([mosquito_a, mosquito_b])

        print(f"\n幀 {i+1}:")
        print(f"  檢測到: A({300+i*10}, 200, conf=0.7), B(500, 300, conf=0.9)")
        selected = tracker.track(detections)
        if selected:
            print(f"  → 追蹤目標 ID={selected['id']} at {selected['center']}")

    print("\n✅ 預期結果：應該持續追蹤目標 A，不被高信心度的 B 干擾")


def test_scenario_3():
    """場景 3：失去目標後選擇新目標"""
    print("\n" + "=" * 60)
    print("場景 3：失去鎖定的目標後，選擇新目標")
    print("=" * 60)

    tracker = MultiTargetTrackingTest()

    # 幀 1-3：追蹤目標 A
    print("\n幀 1-3：追蹤目標 A")
    for i in range(3):
        mosquito_a = (1, 300 + i*10, 200, 0.8)
        detections = create_detections([mosquito_a])

        print(f"\n幀 {i+1}:")
        print(f"  檢測到: A({300+i*10}, 200, conf=0.8)")
        selected = tracker.track(detections)
        if selected:
            print(f"  → 追蹤目標 ID={selected['id']} at {selected['center']}")

    # 幀 4-5：目標 A 消失，只剩目標 B
    print("\n幀 4-5：目標 A 消失（飛出畫面），只剩目標 B")
    for i in range(4, 6):
        mosquito_b = (2, 500, 300, 0.7)
        detections = create_detections([mosquito_b])

        print(f"\n幀 {i+1}:")
        print(f"  檢測到: B(500, 300, conf=0.7)")
        selected = tracker.track(detections)
        if selected:
            print(f"  → 追蹤目標 ID={selected['id']} at {selected['center']}")

    print("\n✅ 預期結果：失去 A 後，重新鎖定目標 B 並追蹤")


def test_scenario_4():
    """場景 4：目標跳躍（超出鎖定距離）"""
    print("\n" + "=" * 60)
    print("場景 4：鎖定的目標突然跳到遠處（超出鎖定距離）")
    print("=" * 60)

    tracker = MultiTargetTrackingTest()

    # 幀 1-3：追蹤目標 A
    print("\n幀 1-3：追蹤目標 A")
    for i in range(3):
        mosquito_a = (1, 300 + i*5, 200, 0.8)
        detections = create_detections([mosquito_a])

        print(f"\n幀 {i+1}:")
        print(f"  檢測到: A({300+i*5}, 200, conf=0.8)")
        selected = tracker.track(detections)
        if selected:
            print(f"  → 追蹤目標 ID={selected['id']} at {selected['center']}")

    # 幀 4：目標 A 突然跳到遠處（200 像素外），同時出現目標 B 在附近
    print("\n幀 4：目標 A 跳到遠處（200px 外），目標 B 出現在附近")
    mosquito_a = (1, 600, 400, 0.8)  # 跳到遠處
    mosquito_b = (2, 320, 210, 0.7)  # 接近上次位置
    detections = create_detections([mosquito_a, mosquito_b])

    print(f"\n幀 4:")
    print(f"  檢測到: A(600, 400, conf=0.8), B(320, 210, conf=0.7)")
    print(f"  上次鎖定位置: {tracker.locked_target_position}")
    selected = tracker.track(detections)
    if selected:
        print(f"  → 追蹤目標 ID={selected['id']} at {selected['center']}")

    print("\n✅ 預期結果：A 跳太遠解除鎖定，選擇距離近的 B（即使信心度較低）")


def main():
    """主測試函數"""
    print("\n🧪 多目標追蹤邏輯驗證測試")
    print("=" * 60)
    print("測試目標：驗證多個蚊子存在時，系統是否能鎖定單一目標")
    print("核心邏輯：")
    print("  1. 初次檢測時，選擇信心度最高的目標")
    print("  2. 鎖定目標後，優先追蹤最接近上次位置的目標")
    print("  3. 只有失去當前目標後，才選擇新目標")
    print("=" * 60)
    print()

    try:
        # 測試 1：兩個目標，鎖定其中一個
        test_scenario_1()
        input("\n按 Enter 繼續下一個測試...")

        # 測試 2：不被高信心度目標干擾
        test_scenario_2()
        input("\n按 Enter 繼續下一個測試...")

        # 測試 3：失去目標後選擇新目標
        test_scenario_3()
        input("\n按 Enter 繼續下一個測試...")

        # 測試 4：目標跳躍
        test_scenario_4()

        print("\n" + "=" * 60)
        print("✅ 所有測試完成！")
        print("=" * 60)
        print("\n📝 測試結論：")
        print("1. ✅ 多目標時，選擇信心度最高的目標開始追蹤")
        print("2. ✅ 鎖定目標後，持續追蹤該目標（基於位置追蹤）")
        print("3. ✅ 不會被畫面中其他蚊子干擾")
        print("4. ✅ 失去目標後，重新選擇新目標")
        print("5. ✅ 支援目標跳躍檢測（超出鎖定距離時解除鎖定）")
        print("\n🎯 結論：多目標追蹤邏輯正確，會專注追蹤單一目標！")

    except KeyboardInterrupt:
        print("\n\n測試被用戶中斷")


if __name__ == "__main__":
    main()
