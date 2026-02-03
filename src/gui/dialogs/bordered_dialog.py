"""
無邊框對話框模組
類似 BorderedMainWindow，但繼承自 QDialog，保留 exec() 和 Accepted/Rejected 功能
"""

from PySide6.QtCore import Qt, QEvent, QSize
from PySide6.QtGui import QColor, QCursor, QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QLabel,
    QPushButton,
    QGraphicsDropShadowEffect,
)

from styles import Styles, THEME
from gui.constants import ICON_PATH, CLOSE_ICON_PATH


class DialogTitleBar(QWidget):
    """對話框專用標題列（無最大化按鈕）"""

    def __init__(self, parent_dialog):
        super().__init__(parent_dialog)
        self.parent_dialog = parent_dialog
        self.setFixedHeight(36)
        self.setMouseTracking(True)

        # 標題 Label (獨立層，不加入 Layout)
        self.title_label = QLabel("Dialog", self)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setAttribute(Qt.WA_TransparentForMouseEvents)

        # 按鈕 Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(0)

        # 應用程式圖標 (最左側) - 使用 QSvgRenderer 高品質渲染，支援高 DPI
        from PySide6.QtWidgets import QApplication

        self.app_icon_label = QLabel(self)
        device_pixel_ratio = QApplication.primaryScreen().devicePixelRatio()
        icon_size = 24
        render_size = int(icon_size * device_pixel_ratio)

        svg_renderer = QSvgRenderer(ICON_PATH)
        app_icon_pixmap = QPixmap(render_size, render_size)
        app_icon_pixmap.fill(Qt.transparent)
        painter = QPainter(app_icon_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        svg_renderer.render(painter)
        painter.end()
        app_icon_pixmap.setDevicePixelRatio(device_pixel_ratio)

        self.app_icon_label.setPixmap(app_icon_pixmap)
        self.app_icon_label.setFixedSize(28, 28)
        self.app_icon_label.setAlignment(Qt.AlignCenter)
        self.app_icon_label.setStyleSheet("background: transparent;")
        layout.addWidget(self.app_icon_label)
        layout.addSpacing(4)

        layout.addStretch()

        # 對話框只需要關閉按鈕 (使用 SVG 圖示)
        self.btn_close = QPushButton()
        self.btn_close.setIcon(QIcon(CLOSE_ICON_PATH))
        self.btn_close.setFixedSize(32, 32)
        self.btn_close.setIconSize(QSize(16, 16))
        self.btn_close.clicked.connect(parent_dialog.reject)  # 使用 reject 而非 close

        layout.addWidget(self.btn_close)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.title_label.setGeometry(0, 0, self.width(), self.height())

    def update_theme(self, theme):
        self.setStyleSheet("background-color: transparent;")
        self.title_label.setStyleSheet(
            f"font-weight:bold; background:transparent; color: {theme['title_text']};"
        )
        btn_style = Styles.TITLE_BTN.format(**theme)
        self.btn_close.setStyleSheet(btn_style + Styles.TITLE_BTN_CLOSE)

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return

        # 檢查是否在縮放區域內，若是則讓父視窗處理
        global_pos = event.globalPosition().toPoint()
        dialog_pos = self.parent_dialog.mapFromGlobal(global_pos)
        resize_dir = self.parent_dialog._get_resize_direction(dialog_pos)

        if resize_dir:
            # 在縮放區域內，將事件傳遞給父視窗處理
            event.ignore()
            return

        # 確保視窗已經有 windowHandle
        window_handle = self.parent_dialog.windowHandle()
        if window_handle:
            if window_handle.startSystemMove():
                event.accept()
                return

        event.ignore()


class BorderedDialog(QDialog):
    """通用無邊框對話框"""

    SHADOW_WIDTH = 3
    BORDER_WIDTH = 5

    def __init__(self, parent=None):
        super().__init__(parent)

        # 基礎設定
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)

        self._resize_dir = None

        # 建立陰影容器
        self._shadow_container = QWidget()
        self._shadow_container.setMouseTracking(True)

        # 主佈局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self._shadow_container)

        # 容器佈局
        self._container_layout = QVBoxLayout(self._shadow_container)
        self._container_layout.setContentsMargins(
            self.SHADOW_WIDTH, self.SHADOW_WIDTH, self.SHADOW_WIDTH, self.SHADOW_WIDTH
        )

        # 視覺邊框 Frame
        self.frame = QFrame()
        self.frame.setObjectName("CentralFrame")
        self.frame.setMouseTracking(True)
        self._container_layout.addWidget(self.frame)

        # 陰影特效
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(0)
        self.shadow.setOffset(0, 0)
        self.frame.setGraphicsEffect(self.shadow)

        # Frame 內部佈局
        self._frame_layout = QVBoxLayout(self.frame)
        self._frame_layout.setContentsMargins(0, 0, 0, 0)
        self._frame_layout.setSpacing(0)

        # 自定義標題列
        self.title_bar = DialogTitleBar(self)
        self._frame_layout.addWidget(self.title_bar)

        # 內容區域
        self._content_widget = QWidget()
        self._content_widget.setMouseTracking(True)
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(10, 10, 10, 10)
        self._frame_layout.addWidget(self._content_widget)

        # 初始化事件監聽與主題
        self.installEventFilter(self)
        self.apply_system_theme()

    def setContentLayout(self, layout):
        """設定對話框內容佈局"""
        # 移除舊佈局
        if self._content_widget.layout():
            old_layout = self._content_widget.layout()
            while old_layout.count():
                item = old_layout.takeAt(0)
                if item.widget():
                    item.widget().setParent(None)
            QWidget().setLayout(old_layout)
        self._content_widget.setLayout(layout)

    def contentWidget(self):
        """取得內容區域 Widget"""
        return self._content_widget

    def setWindowTitle(self, title):
        super().setWindowTitle(title)
        if hasattr(self, "title_bar"):
            self.title_bar.title_label.setText(title)

    # 主題與外觀
    def apply_system_theme(self):
        self._apply_theme(THEME)

    def _apply_theme(self, theme):
        self.frame.setStyleSheet(Styles.FRAME_NORMAL.format(**theme))
        self._content_widget.setStyleSheet(f"background-color: {theme['bg_color']};")
        self.shadow.setColor(QColor(theme["shadow"]))
        self.title_bar.update_theme(theme)

    def changeEvent(self, event):
        if event.type() == QEvent.PaletteChange:
            self.apply_system_theme()
        super().changeEvent(event)

    # Resize 處理
    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseMove or event.type() == QEvent.HoverMove:
            if self._resize_dir:
                return False
            global_pos = QCursor.pos()
            local_pos = self.mapFromGlobal(global_pos)
            self._update_cursor(local_pos)
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = self.mapFromGlobal(event.globalPosition().toPoint())
            self._resize_dir = self._get_resize_direction(pos)

            if self._resize_dir:
                edges = self._convert_dir_to_edges(self._resize_dir)
                if self.windowHandle().startSystemResize(edges):
                    event.accept()
                    self._resize_dir = None
                    return

    def mouseReleaseEvent(self, event):
        self._resize_dir = None
        self.setCursor(Qt.ArrowCursor)

    def _convert_dir_to_edges(self, d):
        edges = Qt.Edges()
        if "l" in d:
            edges |= Qt.LeftEdge
        if "r" in d:
            edges |= Qt.RightEdge
        if "t" in d:
            edges |= Qt.TopEdge
        if "b" in d:
            edges |= Qt.BottomEdge
        return edges

    def _get_resize_direction(self, pos):
        w, h = self.width(), self.height()
        margin = self.SHADOW_WIDTH + self.BORDER_WIDTH
        x, y = pos.x(), pos.y()
        left, right = x < margin, x > w - margin
        top, bottom = y < margin, y > h - margin

        if top and left:
            return "tl"
        if top and right:
            return "tr"
        if bottom and left:
            return "bl"
        if bottom and right:
            return "br"
        if left:
            return "l"
        if right:
            return "r"
        if top:
            return "t"
        if bottom:
            return "b"
        return None

    def _update_cursor(self, pos):
        d = self._get_resize_direction(pos)
        if d:
            cursors = {
                "l": Qt.SizeHorCursor,
                "r": Qt.SizeHorCursor,
                "t": Qt.SizeVerCursor,
                "b": Qt.SizeVerCursor,
                "tl": Qt.SizeFDiagCursor,
                "br": Qt.SizeFDiagCursor,
                "tr": Qt.SizeBDiagCursor,
                "bl": Qt.SizeBDiagCursor,
            }
            self.setCursor(cursors[d])
        else:
            self.setCursor(Qt.ArrowCursor)


