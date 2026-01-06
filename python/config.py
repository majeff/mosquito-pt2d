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

# 偵測模式（預設使用平鋪推理以保留高解析度細節）
# 可選值：'tiling'（平鋪，建議預設）或 'whole'（整張影像）
DEFAULT_DETECTION_MODE = 'tiling'

# 平鋪重疊比例（0.0-0.5 建議範圍），避免邊界漏檢
# 例如 0.25 代表平鋪視窗彼此重疊 25% 邊長
DEFAULT_TILE_OVERLAP = 0.25

# 檢測邊界邊距（0.0-0.5，比例）
# 排除畫面邊緣區域的檢測結果，避免邊界誤檢
# 例如 0.1 代表排除上下左右各 10% 的邊界區域
DEFAULT_DETECTION_MARGIN = 0.1

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
DEFAULT_SAVE_UNCERTAIN_SAMPLES = True

# 中等信心度範圍（用於樣本收集）
DEFAULT_UNCERTAIN_CONF_RANGE = (0.4, 0.7)

# 樣本儲存目錄
DEFAULT_SAVE_DIR = "uncertain_samples"

# 最大存儲照片數量（改為數量限制而非磁碟使用率）
DEFAULT_MAX_SAMPLES = 1000

# 儲存時間間隔（秒）- 避免頻繁存同一位置的照片
DEFAULT_SAVE_INTERVAL = 3.0

# 上一次儲存的照片雜湊值 - 用於避免儲存重複的照片
DEFAULT_LAST_SAVED_HASH = None

# ============================================
# 樣本標註參數
# ============================================

# 樣本標註目錄結構
SAMPLE_COLLECTION_DIR = "sample_collection"
MEDIUM_CONFIDENCE_DIR = "sample_collection/medium_confidence"
CONFIRMED_MOSQUITO_DIR = "sample_collection/confirmed/mosquito"
CONFIRMED_NOT_MOSQUITO_DIR = "sample_collection/confirmed/not_mosquito"

# 樣本搬遷目標目錄（用於備份或遷移樣本）
# 預設指向本機 Google Drive（我的雲端硬碟/Colab Notebooks）下的專案搬遷目錄
# 注意：如您的 Google Drive 掛載磁碟代號不是 G:\，請手動調整下列路徑
RELOCATION_BASE_DIR = r"G:\我的雲端硬碟\Colab Notebooks\mosquito-training\relocated"
RELOCATION_MOSQUITO_DIR = f"{RELOCATION_BASE_DIR}/mosquito"
RELOCATION_NOT_MOSQUITO_DIR = f"{RELOCATION_BASE_DIR}/not_mosquito"

# Colab Notebook 同步目標目錄（根目錄：我的雲端硬碟/Colab Notebooks）
COLAB_NOTEBOOK_DEST_DIR = r"G:\我的雲端硬碟\Colab Notebooks"

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

# ============================================
# 溫度監控參數
# ============================================

# 是否啟用溫度監控
ENABLE_TEMPERATURE_MONITORING = True

# 溫度警告閾值（攝氏度）
TEMPERATURE_WARNING_THRESHOLD = 75.0

# 溫度暫停閾值（攝氏度）- 超過此溫度將暫停 AI 辨識
TEMPERATURE_PAUSE_THRESHOLD = 80.0

# 溫度恢復閾值（攝氏度）- 降至此溫度以下將恢復 AI 辨識
TEMPERATURE_RESUME_THRESHOLD = 70.0

# 溫度檢查間隔（秒）- 每分鐘檢查一次以降低系統耗損
TEMPERATURE_CHECK_INTERVAL = 60.0

# 溫度感測器路徑（Linux 系統）
# Orange Pi 5 / RK3588: /sys/class/thermal/thermal_zone0/temp
# Raspberry Pi: /sys/class/thermal/thermal_zone0/temp
TEMPERATURE_SENSOR_PATH = "/sys/class/thermal/thermal_zone0/temp"

# ============================================
# 光照度監控參數
# ============================================

# 是否啟用光照度監控
ENABLE_ILLUMINATION_MONITORING = True

# 光照度警告閾值（亮度值 0-255 範圍）
# 低於此值時在螢幕提示光照不足
ILLUMINATION_WARNING_THRESHOLD = 60

# 光照度暫停閾值（亮度值 0-255 範圍）
# 低於此值時暫停 AI 辨識，高於此值時恢復 AI 辨識
ILLUMINATION_PAUSE_THRESHOLD = 40

# 光照度檢查間隔（秒）- 每 N 秒檢查一次亮度
ILLUMINATION_CHECK_INTERVAL = 5.0
