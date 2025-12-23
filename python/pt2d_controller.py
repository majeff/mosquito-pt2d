"""
Arduino PT2D 控制器 Python 介面
透過串口與 Arduino 通訊，控制 2D 雲台
"""

import serial
import json
import time
from typing import Dict, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PT2DController:
    """Arduino 2D 雲台控制器類"""

    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 1.0):
        """
        初始化控制器

        Args:
            port: 串口號 (Windows: 'COM3', Linux: '/dev/ttyUSB0')
            baudrate: 波特率，默認 115200
            timeout: 超時時間，默認 1.0 秒
        """
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.is_connected = False

        try:
            self.ser = serial.Serial(port, baudrate, timeout=timeout)
            time.sleep(2)  # 等待 Arduino 初始化
            logger.info(f"已連接至 {port}，波特率 {baudrate}")

            # 清空緩衝區
            self.ser.flushInput()
            self.ser.flushOutput()
            self.is_connected = True

        except Exception as e:
            logger.error(f"無法連接至 {port}: {e}")
            self.is_connected = False

    def send_command(self, cmd: str) -> Dict:
        """
        發送命令並獲取響應

        Args:
            cmd: 命令字符串（不含 < > 符號）

        Returns:
            JSON 格式的響應字典
        """
        if not self.is_connected:
            return {'error': 'Not connected'}

        try:
            # 格式化命令
            if not cmd.startswith('<'):
                cmd = f'<{cmd}>'
            if not cmd.endswith('\n'):
                cmd += '\n'

            # 發送命令
            self.ser.write(cmd.encode())
            time.sleep(0.05)  # 短暫等待

            # 讀取響應
            response = self.ser.readline().decode().strip()

            # 解析 JSON
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                return {'raw': response, 'error': 'Failed to parse JSON'}

        except Exception as e:
            logger.error(f"發送命令失敗: {e}")
            return {'error': str(e)}

    def move_to(self, pan: int, tilt: int) -> Dict:
        """
        移動到絕對位置

        Args:
            pan: Pan 軸角度 (0-270)
            tilt: Tilt 軸角度 (0-180)

        Returns:
            響應字典
        """
        return self.send_command(f'MOVE:{pan},{tilt}')

    def move_by(self, pan_delta: int, tilt_delta: int) -> Dict:
        """
        相對移動

        Args:
            pan_delta: Pan 軸相對角度
            tilt_delta: Tilt 軸相對角度

        Returns:
            響應字典
        """
        return self.send_command(f'MOVER:{pan_delta},{tilt_delta}')

    def get_position(self) -> Tuple[Optional[int], Optional[int]]:
        """
        獲取當前位置

        Returns:
            (pan, tilt) 元組，失敗返回 (None, None)
        """
        response = self.send_command('POS')
        if 'pan' in response and 'tilt' in response:
            return response['pan'], response['tilt']
        return None, None

    def set_speed(self, speed: int) -> Dict:
        """
        設置移動速度

        Args:
            speed: 速度值 (1-100)

        Returns:
            響應字典
        """
        speed = max(1, min(100, speed))  # 限制範圍
        return self.send_command(f'SPEED:{speed}')

    def home(self) -> Dict:
        """回到初始位置"""
        return self.send_command('HOME')

    def stop(self) -> Dict:
        """停止移動"""
        return self.send_command('STOP')

    def calibrate(self) -> Dict:
        """執行校準"""
        return self.send_command('CAL')

    # 提示：韌體已移除掃描模式，以下模式相關命令不再提供

    def wait_until_reached(self, target_pan: int, target_tilt: int,
                           tolerance: int = 2, timeout: float = 10.0) -> bool:
        """
        等待移動到目標位置

        Args:
            target_pan: 目標 Pan 角度
            target_tilt: 目標 Tilt 角度
            tolerance: 允許誤差，默認 2 度
            timeout: 超時時間，默認 10 秒

        Returns:
            是否成功到達
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            pan, tilt = self.get_position()
            if pan is not None and tilt is not None:
                if abs(pan - target_pan) <= tolerance and abs(tilt - target_tilt) <= tolerance:
                    return True
            time.sleep(0.1)
        return False

    def close(self):
        """關閉串口連接"""
        if self.ser is not None and self.ser.is_open:
            self.ser.close()
            self.is_connected = False
            logger.info("連接已關閉")

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()


def test_controller():
    """測試控制器基本功能"""
    print("=== 測試 Arduino PT2D 控制器 ===")

    # 請根據實際串口修改
    port = 'COM3'  # Windows
    # 對於 Orange Pi 5 使用 GPIO UART：
    # 常見為 /dev/ttyS1 或 /dev/ttyS3，請用 dmesg/ls 確認
    # port = '/dev/ttyS1'   # Linux (Orange Pi 5 GPIO UART)

    with PT2DController(port) as pt:
        if not pt.is_connected:
            print(f"無法連接至 {port}")
            return

        print("\n1. 移動到中心位置")
        print(pt.move_to(135, 90))
        time.sleep(2)

        print("\n2. 獲取當前位置")
        pan, tilt = pt.get_position()
        print(f"當前位置: Pan={pan}°, Tilt={tilt}°")

        print("\n3. 設置速度為 60")
        print(pt.set_speed(60))

        print("\n4. 相對移動 (+45°, +20°)")
        print(pt.move_by(45, 20))
        time.sleep(2)

        print("\n5. 回到初始位置")
        print(pt.home())

    print("\n測試完成")


if __name__ == "__main__":
    test_controller()
