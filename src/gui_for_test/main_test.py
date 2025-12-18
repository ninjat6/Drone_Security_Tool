import sys
import json
import os
import shutil
from datetime import datetime
from functools import partial

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QStackedWidget, QMessageBox, QLabel, QDialog, QFormLayout, 
    QLineEdit, QDateEdit, QToolButton, QDialogButtonBox, QFileDialog, 
    QTextEdit, QGroupBox, QCheckBox, QProgressBar, QFrame, QScrollArea,
    QComboBox, QSizePolicy
)
from PySide6.QtCore import Qt, QDate, QObject, Signal, QSize
from PySide6.QtGui import QAction, QPixmap

# ==========================================
# 1. 專案管理器 (Project Manager)
# ==========================================
class ProjectManager(QObject): 
    data_changed = Signal()

    def __init__(self):
        super().__init__()
        self.current_project_path = None
        self.project_data = {}
        self.settings_filename = "project_settings.json"

    def create_project(self, form_data: dict) -> tuple[bool, str]:
        raw_base_path = form_data.get("save_path")
        project_name = form_data.get("project_name")
        
        if not raw_base_path or not project_name:
            return False, "缺少儲存路徑或專案名稱"

        base_path = os.path.abspath(os.path.expanduser(raw_base_path))
        target_folder = os.path.join(base_path, project_name)

        final_path = target_folder
        if os.path.exists(final_path):
            i = 1
            while True:
                new_path = f"{target_folder}_{i}"
                if not os.path.exists(new_path):
                    final_path = new_path
                    break
                i += 1
        
        actual_project_name = os.path.basename(final_path)
        form_data['project_name'] = actual_project_name

        self.project_data = {
            "version": "1.9",
            "info": form_data,
            "tests": {} 
        }

        try:
            os.makedirs(final_path, exist_ok=True)
            os.makedirs(os.path.join(final_path, "images"), exist_ok=True)
            self.current_project_path = final_path
            self.save_all()
            return True, final_path

        except Exception as e:
            return False, f"建立失敗: {e}"

    def load_project(self, folder_path: str) -> tuple[bool, str]:
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

    def import_photo(self, src_path: str, prefix: str) -> str:
        if not self.current_project_path: return None
        try:
            filename = os.path.basename(src_path)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_filename = f"{prefix}_{ts}_{filename}"
            images_dir = os.path.join(self.current_project_path, "images")
            if not os.path.exists(images_dir): os.makedirs(images_dir)
            dest_path = os.path.join(images_dir, new_filename)
            shutil.copy2(src_path, dest_path)
            return os.path.join("images", new_filename)
        except Exception as e:
            print(f"複製照片失敗: {e}")
            return None

    def update_info(self, new_info: dict):
        if not self.current_project_path: return False, "未開啟專案"
        if "info" not in self.project_data: self.project_data["info"] = {}
        self.project_data["info"].update(new_info)
        res = self.save_all()
        self.data_changed.emit()
        return res

    def update_test_result(self, test_id: str, target: str, result_data: dict, is_shared: bool = False):
        if "tests" not in self.project_data: self.project_data["tests"] = {}
        if test_id not in self.project_data["tests"]: self.project_data["tests"][test_id] = {}
        
        self.project_data["tests"][test_id][target] = result_data
        self.project_data["tests"][test_id][target]["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if "__meta__" not in self.project_data["tests"][test_id]:
            self.project_data["tests"][test_id]["__meta__"] = {}
        self.project_data["tests"][test_id]["__meta__"]["is_shared"] = is_shared
        
        self.save_all()
        self.data_changed.emit()

    def get_test_meta(self, test_id: str) -> dict:
        tests = self.project_data.get("tests", {})
        item_data = tests.get(test_id, {})
        return item_data.get("__meta__", {})

    def save_all(self):
        if not self.current_project_path: return False, "無路徑"
        json_path = os.path.join(self.current_project_path, self.settings_filename)
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(self.project_data, f, ensure_ascii=False, indent=4)
            return True, "儲存成功"
        except Exception as e:
            return False, str(e)

    def get_test_status_detail(self, item_config: dict) -> dict:
        test_id = item_config['id']
        required_targets = item_config.get('targets', ["GCS"])
        saved_tests = self.project_data.get("tests", {})
        
        status_map = {}
        item_data = saved_tests.get(test_id, {})
        
        for t in required_targets:
            if t not in item_data:
                status_map[t] = "未檢測"
            else:
                raw_res = item_data[t].get("result", "未判定")
                if "未判定" in raw_res: status_map[t] = "未檢測"
                elif "合格" in raw_res and "不" not in raw_res: status_map[t] = "Pass"
                elif "不合格" in raw_res: status_map[t] = "Fail"
                elif "不適用" in raw_res: status_map[t] = "N/A"
                else: status_map[t] = "Unknown"
        return status_map

    def is_test_fully_completed(self, item_config: dict) -> bool:
        test_id = item_config['id']
        targets = item_config.get('targets', ["GCS"])
        saved = self.project_data.get("tests", {}).get(test_id, {})
        for t in targets:
            if t not in saved: return False
            res = saved[t].get("result", "未判定")
            if "未判定" in res: return False
        return True


# ==========================================
# 2. 專案表單 (新建/編輯共用)
# ==========================================
class ProjectFormController:
    def __init__(self, parent_window, meta_schema, existing_data=None):
        """
        :param existing_data: 如果是編輯模式，傳入 {"project_name": "xxx", ...}
        """
        self.meta_schema = meta_schema
        self.existing_data = existing_data
        self.is_edit_mode = existing_data is not None
        
        self.dialog = QDialog(parent_window)
        title = "編輯專案資訊" if self.is_edit_mode else "新建專案"
        self.dialog.setWindowTitle(title)
        self.dialog.resize(500, 500) # 稍微加大一點
        
        self.inputs = {}
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self.dialog)
        form_layout = QFormLayout()
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")

        for field in self.meta_schema:
            key = field['key']
            f_type = field['type']
            label = field['label']
            
            if f_type == 'hidden': continue

            widget = None
            
            # 1. 一般文字框
            if f_type == 'text':
                widget = QLineEdit()
                if self.is_edit_mode and key in self.existing_data:
                    widget.setText(str(self.existing_data[key]))
                    # 編輯模式下，專案名稱通常不給改，以免路徑對不上
                    if key == "project_name":
                        widget.setReadOnly(True)
                        widget.setStyleSheet("background-color: #f0f0f0;")

            # 2. 日期選擇
            elif f_type == 'date': 
                widget = QDateEdit()
                widget.setCalendarPopup(True)
                if self.is_edit_mode and key in self.existing_data:
                    qdate = QDate.fromString(self.existing_data[key], "yyyy-MM-dd")
                    widget.setDate(qdate)
                else:
                    widget.setDate(QDate.currentDate())

            # 3. 路徑選擇
            elif f_type == 'path_selector':
                widget = QWidget(); h_layout = QHBoxLayout(widget); h_layout.setContentsMargins(0,0,0,0)
                pe = QLineEdit()
                btn = QToolButton(); btn.setText("...")
                
                if self.is_edit_mode:
                    # 編輯模式下，路徑只讀
                    pe.setText(self.existing_data.get(key, ""))
                    pe.setReadOnly(True)
                    btn.setEnabled(False)
                else:
                    pe.setText(desktop_path)
                    btn.clicked.connect(lambda _, le=pe: self._browse_path(le))
                
                h_layout.addWidget(pe); h_layout.addWidget(btn); widget.line_edit = pe 

            # 4. 【新增】Checkbox Group (支援多選)
            elif f_type == 'checkbox_group':
                widget = QGroupBox() # 用 GroupBox 包起來
                v_layout = QVBoxLayout(widget)
                v_layout.setContentsMargins(5, 5, 5, 5)
                
                options = field.get("options", [])
                chk_list = []
                
                # 讀取舊資料 (如果是編輯模式)
                # 假設資料存成 list: ["6", "8.1"]
                checked_values = []
                if self.is_edit_mode:
                    checked_values = self.existing_data.get(key, [])
                
                for opt in options:
                    chk = QCheckBox(opt['label'])
                    # 綁定 value 屬性方便取值
                    chk.setProperty("value", opt['value'])
                    
                    # 預設全選 (新建時)，或根據舊資料勾選
                    if self.is_edit_mode:
                        if opt['value'] in checked_values:
                            chk.setChecked(True)
                    else:
                        chk.setChecked(True) # 新建預設全選
                        
                    v_layout.addWidget(chk)
                    chk_list.append(chk)
                
                # 將 widget 標記為特殊容器，稍後取值用
                widget.checkboxes = chk_list

            if widget:
                form_layout.addRow(label, widget)
                self.inputs[key] = {'widget': widget, 'type': f_type}
        
        layout.addLayout(form_layout)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.dialog.accept); btns.rejected.connect(self.dialog.reject)
        layout.addWidget(btns)
        
    def _browse_path(self, line_edit):
        d = QFileDialog.getExistingDirectory(self.dialog, "選擇儲存資料夾")
        if d: line_edit.setText(d)
            
    def run(self):
        if self.dialog.exec() == QDialog.Accepted: return self._collect_data()
        return None
        
    def _collect_data(self):
        data = {}
        for key, info in self.inputs.items():
            widget = info['widget']; w_type = info['type']
            
            if w_type == 'text': 
                data[key] = widget.text()
            elif w_type == 'date': 
                data[key] = widget.date().toString("yyyy-MM-dd")
            elif w_type == 'path_selector': 
                data[key] = widget.line_edit.text()
            elif w_type == 'checkbox_group':
                # 收集所有被勾選的 value
                selected = []
                for chk in widget.checkboxes:
                    if chk.isChecked():
                        selected.append(chk.property("value"))
                data[key] = selected
                
        return data


