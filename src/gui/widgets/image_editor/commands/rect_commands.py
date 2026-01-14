from PySide6.QtWidgets import QGraphicsScene
from PySide6.QtCore import QRectF, QPointF
from .base_command import BaseCommand


class AddAnnotationCommand(BaseCommand):
    """新增標註命令"""

    def __init__(self, scene: QGraphicsScene, annotation, annotation_list: list):
        super().__init__()
        self._scene = scene
        self._annotation = annotation
        self._list = annotation_list

    def execute(self):
        if self._annotation not in self._scene.items():
            self._scene.addItem(self._annotation)
        if self._annotation not in self._list:
            self._list.append(self._annotation)
        return True

    def undo(self):
        if self._annotation in self._scene.items():
            self._scene.removeItem(self._annotation)
        if self._annotation in self._list:
            self._list.remove(self._annotation)
        return True


class TransformAnnotationCommand(BaseCommand):
    """標註變形命令 (縮放/旋轉)"""

    def __init__(self, annotation, old_state: dict, new_state: dict):
        super().__init__()
        self._annotation = annotation
        self._old_state = old_state
        self._new_state = new_state

    def execute(self):
        self._apply_state(self._new_state)
        return True

    def undo(self):
        self._apply_state(self._old_state)
        return True

    def _apply_state(self, state: dict):
        self._annotation.setRect(QRectF(*state["rect"]))
        self._annotation.setRotation(state["rotation"])
        self._annotation.setPos(QPointF(*state["pos"]))
        # 更新控制點位置 (通常 setRect 會觸發，但 setPos 不會)
        if hasattr(self._annotation, "_update_handle_positions"):
            self._annotation._update_handle_positions()
