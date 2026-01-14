"""
圖片畫布
基於 QGraphicsView 實現，支援圖片顯示、縮放、工具繪製
"""

from typing import Optional, TYPE_CHECKING

from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import (
    QPixmap,
    QImage,
    QPainter,
    QWheelEvent,
    QMouseEvent,
    QKeyEvent,
)
from PySide6.QtWidgets import (
    QGraphicsView,
    QGraphicsScene,
    QGraphicsPixmapItem,
)

try:
    import numpy as np

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

if TYPE_CHECKING:
    from .tools.base_tool import BaseTool


class ImageCanvas(QGraphicsView):
    """
    圖片畫布

    提供圖片顯示、縮放、平移、工具繪製等功能。
    """

    # 信號
    image_changed = Signal()  # 圖片內容變更
    zoom_changed = Signal(float)  # 縮放比例變更

    # 縮放常數
    ZOOM_MIN = 0.1
    ZOOM_MAX = 10.0
    ZOOM_STEP = 1.15

    def __init__(self, parent=None):
        super().__init__(parent)

        # 建立場景
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        # 圖片項目
        self._pixmap_item: Optional[QGraphicsPixmapItem] = None
        self._original_pixmap: Optional[QPixmap] = None
        self._current_crop_rect: Optional[QRectF] = None  # 目前剪裁區域 (相對於原圖)

        # 濾鏡參數
        self._brightness: int = 0  # -128 到 128
        self._contrast: int = 0  # -128 到 128

        # 工具
        self._current_tool: Optional["BaseTool"] = None

        # 縮放
        self._zoom_factor = 1.0

        # 平移模式
        self._is_panning = False
        self._last_pan_pos = None

        # 狀態標記
        self._is_in_crop_session = False

        # 設定
        self._setup_view()

    def _setup_view(self):
        """設定視圖屬性"""
        # 渲染品質
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)

        # 拖曳模式
        self.setDragMode(QGraphicsView.NoDrag)

        # 背景
        self.setBackgroundBrush(Qt.darkGray)

        # 捲軸
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # 變換錨點
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)

        # 啟用滑鼠追蹤
        self.setMouseTracking(True)

    def load_image(self, image_path: str) -> bool:
        """
        載入圖片

        Args:
            image_path: 圖片路徑

        Returns:
            是否載入成功
        """
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            return False

        self.set_pixmap(pixmap)
        return True

    def set_pixmap(self, pixmap: QPixmap):
        """
        設定圖片

        Args:
            pixmap: QPixmap 物件
        """
        # 清除舊圖片
        if self._pixmap_item:
            self._scene.removeItem(self._pixmap_item)

        # 儲存原始圖片
        self._original_pixmap = pixmap.copy()

        # 建立新項目
        self._pixmap_item = QGraphicsPixmapItem(pixmap)
        self._scene.addItem(self._pixmap_item)

        # 設定場景大小
        self._scene.setSceneRect(QRectF(pixmap.rect()))

        # 初始化剪裁區域為全圖 (如果尚未設定)
        if (
            self._current_crop_rect is None
            or pixmap.size() != self._original_pixmap.size()
        ):
            self._current_crop_rect = QRectF(pixmap.rect())

        # 重設縮放
        self.reset_zoom()

        # 初始顯示 (這會套用預設濾鏡 0,0)
        self._refresh_display()

    def get_pixmap(self) -> Optional[QPixmap]:
        """取得目前顯示的圖片"""
        if self._pixmap_item:
            return self._pixmap_item.pixmap()
        return None

    def get_original_pixmap(self) -> Optional[QPixmap]:
        """取得原始圖片"""
        return self._original_pixmap

    def reset_to_original(self):
        """重設回原始圖片"""
        if self._original_pixmap:
            # 清空場景中所有項目
            self._scene.clear()
            self._pixmap_item = None

            # 使用副本還原，避免修改到原始備份
            # 使用副本還原，避免修改到原始備份
            self.set_pixmap(self._original_pixmap.copy())  # 這會重置 _current_crop_rect

            # 確保完全重置
            self._current_crop_rect = QRectF(self._original_pixmap.rect())

            # 重設濾鏡
            self._brightness = 0
            self._contrast = 0

            self._refresh_display()

    def update_pixmap(self, pixmap: QPixmap):
        """
        更新圖片（不重設縮放）

        Args:
            pixmap: 新的 QPixmap
        """
        if self._pixmap_item:
            self._pixmap_item.setPixmap(pixmap)
            self._scene.setSceneRect(QRectF(pixmap.rect()))
            self.image_changed.emit()

    def set_tool(self, tool: Optional["BaseTool"]):
        """
        設定目前工具

        Args:
            tool: 工具實例，None 表示無工具
        """
        if self._current_tool:
            self._current_tool.deactivate()

        self._current_tool = tool

        if self._current_tool:
            self._current_tool.activate()

    def get_tool(self) -> Optional["BaseTool"]:
        """取得目前工具"""
        return self._current_tool

    # ===== 縮放功能 =====

    def zoom_in(self):
        """放大"""
        self._apply_zoom(self.ZOOM_STEP)

    def zoom_out(self):
        """縮小"""
        self._apply_zoom(1 / self.ZOOM_STEP)

    def reset_zoom(self):
        """重設縮放"""
        self.resetTransform()
        self._zoom_factor = 1.0
        self.zoom_changed.emit(self._zoom_factor)

    def fit_in_view(self):
        """適應視窗大小"""
        if self._pixmap_item:
            self.fitInView(self._pixmap_item, Qt.KeepAspectRatio)
            self._zoom_factor = self.transform().m11()
            self.zoom_changed.emit(self._zoom_factor)

    def _apply_zoom(self, factor: float):
        """套用縮放"""
        new_zoom = self._zoom_factor * factor
        if self.ZOOM_MIN <= new_zoom <= self.ZOOM_MAX:
            self.scale(factor, factor)
            self._zoom_factor = new_zoom
            self.zoom_changed.emit(self._zoom_factor)

    @property
    def zoom_factor(self) -> float:
        """取得目前縮放比例"""
        return self._zoom_factor

    # ===== 事件處理 =====

    def wheelEvent(self, event: QWheelEvent):
        """滑鼠滾輪事件（縮放）"""
        if event.angleDelta().y() > 0:
            self.zoom_in()
        else:
            self.zoom_out()

    def mousePressEvent(self, event: QMouseEvent):
        """滑鼠按下事件"""
        # 中鍵或 Space + 左鍵 = 平移
        if event.button() == Qt.MiddleButton:
            self._start_panning(event)
            return

        # 傳遞給工具
        if self._current_tool and event.button() == Qt.LeftButton:
            scene_pos = self.mapToScene(event.position().toPoint())
            self._current_tool.on_mouse_press(event, scene_pos)
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """滑鼠移動事件"""
        # 平移模式
        if self._is_panning and self._last_pan_pos:
            delta = event.position() - self._last_pan_pos
            self._last_pan_pos = event.position()
            self.horizontalScrollBar().setValue(
                int(self.horizontalScrollBar().value() - delta.x())
            )
            self.verticalScrollBar().setValue(
                int(self.verticalScrollBar().value() - delta.y())
            )
            return

        # 傳遞給工具
        if self._current_tool:
            scene_pos = self.mapToScene(event.position().toPoint())
            self._current_tool.on_mouse_move(event, scene_pos)
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """滑鼠釋放事件"""
        # 結束平移
        if event.button() == Qt.MiddleButton:
            self._stop_panning()
            return

        # 傳遞給工具
        if self._current_tool and event.button() == Qt.LeftButton:
            scene_pos = self.mapToScene(event.position().toPoint())
            self._current_tool.on_mouse_release(event, scene_pos)
            return

        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        """鍵盤按下事件"""
        # Space = 進入平移模式
        if event.key() == Qt.Key_Space and not self._is_panning:
            self.setCursor(Qt.OpenHandCursor)

        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent):
        """鍵盤釋放事件"""
        # 結束平移模式
        if event.key() == Qt.Key_Space:
            self.setCursor(Qt.ArrowCursor)

        super().keyReleaseEvent(event)

    def _start_panning(self, event: QMouseEvent):
        """開始平移"""
        self._is_panning = True
        self._last_pan_pos = event.position()
        self.setCursor(Qt.ClosedHandCursor)

    def _stop_panning(self):
        """結束平移"""
        self._is_panning = False
        self._last_pan_pos = None
        self.setCursor(Qt.ArrowCursor)

    def _stop_panning(self):
        """結束平移"""
        self._is_panning = False
        self._last_pan_pos = None
        self.setCursor(Qt.ArrowCursor)

    # ===== 濾鏡功能 =====

    def set_brightness(self, value: int):
        """設定亮度 (-128 ~ 128)"""
        if self._brightness != value:
            self._brightness = value
            self._refresh_display()

    def set_contrast(self, value: int):
        """設定對比 (-128 ~ 128)"""
        if self._contrast != value:
            self._contrast = value
            self._refresh_display()

    def _refresh_display(self):
        """重新整理顯示 (原圖 -> 剪裁 -> 濾鏡 -> 顯示)"""
        if not self._original_pixmap or not self._pixmap_item:
            return

        # 1. 取得基礎剪裁圖片 (無濾鏡)
        crop_rect = (
            self._current_crop_rect
            if self._current_crop_rect
            else QRectF(self._original_pixmap.rect())
        )
        base_pixmap = self._original_pixmap.copy(crop_rect.toRect())

        # 2. 如果正在剪裁模式，直接顯示無濾鏡的原圖
        # 但 start_crop_session 已經處理了顯示邏輯 (設為原圖)，這裡只需處理一般狀態
        # 為了避免衝突，如果 is_in_crop_session，我們應該顯示什麼？
        # start_crop_session 會將 pixmap 設為原圖。
        # 如果在此時呼叫 _refresh_display (例如調整亮度的滑桿還沒被 disable?)，可能會出錯。
        # 假設 UI 會在剪裁時鎖定滑桿，或者我們在這裡判斷
        if self._is_in_crop_session:
            return

        # 3. 套用濾鏡
        filtered_pixmap = self._apply_filters(base_pixmap)

        # 4. 更新顯示
        self._pixmap_item.setPixmap(filtered_pixmap)
        self._scene.setSceneRect(QRectF(filtered_pixmap.rect()))
        self.image_changed.emit()

    def _apply_filters(self, pixmap: QPixmap) -> QPixmap:
        """套用影像處理濾鏡"""
        # print(f"Applying filters: B={self._brightness}, C={self._contrast}, Numpy={HAS_NUMPY}")
        if self._brightness == 0 and self._contrast == 0:
            return pixmap

        if not HAS_NUMPY:
            print("Numpy not available, skipping filters.")
            return pixmap

        try:
            image = pixmap.toImage()
            if image.format() != QImage.Format_ARGB32:
                image = image.convertToFormat(QImage.Format_ARGB32)

            width = image.width()
            height = image.height()

            # 建立 numpy array view/copy
            ptr = image.bits()
            arr = np.array(ptr).reshape(height, width, 4)

            # 如果 arr 是 copy，修改它不會影響 image。
            # 所以我們必須在運算後，用 arr 的資料建立新的 QImage

            # 複製 RGB 通道進行處理
            img_process = arr[:, :, :3].astype(np.float32)

            # 對比 (Contrast)
            if self._contrast != 0:
                f = (259 * (self._contrast + 255)) / (255 * (259 - self._contrast))
                img_process = (img_process - 128) * f + 128

            # 亮度 (Brightness)
            if self._brightness != 0:
                img_process = img_process + self._brightness

            # Clip 0-255
            img_process = np.clip(img_process, 0, 255).astype(np.uint8)

            # 將處理後的數據寫回 arr
            arr[:, :, :3] = img_process

            # 建立新的 QImage
            # 注意: QImage 參考 arr.data，必須確保 arr 在 QPixmap 建立完成前不被回收
            # QPixmap.fromImage 會進行 deep copy
            new_image = QImage(arr.data, width, height, width * 4, QImage.Format_ARGB32)

            return QPixmap.fromImage(new_image)

        except Exception as e:
            print(f"Filter error: {e}")
            import traceback

            traceback.print_exc()
            return pixmap

    # ===== 圖片操作 =====

    def start_crop_session(self) -> QRectF:
        """
        開始剪裁模式：顯示全圖，並偏移標註位置

        Returns:
            目前的剪裁區域 (相對於原圖)
        """
        if not self._original_pixmap:
            return QRectF()

        if self._is_in_crop_session:
            return self._current_crop_rect

        self._is_in_crop_session = True

        self._is_in_crop_session = True

        # 1. 還原顯示原圖 (只更新 Item，不清除 Scene)，且為了剪裁，暫時不套用濾鏡 (顯示 Raw)
        if self._pixmap_item:
            self._pixmap_item.setPixmap(self._original_pixmap)
            self._scene.setSceneRect(QRectF(self._original_pixmap.rect()))

        # 2. 偏移標註：將標註從 "剪裁空間" 移回 "原圖空間"
        # 標註原本在 (x, y)，現在應該在 (x + crop.x, y + crop.y)
        offset = (
            self._current_crop_rect.topLeft()
            if self._current_crop_rect
            else QPointF(0, 0)
        )

        for item in self._scene.items():
            # 排除 pixmap 本身
            if item != self._pixmap_item:
                item.moveBy(offset.x(), offset.y())

        self.fit_in_view()
        return self._current_crop_rect

    def end_crop_session(self, confirm: bool, new_rect: QRectF = None):
        """
        結束剪裁模式：套用剪裁或還原，並反向偏移標註

        Args:
            confirm: 是否確認剪裁
            new_rect: 新的剪裁區域 (僅當 confirm=True 時有效)
        """
        if not self._original_pixmap or not self._is_in_crop_session:
            return

        self._is_in_crop_session = False

        final_rect = self._current_crop_rect
        if confirm and new_rect:
            final_rect = new_rect

        # 更新記錄
        self._current_crop_rect = final_rect.intersected(
            QRectF(self._original_pixmap.rect())
        )

        # 1. 產生剪裁圖
        cropped = self._original_pixmap.copy(self._current_crop_rect.toRect())

        # 2. 更新顯示 (透過 refresh_display 套用濾鏡)
        self._refresh_display()
        # _refresh_display 已經會設定 pixmap 和 scene rect

        # 移除舊的手動設定
        # if self._pixmap_item:
        #     self._pixmap_item.setPixmap(cropped)
        #     self._scene.setSceneRect(QRectF(cropped.rect()))

        # 3. 反向偏移標註：將標註從 "原圖空間" 移回 "剪裁空間"
        # 標註原本在 (x', y')，現在應該在 (x' - final_crop.x, y' - final_crop.y)
        offset = self._current_crop_rect.topLeft()

        for item in self._scene.items():
            if item != self._pixmap_item:
                item.moveBy(-offset.x(), -offset.y())

        self.fit_in_view()
        # self.image_changed.emit() # refresh_display 會 emit

    def crop_image(self, rect: QRectF) -> QPixmap:
        """
        裁切圖片 (舊方法，相容性保留，建議改用 crop session)
        """
        if not self._pixmap_item:
            return QPixmap()

        # ... (可以使用 start/end session 重構，但這裡維持原樣)
        # 為了避免混淆，若使用此方法直接裁切，視為破壞性
        # 我們假設外部只會呼叫 end_crop_session
        return QPixmap()  # Placeholder or Deprecated warning?
        # 為了安全，保留原邏輯但標記 Deprecated
        # 實際上 crop_tool 會調用上面的 session 方法，所以這個舊方法可能不會被用到了
        # 但為了不破壞既有邏輯，暫時不動它下面的實作?
        # 下面原有的實作:

        # 將場景座標轉換為 Item 座標（即圖片像素座標）
        # 使用 mapFromScene 取代直接假設
        polygon = self._pixmap_item.mapFromScene(rect)
        item_rect = polygon.boundingRect().toRect()

        pixmap = self._pixmap_item.pixmap()

        # 確保裁切區域在圖片範圍內
        image_rect = QRectF(pixmap.rect()).toRect()
        crop_rect = item_rect.intersected(image_rect)

        if crop_rect.isEmpty():
            return QPixmap()

        cropped = pixmap.copy(crop_rect)
        return cropped

    def render_to_image(self) -> QImage:
        """
        將場景渲染為圖片（包含所有標註）

        Returns:
            QImage 物件
        """
        if not self._pixmap_item:
            return QImage()

        pixmap = self._pixmap_item.pixmap()
        image = QImage(pixmap.size(), QImage.Format_ARGB32)
        image.fill(Qt.transparent)

        # 暫時隱藏所有選取控制點
        from .tools.rect_tool import AnnotationRect, SelectionHandle
        hidden_items = []
        for item in self._scene.items():
            if isinstance(item, SelectionHandle):
                if item.isVisible():
                    hidden_items.append(item)
                    item.hide()

        painter = QPainter(image)
        self._scene.render(painter)
        painter.end()

        # 恢復控制點的可見性
        for item in hidden_items:
            item.show()

        return image