# ==========================================
# 3. 總覽頁面 (支援 Scope 顯示)
# ==========================================
class OverviewPage(QWidget):
    def __init__(self, project_manager, config):
        super().__init__()
        self.pm = project_manager
        self.config = config
        self._init_ui()

    def _init_ui(self):
        self.main_layout = QVBoxLayout(self)

        info_group = QGroupBox("專案資訊")
        self.info_layout = QFormLayout()
        self.lbl_name = QLabel("-"); self.lbl_id = QLabel("-"); self.lbl_tester = QLabel("-")
        self.info_layout.addRow("專案名稱:", self.lbl_name)
        self.info_layout.addRow("報告編號:", self.lbl_id)
        self.info_layout.addRow("檢測人員:", self.lbl_tester)
        info_group.setLayout(self.info_layout)
        self.main_layout.addWidget(info_group)

        photo_group = QGroupBox("受測物照片")
        photo_layout = QHBoxLayout()
        self.uav_img_lbl = self._create_img_label()
        btn_uav = QPushButton("上傳 UAV 照片")
        btn_uav.clicked.connect(lambda: self.upload_photo("uav"))
        self.gcs_img_lbl = self._create_img_label()
        btn_gcs = QPushButton("上傳 GCS 照片")
        btn_gcs.clicked.connect(lambda: self.upload_photo("gcs"))

        l1 = QVBoxLayout(); l1.addWidget(QLabel("無人機 (UAV)")); l1.addWidget(self.uav_img_lbl); l1.addWidget(btn_uav)
        l2 = QVBoxLayout(); l2.addWidget(QLabel("地面站 (GCS)")); l2.addWidget(self.gcs_img_lbl); l2.addWidget(btn_gcs)
        photo_layout.addLayout(l1); photo_layout.addLayout(l2)
        photo_group.setLayout(photo_layout)
        self.main_layout.addWidget(photo_group)

        self.progress_group = QGroupBox("檢測進度")
        self.progress_layout = QVBoxLayout()
        self.progress_group.setLayout(self.progress_layout)
        self.main_layout.addWidget(self.progress_group)
        self.main_layout.addStretch()

    def _create_img_label(self):
        lbl = QLabel("無照片"); lbl.setFrameShape(QFrame.Box); lbl.setFixedSize(200, 150)
        lbl.setAlignment(Qt.AlignCenter); lbl.setScaledContents(True)
        return lbl

    def refresh_data(self):
        if not self.pm.current_project_path: return
        data = self.pm.project_data.get("info", {})
        self.lbl_name.setText(data.get("project_name", "-"))
        self.lbl_id.setText(data.get("report_id", "-"))
        self.lbl_tester.setText(data.get("tester", "-"))

        self._load_image(data.get("uav_photo_path"), self.uav_img_lbl)
        self._load_image(data.get("gcs_photo_path"), self.gcs_img_lbl)

        # 讀取檢測範圍
        selected_scope = data.get("test_scope", []) 
        # 如果是舊專案沒有 scope，預設全選 (防止報錯)
        if not selected_scope and "test_scope" not in data:
            selected_scope = [s['section_id'] for s in self.config.get("test_standards", [])]

        while self.progress_layout.count():
            child = self.progress_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()

        standards = self.config.get("test_standards", [])
        for section in standards:
            sec_id = section['section_id']
            sec_name = section['section_name']
            
            h = QHBoxLayout()
            lbl = QLabel(sec_name); lbl.setFixedWidth(150)
            p = QProgressBar()
            
            # 【修改】判斷是否在 Scope 內
            if str(sec_id) in selected_scope:
                # 正常計算
                items = section['items']
                total = len(items)
                done = 0
                for item in items:
                    if self.pm.is_test_fully_completed(item): done += 1
                
                p.setRange(0, total); p.setValue(done)
                p.setFormat(f"%v / %m ({int(done/total*100) if total else 0}%)")
            else:
                # 不適用：變灰、不可用
                p.setRange(0, 100); p.setValue(0)
                p.setFormat("不適用 (N/A)")
                p.setStyleSheet("QProgressBar { color: gray; background-color: #f0f0f0; } QProgressBar::chunk { background-color: #cccccc; }")
                lbl.setStyleSheet("color: gray;")

            h.addWidget(lbl); h.addWidget(p)
            w = QWidget(); w.setLayout(h)
            self.progress_layout.addWidget(w)

    def _load_image(self, rel_path, label_widget):
        if rel_path and self.pm.current_project_path:
            full_path = os.path.join(self.pm.current_project_path, rel_path)
            if os.path.exists(full_path):
                label_widget.setPixmap(QPixmap(full_path))
                return
        label_widget.setText("無照片")

    def upload_photo(self, p_type):
        if not self.pm.current_project_path: 
            QMessageBox.warning(self, "警告", "請先建立或開啟專案")
            return
        f, _ = QFileDialog.getOpenFileName(self, "選擇照片", "", "Images (*.png *.jpg *.jpeg)")
        if f:
            relative_path = self.pm.import_photo(f, p_type)
            if relative_path:
                key = "uav_photo_path" if p_type == "uav" else "gcs_photo_path"
                self.pm.update_info({key: relative_path})


