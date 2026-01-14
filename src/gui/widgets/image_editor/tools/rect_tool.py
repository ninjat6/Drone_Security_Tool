"""
框選標註工具
"""

import math
from typing import Optional, List, Dict

from PySide6.QtCore import Qt, QPointF, QRectF, Signal, QObject
from PySide6.QtGui import (
    QMouseEvent,
    QPen,
    QColor,
    QBrush,
    QCursor,
    QTransform,
    QPainter,
)
from PySide6.QtWidgets import (
    QGraphicsRectItem,
    QGraphicsItem,
    QGraphicsEllipseItem,
    QGraphicsSceneMouseEvent,
    QStyleOptionGraphicsItem,
    QStyle,
)

from .base_tool import BaseTool
from ..commands.rect_commands import AddAnnotationCommand, TransformAnnotationCommand


class AnnotationSignals(QObject):
    """
    用於在 QGraphicsItem 中使用 Signal
    """

    # (self, old_state, new_state)
    modification_finished = Signal(object, dict, dict)


class SelectionHandle(QGraphicsEllipseItem):
    """
    選取控制點
    """

    SIZE = 10

    def __init__(self, parent, handle_type: str):
        # 預設位置 (0,0)，大小 10x10
        super().__init__(-self.SIZE / 2, -self.SIZE / 2, self.SIZE, self.SIZE, parent)
        self._handle_type = handle_type

        # 樣式 (白色圓點，黑色邊框)
        self.setBrush(QBrush(Qt.white))
        self.setPen(QPen(Qt.black, 1))

        # 互動設定
        self.setCursor(self._get_cursor())
        self.setFlag(
            QGraphicsItem.ItemIsMovable, False
        )  # 不由 Qt 自動移動，我們自己處理
        self.setFlag(
            QGraphicsItem.ItemIgnoresTransformations, True
        )  # 忽略縮放，保持固定大小
        self.setAcceptHoverEvents(True)

    def _get_cursor(self) -> QCursor:
        cursors = {
            "tl": Qt.SizeFDiagCursor,
            "br": Qt.SizeFDiagCursor,
            "tr": Qt.SizeBDiagCursor,
            "bl": Qt.SizeBDiagCursor,
            "t": Qt.SizeVerCursor,
            "b": Qt.SizeVerCursor,
            "l": Qt.SizeHorCursor,
            "r": Qt.SizeHorCursor,
            "rotate": Qt.PointingHandCursor,  # 旋轉游標
        }
        return cursors.get(self._handle_type, Qt.ArrowCursor)

    @property
    def handle_type(self):
        return self._handle_type

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent):
        # print(f"Handle Press: {self._handle_type}")
        # 標記開始互動，並通知 Parent
        self.parentItem().handle_press(self, event.scenePos())
        event.accept()  # 明確接受事件

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent):
        # print(f"Handle Move: {self._handle_type}")
        # 通知 Parent 進行調整
        self.parentItem().handle_move(self, event.scenePos())

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent):
        # print(f"Handle Release: {self._handle_type}")
        self.parentItem().handle_release(self)


