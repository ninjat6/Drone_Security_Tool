"""
附件元件模組
"""

import os
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
)

from styles import Styles
from .aspect_label import AspectLabel
from .image_editor.editor_dialog import ImageEditorDialog


class AttachmentItemWidget(QWidget):
    """附件項目元件"""

    on_delete = Signal(QWidget)
    on_image_click = Signal(str)  # 圖片點擊信號，傳送檔案路徑

    def __init__(
        self, file_path, title="", file_type="image", row_height=90, extra_data=None
    ):
        super().__init__()
        self.file_path = file_path
        self.file_type = file_type
        self.row_height = row_height
        self.extra_data = extra_data or {}  # 額外欄位 (e.g. command)

        # 追蹤原始標題（用於判斷是否需要重命名檔案）
        self._original_title = title

        # 強制設定整列的高度 (包含 padding)
        self.setFixedHeight(self.row_height)

        self._init_ui(title)

    def _init_ui(self, title):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        # --- 1. 拖曳手柄 ---
        lbl_handle = QLabel("☰")
        lbl_handle.setStyleSheet("color: #aaa; font-size: 16pt;")
        lbl_handle.setCursor(Qt.SizeAllCursor)
        # lbl_handle.setFixedWidth(25)
        lbl_handle.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_handle)

        # --- 2. 圖片 (AspectLabel) ---
        self.lbl_icon = AspectLabel()
        self.lbl_icon.setFixedWidth(int(self.row_height * 1.3))
        self.lbl_icon.setAlignment(Qt.AlignCenter)
        self.lbl_icon.setStyleSheet(Styles.THUMBNAIL)

        if self.file_type == "image" and os.path.exists(self.file_path):
            pix = QPixmap(self.file_path)
            if not pix.isNull():
                self.lbl_icon.setPixmap(pix)
                # 設定游標和工具提示
                self.lbl_icon.setCursor(Qt.PointingHandCursor)
                self.lbl_icon.setToolTip("點擊編輯圖片")
            else:
                self.lbl_icon.setText("Error")
        else:
            self.lbl_icon.setText(self.file_type)

        # 連接點擊事件
        self.lbl_icon.mousePressEvent = self._on_icon_click

        layout.addWidget(self.lbl_icon)

        # --- 3. 資訊區 (單行佈局) ---
        filename = os.path.basename(self.file_path)

        # 標題輸入框
        self.edit_title = QLineEdit(title if title else filename)
        self.edit_title.setPlaceholderText("請輸入說明...")
        self.edit_title.setStyleSheet(Styles.ATTACHMENT_TITLE + " font-size: 9pt;")
        self.edit_title.setToolTip(f"檔案: {filename}")  # Hover 顯示完整檔名

        layout.addWidget(self.edit_title, 1)

        # --- 4. 刪除按鈕 ---
        btn_del = QPushButton("✕")
        btn_del.setFixedSize(30, 30)
        btn_del.setCursor(Qt.PointingHandCursor)
        btn_del.setStyleSheet(Styles.BTN_DANGER)
        btn_del.clicked.connect(lambda: self.on_delete.emit(self))
        layout.addWidget(btn_del)

    def get_current_title(self) -> str:
        """取得使用者輸入的標題"""
        return self.edit_title.text()

    def is_title_changed(self) -> bool:
        """檢查標題是否有變更"""
        return self.get_current_title() != self._original_title

    def update_file_path(self, new_path: str):
        """更新檔案路徑（重命名後呼叫）"""
        self.file_path = new_path
        self._original_title = self.get_current_title()
        # 更新 tooltip
        self.edit_title.setToolTip(f"檔案: {os.path.basename(new_path)}")

    def _on_icon_click(self, event):
        """圖片縮圖點擊事件"""
        if self.file_type == "image" and os.path.exists(self.file_path):
            self.on_image_click.emit(self.file_path)

    def refresh_thumbnail(self):
        """重新載入縮圖（編輯後呼叫）"""
        if self.file_type == "image" and os.path.exists(self.file_path):
            pix = QPixmap(self.file_path)
            if not pix.isNull():
                self.lbl_icon.setPixmap(pix)

    def get_data(self):
        data = {
            "type": self.file_type,
            "path": self.file_path,
            "title": self.edit_title.text(),
        }
        # 合併額外欄位
        data.update(self.extra_data)
        return data


