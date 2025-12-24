"""
增強版 PT2D 控制器 - 處理啟動時的非 JSON 訊息
"""

import serial
import json
import time
from typing import Dict, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PT2DController:
    """Arduino 2D 雲台控制器類（增強版）"""

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

            # 清空緩衝區並讀取啟動訊息
            self._read_startup_messages()
            
            self.is_connected = True

        except Exception as e:
            logger.error(f"無法連接至 {port}: {e}")
            self.is_connected = False

    def _read_startup_messages(self, max_lines: int = 20, timeout: float = 3.0):
        """
        讀取 Arduino 啟動時的訊息（可能是純文字或 JSON）
        
        Args:
            max_lines: 最多讀取的行數
            timeout: 總超時時間（秒）
        """
        start_time = time.time()
        lines_read = 0
        
        logger.info("讀取啟動訊息...")
        
        while lines_read < max_lines and (time.time() - start_time) < timeout:
            try:
                if self.ser.in_waiting > 0:
                    line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        lines_read += 1
                        logger.info(f"啟動訊息 #{lines_read}: {line}")
                        
                        # 嘗試解析 JSON
                        try:
                            data = json.loads(line)
                            if 'pan_id' in data and 'tilt_id' in data:
                                logger.info(f"偵測到舵機 ID: Pan={data['pan_id']}, Tilt={data['tilt_id']}")
                                return data
                        except json.JSONDecodeError:
                            # 非 JSON 格式，繼續讀取
                            pass
                else:
                    time.sleep(0.1)
            except Exception as e:
                logger.warning(f"讀取啟動訊息時發生錯誤: {e}")
                break
        
        logger.info("啟動訊息讀取完畢")
        # 清空剩餘緩衝區
        self.ser.flushInput()
        self.ser.flushOutput()
        return None

    def send_command(self, cmd: str, retry: int = 3) -> Dict:
        """
        發送命令並獲取響應（帶重試機制）

        Args:
            cmd: 命令字符串（不含 < > 符號）
            retry: 重試次數

        Returns:
            JSON 格式的響應字典
        """
        if not self.is_connected:
            return {'error': 'Not connected'}

        for attempt in range(retry):
            try:
                # 格式化命令
                if not cmd.startswith('<'):
                    cmd = f'<{cmd}>'
                if not cmd.endswith('\n'):
                    cmd += '\n'

                # 清空接收緩衝區
                self.ser.flushInput()

                # 發送命令
                self.ser.write(cmd.encode())
                time.sleep(0.05)  # 短暫等待

                # 讀取響應（可能需要多次讀取）
                response = self._read_response()

                # 解析 JSON
                try:
                    return json.loads(response)
                except json.JSONDecodeError:
                    logger.warning(f"嘗試 {attempt + 1}/{retry}: 無法解析 JSON: {response}")
                    if attempt == retry - 1:
                        return {'raw': response, 'error': 'Failed to parse JSON'}
                    time.sleep(0.1)

            except Exception as e:
                logger.error(f"發送命令失敗 (嘗試 {attempt + 1}/{retry}): {e}")
                if attempt == retry - 1:
                    return {'error': str(e)}
                time.sleep(0.1)

        return {'error': 'Max retries exceeded'}

    def _read_response(self, timeout: float = 1.0) -> str:
        """
        讀取一行響應，跳過非 JSON 格式的調試訊息
        
        Args:
            timeout: 超時時間
            
        Returns:
            響應字符串
        """
        start_time = time.time()
        
        while (time.time() - start_time) < timeout:
            if self.ser.in_waiting > 0:
                line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    # 嘗試解析 JSON
                    try:
                        json.loads(line)
                        return line  # 成功解析，返回
                    except json.JSONDecodeError:
                        # 非 JSON 格式，記錄並繼續讀取
                        logger.debug(f"跳過非 JSON 訊息: {line}")
                        continue
            time.sleep(0.01)
        
        return ""

    def send_bus_command(self, raw: str) -> Dict:
        """
        直接發送總線指令（#...!）並回讀原始回覆。

        Args:
            raw: 例如 '#001P1500T1000!'

        Returns:
            {'raw': <回覆字串>} 或錯誤字典
        """
        if not self.is_connected:
            return {'error': 'Not connected'}

        try:
            line = raw
            if not line.endswith('\n'):
                line += '\n'
            # 橋接固件支援直接透傳以 # 開頭的行
            self.ser.write(line.encode())
            time.sleep(0.05)
            response = self.ser.readline().decode().strip()
            return {'raw': response}
        except Exception as e:
            logger.error(f"發送總線指令失敗: {e}")
            return {'error': str(e)}

    def move_to(self, pan: int, tilt: int) -> Dict:
        """移動到絕對位置"""
        return self.send_command(f'MOVE:{pan},{tilt}')

    def move_by(self, pan_delta: int, tilt_delta: int) -> Dict:
        """相對移動"""
        return self.send_command(f'MOVER:{pan_delta},{tilt_delta}')

    def get_position(self) -> Tuple[Optional[int], Optional[int]]:
        """獲取當前位置"""
        response = self.send_command('POS')
        if 'pan' in response and 'tilt' in response:
            return response['pan'], response['tilt']
        return None, None

    def read_position(self) -> Tuple[Optional[int], Optional[int]]:
        """讀取舵機實際位置"""
        response = self.send_command('READ')
        if 'pan' in response and 'tilt' in response:
            return response['pan'], response['tilt']
        return None, None

    def get_status(self) -> Dict:
        """獲取完整狀態（位置+電壓+溫度）"""
        return self.send_command('STATUS')

    def set_speed(self, speed: int) -> Dict:
        """設置移動速度 (1-100)"""
        speed = max(1, min(100, speed))
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

    def close(self):
        """關閉串口連接"""
        if self.ser and self.ser.is_open:
            self.ser.close()
            logger.info("串口已關閉")


# 使用範例
if __name__ == "__main__":
    # 連接到控制器
    controller = PT2DController('/dev/ttyUSB0')  # Linux
    # controller = PT2DController('COM3')  # Windows

    if controller.is_connected:
        # 設置速度
        controller.set_speed(50)

        # 移動到指定位置
        controller.move_to(135, 90)
        time.sleep(2)

        # 讀取當前位置
        pan, tilt = controller.get_position()
        print(f"當前位置: Pan={pan}, Tilt={tilt}")

        # 獲取完整狀態
        status = controller.get_status()
        print(f"狀態: {status}")

        # 回到初始位置
        controller.home()

        controller.close()
