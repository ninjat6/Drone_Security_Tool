# from PySide6.QtWidgets import QApplication
# import sys

# from gui.views.main_window import MainWindow


# def run():
#     app = QApplication(sys.argv)
#     window = MainWindow()
#     window.window.show()
#     sys.exit(app.exec())


# if __name__ == "__main__":
#     run()




import sys
from PySide6.QtWidgets import QApplication
from gui.views.controllers.main_controller import MainController

def main():
    app = QApplication(sys.argv)
    
    try:
        # 實例化主控制器
        controller = MainController()
        controller.show()
        
        sys.exit(app.exec())
    except Exception as e:
        print(f"程式啟動失敗: {e}")

if __name__ == "__main__":
    main()