"""
無邊框主視窗模組
"""

from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QColor, QCursor
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QFrame,
    QGraphicsDropShadowEffect,
)

from styles import Styles, THEME
from .title_bar import CustomTitleBar


class BorderedMainWindow(QMainWindow):
    """通用無邊框視窗"""


    SHADOW_WIDTH = 3
    BORDER_WIDTH = 5

    def __init__(self, parent=None):
        super().__init__(parent)

        # 基礎設定
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)

        self._is_max = False
        self._resize_dir = None

        # 建立陰影容器
        self._shadow_container = QWidget()
        self._shadow_container.setMouseTracking(True)
        super().setCentralWidget(self._shadow_container)

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
        self.title_bar = CustomTitleBar(self)
        self._frame_layout.addWidget(self.title_bar)

        # 內部代理視窗
        self._inner_window = QMainWindow()
        self._inner_window.setWindowFlags(Qt.Widget)
        self._inner_window.setAttribute(Qt.WA_TranslucentBackground)
        self._frame_layout.addWidget(self._inner_window)

        # 初始化事件監聽與主題
        self.installEventFilter(self)
        self.apply_system_theme()

    # 代理方法
    def setCentralWidget(self, widget):
        self._inner_window.setCentralWidget(widget)

    def centralWidget(self):
        return self._inner_window.centralWidget()

    def setMenuBar(self, menu_bar):
        self._inner_window.setMenuBar(menu_bar)

    def menuBar(self):
        return self._inner_window.menuBar()

    def setStatusBar(self, status_bar):
        self._inner_window.setStatusBar(status_bar)

    def statusBar(self):
        return self._inner_window.statusBar()

    def setWindowTitle(self, title):
        super().setWindowTitle(title)
        if hasattr(self, "title_bar"):
            self.title_bar.title_label.setText(title)

    # 主題與外觀
    def apply_system_theme(self):
        self._apply_theme(THEME)

    def _apply_theme(self, theme):
        self.frame.setStyleSheet(Styles.FRAME_NORMAL.format(**theme))
        self._inner_window.setStyleSheet(Styles.INNER_WINDOW.format(**theme))
        self.shadow.setColor(QColor(theme["shadow"]))
        self.title_bar.update_theme(theme)

    def changeEvent(self, event):
        if event.type() == QEvent.PaletteChange:
            self.apply_system_theme()
        elif event.type() == QEvent.WindowStateChange:
            # 監聯系統視窗管理器對視窗狀態的變更（例如拖到螢幕頂部自動最大化）
            is_now_maximized = bool(self.windowState() & Qt.WindowMaximized)
            
            if is_now_maximized != self._is_max:
                self._is_max = is_now_maximized
                
                if is_now_maximized:
                    # 視窗被最大化，移除邊距
                    self._container_layout.setContentsMargins(0, 0, 0, 0)
                    self.frame.setStyleSheet(Styles.FRAME_MAXIMIZED.format(**THEME))
                else:
                    # 視窗被還原，恢復邊距
                    self._container_layout.setContentsMargins(
                        self.SHADOW_WIDTH,
                        self.SHADOW_WIDTH,
                        self.SHADOW_WIDTH,
                        self.SHADOW_WIDTH,
                    )
                    self.frame.setStyleSheet(Styles.FRAME_NORMAL.format(**THEME))
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
        if d and not self._is_max:
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

    def toggle_maximize(self):
        if self._is_max:
            self.showNormal()
            self._is_max = False
            self._container_layout.setContentsMargins(
                self.SHADOW_WIDTH,
                self.SHADOW_WIDTH,
                self.SHADOW_WIDTH,
                self.SHADOW_WIDTH,
            )
            self.frame.setStyleSheet(Styles.FRAME_NORMAL.format(**THEME))
        else:
            self.showMaximized()
            self._is_max = True
            self._container_layout.setContentsMargins(0, 0, 0, 0)
            self.frame.setStyleSheet(Styles.FRAME_MAXIMIZED.format(**THEME))
