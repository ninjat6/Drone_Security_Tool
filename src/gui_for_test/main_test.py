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

# 引入 Flask 與 Werkzeug server
from flask import Flask, request, jsonify, render_template_string
from werkzeug.serving import make_server

# 引入 QR Code 與圖片處理
import qrcode
from PIL import ImageQt

# 引入 PySide6
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QTabWidget,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QStackedWidget,
    QMessageBox,
    QLabel,
    QDialog,
    QFormLayout,
    QLineEdit,
    QDateEdit,
    QToolButton,
    QDialogButtonBox,
    QFileDialog,
    QTextEdit,
    QGroupBox,
    QCheckBox,
    QProgressBar,
    QFrame,
    QScrollArea,
    QComboBox,
    QSizePolicy,
    QListWidget,
    QListWidgetItem,
    QGridLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QInputDialog,
)
from PySide6.QtCore import Qt, QDate, QObject, Signal, Slot, QUrl
from PySide6.QtGui import QPixmap, QShortcut, QKeySequence, QImage, QDesktopServices

# ==============================================================================
# SECTION 1: CONFIGURATION & CONSTANTS
# ==============================================================================

# 檔案系統設定
CONFIG_DIR = "configs"
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
COLOR_BG_WARN = "#fff3cd"

COLOR_TEXT_PASS = "#155724"
COLOR_TEXT_FAIL = "#721c24"
COLOR_TEXT_NORMAL = "#333333"
COLOR_TEXT_WHITE = "white"
COLOR_TEXT_GRAY = "#666666"
COLOR_TEXT_WARN = "#856404"

COLOR_BTN_ACTIVE = "#2196F3"
COLOR_BTN_HOVER = "#1976D2"

# 照片視角與目標定義
TARGET_UAV = "UAV"
TARGET_GCS = "GCS"
TARGETS = [TARGET_UAV, TARGET_GCS]

PHOTO_ANGLES_ORDER = ["front", "back", "side1", "side2", "top", "bottom"]
PHOTO_ANGLES_NAME = {
    "front": "正面 (Front)",
    "back": "背面 (Back)",
    "side1": "側面1 (Side 1)",
    "side2": "側面2 (Side 2)",
    "top": "上方 (Top)",
    "bottom": "下方 (Bottom)",
}

