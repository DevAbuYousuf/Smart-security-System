
"""
Lightweight MJPEG camera streaming and live statistics server for SmartGuard.

The AI application publishes processed frames, detection counters,
and live person recognition information.
This module does NOT open the webcam.
"""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import cv2


_data_lock = threading.Lock()

_latest_jpeg = None

_latest_stats = {
    "detectedPeople": 0,
    "currentInside": 0,
    "totalEntry": 0,
    "totalExit": 0,
    "cameraId": "CAMERA_01",
    "updatedAt": None,
    "livePersons": [],
}

_http_server = None
_server_thread = None


def update_frame(frame):
    """Encode and publish the latest processed OpenCV frame."""
    global _latest_jpeg

    if frame is None:
        return

    success, encoded = cv2.imencode(
        ".jpg",
        frame,
        [int(cv2.IMWRITE_JPEG_QUALITY), 75],
    )

    if not success:
        return

    with _data_lock:
        _latest_jpeg = encoded.tobytes()


def update_stats(
    detected_people,
    current_inside,
    total_entry,
    total_exit,
    live_people=None,
):
    """Publish live AI statistics and person recognition information."""
    global _latest_stats

    stats = {
        "detectedPeople": int(detected_people),
        "currentInside": int(current_inside),
        "totalEntry": int(total_entry),
        "totalExit": int(total_exit),
        "cameraId": "CAMERA_01",
        "updatedAt": time.time(),
        "livePersons": live_people if live_people is not None else [],
    }

    with _data_lock:
        _latest_stats = stats


class _StreamHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        request_path = urlparse(self.path).path

        if request_path == "/health":
            body = b"SmartGuard camera stream is running."

            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
            return

        if request_path == "/stats":
            with _data_lock:
                stats = dict(_latest_stats)

            body = json.dumps(stats).encode("utf-8")

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header(
                "Cache-Control",
                "no-cache, no-store, must-revalidate",
            )
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
            return

        if request_path != "/video_feed":
            self.send_response(404)
            self.end_headers()
            return

        self.send_response(200)
        self.send_header(
            "Content-Type",
            "multipart/x-mixed-replace; boundary=frame",
        )
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Connection", "close")
        self.end_headers()

        try:
            while True:
                with _data_lock:
                    jpeg = _latest_jpeg

                if jpeg is not None:
                    self.wfile.write(b"--frame\r\n")
                    self.wfile.write(b"Content-Type: image/jpeg\r\n")
                    self.wfile.write(
                        f"Content-Length: {len(jpeg)}\r\n\r\n".encode("ascii")
                    )
                    self.wfile.write(jpeg)
                    self.wfile.write(b"\r\n")
                    self.wfile.flush()

                time.sleep(0.04)

        except (
            BrokenPipeError,
            ConnectionResetError,
            ConnectionAbortedError,
        ):
            pass

    def log_message(self, format_string, *args):
        return


def start_stream_server(host="0.0.0.0", port=8000):
    """Start the MJPEG HTTP server in a background thread."""
    global _http_server, _server_thread

    if _http_server is not None:
        return

    class ReusableThreadingHTTPServer(ThreadingHTTPServer):
        allow_reuse_address = True
        daemon_threads = True

    _http_server = ReusableThreadingHTTPServer(
        (host, port),
        _StreamHandler,
    )

    _server_thread = threading.Thread(
        target=_http_server.serve_forever,
        name="SmartGuardCameraStream",
        daemon=True,
    )

    _server_thread.start()

    print(f"Camera streaming server started on http://{host}:{port}")


def stop_stream_server():
    """Stop the HTTP server cleanly."""
    global _http_server, _server_thread

    if _http_server is None:
        return

    _http_server.shutdown()
    _http_server.server_close()

    if _server_thread is not None:
        _server_thread.join(timeout=3)

    _http_server = None
    _server_thread = None

    print("Camera streaming server stopped.")
