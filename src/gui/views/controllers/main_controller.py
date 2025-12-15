from pathlib import Path
from PySide6.QtWidgets import QStackedWidget, QPushButton, QWidget
from PySide6.QtCore import QFile, QObject
from PySide6.QtUiTools import QUiLoader

# 匯入子頁面的 Controller
from gui.views.controllers.page_621_controller import Page621Controller

class MainController(QObject):
    def __init__(self):
        super().__init__()
        
        # 設定路徑 (這會指向 src/gui/views)
        # __file__ 是 controllers 資料夾，parent 是 gui，再進 views
        print(Path(__file__).parent.parent)
        self.views_path = Path(__file__).parent.parent
        
        # 1. 載入主視窗 UI
        self.window = self.load_ui("mainGUI.ui")
        if not self.window:
            raise RuntimeError("無法載入 mainGUI.ui")

        # 2. 綁定主視窗元件
        self.stacked_widget = self.window.findChild(QStackedWidget, "stackedWidget")
        self.btn_621 = self.window.findChild(QPushButton, "btn_621")
        
        if not self.stacked_widget or not self.btn_621:
            print("警告：主視窗找不到 stackedWidget 或 btn_621，請檢查 UI 檔 ObjectName")

        # 3. 初始化儲存空間
        self.controllers = {}   # 用來存活著的 controller
        self.loaded_pages = {}  # 用來存已經載入的 widget (懶加載用)

        # 4. 連接主選單按鈕
        if self.btn_621:
            self.btn_621.clicked.connect(self.switch_to_621)

    def load_ui(self, filename):
        """通用的 UI 載入器"""
        ui_file_path = self.views_path / filename
        ui_file = QFile(str(ui_file_path))
        
        if not ui_file.open(QFile.ReadOnly):
            print(f"錯誤：找不到檔案 {ui_file_path}")
            return None
            
        loader = QUiLoader()
        widget = loader.load(ui_file)
        ui_file.close()
        return widget

    def switch_to_621(self):
        """切換到 6.2.1 頁面 (懶加載模式)"""
        page_id = "621"

        # 如果已經載入過，直接切換，不重新讀檔
        if page_id in self.loaded_pages:
            self.stacked_widget.setCurrentWidget(self.loaded_pages[page_id])
            print("切換至已快取的 6.2.1 頁面")
            return

        print("正在首次載入 6.2.1...")
        # 1. 載入子 UI
        widget = self.load_ui("widget_621.ui")
        if not widget:
            return

        # 2. 建立專屬 Controller (這時候才把 widget 交給它管)
        controller = Page621Controller(widget)
        
        # 3. 重要！存入字典防止被垃圾回收 (Garbage Collection)
        self.controllers[page_id] = controller
        self.loaded_pages[page_id] = widget

        # 4. 放入介面並顯示
        self.stacked_widget.addWidget(widget)
        self.stacked_widget.setCurrentWidget(widget)

    def show(self):
        """顯示主視窗"""
        self.window.show()