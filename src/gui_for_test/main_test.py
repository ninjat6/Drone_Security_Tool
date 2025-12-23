import sys
import json
import os
import shutil
import socket
import uuid
import threading
import requests
from datetime import datetime
from functools import partial
from io import BytesIO
from typing import Dict, List, Optional, Tuple, Any

# 引入 Flask 與 Werkzeug server (關鍵修改)
from flask import Flask, request, jsonify, render_template_string
from werkzeug.serving import make_server

# 引入 QR Code 與圖片處理
import qrcode
# 注意: PIL 在較新版本中建議使用 Pillow
from PIL import ImageQt

# 引入 PySide6
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QStackedWidget, QMessageBox, QLabel, QDialog, QFormLayout,
    QLineEdit, QDateEdit, QToolButton, QDialogButtonBox, QFileDialog,
    QTextEdit, QGroupBox, QCheckBox, QProgressBar, QFrame, QScrollArea,
    QComboBox, QSizePolicy, QListWidget, QListWidgetItem, QGridLayout
)
from PySide6.QtCore import Qt, QDate, QObject, Signal, Slot, QUrl
from PySide6.QtGui import QPixmap, QShortcut, QKeySequence, QImage, QDesktopServices

# ==============================================================================
# SECTION 1: CONFIGURATION & CONSTANTS
# ==============================================================================

# 檔案系統設定
CONFIG_FILENAME = "standard_config.json"
PROJECT_SETTINGS_FILENAME = "project_settings.json"
DIR_IMAGES = "images"
DIR_REPORTS = "reports"
DEFAULT_DESKTOP_PATH = os.path.join(os.path.expanduser("~"), "Desktop")

# 專案類型與預設值
PROJECT_TYPE_FULL = "full"
PROJECT_TYPE_ADHOC = "ad_hoc"
DEFAULT_TESTER_NAME = "QuickUser"
DEFAULT_ADHOC_PREFIX = "ADHOC"

# 日期格式
DATE_FMT_PY_DATE = "%Y-%m-%d"
DATE_FMT_PY_DATETIME = "%Y-%m-%d %H:%M:%S"
DATE_FMT_PY_FILENAME = "%Y%m%d_%H%M%S"
DATE_FMT_PY_FILENAME_SHORT = "%Y%m%d_%H%M"
DATE_FMT_QT = "yyyy-MM-dd"

# 檢測狀態常數
STATUS_PASS = "合格 (Pass)"
STATUS_FAIL = "不合格 (Fail)"
STATUS_NA = "不適用 (N/A)"
STATUS_UNCHECKED = "未判定"
STATUS_NOT_TESTED = "未檢測"
STATUS_UNKNOWN = "Unknown"

# 顏色配置 (HEX)
COLOR_BG_PASS = "#d4edda"
COLOR_BG_FAIL = "#f8d7da"
COLOR_BG_NA = "#e2e3e5"
COLOR_BG_DEFAULT = "#dddddd"

COLOR_TEXT_PASS = "#155724"
COLOR_TEXT_FAIL = "#721c24"
COLOR_TEXT_NORMAL = "#333333"
COLOR_TEXT_WHITE = "white"
COLOR_TEXT_GRAY = "#666666"

COLOR_BTN_ACTIVE = "#2196F3"
COLOR_BTN_HOVER = "#1976D2"

# 照片視角與目標定義
TARGET_UAV = "uav"
TARGET_GCS = "gcs"
TARGETS = [TARGET_UAV, TARGET_GCS]

PHOTO_ANGLES_ORDER = ["front", "back", "side1", "side2", "top", "bottom"]
PHOTO_ANGLES_NAME = {
    "front": "正面 (Front)",
    "back": "背面 (Back)",
    "side1": "側面1 (Side 1)",
    "side2": "側面2 (Side 2)",
    "top": "上方 (Top)",
    "bottom": "下方 (Bottom)"
}

