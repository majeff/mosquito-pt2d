# Python 控制示例

## 📦 環境準備

### 安裝依賴

```bash
pip install pyserial
```

---

## 🐍 基礎示例

### 1. 簡單控制

```python
import serial
import time

# 連接 Arduino
ser = serial.Serial('COM3', 115200, timeout=1)  # Windows: COM3, Linux: /dev/ttyUSB0
time.sleep(2)  # 等待 Arduino 重啟

# 發送命令
ser.write(b'<MOVE:90,45>\n')
time.sleep(0.1)

# 讀取響應
response = ser.readline().decode().strip()
print(response)  # {"status":"ok","message":"OK"}

# 關閉串口
ser.close()
```

---

## 🎯 進階示例

### 2. 類封裝版本

```python
"""
Arduino 2D 雲台控制器 Python 接口
"""

import serial
import json
import time
from typing import Dict, Optional, Tuple

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
        self.ser = serial.Serial(port, baudrate, timeout=timeout)
        time.sleep(2)  # 等待 Arduino 初始化
        print(f"Connected to {port} at {baudrate} baud")

        # 清空緩衝區
        self.ser.flushInput()
        self.ser.flushOutput()

    def send_command(self, cmd: str) -> Dict:
        """
        發送命令並獲取響應

        Args:
            cmd: 命令字符串（不含 < > 符號）

        Returns:
            JSON 格式的響應字典
        """
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

    def move_to(self, pan: int, tilt: int) -> Dict:
        """
        移動到絕對位置

        Args:
            pan: Pan 軸角度 (0-180)
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
        if self.ser.is_open:
            self.ser.close()
            print("Connection closed")

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()

# ==================== 使用示例 ====================

def example_basic():
    """基礎使用示例"""
    print("=== 基礎示例 ===")

    # 創建控制器（使用上下文管理器自動關閉）
    with PT2DController('COM3') as pt:
        # 移動到中心位置
        print(pt.move_to(135, 90))
        time.sleep(2)

        # 獲取當前位置
        pan, tilt = pt.get_position()
        print(f"Current position: Pan={pan}°, Tilt={tilt}°")

        # 設置速度
        pt.set_speed(50)

        # 移動到新位置
        print(pt.move_to(270, 180))
        time.sleep(3)

        # 回到初始位置
        print(pt.home())

def example_auto_scan():
    """自動掃描模式示例"""
    print("=== 自動掃描模式示例 ===")

    with PT2DController('COM3') as pt:
        # 查詢當前模式
        mode_info = pt.get_mode()
        print(f"Current mode: {mode_info}")

        # 切換到自動掃描模式
        print("Switching to auto scan mode...")
        print(pt.set_mode(1))
        time.sleep(1)

        # 觀察自動掃描（垂直固定20°，水平掃描75°-195°）
        print("Auto scanning for 30 seconds...")
        start_time = time.time()
        while time.time() - start_time < 30:
            pan, tilt = pt.get_position()
            print(f"Scanning... Pan={pan}°, Tilt={tilt}°")
            time.sleep(2)

        # 停止掃描
        print("Stopping scan...")
        pt.stop()
        time.sleep(1)

        # 切回手動模式
        print("Switching back to manual mode...")
        print(pt.set_mode(0))

        # 回到中心
        pt.home()

def example_smooth_tracking():
    """平滑追蹤示例"""
    print("=== 平滑追蹤示例 ===")

    with PT2DController('COM3') as pt:
        pt.set_speed(80)  # 設置較快速度

        # 模擬追蹤軌跡（圓形）
        import math
        radius = 40
        center_pan = 135  # Pan 中心：270/2
        center_tilt = 90  # Tilt 中心：180/2

        for angle in range(0, 360, 10):
            rad = math.radians(angle)
            pan = int(center_pan + radius * math.cos(rad))
            tilt = int(center_tilt + radius * math.sin(rad))

            pt.move_to(pan, tilt)
            print(f"Moving to: Pan={pan}°, Tilt={tilt}°")
            time.sleep(0.2)

        pt.home()

def example_scan_pattern():
    """掃描模式示例"""
    print("=== 掃描模式示例 ===")

    with PT2DController('COM3') as pt:
        pt.set_speed(60)

        # 水平掃描
        print("Horizontal scan...")
        for tilt in [45, 90, 135]:
            for pan in range(0, 271, 45):  # Pan: 0, 45, 90, 135, 180, 225, 270
                pt.move_to(pan, tilt)
                time.sleep(1)

        pt.home()

def example_interactive():
    """交互式控制示例"""
    print("=== 交互式控制 ===")
    print("Commands: w/s (tilt), a/d (pan), h (home), q (quit)")

    with PT2DController('COM3') as pt:
        step = 10

        while True:
            cmd = input("Command: ").lower()

            if cmd == 'w':
                pt.move_by(0, step)
            elif cmd == 's':
                pt.move_by(0, -step)
            elif cmd == 'a':
                pt.move_by(-step, 0)
            elif cmd == 'd':
                pt.move_by(step, 0)
            elif cmd == 'h':
                pt.home()
            elif cmd == 'q':
                break
            else:
                print("Invalid command")
                continue

            # 顯示當前位置
            pan, tilt = pt.get_position()
            print(f"Position: Pan={pan}°, Tilt={tilt}°")

def example_camera_tracking():
    """模擬相機追蹤示例（需結合 OpenCV）"""
    print("=== 相機追蹤模擬 ===")

    with PT2DController('COM3') as pt:
        pt.set_speed(70)
        pt.home()

        # 模擬目標位置（實際應從相機獲取）
        targets = [
            (45, 45), (225, 45), (225, 135), (45, 135),
            (135, 90)  # 回中心
        ]

        for target in targets:
            paauto_scan()        # 自動掃描模式
    # example_n, tilt = target
            print(f"Tracking target at Pan={pan}°, Tilt={tilt}°")
            pt.move_to(pan, tilt)

            # 等待到達
            if pt.wait_until_reached(pan, tilt):
                print("Target reached!")
            else:
                print("Failed to reach target")

            time.sleep(1)

def example_position_monitoring():
    """位置監控示例"""
    print("=== 位置監控 ===")

    with PT2DController('COM3') as pt:
        pt.set_speed(30)  # 慢速移動
        pt.move_to(270, 90)

        # 持續監控位置
        start_time = time.time()
        while time.time() - start_time < 5:
            pan, tilt = pt.get_position()
            if pan is not None:
                print(f"Time: {time.time()-start_time:.1f}s | Pan={pan}°, Tilt={tilt}°")
            time.sleep(0.2)

def example_servo_monitoring():
    """舵機狀態監控示例"""
    print("=== 舵機狀態監控 ===")

    with PT2DController('COM3') as pt:
        # 移動到不同位置並監控狀態
        positions = [(135, 90), (0, 90), (270, 90), (135, 0), (135, 180)]

        for target_pan, target_tilt in positions:
            print(f"\nMoving to ({target_pan}°, {target_tilt}°)...")
            pt.move_to(target_pan, target_tilt)
            time.sleep(2)
    # example_servo_monitoring() # 舵機狀態監控
    # example_health_check()     # 健康檢查

            # 讀取完整狀態
            status = pt.read_status()
            print(f"Position: Pan={status['pan']}°, Tilt={status['tilt']}°")
            print(f"Temperature: Pan={status['pan_temp']}°C, Tilt={status['tilt_temp']}°C")
            print(f"Voltage: Pan={status['pan_voltage']/1000:.2f}V, Tilt={status['tilt_voltage']/1000:.2f}V")

            # 檢查溫度警告
            if status['pan_temp'] > 60 or status['tilt_temp'] > 60:
                print("⚠️ WARNING: High temperature detected!")

            # 檢查電壓警告
            if status['pan_voltage'] < 6500 or status['tilt_voltage'] < 6500:
                print("⚠️ WARNING: Low voltage detected!")

        pt.home()

def example_health_check():
    """舵機健康檢查示例"""
    print("=== 舵機健康檢查 ===")

    with PT2DController('COM3') as pt:
        print("\n1. 檢查溫度...")
        temp = pt.read_temperature()
        print(f"   Pan 舵機溫度: {temp['pan_temp']}°C")
        print(f"   Tilt 舵機溫度: {temp['tilt_temp']}°C")

        if temp['pan_temp'] < 20 or temp['pan_temp'] > 70:
            print("   ⚠️ Pan 舵機溫度異常")
        if temp['tilt_temp'] < 20 or temp['tilt_temp'] > 70:
            print("   ⚠️ Tilt 舵機溫度異常")

        print("\n2. 檢查電壓...")
        volt = pt.read_voltage()
        print(f"   Pan 舵機電壓: {volt['pan_voltage']/1000:.2f}V")
        print(f"   Tilt 舵機電壓: {volt['tilt_voltage']/1000:.2f}V")

        if volt['pan_voltage'] < 6000 or volt['pan_voltage'] > 8500:
            print("   ⚠️ Pan 舵機電壓異常")
        if volt['tilt_voltage'] < 6000 or volt['tilt_voltage'] > 8500:
            print("   ⚠️ Tilt 舵機電壓異常")

        print("\n3. 檢查位置...")
        pan, tilt = pt.get_position()
        print(f"   當前位置: Pan={pan}°, Tilt={tilt}°")

        # 測試移動
        print("\n4. 測試移動...")
        pt.move_to(135, 90)
        time.sleep(2)
        pan, tilt = pt.get_position()
        if abs(pan - 135) > 5 or abs(tilt - 90) > 5:
            print("   ⚠️ 位置誤差過大")
        else:
            print("   ✓ 移動正常")

        print("\n健康檢查完成！")

# ==================== 主程序 ====================

if __name__ == '__main__':
    # 根據需要取消註釋運行不同示例

    example_basic()              # 基礎操作
    # example_auto_scan()        # 自動掃描模式
    # example_smooth_tracking()  # 平滑追蹤
    # example_scan_pattern()     # 掃描模式
    # example_interactive()      # 交互式控制
    # example_camera_tracking()  # 相機追蹤
    # example_position_monitoring()  # 位置監控
```