# ==============================================================================
# 測試代碼
# ==============================================================================
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import (
        QApplication,
        QFormLayout,
        QLineEdit,
        QDateEdit,
        QDialogButtonBox,
    )
    from PySide6.QtCore import QDate

    app = QApplication(sys.argv)

    # 建立 BorderedDialog
    dialog = BorderedDialog()
    dialog.setWindowTitle("測試對話框 - BorderedDialog")
    dialog.resize(400, 300)

    # 建立表單內容
    form_layout = QFormLayout()

    name_input = QLineEdit()
    name_input.setPlaceholderText("請輸入專案名稱")
    form_layout.addRow("專案名稱:", name_input)

    date_input = QDateEdit()
    date_input.setCalendarPopup(True)
    date_input.setDate(QDate.currentDate())
    form_layout.addRow("檢測日期:", date_input)

    tester_input = QLineEdit()
    tester_input.setPlaceholderText("請輸入檢測人員姓名")
    form_layout.addRow("檢測人員:", tester_input)

    # 按鈕
    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)

    # 將表單加入對話框
    content_layout = QVBoxLayout()
    content_layout.addLayout(form_layout)
    content_layout.addStretch()
    content_layout.addWidget(buttons)

    # 設定內容
    dialog.contentWidget().layout().addLayout(content_layout)

    # 執行對話框
    result = dialog.exec()

    if result == QDialog.Accepted:
        print("✅ 用戶按下確定")
        print(f"   專案名稱: {name_input.text()}")
        print(f"   檢測日期: {date_input.date().toString('yyyy-MM-dd')}")
        print(f"   檢測人員: {tester_input.text()}")
    else:
        print("❌ 用戶按下取消或關閉視窗")

    sys.exit(0)
