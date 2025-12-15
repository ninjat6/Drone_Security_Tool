from PySide6.QtWidgets import QWidget, QPushButton, QTextEdit, QLineEdit
from PySide6.QtCore import QObject
# from src.core.cmd_runner import CommandRunner

class Page621Controller(QObject):
    def __init__(self, widget: QWidget):
        super().__init__()
        self.widget = widget
        
        # 1. 綁定 UI 元件 (請確保 widget_621.ui 裡的 objectName 是這些)
        self.btn_run = self.widget.findChild(QPushButton, "btn_run")
        self.text_log = self.widget.findChild(QTextEdit, "text_log")
        self.input_target = self.widget.findChild(QLineEdit, "input_target") # 假設有個輸入框

        # 2. 初始化核心邏輯
        # self.runner = CommandRunner()

        # 3. 連接事件
        self.setup_connections()

    def setup_connections(self):
        if self.btn_run:
            self.btn_run.clicked.connect(self.handle_run_click)
        
        # 核心邏輯傳回來的文字 -> 更新到 UI
        # self.runner.output_received.connect(self.append_log)

    def handle_run_click(self):
        """按鈕按下時的邏輯"""
        # 1. 清空 Log
        if self.text_log:
            self.text_log.clear()

        # 2. 獲取輸入參數
        target_ip = "127.0.0.1" # 預設值
        if self.input_target:
            target_ip = self.input_target.text()

        # 3. 呼叫核心執行指令 (範例：ping)
        # 這裡將邏輯完全交給 runner，介面不會卡死
        self.runner.run("ping", ["-c", "4", target_ip])

    def append_log(self, text):
        """更新文字框"""
        if self.text_log:
            self.text_log.insertPlainText(text)
            self.text_log.ensureCursorVisible() # 自動捲動到底部