class AttachmentListWidget(QListWidget):
    """支援拖曳排序且高度自適應的列表元件"""

    # 圖片編輯信號，傳送 (檔案路徑, widget)
    on_image_edit = Signal(str, QWidget)

    def __init__(self):
        super().__init__()
        self.setDragDropMode(QListWidget.InternalMove)
        self.setSelectionMode(QListWidget.SingleSelection)
        self.setSpacing(2)
        self.setResizeMode(QListWidget.Adjust)
        self.setStyleSheet(Styles.ATTACHMENT_LIST)

        # 一列高度 (包含圖片和多行文字的最大高度)
        self.row_height = 40

        # ProjectManager 參考 (用於 move_to_trash)
        self.pm = None

        # 待刪除檔案列表（延遲刪除：儲存時才真正移動）
        self.pending_trash = []

    def set_project_manager(self, pm):
        """設定 ProjectManager 參考"""
        self.pm = pm

    def add_attachment(self, file_path, title="", file_type="image"):
        item = QListWidgetItem(self)

        # 建立 Widget，傳入高度限制
        widget = AttachmentItemWidget(
            file_path, title, file_type, row_height=self.row_height
        )

        self.setItemWidget(item, widget)

        # 設定 Item 的 SizeHint 與 Widget 高度一致
        item.setSizeHint(QSize(widget.sizeHint().width(), self.row_height))

        widget.on_delete.connect(self.remove_attachment_row)
        widget.on_image_click.connect(
            lambda path, w=widget: self._open_image_editor(path, w)
        )

    def add_attachment_with_extra(
        self, file_path, title="", file_type="image", extra_data=None
    ):
        """加入附件並附帶額外欄位 (e.g. command)"""
        item = QListWidgetItem(self)

        widget = AttachmentItemWidget(
            file_path,
            title,
            file_type,
            row_height=self.row_height,
            extra_data=extra_data,
        )

        self.setItemWidget(item, widget)
        item.setSizeHint(QSize(widget.sizeHint().width(), self.row_height))
        widget.on_delete.connect(self.remove_attachment_row)
        widget.on_image_click.connect(
            lambda path, w=widget: self._open_image_editor(path, w)
        )

    def remove_attachment_row(self, widget):
        """移除附件列（延遲刪除：只從 UI 移除，儲存時才移動檔案）"""
        for i in range(self.count()):
            item = self.item(i)
            if self.itemWidget(item) == widget:
                # 將檔案路徑加入待刪除列表（延遲刪除）
                if hasattr(widget, "file_path") and widget.file_path:
                    self.pending_trash.append(widget.file_path)

                self.takeItem(i)
                break

    def flush_pending_trash(self):
        """
        執行延遲刪除：將待刪除檔案移到 trash
        應在 儲存 時呼叫
        """
        if not self.pm:
            self.pending_trash.clear()
            return

        for file_path in self.pending_trash:
            self.pm.move_to_trash(file_path)

        self.pending_trash.clear()

    def clear_pending_trash(self):
        """清空待刪除列表（不執行刪除）"""
        self.pending_trash.clear()

    def flush_pending_renames(self):
        """
        處理標題變更：重命名檔案以符合新標題
        應在 儲存 時呼叫
        """
        if not self.pm:
            return

        for i in range(self.count()):
            item = self.item(i)
            widget = self.itemWidget(item)
            if (
                widget
                and hasattr(widget, "is_title_changed")
                and widget.is_title_changed()
            ):
                new_title = widget.get_current_title()
                old_path = widget.file_path

                # 呼叫 ProjectManager 重命名檔案
                new_path = self.pm.rename_attachment(old_path, new_title)
                if new_path:
                    widget.update_file_path(new_path)

    def get_all_attachments(self) -> list:
        """取得所有附件資料"""
        results = []
        for i in range(self.count()):
            item = self.item(i)
            widget = self.itemWidget(item)
            if widget:
                results.append(widget.get_data())
        return results

    def _open_image_editor(self, image_path: str, widget: AttachmentItemWidget):
        """開啟圖片編輯器"""
        if not os.path.exists(image_path):
            return

        # 建立編輯器對話框
        # 傳入 self.pm (ProjectManager) 以支援自動備份至 rawdatas
        dialog = ImageEditorDialog(
            image_path=image_path,
            project_manager=self.pm,
            parent=self.window() if self.window() else self,
        )

        if dialog.exec():
            # 編輯完成，刷新縮圖
            widget.refresh_thumbnail()

            # 如果還是需要通知外部 (例如 main_app 可能有其他邏輯)，可以保留發送
            # self.on_image_edit.emit(image_path, widget)