# ==========================================
# 4. 單一對象檢測填寫 Widget (保持不變)
# ==========================================
class SingleTargetTestWidget(QWidget):
    def __init__(self, target_name, item_config, project_manager, save_callback=None):
        super().__init__()
        self.target = target_name
        self.config = item_config
        self.pm = project_manager
        self.item_id = self.config['id']
        self.save_callback = save_callback
        self.logic_type = self.config.get("logic", "AND").upper()
        self._init_ui()
        self._load_saved_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel(f"<h3>對象: {self.target}</h3>"))
        logic_text = "(全選才通過)" if self.logic_type == "AND" else "(擇一即通過)"
        lbl_logic = QLabel(logic_text); lbl_logic.setStyleSheet("color: gray; font-size: 10pt;")
        header_layout.addWidget(lbl_logic); header_layout.addStretch()
        layout.addLayout(header_layout)
        
        self.desc_edit = QTextEdit()
        evidence_cfg = self.config.get('evidence_block', {})
        self.desc_edit.setPlaceholderText(evidence_cfg.get('description_template', ''))
        g_desc = QGroupBox("檢測過程說明"); l_desc = QVBoxLayout(); l_desc.addWidget(self.desc_edit)
        g_desc.setLayout(l_desc); layout.addWidget(g_desc)

        self.checks = {}
        criteria = self.config.get('sub_criteria', [])
        if criteria:
            g_crit = QGroupBox("判定標準 (自動判定)"); l_crit = QVBoxLayout()
            for c in criteria:
                chk = QCheckBox(c['content'])
                chk.stateChanged.connect(self.auto_judge)
                self.checks[c['id']] = chk
                l_crit.addWidget(chk)
            g_crit.setLayout(l_crit); layout.addWidget(g_crit)

        g_result = QGroupBox("最終判定"); l_result = QHBoxLayout()
        l_result.addWidget(QLabel("檢測結果:"))
        self.combo_result = QComboBox()
        self.combo_result.addItems(["未判定", "合格 (Pass)", "不合格 (Fail)", "不適用 (N/A)"])
        self.combo_result.currentTextChanged.connect(self.update_combo_color)
        l_result.addWidget(self.combo_result); g_result.setLayout(l_result); layout.addWidget(g_result)

        layout.addStretch()
        btn_save = QPushButton(f"儲存 ({self.target}) 結果")
        btn_save.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
        btn_save.clicked.connect(self.on_save); layout.addWidget(btn_save)

    def auto_judge(self):
        total = len(self.checks)
        if total == 0: return
        checked_count = sum(1 for chk in self.checks.values() if chk.isChecked())
        is_pass = (checked_count == total) if self.logic_type == "AND" else (checked_count > 0)
        self.combo_result.setCurrentText("合格 (Pass)" if is_pass else "不合格 (Fail)")

    def update_combo_color(self, text):
        if "合格" in text and "不" not in text: self.combo_result.setStyleSheet("background-color: #d4edda; color: #155724;")
        elif "不合格" in text: self.combo_result.setStyleSheet("background-color: #f8d7da; color: #721c24;")
        elif "不適用" in text: self.combo_result.setStyleSheet("background-color: #e2e3e5; color: #383d41;")
        else: self.combo_result.setStyleSheet("")

    def get_current_data(self):
        return {
            "description": self.desc_edit.toPlainText(),
            "criteria": {cid: chk.isChecked() for cid, chk in self.checks.items()},
            "result": self.combo_result.currentText(),
            "status": "checked" 
        }

    def on_save(self):
        if not self.pm.current_project_path:
            QMessageBox.warning(self, "警告", "請先建立或開啟專案！"); return
        data = self.get_current_data()
        if self.save_callback: self.save_callback(data)
        else:
            self.pm.update_test_result(self.item_id, self.target, data, is_shared=False)
            QMessageBox.information(self, "成功", f"[{self.target}] 資料已儲存！")

    def _load_saved_data(self):
        if not self.pm.project_data: return
        tests = self.pm.project_data.get("tests", {})
        item_data = tests.get(self.item_id, {})
        load_key = self.target
        if self.target == "Shared":
            targets = self.config.get("targets", [])
            if targets: load_key = targets[0]
        target_data = item_data.get(load_key, {})
        if target_data:
            self.desc_edit.setPlainText(target_data.get("description", ""))
            c_data = target_data.get("criteria", {})
            for cid, chk in self.checks.items():
                chk.blockSignals(True); chk.setChecked(c_data.get(cid, False)); chk.blockSignals(False)
            res = target_data.get("result", "未判定")
            idx = self.combo_result.findText(res)
            if idx >= 0: self.combo_result.setCurrentIndex(idx)
            self.update_combo_color(res)


