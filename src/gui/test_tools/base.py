"""
基礎測項工具模組
包含 BaseTestToolStrings, BaseTestToolView, BaseTestTool
"""

from typing import Dict, Optional, Tuple
import os

from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QCheckBox,
    QTextEdit,
    QGroupBox,
    QComboBox,
    QPushButton,
    QFrame,
    QFileDialog,
    QMessageBox,
    QScrollArea,
)

from styles import Styles
from widgets.attachment import AttachmentListWidget
from dialogs.qr_dialog import QRCodeDialog
from constants import (
    STATUS_PASS,
    STATUS_FAIL,
    STATUS_NA,
    STATUS_UNCHECKED,
    COLOR_BG_PASS,
    COLOR_BG_FAIL,
    COLOR_BG_NA,
    COLOR_TEXT_PASS,
    COLOR_TEXT_FAIL,
    DIR_REPORTS,
)


# ==============================================================================
# 字串常數
# ==============================================================================


class BaseTestToolStrings:
    """BaseTestToolView 字串常數"""

    # 判定邏輯
    LOGIC_AND = "須符合所有項目 (AND)"
    LOGIC_OR = "符合任一項目即可 (OR)"
    LOGIC_PREFIX = "判定邏輯: "

    # 規範說明
    CRITERIA_ALL = "符合下列【所有】項目者為通過"
    CRITERIA_ANY = "符合下列【任一】項目者為通過"
    CRITERIA_ELSE = "，否則為未通過：\n"
    NO_METHOD_DESC = "無測試方法描述"

    # HTML 標籤
    HTML_METHOD_TITLE = "<b style='color:#333;'>【測試方法】</b>"
    HTML_CRITERIA_TITLE = "<b style='color:#333;'>【判定標準】</b>"

    # GroupBox 標題
    GB_NARRATIVE = "規範說明"
    GB_CHECKLIST = "細項檢查表 (Checklist)"
    GB_NOTE = "判定原因 / 備註"

    # Placeholder
    HINT_NOTE = "合格時可留空，不合格時系統將自動帶入原因..."


# ==============================================================================
# View 類別
# ==============================================================================


