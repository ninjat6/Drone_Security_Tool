"""
專案總覽頁面模組
"""

import os
from functools import partial

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QGroupBox,
    QFormLayout,
    QGridLayout,
    QProgressBar,
    QScrollArea,
    QFrame,
    QSizePolicy,
    QMessageBox,
)

from constants import (
    TARGETS,
    PHOTO_ANGLES_ORDER,
    PHOTO_ANGLES_NAME,
    COLOR_BG_DEFAULT,
)
from .gallery import GalleryWindow


class OverviewPage(QWidget):
    """專案總覽頁面"""

    def __init__(self, pm, config):
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

        # 專案資訊 + 檢測進度 (水平排列)
        top_row = QWidget()
        top_row_layout = QHBoxLayout(top_row)
        top_row_layout.setContentsMargins(0, 0, 0, 0)

        # 專案資訊
        self.info_group = QGroupBox("專案資訊")
        self.info_layout = QFormLayout()
        self.info_group.setLayout(self.info_layout)
        top_row_layout.addWidget(self.info_group, 1)

        # 檢測進度
        self.prog_g = QGroupBox("檢測進度")
        self.prog_l = QVBoxLayout()
        self.prog_g.setLayout(self.prog_l)
        top_row_layout.addWidget(self.prog_g, 1)

        self.layout.addWidget(top_row)

        # 檢測照片總覽
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

            self.photo_grid.addWidget(lbl_title, 0, col, 1, 1)

            # btn_mobile removed


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



    def open_gallery(self, target):
        if not self.pm.current_project_path:
            return
        gallery = GalleryWindow(self, self.pm, target)
        gallery.exec()

    @Slot(str, str, str, str)
    def on_photo_received(self, target_id, category, path, title):
        if target_id in TARGETS:
            self.refresh_data()
