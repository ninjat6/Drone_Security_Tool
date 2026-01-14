"""
圖片編輯器獨立測試腳本
"""

import sys
import os

# 確保可以匯入 src 模組
current_dir = os.path.dirname(os.path.abspath(__file__))
# 確保可以匯入 src 模組
current_dir = os.path.dirname(os.path.abspath(__file__))
# Current: .../src/gui/widgets/image_editor
# Root dir (UAV_Security_Tool) - Up 4 levels: widgets -> gui -> src -> UAV_Security_Tool
root_dir = os.path.abspath(os.path.join(current_dir, "../../../../"))
# gui dir (UAV_Security_Tool/src/gui)
gui_dir = os.path.join(root_dir, "src", "gui")

if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
if gui_dir not in sys.path:
    # 插入到最前面，確保優先讀取
    sys.path.insert(0, gui_dir)

print(f"Added paths: {root_dir}, {gui_dir}")

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QPixmap, QColor, QPainter
from src.gui.widgets.image_editor.editor_dialog import ImageEditorDialog


def create_dummy_image(path):
    """建立一個測試用的圖片"""
    pixmap = QPixmap(800, 600)
    pixmap.fill(QColor("white"))

    painter = QPainter(pixmap)
    painter.setPen(QColor("red"))
    painter.drawRect(50, 50, 200, 200)
    painter.setPen(QColor("blue"))
    painter.drawText(100, 100, "Test Image")
    painter.end()

    pixmap.save(path)
    return path


def main():
    app = QApplication(sys.argv)

    # 建立暫存圖片
    image_path = "C:\\Users\\user\\Pictures\\pig.png"
    output_path = "C:\\Users\\user\\Pictures\\pig_edit.png"
    # create_dummy_image(image_path)
    print(f"Test image path: {os.path.abspath(image_path)}")
    print(f"Output path: {os.path.abspath(output_path)}")

    try:
        # 開啟編輯器
        dialog = ImageEditorDialog(image_path, output_path=output_path)
        print("Opening Image Editor...")

        if dialog.exec():
            print("Image saved successfully!")
            print(f"Saved image path: {output_path}")
        else:
            print("Edit cancelled.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # 清理 (不刪除使用者的 pig.png)
        # if os.path.exists(image_path):
        #     try:
        #         os.remove(image_path)
        #         print("Cleaned up test image.")
        #     except:
        #         pass
        if os.path.exists(output_path):
            print(f"Generated file exists at: {output_path}")


if __name__ == "__main__":
    main()
