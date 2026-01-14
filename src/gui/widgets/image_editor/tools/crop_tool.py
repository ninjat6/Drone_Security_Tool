"""
剪裁工具
"""

from typing import Optional, Dict

from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QMouseEvent, QPen, QColor, QBrush, QCursor
from PySide6.QtWidgets import (
    QGraphicsRectItem,
    QGraphicsItem,
)

from .base_tool import BaseTool


class CropTool(BaseTool):
    """
    剪裁工具 (進階版)

    支援：
    1. 8個方位的控制點 (Handles) 調整大小
    2. 拖曳內部移動選取範圍
    3. 預設選取整張圖片
    4. 遮罩顯示
    """

    HANDLE_SIZE = 10  # 控制點大小
    MIN_SIZE = 20  # 最小選取尺寸

    def __init__(self, canvas):
        super().__init__(canvas)
        self._selection_rect: Optional[QGraphicsRectItem] = None
        self._overlay_items = []
        self._handles: Dict[str, QGraphicsRectItem] = {}

        # 狀態
        self._state = "idle"  # idle, creating, moving, resizing
        self._active_handle = None
        self._last_pos = None

    def on_activate(self):
        """啟用時設定"""
        self._canvas.setCursor(Qt.ArrowCursor)

        # 預設選取整張圖片
        pixmap = self._canvas.get_pixmap()
        if pixmap:
            rect = QRectF(pixmap.rect())
            # 留一點邊距 (例如 90% 大小) 以便觀察
            # rect = rect.adjusted(...)
            # 這裡直接選全圖比較直觀
            self._create_selection(rect)

    def on_deactivate(self):
        """停用時清除"""
        self._clear_selection()
        self._canvas.setCursor(Qt.ArrowCursor)

    def set_crop_rect(self, rect: QRectF):
        """設定剪裁範圍"""
        self._create_selection(rect)

    def on_mouse_press(self, event: QMouseEvent, scene_pos: QPointF):
        """滑鼠按下"""
        if not self._canvas.get_pixmap():
            return

        self._last_pos = scene_pos

        # 1. 檢查是否點擊了控制點 -> Resizing
        handle_name = self._hit_test_handles(scene_pos)
        if handle_name:
            self._state = "resizing"
            self._active_handle = handle_name
            return

        # 2. 檢查是否點擊了選取範圍內部 -> Moving
        if self._selection_rect and self._selection_rect.contains(scene_pos):
            self._state = "moving"
            self._canvas.setCursor(Qt.SizeAllCursor)
            return

        # 3. 點擊外部 -> 開始新選取 (Creating)
        self._clear_selection()
        self._state = "creating"
        self._create_selection(QRectF(scene_pos, scene_pos))
        # 必須在 create_selection 後設定，因為 create 會呼叫 clear
        self._start_pos = scene_pos

    def on_mouse_move(self, event: QMouseEvent, scene_pos: QPointF):
        """滑鼠移動"""
        if not self._is_active:
            return

        # 更新游標狀態 (如果沒在操作)
        if self._state == "idle":
            self._update_cursor(scene_pos)
            return

        if self._state == "creating":
            rect = QRectF(self._start_pos, scene_pos).normalized()
            self._update_selection_rect(rect)

        elif self._state == "moving":
            if self._selection_rect and self._last_pos:
                delta = scene_pos - self._last_pos
                rect = self._selection_rect.rect().translated(delta)
                self._update_selection_rect(rect)
                self._last_pos = scene_pos

        elif self._state == "resizing":
            if self._selection_rect and self._active_handle:
                rect = self._calculate_resize(
                    self._selection_rect.rect(), self._active_handle, scene_pos
                )
                self._update_selection_rect(rect)

    def on_mouse_release(self, event: QMouseEvent, scene_pos: QPointF):
        """滑鼠釋放"""
        if self._state == "creating":
            # 檢查是否太小
            if self._selection_rect:
                if (
                    self._selection_rect.rect().width() < self.MIN_SIZE
                    or self._selection_rect.rect().height() < self.MIN_SIZE
                ):
                    self._clear_selection()

        self._state = "idle"
        self._active_handle = None
        self._last_pos = None
        self._update_cursor(scene_pos)

    # ===== 核心邏輯 =====

    def _create_selection(self, rect: QRectF):
        """建立選取範圍"""
        self._clear_selection()

        # 建立主矩形
        self._selection_rect = QGraphicsRectItem()
        # Windows 風格：白線 + 虛線邊框
        self._selection_rect.setPen(QPen(Qt.white, 1, Qt.SolidLine))
        self._selection_rect.setBrush(Qt.NoBrush)
        self.scene.addItem(self._selection_rect)

        # 建立控制點
        self._create_handles()

        # 更新位置
        self._update_selection_rect(rect)

    def _create_handles(self):
        """建立 8 個控制點"""
        from PySide6.QtWidgets import QGraphicsEllipseItem

        positions = ["tl", "t", "tr", "r", "br", "b", "bl", "l"]
        hs = self.HANDLE_SIZE

        for pos in positions:
            # 使用圓形控制點，與 rect_tool 一致
            item = QGraphicsEllipseItem(-hs / 2, -hs / 2, hs, hs)
            item.setBrush(QBrush(Qt.white))
            item.setPen(QPen(Qt.black, 1))
            item.setZValue(100)  # 確保在最上層
            # 忽略縮放，保持固定畫面大小
            item.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
            self.scene.addItem(item)
            self._handles[pos] = item

    def _update_selection_rect(self, rect: QRectF):
        """更新選取範圍與控制點"""
        if not self._selection_rect:
            return

        # 限制在圖片範圍內
        pixmap = self._canvas.get_pixmap()
        if pixmap:
            image_rect = QRectF(0, 0, pixmap.width(), pixmap.height())
            rect = rect.intersected(image_rect)

        self._selection_rect.setRect(rect)
        self._update_handle_positions(rect)
        self._update_overlay(rect)

    def _update_handle_positions(self, rect: QRectF):
        """更新控制點位置"""
        # 因為圓形控制點是以中心為原點定義，setPos 直接設定目標位置即可
        coords = {
            "tl": rect.topLeft(),
            "t": QPointF(rect.center().x(), rect.top()),
            "tr": rect.topRight(),
            "r": QPointF(rect.right(), rect.center().y()),
            "br": rect.bottomRight(),
            "b": QPointF(rect.center().x(), rect.bottom()),
            "bl": rect.bottomLeft(),
            "l": QPointF(rect.left(), rect.center().y()),
        }

        for name, item in self._handles.items():
            if name in coords:
                item.setPos(coords[name])

    def _update_cursor(self, scene_pos: QPointF):
        """根據位置更新游標"""
        handle = self._hit_test_handles(scene_pos)
        if handle:
            cursors = {
                "tl": Qt.SizeFDiagCursor,
                "br": Qt.SizeFDiagCursor,
                "tr": Qt.SizeBDiagCursor,
                "bl": Qt.SizeBDiagCursor,
                "t": Qt.SizeVerCursor,
                "b": Qt.SizeVerCursor,
                "l": Qt.SizeHorCursor,
                "r": Qt.SizeHorCursor,
            }
            self._canvas.setCursor(cursors.get(handle, Qt.ArrowCursor))
        elif self._selection_rect and self._selection_rect.contains(scene_pos):
            self._canvas.setCursor(Qt.SizeAllCursor)
        else:
            self._canvas.setCursor(Qt.CrossCursor)

    def _hit_test_handles(self, scene_pos: QPointF) -> Optional[str]:
        """檢查是否碰到控制點"""
        for name, item in self._handles.items():
            # 使用 mapFromScene 檢查更準確 (考慮 item 自身變換，雖然這裡是 RectItem)
            local_pos = item.mapFromScene(scene_pos)
            if item.contains(local_pos):
                return name
        return None

    def _calculate_resize(self, rect: QRectF, handle: str, pos: QPointF) -> QRectF:
        """根據拖曳控制點計算新矩形"""
        l, t, r, b = rect.left(), rect.top(), rect.right(), rect.bottom()
        x, y = pos.x(), pos.y()

        if "l" in handle:
            l = x
        if "r" in handle:
            r = x
        if "t" in handle:
            t = y
        if "b" in handle:
            b = y

        # 處理翻轉
        return QRectF(QPointF(l, t), QPointF(r, b)).normalized()

    def _update_overlay(self, selection_rect: QRectF):
        """更新遮罩"""
        self._clear_overlay()  # 清除舊的 (或可優化為更新舊的)

        pixmap = self._canvas.get_pixmap()
        if not pixmap:
            return

        image_rect = QRectF(0, 0, pixmap.width(), pixmap.height())
        overlay_color = QColor(0, 0, 0, 120)

        # 簡單一點：使用 Path 製作鏤空遮罩可能更好，但這裡沿用 4-rect 方法
        # 上
        if selection_rect.top() > 0:
            self._add_overlay_rect(
                0, 0, image_rect.width(), selection_rect.top(), overlay_color
            )
        # 下
        if selection_rect.bottom() < image_rect.height():
            self._add_overlay_rect(
                0,
                selection_rect.bottom(),
                image_rect.width(),
                image_rect.height() - selection_rect.bottom(),
                overlay_color,
            )
        # 左
        if selection_rect.left() > 0:
            self._add_overlay_rect(
                0,
                selection_rect.top(),
                selection_rect.left(),
                selection_rect.height(),
                overlay_color,
            )
        # 右
        if selection_rect.right() < image_rect.width():
            self._add_overlay_rect(
                selection_rect.right(),
                selection_rect.top(),
                image_rect.width() - selection_rect.right(),
                selection_rect.height(),
                overlay_color,
            )

    def _add_overlay_rect(self, x, y, w, h, color):
        item = QGraphicsRectItem(x, y, w, h)
        item.setBrush(QBrush(color))
        item.setPen(Qt.NoPen)
        self.scene.addItem(item)
        self._overlay_items.append(item)

    def _clear_overlay(self):
        for item in self._overlay_items:
            self.scene.removeItem(item)
        self._overlay_items.clear()

    def _clear_selection(self):
        """清除所有項目"""
        self._clear_overlay()
        if self._selection_rect:
            self.scene.removeItem(self._selection_rect)
            self._selection_rect = None

        for item in self._handles.values():
            self.scene.removeItem(item)
        self._handles.clear()

        self._start_pos = None

    def get_selection_rect(self) -> Optional[QRectF]:
        if self._selection_rect:
            return self._selection_rect.rect()
        return None

    def confirm_crop(self) -> bool:
        """確認剪裁"""
        rect = self.get_selection_rect()
        if not rect:
            return False

        # 執行剪裁
        cropped = self._canvas.crop_image(rect)
        if not cropped.isNull():
            self._canvas.update_pixmap(cropped)
            self._clear_selection()
            return True
        return False
