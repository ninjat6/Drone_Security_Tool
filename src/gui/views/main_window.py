from pathlib import Path

from PySide6.QtUiTools import QUiLoader  # 修正匯入
from PySide6.QtCore import QFile, QObject, Qt
from PySide6.QtWidgets import QPushButton, QStackedWidget, QMessageBox, QWidget


class MainWindow(QObject):

    def __init__(self):
        super().__init__()

        self.base_path = Path(__file__).parent
        ui_path = self.base_path / "mainGUI.ui"
        ui_file = QFile(str(ui_path))
        if not ui_file.open(QFile.ReadOnly):
            raise FileNotFoundError(f"找不到 UI 檔：{ui_path}")
        
        loader = QUiLoader()
        self.window = loader.load(ui_file)
        ui_file.close()

        if self.window is None:
            raise RuntimeError("UI 載入失敗（loader.load 回傳 None）。")
        
        # --- 2. 獲取 UI 上的元件 (使用 findChild) ---
        # 因為是動態載入，不能直接寫 self.window.btn_621，要用找的
        self.btn_621 = self.window.findChild(QPushButton, "btn_621")
        self.stackedWidget = self.window.findChild(QStackedWidget, "stackedWidget") # 請確認 Designer 裡的名稱

        # 檢查是否都有找到
        if not self.btn_621:
            print("錯誤: 找不到按鈕 'btn_621'")
        if not self.stackedWidget:
            print("錯誤: 找不到堆疊視窗 'stackedWidget'，請確認 Designer 裡的 ObjectName")

        # --- 3. 連接信號 ---
        if self.btn_621 and self.stackedWidget:
            self.btn_621.clicked.connect(self.load_621_widget)
            
        # 用來暫存已經載入過的頁面，避免重複讀取檔案
        self.loaded_pages = {} 

    def load_ui(self, path):
        """通用的 UI 載入函式"""
        ui_file = QFile(str(path))
        if not ui_file.open(QFile.ReadOnly):
            print(f"無法開啟檔案: {path}")
            return None
        loader = QUiLoader()
        widget = loader.load(ui_file)
        ui_file.close()
        return widget

    def load_621_widget(self):
        """按下按鈕後的邏輯"""
        print("正在載入 6.2.1 頁面...")
        
        # 1. 檢查是否已經載入過 (懶加載)
        if "621" in self.loaded_pages:
            widget = self.loaded_pages["621"]
            self.stackedWidget.setCurrentWidget(widget)
            print("切換到已存在的頁面")
            return

        # 2. 如果沒載入過，讀取新的 .ui 檔
        widget_path = self.base_path / "widget_621.ui" # 假設您的測試 UI 檔名
        new_widget = self.load_ui(widget_path)
        
        if new_widget:
            # 3. 加入 StackedWidget 並顯示
            self.stackedWidget.addWidget(new_widget)
            self.stackedWidget.setCurrentWidget(new_widget)
            
            # 4. 存入字典，下次不用重讀
            self.loaded_pages["621"] = new_widget
            print("頁面載入並顯示成功")
        else:
            print("錯誤: widget_621.ui 載入失敗")
    