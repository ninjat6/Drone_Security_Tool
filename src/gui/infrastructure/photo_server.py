"""
照片上傳伺服器模組
提供手機拍照上傳功能的 Flask 伺服器
"""

import os
import socket
import threading
from datetime import datetime

from flask import Flask, request, jsonify, send_from_directory
from wsgiref.simple_server import make_server, WSGIServer
from socketserver import ThreadingMixIn
from PySide6.QtCore import QObject, Signal

from constants import (
    DIR_IMAGES,
    DIR_REPORTS,
    DATE_FMT_PY_FILENAME_SHORT,
    sanitize_filename,
)


class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    """支援多執行緒的 WSGI Server"""
    daemon_threads = True


class PhotoServer(QObject):
    """
    照片上傳伺服器 - 提供手機拍照上傳功能
    
    Signals:
        photo_received: (mode, item_uid, target, full_path, title)
            - mode: 'item' 或 'overview'
            - item_uid: 測項 UID (item 模式) 或 target (overview 模式)
            - target: UAV/GCS/Shared
            - full_path: 儲存的完整路徑
            - title: 使用者輸入的標題
    """
    
    # Signal: mode, item_uid, target, full_path, title
    photo_received = Signal(str, str, str, str, str)

    def __init__(self, port=8000):
        super().__init__()
        self.app = Flask(__name__, static_folder=None)
        self.port = port
        self.project_path = ""
        self.project_name = ""
        self.items = []  # 測項列表
        self.server = None
        self.server_thread = None
        
        # 註冊路由
        self._register_routes()

    def _register_routes(self):
        """註冊 Flask 路由"""
        # 靜態檔案路徑
        static_dir = os.path.dirname(__file__)
        
        @self.app.route("/")
        def index():
            return send_from_directory(static_dir, "mobile.html")
        
        @self.app.route("/api/project")
        def api_project():
            """取得專案資訊和測項列表"""
            return jsonify({
                "name": self.project_name,
                "items": self.items
            })
        
        @self.app.route("/api/upload", methods=["POST"])
        def api_upload():
            """上傳圖片"""
            return self._handle_upload()

    def _handle_upload(self):
        """處理圖片上傳"""
        file = request.files.get("photo")
        if not file:
            return jsonify({"status": "error", "message": "無檔案"}), 400
        
        if not self.project_path:
            return jsonify({"status": "error", "message": "專案未開啟"}), 500
        
        mode = request.form.get("mode", "item")
        title = request.form.get("title", "")
        target = request.form.get("target", "UAV")
        
        try:
            if mode == "overview":
                # 總覽照片：存到 images/
                angle = request.form.get("angle", "front")
                save_dir = os.path.join(self.project_path, DIR_IMAGES)
                os.makedirs(save_dir, exist_ok=True)
                
                filename = f"{target}_{angle}.jpg"
                save_path = os.path.join(save_dir, filename)
                file.save(save_path)
                
                self.photo_received.emit(mode, target, angle, save_path, title)
                
            else:
                # 測項佐證：存到 reports/{item_id}_{item_name}/{target}/
                item_uid = request.form.get("item_uid", "")
                item_id = request.form.get("item_id", "unknown")
                item_name = request.form.get("item_name", "unknown")
                
                # 找到對應的測項取得 targets
                item = next((i for i in self.items if i.get("uid") == item_uid), None)
                targets = item.get("targets", []) if item else []
                
                # 決定資料夾路徑
                safe_name = sanitize_filename(item_name)
                base_folder = f"{item_id}_{safe_name}"
                
                if len(targets) > 1:
                    if target == "Shared":
                        folder = os.path.join(DIR_REPORTS, base_folder, "Shared")
                    else:
                        folder = os.path.join(DIR_REPORTS, base_folder, target)
                else:
                    folder = os.path.join(DIR_REPORTS, base_folder)
                
                save_dir = os.path.join(self.project_path, folder)
                os.makedirs(save_dir, exist_ok=True)
                
                # 檔名格式：{timestamp}_img_{title}.jpg
                ts = datetime.now().strftime(DATE_FMT_PY_FILENAME_SHORT)
                safe_title = sanitize_filename(title) if title else "photo"
                filename = f"{ts}_img_{safe_title}.jpg"
                
                # 防止覆蓋
                save_path = os.path.join(save_dir, filename)
                if os.path.exists(save_path):
                    ts_sec = datetime.now().strftime("%H%M%S")
                    filename = f"{ts}_img_{safe_title}_{ts_sec}.jpg"
                    save_path = os.path.join(save_dir, filename)
                
                file.save(save_path)
                
                self.photo_received.emit(mode, item_uid, target, save_path, title)
            
            return jsonify({"status": "success"})
            
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    def start(self):
        """啟動伺服器"""
        if self.server is not None:
            return
        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()

    def stop(self):
        """停止伺服器"""
        if self.server:
            try:
                self.server.shutdown()
            except Exception as e:
                print(f"Error stopping server: {e}")
        if self.server_thread:
            self.server_thread.join(timeout=1.0)
            self.server_thread = None

    def _run_server(self):
        """執行伺服器 (背景執行緒)"""
        try:
            self.server = make_server(
                "0.0.0.0", self.port, self.app, server_class=ThreadingWSGIServer
            )
            self.server.serve_forever()
        except OSError as e:
            print(f"Web Server Error: {e}")
        except Exception as e:
            print(f"Web Server Start Failed: {e}")
        finally:
            if self.server:
                self.server.server_close()
            self.server = None

    def is_running(self):
        """檢查伺服器是否執行中"""
        return self.server is not None

    def set_project(self, path: str, name: str, items: list):
        """
        設定專案資訊
        
        Args:
            path: 專案路徑
            name: 專案名稱
            items: 測項列表 [{"uid": "...", "id": "...", "name": "...", "targets": [...]}]
        """
        self.project_path = path
        self.project_name = name
        self.items = items

    def get_local_ip(self):
        """取得本機 IP"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def get_url(self):
        """取得連線 URL"""
        return f"http://{self.get_local_ip()}:{self.port}/"
    
    def get_all_ips(self):
        """取得所有可用 IP"""
        ips = []
        try:
            import netifaces
            for iface in netifaces.interfaces():
                addrs = netifaces.ifaddresses(iface)
                if netifaces.AF_INET in addrs:
                    for addr in addrs[netifaces.AF_INET]:
                        ip = addr.get("addr")
                        if ip and not ip.startswith("127."):
                            ips.append(ip)
        except:
            # 如果 netifaces 不可用，使用舊方法
            ips.append(self.get_local_ip())
        return ips if ips else [self.get_local_ip()]

    # ========== 舊 API 相容性 ==========
    
    def set_save_directory(self, path):
        """設定儲存目錄（相容舊 API）"""
        # 新設計直接使用 project_path，此方法保留相容性
        pass
    
    def generate_token(self, target_id, target_name, is_report=False):
        """產生 token（相容舊 API）"""
        # 新設計不需要 token，直接回傳 URL
        return self.get_url()

