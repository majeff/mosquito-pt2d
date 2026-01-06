# 影像串流指南

讓手機即時觀看蚊子追蹤系統的辨識結果。

## 📋 方案比較

| 方案 | 延遲 | 實現難度 | 帶寬消耗 | AI 標註 | 雙目支援 | 推薦度 |
|------|------|----------|----------|---------|----------|--------|
| **HTTP-MJPEG** | 中 (0.5-2s) | ⭐ 簡單 | 高 | ✅ 支援 | ✅ 支援 | ⭐⭐⭐⭐ |
| **RTSP** | 低 (< 0.5s) | ⭐⭐ 中等 | 低 | ✅ 支援 | ✅ 支援 | ⭐⭐⭐⭐⭐ |

**重要說明**：
- ✅ **兩種方案都包含 AI 即時標註結果**（檢測框、信心度、類別等）
- ✅ **完整支援雙目攝像頭**（並排顯示、獨立串流、切換視角）
- ✅ **標註內容**：邊界框、中心點、信心度、類別名稱、追蹤狀態

## 🎯 推薦方案

### **方案 1: HTTP-MJPEG（預設方案，推薦入門）**⭐⭐⭐⭐

**優點：**
- ✅ 實現最簡單，幾行代碼搞定
- ✅ 瀏覽器直接觀看，無需 APP
- ✅ 無需額外伺服器
- ✅ **包含完整 AI 標註**（檢測框、信心度、追蹤狀態）
- ✅ **支援雙目攝像頭並排顯示**
- ✅ **系統預設啟用**

**適合場景：**
- 快速原型開發
- 區域網路內觀看
- 不在意延遲（1-2秒可接受）
- 需要即時查看 AI 檢測結果

### **方案 2: RTSP（需手動啟用，推薦正式使用）**⭐⭐⭐⭐⭐

**優點：**
- ✅ 低延遲（< 0.5s），適合即時追蹤
- ✅ 標準協議，APP 支援廣泛
- ✅ 帶寬消耗低
- ✅ **包含完整 AI 標註**（檢測框、信心度、追蹤狀態）
- ✅ **支援雙目攝像頭獨立串流**

**注意：**
- ⚠️ **需要加上 `--rtsp` 參數才會啟用**
- ⚠️ 需要安裝 MediaMTX 和 FFmpeg

**適合場景：**
- 需要低延遲
- 多客戶端同時觀看
- 正式部署環境
- 專業監控需求

---

## 📹 雙目攝像頭串流方案

本專案使用雙目 USB 攝像頭（3840×1080 @ 60fps），提供三種串流模式：

### **模式 1: 並排顯示**

將左右攝像頭畫面水平拼接，在一個串流中同時顯示。

**優點：**
- ✅ 一個串流地址即可觀看雙目
- ✅ 節省帶寬和資源
- ✅ 方便對比觀察

```python
# 拼接左右畫面
left_frame = frame[:, :1920]   # 左半部
right_frame = frame[:, 1920:]  # 右半部

# AI 檢測（通常只用左側）
detections, result_left = detector.detect(left_frame)
result_left = detector.draw_detections(result_left, detections)

# 拼接並串流
combined = np.hstack([result_left, right_frame])
server.update_frame(combined)
```

### **模式 2: 單一視角（AI 標註）** ⭐ 預設模式

僅串流左側攝像頭，包含完整 AI 標註。

**優點：**
- ✅ 帶寬消耗最低
- ✅ 專注於 AI 檢測結果
- ✅ 適合追蹤監控
- ✅ **系統預設模式**

```python
# 僅使用左側畫面
left_frame = frame[:, :1920]
detections, result = detector.detect(left_frame)
result = detector.draw_detections(result, detections)
server.update_frame(result)
```

### **模式 3: 獨立雙串流**

左右攝像頭各自獨立串流。

**優點：**
- ✅ 可選擇觀看任一視角
- ✅ 支援立體視覺應用
- ✅ 專業級監控

```python
# 創建兩個串流伺服器
server_left = StreamingServer(http_port=5000)   # 左側 + AI
server_right = StreamingServer(http_port=5001)  # 右側原始

# 分別更新
left_frame = frame[:, :1920]
right_frame = frame[:, 1920:]

detections, result_left = detector.detect(left_frame)
result_left = detector.draw_detections(result_left, detections)

server_left.update_frame(result_left)
server_right.update_frame(right_frame)
```

**觀看地址：**
- 左側（AI 標註）：`http://[IP]:5000`
- 右側（原始）：`http://[IP]:5001`

---

## 🚀 快速開始

### 方法 1: HTTP-MJPEG（最簡單）

