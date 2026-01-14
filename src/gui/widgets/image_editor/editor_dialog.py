"""
圖片編輯器對話框
主要介面，包含工具列、畫布、設定面板
"""

import os
from typing import Optional

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPixmap, QColor, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QToolBar,
    QToolButton,
    QWidget,
    QLabel,
    QSlider,
    QSpinBox,
    QPushButton,
    QColorDialog,
    QGroupBox,
    QMessageBox,
    QSplitter,
    QSplitter,
    QFrame,
    QGraphicsDropShadowEffect,
)

from .canvas import ImageCanvas
from .commands import CommandHistory
from .tools.crop_tool import CropTool
from .tools.rect_tool import RectTool, AnnotationRect


class ImageEditorDialog(QDialog):
    """
    圖片編輯器對話框

    提供剪裁、框選標註、亮度/對比調整功能。
    """

    # 信號
    image_saved = Signal(str)  # 圖片儲存完成，傳回路徑

    def __init__(
        self,
        image_path: str,
        output_path: str = None,
        parent=None,
        project_manager=None,
    ):
        """
        初始化編輯器

        Args:
            image_path: 圖片路徑
            output_path: 輸出路徑 (若未指定則覆蓋原檔)
            parent: 父視窗
            project_manager: 專案管理器（用於備份原圖）
        """
        super().__init__(parent)

        self._image_path = image_path
        self._output_path = output_path
        self._pm = project_manager

        # 命令歷史
        self._history = CommandHistory(parent=self)

        # 當前選擇的顏色和線寬
        self._current_color = QColor(255, 0, 0)  # 預設紅色
        self._current_line_width = 3
        self._current_rotation = 0

        # 工具實例
        self._crop_tool = None
        self._rect_tool = None

        # 濾鏡防抖計時器
        self._filter_timer = QTimer(self)
        self._filter_timer.setSingleShot(True)
        self._filter_timer.setInterval(100)  # 100ms 延遲
        self._filter_timer.timeout.connect(self._apply_filter_values)

        # 設定對話框
        self._setup_dialog()
        self._setup_ui()

        self._create_crop_actions_bar()
        self._create_annotation_actions_bar()  # 新增
        self._setup_shortcuts()
        self._connect_signals()

        # 初始化工具 (需在 UI 建立後，因為需要 Canvas)
        self._crop_tool = CropTool(self._canvas)
        self._rect_tool = RectTool(
            self._canvas,
            command_history=self._history,
            color=self._current_color,
            line_width=self._current_line_width,
            rotation=self._current_rotation,
        )
        self._rect_tool.drawing_finished.connect(lambda: self._select_tool("select"))

        # 載入圖片
        self._load_image()

        # 預設使用選擇工具
        self._select_tool("select")

    def _setup_dialog(self):
        """設定對話框屬性"""
        self.setWindowTitle("圖片編輯器")
        self.setMinimumSize(900, 700)
        self.resize(1200, 800)
        self.setModal(True)

    def _setup_ui(self):
        """建立 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # 工具列
        self._toolbar = self._create_toolbar()
        layout.addWidget(self._toolbar)

        # 畫布
        self._canvas = ImageCanvas()
        layout.addWidget(self._canvas, 1)

        # 底部按鈕
        button_layout = self._create_button_bar()
        layout.addLayout(button_layout)

    def _create_toolbar(self) -> QToolBar:
        """建立工具列"""
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setStyleSheet("QToolBar { spacing: 5px; }")

        # 選擇工具
        self._btn_select = QToolButton()
        self._btn_select.setText("🔲 選擇")
        self._btn_select.setCheckable(True)
        self._btn_select.setToolTip("選擇模式 (V)")
        toolbar.addWidget(self._btn_select)

        toolbar.addSeparator()

        # 剪裁工具
        self._btn_crop = QToolButton()
        self._btn_crop.setText("✂️ 剪裁")
        self._btn_crop.setCheckable(True)
        self._btn_crop.setToolTip("剪裁工具 (C)")
        toolbar.addWidget(self._btn_crop)

        # 框選工具
        self._btn_rect = QToolButton()
        self._btn_rect.setText("⬜ 框選")
        self._btn_rect.setCheckable(True)
        self._btn_rect.setToolTip("框選標註 (R)")
        toolbar.addWidget(self._btn_rect)

        toolbar.addSeparator()

        # 重設全圖
        self._btn_reset_all = QToolButton()
        self._btn_reset_all.setText("🔄 重設")
        self._btn_reset_all.setToolTip("重設全圖 (還原至原始狀態)")
        self._btn_reset_all.clicked.connect(self._on_reset_all)
        toolbar.addWidget(self._btn_reset_all)

        toolbar.addSeparator()

        # 撤銷
        self._btn_undo = QToolButton()
        self._btn_undo.setText("↩️ 撤銷")
        self._btn_undo.setEnabled(False)
        self._btn_undo.setToolTip("撤銷 (Ctrl+Z)")
        self._btn_undo.clicked.connect(self._on_undo)
        toolbar.addWidget(self._btn_undo)

        # 重做
        self._btn_redo = QToolButton()
        self._btn_redo.setText("↪️ 重做")
        self._btn_redo.setEnabled(False)
        self._btn_redo.setToolTip("重做 (Ctrl+Y)")
        self._btn_redo.clicked.connect(self._on_redo)
        toolbar.addWidget(self._btn_redo)

        toolbar.addSeparator()

        # 縮放
        self._btn_zoom_in = QToolButton()
        self._btn_zoom_in.setText("🔍+")
        self._btn_zoom_in.setToolTip("放大")
        self._btn_zoom_in.clicked.connect(lambda: self._canvas.zoom_in())
        toolbar.addWidget(self._btn_zoom_in)

        self._btn_zoom_out = QToolButton()
        self._btn_zoom_out.setText("🔍-")
        self._btn_zoom_out.setToolTip("縮小")
        self._btn_zoom_out.clicked.connect(lambda: self._canvas.zoom_out())
        toolbar.addWidget(self._btn_zoom_out)

        self._btn_fit = QToolButton()
        self._btn_fit.setText("📐 適應")
        self._btn_fit.setToolTip("適應視窗")
        self._btn_fit.clicked.connect(lambda: self._canvas.fit_in_view())
        toolbar.addWidget(self._btn_fit)

        # 縮放比例顯示
        self._lbl_zoom = QLabel("100%")
        self._lbl_zoom.setStyleSheet("padding: 0 10px;")
        toolbar.addWidget(self._lbl_zoom)

        toolbar.addSeparator()

        # ===== 濾鏡調整 =====

        # 亮度
        toolbar.addWidget(QLabel("亮度:"))
        self._slider_brightness = QSlider(Qt.Horizontal)
        self._slider_brightness.setRange(-100, 100)
        self._slider_brightness.setValue(0)
        self._slider_brightness.setFixedWidth(100)
        self._slider_brightness.valueChanged.connect(self._on_adjustment_changed)
        toolbar.addWidget(self._slider_brightness)

        self._lbl_brightness = QLabel("0")
        self._lbl_brightness.setFixedWidth(30)
        self._lbl_brightness.setAlignment(Qt.AlignCenter)
        toolbar.addWidget(self._lbl_brightness)

        toolbar.addSeparator()

        # 對比
        toolbar.addWidget(QLabel("對比:"))
        self._slider_contrast = QSlider(Qt.Horizontal)
        self._slider_contrast.setRange(-100, 100)
        self._slider_contrast.setValue(0)
        self._slider_contrast.setFixedWidth(100)
        self._slider_contrast.valueChanged.connect(self._on_adjustment_changed)
        toolbar.addWidget(self._slider_contrast)

        self._lbl_contrast = QLabel("0")
        self._lbl_contrast.setFixedWidth(30)
        self._lbl_contrast.setAlignment(Qt.AlignCenter)
        toolbar.addWidget(self._lbl_contrast)

        # 重設調整
        self._btn_reset_filter = QToolButton()
        self._btn_reset_filter.setText("⟲")
        self._btn_reset_filter.setToolTip("重設調整")
        self._btn_reset_filter.clicked.connect(self._on_reset_adjustments)
        toolbar.addWidget(self._btn_reset_filter)

        return toolbar

    def _create_button_bar(self) -> QHBoxLayout:
        """建立底部按鈕列"""
        layout = QHBoxLayout()

        # 取消
        self._btn_cancel = QPushButton("取消")
        self._btn_cancel.clicked.connect(self.reject)
        layout.addWidget(self._btn_cancel)

        layout.addStretch()

        # 儲存
        self._btn_save = QPushButton("儲存")
        self._btn_save.setStyleSheet(
            "background-color: #4CAF50; color: white; font-weight: bold; padding: 8px 30px;"
        )
        self._btn_save.clicked.connect(self._on_save)
        layout.addWidget(self._btn_save)

        return layout

    def _setup_shortcuts(self):
        """設定快捷鍵"""
        # 撤銷
        QShortcut(QKeySequence.Undo, self, self._on_undo)
        # 重做
        QShortcut(QKeySequence.Redo, self, self._on_redo)
        # 工具切換
        QShortcut(QKeySequence("V"), self, lambda: self._select_tool("select"))
        QShortcut(QKeySequence("C"), self, lambda: self._select_tool("crop"))
        QShortcut(QKeySequence("R"), self, lambda: self._select_tool("rect"))

    def _connect_signals(self):
        """連接信號"""
        # 命令歷史
        self._history.can_undo_changed.connect(self._btn_undo.setEnabled)
        self._history.can_redo_changed.connect(self._btn_redo.setEnabled)

        # 縮放
        self._canvas.zoom_changed.connect(self._on_zoom_changed)

        # 工具按鈕
        self._btn_select.clicked.connect(lambda: self._select_tool("select"))
        self._btn_crop.clicked.connect(lambda: self._select_tool("crop"))
        self._btn_rect.clicked.connect(lambda: self._select_tool("rect"))

        # 場景選取
        if self._canvas.scene():
            self._canvas.scene().selectionChanged.connect(
                self._on_editor_selection_changed
            )

    def _load_image(self):
        """載入圖片"""
        if not self._canvas.load_image(self._image_path):
            QMessageBox.warning(self, "錯誤", f"無法載入圖片: {self._image_path}")
            self.reject()
            return

        # 適應視窗
        self._canvas.fit_in_view()

    # ===== 事件處理 =====

    def _select_tool(self, tool_name: str):
        """選擇工具"""
        # 清除選取以隱藏標註設定列
        if self._canvas.scene():
            self._canvas.scene().clearSelection()

        # 更新按鈕狀態
        self._btn_select.setChecked(tool_name == "select")
        self._btn_crop.setChecked(tool_name == "crop")
        self._btn_rect.setChecked(tool_name == "rect")

        # 控制浮動動作列
        if hasattr(self, "_crop_actions_widget"):
            if tool_name == "crop":
                self._crop_actions_widget.show()
                self._update_crop_actions_pos()
                self._crop_actions_widget.raise_()
            else:
                self._crop_actions_widget.hide()

        # 設定畫布工具
        if tool_name == "select":
            self._canvas.set_tool(None)
        elif tool_name == "crop":
            # 1. 啟動剪裁會話 (還原全圖)
            current_crop = self._canvas.start_crop_session()

            # 2. 設定工具
            self._canvas.set_tool(self._crop_tool)

            # 3. 設定工具初始範圍
            self._crop_tool.set_crop_rect(current_crop)

        elif tool_name == "rect":
            self._canvas.set_tool(self._rect_tool)

    def _confirm_crop(self):
        """確認剪裁"""
        if self._crop_tool:
            # 取得剪裁區域
            selection_rect = self._crop_tool.get_selection_rect()

            if selection_rect:
                # 結束剪裁會話 (確認)
                self._canvas.end_crop_session(confirm=True, new_rect=selection_rect)

            # 切換到選擇模式
            self._select_tool("select")

    def _on_undo(self):
        """撤銷"""
        self._history.undo()

    def _on_redo(self):
        """重做"""
        self._history.redo()

    def _on_zoom_changed(self, factor: float):
        """縮放變更"""
        self._lbl_zoom.setText(f"{int(factor * 100)}%")

        # 更新所有標註的控制點位置（因為旋轉控制點距離需要根據縮放調整）
        scene = self._canvas.scene()
        if scene:
            for item in scene.items():
                if isinstance(item, AnnotationRect):
                    item._update_handle_positions()

    def _on_pick_color(self):
        """選擇顏色"""
        color = QColorDialog.getColor(self._current_color, self, "選擇顏色")
        if color.isValid():
            self._current_color = color
            self._update_color_button()
            # 同步更新工具顏色
            if self._rect_tool:
                self._rect_tool.set_color(color)

    def _update_color_button(self):
        """更新顏色按鈕"""
        self._btn_color.setStyleSheet(
            f"background-color: {self._current_color.name()}; border: 1px solid #ccc;"
        )

    def _on_width_changed(self, value: int):
        """線寬變更"""
        self._current_line_width = value
        self._lbl_width.setText(f"{value}px")
        # 同步更新工具線寬
        if self._rect_tool:
            self._rect_tool.set_line_width(value)

    def _on_adjustment_changed(self):
        """濾鏡調整變更 (使用防抖機制)"""
        brightness = self._slider_brightness.value()
        contrast = self._slider_contrast.value()

        # 即時更新標籤
        self._lbl_brightness.setText(str(brightness))
        self._lbl_contrast.setText(str(contrast))

        # 重設計時器 (防抖)
        self._filter_timer.start()

    def _apply_filter_values(self):
        """實際套用濾鏡值 (由計時器觸發)"""
        self._canvas.set_brightness(self._slider_brightness.value())
        self._canvas.set_contrast(self._slider_contrast.value())

    def _on_reset_adjustments(self):
        """重設調整"""
        # 這會觸發 valueChanged -> _on_adjustment_changed
        self._slider_brightness.setValue(0)
        self._slider_contrast.setValue(0)

    def _on_reset_all(self):
        """重設全圖"""
        # 確認對話框
        reply = QMessageBox.question(
            self,
            "確認重設",
            "確定要重設所有變更並還原至原始圖片嗎？\n這將會清除所有標註與編輯。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            # 1. 還原圖片與清除場景
            self._canvas.reset_to_original()

            # 2. 清除命令歷史
            self._history.clear()

            # 3. 重設工具狀態
            self._select_tool("select")

            # 4. 重設調整參數
            self._on_reset_adjustments()

    def _on_save(self):
        """儲存圖片"""
        try:
            # 備份原圖到 rawdatas
            if self._pm:
                self._backup_original()

            # 渲染並儲存
            image = self._canvas.render_to_image()
            if not image.isNull():
                save_path = self._output_path if self._output_path else self._image_path
                image.save(save_path)
                self.image_saved.emit(save_path)
                self.accept()
            else:
                QMessageBox.warning(self, "錯誤", "無法儲存圖片")
        except Exception as e:
            QMessageBox.warning(self, "錯誤", f"儲存失敗: {e}")

    def _backup_original(self):
        """備份原圖到檔案所在資料夾的 rawdatas 子資料夾"""
        if not self._pm or not self._pm.current_project_path:
            return

        # 取得圖片所在資料夾 (測項資料夾)
        image_dir = os.path.dirname(self._image_path)

        # 在測項資料夾內建立 rawdatas
        rawdatas_dir = os.path.join(image_dir, "rawdatas")
        os.makedirs(rawdatas_dir, exist_ok=True)

        # 檢查是否已備份
        filename = os.path.basename(self._image_path)
        backup_path = os.path.join(rawdatas_dir, filename)

        if not os.path.exists(backup_path):
            # 複製原圖
            original = self._canvas.get_original_pixmap()
            if original and not original.isNull():
                original.save(backup_path)

    def _create_crop_actions_bar(self):
        """建立浮動剪裁動作列"""
        self._crop_actions_widget = QFrame(self._canvas)
        self._crop_actions_widget.setStyleSheet(
            """
            QFrame {
                background-color: white;
                border-radius: 20px;
                border: 1px solid #ddd;
            }
            QPushButton {
                border-radius: 15px;
                font-weight: bold;
                font-size: 14px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
            """
        )

        # 陰影效果
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 5)
        self._crop_actions_widget.setGraphicsEffect(shadow)

        layout = QHBoxLayout(self._crop_actions_widget)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(15)

        # 確認按鈕
        btn_confirm = QPushButton("✓")
        btn_confirm.setFixedSize(30, 30)
        btn_confirm.setStyleSheet("color: #4CAF50; border: 2px solid #4CAF50; font-weight: bold; font-size: 16px;")
        btn_confirm.setToolTip("確認剪裁")
        btn_confirm.setCursor(Qt.PointingHandCursor)
        btn_confirm.clicked.connect(self._confirm_crop)
        layout.addWidget(btn_confirm)

        # 取消按鈕
        btn_cancel = QPushButton("✕")
        btn_cancel.setFixedSize(30, 30)
        btn_cancel.setStyleSheet("color: #F44336; border: 2px solid #F44336; font-weight: bold; font-size: 16px;")
        btn_cancel.setToolTip("取消剪裁")
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.clicked.connect(self._cancel_crop)
        layout.addWidget(btn_cancel)

        # 初始隱藏
        self._crop_actions_widget.hide()

    def _update_crop_actions_pos(self):
        """更新動作列位置 (置中於上方)"""
        if (
            hasattr(self, "_crop_actions_widget")
            and self._crop_actions_widget.isVisible()
        ):
            # 寬度
            w = self._crop_actions_widget.width()
            # 畫布寬度
            canvas_w = self._canvas.width()

            x = (canvas_w - w) // 2
            y = 20  # 距離上方 20px

            self._crop_actions_widget.move(x, y)
            self._crop_actions_widget.raise_()

    def _cancel_crop(self):
        """取消剪裁操作"""
        if self._crop_tool:
            # 結束剪裁會話 (取消)
            self._canvas.end_crop_session(confirm=False)
            self._select_tool("select")

    def resizeEvent(self, event):
        """視窗大小改變時更新位置"""
        super().resizeEvent(event)
        self._update_crop_actions_pos()
        self._update_annotation_actions_pos()

    def _create_annotation_actions_bar(self):
        """建立浮動標註設定列 (顏色/線寬)"""
        self._annotation_actions_widget = QFrame(self._canvas)
        self._annotation_actions_widget.setStyleSheet(
            """
            QFrame {
                background-color: white;
                border-radius: 20px;
                border: 1px solid #ddd;
            }
            QLabel {
                font-weight: bold;
                color: #333;
            }
            """
        )

        # 陰影效果
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 5)
        self._annotation_actions_widget.setGraphicsEffect(shadow)

        layout = QHBoxLayout(self._annotation_actions_widget)
        layout.setContentsMargins(15, 8, 15, 8)
        layout.setSpacing(15)

        # 顏色
        layout.addWidget(QLabel("顏色:"))
        self._btn_color = QPushButton()
        self._btn_color.setFixedSize(30, 30)
        self._btn_color.setStyleSheet(
            f"background-color: {self._current_color.name()}; border: 1px solid #ccc; border-radius: 15px;"
        )
        self._btn_color.setToolTip("更改顏色")
        self._btn_color.clicked.connect(self._on_pick_color)
        layout.addWidget(self._btn_color)

        # 分隔線
        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        # 線寬
        layout.addWidget(QLabel("線寬:"))

        self._slider_width = QSlider(Qt.Horizontal)
        self._slider_width.setRange(1, 20)
        self._slider_width.setValue(self._current_line_width)
        self._slider_width.setFixedWidth(100)
        self._slider_width.valueChanged.connect(self._on_width_changed)
        layout.addWidget(self._slider_width)

        self._lbl_width = QLabel(f"{self._current_line_width}px")
        self._lbl_width.setFixedWidth(40)
        layout.addWidget(self._lbl_width)

        # 初始隱藏
        self._annotation_actions_widget.hide()

    def _update_annotation_actions_pos(self):
        """更新標註設定列位置 (置中於上方)"""
        if (
            hasattr(self, "_annotation_actions_widget")
            and self._annotation_actions_widget.isVisible()
        ):
            w = self._annotation_actions_widget.width()
            h = self._annotation_actions_widget.height()
            canvas_w = self._canvas.width()

            x = (canvas_w - w) // 2
            y = 20  # 距離上方 20px

            self._annotation_actions_widget.move(x, y)
            self._annotation_actions_widget.raise_()

    def _on_editor_selection_changed(self):
        """當編輯器內的選取項目改變時"""
        if not self._annotation_actions_widget:
            return

        scene = self._canvas.scene()
        if not scene:
            return

        selected_items = scene.selectedItems()

        # 檢查是否有選取 AnnotationRect
        has_annotation = False
        for item in selected_items:
            if isinstance(item, AnnotationRect):
                has_annotation = True
                # 更新 UI 顯示目前選取項目的屬性 (取第一個)
                self._current_color = item.annotation_color
                self._current_line_width = item.line_width

                # 更新控制項
                self._update_color_button()
                # 暫時斷開信號以避免迴圈更新
                self._slider_width.blockSignals(True)
                self._slider_width.setValue(self._current_line_width)
                self._slider_width.blockSignals(False)
                self._lbl_width.setText(f"{self._current_line_width}px")
                break

        # 只有在非裁切模式下才顯示
        is_cropping = self._btn_crop.isChecked()

        if has_annotation and not is_cropping:
            self._annotation_actions_widget.show()
            self._annotation_actions_widget.adjustSize()
            self._update_annotation_actions_pos()
        else:
            self._annotation_actions_widget.hide()

    # ===== 公開屬性 =====

    @property
    def current_color(self) -> QColor:
        """取得目前顏色"""
        return self._current_color

    @property
    def current_line_width(self) -> int:
        """取得目前線寬"""
        return self._current_line_width

    @property
    def current_rotation(self) -> int:
        """取得目前旋轉角度"""
        return self._current_rotation

    @property
    def command_history(self) -> CommandHistory:
        """取得命令歷史"""
        return self._history
