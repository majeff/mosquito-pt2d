"""
快速啟動範例 - 蚊子追蹤系統
"""

from mosquito_tracker import MosquitoTracker
from pt2d_controller import PT2DController
import sys
import time

def main():
    """主程式入口"""

    print("=" * 50)
    print("蚊子自動追蹤系統")
    print("=" * 50)
    print()
    print("請確認以下設置:")
    print("1. Arduino 已上傳韌體並連接至電腦")
    print("2. 攝像頭已正確連接")
    print("3. 舵機已正確供電")
    print()

    # 配置參數（根據實際情況修改）
    default_port = 'COM3' if sys.platform.startswith('win') else '/dev/ttyS1'
    prompt = f"請輸入 Arduino 串口號 (例如: {default_port}): "
    ARDUINO_PORT = input(prompt).strip() or default_port

    print(f"\n使用串口: {ARDUINO_PORT}")
    print("左攝像頭 ID: 0")
    print("右攝像頭 ID: 1")
    print()

    # 簡單測試：驗證 Arduino 連接與基本操作
    print("=" * 50)
    print("測試 Arduino 連接...")
    print("=" * 50)
    try:
        with PT2DController(ARDUINO_PORT) as pt:
            if not pt.is_connected:
                print(f"⚠ 無法連接至 {ARDUINO_PORT}，請檢查連線")
                return

            print("✓ Arduino 已連接")
            print()

            # 測試 1: 移動到初始位置
            print("[測試 1] 移動到初始位置 (135°, 90°)...")
            pt.move_to(135, 90)
            time.sleep(1.5)

            # 測試 2: 讀取位置
            print("[測試 2] 讀取當前位置...")
            pan, tilt = pt.get_position()
            print(f"  → Pan: {pan}°, Tilt: {tilt}°")

            # 測試 3: 讀取完整狀態（位置 + 溫度 + 電壓）
            print("[測試 3] 讀取完整系統狀態...")
            status = pt.read_status()
            print(f"  → {status}")

            # 測試 4: 相對移動
            print("[測試 4] 相對移動 (+30°, +15°)...")
            pt.move_by(30, 15)
            time.sleep(1.5)

            # 測試 5: 讀取新位置
            print("[測試 5] 再次讀取位置...")
            pan, tilt = pt.get_position()
            print(f"  → Pan: {pan}°, Tilt: {tilt}°")

            # 測試 6: 回到初始位置
            print("[測試 6] 回到初始位置...")
            pt.home()
            time.sleep(1.5)

            print()
            print("✓ 所有測試完成！系統運作正常")

    except Exception as e:
        print(f"⚠ 測試失敗: {e}")
        return

    print()
    print("按下任意鍵開始追蹤系統...")
    input()

    # 建立並運行追蹤系統
    tracker = MosquitoTracker(
        arduino_port=ARDUINO_PORT,
        camera_left_id=0,
        camera_right_id=1,
        camera_width=640,
        camera_height=480
    )

    print("\n正在啟動追蹤系統...")
    tracker.run()


if __name__ == "__main__":
    main()