# ==========================================
# 5. 通用檢測頁面 (保持不變)
# ==========================================
class UniversalTestPage(QWidget):
    def __init__(self, item_config, project_manager):
        super().__init__()
        self.config = item_config
        self.pm = project_manager
        self.item_id = self.config['id']
        self.targets = self.config.get("targets", ["GCS"]) 
        self.allow_share = self.config.get("allow_share", False)
        self._init_ui()
        self._load_state()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel(f"<h2>{self.config['name']} ({self.item_id})</h2>"))
        self.chk_share = None
        if len(self.targets) > 1 and self.allow_share:
            self.chk_share = QCheckBox("共用檢測結果 (適用於 UAV 與 GCS 相同時)")
            self.chk_share.setStyleSheet("font-weight: bold; color: blue;")
            self.chk_share.toggled.connect(self.on_share_toggled)
            header_layout.addStretch(); header_layout.addWidget(self.chk_share)
        layout.addLayout(header_layout)
        
        self.stack = QStackedWidget(); layout.addWidget(self.stack)
        self.page_separate = QWidget(); sep_layout = QVBoxLayout(self.page_separate); sep_layout.setContentsMargins(0,0,0,0)
        
        if len(self.targets) > 1:
            self.tab_widget = QTabWidget()
            for t in self.targets:
                page = SingleTargetTestWidget(t, self.config, self.pm)
                self.tab_widget.addTab(page, f"檢測對象: {t}")
            sep_layout.addWidget(self.tab_widget)
        else:
            page = SingleTargetTestWidget(self.targets[0], self.config, self.pm)
            sep_layout.addWidget(page)
        self.stack.addWidget(self.page_separate)

        if len(self.targets) > 1:
            self.page_shared = SingleTargetTestWidget("Shared", self.config, self.pm, save_callback=self.save_shared_data)
            self.stack.addWidget(self.page_shared)

    def _load_state(self):
        meta = self.pm.get_test_meta(self.item_id)
        is_shared = meta.get("is_shared", False)
        if self.chk_share:
            self.chk_share.setChecked(is_shared); self.on_share_toggled(is_shared)

    def on_share_toggled(self, checked):
        if checked: self.stack.setCurrentWidget(self.page_shared)
        else: self.stack.setCurrentWidget(self.page_separate)

    def save_shared_data(self, data):
        for t in self.targets: self.pm.update_test_result(self.item_id, t, data, is_shared=True)
        target_str = " & ".join(self.targets)
        QMessageBox.information(self, "成功", f"檢測結果已共用並儲存至 [{target_str}]！")


