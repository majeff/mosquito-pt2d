"""
快速啟動範例 - 蚊子追蹤系統
"""

from mosquito_tracker import MosquitoTracker
import sys

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
    print("按下任意鍵開始...")
    input()

    # 建立並運行追蹤系統
    tracker = MosquitoTracker(
        arduino_port=ARDUINO_PORT,
        camera_left_id=0,
        camera_right_id=1,
        camera_width=640,
        camera_height=480
    )

    print("\n正在啟動系統...")
    tracker.run()


if __name__ == "__main__":
    main()
