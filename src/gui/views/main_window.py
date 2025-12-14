from pathlib import Path

from PySide6.QtUiTools import QUiLoader  # 修正匯入
from PySide6.QtCore import QFile, QObject, Qt
from PySide6.QtCore import QFile


class MainWindow(QObject):

    def __init__(self):
        super().__init__()

        ui_path = Path(__file__).parent / "uav_gui.ui"
        ui_file = QFile(str(ui_path))
        if not ui_file.open(QFile.ReadOnly):
            raise FileNotFoundError(f"找不到 UI 檔：{ui_path}")
        
        loader = QUiLoader()
        self.window = loader.load(ui_file)
        ui_file.close()

        if self.window is None:
            raise RuntimeError("UI 載入失敗（loader.load 回傳 None）。")
        





    