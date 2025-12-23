"""
雷射標記控制模組
透過 Orange Pi 5 GPIO 控制繼電器來啟動/關閉雷射
"""

import time
import logging
from typing import Optional

# 嘗試導入 Orange Pi GPIO 庫
try:
    import OPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    try:
        import RPi.GPIO as GPIO
        GPIO_AVAILABLE = True
    except ImportError:
        GPIO_AVAILABLE = False
        print("警告: GPIO 庫未安裝，雷射控制將無法使用")
        print("請執行: pip3 install OrangePi.GPIO")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LaserController:
    """雷射控制器類"""

    def __init__(self, gpio_pin: int = 5, use_board_mode: bool = True):
        """
        初始化雷射控制器

        Args:
            gpio_pin: GPIO 引腳編號（預設 5 = 實體 Pin 5）
            use_board_mode: True 使用 BOARD 模式（實體引腳），False 使用 BCM 模式
        """
        self.gpio_pin = gpio_pin
        self.use_board_mode = use_board_mode
        self.is_initialized = False
        self.laser_state = False

        if not GPIO_AVAILABLE:
            logger.error("GPIO 庫未安裝，雷射控制功能無法使用")
            return

        try:
            # 設定 GPIO 模式
            if self.use_board_mode:
                GPIO.setmode(GPIO.BOARD)  # 使用實體引腳編號
                logger.info(f"GPIO 模式: BOARD (實體 Pin {gpio_pin})")
            else:
                GPIO.setmode(GPIO.BCM)    # 使用 BCM 編號
                logger.info(f"GPIO 模式: BCM (GPIO {gpio_pin})")

            # 設定引腳為輸出模式
            GPIO.setup(self.gpio_pin, GPIO.OUT)

            # 初始狀態為關閉
            GPIO.output(self.gpio_pin, GPIO.LOW)

            self.is_initialized = True
            logger.info(f"雷射控制器初始化成功 (Pin {gpio_pin})")

        except Exception as e:
            logger.error(f"雷射控制器初始化失敗: {e}")
            logger.error("請確認:")
            logger.error("1. 是否使用 sudo 運行程式")
            logger.error("2. 使用者是否在 gpio 群組中")
            self.is_initialized = False

    def on(self):
        """開啟雷射"""
        if not self.is_initialized:
            logger.warning("雷射控制器未初始化")
            return False

        try:
            GPIO.output(self.gpio_pin, GPIO.HIGH)
            self.laser_state = True
            logger.info("雷射已開啟")
            return True
        except Exception as e:
            logger.error(f"開啟雷射失敗: {e}")
            return False

    def off(self):
        """關閉雷射"""
        if not self.is_initialized:
            logger.warning("雷射控制器未初始化")
            return False

        try:
            GPIO.output(self.gpio_pin, GPIO.LOW)
            self.laser_state = False
            logger.info("雷射已關閉")
            return True
        except Exception as e:
            logger.error(f"關閉雷射失敗: {e}")
            return False

    def pulse(self, duration: float = 0.1):
        """
        發出雷射脈衝（開啟後自動關閉）

        Args:
            duration: 脈衝持續時間（秒）
        """
        if not self.is_initialized:
            logger.warning("雷射控制器未初始化")
            return False

        try:
            self.on()
            time.sleep(duration)
            self.off()
            return True
        except Exception as e:
            logger.error(f"雷射脈衝失敗: {e}")
            return False

    def blink(self, count: int = 3, on_time: float = 0.1, off_time: float = 0.1):
        """
        雷射閃爍

        Args:
            count: 閃爍次數
            on_time: 開啟時間（秒）
            off_time: 關閉時間（秒）
        """
        if not self.is_initialized:
            logger.warning("雷射控制器未初始化")
            return False

        try:
            for i in range(count):
                self.on()
                time.sleep(on_time)
                self.off()
                if i < count - 1:  # 最後一次不需要等待
                    time.sleep(off_time)
            return True
        except Exception as e:
            logger.error(f"雷射閃爍失敗: {e}")
            return False

    def get_state(self) -> bool:
        """獲取雷射當前狀態"""
        return self.laser_state

    def cleanup(self):
        """清理 GPIO 資源"""
        if self.is_initialized:
            try:
                self.off()  # 確保雷射關閉
                GPIO.cleanup(self.gpio_pin)
                logger.info("GPIO 資源已清理")
            except Exception as e:
                logger.error(f"清理 GPIO 失敗: {e}")

        self.is_initialized = False

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.cleanup()


def test_laser():
    """測試雷射控制器"""
    print("=" * 50)
    print("雷射控制器測試程式")
    print("=" * 50)
    print()
    print("⚠️  安全警告:")
    print("1. 確保雷射模組已正確安裝")
    print("2. 請勿直視雷射光")
    print("3. 確保雷射指向安全方向")
    print()

    input("按 Enter 鍵開始測試...")

    # 使用 Pin 5 (實體引腳編號)
    with LaserController(gpio_pin=5, use_board_mode=True) as laser:
        if not laser.is_initialized:
            print("❌ 雷射控制器初始化失敗")
            print("\n解決方法:")
            print("1. 使用 sudo 運行: sudo python3 laser_controller.py")
            print("2. 或將使用者加入 gpio 群組:")
            print("   sudo usermod -a -G gpio $USER")
            print("   (需登出後重新登入)")
            return

        print("\n✅ 雷射控制器初始化成功\n")

        # 測試 1: 開關控制
        print("測試 1: 開關控制")
        print("  開啟雷射...")
        laser.on()
        time.sleep(2)
        print("  關閉雷射...")
        laser.off()
        time.sleep(1)

        # 測試 2: 脈衝
        print("\n測試 2: 脈衝模式 (0.5 秒)")
        laser.pulse(duration=0.5)
        time.sleep(1)

        # 測試 3: 閃爍
        print("\n測試 3: 閃爍模式 (5 次)")
        laser.blink(count=5, on_time=0.2, off_time=0.2)

        print("\n✅ 所有測試完成")
        print(f"當前狀態: {'開啟' if laser.get_state() else '關閉'}")


if __name__ == "__main__":
    test_laser()