class BaseTestToolView(QWidget):
    """
    基礎測項 UI 視圖
    職責：只負責 UI 呈現，透過 Signal 發送使用者操作事件
    子類別可覆寫 _build_custom_section() 來新增專屬 UI
    """

    # Signals - 發送給 Controller
    check_changed = Signal(str, bool)  # (item_id, checked)
    note_changed = Signal(str)

    # 新增 Signals
    upload_pc_clicked = Signal()
    upload_mobile_clicked = Signal()
    result_changed = Signal(str)  # (new_status_text)
    save_clicked = Signal()

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.config = config
        self.logic = config.get("logic", "AND").upper()
        self.checks: Dict[str, QCheckBox] = {}
        self.attachment_list = None
        self.result_combo = None
        self._init_ui()

    def _build_attachment_section(self, layout: QVBoxLayout):
        """建立佐證資料區"""
        g_file = QGroupBox("佐證資料 (圖片/檔案)")
        v_file = QVBoxLayout()
        v_file.setContentsMargins(1, 1, 1, 1)

        h_btn = QHBoxLayout()
        btn_pc = QPushButton("📂 加入檔案 (多選)")
        btn_pc.clicked.connect(self.upload_pc_clicked)
        btn_mobile = QPushButton("📱 手機拍照上傳")
        btn_mobile.clicked.connect(self.upload_mobile_clicked)
        h_btn.addWidget(btn_pc, 1)
        h_btn.addWidget(btn_mobile, 1)
        v_file.addLayout(h_btn)

        self.attachment_list = AttachmentListWidget()
        self.attachment_list.setMinimumHeight(100)
        # 移除 setMaximumHeight 限制，讓列表可以延伸
        v_file.addWidget(self.attachment_list, stretch=1)

        g_file.setLayout(v_file)
        layout.addWidget(g_file, stretch=1)  # 讓整個 GroupBox 延伸填滿空間

    def _build_result_section(self, layout: QVBoxLayout):
        """建立最終判定與儲存區"""
        # Result Group
        g3 = QGroupBox("最終判定")
        h3 = QHBoxLayout()
        # h3.setContentsMargins(1, 1, 1, 1)
        # h3.addWidget(QLabel("結果:"))

        self.result_combo = QComboBox()
        self.result_combo.addItems(
            [STATUS_UNCHECKED, STATUS_PASS, STATUS_FAIL, STATUS_NA]
        )
        self.result_combo.currentTextChanged.connect(self.result_changed)

        h3.addWidget(self.result_combo)
        g3.setLayout(h3)
        layout.addWidget(g3)

        # Save Button 會在 _init_ui 中另外處理，固定在底部

    def _init_ui(self):
        """建構 UI - 使用 Template Method Pattern"""
        # 主容器使用 Vertical Layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 1. 標題區 (Header)
        # h_header = QHBoxLayout()
        # h_header.addStretch()
        # main_layout.addLayout(h_header)

        # 內容容器 (包含 Tool UI + 佐證 + 結果)
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)

        # 左側：標準 Tool UI (Checklist, Note)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        # 1.1 邏輯提示
        self._build_logic_hint(left_layout)

        # 1.2 規範敘述區
        self._build_narrative(left_layout)

        # 1.3 Checkbox 區塊
        self._build_checklist(left_layout)

        # 1.4 備註區
        self._build_note_section(left_layout)

        # 1.5 佐證資料區 (延伸填滿剩餘空間)
        self._build_attachment_section(left_layout)

        # 最終判定與儲存會在底部固定區域處理
        # 移除 addStretch，讓佐證資料區填滿空間

        content_layout.addWidget(left_widget, stretch=1)

        # 右側：客製化區域 (子類別覆寫此方法)
        right_widget = self._build_custom_section()
        if right_widget:
            content_layout.addWidget(right_widget, stretch=1)

        # 建立 ScrollArea 包裹內容
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content_widget)
        scroll.setFrameShape(QFrame.NoFrame)  # 移除邊框讓外觀更乾淨

        main_layout.addWidget(scroll, stretch=1)

        # 底部固定區：最終判定 + 儲存按鈕
        bottom_bar = QHBoxLayout()
        bottom_bar.setContentsMargins(5, 5, 5, 5)
        bottom_bar.setSpacing(10)

        # 最終判定
        bottom_bar.addWidget(QLabel("最終判定:"))  # 不 stretch，只佔文字寬度
        self.result_combo = QComboBox()
        self.result_combo.addItems(
            [STATUS_UNCHECKED, STATUS_PASS, STATUS_FAIL, STATUS_NA]
        )
        self.result_combo.currentTextChanged.connect(self.result_changed)
        bottom_bar.addWidget(self.result_combo, stretch=1)

        # 儲存按鈕
        self.btn_save = QPushButton("儲存")
        self.btn_save.setStyleSheet(
            "background-color: #4CAF50; color: white; font-weight: bold; padding: 10px 30px;"
        )
        self.btn_save.clicked.connect(self.save_clicked)
        bottom_bar.addWidget(self.btn_save, stretch=2)

        main_layout.addLayout(bottom_bar)

    def _build_logic_hint(self, layout: QVBoxLayout):
        """建立判定邏輯提示"""
        S = BaseTestToolStrings
        logic_desc = S.LOGIC_AND if self.logic == "AND" else S.LOGIC_OR
        lbl_logic = QLabel(f"{S.LOGIC_PREFIX}{logic_desc}")
        lbl_logic.setStyleSheet(Styles.LOGIC_HINT)
        layout.addWidget(lbl_logic)

    def _build_narrative(self, layout: QVBoxLayout):
        """建立規範敘述區"""
        S = BaseTestToolStrings
        narrative = self.config.get("narrative", {})
        checklist_data = self.config.get("checklist", [])

        method_text = narrative.get("method", S.NO_METHOD_DESC)
        criteria_text = narrative.get("criteria", "")

        # 自動生成判定標準
        if not criteria_text and checklist_data:
            header = S.CRITERIA_ANY if self.logic == "OR" else S.CRITERIA_ALL
            lines = [
                f"({i+1}) {item.get('content', '')}"
                for i, item in enumerate(checklist_data)
            ]
            criteria_text = f"{header}{S.CRITERIA_ELSE}" + "\n".join(lines)

        method_html = method_text.replace("\n", "<br>")
        criteria_html = criteria_text.replace("\n", "<br>")

        display_html = (
            f"{S.HTML_METHOD_TITLE}"
            f"<div style='margin-left:10px; color:#555;'>{method_html}</div>"
            f"{S.HTML_CRITERIA_TITLE}"
            f"<div style='margin-left:10px; color:#D32F2F;'>{criteria_html}</div>"
        )

        self.desc_edit = QTextEdit()
        self.desc_edit.setHtml(display_html)
        self.desc_edit.setReadOnly(True)
        self.desc_edit.setStyleSheet(Styles.DESC_BOX)
        # self.desc_edit.setMinimumHeight(150)
        self.desc_edit.setMaximumHeight(250)
        self.desc_edit.setLineWrapMode(QTextEdit.WidgetWidth)
        self.desc_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        g1 = QGroupBox(S.GB_NARRATIVE)
        v1 = QVBoxLayout()
        v1.setContentsMargins(1, 1, 1, 1)
        v1.addWidget(self.desc_edit)
        g1.setLayout(v1)
        layout.addWidget(g1)

    def _build_checklist(self, layout: QVBoxLayout):
        """建立 Checkbox 列表"""
        S = BaseTestToolStrings
        checklist_data = self.config.get("checklist", [])
        if not checklist_data:
            return

        gb = QGroupBox(S.GB_CHECKLIST)
        gb_layout = QVBoxLayout()
        gb_layout.setContentsMargins(1, 1, 1, 1)
        gb_layout.setSpacing(8)

        for item in checklist_data:
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(10)

            chk = QCheckBox()
            chk.setFixedWidth(25)
            chk.setStyleSheet(Styles.CHECKBOX)

            content = item.get("content", item.get("id"))
            item_id = item["id"]

            lbl = QLabel(content)
            lbl.setWordWrap(True)
            lbl.setStyleSheet(Styles.LABEL_NORMAL)
            lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)

            # 綁定事件 - 發送 Signal
            chk.stateChanged.connect(
                lambda state, cid=item_id: self.check_changed.emit(
                    cid, state == Qt.Checked
                )
            )
            self.checks[item_id] = chk

            row_layout.addWidget(chk, 0, Qt.AlignTop)
            row_layout.addWidget(lbl, 1)
            gb_layout.addWidget(row_widget)

        gb.setLayout(gb_layout)
        layout.addWidget(gb)

    def _build_custom_section(self) -> Optional[QWidget]:
        """
        子類別擴展區 - 子類別覆寫此方法來新增專屬 UI
        回傳 QWidget 將顯示在右側，回傳 None 則不顯示
        """
        return None

    def _build_note_section(self, layout: QVBoxLayout):
        """建立備註區"""
        S = BaseTestToolStrings
        g3 = QGroupBox(S.GB_NOTE)
        v3 = QVBoxLayout()
        self.user_note = QTextEdit()
        self.user_note.setPlaceholderText(S.HINT_NOTE)
        self.user_note.setFixedHeight(80)
        self.user_note.textChanged.connect(
            lambda: self.note_changed.emit(self.user_note.toPlainText())
        )
        v3.addWidget(self.user_note)
        g3.setLayout(v3)
        layout.addWidget(g3)

    # ----- View 的 Getter/Setter 方法 (供 Controller 使用) -----

    def set_check_state(self, item_id: str, checked: bool, block_signal: bool = False):
        """設定 checkbox 狀態"""
        if item_id in self.checks:
            chk = self.checks[item_id]
            if block_signal:
                chk.blockSignals(True)
            chk.setChecked(checked)
            if block_signal:
                chk.blockSignals(False)

    def get_check_states(self) -> Dict[str, bool]:
        """取得所有 checkbox 狀態"""
        return {k: c.isChecked() for k, c in self.checks.items()}

    def get_note(self) -> str:
        return self.user_note.toPlainText()

    def set_note(self, text: str):
        if self.user_note.toPlainText() != text:
            self.user_note.setPlainText(text)


