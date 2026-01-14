"""
命令歷史管理器
管理撤銷/重做堆疊
"""

from typing import List, Optional

from PySide6.QtCore import QObject, Signal

from .base_command import BaseCommand


class CommandHistory(QObject):
    """
    命令歷史管理器

    管理撤銷/重做堆疊，並發送狀態變更信號。
    """

    # 信號
    history_changed = Signal()  # 歷史紀錄變更
    can_undo_changed = Signal(bool)  # 可撤銷狀態變更
    can_redo_changed = Signal(bool)  # 可重做狀態變更

    def __init__(self, max_history: int = 50, parent: Optional[QObject] = None):
        """
        初始化命令歷史

        Args:
            max_history: 最大歷史紀錄數量
            parent: 父物件
        """
        super().__init__(parent)
        self._max_history = max_history
        self._undo_stack: List[BaseCommand] = []
        self._redo_stack: List[BaseCommand] = []

    @property
    def can_undo(self) -> bool:
        """是否可撤銷"""
        return len(self._undo_stack) > 0

    @property
    def can_redo(self) -> bool:
        """是否可重做"""
        return len(self._redo_stack) > 0

    def execute(self, command: BaseCommand) -> bool:
        """
        執行命令並加入歷史

        Args:
            command: 要執行的命令

        Returns:
            是否執行成功
        """
        if command.execute():
            self._undo_stack.append(command)
            self._redo_stack.clear()  # 執行新命令時清空重做堆疊

            # 限制歷史紀錄數量
            while len(self._undo_stack) > self._max_history:
                self._undo_stack.pop(0)

            self._emit_changes()
            return True
        return False

    def undo(self) -> bool:
        """
        撤銷上一個命令

        Returns:
            是否撤銷成功
        """
        if not self.can_undo:
            return False

        command = self._undo_stack.pop()
        if command.undo():
            self._redo_stack.append(command)
            self._emit_changes()
            return True
        else:
            # 撤銷失敗，放回堆疊
            self._undo_stack.append(command)
            return False

    def redo(self) -> bool:
        """
        重做下一個命令

        Returns:
            是否重做成功
        """
        if not self.can_redo:
            return False

        command = self._redo_stack.pop()
        if command.redo():
            self._undo_stack.append(command)
            self._emit_changes()
            return True
        else:
            # 重做失敗，放回堆疊
            self._redo_stack.append(command)
            return False

    def clear(self):
        """清空歷史紀錄"""
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._emit_changes()

    def get_undo_description(self) -> str:
        """取得撤銷命令的描述"""
        if self.can_undo:
            return self._undo_stack[-1].description
        return ""

    def get_redo_description(self) -> str:
        """取得重做命令的描述"""
        if self.can_redo:
            return self._redo_stack[-1].description
        return ""

    def _emit_changes(self):
        """發送狀態變更信號"""
        self.history_changed.emit()
        self.can_undo_changed.emit(self.can_undo)
        self.can_redo_changed.emit(self.can_redo)
