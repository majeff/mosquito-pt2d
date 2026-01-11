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
影像串流伺服器
支援 HTTP-MJPEG 串流（RTSP 需額外安裝 MediaMTX + FFmpeg）
"""

import cv2
import numpy as np
import os
import sys
import subprocess
import shutil
from flask import Flask, Response, render_template_string, jsonify, send_from_directory
import threading
import time
import logging
from typing import Optional
from pathlib import Path
try:
    from config_loader import config  # 使用新的配置加載模組
    DEFAULT_DEVICE_IP = config.device_ip
    DEFAULT_EXTERNAL_URL = config.external_url
except ImportError:
    DEFAULT_DEVICE_IP = None
    DEFAULT_EXTERNAL_URL = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StreamingServer:
    """影像串流伺服器（HTTP-MJPEG）

    特色：
    - 完整支援 AI 即時標註（檢測框、信心度、追蹤狀態）
    - 支援雙目攝像頭（並排顯示、獨立串流、切換視角）
    - 低延遲 MJPEG 串流
    - 多客戶端同時觀看

    RTSP 支援：
    - 需要安裝 MediaMTX (RTSP 伺服器) + FFmpeg
    - 使用 enable_rtsp_push() 方法啟動推流
    - 參考文檔: docs/STREAMING_GUIDE.md
    """

    def __init__(self,
                 http_port: int = 5000,
                 fps: int = 30,
                 quality: int = 85,
                 device_ip: Optional[str] = DEFAULT_DEVICE_IP,
                 external_url: Optional[str] = DEFAULT_EXTERNAL_URL,
                 rtsp_url: Optional[str] = None):
        """
        初始化串流伺服器

        Args:
            http_port: HTTP 伺服器端口
            fps: 串流幀率
            quality: JPEG 壓縮品質 (1-100)
            device_ip: 設備 IP 地址（用於生成訪問說明）
            external_url: 外部訪問 URL（透過 Nginx Reverse Proxy）
            rtsp_url: RTSP 推流目標地址（需先啟動 MediaMTX）
                     例如: "rtsp://0.0.0.0:8554/mosquito" (允許外部訪問)
        """
        self.http_port = http_port
        self.fps = fps
        self.quality = quality
        self.device_ip = device_ip
        self.external_url = external_url
        self.rtsp_url = rtsp_url

        # 當前影像（線程安全）
        self.current_frame = None
        self.frame_lock = threading.Lock()

        # 統計資訊
        self.stats = {
            'total_frames': 0,
            'rtsp_enabled': False,
            'start_time': time.time(),
            'unique_targets': 0,
            'tracking_active': False,
            'fps': 0.0,
            'lux': 0,
            'lux_status': 'Unknown'
        }

        # Flask APP
        self.app = Flask(__name__)
        self._setup_routes()

        # RTSP 推流進程
        self.rtsp_process = None
        self.rtsp_frame_size = None

        logger.info(f"串流伺服器已初始化")
        logger.info(f"HTTP MJPEG: http://0.0.0.0:{http_port}/video")
        if rtsp_url:
            logger.info(f"RTSP 目標: {rtsp_url} (使用 enable_rtsp_push() 啟動)")

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
            <html lang="zh-TW">
            <head>
                <title>🦟 蚊子追蹤系統 - 即時監控</title>
                <link rel="icon" type="image/svg+xml" href="/favicon.ico">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <meta charset="UTF-8">
                <script src="https://code.jquery.com/jquery-3.6.4.min.js"></script>
                <style>
                    :root {{
                        --primary: #4CAF50;
                        --bg-dark: #1a1a1a;
                        --bg-card: #2d2d2d;
                        --text-light: #fff;
                        --text-dim: #888;
                    }}

                    * {{
                        margin: 0;
                        padding: 0;
                        box-sizing: border-box;
                    }}

                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        background-color: var(--bg-dark);
                        color: var(--text-light);
                        line-height: 1.6;
                    }}

                    .container {{
                        max-width: 1200px;
                        margin: 0 auto;
                        padding: 20px;
                    }}

                    h1 {{
                        text-align: center;
                        color: var(--primary);
                        margin-bottom: 30px;
                        font-size: 2.5em;
                    }}

                    .video-container {{
                        position: relative;
                        width: 100%;
                        aspect-ratio: 16 / 9;
                        max-width: 960px;
                        margin: 20px auto;
                        background-color: #000;
                        border: 3px solid var(--primary);
                        border-radius: 12px;
                        overflow: hidden;
                        box-shadow: 0 8px 32px rgba(76, 175, 80, 0.1);
                    }}

                    .video-container img {{
                        width: 100%;
                        height: 100%;
                        object-fit: contain;
                    }}

                    .stats-grid {{
                        display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                        gap: 15px;
                        margin-top: 30px;
                    }}

                    .stat-card {{
                        background-color: var(--bg-card);
                        padding: 20px;
                        border-radius: 8px;
                        border-left: 4px solid var(--primary);
                        transition: transform 0.2s;
                    }}

                    .stat-card:hover {{
                        transform: translateY(-2px);
                    }}

                    .stat-label {{
                        color: var(--text-dim);
                        font-size: 0.9em;
                        text-transform: uppercase;
                        letter-spacing: 0.5px;
                        margin-bottom: 8px;
                    }}

                    .stat-value {{
                        color: var(--primary);
                        font-size: 2em;
                        font-weight: bold;
                        font-variant-numeric: tabular-nums;
                    }}

                    .info-section {{
                        background-color: var(--bg-card);
                        padding: 25px;
                        border-radius: 8px;
                        margin-top: 30px;
                    }}

                    .info-section h3 {{
                        margin-top: 0;
                        color: var(--primary);
                        margin-bottom: 15px;
                    }}

                    .info-section p {{
                        margin: 10px 0;
                    }}

                    code {{
                        background-color: #1a1a1a;
                        padding: 4px 8px;
                        border-radius: 4px;
                        color: var(--primary);
                        font-family: 'Courier New', monospace;
                        font-size: 0.95em;
                    }}

                    .copy-btn {{
                        background-color: var(--primary);
                        color: #000;
                        border: none;
                        padding: 6px 12px;
                        border-radius: 4px;
                        cursor: pointer;
                        font-size: 0.85em;
                        margin-left: 10px;
                        transition: background-color 0.2s;
                    }}

                    .copy-btn:hover {{
                        background-color: #45a049;
                    }}

                    .hint {{
                        color: var(--text-dim);
                        font-size: 0.85em;
                        margin-top: 10px;
                    }}

                    .status-indicator {{
                        display: inline-block;
                        width: 12px;
                        height: 12px;
                        border-radius: 50%;
                        margin-right: 8px;
                        vertical-align: middle;
                        animation: pulse 2s infinite;
                    }}

                    .status-active {{
                        background-color: var(--primary);
                    }}

                    .status-idle {{
                        background-color: var(--text-dim);
                    }}

                    @keyframes pulse {{
                        0%, 100% {{ opacity: 1; }}
                        50% {{ opacity: 0.5; }}
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🦟 蚊子追蹤系統</h1>

                    <div class="video-container">
                        <img id="stream" src="/video" alt="即時影像串流" onerror="this.alt='串流連線中斷'">
                    </div>

                    <div class="stats-grid" id="stats-grid">
                        <div class="stat-card">
                            <div class="stat-label">唯一目標</div>
                            <div class="stat-value" id="targets">-</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">追蹤狀態</div>
                            <div class="stat-value" id="status">
                                <span class="status-indicator status-idle"></span>停用
                            </div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">FPS</div>
                            <div class="stat-value" id="fps">-</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">光照 (Lux)</div>
                            <div class="stat-value" id="lux">-</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">總幀數</div>
                            <div class="stat-value" id="frames">-</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">運行時間</div>
                            <div class="stat-value" id="uptime">-</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">中信心度樣本</div>
                            <div class="stat-value" id="samples">-</div>
                        </div>
                    </div>

                    <div class="info-section">
                        <h3>📱 訪問方式</h3>
                        <p><strong>本機訪問：</strong> <code>http://localhost:{self.http_port}</code></p>
                        <p><strong>區域網路：</strong> <code>{http_direct_url}</code></p>
{external_info}
                        <p class="hint">✓ 設備需與監控主機在同一網路上</p>
                    </div>
                </div>

                <script>
                    $(document).ready(function() {{
                        function formatTime(seconds) {{
                            const h = Math.floor(seconds / 3600);
                            const m = Math.floor((seconds % 3600) / 60);
                            const s = Math.floor(seconds % 60);
                            return String(h).padStart(2, '0') + ':' +
                                   String(m).padStart(2, '0') + ':' +
                                   String(s).padStart(2, '0');
                        }}

                        function updateStats() {{
                            $.ajax({{
                                url: '/stats',
                                type: 'GET',
                                cache: false,
                                dataType: 'json',
                                timeout: 5000,
                                success: function(data) {{
                                    $('#targets').text(data.unique_targets || '-');
                                    $('#fps').text((data.fps || 0).toFixed(1));
                                    $('#lux').text(data.lux || '-');
                                    $('#frames').text(data.total_frames || '-');
                                    $('#uptime').text(formatTime(data.elapsed_time || 0));
                                    $('#samples').text(data.samples_saved || '-');

                                    const isActive = data.tracking_active;
                                    const statusClass = isActive ? 'status-active' : 'status-idle';
                                    const statusText = isActive ? '啟用' : '停用';
                                    $('#status').html('<span class="status-indicator ' + statusClass + '"></span>' + statusText);
                                }},
                                error: function(jqXHR, textStatus, errorThrown) {{
                                    console.warn('Stats update failed:', textStatus);
                                }}
                            }});
                        }}

                        // 立即執行一次
                        updateStats();

                        // 每 1000ms 執行一次
                        setInterval(updateStats, 1000);
                    }});
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
            response = jsonify({
                'total_frames': self.stats['total_frames'],
                'start_time': self.stats['start_time'],
                'unique_targets': self.stats['unique_targets'],
                'tracking_active': self.stats['tracking_active'],
                'fps': self.stats['fps'],
                'lux': self.stats['lux'],
                'lux_status': self.stats['lux_status']
            })
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            return response

        @self.app.route('/favicon.ico')
        def favicon():
            """提供網站圖標"""
            static_folder = os.path.join(os.path.dirname(__file__), 'static')
            if os.path.exists(os.path.join(static_folder, 'favicon.svg')):
                return send_from_directory(static_folder, 'favicon.svg', mimetype='image/svg+xml')
            # 如果找不到 SVG，返回空響應避免 404 錯誤
            return '', 204

    def _generate_frames(self):
        """生成 MJPEG 幀"""
        logger.info(f"新客戶端連線")

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
            logger.info(f"客戶端斷線")

    def update_frame(self, frame: np.ndarray):
        """更新當前影像幀（同時推送到 HTTP 和 RTSP）"""
        with self.frame_lock:
            self.current_frame = frame
            self.stats['total_frames'] += 1

        # 推送到 RTSP（如已啟用）
        if self.rtsp_process and self.stats['rtsp_enabled']:
            try:
                self.rtsp_process.stdin.write(frame.tobytes())
            except (BrokenPipeError, IOError):
                logger.warning("RTSP 推流中斷")
                self.stats['rtsp_enabled'] = False

    def update_stats(self, unique_targets: int = None, tracking_active: bool = None,
                    fps: float = None, lux: int = None, lux_status: str = None):
        """更新統計資訊

        Args:
            unique_targets: 唯一目標數量
            tracking_active: 追蹤是否啟用
            fps: 當前 FPS
            lux: 光照度
            lux_status: 光照狀態 ('正常', '偏暗', '過暗', '未知')
        """
        if unique_targets is not None:
            self.stats['unique_targets'] = unique_targets
        if tracking_active is not None:
            self.stats['tracking_active'] = tracking_active
        if fps is not None:
            self.stats['fps'] = fps
        if lux is not None:
            self.stats['lux'] = lux
        if lux_status is not None:
            self.stats['lux_status'] = lux_status

    def enable_rtsp_push(self, frame_width: int, frame_height: int,
                         bitrate: int = 2000, preset: str = 'ultrafast'):
        """
        啟動 RTSP 推流（需要先安裝 MediaMTX 和 FFmpeg）

        Args:
            frame_width: 影像寬度
            frame_height: 影像高度
            bitrate: 視頻碼率 (kbps)，建議 1000-3000
            preset: FFmpeg 編碼預設 (ultrafast/superfast/veryfast/faster/fast)

        Returns:
            bool: 是否成功啟動

        使用範例:
            server = StreamingServer(rtsp_url="rtsp://0.0.0.0:8554/mosquito")
            server.enable_rtsp_push(1920, 1080)
        """
        if not self.rtsp_url:
            logger.error("RTSP URL 未設定，無法啟動推流")
            return False

        # 檢查 FFmpeg 是否安裝
        if not shutil.which('ffmpeg'):
            logger.error("❌ FFmpeg 未安裝！")
            logger.error("請先安裝：")
            logger.error("  Ubuntu/Debian: sudo apt install ffmpeg")
            logger.error("  Orange Pi: sudo apt install ffmpeg")
            logger.error("  Windows: 從 https://ffmpeg.org/download.html 下載")
            return False

        logger.info(f"正在啟動 RTSP 推流到 {self.rtsp_url}")
        logger.info(f"解析度: {frame_width}x{frame_height}, FPS: {self.fps}, 碼率: {bitrate}kbps")

        self.rtsp_frame_size = (frame_width, frame_height)

        # 構建 FFmpeg 推流命令
        ffmpeg_cmd = [
            'ffmpeg',
            '-y',                                    # 覆蓋輸出
            '-f', 'rawvideo',                        # 輸入格式
            '-vcodec', 'rawvideo',
            '-pix_fmt', 'bgr24',                     # OpenCV 格式
            '-s', f'{frame_width}x{frame_height}',   # 影像尺寸
            '-r', str(self.fps),                     # 幀率
            '-i', '-',                               # 從 stdin 讀取
            '-c:v', 'libx264',                       # H.264 編碼
            '-preset', preset,                       # 編碼速度預設
            '-tune', 'zerolatency',                  # 低延遲
            '-b:v', f'{bitrate}k',                   # 碼率
            '-f', 'rtsp',                            # 輸出格式
            self.rtsp_url                            # RTSP 目標地址
        ]

        try:
            # 啟動 FFmpeg 進程
            logger.info(f"執行: {' '.join(ffmpeg_cmd[:10])}...")
            self.rtsp_process = subprocess.Popen(
                ffmpeg_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=False
            )

            # 給 FFmpeg 一點時間初始化
            time.sleep(1)

            # 檢查進程是否還在運行
            if self.rtsp_process.poll() is not None:
                # 進程已退出，獲取錯誤信息
                _, stderr = self.rtsp_process.communicate(timeout=1)
                error_msg = stderr.decode('utf-8', errors='ignore') if stderr else "未知錯誤"
                logger.error(f"❌ FFmpeg 啟動失敗:")
                logger.error(f"{error_msg}")
                logger.error(f"⚠️  請檢查：")
                logger.error(f"  1. MediaMTX 是否在運行？(應該在 {self.rtsp_url.split(':')[0]}:{self.rtsp_url.split('/')[2].split(':')[1]} 監聽)")
                logger.error(f"  2. RTSP URL 是否正確？")
                logger.error(f"  3. FFmpeg 版本是否支援 RTSP？")
                self.rtsp_process = None
                return False

            self.stats['rtsp_enabled'] = True
            logger.info(f"✅ RTSP 推流已啟動！")
            logger.info(f"   目標: {self.rtsp_url}")
            return True

        except Exception as e:
            logger.error(f"❌ RTSP 推流啟動失敗: {e}")
            logger.error(f"⚠️  請檢查：")
            logger.error(f"  1. MediaMTX 是否安裝並運行？")
            logger.error(f"  2. FFmpeg 是否安裝？")
            logger.error(f"  3. RTSP 地址是否正確？")
            self.rtsp_process = None
            return False

    def disable_rtsp_push(self):
        """停止 RTSP 推流"""
        if self.rtsp_process:
            try:
                self.rtsp_process.stdin.close()
                self.rtsp_process.terminate()
                self.rtsp_process.wait(timeout=3)
            except:
                self.rtsp_process.kill()
            finally:
                self.rtsp_process = None
                self.stats['rtsp_enabled'] = False
                logger.info("RTSP 推流已停止")

    def cleanup(self):
        """清理資源（關閉 RTSP 推流）"""
        self.disable_rtsp_push()

    def run(self, threaded: bool = True):
        """啟動 HTTP 伺服器"""
        if threaded:
            self.server_thread = threading.Thread(target=self._run_server, daemon=True)
            self.server_thread.start()
            logger.info(f"HTTP 伺服器已在背景啟動 (端口 {self.http_port})")
        else:
            self._run_server()

    def _run_server(self):
        """執行 Flask 伺服器"""
        try:
            # 禁用 Werkzeug 請求日誌
            log = logging.getLogger('werkzeug')
            log.setLevel(logging.ERROR)

            # 禁用 Flask 應用日誌（除了錯誤）
            self.app.logger.setLevel(logging.ERROR)

            self.app.run(host='0.0.0.0', port=self.http_port, threaded=True, debug=False, use_reloader=False)
        except Exception as e:
            logger.error(f"串流伺服器錯誤: {e}")

    def shutdown(self):
        """優雅關閉伺服器"""
        logger.info(f"正在關閉伺服器 (端口 {self.http_port})...")
        try:
            # 使用 werkzeug 伺服器關閉機制
            func = self.app.wsgi_app.server.shutdown
            if func:
                func()
        except:
            pass


def test_streaming():
    """測試串流伺服器（HTTP-MJPEG，無本機顯示）"""

    logger.info("=" * 60)
    logger.info("影像串流伺服器測試（遠端模式）")
    logger.info("=" * 60)

    # 初始化串流伺服器
    server = StreamingServer(http_port=5000, fps=30)
    server.run(threaded=True)

    logger.info(f"\n✓ 伺服器已啟動")
    logger.info(f"\n📱 觀看方式：")
    logger.info(f"   在瀏覽器輸入: http://[伺服器IP]:5000")
    logger.info(f"\n按 Ctrl+C 退出")

    # 開啟攝像頭
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        logger.error("無法開啟攝像頭")
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

            # 更新串流影像
            server.update_frame(frame)

            # 每 100 幀輸出一次狀態
            if frame_count % 100 == 0:
                logger.info(f"幀數: {frame_count}")

            # 短暫休眠以控制幀率
            time.sleep(1.0 / server.fps)

    except KeyboardInterrupt:
        logger.info("\n用戶中斷")
    finally:
        cap.release()
        logger.info("測試完成")


def test_rtsp_streaming():
    """測試 RTSP 串流（需先啟動 MediaMTX，無本機顯示）"""

    logger.info("=" * 60)
    logger.info("RTSP 串流測試（遠端模式）")
    logger.info("=" * 60)
    logger.info("")
    logger.info("⚠️  請確認已啟動 MediaMTX:")
    logger.info("   ./mediamtx")
    logger.info("")
    input("按 Enter 繼續...")

    # 初始化串流伺服器（HTTP + RTSP）
    server = StreamingServer(
        http_port=5000,
        fps=30,
        rtsp_url="rtsp://0.0.0.0:8554/mosquito"
    )
    server.run(threaded=True)

    # 開啟攝像頭
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        logger.error("無法開啟攝像頭")
        return

    # 獲取影像尺寸
    ret, frame = cap.read()
    if not ret:
        logger.error("無法讀取影像")
        return

    height, width = frame.shape[:2]

    # 啟動 RTSP 推流
    logger.info(f"\n啟動 RTSP 推流 ({width}x{height})...")
    if server.enable_rtsp_push(width, height, bitrate=2000):
        logger.info(f"\n✓ RTSP 串流已啟動")
        logger.info(f"\n📱 觀看方式：")
        logger.info(f"   HTTP-MJPEG: http://[伺服器IP]:5000")
        logger.info(f"   RTSP: rtsp://[伺服器IP]:8554/mosquito")
        logger.info(f"\n🎬 RTSP 播放器：")
        logger.info(f"   - VLC Media Player")
        logger.info(f"   - 手機 APP: RTSP Player, VLC for Mobile")
        logger.info(f"\n按 Ctrl+C 退出")
    else:
        logger.warning("\n✗ RTSP 推流啟動失敗，僅運行 HTTP-MJPEG")

    frame_count = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1

            # 添加資訊
            cv2.putText(frame, f"Frame: {frame_count}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(frame, f"RTSP: {'ON' if server.stats['rtsp_enabled'] else 'OFF'}",
                       (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                       (0, 255, 0) if server.stats['rtsp_enabled'] else (0, 0, 255), 2)

            # 更新串流（同時推送到 HTTP 和 RTSP）
            server.update_frame(frame)

            # 每 100 幀輸出一次狀態
            if frame_count % 100 == 0:
                rtsp_status = "ON" if server.stats['rtsp_enabled'] else "OFF"
                logger.info(f"幀數: {frame_count}, RTSP: {rtsp_status}")

            # 短暫休眠以控制幀率
            time.sleep(1.0 / server.fps)

    except KeyboardInterrupt:
        logger.info("\n用戶中斷")
    finally:
        server.cleanup()
        cap.release()
        logger.info("測試完成")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "rtsp":
        test_rtsp_streaming()
    else:
        test_streaming()
