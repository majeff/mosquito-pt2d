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
Arduino PT2D 控制器 Python 介面
透過串口與 Arduino 通訊，控制 2D 雲台
"""

from config import ARDUINO_BAUDRATE, ARDUINO_TIMEOUT
import serial
import json
import time
from typing import Dict, Optional, Tuple, Union
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PT2DController:
    """Arduino 2D 雲台控制器類"""

    def __init__(self, port: str, baudrate: int = ARDUINO_BAUDRATE, timeout: float = ARDUINO_TIMEOUT):
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
        self.servo_enabled = False  # 初始為禁用，只有在成功初始化後才啟用

        # 角度限制（初始值，會由 Arduino 動態設置）
        self.pan_min = 0
        self.pan_max = 270
        self.tilt_min = 15
        self.tilt_max = 165

        try:
            self.ser = serial.Serial(port, baudrate, timeout=timeout)
            time.sleep(2)  # 等待 Arduino 初始化
            logger.info(f"已連接至 {port}，波特率 {baudrate}")

            # 讀取並清空啟動訊息
            self._clear_startup_messages()

            # 檢查舵機控制是否啟用
            if not self.servo_enabled:
                logger.error("舵機控制已禁用，無法建立連接")
                self.is_connected = False
            else:
                self.is_connected = True

        except Exception as e:
            logger.error(f"無法連接至 {port}: {e}")
            if self.ser is not None and self.ser.is_open:
                self.ser.close()
            self.is_connected = False

    def _clear_startup_messages(self, timeout: float = 3.0):
        """
        清空啟動時的訊息，並從 Arduino 解析角度限制及舵機控制狀態

        Args:
            timeout: 總超時時間（秒）
        """
        start_time = time.time()
        logger.info("讀取啟動訊息...")

        while (time.time() - start_time) < timeout:
            try:
                if self.ser.in_waiting > 0:
                    line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        logger.debug(f"啟動訊息: {line}")
                        # 嘗試解析 JSON，記錄舵機 ID 和角度限制
                        try:
                            data = json.loads(line)

                            # 檢查舵機控制是否失敗（error 狀態且 ID 為 0）
                            if data.get('status') == 'error' and 'pan_id' in data:
                                pan_id = data.get('pan_id', 0)
                                tilt_id = data.get('tilt_id', 0)
                                if pan_id == 0 or tilt_id == 0:
                                    logger.error(f"舵機設置失敗: Pan ID={pan_id}, Tilt ID={tilt_id}")
                                    self.servo_enabled = False
                                    # 繼續讀取剩餘訊息，不要直接 break

                            if 'pan_id' in data and 'tilt_id' in data:
                                pan_id = data.get('pan_id', 0)
                                tilt_id = data.get('tilt_id', 0)
                                if pan_id > 0 and tilt_id > 0:
                                    logger.info(f"偵測到舵機 ID: Pan={pan_id}, Tilt={tilt_id}")

                            # 解析角度限制
                            if 'pan_min' in data:
                                self.pan_min = data['pan_min']
                            if 'pan_max' in data:
                                self.pan_max = data['pan_max']
                            if 'tilt_min' in data:
                                self.tilt_min = data['tilt_min']
                            if 'tilt_max' in data:
                                self.tilt_max = data['tilt_max']

                            # 若收到所有限制值，記錄並標記舵機已啟用
                            if all(k in data for k in ['pan_min', 'pan_max', 'tilt_min', 'tilt_max']):
                                if data.get('status') == 'ok':  # 只在狀態為 ok 時啟用
                                    logger.info(f"角度限制已設置: Pan=[{self.pan_min}°-{self.pan_max}°], "
                                              f"Tilt=[{self.tilt_min}°-{self.tilt_max}°]")
                                    self.servo_enabled = True
                        except json.JSONDecodeError:
                            pass
                else:
                    time.sleep(0.05)
            except Exception as e:
                logger.warning(f"讀取啟動訊息時發生錯誤: {e}")
                break

        # 清空剩餘緩衝區
        try:
            self.ser.flushInput()
            self.ser.flushOutput()
        except Exception as e:
            logger.warning(f"清理緩衝區失敗: {e}")

        logger.info("啟動訊息處理完畢")

    def _read_json_response(self, timeout: float = 1.0) -> str:
        """
        讀取一行 JSON 響應，自動跳過非 JSON 格式的調試訊息

        Args:
            timeout: 超時時間（秒）

        Returns:
            JSON 格式的響應字符串
        """
        start_time = time.time()

        while (time.time() - start_time) < timeout:
            if self.ser.in_waiting > 0:
                line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    # 嘗試解析 JSON
                    try:
                        json.loads(line)  # 驗證是否為有效 JSON
                        return line
                    except json.JSONDecodeError:
                        # 非 JSON 格式，記錄並繼續讀取下一行
                        logger.debug(f"跳過非 JSON 訊息: {line}")
                        continue
            time.sleep(0.01)

        return ""

    def send_command(self, cmd: str, retry: int = 1) -> Dict:
        """
        發送命令並獲取響應（支援重試機制）

        Args:
            cmd: 命令字符串（不含 < > 符號）
            retry: 重試次數（預設 1 次，即不重試）

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

                # 清空接收緩衝區（避免讀取舊數據）
                self.ser.flushInput()

                # 發送命令
                self.ser.write(cmd.encode())
                time.sleep(0.05)  # 短暫等待

                # 讀取響應（自動過濾非 JSON）
                response = self._read_json_response()

                if response:
                    # 解析 JSON
                    try:
                        return json.loads(response)
                    except json.JSONDecodeError:
                        logger.warning(f"嘗試 {attempt + 1}/{retry}: 無法解析 JSON: {response}")
                        if attempt == retry - 1:
                            return {'raw': response, 'error': 'Failed to parse JSON'}
                else:
                    logger.warning(f"嘗試 {attempt + 1}/{retry}: 未收到響應")
                    if attempt == retry - 1:
                        return {'error': 'No response received'}

                # 重試前等待
                if attempt < retry - 1:
                    time.sleep(0.1)

            except Exception as e:
                logger.error(f"發送命令失敗 (嘗試 {attempt + 1}/{retry}): {e}")
                if attempt == retry - 1:
                    return {'error': str(e)}
                time.sleep(0.1)

        return {'error': 'Max retries exceeded'}

    def send_bus_command(self, raw: str) -> Dict:
        """
        直接發送總線指令（#...!）並回讀原始回覆。

        用途：當固件以橋接模式運作時，可直接透過 Arduino 轉發到總線。

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
        """
        移動到絕對位置（上位機自動限制角度在 Arduino 指定的安全範圍內）

        Args:
            pan: Pan 軸角度 (超出範圍自動限制)
            tilt: Tilt 軸角度 (超出範圍自動限制)

        Returns:
            響應字典
        """
        if not self.servo_enabled:
            return {'error': 'Servo control is disabled due to initialization failure'}

        # 限制角度在 Arduino 指定的範圍內
        pan = max(self.pan_min, min(self.pan_max, pan))
        tilt = max(self.tilt_min, min(self.tilt_max, tilt))

        logger.debug(f"Move to: Pan={pan}° (限制範圍 {self.pan_min}-{self.pan_max}), "
                    f"Tilt={tilt}° (限制範圍 {self.tilt_min}-{self.tilt_max})")
        return self.send_command(f'MOVE:{pan},{tilt}')

    def move_by(self, pan_delta: int, tilt_delta: int) -> Dict:
        """
        相對移動（上位機自動限制最終角度在 Arduino 指定的安全範圍內）

        Args:
            pan_delta: Pan 軸相對角度
            tilt_delta: Tilt 軸相對角度

        Returns:
            響應字典
        """
        if not self.servo_enabled:
            return {'error': 'Servo control is disabled due to initialization failure'}

        # 獲取當前位置
        current_pan, current_tilt = self.get_position()

        if current_pan is None or current_tilt is None:
            logger.warning("無法獲取當前位置，無法執行相對移動")
            return {'error': 'Cannot get current position'}

        # 計算目標位置並限制在 Arduino 指定的範圍內
        target_pan = max(self.pan_min, min(self.pan_max, current_pan + pan_delta))
        target_tilt = max(self.tilt_min, min(self.tilt_max, current_tilt + tilt_delta))

        logger.debug(f"Relative move: from Pan={current_pan}° Tilt={current_tilt}° "
                    f"→ to Pan={target_pan}° Tilt={target_tilt}° "
                    f"(Pan限制 {self.pan_min}-{self.pan_max}, Tilt限制 {self.tilt_min}-{self.tilt_max})")

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

    def read_position(self) -> Tuple[Optional[int], Optional[int]]:
        """
        讀取舵機實際位置（READ 強制重新讀取）

        Returns:
            (pan, tilt) 元組，失敗返回 (None, None)
        """
        response = self.send_command('READ')
        if 'pan' in response and 'tilt' in response:
            return response['pan'], response['tilt']
        return None, None

    def read_temperature(self) -> Dict:
        """讀取雙軸溫度"""
        return self.send_command('TEMP')

    def read_voltage(self) -> Dict:
        """讀取雙軸電壓"""
        return self.send_command('VOLT')

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

    def config_servo_id(self, servo_id: int) -> Dict:
        """
        配置舵機硬件 ID（固件 <CONFIGSERVO:id>，透過廣播 #255PIDXXX!）

        注意：此命令需在單一舵機連接到總線時執行，以避免多機同時被改ID。

        Args:
            servo_id: 目標舵機硬件 ID（1-254）

        Returns:
            響應字典（含狀態與提示訊息）
        """
        if not (1 <= servo_id <= 254):
            return {'error': 'Servo ID must be between 1 and 254'}
        logger.info(f"配置舵機硬件 ID: {servo_id}")
        return self.send_command(f'CONFIGSERVO:{servo_id}')

    def get_info(self) -> Dict:
        """
        獲取 Arduino 系統信息（舵機ID、角度限制、固件版本等）

        Returns:
            包含以下字段的字典：
            - pan_id: Pan軸舵機ID
            - tilt_id: Tilt軸舵機ID
            - pan_min, pan_max: Pan軸角度範圍
            - tilt_min, tilt_max: Tilt軸角度範圍
            - firmware_version: 固件版本
        """
        logger.info("查詢 Arduino 系統信息...")
        result = self.send_command('GETINFO')

        # 如果查詢成功，更新本地配置
        if result.get('status') == 'ok':
            # 更新舵機ID
            if 'pan_id' in result:
                pan_id = result.get('pan_id', 0)
                tilt_id = result.get('tilt_id', 0)
                if pan_id > 0 and tilt_id > 0:
                    logger.info(f"當前舵機 ID: Pan={pan_id}, Tilt={tilt_id}")
                else:
                    logger.warning(f"舵機 ID 無效: Pan={pan_id}, Tilt={tilt_id}")

            # 更新角度限制
            if 'pan_min' in result:
                self.pan_min = result['pan_min']
                self.pan_max = result['pan_max']
                self.tilt_min = result['tilt_min']
                self.tilt_max = result['tilt_max']
                logger.info(f"角度限制: Pan=[{self.pan_min}-{self.pan_max}], "
                           f"Tilt=[{self.tilt_min}-{self.tilt_max}]")

            # 記錄固件版本
            if 'firmware_version' in result:
                logger.info(f"固件版本: {result['firmware_version']}")
        else:
            logger.error(f"查詢系統信息失敗: {result.get('message', 'Unknown error')}")

        return result

    def beep(self) -> Dict:
        """
        發送蜂鳴器信號（3聲短鳴）

        Returns:
            響應字典
        """
        logger.info("發送蜂鳴器信號...")
        return self.send_command('BEEP')

    def home(self) -> Dict:
        """回到初始位置"""
        return self.send_command('HOME')

    def stop(self) -> Dict:
        """停止移動"""
        return self.send_command('STOP')

    def set_led(self, state: Union[bool, str]) -> Dict:
        """
        設置 LED 狀態（固件 <LED:ON|OFF>）

        Args:
            state: True/'ON' 開啟，False/'OFF' 關閉
        """
        val = 'ON' if (isinstance(state, bool) and state or (isinstance(state, str) and state.upper() == 'ON')) else 'OFF'
        return self.send_command(f'LED:{val}')

    def set_laser(self, state: Union[bool, str]) -> Dict:
        """
        設置雷射狀態（固件 <LASER:ON|OFF>）

        Args:
            state: True/'ON' 開啟，False/'OFF' 關閉
        """
        val = 'ON' if (isinstance(state, bool) and state or (isinstance(state, str) and state.upper() == 'ON')) else 'OFF'
        return self.send_command(f'LASER:{val}')

    # 總線指令快捷方法（橋接模式）
    def bus_move(self, servo_id: int, position: int, time_ms: int) -> Dict:
        """以總線指令移動單一舵機：#ID Pxxxx Tyyyy!"""
        return self.send_bus_command(f"#{servo_id:03d}P{position:04d}T{time_ms:04d}!")

    def bus_stop(self, servo_id: int) -> Dict:
        return self.send_bus_command(f"#{servo_id:03d}PDST!")

    def bus_pause(self, servo_id: int) -> Dict:
        return self.send_bus_command(f"#{servo_id:03d}PDPT!")

    def bus_continue(self, servo_id: int) -> Dict:
        return self.send_bus_command(f"#{servo_id:03d}PDCT!")

    def bus_read_angle(self, servo_id: int) -> Dict:
        return self.send_bus_command(f"#{servo_id:03d}PRAD!")

    def bus_read_voltage_temp(self, servo_id: int) -> Dict:
        return self.send_bus_command(f"#{servo_id:03d}PRTV!")

    # 解析後 JSON（橋接固件命令）
    def read_angle(self, servo_id: int) -> Dict:
        """使用橋接固件的 <READANGLE:id> 取得角度 JSON"""
        return self.send_command(f"READANGLE:{servo_id}")

    def read_voltage_temp(self, servo_id: int) -> Dict:
        """使用橋接固件的 <READVOLTEMP:id> 取得電壓與溫度 JSON"""
        return self.send_command(f"READVOLTEMP:{servo_id}")

    def read_status(self) -> Dict:
        """讀取雙軸完整狀態（位置+電壓+溫度），對應固件 <STATUS>"""
        return self.send_command("STATUS")

    def swing_test(self) -> bool:
        """
        執行擺動測試：
        - 水平擺動：0° → 270° → 135°（中心），各2秒轉動
        - 垂直擺動：15° → 165° → 90°（中心），各2秒轉動

        Returns:
            是否成功完成測試
        """
        logger.info("開始擺動測試...")

        try:
            # 水平擺動測試
            logger.info("執行水平擺動測試")

            # 移動到 0°
            logger.info("移動到 Pan=0°")
            self.move_to(0, 90)
            time.sleep(2.5)

            # 移動到 270°
            logger.info("移動到 Pan=270°")
            self.move_to(270, 90)
            time.sleep(2.5)

            # 回到 135°（中心）
            logger.info("回到 Pan=135°（中心）")
            self.move_to(135, 90)
            time.sleep(2.5)

            # 垂直擺動測試
            logger.info("執行垂直擺動測試")

            # 移動到 15°
            logger.info("移動到 Tilt=15°")
            self.move_to(135, 15)
            time.sleep(2.5)

            # 移動到 165°
            logger.info("移動到 Tilt=165°")
            self.move_to(135, 165)
            time.sleep(2.5)

            # 回到初始位置（90°）
            logger.info("回到初始位置 Tilt=90°")
            self.move_to(135, 90)
            time.sleep(2.5)

            logger.info("擺動測試完成")
            return True

        except Exception as e:
            logger.error(f"擺動測試失敗: {e}")
            return False



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
    logger.info("=== 測試 Arduino PT2D 控制器 ===")

    # 請根據實際串口修改
    port = 'COM3'  # Windows
    # 對於 Orange Pi 5 使用 GPIO UART：
    # 常見為 /dev/ttyS1 或 /dev/ttyS3，請用 dmesg/ls 確認
    # port = '/dev/ttyS1'   # Linux (Orange Pi 5 GPIO UART)

    with PT2DController(port) as pt:
        if not pt.is_connected:
            logger.error(f"無法連接至 {port}")
            return

        logger.info("\n1. 移動到中心位置")
        logger.info(pt.move_to(135, 90))
        time.sleep(2)

        logger.info("\n2. 獲取當前位置")
        pan, tilt = pt.get_position()
        logger.info(f"當前位置: Pan={pan}°, Tilt={tilt}°")

        logger.info("\n3. 設置速度為 60")
        logger.info(pt.set_speed(60))

        logger.info("\n4. 相對移動 (+45°, +20°)")
        logger.info(pt.move_by(45, 20))
        time.sleep(2)

        logger.info("\n5. 執行擺動測試")
        if pt.swing_test():
            logger.info("✓ 擺動測試成功")
        else:
            logger.warning("✗ 擺動測試失敗")

        logger.info("\n6. 回到初始位置")
        logger.info(pt.home())

    logger.info("\n測試完成")


if __name__ == "__main__":
    test_controller()
