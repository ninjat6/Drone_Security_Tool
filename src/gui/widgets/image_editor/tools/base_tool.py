"""
工具基類
使用 Strategy Pattern 設計，所有工具繼承此類
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import QObject, Signal, QPointF
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QGraphicsScene

if TYPE_CHECKING:
    from ..canvas import ImageCanvas


class BaseTool(QObject):
    """
    工具基類

    所有繪圖工具必須繼承此類並實作滑鼠事件處理方法。
    這是一個 Strategy Pattern 的實現。
    """

    # 繪圖完成信號（用於切換回選擇模式）
    drawing_finished = Signal()

    def __init__(self, canvas: "ImageCanvas"):
        """
        初始化工具

        Args:
            canvas: 圖片畫布實例
        """
        super().__init__()
        self._canvas = canvas
        self._is_active = False
        self._start_pos: Optional[QPointF] = None

    @property
    def canvas(self) -> "ImageCanvas":
        """取得畫布實例"""
        return self._canvas

    @property
    def scene(self) -> QGraphicsScene:
        """取得場景實例"""
        return self._canvas.scene()

    @property
    def is_active(self) -> bool:
        """工具是否正在使用中"""
        return self._is_active

    def activate(self):
        """啟用工具"""
        self._is_active = True
        self.on_activate()

    def deactivate(self):
        """停用工具"""
        self._is_active = False
        self._start_pos = None
        self.on_deactivate()

    def on_activate(self):
        """啟用時的額外處理（子類可覆寫）"""
        pass

    def on_deactivate(self):
        """停用時的額外處理（子類可覆寫）"""
        pass

    @abstractmethod
    def on_mouse_press(self, event: QMouseEvent, scene_pos: QPointF):
        """
        滑鼠按下事件

        Args:
            event: 滑鼠事件
            scene_pos: 場景座標
        """
        pass

    @abstractmethod
    def on_mouse_move(self, event: QMouseEvent, scene_pos: QPointF):
        """
        滑鼠移動事件

        Args:
            event: 滑鼠事件
            scene_pos: 場景座標
        """
        pass

    @abstractmethod
    def on_mouse_release(self, event: QMouseEvent, scene_pos: QPointF):
        """
        滑鼠釋放事件

        Args:
            event: 滑鼠事件
            scene_pos: 場景座標
        """
        pass

    def get_name(self) -> str:
        """取得工具名稱"""
        return self.__class__.__name__
