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

"""
舵機硬件 ID 配置工具

用途：通過 Arduino 配置舵機硬件 ID
- 通過 Arduino 的 <CONFIGSERVO:id> 命令設置舵機硬件 ID
- Arduino 會轉發廣播命令 #255PIDXXX! 到舵機總線
- 這是一次性配置，設置後需要重啟 Arduino

使用方式：
  python configure_servo_id.py <端口> <舵機ID>

例：
  python configure_servo_id.py COM3 1        # 配置舵機硬件 ID 為 1（水平 Pan）
  python configure_servo_id.py COM3 2        # 配置舵機硬件 ID 為 2（垂直 Tilt）
  python configure_servo_id.py /dev/ttyUSB0 1
"""

import sys
import time
import traceback
import serial
import json

def send_servo_id_config(port: str, servo_id: int) -> bool:
    """
    通過 Arduino 配置舵機硬件 ID

    Args:
        port: 串口號（如 'COM3', '/dev/ttyUSB0'）
        servo_id: 目標舵機硬件 ID（1-254）

    Returns:
        True 如果配置成功，False 如果失敗
    """
    if not (1 <= servo_id <= 254):
        print(f"❌ 舵機 ID 必須在 1-254 之間，收到: {servo_id}")
        return False

    try:
        # 連接到 Arduino
        print(f"正在連接到 {port}...")
        ser = serial.Serial(port, 115200, timeout=2)
        time.sleep(1)  # 等待初始化

        print(f"✅ 已連接")

        # 清空緩衝區
        ser.reset_input_buffer()
        ser.reset_output_buffer()

        # 生成配置命令：<CONFIGSERVO:xxx>
        # Arduino 會轉發為 #255PIDXXX! 到舵機總線
        command = f"<CONFIGSERVO:{servo_id}>\n"

        print(f"\n準備發送舵機硬件 ID 配置命令...")
        print(f"  目標舵機硬件 ID: {servo_id}")
        print(f"  Arduino 命令: {command.strip()}")

        # 發送命令到 Arduino
        print(f"\n發送命令到 Arduino...")
        ser.write(command.encode())
        ser.flush()

        print(f"✅ 命令已發送")

        # 等待響應
        print(f"\n等待 Arduino 確認...")
        time.sleep(1)

        # 讀取響應
        responses = []
        start_time = time.time()

        while time.time() - start_time < 2:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    responses.append(line)
                    print(f"  收到: {line}")

        ser.close()

        # 分析響應
        if responses:
            print(f"\n✅ Arduino 響應已收到")

            # 檢查是否有成功消息
            success = any('成功' in r or 'ok' in r.lower() for r in responses)

            if success:
                print(f"\n✅ 舵機硬件 ID 配置命令已發送！")
                print(f"   目標舵機硬件 ID: {servo_id}")
                print(f"   需要重啟 Arduino 以使配置生效")
                return True
            else:
                print(f"\n⚠️  Arduino 已收到命令，請檢查舵機連接")
                print(f"   需要重啟 Arduino 確認配置")
                return True
        else:
            print(f"\n⚠️  未收到 Arduino 響應")
            print(f"   但命令已發送，請重啟 Arduino")
            return True

    except serial.SerialException as e:
        print(f"\n❌ 串口連接失敗: {e}")
        print(f"   請檢查：")
        print(f"   1. 串口號是否正確")
        print(f"   2. Arduino 是否已連接")
        print(f"   3. 是否有其他程序佔用串口")
        return False
    except Exception as e:
        print(f"\n❌ 發生錯誤: {e}")
        traceback.print_exc()
        return False

def main():
    """主函數"""
    if len(sys.argv) < 3:
        print("舵機硬件 ID 配置工具")
        print("=" * 60)
        print("\n用途：通過 Arduino 配置舵機硬件 ID")
        print("    Arduino 會轉發廣播命令 #255PIDXXX! 到舵機總線")
        print("\n使用方式：")
        print("  python configure_servo_id.py <端口> <舵機ID>")
        print("\n例：")
        print("  python configure_servo_id.py COM3 1        # 配置舵機硬件 ID 為 1（水平 Pan）")
        print("  python configure_servo_id.py COM3 2        # 配置舵機硬件 ID 為 2（垂直 Tilt）")
        print("  python configure_servo_id.py /dev/ttyUSB0 1")
        print("\n注意：")
        print("  - 舵機硬件 ID 範圍：1-254")
        print("  - 建議 Pan 舵機設置 ID 1，Tilt 舵機設置 ID 2")
        print("  - 配置後需要重啟 Arduino 使配置生效")
        print("=" * 60)
        return

    port = sys.argv[1]
    try:
        servo_id = int(sys.argv[2])
    except ValueError:
        print(f"❌ 舵機 ID 必須是整數，收到: {sys.argv[2]}")
        return

    print("\n" + "=" * 60)
    print("舵機硬件 ID 配置工具")
    print("=" * 60)

    success = send_servo_id_config(port, servo_id)

    if success:
        print("\n" + "=" * 60)
        print("配置已發送！")
        print("=" * 60)
        print("\n後續步驟：")
        print("  1. 重啟 Arduino")
        print("  2. 使用 GETINFO 命令查詢舵機 ID 確認")
        print("     python test_serial_protocol.py <端口>")
    else:
        print("\n配置失敗，請檢查設置後重試")

if __name__ == "__main__":
    main()