---

## 🎮 進階應用

### 3. 遊戲手把控制

```python
"""使用遊戲手把控制雲台（需要 pygame）"""

import pygame
from pt2d_controller import PT2DController
import time

def gamepad_control():
    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        print("No gamepad found!")
        return

    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    print(f"Using: {joystick.get_name()}")

    with PT2DController('COM3') as pt:
        pt.set_speed(70)
        pt.home()

        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            # 讀取搖桿位置
            axis_x = joystick.get_axis(0)  # 左搖桿 X
            axis_y = joystick.get_axis(1)  # 左搖桿 Y

            # 死區過濾
            if abs(axis_x) < 0.1:
                axis_x = 0
            if abs(axis_y) < 0.1:
                axis_y = 0

            # 控制雲台
            if axis_x != 0 or axis_y != 0:
                pan_delta = int(axis_x * 5)
                tilt_delta = int(axis_y * 5)
                pt.move_by(pan_delta, -tilt_delta)

            # 按鈕控制
            if joystick.get_button(0):  # A 按鈕回中心
                pt.home()

            time.sleep(0.05)

    pygame.quit()

if __name__ == '__main__':
    gamepad_control()
```

### 4. OpenCV 人臉追蹤

```python
"""使用 OpenCV 進行人臉追蹤（需要 opencv-python）"""

import cv2
from pt2d_controller import PT2DController
import time

def face_tracking():
    # 初始化相機
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Cannot open camera")
        return

    # 加載人臉檢測器
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    )

    with PT2DController('COM3') as pt:
        pt.set_speed(60)
        pt.home()
        time.sleep(1)

        # PID 控制參數
        kp = 0.1

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # 轉灰度圖
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # 檢測人臉
            faces = face_cascade.detectMultiScale(gray, 1.3, 5)

            if len(faces) > 0:
                # 取第一個人臉
                (x, y, w, h) = faces[0]

                # 計算人臉中心
                face_center_x = x + w // 2
                face_center_y = y + h // 2

                # 計算畫面中心
                frame_center_x = frame.shape[1] // 2
                frame_center_y = frame.shape[0] // 2

                # 計算誤差
                error_x = face_center_x - frame_center_x
                error_y = face_center_y - frame_center_y

                # PID 控制
                pan_delta = int(error_x * kp)
                tilt_delta = int(-error_y * kp)

                # 控制雲台
                if abs(error_x) > 20 or abs(error_y) > 20:
                    pt.move_by(pan_delta, tilt_delta)

                # 繪製矩形
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.circle(frame, (face_center_x, face_center_y), 5, (0, 0, 255), -1)

            # 顯示畫面
            cv2.imshow('Face Tracking', frame)

            # 按 'q' 退出
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            time.sleep(0.05)

    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    face_tracking()
```