#### 1. 安裝依賴

```bash
pip install flask
```

#### 2. 啟動串流伺服器（含 AI 標註 + 雙目支援）

```python
from streaming_server import StreamingServer
from mosquito_detector import MosquitoDetector
import cv2
import numpy as np

# 初始化 AI 檢測器
detector = MosquitoDetector(model_path="models/mosquito")

# 初始化串流伺服器
server = StreamingServer(http_port=5000)
server.run(threaded=True)

print("串流伺服器已啟動（包含 AI 即時標註）")
print("手機觀看: http://[你的IP]:5000")

# 開啟雙目攝像頭（3840×1080）
cap = cv2.VideoCapture(0)  # 左攝像頭 ID
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 3840)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # 分離左右畫面
    left_frame = frame[:, :1920]   # 左側：用於 AI 檢測
    right_frame = frame[:, 1920:]  # 右側：原始畫面

    # AI 檢測與標註（在左側畫面）
    detections, result_left = detector.detect(left_frame)
    result_left = detector.draw_detections(result_left, detections)

    # 添加檢測資訊
    cv2.putText(result_left, f"Detections: {len(detections)}",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    # 模式 1: 並排顯示（推薦）
    combined = np.hstack([result_left, right_frame])
    server.update_frame(combined)

    # 模式 2: 僅顯示 AI 標註畫面
    # server.update_frame(result_left)
```

**串流內容說明：**
- ✅ 左側畫面：完整 AI 標註（檢測框、信心度、類別、中心點）
- ✅ 右側畫面：原始影像
- ✅ 頂部顯示：檢測數量、連線數、運行時間
- ✅ 底部右方：光照強度（Lux 值）與狀態指示
- ✅ 即時更新：每幀都包含最新的 AI 檢測結果

**光照度監測說明：**
- 🟢 **綠色（正常）**: 光照充足，AI 檢測正常運行
- 🟠 **橙色（警告）**: 光照開始降低，接近暫停閾值
- 🔴 **紅色（暫停）**: 光照過低，AI 檢測已自動暫停以節省資源
- 🟡 **黃色（已恢復）**: 光照已改善，AI 檢測已恢復運行

AI 會根據 `config.py` 中的閾值自動調整：
- `ILLUMINATION_WARNING_THRESHOLD = 30`：警告光照值
- `ILLUMINATION_PAUSE_THRESHOLD = 15`：暫停檢測光照值
- `ILLUMINATION_RESUME_THRESHOLD = 25`：恢復檢測光照值

#### 3. 手機觀看

在手機瀏覽器輸入：
```
http://[Orange_Pi_IP]:5000
```

例如：`http://192.168.1.100:5000`

**查看 IP 地址：**
```bash
# Linux/Orange Pi
ip addr show

# Windows
ipconfig
```

---

### 方法 2: RTSP（推薦）

#### 1. 安裝 mediamtx（RTSP 伺服器）

**Orange Pi / Linux:**
```bash
# 下載
wget https://github.com/bluenviron/mediamtx/releases/download/v1.5.0/mediamtx_v1.5.0_linux_arm64v8.tar.gz

# 解壓
tar -xzf mediamtx_v1.5.0_linux_arm64v8.tar.gz

# 執行
./mediamtx
```

**Windows:**
1. 下載：https://github.com/bluenviron/mediamtx/releases
2. 解壓並執行 `mediamtx.exe`

#### 2. 安裝 FFmpeg

```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# Windows
# 下載：https://ffmpeg.org/download.html
```

#### 3. 推流到 RTSP

**方式 A：使用 FFmpeg 推流**

```python
import subprocess
import cv2
from mosquito_detector import MosquitoDetector

detector = MosquitoDetector(model_path="models/mosquito")
cap = cv2.VideoCapture(0)

# 取得影像尺寸
ret, frame = cap.read()
height, width = frame.shape[:2]

# FFmpeg 推流命令
ffmpeg_cmd = [
    'ffmpeg',
    '-y',
    '-f', 'rawvideo',
    '-vcodec', 'rawvideo',
    '-pix_fmt', 'bgr24',
    '-s', f'{width}x{height}',
    '-r', '30',
    '-i', '-',
    '-c:v', 'libx264',
    '-preset', 'ultrafast',
    '-tune', 'zerolatency',
    '-f', 'rtsp',
    'rtsp://localhost:8554/mosquito'
]

process = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # AI 檢測
    detections, result = detector.detect(frame)
    result = detector.draw_detections(result, detections)

    # 推流
    process.stdin.write(result.tobytes())
```

