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
            <html>
            <head>
                <title>🦟 蚊子追蹤系統 - 即時監控</title>
                <link rel="icon" type="image/svg+xml" href="/favicon.ico">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        margin: 0;
                        padding: 20px;
                        background-color: #1a1a1a;
                        color: #fff;
                    }}
                    .container {{
                        max-width: 1200px;
                        margin: 0 auto;
                    }}
                    h1 {{
                        text-align: center;
                        color: #4CAF50;
                    }}
                    .video-container {{
                        position: relative;
                        width: 100%;
                        max-width: 960px;
                        margin: 20px auto;
                        background-color: #000;
                        border: 2px solid #4CAF50;
                        border-radius: 8px;
                        overflow: hidden;
                    }}
                    img {{
                        width: 100%;
                        height: auto;
                        display: block;
                    }}
                    .stats {{
                        background-color: #2d2d2d;
                        padding: 15px;
                        border-radius: 8px;
                        margin-top: 20px;
                    }}
                    .stat-item {{
                        display: inline-block;
                        margin: 10px 20px;
                    }}
                    .stat-label {{
                        color: #888;
                        font-size: 12px;
                    }}
                    .stat-value {{
                        color: #4CAF50;
                        font-size: 24px;
                        font-weight: bold;
                    }}
                    .info {{
                        background-color: #2d2d2d;
                        padding: 15px;
                        border-radius: 8px;
                        margin-top: 20px;
                    }}
                    .info h3 {{
                        margin-top: 0;
                        color: #4CAF50;
                    }}
                    code {{
                        background-color: #1a1a1a;
                        padding: 2px 6px;
                        border-radius: 3px;
                        color: #4CAF50;
                    }}
                    .offline {{
                        text-align: center;
                        padding: 50px;
                        color: #888;
                    }}
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
                            <div class="stat-label">唯一目標</div>
                            <div class="stat-value" id="targets">0</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">追蹤狀態</div>
                            <div class="stat-value" id="status" style="font-size: 18px;">停用</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">FPS</div>
                            <div class="stat-value" id="fps">0.0</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">運行時間</div>
                            <div class="stat-value" id="uptime" style="font-size: 18px;">00:00:00</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">光照 (Lux)</div>
                            <div class="stat-value" id="lux">0</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">光照狀態</div>
                            <div class="stat-value" id="lux-status" style="font-size: 16px;">未知</div>
                        </div>
                    </div>

                    <div class="info">
                        <h3>📱 手機觀看方式</h3>
                        <p><strong>方式 1：區域網路直連（推薦）</strong></p>
                        <p>在手機瀏覽器輸入：<code>{http_direct_url}</code></p>

{external_info}
                        <p style="color: #888; font-size: 12px;">
                            * 區域網路訪問需確保設備與辨識主機在同一網路
                        </p>
                    </div>
                </div>

                <script>
                    console.log("Script loaded");

                    function updateStats() {{
                        console.log("updateStats called");
                        fetch("/stats")
                            .then(response => {{
                                console.log("Response received:", response.status);
                                if (!response.ok) {{
                                    throw new Error("Network response was not ok: " + response.status);
                                }}
                                return response.json();
                            }})
                            .then(data => {{
                                console.log("Stats data:", data);

                                const frames = document.getElementById("frames");
                                const targets = document.getElementById("targets");
                                const status = document.getElementById("status");
                                const fps = document.getElementById("fps");
                                const lux = document.getElementById("lux");
                                const luxStatus = document.getElementById("lux-status");
                                const uptime = document.getElementById("uptime");

                                if (frames) frames.textContent = data.total_frames || 0;
                                if (targets) targets.textContent = data.unique_targets || 0;
                                if (status) status.textContent = data.tracking_active ? "啟用" : "停用";
                                if (fps) fps.textContent = (data.fps || 0).toFixed(1);
                                if (lux) lux.textContent = data.lux || 0;
                                if (luxStatus) luxStatus.textContent = data.lux_status || "未知";

                                if (status) {{
                                    status.style.color = data.tracking_active ? "#4CAF50" : "#888";
                                }}

                                if (luxStatus) {{
                                    if (data.lux_status === "正常") {{
                                        luxStatus.style.color = "#4CAF50";
                                    }} else if (data.lux_status === "偏暗") {{
                                        luxStatus.style.color = "#FFA500";
                                    }} else if (data.lux_status === "過暗") {{
                                        luxStatus.style.color = "#FF5555";
                                    }} else {{
                                        luxStatus.style.color = "#888";
                                    }}
                                }}

                                if (data.start_time && uptime) {{
                                    const elapsed = Math.floor(Date.now() / 1000 - data.start_time);
                                    const hours = Math.floor(elapsed / 3600);
                                    const minutes = Math.floor((elapsed % 3600) / 60);
                                    const seconds = elapsed % 60;
                                    uptime.textContent =
                                        hours.toString().padStart(2, "0") + ":" +
                                        minutes.toString().padStart(2, "0") + ":" +
                                        seconds.toString().padStart(2, "0");
                                }}
                            }})
                            .catch(error => {{
                                console.error("Error fetching stats:", error);
                            }});
                    }}

                    console.log("Starting immediate updates...");
                    updateStats();
                    const interval = setInterval(updateStats, 1000);

                    if (document.readyState === "loading") {{
                        document.addEventListener("DOMContentLoaded", function() {{
                            console.log("DOMContentLoaded fired");
                            updateStats();
                        }});
                    }} else {{
                        console.log("Document already loaded");
                        updateStats();
                    }}
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
                'start_time': self.stats['start_time'],
                'unique_targets': self.stats['unique_targets'],
                'tracking_active': self.stats['tracking_active'],
                'fps': self.stats['fps'],
                'lux': self.stats['lux'],
                'lux_status': self.stats['lux_status']
            })

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
            self.app.run(host='0.0.0.0', port=self.http_port, threaded=True, debug=False)
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