---

## 🧪 測試腳本

### 5. 功能測試

```python
"""完整功能測試腳本"""

from pt2d_controller import PT2DController
import time

def test_all_commands():
    print("=== Arduino 2D Pan-Tilt 功能測試 ===\n")

    with PT2DController('COM3') as pt:

        # 測試 1: 移動到絕對位置
        print("Test 1: Move to absolute position")
        print(pt.move_to(135, 90))
        time.sleep(2)
        pan, tilt = pt.get_position()
        print(f"Position: Pan={pan}°, Tilt={tilt}°\n")

        # 測試 2: 相對移動
        print("Test 2: Move by relative position")
        print(pt.move_by(50, -30))
        time.sleep(2)
        pan, tilt = pt.get_position()
        print(f"Position: Pan={pan}°, Tilt={tilt}°\n")

        # 測試 3: 速度控制
        print("Test 3: Speed control")
        print(pt.set_speed(10))
        print(pt.move_to(270, 90))
        time.sleep(5)
        print(pt.set_speed(100))
        print(pt.move_to(0, 90))
        time.sleep(2)
        print()

        # 測試 4: 回初始位置
        print("Test 4: Home position")
        print(pt.home())
        time.sleep(2)
        pan, tilt = pt.get_position()
        print(f"Position: Pan={pan}°, Tilt={tilt}°\n")

        # 測試 5: 停止命令
        print("Test 5: Stop command")
        print(pt.set_speed(10))
        print(pt.move_to(180, 180))
        time.sleep(1)
        print(pt.stop())
        pan, tilt = pt.get_position()
        print(f"Stopped at: Pan={pan}°, Tilt={tilt}°\n")

        # 測試 6: 校準
        print("Test 6: Calibration")
        print(pt.calibrate())
        time.sleep(10)  # 校準需要較長時間
        print("Calibration complete\n")

        print("=== All tests completed ===")

if __name__ == '__main__':
    test_all_commands()
```

---

## 📚 依賴安裝

```bash
# 基礎功能
pip install pyserial

# 遊戲手把控制
pip install pygame

# 人臉追蹤
pip install opencv-python

# 或一次安裝所有
pip install pyserial pygame opencv-python
```

---

## ⚙️ 配置說明

### 串口號查找

**Windows**:
```python
import serial.tools.list_ports

ports = serial.tools.list_ports.comports()
for port in ports:
    print(f"{port.device}: {port.description}")
```

**Linux/Mac**:
```bash
ls /dev/tty*
# 通常是 /dev/ttyUSB0 或 /dev/ttyACM0
```

---

**更新日期**: 2025-12-23
**版本**: 1.0.0
