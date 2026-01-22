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
    QDateEdit,
    QGroupBox,
    QCheckBox,
    QToolButton,
    QDialogButtonBox,
    QFileDialog,
    QWidget,
    QScrollArea,
    QFrame,
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
        form = QFormLayout(form_container)
        form.setContentsMargins(10, 10, 10, 10)
        desktop = DEFAULT_DESKTOP_PATH

        for field in self.meta_schema:
            key = field["key"]
            f_type = field["type"]
            label = field["label"]

            if f_type == "hidden":
                continue

            widget = None

            if f_type == "text":
                widget = QLineEdit()
                if self.is_edit_mode and key in self.existing_data:
                    widget.setText(str(self.existing_data[key]))
                    if key == "project_name":
                        widget.setReadOnly(True)
                        widget.setStyleSheet("background-color:#f0f0f0;")

            elif f_type == "date":
                widget = QDateEdit()
                widget.setCalendarPopup(True)
                widget.setDisplayFormat(DATE_FMT_QT)
                if self.is_edit_mode and key in self.existing_data:
                    widget.setDate(
                        QDate.fromString(self.existing_data[key], DATE_FMT_QT)
                    )
                else:
                    widget.setDate(QDate.currentDate())

            elif f_type == "path_selector":
                widget = QWidget()
                h = QHBoxLayout(widget)
                h.setContentsMargins(0, 0, 0, 0)
                pe = QLineEdit()
                btn = QToolButton()
                btn.setText("...")

                if self.is_edit_mode:
                    pe.setText(self.existing_data.get(key, ""))
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

                vals = self.existing_data.get(key, []) if self.is_edit_mode else []
                widget.checkboxes = []
                for o in opts:
                    chk = QCheckBox(o["label"])
                    chk.setProperty("val", o["value"])
                    if self.is_edit_mode and o["value"] in vals:
                        chk.setChecked(True)
                    v.addWidget(chk)
                    widget.checkboxes.append(chk)

            if widget:
                form.addRow(label, widget)
                self.inputs[key] = {"w": widget, "t": f_type}

        # 將表單容器放入滾動區域
        scroll.setWidget(form_container)
        layout.addWidget(scroll)

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
            w = inf["w"]
            t = inf["t"]
            if t == "text":
                data[key] = w.text()
            elif t == "date":
                data[key] = w.date().toString(DATE_FMT_QT)
            elif t == "path_selector":
                data[key] = w.line_edit.text()
            elif t == "checkbox_group":
                data[key] = [c.property("val") for c in w.checkboxes if c.isChecked()]
        return data


if __name__ == "__main__":
    app = QApplication([])
    controller = ProjectFormController(None, {})
    result = controller.run()
    print(result)
    app.exec()
