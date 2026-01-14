"""
命令基類
使用 Command Pattern 設計，支援撤銷/重做
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseCommand(ABC):
    """
    命令基類

    所有可撤銷的操作必須繼承此類並實作 execute 和 undo 方法。
    這是一個 Command Pattern 的實現。
    """

    def __init__(self, description: str = ""):
        """
        初始化命令

        Args:
            description: 命令描述（用於顯示在撤銷/重做選單）
        """
        self._description = description
        self._executed = False

    @property
    def description(self) -> str:
        """取得命令描述"""
        return self._description

    @property
    def is_executed(self) -> bool:
        """命令是否已執行"""
        return self._executed

    @abstractmethod
    def execute(self) -> bool:
        """
        執行命令

        Returns:
            是否執行成功
        """
        pass

    @abstractmethod
    def undo(self) -> bool:
        """
        撤銷命令

        Returns:
            是否撤銷成功
        """
        pass

    def redo(self) -> bool:
        """
        重做命令（預設與 execute 相同）

        Returns:
            是否重做成功
        """
        return self.execute()
