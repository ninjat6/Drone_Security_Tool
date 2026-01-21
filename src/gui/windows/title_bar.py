"""
自訂標題列模組
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
    QPushButton,
)

from styles import Styles


class CustomTitleBar(QWidget):
    """自訂標題列"""

    def __init__(self, parent_window):
        super().__init__(parent_window)
        self.parent_window = parent_window
        self.setFixedHeight(36)
        self.setMouseTracking(True)

        # 標題 Label (獨立層，不加入 Layout)
        self.title_label = QLabel("MainWindow", self)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setAttribute(Qt.WA_TransparentForMouseEvents)

        # 按鈕 Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(0)

        # 視窗控制按鈕 (使用 SVG 圖示)
        import os
        from PySide6.QtGui import QIcon, QPixmap, QPainter
        from PySide6.QtCore import QSize
        from PySide6.QtSvg import QSvgRenderer

        icons_dir = os.path.join(os.path.dirname(__file__), "..", "resources", "icons")

        # 應用程式圖標 (最左側) - 使用 QSvgRenderer 高品質渲染，支援高 DPI
        self.app_icon_label = QLabel(self)
        app_icon_path = os.path.join(icons_dir, "UAV_Security_Tool_icon_v3.svg")

        # 取得螢幕 DPI 縮放比例
        from PySide6.QtWidgets import QApplication

        device_pixel_ratio = QApplication.primaryScreen().devicePixelRatio()
        icon_size = 24
        render_size = int(icon_size * device_pixel_ratio)

        svg_renderer = QSvgRenderer(app_icon_path)
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

        self.btn_min = QPushButton()
        self.btn_max = QPushButton()
        self.btn_close = QPushButton()

        self.btn_min.setIcon(QIcon(os.path.join(icons_dir, "Minimize.svg")))
        self.btn_max.setIcon(QIcon(os.path.join(icons_dir, "Maximize.svg")))
        self.btn_close.setIcon(QIcon(os.path.join(icons_dir, "Close.svg")))

        self.buttons = [self.btn_min, self.btn_max, self.btn_close]

        for b in self.buttons:
            b.setFixedSize(32, 32)
            b.setIconSize(QSize(16, 16))

        self.btn_min.clicked.connect(parent_window.showMinimized)
        self.btn_max.clicked.connect(parent_window.toggle_maximize)
        self.btn_close.clicked.connect(parent_window.close)

        layout.addWidget(self.btn_min)
        layout.addWidget(self.btn_max)
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
        for b in self.buttons:
            b.setStyleSheet(btn_style)
        self.btn_close.setStyleSheet(btn_style + Styles.TITLE_BTN_CLOSE)

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return

        top_resize_limit = self.parent_window.y() + self.parent_window.BORDER_WIDTH + 10
        if (
            event.globalPosition().y() < top_resize_limit
            and not self.parent_window.isMaximized()
        ):
            event.ignore()
            return

        if self.parent_window.windowHandle().startSystemMove():
            event.accept()

    def mouseDoubleClickEvent(self, event):
        top_resize_limit = self.parent_window.y() + self.parent_window.BORDER_WIDTH + 10
        if (
            event.button() == Qt.LeftButton
            and event.globalPosition().y() > top_resize_limit
        ):
            self.parent_window.toggle_maximize()
