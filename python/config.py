"""
系統配置參數
統一管理系統中的關鍵參數，方便調整和維護
"""

# ============================================
# AI 檢測參數
# ============================================

# 輸入影像解析度（像素）
# - 320: 快速推理，適合低效能設備（約 15-25 FPS on Orange Pi 5）
# - 416: 平衡選項，中等精度與速度
# - 640: 標準精度，推薦使用（約 10-15 FPS on Orange Pi 5）
# - 800/1280: 高精度，適合 PC 開發環境
DEFAULT_IMGSZ = 640

# 信心度閾值（0.0-1.0）
# 只有信心度超過此閾值的檢測結果會被接受
DEFAULT_CONFIDENCE_THRESHOLD = 0.4

# IoU 閾值（Non-Maximum Suppression）
DEFAULT_IOU_THRESHOLD = 0.45

# ============================================
# 追蹤參數
# ============================================

# 追蹤增益（控制雲台移動的靈敏度）
DEFAULT_PAN_GAIN = 0.15
DEFAULT_TILT_GAIN = 0.15

# 無檢測超時時間（秒）
# 連續 N 秒無檢測到目標時，返回監控模式
DEFAULT_NO_DETECTION_TIMEOUT = 3.0

# 目標鎖定距離（像素）
# 多目標時，優先追蹤距離上次位置在此範圍內的目標
DEFAULT_TARGET_LOCK_DISTANCE = 100

# ============================================
# 硬體參數
# ============================================

# Arduino 串口設定
DEFAULT_ARDUINO_PORT = '/dev/ttyUSB0'  # Linux/Orange Pi
# DEFAULT_ARDUINO_PORT = 'COM3'        # Windows

# 攝像頭 ID
DEFAULT_LEFT_CAMERA_ID = 0
DEFAULT_RIGHT_CAMERA_ID = 1

# ============================================
# 雷射與蜂鳴器控制
# ============================================

# 蜂鳴器冷卻時間（秒）
DEFAULT_BEEP_COOLDOWN = 2.0

# 雷射冷卻時間（秒）
DEFAULT_LASER_COOLDOWN = 0.5

# ============================================
# 樣本收集參數
# ============================================

# 是否自動儲存中等信心度樣本
DEFAULT_SAVE_UNCERTAIN_SAMPLES = False

# 中等信心度範圍（用於樣本收集）
DEFAULT_UNCERTAIN_CONF_RANGE = (0.35, 0.65)

# 樣本儲存目錄
DEFAULT_SAVE_DIR = "uncertain_samples"

# 最大磁碟使用率百分比
DEFAULT_MAX_DISK_USAGE_PERCENT = 20.0

# ============================================
# 網路配置
# ============================================

# Orange Pi 5 IP 地址（用於生成訪問說明）
# 設為 None 時會顯示 [Your_IP] 提示
DEFAULT_DEVICE_IP = None  # 例如: "192.168.1.100"

# 外部訪問 URL（透過 Nginx Reverse Proxy）
# 設為 None 時不顯示外部 URL
DEFAULT_EXTERNAL_URL = None  # 例如: "https://mosquito.ma7.in"

# ============================================
# 串流伺服器參數
# ============================================

# HTTP 串流伺服器端口
DEFAULT_STREAM_PORT = 5000

# 串流品質（1-100）
DEFAULT_STREAM_QUALITY = 80

# 串流 FPS
DEFAULT_STREAM_FPS = 15

# RTSP 配置（需外部 MediaMTX 伺服器）
DEFAULT_RTSP_URL = "rtsp://0.0.0.0:8554/mosquito"  # RTSP 目標地址（0.0.0.0 允許外部訪問）
DEFAULT_RTSP_BITRATE = 2000  # kbps
DEFAULT_RTSP_PRESET = "ultrafast"  # FFmpeg 編碼預設