# 手機端 HTML 模板
MOBILE_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-Hant">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
    <title>Photo Helper</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/cropperjs/1.5.13/cropper.min.css">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; padding: 0; background: #f8f9fa; color: #333; overscroll-behavior-y: contain; }
        .container { max-width: 100%; padding: 15px; padding-bottom: 60px; box-sizing: border-box; }
        h3 { margin-top: 0; text-align: center; font-size: 1.2rem; }
        .btn { display: block; width: 100%; padding: 12px; margin: 8px 0; font-size: 16px; font-weight: bold; color: white; border: none; border-radius: 8px; cursor: pointer; text-align: center; }
        .btn-primary { background-color: #007bff; }
        .btn-success { background-color: #28a745; }
        .btn-danger { background-color: #dc3545; }
        .btn-secondary { background-color: #6c757d; }
        .btn-outline { background-color: transparent; border: 1px solid #666; color: #666; }
        .btn:disabled { background-color: #ccc; cursor: not-allowed; }
        .btn-row { display: flex; gap: 10px; margin-bottom: 10px; }
        .btn-row .btn { margin: 0; }
        select { width: 100%; padding: 10px; font-size: 16px; border-radius: 6px; border: 1px solid #ccc; background: white; margin-bottom: 15px; }
        .controls-panel { background: #fff; border: 1px solid #ddd; border-radius: 8px; padding: 10px; margin-bottom: 10px; display: flex; align-items: center; justify-content: space-between; gap: 10px; }
        .control-item { display: flex; align-items: center; gap: 5px; font-size: 14px; font-weight: bold; }
        input[type="color"] { border: none; width: 40px; height: 35px; cursor: pointer; background: none; }
        input[type="range"] { width: 100px; }
        #step1-crop, #step2-draw { display: none; }
        .img-container { width: 100%; height: 55vh; background-color: #333; overflow: hidden; border-radius: 8px; margin-bottom: 10px; }
        #image-to-crop { max-width: 100%; display: block; }
        .canvas-wrapper { width: 100%; overflow: hidden; border: 2px solid #ddd; border-radius: 8px; background-color: #fff; margin-bottom: 10px; display: flex; justify-content: center; }
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
        <button class="btn btn-primary" onclick="document.getElementById('file-input').click()">📷 拍照或選取照片</button>
    </div>
    <div id="step1-crop">
        <div class="hint">請縮放或拖曳圖片以進行裁切</div>
        <div class="img-container"><img id="image-to-crop" src=""></div>
        <div class="btn-row">
            <button class="btn btn-secondary" onclick="resetAll()">取消</button>
            <button class="btn btn-primary" onclick="finishCrop()">下一步: 標記 ➡️</button>
        </div>
    </div>
    <div id="step2-draw">
        <div class="controls-panel">
            <div class="control-item">顏色: <input type="color" id="line-color" value="#ff0000"></div>
            <div class="control-item">粗細: <input type="range" id="line-width" min="1" max="15" value="5"><span id="width-val">5</span></div>
        </div>
        <div class="canvas-wrapper"><canvas id="fabric-canvas"></canvas></div>
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
    const colorInput = document.getElementById('line-color');
    const widthInput = document.getElementById('line-width');
    const widthVal = document.getElementById('width-val');
    document.getElementById('page-title').innerText = TARGET_NAME;
    if (IS_REPORT_MODE) { document.getElementById('category-section').style.display = 'block'; }
    let cropper = null; let fabricCanvas = null; let originalImageWidth = 0;
    widthInput.addEventListener('input', function() { widthVal.innerText = this.value; updateActiveObject(); });
    colorInput.addEventListener('input', function() { updateActiveObject(); });
    function updateActiveObject() { if (!fabricCanvas) return; const activeObj = fabricCanvas.getActiveObject(); if (activeObj) { activeObj.set({ stroke: colorInput.value, strokeWidth: parseInt(widthInput.value, 10) }); fabricCanvas.requestRenderAll(); } }
    document.getElementById('file-input').addEventListener('change', function(e) { const file = e.target.files[0]; if (file) { statusEl.innerText = "讀取中..."; const reader = new FileReader(); reader.onload = function(evt) { imgElement.src = evt.target.result; startCropMode(); statusEl.innerText = ""; }; reader.readAsDataURL(file); } this.value = ''; });
    function startCropMode() { step0.style.display = 'none'; step1.style.display = 'block'; step2.style.display = 'none'; if (cropper) { cropper.destroy(); } setTimeout(() => { cropper = new Cropper(imgElement, { viewMode: 1, dragMode: 'move', autoCropArea: 0.9, restore: false, guides: true, center: true, highlight: false, cropBoxMovable: true, cropBoxResizable: true, toggleDragModeOnDblclick: false, }); }, 100); }
    function finishCrop() { if (!cropper) return; statusEl.innerText = "處理中..."; const croppedCanvas = cropper.getCroppedCanvas({ maxWidth: 4096, maxHeight: 4096, imageSmoothingQuality: 'high', }); if (!croppedCanvas) { alert("裁切失敗"); return; } originalImageWidth = croppedCanvas.width; const croppedImageURL = croppedCanvas.toDataURL('image/jpeg', 0.95); startDrawMode(croppedImageURL, croppedCanvas.width, croppedCanvas.height); }
    function startDrawMode(imageURL, w, h) { step1.style.display = 'none'; step2.style.display = 'block'; statusEl.innerText = ""; const containerWidth = document.querySelector('.container').clientWidth - 34; const scaleFactor = containerWidth / w; const finalWidth = containerWidth; const finalHeight = h * scaleFactor; if (fabricCanvas) { fabricCanvas.dispose(); } const canvasEl = document.getElementById('fabric-canvas'); canvasEl.width = finalWidth; canvasEl.height = finalHeight; fabricCanvas = new fabric.Canvas('fabric-canvas', { width: finalWidth, height: finalHeight, selection: false }); fabric.Image.fromURL(imageURL, function(img) { img.set({ originX: 'left', originY: 'top', scaleX: scaleFactor, scaleY: scaleFactor, selectable: false }); fabricCanvas.setBackgroundImage(img, fabricCanvas.renderAll.bind(fabricCanvas)); addRect(); }); fabricCanvas.on('selection:created', syncControls); fabricCanvas.on('selection:updated', syncControls); }
    function syncControls(e) { const obj = e.selected[0]; if (obj) { colorInput.value = obj.stroke; widthInput.value = obj.strokeWidth; widthVal.innerText = obj.strokeWidth; } }
    function addRect() { if (!fabricCanvas) return; const rect = new fabric.Rect({ left: fabricCanvas.width / 4, top: fabricCanvas.height / 4, width: fabricCanvas.width / 3, height: fabricCanvas.height / 3, fill: 'transparent', stroke: colorInput.value, strokeWidth: parseInt(widthInput.value, 10), cornerColor: 'blue', cornerSize: 20, transparentCorners: false, strokeUniform: true }); fabricCanvas.add(rect); fabricCanvas.setActiveObject(rect); }
    function removeActiveObject() { const activeObj = fabricCanvas.getActiveObject(); if (activeObj) { fabricCanvas.remove(activeObj); } }
    function backToCrop() { step2.style.display = 'none'; step1.style.display = 'block'; }
    function resetAll() { if (confirm("重新選取照片？")) { step1.style.display = 'none'; step2.style.display = 'none'; step0.style.display = 'block'; if (cropper) cropper.destroy(); cropper = null; document.getElementById('file-input').value = ''; } }
    function uploadResult() { if (!fabricCanvas) return; fabricCanvas.discardActiveObject(); fabricCanvas.renderAll(); const multiplier = originalImageWidth / fabricCanvas.getWidth(); const dataURL = fabricCanvas.toDataURL({ format: 'jpeg', quality: 1.0, multiplier: multiplier }); statusEl.innerText = "上傳中..."; document.getElementById('btn-upload').disabled = true; const blob = dataURLtoBlob(dataURL); const formData = new FormData(); formData.append('photo', blob, 'upload.jpg'); formData.append('token', UPLOAD_TOKEN); if (IS_REPORT_MODE) { formData.append('category', document.getElementById('category-select').value); } fetch('/upload_endpoint', { method: 'POST', body: formData }).then(response => response.json()).then(data => { if (data.status === 'success') { statusEl.innerText = "✅ 成功"; statusEl.style.color = "green"; setTimeout(() => { alert("上傳成功！"); resetToStart(); }, 500); } else { alert("失敗: " + data.message); statusEl.innerText = ""; document.getElementById('btn-upload').disabled = false; } }).catch(err => { alert("網路錯誤"); statusEl.innerText = ""; document.getElementById('btn-upload').disabled = false; }); }
    function resetToStart() { step1.style.display = 'none'; step2.style.display = 'none'; step0.style.display = 'block'; statusEl.innerText = ""; document.getElementById('btn-upload').disabled = false; document.getElementById('file-input').value = ''; }
    function dataURLtoBlob(dataurl) { var arr = dataurl.split(','), mime = arr[0].match(/:(.*?);/)[1], bstr = atob(arr[1]), n = bstr.length, u8arr = new Uint8Array(n); while(n--){ u8arr[n] = bstr.charCodeAt(n); } return new Blob([u8arr], {type:mime}); }
</script>
</body>
</html>
"""

# ==============================================================================
# SECTION 2: INFRASTRUCTURE LAYER (基礎設施層)
# ==============================================================================


class PhotoServer(QObject):
    photo_received = Signal(str, str, str)  # target_id, category, full_path

    def __init__(self, port=8000):
        super().__init__()
        self.app = Flask(__name__)
        self.port = port
        self.save_dir = ""
        self.active_tokens = {}
        self.server = None
        self.server_thread = None
        self.app.add_url_rule(
            "/upload", "upload_page", self.upload_page, methods=["GET"]
        )
        self.app.add_url_rule(
            "/upload_endpoint",
            "upload_endpoint",
            self.upload_endpoint,
            methods=["POST"],
        )

    def start(self):
        if self.server is not None:
            return
        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()

    def stop(self):
        if self.server:
            try:
                self.server.shutdown()
            except Exception as e:
                print(f"Error stopping server: {e}")
            finally:
                self.server = None
        if self.server_thread:
            self.server_thread.join(timeout=1.0)
            self.server_thread = None

    def _run_server(self):
        try:
            self.server = make_server("0.0.0.0", self.port, self.app, threaded=True)
            self.server.serve_forever()
        except OSError as e:
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
            "timestamp": datetime.now(),
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

    def upload_page(self):
        token = request.args.get("token")
        if token not in self.active_tokens:
            return "連結已失效或錯誤", 404
        data = self.active_tokens[token]
        return render_template_string(
            MOBILE_HTML_TEMPLATE,
            token=token,
            target_name=data["name"],
            is_report=data["is_report"],
        )

    def upload_endpoint(self):
        token = request.form.get("token")
        if token not in self.active_tokens:
            return jsonify({"status": "error", "message": "無效 Token"}), 400
        file = request.files.get("photo")
        if not file:
            return jsonify({"status": "error", "message": "無檔案"}), 400
        task_info = self.active_tokens[token]
        category = request.form.get("category", "default")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_id = task_info["id"].replace(".", "_")
        filename = f"{safe_id}_{category}_{ts}.jpg"
        if not self.save_dir:
            return jsonify({"status": "error", "message": "伺服器儲存路徑未設定"}), 500
        save_path = os.path.join(self.save_dir, filename)
        try:
            file.save(save_path)
            self.photo_received.emit(task_info["id"], category, save_path)
            return jsonify({"status": "success"})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500


# ==============================================================================
# SECTION 2.5: TOOL HANDLER SYSTEM (新增：檢測工具處理層)
# ==============================================================================


class BaseTestTool(QObject):
    """
    通用檢測工具 (Universal Test Tool)：
    1. 內建 UI：顯示規範敘述、檢查表、備註欄。
    2. 內建邏輯：支援 AND/OR 判定、自動換行 Checkbox、自動生成未通過原因。
    """
    data_updated = Signal(dict)
    status_changed = Signal(str) 
    checklist_changed = Signal() 

    def __init__(self, config, result_data, target):
        super().__init__()
        self.config = config        
        self.result_data = result_data 
        self.target = target        
        self.widget = QWidget()
        
        # 內部狀態
        self.checks = {} 
        self.item_content_map = {} 
        self.logic = self.config.get("logic", "AND").upper()

        # 初始化 UI 與載入資料
        self._init_ui()
        if result_data:
            self.load_data(result_data)

    def get_widget(self) -> QWidget:
        return self.widget

    # [New] 提供外部正確獲取備註文字的方法
    def get_user_note(self) -> str:
        return self.user_note.toPlainText()

    # [New] 提供外部設定備註文字的方法
    def set_user_note(self, text: str):
        if self.user_note.toPlainText() != text:
            self.user_note.setPlainText(text)

    def _init_ui(self):
        """建構完整的檢測 UI"""
        layout = QVBoxLayout(self.widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # 1. 邏輯提示
        logic_desc = "須符合所有項目 (AND)" if self.logic == "AND" else "符合任一項目即可 (OR)"
        lbl_logic = QLabel(f"判定邏輯: {logic_desc}")
        lbl_logic.setStyleSheet("color: #1976D2; font-weight: bold; font-size: 11pt;")
        layout.addWidget(lbl_logic)

        # 2. 規範敘述區
        narrative = self.config.get("narrative", {})
        checklist_data = self.config.get("checklist", [])
        
        method_text = narrative.get("method", "無測試方法描述")
        criteria_text = narrative.get("criteria", "")
        
        # 自動生成判定標準
        if not criteria_text and checklist_data:
            header = "符合下列【任一】項目者為通過" if self.logic == "OR" else "符合下列【所有】項目者為通過"
            lines = [f"({i+1}) {item.get('content', '')}" for i, item in enumerate(checklist_data)]
            criteria_text = f"{header}，否則為未通過：\n" + "\n".join(lines)
            
        method_html = method_text.replace("\n", "<br>")
        criteria_html = criteria_text.replace("\n", "<br>")

        display_html = (
            f"<b style='color:#333;'>【測試方法】</b>"
            f"<div style='margin-left:10px; color:#555;'>{method_html}</div>"
            f"<b style='color:#333;'>【判定標準】</b>"
            f"<div style='margin-left:10px; color:#D32F2F;'>{criteria_html}</div>"
        )
        
        # 這是第一個 QTextEdit (規範說明)
        self.desc_edit = QTextEdit()
        self.desc_edit.setHtml(display_html)
        self.desc_edit.setReadOnly(True) 
        self.desc_edit.setStyleSheet("background-color: #f5f5f5; border: 1px solid #ddd; border-radius: 4px; font-size: 11pt; padding: 5px;")
        self.desc_edit.setMinimumHeight(150)
        self.desc_edit.setLineWrapMode(QTextEdit.WidgetWidth)
        self.desc_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        g1 = QGroupBox("規範說明")
        v1 = QVBoxLayout()
        v1.addWidget(self.desc_edit)
        g1.setLayout(v1)
        layout.addWidget(g1)

        # 3. Checkbox 區塊
        if checklist_data:
            checklist_widget = self._create_checklist_widget(checklist_data)
            layout.addWidget(checklist_widget)
        
        # 4. 備註/觀察結果區
        g3 = QGroupBox("判定原因 / 備註")
        v3 = QVBoxLayout()
        # 這是第二個 QTextEdit (備註欄)
        self.user_note = QTextEdit()
        self.user_note.setPlaceholderText("合格時可留空，不合格時系統將自動帶入原因...")
        self.user_note.setFixedHeight(80)
        v3.addWidget(self.user_note)
        g3.setLayout(v3)
        layout.addWidget(g3)

    def _create_checklist_widget(self, checklist_data: list) -> QGroupBox:
        gb = QGroupBox("細項檢查表 (Checklist)")
        layout = QVBoxLayout()
        layout.setSpacing(8)

        for item in checklist_data:
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(10)

            chk = QCheckBox()
            chk.setFixedWidth(25) 
            chk.setStyleSheet("QCheckBox::indicator { width: 20px; height: 20px; }")
            
            content = item.get('content', item.get('id'))
            self.item_content_map[item['id']] = content 
            
            lbl = QLabel(content)
            lbl.setWordWrap(True)
            lbl.setStyleSheet("font-size: 11pt; line-height: 1.2;")
            lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)

            chk.stateChanged.connect(self._on_check_changed)
            self.checks[item['id']] = chk

            row_layout.addWidget(chk, 0, Qt.AlignTop)
            row_layout.addWidget(lbl, 1)
            layout.addWidget(row_widget)

        gb.setLayout(layout)
        return gb

    def _on_check_changed(self):
        status, fail_reason = self.calculate_result()
        self.status_changed.emit(status)
        
        if status == STATUS_FAIL:
            self.user_note.setPlainText(fail_reason)
        else:
            curr_text = self.user_note.toPlainText()
            if "未通過" in curr_text or "未符合" in curr_text:
                self.user_note.setPlainText("符合規範要求。")

    def calculate_result(self) -> Tuple[str, str]:
        if not self.checks:
            return STATUS_FAIL, "無檢查項目"

        criteria_res = {k: c.isChecked() for k, c in self.checks.items()}
        values = list(criteria_res.values())
        
        is_pass = False
        if self.logic == "OR":
            is_pass = any(values)
        else:
            is_pass = all(values) 

        status = STATUS_PASS if is_pass else STATUS_FAIL
        fail_reason = ""

        if status == STATUS_FAIL:
            fail_list = []
            if self.logic == "AND":
                for cid, checked in criteria_res.items():
                    if not checked:
                        fail_list.append(self.item_content_map.get(cid, cid))
                if fail_list:
                    fail_reason = "未通過，原因如下：\n" + "\n".join(f"- 未符合：{r}" for r in fail_list)
            elif self.logic == "OR":
                fail_reason = "未通過，原因：上述所有項目皆未符合。"

        return status, fail_reason

    def get_result(self) -> Dict:
        status, _ = self.calculate_result()
        criteria_res = {k: c.isChecked() for k, c in self.checks.items()}
        return {
            "criteria": criteria_res,
            "description": self.user_note.toPlainText(),
            "auto_suggest_result": status
        }

    def load_data(self, data):
        saved_criteria = data.get("criteria", {})
        
        # 1. 回填 Checkbox (暫停訊號)
        for cid, chk in self.checks.items():
            if cid in saved_criteria:
                chk.blockSignals(True)
                chk.setChecked(saved_criteria[cid])
                chk.blockSignals(False)
        
        # 2. 回填文字
        self.user_note.setPlainText(data.get("description", ""))

class ToolFactory:
    @staticmethod
    def create_tool(class_name, config, result_data, target) -> BaseTestTool:
        if class_name == "BaseTestTool":
            return BaseTestTool(config, result_data, target)
        return BaseTestTool(config, result_data, target)


# ==============================================================================
# SECTION 3: CORE LOGIC LAYER (核心邏輯層)
# ==============================================================================


class ConfigManager:
    def __init__(self, config_dir=CONFIG_DIR):
        self.config_dir = config_dir
        self._ensure_dir()

    def _ensure_dir(self):
        if not os.path.exists(self.config_dir):
            try:
                os.makedirs(self.config_dir)
            except OSError as e:
                print(f"Error creating config dir: {e}")

    def list_available_configs(self) -> List[Dict[str, str]]:
        configs = []
        if not os.path.exists(self.config_dir):
            return configs
        for filename in os.listdir(self.config_dir):
            if filename.endswith(".json"):
                full_path = os.path.join(self.config_dir, filename)
                display_name = filename
                try:
                    with open(full_path, "r", encoding="utf-8-sig") as f:
                        data = json.load(f)
                        if "standard_name" in data:
                            display_name = data["standard_name"]
                        elif "standard_version" in data:
                            display_name = f"規範版本 {data['standard_version']} ({filename})"
                except Exception as e:
                    display_name = f"{filename} (讀取錯誤)"
                configs.append({"name": display_name, "path": full_path})
        configs.sort(key=lambda x: x["name"], reverse=True)
        return configs

    def _validate_config_integrity(self, data: Dict, filename: str):
        if "test_standards" not in data:
            raise ValueError(f"檔案 {filename} 格式錯誤：缺少 'test_standards' 欄位")
        for section in data.get("test_standards", []):
            sec_id = section.get("section_id", "Unknown")
            for item in section.get("items", []):
                item_id = item.get("id", "Unknown ID")
                if "uid" not in item or not item["uid"]:
                    raise ValueError(
                        f"規範完整性檢查失敗！\n檔案: {filename}\n位置: Section {sec_id} -> Item {item_id}\n原因: 缺少必要的 'uid' 欄位。\n無法載入不含 UID 的規範。"
                    )

    def load_config(self, path: str) -> Dict:
        filename = os.path.basename(path)
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            self._validate_config_integrity(data, filename)
            return data
        except json.JSONDecodeError as e:
            raise ValueError(f"檔案 {filename} 不是有效的 JSON 格式")
        except Exception as e:
            print(f"Loading config failed: {e}")
            raise e

    def find_config_by_name(self, target_name: str) -> Optional[Dict]:
        configs = self.list_available_configs()
        for cfg in configs:
            if cfg["name"] == target_name:
                try:
                    return self.load_config(cfg["path"])
                except:
                    return None
        return None
    
    def get_latest_config(self) -> Optional[Dict]:
        """取得列表中的第一個（最新）規範設定"""
        configs = self.list_available_configs()
        if configs:
            try:
                return self.load_config(configs[0]['path'])
            except:
                return None
        return None    


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

    def save_snapshot(self, note="backup"):
        if not self.current_project_path:
            return False
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        std_name = self.project_data.get("standard_name", "unknown").replace(" ", "_")
        filename = f"snapshot_{std_name}_{timestamp}_{note}.json"
        src = os.path.join(self.current_project_path, self.settings_filename)
        dst = os.path.join(self.current_project_path, filename)
        try:
            shutil.copy2(src, dst)
            return True, filename
        except Exception as e:
            return False, str(e)

    def list_snapshots(self) -> List[str]:
        if not self.current_project_path:
            return []
        snaps = []
        for f in os.listdir(self.current_project_path):
            if f.startswith("snapshot_") and f.endswith(".json"):
                snaps.append(f)
        snaps.sort(reverse=True)
        return snaps

    def restore_snapshot(self, snapshot_filename):
        if not self.current_project_path:
            return False
        src = os.path.join(self.current_project_path, snapshot_filename)
        dst = os.path.join(self.current_project_path, self.settings_filename)
        try:
            shutil.copy2(src, dst)
            return self.load_project(self.current_project_path)
        except Exception as e:
            return False, str(e)

    def calculate_migration_impact(self, new_config) -> List[Dict]:
        report = []
        current_tests = self.project_data.get("tests", {})
        new_uids = set()

        if "test_standards" not in new_config:
            raise ValueError("無效的規範設定檔 (缺少 test_standards)")

        for section in new_config.get("test_standards", []):
            for item in section.get("items", []):
                uid = item.get("uid")
                if not uid:
                    raise ValueError(f"新規範中發現缺少 UID 的項目: {item.get('name')}")
                new_uids.add(uid)
                status = "NEW"
                msg = "新規範新增項目"
                if uid in current_tests:
                    old_data = current_tests[uid]
                    old_ver = "unknown"
                    for t in TARGETS:
                        if t in old_data and "criteria_version_snapshot" in old_data[t]:
                            old_ver = old_data[t]["criteria_version_snapshot"]
                            break
                    new_ver = item.get("criteria_version")

                    if old_ver == new_ver:
                        status = "MATCH"
                        msg = "標準未變，完全沿用"
                    else:
                        status = "RESET"
                        msg = f"標準變更 ({old_ver} -> {new_ver})，需重判"

                report.append(
                    {"uid": uid, "name": item.get("name"), "status": status, "msg": msg}
                )

        for uid in current_tests.keys():
            if uid not in new_uids and uid != "__meta__":
                report.append(
                    {
                        "uid": uid,
                        "name": f"Unknown ({uid})",
                        "status": "REMOVE",
                        "msg": "新規範已移除此項目",
                    }
                )

        return report

    def apply_version_switch(self, new_config, migration_report):
        self.save_snapshot("before_switch")
        old_tests_data = self.project_data.get("tests", {})
        new_tests_data = {}
        new_item_map = {}
        for sec in new_config["test_standards"]:
            for item in sec["items"]:
                new_item_map[item["uid"]] = item

        for row in migration_report:
            uid = row["uid"]
            status = row["status"]
            if status == "REMOVE":
                continue
            new_item_def = new_item_map.get(uid)
            new_ver = (
                new_item_def.get("criteria_version") if new_item_def else "unknown"
            )

            if status == "NEW":
                new_tests_data[uid] = {}  # 初始化
            elif status == "MATCH":
                new_tests_data[uid] = old_tests_data[uid].copy()
            elif status == "RESET":
                old_entry = old_tests_data[uid]
                new_entry = {}
                for target in TARGETS:
                    if target in old_entry:
                        new_entry[target] = {}
                        if "report_path" in old_entry[target]:
                            new_entry[target]["report_path"] = old_entry[target][
                                "report_path"
                            ]
                        new_entry[target]["result"] = STATUS_UNCHECKED
                        new_entry[target]["criteria_version_snapshot"] = new_ver
                new_tests_data[uid] = new_entry

        self.project_data["standard_name"] = new_config.get("standard_name")
        self.project_data["standard_version"] = new_config.get("standard_version")
        self.project_data["tests"] = new_tests_data
        self.set_standard_config(new_config)
        self.save_all()
        self.data_changed.emit()

    def handle_mobile_photo(self, target_id, category, full_path):
        if self.current_project_path:
            rel_path = os.path.relpath(full_path, self.current_project_path)
            rel_path = rel_path.replace("\\", "/")
        else:
            rel_path = full_path
        if target_id in TARGETS:
            info_key = f"{target_id}_{category}_path"
            self.update_info({info_key: rel_path})
        self.photo_received.emit(target_id, category, rel_path)

    def generate_mobile_link(
        self, target_id, target_name, is_report=False
    ) -> Optional[str]:
        if not self.current_project_path:
            return None
        if not self.server.is_running():
            self.server.start()
        save_dir = os.path.join(self.current_project_path, DIR_IMAGES)
        self.server.set_save_directory(save_dir)
        token = self.server.generate_token(target_id, target_name, is_report)
        ip = self.server.get_local_ip()
        return f"http://{ip}:{self.server.port}/upload?token={token}"

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
            return any(item.get("uid") in whitelist for item in section_items)
        else:
            scope = info.get("test_scope", [])
            if not scope and "test_scope" not in info:
                return True
            return str(section_id) in scope

    def _find_section_id_by_item(self, item_identifier) -> str:
        """
        根據 ID 或 UID 查找該項目所屬的 section_id
        [Fix] 同時比對 id 與 uid，確保傳入任何一種都能找到章節
        """
        for sec in self.std_config.get("test_standards", []):
            for item in sec["items"]:
                # 只要 id 相符 或 uid 相符，就回傳該章節 ID
                if item.get("id") == item_identifier or item.get("uid") == item_identifier:
                    return str(sec["section_id"])
        return ""

    def _get_items_in_section(self, section_id) -> List[Dict]:
        for sec in self.std_config.get("test_standards", []):
            if str(sec["section_id"]) == str(section_id):
                return sec["items"]
        return []

    def create_project(self, form_data: dict) -> Tuple[bool, str]:
        raw_base_path = form_data.get("save_path")
        project_name = form_data.get("project_name")
        if not raw_base_path or not project_name:
            return False, "缺少儲存路徑或專案名稱"
        base_path = os.path.abspath(os.path.expanduser(raw_base_path))
        target_folder = os.path.join(base_path, project_name)
        final_path = self._get_unique_path(target_folder)
        form_data["project_name"] = os.path.basename(final_path)
        form_data["project_type"] = PROJECT_TYPE_FULL
        current_std_name = self.std_config.get("standard_name", "Unknown")
        current_std_version = self.std_config.get("standard_version", "Unknown")
        self.project_data = {
            "standard_version": current_std_version,
            "standard_name": current_std_name,
            "info": form_data,
            "tests": {},
        }
        return self._init_folder_and_save(final_path)

    def create_ad_hoc_project(
        self, selected_items: list, save_base_path: str
    ) -> Tuple[bool, str]:
        ts_str = datetime.now().strftime(DATE_FMT_PY_FILENAME_SHORT)
        folder_name = f"QuickTest_{ts_str}"
        target_folder = os.path.join(save_base_path, folder_name)
        final_path = self._get_unique_path(target_folder)
        info_data = {}
        schema = self.std_config.get("project_meta_schema", [])
        for field in schema:
            key = field.get("key")
            f_type = field.get("type")
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
        current_std_name = self.std_config.get("standard_name", "Unknown")
        current_std_version = self.std_config.get("standard_version", "Unknown")
        self.project_data = {
            "standard_version": current_std_version,
            "standard_name": current_std_name,
            "info": info_data,
            "tests": {},
        }
        return self._init_folder_and_save(final_path)


    def fork_project_to_new_version(self, new_project_name, new_config, migration_report) -> Tuple[bool, str]:
        """
        另存新檔並升級規範版本：
        1. 建立新資料夾。
        2. 複製 images/reports 資料夾。
        3. 根據 migration_report 產生新的 project_settings.json。
        """
        if not self.current_project_path:
            return False, "未開啟專案"

        # 1. 準備路徑
        # 假設新專案建立在原專案的「同層目錄」
        parent_dir = os.path.dirname(self.current_project_path)
        new_project_path = os.path.join(parent_dir, new_project_name)
        
        if os.path.exists(new_project_path):
            return False, "目標資料夾已存在，請更換名稱。"
        
        try:
            os.makedirs(new_project_path)
            
            # 2. 複製資源資料夾 (images, reports)
            for folder in [DIR_IMAGES, DIR_REPORTS]:
                src = os.path.join(self.current_project_path, folder)
                dst = os.path.join(new_project_path, folder)
                if os.path.exists(src):
                    shutil.copytree(src, dst)
                else:
                    os.makedirs(dst) # 若原專案沒有，新專案也要建空的
            
            # 3. 準備新的專案資料 (基於 migration_report)
            old_data = self.project_data
            new_data = {
                "standard_version": new_config.get("standard_version"),
                "standard_name": new_config.get("standard_name"),
                "info": old_data.get("info", {}).copy(),
                "tests": {}
            }
            
            # 更新專案名稱
            new_data["info"]["project_name"] = new_project_name
            
            # 處理測項資料遷移
            old_tests = old_data.get("tests", {})
            new_tests = {}
            
            # 建立 UID -> New Item 的對照，方便取用新版資訊
            uid_to_new_item = {}
            for sec in new_config.get("test_standards", []):
                for item in sec["items"]:
                    uid_to_new_item[item["uid"]] = item

            # 根據遷移報告決定資料去留
            for row in migration_report:
                uid = row["uid"]
                status = row["status"]
                
                if status == "REMOVE":
                    continue # 移除的就不帶過去了
                
                if status == "NEW":
                    new_tests[uid] = {} # 新增的初始化為空
                
                elif status == "MATCH":
                    # 完全沿用
                    if uid in old_tests:
                        new_tests[uid] = old_tests[uid].copy()
                        
                elif status == "RESET":
                    # 版本變更，重置結果但保留照片連結
                    if uid in old_tests:
                        old_entry = old_tests[uid]
                        new_entry = {}
                        
                        # 取得該項目在新規範的版本號
                        new_ver = uid_to_new_item[uid].get("criteria_version", "unknown")
                        
                        for target in TARGETS: # UAV, GCS
                            if target in old_entry:
                                new_entry[target] = {}
                                # 保留照片路徑
                                if "report_path" in old_entry[target]:
                                    new_entry[target]["report_path"] = old_entry[target]["report_path"]
                                # 重置結果
                                new_entry[target]["result"] = STATUS_UNCHECKED
                                # 更新快照版本
                                new_entry[target]["criteria_version_snapshot"] = new_ver
                                # 添加備註
                                old_desc = old_entry[target].get("description", "")
                                new_entry[target]["description"] = f"[系統] 因規範版本變更 ({old_entry[target].get('criteria_version_snapshot')} -> {new_ver})，請重新判定。\n{old_desc}"
                        
                        new_tests[uid] = new_entry
                        # 別忘了複製 Meta
                        if "__meta__" in old_entry:
                            new_entry["__meta__"] = old_entry["__meta__"].copy()

            new_data["tests"] = new_tests

            # 4. 寫入新的 json 檔案
            new_json_path = os.path.join(new_project_path, self.settings_filename)
            with open(new_json_path, "w", encoding="utf-8") as f:
                json.dump(new_data, f, ensure_ascii=False, indent=4)
                
            return True, new_project_path

        except Exception as e:
            # 發生錯誤時嘗試清理殘局 (刪除建立到一半的資料夾)
            if os.path.exists(new_project_path):
                shutil.rmtree(new_project_path)
            return False, str(e)

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

    def peek_project_standard(self, folder_path: str) -> Optional[str]:
        json_path = os.path.join(folder_path, self.settings_filename)
        if not os.path.exists(json_path):
            return None
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("standard_name")
        except:
            return None

    def load_project(self, folder_path: str) -> Tuple[bool, str]:
        json_path = os.path.join(folder_path, self.settings_filename)
        if not os.path.exists(json_path):
            return False, "找不到專案設定檔"
        try:
            with open(json_path, "r", encoding="utf-8") as f:
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
            return False, "來源無效 (找不到 project_settings.json)"
            
        try:
            with open(source_json_path, "r", encoding="utf-8") as f:
                source_data = json.load(f)
            
            # 1. 檢查類型
            if source_data.get("info", {}).get("project_type") != PROJECT_TYPE_ADHOC:
                return False, "只能合併 Ad-Hoc 類型的專案"

            # 2. [Modified] 嚴格檢查規範版本 (Standard Name)
            src_std = source_data.get("standard_name", "")
            curr_std = self.project_data.get("standard_name", "")
            
            if src_std != curr_std:
                return False, f"規範版本不符，無法合併！\n\n主專案規範: {curr_std}\n來源檔規範: {src_std}\n\n(各別檢測模式的結果必須與主專案規範完全一致才可合併)"

            # --- 以下為原本的合併邏輯 (複製檔案與數據) ---
            
            # 3. 複製檔案
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

            # 4. 合併測試數據 (因為規範相同，直接合併即可)
            source_tests = source_data.get("tests", {})
            current_tests = self.project_data.get("tests", {})
            merged_count = 0
            
            for test_id, targets_data in source_tests.items():
                if test_id not in current_tests:
                    current_tests[test_id] = {}
                for target, result_data in targets_data.items():
                    # 直接覆寫，因為已確認規範一致
                    current_tests[test_id][target] = result_data
                    merged_count += 1
            
            self.save_all()
            self.data_changed.emit()
            return True, f"成功合併 {merged_count} 筆測項資料"
            
        except Exception as e:
            return False, f"合併失敗: {str(e)}"
        
    def update_info(self, new_info):
        if not self.current_project_path:
            return False
        self.project_data.setdefault("info", {}).update(new_info)
        self.save_all()
        self.data_changed.emit()
        return True

    def update_test_result(self, test_uid, target, result_data, is_shared=False):
        if "tests" not in self.project_data:
            self.project_data["tests"] = {}
        if test_uid not in self.project_data["tests"]:
            self.project_data["tests"][test_uid] = {}
        self.project_data["tests"][test_uid][target] = result_data
        self.project_data["tests"][test_uid][target][
            "last_updated"
        ] = datetime.now().strftime(DATE_FMT_PY_DATETIME)
        meta = self.project_data["tests"][test_uid].setdefault("__meta__", {})
        meta["is_shared"] = is_shared
        self.save_all()
        self.data_changed.emit()

    def update_adhoc_items(self, new_whitelist, removed_items):
        """[New] 更新 Ad-Hoc 白名單，並刪除被移除項目的資料"""
        if not self.current_project_path: return

        # 1. 更新 Info
        self.project_data.setdefault("info", {})["target_items"] = new_whitelist
        
        # 2. 刪除資料
        tests_data = self.project_data.get("tests", {})
        for uid in removed_items:
            if uid in tests_data:
                del tests_data[uid]
                print(f"Deleted data for: {uid}")
        
        self.save_all()
        self.data_changed.emit()

    def get_test_meta(self, test_uid):
        return self.project_data.get("tests", {}).get(test_uid, {}).get("__meta__", {})

    def save_all(self):
        if not self.current_project_path:
            return False, "No Path"
        path = os.path.join(self.current_project_path, self.settings_filename)
        temp_path = path + ".tmp"
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self.project_data, f, ensure_ascii=False, indent=4)
                f.flush()
                os.fsync(f.fileno()) # 強制寫入磁碟
            
            # 2. 原子寫入
            if os.path.exists(path):
                os.replace(temp_path, path)
            else:
                os.rename(temp_path, path)
                
            return True, "Saved"
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return False, str(e)

    def get_test_status_detail(self, item_config) -> Dict[str, str]:
        uid = item_config.get("uid", item_config.get("id"))
        targets = item_config.get("targets", [TARGET_GCS])
        item_data = self.project_data.get("tests", {}).get(uid, {})
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
        uid = item_config.get("uid", item_config.get("id"))
        targets = item_config.get("targets", [TARGET_GCS])
        saved = self.project_data.get("tests", {}).get(uid, {})
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
    def __init__(self, parent, pm, url, title="手機掃碼上傳"):
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


class VersionSelectionDialog(QDialog):
    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("選擇檢測規範版本")
        self.resize(400, 200)
        self.cm = config_manager
        self.selected_config = None
        self.selected_path = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h2>請選擇本次檢測使用的規範版本：</h2>"))
        self.combo = QComboBox()
        self.configs = self.cm.list_available_configs()
        if not self.configs:
            self.combo.addItem("找不到設定檔 (請檢查 configs 資料夾)")
            self.combo.setEnabled(False)
        else:
            for cfg in self.configs:
                self.combo.addItem(cfg["name"], cfg["path"])
        layout.addWidget(self.combo)
        hint = QLabel("設定檔請放置於程式目錄下的 'configs' 資料夾中")
        hint.setStyleSheet("color: gray; font-size: 10pt;")
        layout.addWidget(hint)
        layout.addStretch()
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.on_accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def on_accept(self):
        if not self.configs:
            return
        idx = self.combo.currentIndex()
        path = self.combo.itemData(idx)
        try:
            data = self.cm.load_config(path)
            if "test_standards" not in data:
                raise ValueError("JSON 格式不符 (缺少 test_standards)")
            self.selected_config = data
            self.selected_path = path
            self.accept()
        except ValueError as ve:
            QMessageBox.critical(self, "規範驗證失敗", str(ve))
        except Exception as e:
            QMessageBox.critical(self, "讀取失敗", f"設定檔無效：\n{str(e)}")


class MigrationReportDialog(QDialog):
    def __init__(self, parent, report):
        super().__init__(parent)
        self.setWindowTitle("規範遷移預覽報告")
        self.resize(700, 500)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h3>即將切換規範版本，請確認以下變更：</h3>"))
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["測項名稱", "UID", "狀態", "說明"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        table.setRowCount(len(report))
        for i, row in enumerate(report):
            table.setItem(i, 0, QTableWidgetItem(row["name"]))
            table.setItem(i, 1, QTableWidgetItem(row["uid"]))
            status_item = QTableWidgetItem(row["status"])
            if row["status"] == "MATCH":
                status_item.setForeground(QImage(COLOR_TEXT_PASS))
            elif row["status"] == "RESET":
                status_item.setForeground(Qt.red)
            elif row["status"] == "NEW":
                status_item.setForeground(Qt.blue)
            table.setItem(i, 2, status_item)
            table.setItem(i, 3, QTableWidgetItem(row["msg"]))
        layout.addWidget(table)
        hint = QLabel("注意：切換前系統將自動備份目前的專案設定檔。")
        hint.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(hint)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)


class SingleTargetTestWidget(QWidget):
    def __init__(self, target, config, pm, save_cb=None):
        super().__init__()
        self.target = target
        self.config = config
        self.pm = pm
        self.item_uid = config.get("uid", config.get("id"))
        self.save_cb = save_cb
        self.logic = config.get("logic", "AND").upper()

        handler_cfg = config.get("handler", {})
        class_name = handler_cfg.get("class_name", "BaseTestTool")

        item_data = self.pm.project_data.get("tests", {}).get(self.item_uid, {})
        target_key = self.target
        if self.target == "Shared":
            target_key = self.config.get("targets", [TARGET_GCS])[0]
        self.saved_data = item_data.get(target_key, {})

        self.tool = ToolFactory.create_tool(class_name, config, self.saved_data, target)

        self._init_ui()

        self.tool.status_changed.connect(self.update_combo_from_tool)
        self.pm.photo_received.connect(self.on_photo_received)

    def update_combo_from_tool(self, new_status):
        """[New] 當工具判定狀態改變時，自動更新下拉選單"""
        self.combo.setCurrentText(new_status)
        # update_color 會因為 CurrentTextChanged 而自動被觸發，所以這裡不用手動呼叫

    def _init_ui(self):
        l = QVBoxLayout(self)
        h = QHBoxLayout()
        h.addWidget(QLabel(f"<h3>對象: {self.target}</h3>"))
        h.addWidget(QLabel(f"({self.logic})"))
        h.addStretch()
        l.addLayout(h)
        l.addWidget(self.tool.get_widget())

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

        self.current_report_path = self.saved_data.get("report_path")
        if self.current_report_path:
            self.lbl_file.setText(os.path.basename(self.current_report_path))

        g3 = QGroupBox("最終判定")
        h3 = QHBoxLayout()
        h3.addWidget(QLabel("結果:"))
        self.combo = QComboBox()
        self.combo.addItems([STATUS_UNCHECKED, STATUS_PASS, STATUS_FAIL, STATUS_NA])
        self.combo.currentTextChanged.connect(self.update_color)
        saved_res = self.saved_data.get("result", STATUS_UNCHECKED)
        idx = self.combo.findText(saved_res)
        if idx >= 0:
            self.combo.setCurrentIndex(idx)
        self.update_color(saved_res)
        h3.addWidget(self.combo)
        g3.setLayout(h3)
        l.addWidget(g3)
        l.addStretch()
        btn = QPushButton(f"儲存 ({self.target})")
        btn.setStyleSheet(
            "background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;"
        )
        btn.clicked.connect(self.on_save)
        l.addWidget(btn)

    def upload_report_pc(self):
        if not self.pm.current_project_path:
            return
        f, _ = QFileDialog.getOpenFileName(
            self, "選擇檔案", "", "Files (*.pdf *.html *.txt *.jpg *.png)"
        )
        if f:
            rel = self.pm.import_file(f, DIR_REPORTS)
            if rel:
                self.current_report_path = rel
                self.lbl_file.setText(os.path.basename(rel))

    def upload_report_mobile(self):
        if not self.pm.current_project_path:
            return
        title = f"{self.item_uid} 佐證 ({self.target})"
        url = self.pm.generate_mobile_link(self.item_uid, title, is_report=False)
        if url:
            QRCodeDialog(self, self.pm, url, title).exec()

    @Slot(str, str, str)
    def on_photo_received(self, target_id, category, path):
        if target_id == self.item_uid:
            self.current_report_path = path
            self.lbl_file.setText(f"收到: {os.path.basename(path)}")
            QMessageBox.information(
                self,
                "收到佐證",
                f"已收到手機上傳的佐證照片：\n{os.path.basename(path)}",
            )

    def update_color(self, t):
        """
        根據下拉選單的文字改變顏色，並自動更新備註欄引導文字。
        """
        s = ""
        # [Fix] 使用 get_user_note() 確保讀到正確的欄位
        current_note = self.tool.get_user_note()

        if STATUS_PASS in t:
            s = f"background-color: {COLOR_BG_PASS}; color: {COLOR_TEXT_PASS};"
            if not current_note or "未通過" in current_note or "不適用" in current_note:
                self.tool.set_user_note("符合規範要求。")
                
        elif STATUS_FAIL in t:
            s = f"background-color: {COLOR_BG_FAIL}; color: {COLOR_TEXT_FAIL};"
            if "符合規範" in current_note or "不適用" in current_note:
                _, fail_reason = self.tool.calculate_result()
                self.tool.set_user_note(fail_reason if fail_reason else "未通過，原因：")

        elif STATUS_NA in t:
            s = f"background-color: {COLOR_BG_NA};"
            if not current_note or "符合規範" in current_note or "未通過" in current_note:
                self.tool.set_user_note("不適用，原因如下：\n")
                
        self.combo.setStyleSheet(s)

    # 在 SingleTargetTestWidget class 內
    def on_save(self):
        if not self.pm.current_project_path: return
        
        # 1. 取得 Tool 內部的資料
        tool_data = self.tool.get_result()
        
        # 2. 組合資料 (下拉選單已經即時連動，直接讀取即可)
        final_data = tool_data.copy()
        
        # 移除暫存欄位
        if "auto_suggest_result" in final_data:
            del final_data["auto_suggest_result"]

        final_data.update({
            "result": self.combo.currentText(), # 這裡會是使用者看到的最新狀態
            "report_path": self.current_report_path,
            "criteria_version_snapshot": self.config.get("criteria_version")
        })
        
        if self.save_cb:
            self.save_cb(final_data)
        else:
            self.pm.update_test_result(self.item_uid, self.target, final_data)
            QMessageBox.information(self, "成功", "已儲存")

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
        # h.addWidget(QLabel(f"<h2>{self.config['name']}</h2>"))
        # l.addLayout(h)
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
        v.setContentsMargins(0, 0, 0, 0)
        if len(self.targets) > 1:
            tabs = QTabWidget()
            for t in self.targets:
                tabs.addTab(SingleTargetTestWidget(t, self.config, self.pm), t)
            v.addWidget(tabs)
        else:
            v.addWidget(SingleTargetTestWidget(self.targets[0], self.config, self.pm))
        self.stack.addWidget(self.p_sep)
        if len(self.targets) > 1:
            self.p_share = SingleTargetTestWidget(
                "Shared", self.config, self.pm, save_cb=self.save_share
            )
            self.stack.addWidget(self.p_share)

    def _load_state(self):
        uid = self.config.get("uid", self.config.get("id"))
        meta = self.pm.get_test_meta(uid)
        if self.chk and meta.get("is_shared"):
            self.chk.setChecked(True)
            self.stack.setCurrentWidget(self.p_share)

    def on_share(self, checked):
        self.stack.setCurrentWidget(self.p_share if checked else self.p_sep)

    def save_share(self, data):
        uid = self.config.get("uid", self.config.get("id"))
        for t in self.targets:
            self.pm.update_test_result(uid, t, data, is_shared=True)
        QMessageBox.information(self, "成功", "共用儲存完成")


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
        positions = {
            "front": (0, 0),
            "back": (0, 1),
            "top": (0, 2),
            "side1": (1, 0),
            "side2": (1, 1),
            "bottom": (1, 2),
        }
        info_data = self.pm.project_data.get("info", {})
        for angle in PHOTO_ANGLES_ORDER:
            row, col = positions.get(angle, (0, 0))
            container = QFrame()
            container.setFrameShape(QFrame.Box)
            v_box = QVBoxLayout(container)
            lbl_title = QLabel(PHOTO_ANGLES_NAME[angle])
            lbl_title.setAlignment(Qt.AlignCenter)
            lbl_title.setStyleSheet("font-weight: bold; background-color: #eee;")
            lbl_img = QLabel()
            lbl_img.setAlignment(Qt.AlignCenter)
            lbl_img.setMinimumSize(300, 200)
            path_key = f"{self.target_name}_{angle}_path"
            rel_path = info_data.get(path_key)
            if rel_path and self.pm.current_project_path:
                full_path = os.path.join(self.pm.current_project_path, rel_path)
                if os.path.exists(full_path):
                    pixmap = QPixmap(full_path)
                    lbl_img.setPixmap(
                        pixmap.scaled(
                            320, 240, Qt.KeepAspectRatio, Qt.SmoothTransformation
                        )
                    )
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
            for item in section["items"]:
                li = QListWidgetItem(f"{item['id']} {item['name']}")
                li.setFlags(li.flags() | Qt.ItemIsUserCheckable)
                li.setCheckState(Qt.Unchecked)
                li.setData(Qt.UserRole, item.get("uid", item.get("id")))
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
    """
    專案資訊填寫表單控制器。
    [Update] 支援根據 test_standards 動態生成 test_scope 選項。
    """
    def __init__(self, parent_window, full_config, existing_data=None):
        self.full_config = full_config # 接收完整的 config 以讀取 test_standards
        self.meta_schema = full_config.get("project_meta_schema", [])
        self.existing_data = existing_data
        self.is_edit_mode = existing_data is not None
        
        self.dialog = QDialog(parent_window)
        self.dialog.setWindowTitle("編輯專案" if self.is_edit_mode else "新建專案")
        self.dialog.resize(500, 600)
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
            
            if f_type == 'hidden': continue
            
            widget = None
            
            # --- 1. 一般文字輸入 ---
            if f_type == 'text':
                widget = QLineEdit()
                if self.is_edit_mode and key in self.existing_data:
                    widget.setText(str(self.existing_data[key]))
                    # 專案名稱在編輯模式下通常不給改，避免路徑錯亂
                    if key == "project_name":
                        widget.setReadOnly(True)
                        widget.setStyleSheet("background-color:#f0f0f0;")
            
            # --- 2. 日期選擇 ---
            elif f_type == 'date': 
                widget = QDateEdit()
                widget.setCalendarPopup(True)
                widget.setDisplayFormat(DATE_FMT_QT)
                if self.is_edit_mode and key in self.existing_data: 
                    widget.setDate(QDate.fromString(self.existing_data[key], DATE_FMT_QT))
                else: 
                    widget.setDate(QDate.currentDate())
            
            # --- 3. 路徑選擇 ---
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
            
            # --- 4. Checkbox 群組 (動態生成邏輯) ---
            elif f_type == 'checkbox_group':
                widget = QGroupBox()
                v = QVBoxLayout(widget)
                v.setContentsMargins(5, 5, 5, 5)
                
                # [Modified] 動態生成 test_scope 選項
                opts = []
                if key == "test_scope":
                    standards = self.full_config.get("test_standards", [])
                    for sec in standards:
                        opts.append({
                            "value": sec["section_id"], # 使用 section_id 作為 value
                            "label": sec["section_name"] # 使用 section_name 作為 label
                        })
                else:
                    # 若沒有特別需求，則使用 schema 中定義的選項
                    opts = field.get("options", [])

                vals = self.existing_data.get(key, []) if self.is_edit_mode else []
                widget.checkboxes = []
                for o in opts:
                    chk = QCheckBox(o["label"])
                    chk.setProperty("val", o["value"])
                    if self.is_edit_mode:
                        if o["value"] in vals:
                            chk.setChecked(True)
                    else:
                        chk.setChecked(False) # 新建時預設全不選
                    v.addWidget(chk)
                    widget.checkboxes.append(chk)

            if widget:
                form.addRow(label, widget)
                self.inputs[key] = {'w': widget, 't': f_type}
        
        layout.addLayout(form)
        
        # 按鈕區
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
            if files: le.setText(files[0])

    def run(self):
        if self.dialog.exec() == QDialog.Accepted: return self._collect()
        return None

    def _collect(self):
        data = {}
        for key, inf in self.inputs.items():
            w = inf['w']
            t = inf['t']
            if t == 'text': data[key] = w.text()
            elif t == 'date': data[key] = w.date().toString(DATE_FMT_QT)
            elif t == 'path_selector': data[key] = w.line_edit.text()
            elif t == 'checkbox_group': data[key] = [c.property("val") for c in w.checkboxes if c.isChecked()]
        return data

class OverviewPage(QWidget):
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
        photo_g = QGroupBox("檢測照片總覽")
        self.photo_grid = QGridLayout()
        photo_g.setLayout(self.photo_grid)
        self.layout.addWidget(photo_g)
        self.photo_labels = {}
        for col, t in enumerate(TARGETS):
            lbl_title = QLabel(t.upper())
            lbl_title.setAlignment(Qt.AlignCenter)
            lbl_title.setStyleSheet("font-weight: bold; font-size: 16pt; padding: 5px;")
            self.photo_grid.addWidget(lbl_title, 0, col, 1, 1)
            btn_mobile = QPushButton(f"📱 上傳 {t.upper()} 照片 (含各角度)")
            btn_mobile.clicked.connect(partial(self.up_photo_mobile, t))
            self.photo_grid.addWidget(btn_mobile, 1, col, 1, 1)
            front_key = f"{t}_{PHOTO_ANGLES_ORDER[0]}"
            front_container = QWidget()
            front_v = QVBoxLayout(front_container)
            lbl_img = QLabel("正面照片 (Front)\n未上傳")
            lbl_img.setFrameShape(QFrame.NoFrame)
            lbl_img.setFixedSize(320, 240)
            lbl_img.setAlignment(Qt.AlignCenter)
            btn_view = QPushButton("檢視六視角照片")
            btn_view.clicked.connect(partial(self.open_gallery, t))
            btn_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            front_v.addWidget(lbl_img, 0, Qt.AlignCenter)
            front_v.addWidget(btn_view)
            self.photo_grid.addWidget(front_container, 2, col, 1, 1)
            self.photo_labels[front_key] = lbl_img
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
                key = field["key"]
                label_text = field["label"]
                value = info_data.get(key, "-")
                if isinstance(value, list):
                    value = ", ".join(value)
                val_label = QLabel(str(value))
                val_label.setStyleSheet("font-weight: bold; color: #333;")
                val_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
                self.info_layout.addRow(f"{label_text}:", val_label)
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
                if has_file:
                    pix = QPixmap(full_path)
                    if not pix.isNull():
                        scaled_pix = pix.scaled(
                            widget.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
                        )
                        widget.setPixmap(scaled_pix)
                else:
                    widget.setText("正面照片 (Front)\n未上傳")
            else:
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
            sec_id = section["section_id"]
            sec_name = section["section_name"]
            is_visible = self.pm.is_section_visible(sec_id)
            h = QHBoxLayout()
            lbl = QLabel(sec_name)
            lbl.setFixedWidth(150)
            p = QProgressBar()
            if is_visible:
                items = section["items"]
                active_items = []
                for i in items:
                    target_id = i.get("uid", i.get("id"))
                    if self.pm.is_item_visible(target_id):
                        active_items.append(i)
                total = len(active_items)
                done = sum(
                    1 for i in active_items if self.pm.is_test_fully_completed(i)
                )
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
                p.setStyleSheet(
                    f"QProgressBar {{ color: gray; background-color: {COLOR_BG_DEFAULT}; }}"
                )
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
        if not self.pm.current_project_path:
            return
        gallery = GalleryWindow(self, self.pm, target)
        gallery.exec()

    @Slot(str, str, str)
    def on_photo_received(self, target_id, category, path):
        if target_id in TARGETS:
            self.refresh_data()
            QMessageBox.information(
                self,
                "收到照片",
                f"已收到:\n{target_id.upper()} - {category}\n{os.path.basename(path)}",
            )



# ==============================================================================
# SECTION 5: MAIN APPLICATION (程式入口)
# ==============================================================================

class MainApp(QMainWindow):
    def __init__(self, config_mgr):
        super().__init__()
        self.config_mgr = config_mgr
        self.pm = ProjectManager()
        self.test_ui_elements = {}
        self.current_font_size = 10
        
        # 1. 嘗試載入最新規範作為預設 UI 框架 (若無則為 None)
        # 注意: ConfigManager 需要有 get_latest_config() 方法，若沒有請補上，或用 list_available_configs()[0]
        self.config = self._get_initial_config()
        
        # UI 初始化
        self.cw = QWidget()
        self.setCentralWidget(self.cw)
        self.main_l = QVBoxLayout(self.cw)
        
        self._init_menu() # 建立選單
        
        self.tabs = QTabWidget()
        self.main_l.addWidget(self.tabs)
        self._init_zoom()

        # 2. 根據預設規範建立介面，但先鎖定
        if self.config:
            self.rebuild_ui_from_config()
            self._set_ui_locked(True) # [關鍵] 初始狀態：鎖定
            self.setWindowTitle("無人機資安檢測工具 (請從選單建立或開啟專案)")
        else:
            QMessageBox.warning(self, "警告", "找不到任何規範設定檔，請檢查 configs 資料夾。")
            self._set_ui_locked(True)

    def _get_initial_config(self):
        """取得列表中的第一個（最新）規範設定，用於繪製初始畫面"""
        configs = self.config_mgr.list_available_configs()
        if configs:
            try:
                return self.config_mgr.load_config(configs[0]['path'])
            except:
                return None
        return None

    def _set_ui_locked(self, locked: bool):
        """
        鎖定或解鎖 UI 互動。
        locked = True: 剛開啟程式，未載入專案，禁止操作測項。
        locked = False: 專案已載入，允許操作。
        """
        # 鎖定中間的分頁 (讓使用者看得到但不能點)
        self.tabs.setEnabled(not locked)
        
        # 鎖定特定選單功能
        self.a_edit.setEnabled(not locked)
        self.a_merge.setEnabled(not locked)

        
        # 如果是解鎖狀態，將焦點切到總覽頁
        if not locked and self.tabs.count() > 0:
            self.tabs.setCurrentIndex(0)

    def rebuild_ui_from_config(self):
        """根據目前的 self.config 重建介面 (Tabs & Buttons)"""
        if not self.config: return

        # 設定視窗標題
        std_name = self.config.get("standard_name", self.config.get("standard_version", "Unknown"))
        if self.pm.current_project_path:
             proj_name = self.pm.project_data.get("info", {}).get("project_name", "未命名")
             self.setWindowTitle(f"無人機資安檢測工具 - {proj_name} [{std_name}]")
        else:
             self.setWindowTitle(f"無人機資安檢測工具 - {std_name}")

        self.pm.set_standard_config(self.config)
        
        # 清空舊介面
        self.tabs.clear()
        self.test_ui_elements = {}
        
        # 1. 建立總覽頁
        self.overview = OverviewPage(self.pm, self.config)
        self.tabs.addTab(self.overview, "總覽 Overview")
        self.tabs.currentChanged.connect(lambda i: self.overview.refresh_data() if i == 0 else None)
        self.pm.data_changed.connect(self.refresh_ui)

        # 2. 建立各章節頁面
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
            
            for item in sec["items"]:
                row = QWidget()
                rh = QHBoxLayout(row)
                rh.setContentsMargins(0, 5, 0, 5)
                
                # 測項按鈕
                btn = QPushButton(f"{item['id']} {item['name']}")
                btn.setFixedHeight(40)
                btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                btn.clicked.connect(partial(self.open_test, item))

                # 狀態標籤容器
                st_cont = QWidget()
                st_l = QHBoxLayout(st_cont)
                st_l.setContentsMargins(0, 0, 0, 0)
                st_cont.setFixedWidth(240)
                rh.addWidget(btn)
                rh.addWidget(st_cont)
                cv.addWidget(row)
                
                # [關鍵] 使用 UID 作為 Key，若無則 fallback 到 ID
                uid = item.get("uid", item.get("id"))
                self.test_ui_elements[uid] = (btn, st_l, item, row)
            
            cv.addStretch()
            self.tabs.addTab(p, sec["section_id"])
            
        self.update_font()

    def _init_menu(self):
        mb = self.menuBar()
        
        # --- 檔案選單 ---
        f_menu = mb.addMenu("檔案")
        f_menu.addAction("📝 新建專案", self.on_new)
        f_menu.addAction("📂 開啟專案", self.on_open)
        f_menu.addSeparator()
        self.a_edit = f_menu.addAction("編輯專案資訊", self.on_edit) # 初始禁用
        
        # [Deleted] 移除 "版本與快照" 選單
        
        # --- 工具選單 ---
        t_menu = mb.addMenu("工具")
        
        # [New] 另存專案為不同版本規範 (初始禁用，需開啟專案後才可用)
        self.a_save_as_ver = t_menu.addAction("🔄 另存專案為不同版本規範", self.on_save_as_new_version)
        self.a_save_as_ver.setEnabled(False)
        
        t_menu.addSeparator()
        self.a_merge = t_menu.addAction("匯入各別檢測結果 (Merge Ad-Hoc)", self.on_merge) # 初始禁用
        
    def _init_zoom(self):
        self.shortcut_zoom_in = QShortcut(QKeySequence.ZoomIn, self)
        self.shortcut_zoom_in.activated.connect(self.zoom_in)
        self.shortcut_zoom_in_alt = QShortcut(QKeySequence("Ctrl+="), self)
        self.shortcut_zoom_in_alt.activated.connect(self.zoom_in)
        self.shortcut_zoom_out = QShortcut(QKeySequence.ZoomOut, self)
        self.shortcut_zoom_out.activated.connect(self.zoom_out)

    def zoom_in(self):
        if self.current_font_size < 30: self.current_font_size += 2; self.update_font()
    def zoom_out(self):
        if self.current_font_size > 8: self.current_font_size -= 2; self.update_font()
    def update_font(self):
        font_family = '"Microsoft JhengHei", "Segoe UI", sans-serif'
        QApplication.instance().setStyleSheet(f"QWidget {{ font-size: {self.current_font_size}pt; font-family: {font_family}; }}")

    # --- 功能實作 ---

    def on_new(self):
        """新建專案流程：選版本 -> 填資料 -> 建立 -> 解鎖"""
        # 1. 選擇規範版本
        sel_dialog = VersionSelectionDialog(self.config_mgr, self)
        if sel_dialog.exec() != QDialog.Accepted or not sel_dialog.selected_config:
            return
        
        selected_config = sel_dialog.selected_config
        
        # 2. 填寫資料
        c = ProjectFormController(self, selected_config)
        d = c.run()
        if d:
            # 3. 切換 UI 並建立專案
            self.config = selected_config
            self.rebuild_ui_from_config() 
            
            ok, r = self.pm.create_project(d)
            if ok:
                self.project_ready() # 解鎖介面
            else:
                QMessageBox.warning(self, "建立失敗", r)

    def on_open(self):
        """開啟專案流程：選路徑 -> 自動辨識版本 -> 載入 -> 解鎖"""
        dialog = QFileDialog(self, "選專案")
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setOption(QFileDialog.DontUseNativeDialog, True)
        
        if dialog.exec() == QDialog.Accepted:
            selected = dialog.selectedFiles()
            if selected:
                folder_path = selected[0]
                
                # 1. 偷看專案使用的規範名稱
                proj_std = self.pm.peek_project_standard(folder_path)
                
                # 2. 嘗試自動載入該規範
                if proj_std:
                    target_config = self.config_mgr.find_config_by_name(proj_std)
                    if target_config:
                        self.config = target_config
                        self.rebuild_ui_from_config()
                    else:
                        # 找不到對應規範，詢問是否用目前的硬開
                        ret = QMessageBox.question(self, "規範遺失", 
                                             f"專案使用規範：{proj_std}\n系統找不到此規範檔。\n是否嘗試使用目前載入的規範開啟？",
                                             QMessageBox.Yes | QMessageBox.No)
                        if ret == QMessageBox.No: return
                else:
                    QMessageBox.warning(self, "警告", "無法識別專案規範版本，將使用目前版本開啟。")
                
                # 3. 載入資料
                ok, m = self.pm.load_project(folder_path)
                if ok:
                    self.project_ready() # 解鎖介面
                else:
                    QMessageBox.warning(self, "載入失敗", m)

    def on_adhoc(self):
        """[Modified] 個別檢測流程：提示 -> 選版本 -> 選項目 -> 建立 -> 鎖定功能"""
        
        # 1. 提示使用者限制
        QMessageBox.information(self, "各別檢測模式說明", 
                                "【注意】\n\n"
                                "各別檢測模式 (Ad-Hoc) 產生的結果，\n"
                                "日後僅能合併至「完全相同規範版本」的完整專案中。\n\n"
                                "請確認您選擇的規範版本與目標專案一致。")

        # 2. 選擇規範
        sel_dialog = VersionSelectionDialog(self.config_mgr, self)
        if sel_dialog.exec() != QDialog.Accepted or not sel_dialog.selected_config:
            return
            
        selected_config = sel_dialog.selected_config

        # 3. 選擇測項
        d = QuickTestSelector(self, selected_config)
        s, p = d.run()
        if s and p:
            # 4. 切換 UI 並建立專案
            self.config = selected_config
            self.rebuild_ui_from_config()
            
            ok, r = self.pm.create_ad_hoc_project(s, p)
            if ok:
                self.project_ready() # 進入 UI 狀態更新
            else:
                QMessageBox.warning(self, "建立失敗", r)

    def on_edit(self):
        if not self.pm.current_project_path: return
        
        p_type = self.pm.get_current_project_type()
        
        if p_type == PROJECT_TYPE_ADHOC:
            # [New] Ad-Hoc 編輯模式：開啟測項選擇器
            self.edit_adhoc_items()
        else:
            # 一般模式：開啟專案資訊表單
            c = ProjectFormController(self, self.config, self.pm.project_data.get("info", {}))
            d = c.run()
            if d and self.pm.update_info(d):
                QMessageBox.information(self, "OK", "已更新")
                self.overview.refresh_data()

    def on_save_as_new_version(self):
        if not self.pm.current_project_path: return
        
        # 1. 選擇新規範
        sel_dialog = VersionSelectionDialog(self.config_mgr, self)
        if sel_dialog.exec() != QDialog.Accepted or not sel_dialog.selected_config: return
        
        new_config = sel_dialog.selected_config
        new_std_name = new_config.get("standard_name", "NewVer")
        
        # 2. 計算遷移影響 (預覽)
        try:
            report = self.pm.calculate_migration_impact(new_config)
            
            # 顯示預覽報告
            report_dialog = MigrationReportDialog(self, report)
            if report_dialog.exec() != QDialog.Accepted:
                return # 使用者取消
            
            # 3. 設定新專案名稱
            current_name = self.pm.project_data.get("info", {}).get("project_name", "Project")
            default_new_name = f"{current_name}_{new_std_name}"
            
            new_name, ok = QInputDialog.getText(self, "另存新版本專案", 
                                          "請輸入新專案名稱 (將建立新資料夾)：", 
                                          QLineEdit.Normal, default_new_name)
            
            if ok and new_name:
                # 4. 執行 Fork 與遷移
                success, msg = self.pm.fork_project_to_new_version(new_name, new_config, report)
                
                if success:
                    QMessageBox.information(self, "成功", f"已建立新專案：{new_name}\n\n系統將自動切換至新專案。")
                    
                    # 5. 自動切換到新專案
                    # msg 回傳的是新專案的路徑
                    new_project_path = msg 
                    
                    # 載入新專案
                    ok_load, err_load = self.pm.load_project(new_project_path)
                    
                    if ok_load:
                        # 更新 UI 的 config 參考
                        self.config = new_config
                        # 重建 UI
                        self.rebuild_ui_from_config()
                        self.project_ready()
                    else:
                        QMessageBox.warning(self, "載入失敗", f"新專案建立成功但載入失敗：{err_load}")
                else:
                    QMessageBox.critical(self, "建立失敗", msg)
                    
        except ValueError as e:
            QMessageBox.critical(self, "錯誤", f"遷移計算失敗：\n{str(e)}")


    def edit_adhoc_items(self):
        """[New] 編輯 Ad-Hoc 測項：增刪邏輯"""
        # 1. 取得目前已選的項目
        current_whitelist = self.pm.project_data.get("info", {}).get("target_items", [])
        
        # 2. 開啟選擇器，並預設勾選目前的項目
        d = QuickTestSelector(self, self.config)
        
        # 這裡需要稍微修改 QuickTestSelector 讓它支援預設勾選
        # 我們直接操作它的 list_widget
        for i in range(d.list_widget.count()):
            item = d.list_widget.item(i)
            uid = item.data(Qt.UserRole)
            if uid in current_whitelist:
                item.setCheckState(Qt.Checked)
        
        new_selected, _ = d.run() # 第二個返回值是 path，編輯模式下用不到
        
        if new_selected is not None: # 使用者按下 OK (可能是空 list，代表全刪)
            # 3. 計算被移除的項目
            removed_items = set(current_whitelist) - set(new_selected)
            
            if removed_items:
                ret = QMessageBox.question(self, "確認移除", 
                                     f"您取消了 {len(removed_items)} 個測項。\n"
                                     "這些測項的現有檢測結果將被永久刪除！\n\n"
                                     "確定要繼續嗎？",
                                     QMessageBox.Yes | QMessageBox.No)
                if ret == QMessageBox.No: return

            # 4. 執行更新
            self.pm.update_adhoc_items(new_selected, removed_items)
            
            self.refresh_ui() # 重繪介面
            self.rebuild_ui_from_config() # 因為按鈕顯示狀態變了，最好重建一下 Tab 結構比較保險
            self.project_ready() # 重新初始化狀態
            QMessageBox.information(self, "更新完成", "檢測項目已更新。")

    def on_switch_version(self):
        if not self.pm.current_project_path: return
        sel_dialog = VersionSelectionDialog(self.config_mgr, self)
        if sel_dialog.exec() != QDialog.Accepted or not sel_dialog.selected_config: return
        new_config = sel_dialog.selected_config
        try:
            report = self.pm.calculate_migration_impact(new_config)
            report_dialog = MigrationReportDialog(self, report)
            if report_dialog.exec() == QDialog.Accepted:
                self.pm.apply_version_switch(new_config, report)
                self.config = new_config
                self.rebuild_ui_from_config()
                self.project_ready()
                QMessageBox.information(self, "成功", "版本切換完成，舊設定已備份。")
        except ValueError as e:
            QMessageBox.critical(self, "遷移失敗", f"無法切換至此版本：\n{str(e)}")

    def on_restore_snapshot(self):
        snaps = self.pm.list_snapshots()
        if not snaps:
            QMessageBox.information(self, "無快照", "目前沒有備份快照。")
            return
        item, ok = QInputDialog.getItem(self, "還原快照", "請選擇要還原的時間點：", snaps, 0, False)
        if ok and item:
            if QMessageBox.question(self, "確認", "還原將覆蓋目前的進度，確定嗎？") == QMessageBox.Yes:
                ok, msg = self.pm.restore_snapshot(item)
                if ok:
                    std_name = self.pm.project_data.get("standard_name")
                    target_config = self.config_mgr.find_config_by_name(std_name)
                    if target_config:
                        self.config = target_config
                        self.rebuild_ui_from_config()
                        self.project_ready()
                        QMessageBox.information(self, "成功", "專案已還原")
                    else:
                        QMessageBox.warning(self, "警告", "還原成功，但找不到對應的規範 JSON。")
                else:
                    QMessageBox.warning(self, "失敗", msg)

    def on_merge(self):
        d = QFileDialog.getExistingDirectory(self, "選匯入目錄")
        if d:
            ok, msg = self.pm.merge_external_project(d)
            if ok: QMessageBox.information(self, "OK", msg)
            else: QMessageBox.warning(self, "Fail", msg)

    def project_ready(self):
        """專案載入成功後呼叫，設定標題與解鎖 UI"""
        self._set_ui_locked(False)
        self.refresh_ui()
        self.tabs.setCurrentIndex(0)
        
        # [Modified] 根據專案類型設定 Title
        std_name = self.config.get("standard_name", "Unknown")
        proj_name = self.pm.project_data.get("info", {}).get("project_name", "未命名")
        p_type = self.pm.get_current_project_type()
        
        if p_type == PROJECT_TYPE_ADHOC:
            self.setWindowTitle(f"無人機資安檢測工具 [各別檢測模式] - {proj_name} [{std_name}]")
        else:
            self.setWindowTitle(f"無人機資安檢測工具 - {proj_name} [{std_name}]")

    def refresh_ui(self):
        """根據專案狀態更新 UI 元件的啟用/禁用"""
        self.overview.refresh_data()
        self.update_status()
        self.update_tab_visibility()
        
        has_proj = self.pm.current_project_path is not None
        p_type = self.pm.get_current_project_type()

        # 基礎功能啟用狀態
        self.a_edit.setEnabled(has_proj)
        self.a_merge.setEnabled(has_proj)
        
        # [New] 另存版本功能：只有完整專案可以使用，Ad-Hoc 不支援
        if has_proj and p_type == PROJECT_TYPE_FULL:
            self.a_save_as_ver.setEnabled(True)
        else:
            self.a_save_as_ver.setEnabled(False)

        # Ad-Hoc 特殊處理
        if has_proj and p_type == PROJECT_TYPE_ADHOC:
            self.a_edit.setEnabled(True)    # Ad-Hoc 可編輯測項
            self.a_edit.setText("編輯檢測項目 (Ad-Hoc)")
            self.a_merge.setEnabled(False)  # Ad-Hoc 不能匯入別人
        else:
            self.a_edit.setText("編輯專案資訊")

    def update_status(self):
        for uid, (btn, layout, conf, row) in self.test_ui_elements.items():
            # [Fix] 這裡傳入 UID，解決 Ad-Hoc 顯示問題
            target_id = conf.get("uid", conf.get("id"))
            
            if not self.pm.is_item_visible(target_id): 
                row.hide(); continue
            row.show()
            
            status_map = self.pm.get_test_status_detail(conf)
            is_any = any(s != STATUS_NOT_TESTED for s in status_map.values())
            if is_any: btn.setStyleSheet(f"QPushButton {{ background-color: {COLOR_BTN_ACTIVE}; color: white; font-weight: bold; }}")
            else: btn.setStyleSheet("")
            
            while layout.count(): layout.takeAt(0).widget().deleteLater()
            for t, s in status_map.items():
                lbl = QLabel(f"{t}: {s}" if len(status_map)>1 else s)
                lbl.setAlignment(Qt.AlignCenter)
                lbl.setFixedHeight(30)
                c = COLOR_BG_DEFAULT; tc = COLOR_TEXT_GRAY
                if s == "Pass": c = COLOR_BG_PASS; tc = COLOR_TEXT_PASS
                elif s == "Fail": c = COLOR_BG_FAIL; tc = COLOR_TEXT_FAIL
                elif s == "N/A": c = COLOR_BG_NA; tc = COLOR_TEXT_WHITE 
                
                lbl.setStyleSheet(f"background-color:{c}; color:{tc}; border-radius:4px; font-weight:bold;")
                layout.addWidget(lbl)

    def update_tab_visibility(self):
        if not self.pm.current_project_path: return
        for i, sec in enumerate(self.config.get("test_standards", [])):
            t_idx = i + 1
            sec_id = sec['section_id']
            is_visible = self.pm.is_section_visible(sec_id)
            self.tabs.setTabEnabled(t_idx, is_visible)
            self.tabs.setTabText(t_idx, sec['section_name'] + (" (N/A)" if not is_visible else ""))

    def open_test(self, item):
        self.win = QWidget()
        self.win.setWindowTitle(f"檢測 {item['id']} {item['name']}")
        self.win.resize(600, 700)
        l = QVBoxLayout(self.win)
        l.addWidget(UniversalTestPage(item, self.pm))
        self.win.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    font_family = '"Microsoft JhengHei", "Segoe UI", sans-serif'
    app.setStyleSheet(f"QWidget {{ font-family: {font_family}; font-size: 10pt; }}")

    config_mgr = ConfigManager(config_dir=CONFIG_DIR)
    
    if not config_mgr.list_available_configs():
        QMessageBox.warning(None, "警告", "未偵測到設定檔，請將 json 放入 configs 資料夾")

    # [Changed] 直接啟動 MainApp，不帶參數 (參數在內部處理)
    window = MainApp(config_mgr)
    window.show()
    
    sys.exit(app.exec())