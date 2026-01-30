"""
專案表單控制器模組
"""

from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QPlainTextEdit,
    QDateEdit,
    QGroupBox,
    QCheckBox,
    QToolButton,
    QDialogButtonBox,
    QFileDialog,
    QWidget,
    QScrollArea,
    QFrame,
    QMessageBox,
)

from constants import DEFAULT_DESKTOP_PATH, DATE_FMT_QT
from dialogs.bordered_dialog import BorderedDialog


class ProjectFormController:
    """專案資訊填寫表單控制器"""

    def __init__(self, parent_window, full_config, existing_data=None):
        self.full_config = full_config
        self.meta_schema = full_config.get("project_meta_schema", [])
        self.existing_data = existing_data
        self.is_edit_mode = existing_data is not None

        self.dialog = BorderedDialog(parent_window)
        self.dialog.setWindowTitle("編輯專案" if self.is_edit_mode else "新建專案")
        self.dialog.resize(500, 600)
        self.inputs = {}
        self._init_ui()

    def _init_ui(self):
        # 取得 BorderedDialog 的內容區域佈局
        layout = self.dialog.contentWidget().layout()

        # 建立滾動區域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # 建立表單容器
        form_container = QWidget()
        main_layout = QVBoxLayout(form_container)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        # 遍歷每個群組
        for group in self.meta_schema:
            group_label = group.get("group_label", "")
            fields = group.get("fields", [])

            # 建立群組框
            group_box = QGroupBox(group_label)
            group_layout = QFormLayout(group_box)
            group_layout.setContentsMargins(10, 15, 10, 10)
            group_layout.setSpacing(8)

            # 渲染群組內的欄位
            for field in fields:
                self._create_field_widget(field, group_layout)

            main_layout.addWidget(group_box)

        main_layout.addStretch()

        # 將表單容器放入滾動區域
        scroll.setWidget(form_container)
        layout.addWidget(scroll)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.dialog.accept)
        btns.rejected.connect(self.dialog.reject)
        layout.addWidget(btns)

    def _create_field_widget(self, field, parent_layout):
        """根據欄位定義建立對應的 widget 並加入佈局"""
        key = field["key"]
        f_type = field["type"]
        label = field["label"]
        desktop = DEFAULT_DESKTOP_PATH

        if f_type == "hidden":
            return

        # 輔助函式：取得欄位值（支援物件格式 {value, remark}）
        def get_value(key, default=None):
            if key not in self.existing_data:
                return default
            field_data = self.existing_data[key]
            if isinstance(field_data, dict):
                return field_data.get("value", default)
            return field_data

        widget = None

        if f_type == "text":
            widget = QLineEdit()
            if self.is_edit_mode and key in self.existing_data:
                widget.setText(str(get_value(key, "")))
                if key == "project_name":
                    widget.setReadOnly(True)
                    widget.setStyleSheet("background-color:#f0f0f0;")

        elif f_type == "date":
            widget = QDateEdit()
            widget.setCalendarPopup(True)
            widget.setDisplayFormat(DATE_FMT_QT)
            if self.is_edit_mode and key in self.existing_data:
                widget.setDate(QDate.fromString(get_value(key, ""), DATE_FMT_QT))
            else:
                widget.setDate(QDate.currentDate())

        elif f_type == "textarea":
            widget = QPlainTextEdit()
            widget.setMaximumHeight(100)
            if self.is_edit_mode and key in self.existing_data:
                widget.setPlainText(str(get_value(key, "")))

        elif f_type == "path_selector":
            widget = QWidget()
            h = QHBoxLayout(widget)
            h.setContentsMargins(0, 0, 0, 0)
            pe = QLineEdit()
            btn = QToolButton()
            btn.setText("...")

            if self.is_edit_mode:
                pe.setText(get_value(key, "") or "")
                pe.setReadOnly(True)
                btn.setEnabled(False)
            else:
                pe.setText(desktop)
                btn.clicked.connect(lambda _, le=pe: self._browse(le))

            h.addWidget(pe)
            h.addWidget(btn)
            widget.line_edit = pe

        elif f_type == "checkbox_group":
            widget = QGroupBox()
            v = QVBoxLayout(widget)
            v.setContentsMargins(5, 5, 5, 5)

            opts = []
            if key == "test_scope":
                standards = self.full_config.get("test_standards", [])
                for sec in standards:
                    opts.append(
                        {
                            "value": sec["section_id"],
                            "label": f"{sec['section_id']} {sec['section_name']}",
                        }
                    )
            else:
                opts = field.get("options", [])

            vals = get_value(key, []) if self.is_edit_mode else []
            widget.checkboxes = []
            for o in opts:
                chk = QCheckBox(o["label"])
                chk.setProperty("val", o["value"])
                if self.is_edit_mode and o["value"] in vals:
                    chk.setChecked(True)
                v.addWidget(chk)
                widget.checkboxes.append(chk)

        if widget:
            # 處理備註功能
            has_remark = field.get("remark", False)
            remark_widget = None

            if has_remark:
                # 建立包含原欄位和備註的容器
                container = QWidget()
                h_layout = QHBoxLayout(container)
                h_layout.setContentsMargins(0, 0, 0, 0)
                h_layout.setSpacing(8)

                # 原欄位佔較大空間
                h_layout.addWidget(widget, stretch=3)

                # 備註輸入框
                remark_widget = QLineEdit()
                remark_widget.setPlaceholderText("備註...")
                if self.is_edit_mode and key in self.existing_data:
                    # 支援物件格式 {value, remark}
                    field_data = self.existing_data[key]
                    if isinstance(field_data, dict):
                        remark_widget.setText(str(field_data.get("remark", "")))
                h_layout.addWidget(remark_widget, stretch=2)

                parent_layout.addRow(label, container)
            else:
                parent_layout.addRow(label, widget)

            self.inputs[key] = {
                "w": widget,
                "t": f_type,
                "label": label,
                "required": field.get("required", False),
                "has_remark": has_remark,
                "remark_widget": remark_widget,
            }

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
        while self.dialog.exec() == QDialog.Accepted:
            errors = self._validate()
            if errors:
                QMessageBox.warning(
                    self.dialog,
                    "欄位驗證失敗",
                    "以下必填欄位尚未填寫：\n" + "\n".join(f"- {e}" for e in errors),
                )
                continue
            return self._collect()
        return None

    def _validate(self):
        """驗證必填欄位，回傳錯誤訊息列表"""
        errors = []
        for key, inf in self.inputs.items():
            if not inf.get("required", False):
                continue

            w = inf["w"]
            t = inf["t"]
            label = inf["label"]
            is_empty = False

            if t == "text":
                is_empty = not w.text().strip()
            elif t == "textarea":
                is_empty = not w.toPlainText().strip()
            elif t == "path_selector":
                is_empty = not w.line_edit.text().strip()
            elif t == "checkbox_group":
                is_empty = not any(c.isChecked() for c in w.checkboxes)
            # date 類型有預設值，不需要驗證

            if is_empty:
                errors.append(label)

        return errors

    def _collect(self):
        data = {}
        for key, inf in self.inputs.items():
            w = inf["w"]
            t = inf["t"]
            has_remark = inf.get("has_remark", False)
            remark_widget = inf.get("remark_widget")

            # 取得欄位值
            if t == "text":
                value = w.text()
            elif t == "textarea":
                value = w.toPlainText()
            elif t == "date":
                value = w.date().toString(DATE_FMT_QT)
            elif t == "path_selector":
                value = w.line_edit.text()
            elif t == "checkbox_group":
                value = [c.property("val") for c in w.checkboxes if c.isChecked()]
            else:
                value = None

            # 有備註的欄位使用物件格式 {value, remark}
            if has_remark and remark_widget:
                data[key] = {
                    "value": value,
                    "remark": remark_widget.text(),
                }
            else:
                data[key] = value

        return data


if __name__ == "__main__":
    pass