**方式 B：使用 OpenCV 直接推流（需安裝 GStreamer）**

```python
import cv2
from mosquito_detector import MosquitoDetector

detector = MosquitoDetector(model_path="models/mosquito")
cap = cv2.VideoCapture(0)

# GStreamer pipeline
gst_out = (
    'appsrc ! videoconvert ! x264enc tune=zerolatency bitrate=2000 ! '
    'rtspclientsink location=rtsp://localhost:8554/mosquito'
)

out = cv2.VideoWriter(gst_out, cv2.CAP_GSTREAMER, 30, (640, 480), True)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # AI 檢測
    detections, result = detector.detect(frame)
    result = detector.draw_detections(result, detections)

    # 推流
    out.write(result)
```

#### 4. 手機觀看

**使用 RTSP 播放器 APP：**

- **Android**: VLC for Android, RTSP Player
- **iOS**: VLC for iOS, RTSP Player

輸入 RTSP 地址：
```
rtsp://[Orange_Pi_IP]:8554/mosquito
```

例如：`rtsp://192.168.1.100:8554/mosquito`

---

## 📱 手機 APP 推薦

### Android
1. **VLC for Android**（推薦）
   - 免費、開源
   - 支援 RTSP、HTTP-MJPEG
   - Play 商店下載

2. **RTSP Player**
   - 專為 RTSP 設計
   - 延遲更低

### iOS
1. **VLC for iOS**（推薦）
   - 免費、開源
   - 支援 RTSP、HTTP-MJPEG
   - App Store 下載

2. **IP Camera Lite**
   - 專業監控 APP
   - 支援多路串流

---

## 🔧 進階配置

### 網路訪問設定

**預設配置：**
- 串流伺服器預設綁定到 `0.0.0.0`（監聽所有網路介面）
- 允許任何 IP 地址訪問（區域網路和外網）
- 無內建身份驗證機制

**安全建議：**
```bash
# 方法 1: 使用防火牆限制訪問（推薦）
sudo ufw allow from 192.168.1.0/24 to any port 5000  # 僅允許區域網路

# 方法 2: 使用 Nginx 反向代理 + 密碼保護
sudo apt install nginx apache2-utils
sudo htpasswd -c /etc/nginx/.htpasswd username

# 方法 3: VPN 訪問（最安全）
# 安裝 Tailscale/Zerotier，僅允許 VPN 內部訪問
```

**Nginx 配置範例（含密碼保護）：**
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        auth_basic "Restricted Access";
        auth_basic_user_file /etc/nginx/.htpasswd;
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

### 降低延遲

**RTSP 配置：**
```yaml
# mediamtx.yml
paths:
  mosquito:
    source: publisher
    readTimeout: 5s
    readBufferCount: 512  # 減少緩衝
```

**FFmpeg 推流優化：**
```bash
-preset ultrafast      # 最快編碼
-tune zerolatency      # 零延遲調校
-bufsize 1000k         # 減少緩衝
-g 30                  # 關鍵幀間隔
```

### 調整畫質與帶寬

**高畫質（需要更好網路）：**
```python
server = StreamingServer(quality=95)  # JPEG 品質 95
```

**省帶寬：**
```python
server = StreamingServer(quality=70, fps=15)  # 降低品質和幀率
```

### 遠端訪問（外網）

1. **使用 Tailscale/Zerotier（推薦）**
   - 無需公網 IP
   - 安全的虛擬區域網路
   - 零配置

2. **端口轉發**
   - 路由器設定端口映射
   - 需要公網 IP
   - 注意安全性

3. **內網穿透（frp/ngrok）**
   - 無需公網 IP
   - 可能有延遲

---

## 🎥 整合範例

### 完整串流系統

```python
"""
完整的蚊子追蹤串流系統
"""

from streaming_server import StreamingServer
from mosquito_detector import MosquitoDetector
from mosquito_tracker import MosquitoTracker
from pt2d_controller import PT2DController
import cv2

def main():
    # 初始化組件
    detector = MosquitoDetector(model_path="models/mosquito")
    pt = PT2DController('/dev/ttyUSB0')
    tracker = MosquitoTracker(detector, pt)

    # 啟動串流伺服器
    server = StreamingServer(http_port=5000, fps=30)
    server.run(threaded=True)

    print("串流伺服器已啟動")
    print(f"手機觀看: http://[你的IP]:5000")

    # 主循環
    cap = cv2.VideoCapture(0)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # AI 檢測與追蹤
        detections, result = detector.detect(frame)
        result = detector.draw_detections(result, detections)

        if detections:
            tracker.track(detections[0])

        # 更新串流
        server.update_frame(result)

        # Headless 模式：無本地顯示窗口
        # 通過瀏覽器訪問 http://[IP]:5000 查看影像
        time.sleep(0.03)  # 控制幀率 ~30 FPS

    cap.release()

if __name__ == "__main__":
    main()
```

