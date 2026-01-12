"""
測項工具工廠模組
"""

from .base import BaseTestTool
from .command import CommandTestTool
from .nmap import NmapTestTool


class ToolFactory:
    """工廠類別 - 根據設定建立對應的 Tool"""

    # 註冊的 Tool 類別
    _registry = {
        "BaseTestTool": BaseTestTool,
        "CommandTestTool": CommandTestTool,
        "NmapTestTool": NmapTestTool,
    }

    @classmethod
    def register(cls, name: str, tool_class):
        """註冊新的 Tool 類別"""
        cls._registry[name] = tool_class

    @staticmethod
    def create_tool(
        class_name: str,
        config,
        result_data,
        target,
        project_manager=None,
        save_callback=None,
        is_shared=False,
    ) -> BaseTestTool:
        """建立 Tool 實例"""
        tool_class = ToolFactory._registry.get(class_name, BaseTestTool)
        return tool_class(config, result_data, target, project_manager, save_callback, is_shared)