class AnnotationRect(QGraphicsRectItem):
    """
    可選取、可旋轉、可縮放的標註矩形
    """

    MIN_SIZE = 10

    def __init__(
        self, rect: QRectF, color: QColor, line_width: int, rotation: float = 0
    ):
        super().__init__(rect)
        self._color = color
        self._line_width = line_width
        # Rotation 透過 setRotation 處理，這裡只是初始參數

        # 設定樣式
        self.setPen(QPen(color, line_width))
        self.setBrush(QBrush(Qt.transparent))

        # 可選取、可移動
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)

        # 控制點
        self._handles: Dict[str, SelectionHandle] = {}
        self._create_handles()
        self._update_handles_visibility()

        # 互動狀態
        self._is_resizing = False
        self._start_rect = QRectF()
        self._start_pos = QPointF()
        self._start_rotation = 0.0

        # 套用初始旋轉
        if rotation != 0:
            self.setTransformOriginPoint(rect.center())
            self.setRotation(rotation)

        # 信號代理
        self.signals = AnnotationSignals()

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget):
        # 覆寫 paint 以去除選取時的虛線框 (Qt 預設行為)
        # 我們希望用 Handles 來表示選取，而不是醜醜的虛線

        # 移除 State_Selected 標記，暫時騙過 drawRect
        # 但這樣會導致 Handles 不顯示? 不，Handles 可見性由我們控制
        # 其實只需要將 option.state 的 Selected bit 去掉
        option.state &= ~QStyle.State.State_Selected
        super().paint(painter, option, widget)

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value):
        if change == QGraphicsItem.ItemSelectedChange:
            # 選取狀態改變，更新 Handles 顯示
            self._update_handles_visibility(selected=bool(value))
        return super().itemChange(change, value)

    def setRect(self, rect: QRectF):
        """覆寫 setRect 以更新控制點位置"""
        super().setRect(rect)
        self._update_handle_positions()

    def _create_handles(self):
        directions = ["tl", "t", "tr", "r", "br", "b", "bl", "l", "rotate"]
        for d in directions:
            handle = SelectionHandle(self, d)
            self._handles[d] = handle

        self._update_handle_positions()

    def _update_handles_visibility(self, selected: bool = False):
        for handle in self._handles.values():
            handle.setVisible(selected)

    def _update_handle_positions(self):
        """更新所有控制點位置"""
        rect = self.rect()
        offset = 0  # 貼齊邊線

        pos_map = {
            "tl": rect.topLeft(),
            "t": QPointF(rect.center().x(), rect.top()),
            "tr": rect.topRight(),
            "r": QPointF(rect.right(), rect.center().y()),
            "br": rect.bottomRight(),
            "b": QPointF(rect.center().x(), rect.bottom()),
            "bl": rect.bottomLeft(),
            "l": QPointF(rect.left(), rect.center().y()),
            "rotate": QPointF(rect.center().x(), rect.top() - 30),  # 上方 30px
        }

        for name, handle in self._handles.items():
            if name in pos_map:
                handle.setPos(pos_map[name])

        # 更新旋轉中心 (保持在中心)
        self.setTransformOriginPoint(rect.center())

    # ===== Handle callbacks =====

    def handle_press(self, handle: SelectionHandle, scene_pos: QPointF):
        self._is_resizing = True
        self.setFlag(QGraphicsItem.ItemIsMovable, False)  # 暫停移動，避免衝突
        self._start_rect = self.rect()
        # 記錄 Local 座標的點 (更方便計算 Resize)
        self._start_pos = self.mapFromScene(scene_pos)
        self._start_scene_pos = scene_pos
        self._start_rotation = self.rotation()

        # 記錄完整初始狀態 (用於 Undo)
        self._start_state = self.get_data()

    def handle_move(self, handle: SelectionHandle, scene_pos: QPointF):
        if not self._is_resizing:
            return

        h_type = handle.handle_type

        # 旋轉處理
        if h_type == "rotate":
            center = self.mapToScene(self.rect().center())
            delta = scene_pos - center
            angle = math.degrees(math.atan2(delta.y(), delta.x())) + 90

            # --- 吸附邏輯 (Snapping) ---
            # 當角度接近 45, 90, 135... 時自動吸附
            SNAP_INTERVAL = 45
            SNAP_THRESHOLD = 5

            nearest_multiple = round(angle / SNAP_INTERVAL) * SNAP_INTERVAL
            if abs(angle - nearest_multiple) < SNAP_THRESHOLD:
                angle = nearest_multiple

            self.setRotation(angle)
            return

        # --- 縮放處理 (錨點補償) ---

        # 1. 決定固定錨點 (Anchor) - 在 Local 座標系中的相對位置 (0~1)
        # 例如：拖曳左上(TL)，固定點為右下(BR) -> (1, 1)
        anchor_map = {
            "tl": (1, 1),
            "t": (0.5, 1),
            "tr": (0, 1),
            "l": (1, 0.5),
            "r": (0, 0.5),
            "bl": (1, 0),
            "b": (0.5, 0),
            "br": (0, 0),
        }
        ax, ay = anchor_map.get(h_type, (0.5, 0.5))

        curr_rect = self.rect()
        anchor_local = QPointF(
            curr_rect.x() + curr_rect.width() * ax,
            curr_rect.y() + curr_rect.height() * ay,
        )
        anchor_scene = self.mapToScene(anchor_local)

        # 2. 計算新矩形
        local_pos = self.mapFromScene(scene_pos)
        l, t, w, h = curr_rect.x(), curr_rect.y(), curr_rect.width(), curr_rect.height()
        r_right, r_bottom = l + w, t + h

        new_l, new_t, new_r, new_b = l, t, r_right, r_bottom

        if "l" in h_type:
            new_l = min(local_pos.x(), r_right - self.MIN_SIZE)
        if "r" in h_type:
            new_r = max(local_pos.x(), l + self.MIN_SIZE)
        if "t" in h_type:
            new_t = min(local_pos.y(), r_bottom - self.MIN_SIZE)
        if "b" in h_type:
            new_b = max(local_pos.y(), t + self.MIN_SIZE)

        new_rect = QRectF(QPointF(new_l, new_t), QPointF(new_r, new_b))
        self.setRect(new_rect)

        # 3. 更新旋轉中心與控制點
        # 注意：這會改變 coordinate system mapping
        self._update_handle_positions()

        # 4. 位移補償
        # 計算新的 anchor 在哪裡 (基於同樣的相對比例)
        new_anchor_local = QPointF(
            new_rect.x() + new_rect.width() * ax, new_rect.y() + new_rect.height() * ay
        )
        new_anchor_scene = self.mapToScene(new_anchor_local)

        # 移動 Item 以讓 Anchor 回到原本的 Scene 位置
        delta = anchor_scene - new_anchor_scene
        self.moveBy(delta.x(), delta.y())

    # Signal: (self, old_state, new_state)
    # modification_finished = Signal(object, dict, dict) # Removed: use self.signals proxy

    def handle_release(self, handle: SelectionHandle):
        self._is_resizing = False
        self.setFlag(QGraphicsItem.ItemIsMovable, True)

        # 檢查是否有變更
        new_state = self.get_data()

        # 簡單比較 (如果不一樣則發送信號)
        # 比較 rect, rotation, pos
        changed = False

        # 比較 Rect
        current_rect = self.rect()
        if (
            abs(current_rect.x() - self._start_rect.x()) > 0.1
            or abs(current_rect.y() - self._start_rect.y()) > 0.1
            or abs(current_rect.width() - self._start_rect.width()) > 0.1
            or abs(current_rect.height() - self._start_rect.height()) > 0.1
        ):
            changed = True

        # 比較 Rotation
        if abs(self.rotation() - self._start_rotation) > 0.1:
            changed = True

        # 比較 Pos (start_pos 是 Local, 但我們應該比較 Scene Pos?
        # get_data 返回的是 Scene Pos)
        # 不過 handle_press 沒有記錄初始的 Scene Pos 完整的狀態
        # 為了簡化，我們在 handle_press 應該記錄完整的 state dict

        # 修正: 在 handle_press 記錄完整 state
        if hasattr(self, "_start_state") and self._start_state:
            # 比較各個數值
            for k in ["rect", "rotation", "pos"]:
                if self._start_state[k] != new_state[k]:
                    changed = True
                    break

        if changed and hasattr(self, "_start_state"):
            self.signals.modification_finished.emit(self, self._start_state, new_state)

    # ===== Properties =====

    @property
    def annotation_color(self) -> QColor:
        return self._color

    @annotation_color.setter
    def annotation_color(self, color: QColor):
        self._color = color
        self.setPen(QPen(color, self._line_width))

    @property
    def line_width(self) -> int:
        return self._line_width

    @line_width.setter
    def line_width(self, width: int):
        self._line_width = width
        self.setPen(QPen(self._color, width))

    def get_data(self) -> dict:
        """取得標註資料"""
        return {
            "rect": [
                self.rect().x(),
                self.rect().y(),
                self.rect().width(),
                self.rect().height(),
            ],
            "color": self._color.name(),
            "line_width": self._line_width,
            "rotation": self.rotation(),
            "pos": [self.pos().x(), self.pos().y()],
        }


