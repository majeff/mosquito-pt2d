#!/usr/bin/env python3
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
以串流輸出執行蚊子追蹤系統
- 啟動 HTTP-MJPEG 串流伺服器
- 將 MosquitoTracker 的結果畫面推送到 /video

使用方式：
    python run_tracker_stream.py
或指定串口：
    python run_tracker_stream.py COM3
"""

import sys
import time
from streaming_server import StreamingServer
from mosquito_tracker import MosquitoTracker
from config import (
    DEFAULT_STREAM_PORT,
    DEFAULT_STREAM_FPS,
    DEFAULT_STREAM_QUALITY,
)


def main():
    # 決定 Arduino 串口（Windows 預設 COM3，Linux/OPi 可自行改）
    default_port = 'COM3' if sys.platform.startswith('win') else '/dev/ttyUSB0'
    arduino_port = sys.argv[1] if len(sys.argv) > 1 else default_port

    # 啟動串流伺服器
    server = StreamingServer(
        http_port=DEFAULT_STREAM_PORT,
        fps=DEFAULT_STREAM_FPS,
        quality=DEFAULT_STREAM_QUALITY,
    )
    server.run(threaded=True)

    print(f"\n✓ 串流伺服器已啟動：http://[你的IP]:{DEFAULT_STREAM_PORT}\n")

    # 建立追蹤器（傳入 streaming_server）
    tracker = MosquitoTracker(
        arduino_port=arduino_port,
        camera_left_id=0,
        camera_right_id=1,
        camera_width=1920,
        camera_height=1080,
        streaming_server=server,
    )

    try:
        tracker.run()
    finally:
        # 程式結束時清理
        try:
            server.cleanup()
        except Exception:
            pass


if __name__ == "__main__":
    main()