---

## 🐛 故障排除

### RTSP 推流故障排除

#### 檢查清單

如果 RTSP 不能正常啟動，請按以下步驟檢查：

**1. 檢查 FFmpeg 安裝**
```bash
# Linux/Orange Pi
ffmpeg -version

# 如果未安裝
sudo apt update
sudo apt install ffmpeg

# Windows - 下載並添加到 PATH
# https://ffmpeg.org/download.html
```

**2. 檢查 MediaMTX 是否在運行**
```bash
# 下載 MediaMTX
# Linux ARM64 (Orange Pi):
wget https://github.com/bluenviron/mediamtx/releases/download/v1.7.0/mediamtx_v1.7.0_linux_arm64.tar.gz
tar -xzf mediamtx_v1.7.0_linux_arm64.tar.gz

# 運行
./mediamtx

# 驗證是否監聽 8554 端口
netstat -tuln | grep 8554
# 或
ss -tuln | grep 8554
```

**3. 檢查網絡連接**
```bash
# 測試 MediaMTX 連接
nc -zv 0.0.0.0 8554

# 或使用 Python
python -c "import socket; s=socket.socket(); s.settimeout(2); print('OK' if s.connect_ex(('0.0.0.0', 8554))==0 else 'FAILED'); s.close()"
```

**4. 查看詳細日誌**

運行系統時需要加上 `--rtsp` 參數來啟用 RTSP 推流（預設停用）：
```bash
python streaming_tracking_system.py --rtsp
```

**注意**：RTSP 推流預設是停用的，如果不加 `--rtsp` 參數，系統只會使用 HTTP-MJPEG 串流。

查看日誌輸出：
```
[6/6] 初始化 RTSP 推流...
      ✓ RTSP 已配置
         URL: rtsp://0.0.0.0:8554/mosquito
         碼率: 2000kbps
      ⏳ RTSP 推流將在第一幀時啟動...
...
🔧 正在初始化 RTSP...
   RTSP URL: rtsp://0.0.0.0:8554/mosquito
   RTSP 碼率: 2000kbps
   幀尺寸: 1920x1080
正在啟動 RTSP 推流到 rtsp://0.0.0.0:8554/mosquito
解析度: 1920x1080, FPS: 30, 碼率: 2000kbps
✅ RTSP 推流已啟動！
```

如果看到錯誤信息，根據提示進行修復。

**常見錯誤及解決方案：**

| 錯誤 | 原因 | 解決方法 |
|------|------|----------|
| `❌ FFmpeg 未安裝！` | FFmpeg 未安裝或不在 PATH | 安裝 FFmpeg 並確保可以在命令行執行 |
| `❌ FFmpeg 啟動失敗` | MediaMTX 未運行 | 啟動 MediaMTX 並確保監聽 8554 端口 |
| `Connection refused` | MediaMTX 未監聽正確的地址 | 檢查 mediamtx.yml 配置 |
| `管道已斷開` | RTSP URL 錯誤或網絡問題 | 驗證 URL 格式和網絡連接 |

### 問題 1: 手機無法連線

**檢查項目：**
1. Orange Pi 和手機在同一 Wi-Fi 網路
2. 防火牆是否阻擋端口
3. IP 地址是否正確

**解決方法：**
```bash
# 檢查端口是否開啟
sudo netstat -tulpn | grep 5000

# 臨時關閉防火牆測試
sudo ufw disable
```

### 問題 2: 延遲太高

**HTTP-MJPEG:**
- 降低 JPEG 品質
- 降低幀率
- 減小影像尺寸

**RTSP:**
- 使用 ultrafast preset
- 啟用 zerolatency tune
- 減少緩衝區

### 問題 3: CPU 使用率過高

**優化方法：**
1. 降低串流解析度
2. 降低 AI 檢測幀率（每 N 幀檢測一次）
3. 使用硬體編碼（Orange Pi 5 支援）

---

## 📚 相關文檔

- [mediamtx GitHub](https://github.com/bluenviron/mediamtx)
- [FFmpeg 文檔](https://ffmpeg.org/documentation.html)
- [RTSP 協議說明](https://en.wikipedia.org/wiki/Real_Time_Streaming_Protocol)
- [Flask 文檔](https://flask.palletsprojects.com/)

![GA Tracking](https://ga4.ma7.in/ga/github/STREAMING_GUIDE/影像串流指南)
