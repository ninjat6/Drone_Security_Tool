from PySide6.QtWidgets import QApplication
import sys

from gui.views.main_window import MainWindow


def run():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run()


