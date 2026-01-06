"""
測試頁面模組
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QCheckBox,
    QStackedWidget,
    QTabWidget,
    QMessageBox,
)

from constants import TARGET_UAV

from test_tools.factory import ToolFactory


class UniversalTestPage(QWidget):
    """
    通用測試頁面 - 一個測項的完整頁面
    負責管理 Tab 分頁 (UAV/GCS)
    """

    def __init__(self, config, pm):
        super().__init__()
        self.config = config
        self.pm = pm
        self.targets = config.get("targets", [TARGET_UAV])
        self.allow_share = config.get("allow_share", False)
        self.tools = []  # 防止 Tool 被 Garbage Collection 回收
        self._init_ui()
        self._load_state()

    def _init_ui(self):
        # self.resize(1200, 1200)
        layout = QVBoxLayout(self)
        h = QHBoxLayout()
        h.addWidget(QLabel(f"<h2>{self.config['name']}</h2>"))
        layout.addLayout(h)

        self.chk = None
        if len(self.targets) > 1:
            self.chk = QCheckBox("共用結果")
            self.chk.setStyleSheet("color: blue; font-weight: bold;")
            self.chk.toggled.connect(self.on_share)
            h.addStretch()
            h.addWidget(self.chk)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        self.p_sep = QWidget()
        v = QVBoxLayout(self.p_sep)
        v.setContentsMargins(0, 0, 0, 0)

        if len(self.targets) > 1:
            tabs = QTabWidget()
            for t in self.targets:
                tabs.addTab(self._create_tool_widget(t), t)
            v.addWidget(tabs)
        else:
            v.addWidget(self._create_tool_widget(self.targets[0]))

        self.stack.addWidget(self.p_sep)

        if len(self.targets) > 1:
            self.p_share = self._create_tool_widget(
                "Shared", is_shared=True, save_cb=self.save_share
            )
            self.stack.addWidget(self.p_share)

    def _create_tool_widget(self, target, is_shared=False, save_cb=None):
        """建立測項 Widget"""
        uid = self.config.get("uid", self.config.get("id"))

        # 取得已存資料
        if save_cb:  # Shared mode usually passes save_cb
            # For shared, we might just load from one target or a specific shared record?
            # Logic in original SingleTargetTestWidget for shared: "Shared" as target
            data = self.pm.get_test_result(uid, target, is_shared=is_shared)
        else:
            data = self.pm.get_test_result(uid, target, is_shared=False)

        # 優先從 handler.class_name 讀取，相容舊版 tool_class
        handler = self.config.get("handler", {})
        class_name = handler.get("class_name")
        if not class_name:
            class_name = self.config.get("tool_class", "BaseTestTool")

        tool = ToolFactory.create_tool(
            class_name,
            self.config,
            data,
            target,
            project_manager=self.pm,
            save_callback=save_cb,
        )
        self.tools.append(tool)
        return tool.get_widget()

    def _load_state(self):
        uid = self.config.get("uid", self.config.get("id"))
        meta = self.pm.get_test_meta(uid)
        if self.chk and meta.get("is_shared"):
            self.chk.setChecked(True)
            self.stack.setCurrentWidget(self.p_share)

    def on_share(self, checked):
        self.stack.setCurrentWidget(self.p_share if checked else self.p_sep)

    def save_share(self, data):
        uid = self.config.get("uid", self.config.get("id"))
        for t in self.targets:
            self.pm.update_test_result(uid, t, data, is_shared=True)
        QMessageBox.information(self, "成功", "共用儲存完成")