# ==============================================================================
# Tool 類別 (邏輯 + 控制層)
# ==============================================================================


class BaseTestTool(QObject):
    """
    基礎測項工具 (邏輯 + 控制層)
    職責：
    - 建立並管理 View
    - 處理 checkbox 判定邏輯 (AND/OR)
    - 計算 Pass/Fail 結果
    - 資料存取
    """

    data_updated = Signal(dict)
    status_changed = Signal(str)
    checklist_changed = Signal()

    # 新增 Signals
    save_completed = Signal(bool, str)

    def __init__(
        self, config, result_data, target, project_manager=None, save_callback=None, is_shared=False
    ):
        super().__init__()
        self.config = config
        self.result_data = result_data
        self.target = target
        self.pm = project_manager  # ProjectManager 實例
        self.save_cb = save_callback
        self.logic = config.get("logic", "AND").upper()
        self.item_uid = config.get("uid", config.get("id"))
        self.item_id = config.get("id", "")      # 檢測項目 ID (6.2.1)
        self.item_name = config.get("name", "")  # 檢測項目名稱 (身分鑑別)
        self.targets = config.get("targets", [])  # 目標列表 ["UAV", "GCS"]
        self.is_shared = is_shared               # 是否為共用模式

        # 內容對照 (用於產生失敗原因)
        self.item_content_map = {}
        for item in config.get("checklist", []):
            self.item_content_map[item["id"]] = item.get("content", item["id"])

        # 建立 View
        self.view = self._create_view(config)

        # 設定 attachment_list 的 ProjectManager 參考
        if self.view.attachment_list and self.pm:
            self.view.attachment_list.set_project_manager(self.pm)

        # 綁定 View 事件
        self.view.check_changed.connect(self._on_check_changed)
        self.view.result_changed.connect(self._on_result_changed)
        self.view.upload_pc_clicked.connect(self._on_upload_pc)
        self.view.upload_mobile_clicked.connect(self._on_upload_mobile)
        self.view.save_clicked.connect(self._save)

        # 綁定 PhotoServer 事件 (如果 pm 存在)
        if self.pm:
            self.pm.photo_received.connect(self._on_photo_received)

        # 載入已存資料
        if result_data:
            self._load_data(result_data)

    def _create_view(self, config) -> BaseTestToolView:
        """
        建立 View - 子類別覆寫此方法回傳不同的 View 類別
        """
        return BaseTestToolView(config)

    def get_widget(self) -> QWidget:
        """回傳 UI Widget"""
        return self.view

    def get_user_note(self) -> str:
        return self.view.get_note()

    def set_user_note(self, text: str):
        self.view.set_note(text)

    def _on_check_changed(self, item_id: str, checked: bool):
        """處理 checkbox 變更"""
        status, fail_reason = self.calculate_result()
        self.status_changed.emit(status)

        # 自動更新 UI
        if self.view.result_combo:
            idx = self.view.result_combo.findText(status)
            if idx >= 0:
                self.view.result_combo.setCurrentIndex(idx)

        # 更新顏色與備註
        self._update_result_ui(status, fail_reason)

    def _on_result_changed(self, new_text: str):
        """處理手動變更結果"""
        self._update_result_ui(new_text)

    def _update_result_ui(self, status, fail_reason=None):
        """更新結果 UI 樣式與備註"""
        # 更新顏色
        if STATUS_PASS in status:
            s = f"background-color: {COLOR_BG_PASS}; color: {COLOR_TEXT_PASS};"
        elif STATUS_FAIL in status:
            s = f"background-color: {COLOR_BG_FAIL}; color: {COLOR_TEXT_FAIL};"
        elif STATUS_NA in status:
            s = f"background-color: {COLOR_BG_NA};"
        else:
            s = ""

        if self.view.result_combo:
            self.view.result_combo.setStyleSheet(s)

        # 更新備註 (僅在自動判定或狀態不符時更新)
        current_note = self.view.get_note()

        if STATUS_PASS in status:
            if not current_note or "未通過" in current_note or "不適用" in current_note:
                self.view.set_note("符合規範要求。")

        elif STATUS_FAIL in status:
            if "符合規範" in current_note or "不適用" in current_note:
                if not fail_reason:
                    _, fail_reason = self.calculate_result()
                self.view.set_note(fail_reason if fail_reason else "未通過，原因：")

        elif STATUS_NA in status:
            if (
                not current_note
                or "符合規範" in current_note
                or "未通過" in current_note
            ):
                self.view.set_note("不適用，原因如下：\n")

    def calculate_result(self) -> Tuple[str, str]:
        """計算判定結果"""
        check_states = self.view.get_check_states()
        if not check_states:
            return STATUS_FAIL, "無檢查項目"

        values = list(check_states.values())

        if self.logic == "OR":
            is_pass = any(values)
        else:
            is_pass = all(values)

        status = STATUS_PASS if is_pass else STATUS_FAIL
        fail_reason = ""

        if status == STATUS_FAIL:
            if self.logic == "AND":
                fail_list = [
                    self.item_content_map.get(cid, cid)
                    for cid, checked in check_states.items()
                    if not checked
                ]
                if fail_list:
                    fail_reason = "未通過，原因如下：\n" + "\n".join(
                        f"- 未符合：{r}" for r in fail_list
                    )
            else:  # OR
                fail_reason = "未通過，原因：上述所有項目皆未符合。"

        return status, fail_reason

    def get_result(self) -> Dict:
        """取得結果資料 (供儲存)"""
        # 收集基本資料
        data = {
            "criteria": self.view.get_check_states(),
            "description": self.view.get_note(),
        }

        # 收集結果
        if self.view.result_combo:
            data["result"] = self.view.result_combo.currentText()

        # 收集附件
        if self.view.attachment_list:
            attachments = self.view.attachment_list.get_all_attachments()
            # 轉換為相對路徑
            if self.pm and self.pm.current_project_path:
                for att in attachments:
                    full_path = att["path"]
                    if os.path.isabs(full_path) and full_path.startswith(
                        self.pm.current_project_path
                    ):
                        rel = os.path.relpath(full_path, self.pm.current_project_path)
                        att["path"] = rel.replace("\\", "/")
            data["attachments"] = attachments

        return data

    def _save(self):
        """儲存資料"""
        if not self.pm:
            return

        # 儲存前先處理重命名（讓 JSON 記錄新的檔案路徑）
        if self.view.attachment_list:
            self.view.attachment_list.flush_pending_renames()

        final_data = self.get_result()
        final_data["criteria_version_snapshot"] = self.config.get("criteria_version")

        if self.save_cb:
            self.save_cb(final_data)
        else:
            self.pm.update_test_result(self.item_uid, self.target, final_data)
            
            # 儲存成功後，執行延遲刪除（將待刪除檔案移到 trash）
            if self.view.attachment_list:
                self.view.attachment_list.flush_pending_trash()

            # 刷新 UI：重新載入資料以確保介面與儲存結果一致 (例如 timestamp, 檔名)
            saved_data = self.pm.get_test_result(self.item_uid, self.target)
            
            # 必須先清空附件列表，避免重複添加
            if self.view.attachment_list:
                self.view.attachment_list.clear()
            
            self.load_data(saved_data)

            QMessageBox.information(self.view, "成功", "已儲存")

        self.save_completed.emit(True, "Saved")

    def set_project_path(self, path):
        """相容性方法"""
        pass

    def _on_upload_pc(self):
        """電腦上傳"""
        if not self.pm or not self.pm.current_project_path:
            return

        files, _ = QFileDialog.getOpenFileNames(
            self.view,
            "選擇檔案",
            "",
            "All Files (*)",
        )
        if files:
            img_exts = [
                ".jpg",
                ".jpeg",
                ".png",
                ".bmp",
                ".gif",
                ".webp",
                ".svg",
                ".ico",
                ".tif",
                ".tiff",
                ".heic",
            ]
            for f_path in files:
                ext = os.path.splitext(f_path)[1].lower()
                ftype = "img" if ext in img_exts else "file"
                
                # 使用原檔名 (去除副檔名) 作為標題
                title = os.path.splitext(os.path.basename(f_path))[0]
                
                # 使用新的 import_attachment 方法（支援多目標）
                rel_path = self.pm.import_attachment(
                    f_path,
                    self.item_id,
                    self.item_name,
                    file_type=ftype,
                    title=title,
                    targets=self.targets,
                    target=self.target,
                    is_shared=self.is_shared,
                )
                if rel_path:
                    full_path = os.path.join(self.pm.current_project_path, rel_path)
                    display_type = "image" if ftype == "img" else "file"
                    self.view.attachment_list.add_attachment(full_path, title, display_type)

    def _on_upload_mobile(self):
        """手機上傳"""
        if not self.pm or not self.pm.current_project_path:
            return

        title = f"{self.item_uid} 佐證 ({self.target})"
        url = self.pm.generate_mobile_link(self.item_uid, title, is_report=False)
        if url:
            QRCodeDialog(self.view, self.pm, url, title).exec()

    def _on_photo_received(self, item_uid, target, path, title):
        """接收手機照片"""
        if item_uid == self.item_uid:
            self.view.attachment_list.add_attachment(path, title, "image")

    def _load_data(self, data):
        """載入已存資料"""
        saved_criteria = data.get("criteria", {})

        # 回填 Checkbox
        for cid, checked in saved_criteria.items():
            self.view.set_check_state(cid, checked, block_signal=True)

        # 回填備註
        self.view.set_note(data.get("description", ""))

        # 回填結果
        saved_res = data.get("result", STATUS_UNCHECKED)
        if self.view.result_combo:
            idx = self.view.result_combo.findText(saved_res)
            if idx >= 0:
                self.view.result_combo.setCurrentIndex(idx)
            self._update_result_ui(saved_res)

        # 回填附件
        attachments = data.get("attachments", [])
        if self.view.attachment_list and self.pm and self.pm.current_project_path:
            for item in attachments:
                rel_path = item["path"]
                full_path = rel_path
                if not os.path.isabs(rel_path):
                    full_path = os.path.join(self.pm.current_project_path, rel_path)

                self.view.attachment_list.add_attachment(
                    full_path, item.get("title", ""), item.get("type", "image")
                )

    def load_data(self, data):
        """公開的載入方法"""
        self._load_data(data)


if __name__ == "__main__":
    import sys
    import os
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    dummy_config = {
        "id": "test_cmd",
        "name": "獨立測試視窗",
        "logic": "AND",
        "checklist": [{"id": "chk1", "content": "測試檢查點"}],
    }

    # 直接實例化 Tool (包含邏輯與控制)
    tool = BaseTestTool(dummy_config, {}, "test_target")
    # tool.set_project_path(os.path.join(os.path.expanduser("~"), "Desktop"))

    tool.get_widget().show()
    sys.exit(app.exec())
