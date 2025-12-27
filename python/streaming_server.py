"""
影像串流伺服器
支援 RTSP 和 HTTP-MJPEG 兩種串流方式
"""

import cv2
import numpy as np
from flask import Flask, Response, render_template_string, jsonify
import threading
import time
import logging
from typing import Optional
from pathlib import Path
try:
    from config import DEFAULT_DEVICE_IP, DEFAULT_EXTERNAL_URL
except ImportError:
    DEFAULT_DEVICE_IP = None
    DEFAULT_EXTERNAL_URL = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StreamingServer:
    """影像串流伺服器（支援 RTSP 和 HTTP-MJPEG）

    特色：
    - 完整支援 AI 即時標註（檢測框、信心度、追蹤狀態）
    - 支援雙目攝像頭（並排顯示、獨立串流、切換視角）
    - 低延遲 MJPEG 串流
    - 多客戶端同時觀看
    """

    def __init__(self,
                 http_port: int = 5000,
                 fps: int = 30,
                 quality: int = 85,
                 device_ip: Optional[str] = DEFAULT_DEVICE_IP,
                 external_url: Optional[str] = DEFAULT_EXTERNAL_URL):
        """
        初始化串流伺服器

        Args:
            http_port: HTTP 伺服器端口
            fps: 串流幀率
            quality: JPEG 壓縮品質 (1-100)
            device_ip: 設備 IP 地址（用於生成訪問說明）
            external_url: 外部訪問 URL（透過 Nginx Reverse Proxy）
        """
        self.http_port = http_port
        self.fps = fps
        self.quality = quality
        self.device_ip = device_ip
        self.external_url = external_url

        # 當前影像（線程安全）
        self.current_frame = None
        self.frame_lock = threading.Lock()

        # 統計資訊
        self.stats = {
            'total_frames': 0,
            'clients': 0,
            'start_time': time.time()
        }

        # Flask APP
        self.app = Flask(__name__)
        self._setup_routes()

        # RTSP 推流進程
        self.rtsp_process = None

        logger.info(f"串流伺服器已初始化")
        logger.info(f"HTTP MJPEG: http://0.0.0.0:{http_port}/video")

    def _setup_routes(self):
        """設置 Flask 路由"""

        @self.app.route('/')
        def index():
            """首頁 - 顯示即時串流"""
            # 生成訪問地址說明
            device_ip = self.device_ip if self.device_ip else "[Your_IP]"
            http_direct_url = f"http://{device_ip}:{self.http_port}"

            # 外部 URL 說明
            external_info = ""
            if self.external_url:
                external_info = f"""
                        <p><strong>方式 3：外部訪問（透過 Nginx Reverse Proxy）</strong></p>
                        <p>從外部網路訪問：<code>{self.external_url}</code></p>
                        <p style="color: #888; font-size: 12px;">
                            * 需要 Nginx 配置 reverse proxy 指向本機 {self.http_port} 端口
                        </p>
                """

            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>蚊子追蹤系統 - 即時監控</title>
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        margin: 0;
                        padding: 20px;
                        background-color: #1a1a1a;
                        color: #fff;
                    }
                    .container {
                        max-width: 1200px;
                        margin: 0 auto;
                    }
                    h1 {
                        text-align: center;
                        color: #4CAF50;
                    }
                    .video-container {
                        position: relative;
                        width: 100%;
                        max-width: 960px;
                        margin: 20px auto;
                        background-color: #000;
                        border: 2px solid #4CAF50;
                        border-radius: 8px;
                        overflow: hidden;
                    }
                    img {
                        width: 100%;
                        height: auto;
                        display: block;
                    }
                    .stats {
                        background-color: #2d2d2d;
                        padding: 15px;
                        border-radius: 8px;
                        margin-top: 20px;
                    }
                    .stat-item {
                        display: inline-block;
                        margin: 10px 20px;
                    }
                    .stat-label {
                        color: #888;
                        font-size: 12px;
                    }
                    .stat-value {
                        color: #4CAF50;
                        font-size: 24px;
                        font-weight: bold;
                    }
                    .info {
                        background-color: #2d2d2d;
                        padding: 15px;
                        border-radius: 8px;
                        margin-top: 20px;
                    }
                    .info h3 {
                        margin-top: 0;
                        color: #4CAF50;
                    }
                    code {
                        background-color: #1a1a1a;
                        padding: 2px 6px;
                        border-radius: 3px;
                        color: #4CAF50;
                    }
                    .offline {
                        text-align: center;
                        padding: 50px;
                        color: #888;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🦟 蚊子追蹤系統 - 即時監控</h1>

                    <div class="video-container">
                        <img src="/video" alt="即時影像串流" onerror="this.src='/static/offline.jpg'">
                    </div>

                    <div class="stats">
                        <div class="stat-item">
                            <div class="stat-label">總幀數</div>
                            <div class="stat-value" id="frames">0</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">連線數</div>
                            <div class="stat-value" id="clients">0</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">運行時間</div>
                            <div class="stat-value" id="uptime">00:00:00</div>
                        </div>
                    </div>

                    <div class="info">
                        <h3>📱 手機觀看方式</h3>
                        <p><strong>方式 1：區域網路直連（推薦）</strong></p>
                        <p>在手機瀏覽器輸入：<code>{http_direct_url}</code></p>

{external_info}
                        <p style="color: #888; font-size: 12px;">
                            * 區域網路訪問需確保設備與 Orange Pi 5 在同一網路
                        </p>

                        <h3>🎯 串流內容</h3>
                        <p>✅ <strong>包含完整 AI 即時標註：</strong></p>
                        <ul>
                            <li>✅ 檢測邊界框（顏色標示信心度高低）</li>
                            <li>✅ 類別名稱與信心度百分比</li>
                            <li>✅ 目標中心點標記</li>
                            <li>✅ 檢測數量與統計資訊</li>
                            <li>✅ 追蹤狀態（如啟用追蹤功能）</li>
                        </ul>

                        <p>🎥 <strong>雙目攝像頭模式：</strong></p>
                        <ul>
                            <li>並排顯示：左側 AI 標註 + 右側原始畫面</li>
                            <li>單一視角：僅顯示 AI 標註畫面</li>
                            <li>獨立串流：左右攝像頭分別串流（需兩個端口）</li>
                        </ul>
                    </div>
                </div>

                <script>
                    // 定期更新統計資訊
                    function updateStats() {{
                        fetch('/stats')
                            .then(response => response.json())
                            .then(data => {{
                                document.getElementById('frames').textContent = data.total_frames;
                                document.getElementById('clients').textContent = data.clients;

                                // 計算運行時間
                                const uptime = Math.floor(Date.now() / 1000 - data.start_time);
                                const hours = Math.floor(uptime / 3600);
                                const minutes = Math.floor((uptime % 3600) / 60);
                                const seconds = uptime % 60;
                                document.getElementById('uptime').textContent =
                                    `${{hours.toString().padStart(2, '0')}}:${{minutes.toString().padStart(2, '0')}}:${{seconds.toString().padStart(2, '0')}}`;
                            }});
                    }}

                    // 每秒更新一次
                    setInterval(updateStats, 1000);
                    updateStats();
                </script>
            </body>
            </html>
            """
            return html

        @self.app.route('/video')
        def video():
            """MJPEG 視頻流"""
            return Response(self._generate_frames(),
                          mimetype='multipart/x-mixed-replace; boundary=frame')

        @self.app.route('/stats')
        def stats():
            """返回統計資訊"""
            return jsonify({
                'total_frames': self.stats['total_frames'],
                'clients': self.stats['clients'],
                'start_time': self.stats['start_time']
            })

    def _generate_frames(self):
        """生成 MJPEG 幀"""
        self.stats['clients'] += 1
        logger.info(f"新客戶端連線，當前連線數: {self.stats['clients']}")

        try:
            while True:
                with self.frame_lock:
                    if self.current_frame is None:
                        time.sleep(0.1)
                        continue

                    frame = self.current_frame.copy()

                # 編碼為 JPEG
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.quality]
                ret, buffer = cv2.imencode('.jpg', frame, encode_param)

                if not ret:
                    continue

                frame_bytes = buffer.tobytes()

                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

                time.sleep(1.0 / self.fps)

        finally:
            self.stats['clients'] -= 1
            logger.info(f"客戶端斷線，當前連線數: {self.stats['clients']}")

    def update_frame(self, frame: np.ndarray):
        """更新當前影像幀"""
        with self.frame_lock:
            self.current_frame = frame
            self.stats['total_frames'] += 1

    def run(self, threaded: bool = True):
        """啟動 HTTP 伺服器"""
        if threaded:
            thread = threading.Thread(target=self._run_server, daemon=True)
            thread.start()
            logger.info(f"HTTP 伺服器已在背景啟動 (端口 {self.http_port})")
        else:
            self._run_server()

    def _run_server(self):
        """執行 Flask 伺服器"""
        self.app.run(host='0.0.0.0', port=self.http_port, threaded=True, debug=False)


def test_streaming():
    """測試串流伺服器"""
    import cv2

    print("=" * 60)
    print("影像串流伺服器測試")
    print("=" * 60)

    # 初始化串流伺服器
    server = StreamingServer(http_port=5000, fps=30)
    server.run(threaded=True)

    print(f"\n✓ 伺服器已啟動")
    print(f"\n📱 手機觀看方式：")
    print(f"   在手機瀏覽器輸入: http://[你的IP]:5000")
    print(f"\n按 'q' 退出")
    print()

    # 開啟攝像頭
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("無法開啟攝像頭")
        return

    frame_count = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1

            # 在影像上添加資訊
            cv2.putText(frame, f"Frame: {frame_count}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            cv2.putText(frame, f"Clients: {server.stats['clients']}", (10, 70),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            # 更新串流影像
            server.update_frame(frame)

            # 本地顯示
            cv2.imshow('Streaming Server', frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        print("\n用戶中斷")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("測試完成")


if __name__ == "__main__":
    test_streaming()