# ==========================================
# 6. 主程式
# ==========================================
class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("無人機資安檢測工具 v14.0 (Scope & Edit)")
        self.resize(1000, 700)
        self.pm = ProjectManager()
        self.config = self._load_config()
        self.pm.data_changed.connect(self.refresh_all_ui)
        self.test_ui_elements = {} 

        self.central_widget = QWidget(); self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        self._init_menubar()
        
        self.tab_widget = QTabWidget()
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        self.main_layout.addWidget(self.tab_widget)
        
        self.overview_page = OverviewPage(self.pm, self.config)
        self.tab_widget.addTab(self.overview_page, "總覽 Overview")
        self._init_dynamic_tabs()
        self._set_tabs_enabled(False)

    def _load_config(self):
        if not os.path.exists("standard_config.json"):
            QMessageBox.critical(self, "錯誤", "找不到 standard_config.json")
            return {"test_standards": [], "project_meta_schema": []}
        with open("standard_config.json", "r", encoding='utf-8') as f:
            return json.load(f)

    def _init_menubar(self):
        mb = self.menuBar(); f_menu = mb.addMenu("檔案 (File)")
        a_new = QAction("新建專案", self); a_new.triggered.connect(self.on_new_project); f_menu.addAction(a_new)
        a_open = QAction("開啟專案", self); a_open.triggered.connect(self.on_open_project); f_menu.addAction(a_open)
        
        # 【新增】編輯專案
        a_edit = QAction("編輯專案資訊", self)
        a_edit.triggered.connect(self.on_edit_project)
        # 初始停用，等到有專案才啟用
        a_edit.setEnabled(False) 
        self.action_edit = a_edit
        f_menu.addAction(a_edit)

    def _init_dynamic_tabs(self):
        standards = self.config.get("test_standards", [])
        self.test_ui_elements = {}

        for section in standards:
            page = QWidget(); layout = QVBoxLayout(page)
            layout.addWidget(QLabel(f"<h3>{section['section_name']}</h3>"))
            scroll = QScrollArea(); scroll.setWidgetResizable(True)
            content = QWidget(); c_layout = QVBoxLayout(content)
            
            for item in section['items']:
                row_widget = QWidget(); row_layout = QHBoxLayout(row_widget); row_layout.setContentsMargins(0, 5, 0, 5)
                btn = QPushButton(f"{item['id']} {item['name']}")
                btn.setFixedHeight(40); btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                btn.clicked.connect(partial(self.open_test_window, item))
                
                status_container = QWidget(); status_layout = QHBoxLayout(status_container); status_layout.setContentsMargins(0, 0, 0, 0); status_layout.setSpacing(5); status_container.setFixedWidth(240) 
                
                row_layout.addWidget(btn); row_layout.addWidget(status_container); c_layout.addWidget(row_widget)
                self.test_ui_elements[item['id']] = (btn, status_layout, item)
                
            c_layout.addStretch(); scroll.setWidget(content); layout.addWidget(scroll)
            self.tab_widget.addTab(page, section['section_id'])

    def refresh_all_ui(self):
        self.overview_page.refresh_data()
        self.update_test_status()
        self.update_tabs_visibility()

    def update_tabs_visibility(self):
        """根据 test_scope 控制 Tab 是否可用"""
        if not self.pm.current_project_path: return
        
        data = self.pm.project_data.get("info", {})
        # 获取勾选的范围，如果是旧专案没有这个字段，默认全选
        selected_scope = data.get("test_scope", [])
        
        # 如果是旧专案或没存 scope，默认全部启用
        if not selected_scope and "test_scope" not in data:
            for i in range(1, self.tab_widget.count()):
                self.tab_widget.setTabEnabled(i, True)
            return

        # 遍历 Tab (注意：index 0 是 Overview，从 1 开始是检测项)
        standards = self.config.get("test_standards", [])
        
        # 建立 section_id -> tab_index 的映射
        # 假设 standards 的顺序和 tab 添加的顺序是一致的
        # Tab 0: Overview
        # Tab 1: Standard[0] (e.g., Section 6)
        # Tab 2: Standard[1] (e.g., Section 7)
        
        for i, section in enumerate(standards):
            tab_index = i + 1 # 因为第0页是总览
            sec_id = str(section['section_id'])
            
            is_enabled = sec_id in selected_scope
            self.tab_widget.setTabEnabled(tab_index, is_enabled)
            
            # 视觉优化：如果禁用了，可以在标题加个 (N/A)
            title = section['section_id']
            if not is_enabled:
                title += " (N/A)"
            
            self.tab_widget.setTabText(tab_index, title)

    def update_test_status(self):
        for test_id, (btn, layout, item_config) in self.test_ui_elements.items():
            status_map = self.pm.get_test_status_detail(item_config)
            is_any_tested = any(s != "未檢測" for s in status_map.values())
            
            if is_any_tested:
                btn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; border-radius: 5px; font-weight: bold; border: none; } QPushButton:hover { background-color: #1976D2; }")
            else:
                btn.setStyleSheet("")

            while layout.count():
                child = layout.takeAt(0); 
                if child.widget(): child.widget().deleteLater()

            count = len(status_map)
            for target, status in status_map.items():
                lbl = QLabel(); lbl.setAlignment(Qt.AlignCenter); lbl.setFixedHeight(30)
                if count > 1: lbl.setText(f"{target}: {status}")
                else: lbl.setText(status) 

                bg_color = "#dddddd"; text_color = "#666666" 
                if status == "Pass": bg_color = "#4CAF50"; text_color = "white"
                elif status == "Fail": bg_color = "#F44336"; text_color = "white"
                elif status == "N/A": bg_color = "#9E9E9E"; text_color = "white"
                elif status == "Unknown": bg_color = "#FF9800"; text_color = "white"

                lbl.setStyleSheet(f"QLabel {{ background-color: {bg_color}; color: {text_color}; border-radius: 4px; font-weight: bold; font-size: 12px; }}")
                layout.addWidget(lbl)

    def _set_tabs_enabled(self, enabled):
        for i in range(1, self.tab_widget.count()): self.tab_widget.setTabEnabled(i, enabled)
        if hasattr(self, 'action_edit'): self.action_edit.setEnabled(enabled)

    def on_tab_changed(self, index):
        if index == 0: self.overview_page.refresh_data()

    def on_new_project(self):
        schema = self.config.get("project_meta_schema", [])
        ctrl = ProjectFormController(self, schema)
        data = ctrl.run()
        if data:
            success, result = self.pm.create_project(data)
            if success: QMessageBox.information(self, "成功", f"專案建立於:\n{result}"); self.project_ready()
            else: QMessageBox.warning(self, "失敗", result)

    def on_edit_project(self):
        """【新增】編輯專案"""
        if not self.pm.current_project_path: return
        
        # 取得目前專案資料回填
        current_info = self.pm.project_data.get("info", {})
        schema = self.config.get("project_meta_schema", [])
        
        ctrl = ProjectFormController(self, schema, existing_data=current_info)
        new_data = ctrl.run()
        
        if new_data:
            # 更新專案資訊
            success = self.pm.update_info(new_data)
            if success:
                QMessageBox.information(self, "成功", "專案資訊已更新")
                self.overview_page.refresh_data()
            else:
                QMessageBox.warning(self, "失敗", "無法更新專案")

    def on_open_project(self):
        folder = QFileDialog.getExistingDirectory(self, "選擇專案資料夾")
        if folder:
            success, msg = self.pm.load_project(folder)
            if success: QMessageBox.information(self, "成功", "專案讀取成功"); self.project_ready()
            else: QMessageBox.warning(self, "失敗", msg)

    def project_ready(self):
        self._set_tabs_enabled(True); self.refresh_all_ui(); self.tab_widget.setCurrentIndex(0)

    def open_test_window(self, item_config):
        self.test_win = QWidget()
        self.test_win.setWindowTitle(f"檢測: {item_config['id']}")
        self.test_win.resize(600, 700)
        page = UniversalTestPage(item_config, self.pm)
        layout = QVBoxLayout(self.test_win); layout.addWidget(page); self.test_win.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainApp()
    window.show()
    sys.exit(app.exec())