# 手機端 HTML 模板 (V7 功能增強版：加入顏色與粗細控制)
MOBILE_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-Hant">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
    <title>Photo Helper</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/cropperjs/1.5.13/cropper.min.css">
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; 
            margin: 0; padding: 0; 
            background: #f8f9fa; color: #333;
            overscroll-behavior-y: contain;
        }
        
        .container {
            max-width: 100%;
            padding: 15px;
            padding-bottom: 60px;
            box-sizing: border-box;
        }

        h3 { margin-top: 0; text-align: center; font-size: 1.2rem; }

        /* 按鈕樣式 */
        .btn {
            display: block; width: 100%; padding: 12px; margin: 8px 0;
            font-size: 16px; font-weight: bold; color: white;
            border: none; border-radius: 8px; cursor: pointer; text-align: center;
        }
        .btn-primary { background-color: #007bff; }
        .btn-success { background-color: #28a745; }
        .btn-danger { background-color: #dc3545; }
        .btn-secondary { background-color: #6c757d; }
        .btn-outline { background-color: transparent; border: 1px solid #666; color: #666; }
        .btn:disabled { background-color: #ccc; cursor: not-allowed; }

        .btn-row { display: flex; gap: 10px; margin-bottom: 10px; }
        .btn-row .btn { margin: 0; }

        select {
            width: 100%; padding: 10px; font-size: 16px;
            border-radius: 6px; border: 1px solid #ccc; background: white; margin-bottom: 15px;
        }

        /* 控制面板 (顏色/粗細) */
        .controls-panel {
            background: #fff; border: 1px solid #ddd; border-radius: 8px;
            padding: 10px; margin-bottom: 10px;
            display: flex; align-items: center; justify-content: space-between; gap: 10px;
        }
        .control-item { display: flex; align-items: center; gap: 5px; font-size: 14px; font-weight: bold; }
        
        input[type="color"] {
            border: none; width: 40px; height: 35px; cursor: pointer; background: none;
        }
        input[type="range"] {
            width: 100px;
        }

        /* 步驟容器 */
        #step1-crop, #step2-draw { display: none; }
        
        .img-container {
            width: 100%; height: 55vh; background-color: #333;
            overflow: hidden; border-radius: 8px; margin-bottom: 10px;
        }
        #image-to-crop { max-width: 100%; display: block; }

        .canvas-wrapper {
            width: 100%; overflow: hidden; border: 2px solid #ddd;
            border-radius: 8px; background-color: #fff; margin-bottom: 10px;
            display: flex; justify-content: center;
        }

        #status { text-align: center; font-weight: bold; margin-bottom: 10px; color: #666; min-height: 20px; }
        .hint { font-size: 12px; color: #888; text-align: center; margin-bottom: 5px; }
    </style>
</head>
<body>

<div class="container">
    <h3 id="page-title">Loading...</h3>
    <div id="status"></div>

    <div id="step0-select">
        <div id="category-section" style="display:none;">
            <label>視角 (View):</label>
            <select id="category-select">
                <option value="front">正面 (Front)</option>
                <option value="back">背面 (Back)</option>
                <option value="side1">側面1 (Side 1)</option>
                <option value="side2">側面2 (Side 2)</option>
                <option value="top">上方 (Top)</option>
                <option value="bottom">下方 (Bottom)</option>
            </select>
        </div>
        
        <input type="file" id="file-input" accept="image/*" style="display:none;">
        <button class="btn btn-primary" onclick="document.getElementById('file-input').click()">
            📷 拍照或選取照片
        </button>
    </div>

    <div id="step1-crop">
        <div class="hint">請縮放或拖曳圖片以進行裁切</div>
        <div class="img-container">
            <img id="image-to-crop" src="">
        </div>
        <div class="btn-row">
            <button class="btn btn-secondary" onclick="resetAll()">取消</button>
            <button class="btn btn-primary" onclick="finishCrop()">下一步: 標記 ➡️</button>
        </div>
    </div>

    <div id="step2-draw">
        <div class="controls-panel">
            <div class="control-item">
                顏色: <input type="color" id="line-color" value="#ff0000">
            </div>
            <div class="control-item">
                粗細: <input type="range" id="line-width" min="1" max="15" value="5">
                <span id="width-val">5</span>
            </div>
        </div>

        <div class="canvas-wrapper">
            <canvas id="fabric-canvas"></canvas>
        </div>

        <div class="btn-row">
            <button class="btn btn-danger" onclick="addRect()">+ 加入框線</button>
            <button class="btn btn-outline" onclick="removeActiveObject()">刪除選取</button>
        </div>

        <div class="btn-row" style="margin-top: 20px;">
            <button class="btn btn-secondary" onclick="backToCrop()">⬅️ 重裁</button>
            <button class="btn btn-success" id="btn-upload" onclick="uploadResult()">☁️ 確認上傳</button>
        </div>
    </div>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/cropperjs/1.5.13/cropper.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/fabric.js/5.3.1/fabric.min.js"></script>

<script>
    const UPLOAD_TOKEN = "{{ token }}";
    const TARGET_NAME = "{{ target_name }}";
    const IS_REPORT_MODE = {{ 'true' if is_report else 'false' }};

    const statusEl = document.getElementById('status');
    const step0 = document.getElementById('step0-select');
    const step1 = document.getElementById('step1-crop');
    const step2 = document.getElementById('step2-draw');
    const imgElement = document.getElementById('image-to-crop');
    
    // 控制項元件
    const colorInput = document.getElementById('line-color');
    const widthInput = document.getElementById('line-width');
    const widthVal = document.getElementById('width-val');

    document.getElementById('page-title').innerText = TARGET_NAME;
    if (IS_REPORT_MODE) {
        document.getElementById('category-section').style.display = 'block';
    }

    let cropper = null;
    let fabricCanvas = null;

    // --- 監聽樣式改變 (即時更新選取物件) ---
    widthInput.addEventListener('input', function() {
        widthVal.innerText = this.value;
        updateActiveObject();
    });
    
    colorInput.addEventListener('input', function() {
        updateActiveObject();
    });

    function updateActiveObject() {
        if (!fabricCanvas) return;
        const activeObj = fabricCanvas.getActiveObject();
        if (activeObj) {
            activeObj.set({
                stroke: colorInput.value,
                strokeWidth: parseInt(widthInput.value, 10)
            });
            fabricCanvas.requestRenderAll();
        }
    }

    // --- 步驟 0: 讀檔 ---
    document.getElementById('file-input').addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            statusEl.innerText = "讀取中...";
            const reader = new FileReader();
            reader.onload = function(evt) {
                imgElement.src = evt.target.result;
                startCropMode();
                statusEl.innerText = "";
            };
            reader.readAsDataURL(file);
        }
        this.value = '';
    });

    // --- 步驟 1: 裁切 ---
    function startCropMode() {
        step0.style.display = 'none';
        step1.style.display = 'block';
        step2.style.display = 'none';

        if (cropper) { cropper.destroy(); }
        setTimeout(() => {
            cropper = new Cropper(imgElement, {
                viewMode: 1,
                dragMode: 'move',
                autoCropArea: 0.9,
                restore: false,
                guides: true,
                center: true,
                highlight: false,
                cropBoxMovable: true,
                cropBoxResizable: true,
                toggleDragModeOnDblclick: false,
            });
        }, 100);
    }

    function finishCrop() {
        if (!cropper) return;
        statusEl.innerText = "處理中...";
        
        const croppedCanvas = cropper.getCroppedCanvas({
            maxWidth: 1600,
            maxHeight: 1600,
            imageSmoothingQuality: 'high',
        });

        if (!croppedCanvas) {
            alert("裁切失敗"); return;
        }

        const croppedImageURL = croppedCanvas.toDataURL('image/jpeg', 0.9);
        startDrawMode(croppedImageURL, croppedCanvas.width, croppedCanvas.height);
    }

    // --- 步驟 2: 繪圖 ---
    function startDrawMode(imageURL, w, h) {
        step1.style.display = 'none';
        step2.style.display = 'block';
        statusEl.innerText = "";

        const containerWidth = document.querySelector('.container').clientWidth - 34; 
        const scaleFactor = containerWidth / w;
        
        const finalWidth = containerWidth;
        const finalHeight = h * scaleFactor;

        if (fabricCanvas) { fabricCanvas.dispose(); }
        
        const canvasEl = document.getElementById('fabric-canvas');
        canvasEl.width = finalWidth;
        canvasEl.height = finalHeight;

        fabricCanvas = new fabric.Canvas('fabric-canvas', {
            width: finalWidth,
            height: finalHeight,
            selection: false
        });

        fabric.Image.fromURL(imageURL, function(img) {
            img.set({
                originX: 'left',
                originY: 'top',
                scaleX: scaleFactor,
                scaleY: scaleFactor,
                selectable: false // 背景不可選
            });
            fabricCanvas.setBackgroundImage(img, fabricCanvas.renderAll.bind(fabricCanvas));
            
            addRect(); // 預設加一個框
        });

        // 當使用者點選某個框時，更新控制面板數值
        fabricCanvas.on('selection:created', syncControls);
        fabricCanvas.on('selection:updated', syncControls);
    }

    function syncControls(e) {
        const obj = e.selected[0];
        if (obj) {
            colorInput.value = obj.stroke;
            widthInput.value = obj.strokeWidth;
            widthVal.innerText = obj.strokeWidth;
        }
    }

    function addRect() {
        if (!fabricCanvas) return;
        
        const rect = new fabric.Rect({
            left: fabricCanvas.width / 4,
            top: fabricCanvas.height / 4,
            width: fabricCanvas.width / 3,
            height: fabricCanvas.height / 3,
            fill: 'transparent',
            stroke: colorInput.value, // 使用當前選擇的顏色
            strokeWidth: parseInt(widthInput.value, 10), // 使用當前粗細
            cornerColor: 'blue',
            cornerSize: 20,
            transparentCorners: false
        });
        
        fabricCanvas.add(rect);
        fabricCanvas.setActiveObject(rect);
    }

    function removeActiveObject() {
        const activeObj = fabricCanvas.getActiveObject();
        if (activeObj) {
            fabricCanvas.remove(activeObj);
        }
    }

    function backToCrop() {
        step2.style.display = 'none';
        step1.style.display = 'block';
    }

    function resetAll() {
        if (confirm("重新選取照片？")) {
            step1.style.display = 'none';
            step2.style.display = 'none';
            step0.style.display = 'block';
            if (cropper) cropper.destroy();
            cropper = null;
            document.getElementById('file-input').value = '';
        }
    }

    // --- 上傳 ---
    function uploadResult() {
        if (!fabricCanvas) return;
        
        fabricCanvas.discardActiveObject(); 
        fabricCanvas.renderAll();

        const dataURL = fabricCanvas.toDataURL({ format: 'jpeg', quality: 0.9 });
        statusEl.innerText = "上傳中...";
        document.getElementById('btn-upload').disabled = true;

        const blob = dataURLtoBlob(dataURL);
        const formData = new FormData();
        formData.append('photo', blob, 'upload.jpg');
        formData.append('token', UPLOAD_TOKEN);
        
        if (IS_REPORT_MODE) {
            formData.append('category', document.getElementById('category-select').value);
        }

        fetch('/upload_endpoint', { method: 'POST', body: formData })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                statusEl.innerText = "✅ 成功";
                statusEl.style.color = "green";
                setTimeout(() => {
                    alert("上傳成功！");
                    resetToStart();
                }, 500);
            } else {
                alert("失敗: " + data.message);
                statusEl.innerText = "";
                document.getElementById('btn-upload').disabled = false;
            }
        })
        .catch(err => {
            alert("網路錯誤");
            statusEl.innerText = "";
            document.getElementById('btn-upload').disabled = false;
        });
    }

    function resetToStart() {
        step1.style.display = 'none';
        step2.style.display = 'none';
        step0.style.display = 'block';
        statusEl.innerText = "";
        document.getElementById('btn-upload').disabled = false;
        document.getElementById('file-input').value = '';
    }

    function dataURLtoBlob(dataurl) {
        var arr = dataurl.split(','), mime = arr[0].match(/:(.*?);/)[1],
            bstr = atob(arr[1]), n = bstr.length, u8arr = new Uint8Array(n);
        while(n--){
            u8arr[n] = bstr.charCodeAt(n);
        }
        return new Blob([u8arr], {type:mime});
    }
</script>
</body>
</html>
"""

# ==============================================================================
# SECTION 2: INFRASTRUCTURE LAYER (基礎設施層)
# ==============================================================================

class PhotoServer(QObject):
    """
    封裝 Flask 伺服器，改寫為使用 werkzeug.serving.make_server
    這樣可以確保呼叫 shutdown() 時能夠真正釋放 Port，解決 Address already in use 問題。
    """
    photo_received = Signal(str, str, str)  # target_id, category, full_path
    
    def __init__(self, port=8000):
        super().__init__()
        self.app = Flask(__name__)
        self.port = port
        self.save_dir = "" 
        self.active_tokens = {} 
        self.server = None  # 用來保存 Werkzeug 的 Server 物件
        self.server_thread = None
        
        # 註冊 Flask 路由
        self.app.add_url_rule('/upload', 'upload_page', self.upload_page, methods=['GET'])
        self.app.add_url_rule('/upload_endpoint', 'upload_endpoint', self.upload_endpoint, methods=['POST'])

    def start(self):
        # 如果伺服器已經在運行，直接忽略這次啟動請求
        if self.server is not None:
            print(f"Server is already running on port {self.port}")
            return

        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()
        print(f"Web Server starting on port {self.port}...")

    def stop(self):
        """
        乾淨地停止伺服器並釋放 Port
        """
        if self.server:
            try:
                print("Stopping Web Server...")
                self.server.shutdown() # 這是 werkzeug 提供的正確停止方法
            except Exception as e:
                print(f"Error stopping server: {e}")
            finally:
                self.server = None
                
        if self.server_thread:
            self.server_thread.join(timeout=1.0)
            self.server_thread = None
            print("Server thread stopped.")

    def _run_server(self):
        try:
            # 使用 make_server 來建立伺服器，這樣我們才能控制它的生命週期
            # threaded=True 允許同時處理多個請求 (避免上傳大檔時卡死)
            self.server = make_server('0.0.0.0', self.port, self.app, threaded=True)
            self.server.serve_forever()
        except OSError as e:
            if "Address already in use" in str(e):
                print(f"CRITICAL ERROR: Port {self.port} is already in use!")
            else:
                print(f"Web Server Error: {e}")
        except Exception as e:
            print(f"Web Server Start Failed: {e}")
        finally:
            self.server = None

    def is_running(self):
        return self.server is not None

    def set_save_directory(self, path):
        self.save_dir = path
        if path and not os.path.exists(path):
            os.makedirs(path, exist_ok=True)

    def generate_token(self, target_id, target_name, is_report=False):
        token = str(uuid.uuid4())[:8]
        self.active_tokens[token] = {
            "id": target_id,
            "name": target_name,
            "is_report": is_report,
            "timestamp": datetime.now()
        }
        return token

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    # --- Flask Routes ---

    def upload_page(self):
        token = request.args.get('token')
        if token not in self.active_tokens:
            return "連結已失效或錯誤", 404
        data = self.active_tokens[token]
        return render_template_string(
            MOBILE_HTML_TEMPLATE, 
            token=token, 
            target_name=data['name'],
            is_report=data['is_report']
        )

    def upload_endpoint(self):
        token = request.form.get('token')
        if token not in self.active_tokens:
            return jsonify({"status": "error", "message": "無效 Token"}), 400
        
        file = request.files.get('photo')
        if not file:
            return jsonify({"status": "error", "message": "無檔案"}), 400

        task_info = self.active_tokens[token]
        category = request.form.get('category', 'default') 
        
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_id = task_info['id'].replace(".", "_")
        filename = f"{safe_id}_{category}_{ts}.jpg"
        
        if not self.save_dir:
            return jsonify({"status": "error", "message": "伺服器儲存路徑未設定"}), 500

        save_path = os.path.join(self.save_dir, filename)
        try:
            file.save(save_path)
            # 通知 UI 執行緒
            self.photo_received.emit(task_info['id'], category, save_path)
            return jsonify({"status": "success"})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

# ==============================================================================
# SECTION 3: CORE LOGIC LAYER (核心邏輯層)
# ==============================================================================

class ProjectManager(QObject): 
    data_changed = Signal()
    photo_received = Signal(str, str, str)

    def __init__(self):
        super().__init__()
        self.current_project_path: Optional[str] = None
        self.project_data: Dict = {}
        self.settings_filename = PROJECT_SETTINGS_FILENAME
        self.std_config: Dict = {} 
        self.server = PhotoServer(port=8000)
        self.server.photo_received.connect(self.handle_mobile_photo)

    def set_standard_config(self, config):
        self.std_config = config
        
    def handle_mobile_photo(self, target_id, category, full_path):
        if self.current_project_path:
            # 轉換為相對路徑以便儲存
            rel_path = os.path.relpath(full_path, self.current_project_path)
            rel_path = rel_path.replace("\\", "/") 
        else:
            rel_path = full_path

        # 如果是報告總覽照片 (UAV/GCS)
        if target_id in TARGETS:
            info_key = f"{target_id}_{category}_path"
            self.update_info({info_key: rel_path})
        
        self.photo_received.emit(target_id, category, rel_path)

    def generate_mobile_link(self, target_id, target_name, is_report=False) -> Optional[str]:
        if not self.current_project_path:
            return None
        
        # 即使伺服器已經在跑，再次呼叫 start() 也是安全的 (PhotoServer 有做檢查)
        if not self.server.is_running():
            self.server.start()
        
        save_dir = os.path.join(self.current_project_path, DIR_IMAGES)
        self.server.set_save_directory(save_dir)
        
        token = self.server.generate_token(target_id, target_name, is_report)
        ip = self.server.get_local_ip()
        port = self.server.port
        
        url = f"http://{ip}:{port}/upload?token={token}"
        return url

    def stop_server(self):
        self.server.stop()

    def get_current_project_type(self) -> str:
        return self.project_data.get("info", {}).get("project_type", PROJECT_TYPE_FULL)

    def is_item_visible(self, item_id) -> bool:
        if not self.current_project_path:
            return False
        info = self.project_data.get("info", {})
        p_type = info.get("project_type", PROJECT_TYPE_FULL)
        
        if p_type == PROJECT_TYPE_ADHOC:
            whitelist = info.get("target_items", [])
            return item_id in whitelist
        else:
            scope = info.get("test_scope", [])
            if not scope and "test_scope" not in info:
                return True 
            section_id = self._find_section_id_by_item(item_id)
            return section_id in scope

    def is_section_visible(self, section_id) -> bool:
        if not self.current_project_path:
            return False
        info = self.project_data.get("info", {})
        p_type = info.get("project_type", PROJECT_TYPE_FULL)
        
        if p_type == PROJECT_TYPE_ADHOC:
            whitelist = info.get("target_items", [])
            section_items = self._get_items_in_section(section_id)
            return any(item['id'] in whitelist for item in section_items)
        else:
            scope = info.get("test_scope", [])
            if not scope and "test_scope" not in info:
                return True
            return str(section_id) in scope

    def _find_section_id_by_item(self, item_id) -> str:
        for sec in self.std_config.get("test_standards", []):
            for item in sec['items']:
                if item['id'] == item_id:
                    return str(sec['section_id'])
        return ""

    def _get_items_in_section(self, section_id) -> List[Dict]:
        for sec in self.std_config.get("test_standards", []):
            if str(sec['section_id']) == str(section_id):
                return sec['items']
        return []

    def create_project(self, form_data: dict) -> Tuple[bool, str]:
        raw_base_path = form_data.get("save_path")
        project_name = form_data.get("project_name")
        
        if not raw_base_path or not project_name:
            return False, "缺少儲存路徑或專案名稱"
            
        base_path = os.path.abspath(os.path.expanduser(raw_base_path))
        target_folder = os.path.join(base_path, project_name)
        final_path = self._get_unique_path(target_folder)
        
        form_data['project_name'] = os.path.basename(final_path)
        form_data['project_type'] = PROJECT_TYPE_FULL 
        
        self.project_data = {
            "version": "2.0",
            "info": form_data,
            "tests": {}
        }
        return self._init_folder_and_save(final_path)

    def create_ad_hoc_project(self, selected_items: list, save_base_path: str) -> Tuple[bool, str]:
        ts_str = datetime.now().strftime(DATE_FMT_PY_FILENAME_SHORT)
        folder_name = f"QuickTest_{ts_str}"
        target_folder = os.path.join(save_base_path, folder_name)
        final_path = self._get_unique_path(target_folder)
        
        info_data = {}
        schema = self.std_config.get("project_meta_schema", [])
        
        for field in schema:
            key = field.get('key')
            f_type = field.get('type')
            
            if key == "project_name":
                info_data[key] = os.path.basename(final_path)
                continue
            
            if f_type == "date":
                info_data[key] = datetime.now().strftime(DATE_FMT_PY_DATE)
            elif f_type == "checkbox_group":
                info_data[key] = []
            elif f_type == "path_selector":
                info_data[key] = ""
            elif f_type == "text":
                key_lower = key.lower()
                if "id" in key_lower or "no" in key_lower:
                    info_data[key] = f"{DEFAULT_ADHOC_PREFIX}-{ts_str}"
                elif "tester" in key_lower or "user" in key_lower:
                    info_data[key] = DEFAULT_TESTER_NAME
                else:
                    info_data[key] = "-"
            else:
                info_data[key] = ""
                
        info_data["project_type"] = PROJECT_TYPE_ADHOC
        info_data["target_items"] = selected_items
        
        self.project_data = {
            "version": "2.0",
            "info": info_data,
            "tests": {}
        }
        return self._init_folder_and_save(final_path)

    def _get_unique_path(self, target_folder) -> str:
        final_path = target_folder
        if os.path.exists(final_path):
            i = 1
            while True:
                new_path = f"{target_folder}_{i}"
                if not os.path.exists(new_path):
                    final_path = new_path
                    break
                i += 1
        return final_path

    def _init_folder_and_save(self, path) -> Tuple[bool, str]:
        try:
            os.makedirs(path, exist_ok=True)
            os.makedirs(os.path.join(path, DIR_IMAGES), exist_ok=True)
            os.makedirs(os.path.join(path, DIR_REPORTS), exist_ok=True)
            self.current_project_path = path
            self.save_all()
            return True, path
        except Exception as e:
            return False, str(e)

    def load_project(self, folder_path: str) -> Tuple[bool, str]:
        json_path = os.path.join(folder_path, self.settings_filename)
        if not os.path.exists(json_path):
            return False, "找不到專案設定檔"
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                self.project_data = json.load(f)
            self.current_project_path = folder_path
            self.data_changed.emit()
            return True, "讀取成功"
        except Exception as e:
            return False, f"讀取失敗: {e}"

    def import_file(self, src_path: str, sub_folder: str = DIR_IMAGES) -> Optional[str]:
        if not self.current_project_path:
            return None
        try:
            filename = os.path.basename(src_path)
            ts = datetime.now().strftime(DATE_FMT_PY_FILENAME)
            new_filename = f"{ts}_{filename}"
            target_dir = os.path.join(self.current_project_path, sub_folder)
            
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
                
            dest_path = os.path.join(target_dir, new_filename)
            shutil.copy2(src_path, dest_path)
            return f"{sub_folder}/{new_filename}"
        except Exception as e:
            print(f"複製檔案失敗: {e}")
            return None

    def merge_external_project(self, source_folder: str) -> Tuple[bool, str]:
        if not self.current_project_path:
            return False, "請先開啟主專案"
        if self.get_current_project_type() != PROJECT_TYPE_FULL:
            return False, "非完整專案不可合併"
            
        source_json_path = os.path.join(source_folder, self.settings_filename)
        if not os.path.exists(source_json_path):
            return False, "來源無效"
            
        try:
            with open(source_json_path, 'r', encoding='utf-8') as f:
                source_data = json.load(f)
            
            if source_data.get("info", {}).get("project_type") != PROJECT_TYPE_ADHOC:
                return False, "只能合併 Ad-Hoc"
                
            # 複製檔案 (圖片與報告)
            for sub in [DIR_IMAGES, DIR_REPORTS]:
                src_sub_dir = os.path.join(source_folder, sub)
                if not os.path.exists(src_sub_dir):
                    continue
                dest_sub_dir = os.path.join(self.current_project_path, sub)
                if not os.path.exists(dest_sub_dir):
                    os.makedirs(dest_sub_dir)
                
                for filename in os.listdir(src_sub_dir):
                    s_file = os.path.join(src_sub_dir, filename)
                    d_file = os.path.join(dest_sub_dir, filename)
                    if os.path.exists(d_file):
                        d_file = os.path.join(dest_sub_dir, f"merged_{filename}")
                    if os.path.isfile(s_file):
                        shutil.copy2(s_file, d_file)
            
            # 合併測試數據
            source_tests = source_data.get("tests", {})
            current_tests = self.project_data.get("tests", {})
            merged_count = 0
            
            for test_id, targets_data in source_tests.items():
                if test_id not in current_tests:
                    current_tests[test_id] = {}
                for target, result_data in targets_data.items():
                    current_tests[test_id][target] = result_data
                    merged_count += 1
            
            self.save_all()
            self.data_changed.emit()
            return True, f"合併 {merged_count} 筆"
        except Exception as e:
            return False, f"失敗: {str(e)}"

    def update_info(self, new_info):
        if not self.current_project_path:
            return False
        self.project_data.setdefault("info", {}).update(new_info)
        self.save_all()
        self.data_changed.emit()
        return True

    def update_test_result(self, test_id, target, result_data, is_shared=False):
        if "tests" not in self.project_data:
            self.project_data["tests"] = {}
        if test_id not in self.project_data["tests"]:
            self.project_data["tests"][test_id] = {}
            
        self.project_data["tests"][test_id][target] = result_data
        self.project_data["tests"][test_id][target]["last_updated"] = datetime.now().strftime(DATE_FMT_PY_DATETIME)
        
        meta = self.project_data["tests"][test_id].setdefault("__meta__", {})
        meta["is_shared"] = is_shared
        
        self.save_all()
        self.data_changed.emit()

    def get_test_meta(self, test_id):
        return self.project_data.get("tests", {}).get(test_id, {}).get("__meta__", {})

    def save_all(self):
        if not self.current_project_path:
            return False, "No Path"
        path = os.path.join(self.current_project_path, self.settings_filename)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.project_data, f, ensure_ascii=False, indent=4)
            return True, "Saved"
        except Exception as e:
            return False, str(e)

    def get_test_status_detail(self, item_config) -> Dict[str, str]:
        test_id = item_config['id']
        targets = item_config.get('targets', [TARGET_GCS])
        item_data = self.project_data.get("tests", {}).get(test_id, {})
        status_map = {}
        
        for t in targets:
            if t not in item_data:
                status_map[t] = STATUS_NOT_TESTED
            else:
                res = item_data[t].get("result", STATUS_UNCHECKED)
                if STATUS_UNCHECKED in res:
                    status_map[t] = STATUS_NOT_TESTED
                elif STATUS_PASS in res:
                    status_map[t] = "Pass"
                elif STATUS_FAIL in res:
                    status_map[t] = "Fail"
                elif STATUS_NA in res:
                    status_map[t] = "N/A"
                else:
                    status_map[t] = STATUS_UNKNOWN
        return status_map

    def is_test_fully_completed(self, item_config) -> bool:
        test_id = item_config['id']
        targets = item_config.get('targets', [TARGET_GCS])
        saved = self.project_data.get("tests", {}).get(test_id, {})
        
        for t in targets:
            if t not in saved:
                return False
            if STATUS_UNCHECKED in saved[t].get("result", STATUS_UNCHECKED):
                return False
        return True

# ==============================================================================
# SECTION 4: UI COMPONENTS (UI 元件層)
# ==============================================================================

class QRCodeDialog(QDialog):
    def __init__(self, parent, pm: ProjectManager, url: str, title="手機掃碼上傳"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(400, 500)
        self.pm = pm 
        self.url = url
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        lbl_hint = QLabel("請使用手機掃描下方 QR Code\n(需連接同一 Wi-Fi)")
        lbl_hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_hint)

        qr_lbl = QLabel()
        qr_lbl.setAlignment(Qt.AlignCenter)
        
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(self.url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        qimg = QImage.fromData(buffer.getvalue())
        
        qr_lbl.setPixmap(QPixmap.fromImage(qimg).scaled(300, 300, Qt.KeepAspectRatio))
        layout.addWidget(qr_lbl)

        link_layout = QHBoxLayout()
        self.link_edit = QLineEdit(self.url)
        self.link_edit.setReadOnly(True)
        btn_copy = QPushButton("複製連結")
        btn_copy.clicked.connect(self.copy_link)
        
        link_layout.addWidget(self.link_edit)
        link_layout.addWidget(btn_copy)
        layout.addLayout(link_layout)

        btn_close = QPushButton("關閉 (停止伺服器)")
        btn_close.clicked.connect(self.close) 
        layout.addWidget(btn_close)

    def copy_link(self):
        cb = QApplication.clipboard()
        cb.setText(self.url)
        QMessageBox.information(self, "複製成功", "網址已複製到剪貼簿")

    def closeEvent(self, event):
        # 關閉視窗時，強制呼叫停止伺服器方法
        self.pm.stop_server()
        event.accept()

# [New] GalleryWindow: 用於一次顯示 6 張照片
class GalleryWindow(QDialog):
    def __init__(self, parent, pm, target_name):
        super().__init__(parent)
        self.pm = pm
        self.target_name = target_name
        self.setWindowTitle(f"{target_name.upper()} - 六視角照片檢視")
        self.resize(1000, 700)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        grid = QGridLayout()
        layout.addLayout(grid)
        
        # 6個視角的位置配置 (Row, Col)
        # 0,0: Front | 0,1: Back | 0,2: Top
        # 1,0: Side1 | 1,1: Side2 | 1,2: Bottom
        positions = {
            "front": (0, 0), "back": (0, 1), "top": (0, 2),
            "side1": (1, 0), "side2": (1, 1), "bottom": (1, 2)
        }
        
        info_data = self.pm.project_data.get("info", {})
        
        for angle in PHOTO_ANGLES_ORDER:
            row, col = positions.get(angle, (0, 0))
            
            # 建立一個容器
            container = QFrame()
            container.setFrameShape(QFrame.Box)
            v_box = QVBoxLayout(container)
            
            # 標題
            lbl_title = QLabel(PHOTO_ANGLES_NAME[angle])
            lbl_title.setAlignment(Qt.AlignCenter)
            lbl_title.setStyleSheet("font-weight: bold; background-color: #eee;")
            
            # 圖片顯示區
            lbl_img = QLabel()
            lbl_img.setAlignment(Qt.AlignCenter)
            lbl_img.setMinimumSize(300, 200)
            
            # 讀取圖片路徑
            path_key = f"{self.target_name}_{angle}_path"
            rel_path = info_data.get(path_key)
            
            if rel_path and self.pm.current_project_path:
                full_path = os.path.join(self.pm.current_project_path, rel_path)
                if os.path.exists(full_path):
                    pixmap = QPixmap(full_path)
                    # 縮放圖片以適應視窗，保持比例
                    lbl_img.setPixmap(pixmap.scaled(320, 240, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                else:
                    lbl_img.setText("檔案遺失")
                    lbl_img.setStyleSheet("color: red;")
            else:
                lbl_img.setText("未上傳")
                lbl_img.setStyleSheet("color: gray; font-size: 14pt;")
            
            v_box.addWidget(lbl_title)
            v_box.addWidget(lbl_img)
            grid.addWidget(container, row, col)
        
        btn_close = QPushButton("關閉")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

class QuickTestSelector(QDialog):
    def __init__(self, parent, config):
        super().__init__(parent)
        self.setWindowTitle("選擇檢測項目 (各別模式)")
        self.resize(400, 500)
        self.config = config
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("請勾選本次要進行檢測的項目："))
        self.list_widget = QListWidget()
        
        for section in self.config.get("test_standards", []):
            header = QListWidgetItem(f"--- {section['section_name']} ---")
            header.setFlags(Qt.NoItemFlags) 
            self.list_widget.addItem(header)
            
            for item in section['items']:
                li = QListWidgetItem(f"{item['id']} {item['name']}")
                li.setFlags(li.flags() | Qt.ItemIsUserCheckable)
                li.setCheckState(Qt.Unchecked)
                li.setData(Qt.UserRole, item['id'])
                self.list_widget.addItem(li)
                
        layout.addWidget(self.list_widget)
        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit(DEFAULT_DESKTOP_PATH)
        btn_browse = QPushButton("...")
        btn_browse.clicked.connect(self._browse)
        
        path_layout.addWidget(QLabel("儲存位置:"))
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(btn_browse)
        layout.addLayout(path_layout)
        
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "選擇資料夾")
        if d:
            self.path_edit.setText(d)

    def get_data(self):
        selected = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.Checked:
                selected.append(item.data(Qt.UserRole))
        return selected, self.path_edit.text()

    def run(self):
        if self.exec() == QDialog.Accepted:
            return self.get_data()
        return None, None

class ProjectFormController:
    def __init__(self, parent_window, meta_schema, existing_data=None):
        self.meta_schema = meta_schema
        self.existing_data = existing_data
        self.is_edit_mode = existing_data is not None
        self.dialog = QDialog(parent_window)
        self.dialog.setWindowTitle("編輯專案" if self.is_edit_mode else "新建專案")
        self.dialog.resize(500, 500)
        self.inputs = {}
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self.dialog)
        form = QFormLayout()
        desktop = DEFAULT_DESKTOP_PATH
        
        for field in self.meta_schema:
            key = field['key']
            f_type = field['type']
            label = field['label']
            
            if f_type == 'hidden':
                continue
            
            widget = None
            if f_type == 'text':
                widget = QLineEdit()
                if self.is_edit_mode and key in self.existing_data:
                    widget.setText(str(self.existing_data[key]))
                    if key == "project_name":
                        widget.setReadOnly(True)
                        widget.setStyleSheet("background-color:#f0f0f0;")
                        
            elif f_type == 'date': 
                widget = QDateEdit()
                widget.setCalendarPopup(True)
                if self.is_edit_mode and key in self.existing_data:
                    widget.setDate(QDate.fromString(self.existing_data[key], DATE_FMT_QT))
                else:
                    widget.setDate(QDate.currentDate())
                    
            elif f_type == 'path_selector':
                widget = QWidget()
                h = QHBoxLayout(widget)
                h.setContentsMargins(0,0,0,0)
                pe = QLineEdit()
                btn = QToolButton()
                btn.setText("...")
                
                if self.is_edit_mode:
                    pe.setText(self.existing_data.get(key,""))
                    pe.setReadOnly(True)
                    btn.setEnabled(False)
                else:
                    pe.setText(desktop)
                    btn.clicked.connect(lambda _, le=pe: self._browse(le))
                    
                h.addWidget(pe)
                h.addWidget(btn)
                widget.line_edit = pe
                
            elif f_type == 'checkbox_group':
                widget = QGroupBox()
                v = QVBoxLayout(widget)
                v.setContentsMargins(5,5,5,5)
                opts = field.get("options", [])
                vals = self.existing_data.get(key, []) if self.is_edit_mode else []
                widget.checkboxes = [] 
                
                for o in opts:
                    chk = QCheckBox(o['label'])
                    chk.setProperty("val", o['value'])
                    if self.is_edit_mode: 
                        if o['value'] in vals:
                            chk.setChecked(True)
                    else:
                        chk.setChecked(True)
                    v.addWidget(chk)
                    widget.checkboxes.append(chk)
            
            if widget:
                form.addRow(label, widget)
                self.inputs[key] = {'w': widget, 't': f_type}
        
        layout.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.dialog.accept)
        btns.rejected.connect(self.dialog.reject)
        layout.addWidget(btns)

    def _browse(self, le):
        dialog = QFileDialog(self.dialog, "選擇資料夾")
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setOption(QFileDialog.DontUseNativeDialog, True)
        dialog.setWindowModality(Qt.ApplicationModal)
        if dialog.exec() == QDialog.Accepted:
            files = dialog.selectedFiles()
            if files:
                le.setText(files[0])

    def run(self):
        if self.dialog.exec() == QDialog.Accepted:
            return self._collect()
        return None

    def _collect(self):
        data = {}
        for key, inf in self.inputs.items():
            w = inf['w']
            t = inf['t']
            if t == 'text':
                data[key] = w.text()
            elif t == 'date':
                data[key] = w.date().toString(DATE_FMT_QT)
            elif t == 'path_selector':
                data[key] = w.line_edit.text()
            elif t == 'checkbox_group':
                data[key] = [c.property("val") for c in w.checkboxes if c.isChecked()]
        return data

class OverviewPage(QWidget):
    """
    專案總覽頁面
    修改：移除列表中的小眼睛按鈕，主圖片按鈕改為開啟六視角 GalleryWindow
    """
    def __init__(self, pm: ProjectManager, config):
        super().__init__()
        self.pm = pm
        self.config = config
        self._init_ui()
        self.pm.photo_received.connect(self.on_photo_received)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        self.layout = QVBoxLayout(content_widget)
        
        self.info_group = QGroupBox("專案資訊")
        self.info_layout = QFormLayout()
        self.info_group.setLayout(self.info_layout)
        self.layout.addWidget(self.info_group)

        self.prog_g = QGroupBox("檢測進度")
        self.prog_l = QVBoxLayout()
        self.prog_g.setLayout(self.prog_l)
        self.layout.addWidget(self.prog_g)

        # 檢測照片總覽 (Grid Layout)
        photo_g = QGroupBox("檢測照片總覽")
        self.photo_grid = QGridLayout()
        photo_g.setLayout(self.photo_grid)
        self.layout.addWidget(photo_g)
        
        self.photo_labels = {} 
        
        # 建立 Header (UAV / GCS)
        targets = [TARGET_UAV, TARGET_GCS]
        for col, t in enumerate(targets):
            # 標題
            lbl_title = QLabel(t.upper())
            lbl_title.setAlignment(Qt.AlignCenter)
            lbl_title.setStyleSheet("font-weight: bold; font-size: 16pt; padding: 5px;")
            self.photo_grid.addWidget(lbl_title, 0, col, 1, 1)

            # 手機上傳按鈕
            btn_mobile = QPushButton(f"📱 上傳 {t.upper()} 照片 (含各角度)")
            btn_mobile.clicked.connect(partial(self.up_photo_mobile, t))
            self.photo_grid.addWidget(btn_mobile, 1, col, 1, 1)
            
            # --- 正面大圖 (Front) 區域 ---
            front_key = f"{t}_{PHOTO_ANGLES_ORDER[0]}" # front
            
            front_container = QWidget()
            front_v = QVBoxLayout(front_container)
            
            lbl_img = QLabel("正面照片 (Front)\n未上傳")
            lbl_img.setFrameShape(QFrame.Box)
            lbl_img.setFixedSize(320, 240)
            lbl_img.setAlignment(Qt.AlignCenter)
            lbl_img.setScaledContents(True)
            
            # [修改] 這裡改為開啟六格視窗
            btn_view = QPushButton("檢視六視角照片")
            btn_view.clicked.connect(partial(self.open_gallery, t))
            
            front_v.addWidget(lbl_img)
            front_v.addWidget(btn_view)
            
            self.photo_grid.addWidget(front_container, 2, col, 1, 1)
            # 這裡只存 lbl_img，按鈕不需要動態更新文字
            self.photo_labels[front_key] = lbl_img
            
            # --- 其他角度狀態清單 (純顯示狀態，無按鈕) ---
            other_angles_group = QGroupBox("其他角度狀態")
            other_v = QVBoxLayout(other_angles_group)
            
            for angle in PHOTO_ANGLES_ORDER:
                if angle == "front":
                    continue
                
                angle_key = f"{t}_{angle}"
                row_w = QWidget()
                row_h = QHBoxLayout(row_w)
                row_h.setContentsMargins(0, 0, 0, 0)
                
                lbl_status = QLabel("●") 
                lbl_status.setFixedSize(20, 20)
                lbl_status.setStyleSheet("color: gray; font-size: 14pt;") 
                
                lbl_text = QLabel(PHOTO_ANGLES_NAME[angle])
                
                row_h.addWidget(lbl_status)
                row_h.addWidget(lbl_text)
                row_h.addStretch()
                
                other_v.addWidget(row_w)
                
                self.photo_labels[angle_key] = lbl_status

            self.photo_grid.addWidget(other_angles_group, 3, col, 1, 1)


        self.layout.addStretch()

        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

    def refresh_data(self):
        if not self.pm.current_project_path:
            return
        info_data = self.pm.project_data.get("info", {})
        schema = self.config.get("project_meta_schema", [])

        while self.info_layout.count():
            child = self.info_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        for field in schema:
            if field.get("show_in_overview", False):
                key = field['key']
                label_text = field['label']
                value = info_data.get(key, "-")
                if isinstance(value, list):
                    value = ", ".join(value)
                val_label = QLabel(str(value))
                val_label.setStyleSheet("font-weight: bold; color: #333;")
                val_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
                self.info_layout.addRow(f"{label_text}:", val_label)

        # --- 更新照片狀態 ---
        for key, widget in self.photo_labels.items():
            path_key = f"{key}_path"
            rel_path = info_data.get(path_key)
            has_file = False
            full_path = ""
            
            if rel_path:
                full_path = os.path.join(self.pm.current_project_path, rel_path)
                if os.path.exists(full_path):
                    has_file = True
            
            if "front" in key:
                # widget 是正面大圖的 QLabel
                if has_file:
                    widget.setPixmap(QPixmap(full_path))
                else:
                    widget.setText("正面照片 (Front)\n未上傳")
            else:
                # widget 是小圓點 QLabel
                if has_file:
                    widget.setStyleSheet("color: green; font-size: 14pt;") 
                    widget.setToolTip("已上傳")
                else:
                    widget.setStyleSheet("color: red; font-size: 14pt;") 
                    widget.setToolTip("尚未上傳")

        while self.prog_l.count(): 
            child = self.prog_l.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        for section in self.config.get("test_standards", []):
            sec_id = section['section_id']
            sec_name = section['section_name']
            is_visible = self.pm.is_section_visible(sec_id)
            h = QHBoxLayout()
            lbl = QLabel(sec_name)
            lbl.setFixedWidth(150)
            p = QProgressBar()
            
            if is_visible:
                items = section['items']
                active_items = [i for i in items if self.pm.is_item_visible(i['id'])]
                total = len(active_items)
                done = sum(1 for i in active_items if self.pm.is_test_fully_completed(i))
                if total > 0:
                    p.setRange(0, total)
                    p.setValue(done)
                    p.setFormat(f"%v / %m ({int(done/total*100)}%)")
                else:
                    p.setRange(0, 100)
                    p.setValue(0)
                    p.setFormat("無項目")
            else:
                p.setRange(0, 100)
                p.setValue(0)
                p.setFormat("不適用 (N/A)")
                p.setStyleSheet(f"QProgressBar {{ color: gray; background-color: {COLOR_BG_DEFAULT}; }}")
                lbl.setStyleSheet("color: gray;")
                
            h.addWidget(lbl)
            h.addWidget(p)
            w = QWidget()
            w.setLayout(h)
            self.prog_l.addWidget(w)

    def up_photo_mobile(self, target):
        if not self.pm.current_project_path:
            QMessageBox.warning(self, "警告", "請先建立或開啟專案")
            return
        title = f"{target.upper()} 照片上傳"
        url = self.pm.generate_mobile_link(target, title, is_report=True)
        if url: 
            QRCodeDialog(self, self.pm, url, title).exec()
        else:
            QMessageBox.critical(self, "錯誤", "無法生成連結")

    def open_gallery(self, target):
        """開啟六視角照片瀏覽視窗"""
        if not self.pm.current_project_path:
            return
        
        gallery = GalleryWindow(self, self.pm, target)
        gallery.exec()

    @Slot(str, str, str)
    def on_photo_received(self, target_id, category, path):
        if target_id in TARGETS:
            self.refresh_data()
            QMessageBox.information(self, "收到照片", f"已收到:\n{target_id.upper()} - {category}\n{os.path.basename(path)}")

class SingleTargetTestWidget(QWidget):
    def __init__(self, target, config, pm, save_cb=None):
        super().__init__()
        self.target = target
        self.config = config
        self.pm = pm
        self.item_id = config['id']
        self.save_cb = save_cb
        self.logic = config.get("logic", "AND").upper()
        self._init_ui()
        self._load()
        self.pm.photo_received.connect(self.on_photo_received)

    def _init_ui(self):
        l = QVBoxLayout(self)
        h = QHBoxLayout()
        h.addWidget(QLabel(f"<h3>對象: {self.target}</h3>"))
        h.addWidget(QLabel(f"({self.logic})"))
        h.addStretch()
        l.addLayout(h)
        
        self.desc = QTextEdit()
        self.desc.setPlaceholderText(self.config.get('evidence_block', {}).get('description_template', ''))
        
        g1 = QGroupBox("說明")
        v1 = QVBoxLayout()
        v1.addWidget(self.desc)
        g1.setLayout(v1)
        l.addWidget(g1)
        
        self.checks = {}
        criteria = self.config.get('sub_criteria', [])
        if criteria:
            g2 = QGroupBox("標準")
            v2 = QVBoxLayout()
            for c in criteria:
                chk = QCheckBox(c['content'])
                chk.stateChanged.connect(self.auto_judge)
                self.checks[c['id']] = chk
                v2.addWidget(chk)
            g2.setLayout(v2)
            l.addWidget(g2)
            
        g_file = QGroupBox("附加報告/檔案/照片")
        h_file = QHBoxLayout()
        self.lbl_file = QLabel("未選擇檔案")
        btn_pc = QPushButton("📂 本機檔案")
        btn_pc.clicked.connect(self.upload_report_pc)
        btn_mobile = QPushButton("📱 手機拍照")
        btn_mobile.clicked.connect(self.upload_report_mobile)
        
        h_file.addWidget(self.lbl_file)
        h_file.addWidget(btn_pc)
        h_file.addWidget(btn_mobile)
        g_file.setLayout(h_file)
        l.addWidget(g_file)
        
        self.current_report_path = None 
        
        g3 = QGroupBox("判定")
        h3 = QHBoxLayout()
        h3.addWidget(QLabel("結果:"))
        self.combo = QComboBox()
        self.combo.addItems([STATUS_UNCHECKED, STATUS_PASS, STATUS_FAIL, STATUS_NA])
        self.combo.currentTextChanged.connect(self.update_color)
        h3.addWidget(self.combo)
        g3.setLayout(h3)
        l.addWidget(g3)
        
        l.addStretch()
        
        btn = QPushButton(f"儲存 ({self.target})")
        btn.setStyleSheet("background-color: #4CAF50; color: white;")
        btn.clicked.connect(self.on_save)
        l.addWidget(btn)

    def upload_report_pc(self):
        if not self.pm.current_project_path:
            QMessageBox.warning(self, "警告", "請先建立專案")
            return
        f, _ = QFileDialog.getOpenFileName(self, "選擇檔案", "", "Files (*.pdf *.html *.txt *.jpg *.png)")
        if f:
            rel = self.pm.import_file(f, DIR_REPORTS)
            if rel:
                self.current_report_path = rel
                self.lbl_file.setText(os.path.basename(rel))

    def upload_report_mobile(self):
        if not self.pm.current_project_path:
            QMessageBox.warning(self, "警告", "請先建立專案")
            return
        title = f"{self.item_id} 佐證 ({self.target})"
        url = self.pm.generate_mobile_link(self.item_id, title, is_report=False)
        if url: 
            QRCodeDialog(self, self.pm, url, title).exec()
        else:
            QMessageBox.critical(self, "錯誤", "無法生成連結")

    @Slot(str, str, str)
    def on_photo_received(self, target_id, category, path):
        if target_id == self.item_id:
            self.current_report_path = path
            self.lbl_file.setText(f"收到: {os.path.basename(path)}")
            QMessageBox.information(self, "收到佐證", f"已收到手機上傳的佐證照片：\n{os.path.basename(path)}")

    def auto_judge(self):
        if not self.checks:
            return
        checked = sum(1 for c in self.checks.values() if c.isChecked())
        is_pass = (checked == len(self.checks)) if self.logic == "AND" else (checked > 0)
        self.combo.setCurrentText(STATUS_PASS if is_pass else STATUS_FAIL)

    def update_color(self, t):
        s = ""
        if STATUS_PASS in t:
            s = f"background-color: {COLOR_BG_PASS}; color: {COLOR_TEXT_PASS};"
        elif STATUS_FAIL in t:
            s = f"background-color: {COLOR_BG_FAIL}; color: {COLOR_TEXT_FAIL};"
        elif STATUS_NA in t:
            s = f"background-color: {COLOR_BG_NA};"
        self.combo.setStyleSheet(s)

    def on_save(self):
        if not self.pm.current_project_path:
            return
        data = {
            "description": self.desc.toPlainText(),
            "criteria": {k: c.isChecked() for k,c in self.checks.items()},
            "result": self.combo.currentText(),
            "report_path": self.current_report_path,
            "status": "checked"
        }
        if self.save_cb:
            self.save_cb(data)
        else: 
            self.pm.update_test_result(self.item_id, self.target, data)
            QMessageBox.information(self, "成功", "已儲存")

    def _load(self):
        if not self.pm.project_data:
            return
        item = self.pm.project_data.get("tests", {}).get(self.item_id, {})
        key = self.target
        if self.target == "Shared":
            key = self.config.get("targets", [TARGET_GCS])[0]
            
        data = item.get(key, {})
        if data:
            self.desc.setPlainText(data.get("description", ""))
            for k, v in data.get("criteria", {}).items():
                if k in self.checks:
                    self.checks[k].blockSignals(True)
                    self.checks[k].setChecked(v)
                    self.checks[k].blockSignals(False)
            res = data.get("result", STATUS_UNCHECKED)
            idx = self.combo.findText(res)
            if idx >= 0:
                self.combo.setCurrentIndex(idx)
            self.update_color(res)
            rp = data.get("report_path")
            if rp:
                self.current_report_path = rp
                self.lbl_file.setText(os.path.basename(rp))

class UniversalTestPage(QWidget):
    def __init__(self, config, pm):
        super().__init__()
        self.config = config
        self.pm = pm
        self.targets = config.get("targets", [TARGET_GCS])
        self.allow_share = config.get("allow_share", False)
        self._init_ui()
        self._load_state()

    def _init_ui(self):
        l = QVBoxLayout(self)
        h = QHBoxLayout()
        h.addWidget(QLabel(f"<h2>{self.config['name']}</h2>"))
        l.addLayout(h)
        
        self.chk = None
        if len(self.targets) > 1:
            self.chk = QCheckBox("共用結果")
            self.chk.setStyleSheet("color: blue; font-weight: bold;")
            self.chk.toggled.connect(self.on_share)
            h.addStretch()
            h.addWidget(self.chk)

        self.stack = QStackedWidget()
        l.addWidget(self.stack)
        
        self.p_sep = QWidget()
        v = QVBoxLayout(self.p_sep)
        v.setContentsMargins(0,0,0,0)
        
        if len(self.targets) > 1:
            tabs = QTabWidget()
            for t in self.targets:
                tabs.addTab(SingleTargetTestWidget(t, self.config, self.pm), t)
            v.addWidget(tabs)
        else:
            v.addWidget(SingleTargetTestWidget(self.targets[0], self.config, self.pm))
            
        self.stack.addWidget(self.p_sep)

        if len(self.targets) > 1:
            self.p_share = SingleTargetTestWidget("Shared", self.config, self.pm, save_cb=self.save_share)
            self.stack.addWidget(self.p_share)

    def _load_state(self):
        meta = self.pm.get_test_meta(self.config['id'])
        if self.chk and meta.get("is_shared"):
            self.chk.setChecked(True)
            self.stack.setCurrentWidget(self.p_share)

    def on_share(self, checked):
        self.stack.setCurrentWidget(self.p_share if checked else self.p_sep)

    def save_share(self, data):
        for t in self.targets:
            self.pm.update_test_result(self.config['id'], t, data, is_shared=True)
        QMessageBox.information(self, "成功", "共用儲存完成")

# ==============================================================================
# SECTION 5: MAIN APPLICATION (程式入口)
# ==============================================================================

class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("無人機資安檢測工具 v2.0 Refactored")
        self.resize(1200, 800)
        self.config = self._load_config()
        
        self.pm = ProjectManager()
        self.pm.set_standard_config(self.config) 
        self.pm.data_changed.connect(self.refresh_ui)
        
        self.test_ui_elements = {}
        self.current_font_size = 10 

        self.cw = QWidget()
        self.setCentralWidget(self.cw)
        self.main_l = QVBoxLayout(self.cw)
        
        self._init_menu()
        
        self.tabs = QTabWidget()
        self.tabs.currentChanged.connect(lambda i: self.overview.refresh_data() if i==0 else None)
        self.main_l.addWidget(self.tabs)
        
        self.overview = OverviewPage(self.pm, self.config)
        self.tabs.addTab(self.overview, "總覽 Overview")
        self._init_tabs()
        
        self._set_enabled(False)
        self._init_zoom()

    def closeEvent(self, event):
        self.pm.stop_server()
        event.accept()

    def _init_zoom(self):
        self.shortcut_zoom_in = QShortcut(QKeySequence.ZoomIn, self)
        self.shortcut_zoom_in.activated.connect(self.zoom_in)
        self.shortcut_zoom_in_alt = QShortcut(QKeySequence("Ctrl+="), self)
        self.shortcut_zoom_in_alt.activated.connect(self.zoom_in)
        self.shortcut_zoom_out = QShortcut(QKeySequence.ZoomOut, self)
        self.shortcut_zoom_out.activated.connect(self.zoom_out)

    def zoom_in(self):
        if self.current_font_size < 30:
            self.current_font_size += 2
            self.update_font()

    def zoom_out(self):
        if self.current_font_size > 8:
            self.current_font_size -= 2
            self.update_font()

    def update_font(self):
        QApplication.instance().setStyleSheet(f"QWidget {{ font-size: {self.current_font_size}pt; }}")

    def _load_config(self):
        json_path = CONFIG_FILENAME
        fallback_cfg = {"test_standards": [], "project_meta_schema": []}
        if not os.path.exists(json_path):
            return fallback_cfg
        try:
            with open(json_path, "r", encoding='utf-8-sig') as f:
                return json.load(f)
        except Exception:
            return fallback_cfg

    def _init_menu(self):
        mb = self.menuBar()
        f_menu = mb.addMenu("檔案")
        f_menu.addAction("新建專案", self.on_new)
        f_menu.addAction("開啟專案", self.on_open)
        
        self.a_edit = f_menu.addAction("編輯專案", self.on_edit)
        self.a_edit.setEnabled(False)
        
        t_menu = mb.addMenu("工具")
        t_menu.addAction("各別檢測模式 (Ad-Hoc)", self.on_adhoc)
        self.a_merge = t_menu.addAction("匯入各別檢測結果", self.on_merge)
        self.a_merge.setEnabled(False)

    def _init_tabs(self):
        for sec in self.config.get("test_standards", []):
            p = QWidget()
            v = QVBoxLayout(p)
            v.addWidget(QLabel(f"<h3>{sec['section_name']}</h3>"))
            
            scr = QScrollArea()
            scr.setWidgetResizable(True)
            v.addWidget(scr)
            
            cont = QWidget()
            cv = QVBoxLayout(cont)
            scr.setWidget(cont)
            
            for item in sec['items']:
                row = QWidget()
                rh = QHBoxLayout(row)
                rh.setContentsMargins(0,5,0,5)
                
                btn = QPushButton(f"{item['id']} {item['name']}")
                btn.setFixedHeight(40)
                btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                btn.clicked.connect(partial(self.open_test, item))
                
                st_cont = QWidget()
                st_l = QHBoxLayout(st_cont)
                st_l.setContentsMargins(0,0,0,0)
                st_cont.setFixedWidth(240)
                
                rh.addWidget(btn)
                rh.addWidget(st_cont)
                cv.addWidget(row)
                
                self.test_ui_elements[item['id']] = (btn, st_l, item, row)
            
            cv.addStretch()
            self.tabs.addTab(p, sec['section_id'])

    def refresh_ui(self):
        self.overview.refresh_data()
        self.update_status()
        self.update_tab_visibility()
        
        has_proj = self.pm.current_project_path is not None
        self.a_edit.setEnabled(has_proj)
        
        info = self.pm.project_data.get("info", {})
        is_full = info.get("project_type", PROJECT_TYPE_FULL) == PROJECT_TYPE_FULL
        self.a_merge.setEnabled(has_proj and is_full)
        
        self.setWindowTitle(f"無人機資安檢測工具 - {info.get('project_name', '')} ({'完整' if is_full else '各別'})")

    def update_status(self):
        for tid, (btn, layout, conf, row) in self.test_ui_elements.items():
            if not self.pm.is_item_visible(tid):
                row.hide()
                continue
            row.show()
            
            status_map = self.pm.get_test_status_detail(conf)
            is_any = any(s != STATUS_NOT_TESTED for s in status_map.values())
            
            if is_any:
                btn.setStyleSheet(f"QPushButton {{ background-color: {COLOR_BTN_ACTIVE}; color: white; font-weight: bold; }} QPushButton:hover {{ background-color: {COLOR_BTN_HOVER}; }}")
            else:
                btn.setStyleSheet("")
                
            while layout.count():
                layout.takeAt(0).widget().deleteLater()
                
            for t, s in status_map.items():
                lbl_text = f"{t}: {s}" if len(status_map)>1 else s
                lbl = QLabel(lbl_text)
                lbl.setAlignment(Qt.AlignCenter)
                lbl.setFixedHeight(30)
                
                c = COLOR_BG_DEFAULT
                tc = COLOR_TEXT_GRAY
                if s == "Pass":
                    c = COLOR_BG_PASS
                    tc = COLOR_TEXT_PASS
                elif s == "Fail":
                    c = COLOR_BG_FAIL
                    tc = COLOR_TEXT_FAIL
                elif s == "N/A":
                    c = COLOR_BG_NA
                    tc = COLOR_TEXT_WHITE 
                    
                lbl.setStyleSheet(f"background-color:{c}; color:{tc}; border-radius:4px; font-weight:bold;")
                layout.addWidget(lbl)

    def update_tab_visibility(self):
        if not self.pm.current_project_path:
            return
        for i, sec in enumerate(self.config.get("test_standards", [])):
            t_idx = i + 1
            sec_id = sec['section_id']
            is_visible = self.pm.is_section_visible(sec_id)
            self.tabs.setTabEnabled(t_idx, is_visible)
            self.tabs.setTabText(t_idx, sec['section_name'] + (" (N/A)" if not is_visible else ""))

    def _set_enabled(self, e):
        for i in range(1, self.tabs.count()):
            self.tabs.setTabEnabled(i, e)

    def on_new(self):
        c = ProjectFormController(self, self.config['project_meta_schema'])
        d = c.run()
        if d: 
            ok, r = self.pm.create_project(d)
            if ok:
                QMessageBox.information(self, "OK", f"建立於 {r}")
                self.project_ready()
            else:
                QMessageBox.warning(self, "Fail", r)

    def on_open(self):
        dialog = QFileDialog(self, "選專案")
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setOption(QFileDialog.DontUseNativeDialog, True)
        dialog.setWindowModality(Qt.ApplicationModal)
        if dialog.exec() == QDialog.Accepted:
            selected = dialog.selectedFiles()
            if selected:
                ok, m = self.pm.load_project(selected[0])
                if ok:
                    self.project_ready()
                else:
                    QMessageBox.warning(self, "Fail", m)

    def on_edit(self):
        if not self.pm.current_project_path:
            return
        c = ProjectFormController(self, self.config['project_meta_schema'], self.pm.project_data.get("info", {}))
        d = c.run()
        if d and self.pm.update_info(d):
            QMessageBox.information(self, "OK", "已更新")
            self.overview.refresh_data()

    def on_adhoc(self):
        d = QuickTestSelector(self, self.config)
        s, p = d.run()
        if s and p:
            ok, r = self.pm.create_ad_hoc_project(s, p)
            if ok:
                QMessageBox.information(self, "OK", f"已建立:\n{r}")
                self.project_ready()
            else:
                QMessageBox.warning(self, "Fail", r)

    def on_merge(self):
        d = QFileDialog.getExistingDirectory(self, "選匯入目錄")
        if d:
            ok, msg = self.pm.merge_external_project(d)
            if ok:
                QMessageBox.information(self, "OK", msg)
            else:
                QMessageBox.warning(self, "Fail", msg)

    def project_ready(self):
        self._set_enabled(True)
        self.refresh_ui()
        self.tabs.setCurrentIndex(0)

    def open_test(self, item):
        self.win = QWidget()
        self.win.setWindowTitle(f"檢測 {item['id']}")
        self.win.resize(600, 700)
        l = QVBoxLayout(self.win)
        l.addWidget(UniversalTestPage(item, self.pm))
        self.win.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainApp()
    window.show()
    sys.exit(app.exec())