class RectTool(BaseTool):
    """
    框選標註工具
    """

    def __init__(
        self,
        canvas,
        command_history=None,
        color: QColor = None,
        line_width: int = 3,
        rotation: float = 0,
    ):
        super().__init__(canvas)
        self._command_history = command_history
        self._color = color or QColor(255, 0, 0)
        self._line_width = line_width
        self._rotation = rotation

        self._current_rect: Optional[AnnotationRect] = None
        self._annotations: List[AnnotationRect] = []

    def on_activate(self):
        self._canvas.setCursor(Qt.CrossCursor)

    def on_deactivate(self):
        self._canvas.setCursor(Qt.ArrowCursor)
        self._current_rect = None

    def set_color(self, color: QColor):
        self._color = color
        # 更新選取項目
        self.update_selected(color=color)

    def set_line_width(self, width: int):
        self._line_width = width
        self.update_selected(width=width)

    def set_rotation(self, rotation: float):
        self._rotation = rotation
        # 更新選取項目 (注意：這會強制覆蓋個別旋轉)
        self.update_selected(rotation=rotation)

    def update_selected(self, color=None, width=None, rotation=None):
        """更新場景中所有選取的 AnnotationRect"""
        for item in self.scene.selectedItems():
            if isinstance(item, AnnotationRect):
                if color is not None:
                    item.annotation_color = color
                if width is not None:
                    item.line_width = width
                if rotation is not None:
                    item.setRotation(rotation)

    def on_mouse_press(self, event: QMouseEvent, scene_pos: QPointF):
        """開始繪製"""
        self._start_pos = scene_pos

        rect = QRectF(scene_pos, scene_pos)
        self._current_rect = AnnotationRect(
            rect, self._color, self._line_width, self._rotation
        )

        # 連接變形信號
        self._current_rect.signals.modification_finished.connect(
            self._on_annotation_modified
        )

        self.scene.addItem(self._current_rect)
        self._is_active = True

    def on_mouse_move(self, event: QMouseEvent, scene_pos: QPointF):
        """更新矩形大小"""
        if not self._is_active or not self._current_rect or not self._start_pos:
            return

        rect = QRectF(self._start_pos, scene_pos).normalized()
        self._current_rect.setRect(rect)
        # 繪製過程中，暫時不需要 Handles
        self._current_rect.setSelected(False)
        # (但實際上新建立的 Item 預設不會 Selected，除非 setSelected(True))

    def on_mouse_release(self, event: QMouseEvent, scene_pos: QPointF):
        """完成繪製"""
        self._is_active = False

        if self._current_rect:
            rect = self._current_rect.rect()
            if rect.width() > 5 and rect.height() > 5:
                # 有效矩形
                if self._command_history:
                    # 使用 Command 處理 (支援撤銷)
                    cmd = AddAnnotationCommand(
                        self.scene, self._current_rect, self._annotations
                    )
                    # CommandHistory.execute 會呼叫 cmd.execute()
                    self._command_history.execute(cmd)
                else:
                    # Fallback (如果要支援無 History 模式)
                    self._annotations.append(self._current_rect)

                # 自動選取剛畫好的 (這樣就可以直接編輯)
                self._current_rect.setSelected(True)

                # 發送完成信號 (切換回 Select 模式)
                self.drawing_finished.emit()
            else:
                self.scene.removeItem(self._current_rect)

        self._current_rect = None
        self._start_pos = None

    def get_annotations(self) -> List[AnnotationRect]:
        return self._annotations.copy()

    def remove_selected(self):
        """移除選取的標註"""
        # 注意：使用 list() 複製，因為會在迴圈中 modify
        for item in list(self.scene.selectedItems()):
            if isinstance(item, AnnotationRect) and item in self._annotations:
                self._annotations.remove(item)
                self.scene.removeItem(item)

    def clear_all(self):
        for item in self._annotations:
            self.scene.removeItem(item)
        self._annotations.clear()

    def _on_annotation_modified(self, annotation, old_state, new_state):
        """標註變形完成 (Callback)"""
        if self._command_history:
            cmd = TransformAnnotationCommand(annotation, old_state, new_state)
            self._command_history.execute(cmd)

    def get_all_data(self) -> List[dict]:
        return [ann.get_data() for ann in self._annotations]
