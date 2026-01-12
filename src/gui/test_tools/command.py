"""
指令執行測項工具模組
包含 CommandTestToolStrings, CommandTestToolView, CommandWorker, CommandTestTool
"""

import os
import sys
import signal
from datetime import datetime
from typing import Dict, Optional

from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QPainter, QPixmap, QColor, QTextCursor, QTextCharFormat
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QGroupBox,
    QMessageBox,
    QApplication,
)

from styles import Styles
from constants import sanitize_filename, DATE_FMT_PY_FILENAME_SHORT
from .base import BaseTestToolView, BaseTestTool


# ==============================================================================
# 字串常數
# ==============================================================================


class CommandTestToolStrings:
    """CommandTestToolView 字串常數"""

    # GroupBox 標題
    GB_TOOL = "🔧 指令執行設定"
    GB_RESULT = "執行結果"

    # Labels
    LBL_COMMAND = "將執行的指令 (可自訂)："

    # 按鈕
    BTN_RUN = "▶️ 執行"
    BTN_RUNNING = "⏳ 執行中..."
    BTN_STOP = "⏹️ 停止"
    BTN_SCREENSHOT = "📷 擷取截圖加入佐證"
    BTN_SAVE_LOG = "💾 儲存 Log 紀錄"

    # Placeholder
    HINT_RESULT = "執行結果將顯示於此..."

    # 錯誤訊息
    ERR_EMPTY_CMD = "請輸入指令"
    TITLE_ERROR = "錯誤"
    ERR_CMD_NOT_FOUND = "[ERROR] 找不到指令，請確認已安裝"
    ERR_EXEC_FAILED = "[ERROR] 執行失敗："


# ==============================================================================
# View 類別
# ==============================================================================


class CommandTestToolView(BaseTestToolView):
    """
    指令執行測項通用 UI 視圖
    繼承 BaseTestToolView，提供：
    - 指令輸入/編輯區
    - 執行按鈕
    - 結果顯示區
    - 截圖/儲存 Log 按鈕

    子類別可覆寫：
    - _build_input_section(): 新增專屬輸入欄位 (如 IP、Port 等)
    - _get_tool_title(): 工具標題
    - _get_result_placeholder(): 結果區預設文字
    """

    # Signals
    run_requested = Signal(str)  # 發送要執行的指令
    screenshot_requested = Signal()  # 請求截圖
    save_log_requested = Signal()  # 請求儲存 log

    def _build_custom_section(self) -> QWidget:
        """覆寫：建立指令執行通用 UI (顯示在右側)"""
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(10)

        # 1. 工具設定區 (包含子類別專屬輸入)
        g_tool = QGroupBox(self._get_tool_title())
        v = QVBoxLayout()
        v.setSpacing(8)

        # 子類別專屬輸入區
        input_section = self._build_input_section()
        if input_section:
            v.addWidget(input_section)

        # 指令顯示/編輯區
        S = CommandTestToolStrings
        v.addWidget(QLabel(S.LBL_COMMAND))
        self.command_edit = QLineEdit()
        self.command_edit.setStyleSheet(Styles.INPUT_COMMAND)
        v.addWidget(self.command_edit)

        h_btn = QHBoxLayout()
        self.btn_run = QPushButton(self._get_run_button_text())
        self.btn_run.setStyleSheet(Styles.BTN_PRIMARY)
        self.btn_run.clicked.connect(self._on_run_clicked)
        h_btn.addWidget(self.btn_run)

        self.btn_stop = QPushButton(CommandTestToolStrings.BTN_STOP)
        self.btn_stop.setStyleSheet(Styles.BTN_DANGER)
        self.btn_stop.clicked.connect(self._on_stop_clicked)
        self.btn_stop.setVisible(False)
        h_btn.addWidget(self.btn_stop)

        h_btn.addStretch()
        v.addLayout(h_btn)

        g_tool.setLayout(v)
        container_layout.addWidget(g_tool)

        # 2. 結果顯示區 - 延伸到底部
        g_result = QGroupBox(S.GB_RESULT)
        v_result = QVBoxLayout()

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setStyleSheet(Styles.TEXT_RESULT)
        self.result_text.setPlaceholderText(self._get_result_placeholder())
        v_result.addWidget(self.result_text, stretch=1)

        # 操作按鈕列
        h_actions = QHBoxLayout()

        self.btn_screenshot = QPushButton(S.BTN_SCREENSHOT)
        self.btn_screenshot.setStyleSheet(Styles.BTN_PADDING)
        self.btn_screenshot.clicked.connect(lambda: self.screenshot_requested.emit())
        h_actions.addWidget(self.btn_screenshot, 1)

        self.btn_save_log = QPushButton(S.BTN_SAVE_LOG)
        self.btn_save_log.setStyleSheet(Styles.BTN_PADDING)
        self.btn_save_log.clicked.connect(lambda: self.save_log_requested.emit())
        h_actions.addWidget(self.btn_save_log, 1)

        # h_actions.addStretch()
        v_result.addLayout(h_actions)

        g_result.setLayout(v_result)
        container_layout.addWidget(g_result, stretch=1)

        # 初始化指令
        self._update_command_preview()

        return container

    # ----- 子類別可覆寫的方法 -----

    def _build_input_section(self) -> Optional[QWidget]:
        """
        子類別覆寫：建立專屬輸入區
        回傳 QWidget 將顯示在指令輸入框上方
        """
        return None

    def _get_tool_title(self) -> str:
        """子類別覆寫：工具標題"""
        return CommandTestToolStrings.GB_TOOL

    def _get_run_button_text(self) -> str:
        """子類別覆寫：執行按鈕文字"""
        return CommandTestToolStrings.BTN_RUN

    def _get_running_button_text(self) -> str:
        """子類別覆寫：執行中按鈕文字"""
        return CommandTestToolStrings.BTN_RUNNING

    def _get_result_placeholder(self) -> str:
        """子類別覆寫：結果區預設文字"""
        return CommandTestToolStrings.HINT_RESULT

    def _update_command_preview(self):
        """子類別覆寫：更新指令預覽"""
        pass

    def _validate_before_run(self) -> bool:
        """子類別覆寫：執行前驗證，回傳 False 則不執行"""
        S = CommandTestToolStrings
        cmd = self.command_edit.text().strip()
        if not cmd:
            QMessageBox.warning(self, S.TITLE_ERROR, S.ERR_EMPTY_CMD)
            return False
        return True

    stop_requested = Signal()  # 請求停止

    def _on_run_clicked(self):
        """執行按鈕點擊"""
        if not self._validate_before_run():
            return
        cmd = self.command_edit.text().strip()
        self.run_requested.emit(cmd)

    def _on_stop_clicked(self):
        """停止按鈕點擊"""
        self.stop_requested.emit()

    # ----- View 通用方法 -----

    def set_running(self, is_running: bool):
        """設定執行中狀態"""
        self.btn_run.setVisible(not is_running)
        self.btn_stop.setVisible(is_running)

        if is_running:
            self.btn_run.setText(self._get_running_button_text())
        else:
            self.btn_run.setText(self._get_run_button_text())

        self.command_edit.setEnabled(not is_running)
        self._set_inputs_enabled(not is_running)

    def _set_inputs_enabled(self, enabled: bool):
        """子類別覆寫：設定專屬輸入欄位的啟用狀態"""
        pass

    def set_result(self, text: str):
        """設定結果"""
        self.result_text.setPlainText(text)

    def append_result(self, text: str):
        """附加結果"""
        self.result_text.append(text)

    def get_command(self) -> str:
        return self.command_edit.text().strip()

    def get_result_text(self) -> str:
        return self.result_text.toPlainText()


# ==============================================================================
# Worker 類別 (背景執行緒)
# ==============================================================================


class CommandWorker(QThread):
    """
    通用指令執行工作執行緒 - 避免 UI 凍結
    支援 pkexec 提權、即時輸出、取消執行
    """

    output_ready = Signal(str)  # 即時輸出
    finished_signal = Signal(str)  # 執行完成

    def __init__(self, command: list, parent=None):
        super().__init__(parent)
        self.command = command
        self._is_cancelled = False
        self.process = None

    def run(self):
        import subprocess
        import select

        try:
            self.process = subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                start_new_session=True,
            )

            # 使用 select 進行非阻塞讀取，每 0.1 秒檢查一次取消狀態
            while True:
                if self._is_cancelled:
                    break

                # 檢查是否有資料可讀 (timeout 0.1 秒)
                ready, _, _ = select.select([self.process.stdout], [], [], 0.1)

                if ready:
                    line = self.process.stdout.readline()
                    if line == "":
                        break  # EOF - 程序已結束
                    self.output_ready.emit(line)

                # 檢查程序是否已結束
                if self.process.poll() is not None:
                    # 讀取剩餘輸出
                    remaining = self.process.stdout.read()
                    if remaining:
                        self.output_ready.emit(remaining)
                    break

            self.process.stdout.close()

            # 只有在非取消狀態下才等待程序結束
            if not self._is_cancelled:
                self.process.wait()

            self.finished_signal.emit("")

        except FileNotFoundError:
            self.output_ready.emit(CommandTestToolStrings.ERR_CMD_NOT_FOUND + "\n")
            self.finished_signal.emit("")
        except Exception as e:
            if not self._is_cancelled:
                self.output_ready.emit(
                    CommandTestToolStrings.ERR_EXEC_FAILED + str(e) + "\n"
                )
            self.finished_signal.emit("")

    def cancel(self):
        self._is_cancelled = True
        if self.process:
            # 殺掉整個 Process Group
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
            except:
                pass

            # 強制殺死 pkexec
            try:
                self.process.kill()
            except:
                pass


# ==============================================================================
# Tool 類別 (邏輯 + 控制層)
# ==============================================================================


class CommandTestTool(BaseTestTool):
    """
    指令執行測項工具 (通用基礎類別)
    繼承 BaseTestTool，提供：
    - 指令執行 (使用 QThread 避免 UI 凍結)
    - 截圖功能
    - Log 儲存功能

    子類別可覆寫：
    - _get_tool_name(): 工具名稱 (用於檔名)
    - _get_screenshot_title(): 截圖建議標題
    - _get_log_header(): Log 檔案標頭
    - _needs_root(command): 判斷是否需要 root 權限
    - _get_command_data_key(): 資料儲存的 key 名稱
    - _load_command_data(data): 載入專用資料
    """

    # Signals
    screenshot_taken = Signal(str, str)  # (image_path, suggested_title)
    log_saved = Signal(str)  # log_path

    def __init__(
        self, config, result_data, target, project_manager=None, save_callback=None, is_shared=False
    ):
        super().__init__(config, result_data, target, project_manager, save_callback, is_shared)

        # 指令執行狀態
        self.last_command = ""
        self.last_result = ""
        self.worker = None
        self.log_path = ""
        self.worker = None
        self.log_path = ""

        # 綁定 View 事件
        self.view.run_requested.connect(self._run_command)
        self.view.stop_requested.connect(self._stop_command)
        self.view.screenshot_requested.connect(self._take_screenshot)
        self.view.save_log_requested.connect(self._save_log)

        # 載入專用資料
        if result_data:
            self._load_command_data(result_data)

    @property
    def project_path(self):
        """取得專案路徑 (從 ProjectManager)"""
        return self.pm.current_project_path if self.pm else None

    def _create_view(self, config) -> CommandTestToolView:
        """覆寫：回傳 CommandTestToolView"""
        return CommandTestToolView(config)

    def _run_command(self, command: str):
        """執行指令 (使用 QThread)"""
        # 如果已有執行中的指令，先取消
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait()

        self.last_command = command
        self.last_result = ""
        self.view.set_running(True)

        # 判斷是否需要 root 權限
        needs_root = self._needs_root(command)

        if needs_root:
            full_command = ["pkexec"] + command.split()
            self.view.set_result(
                f"執行指令 (需要 root 權限)：pkexec {command}\n\n請在彈出視窗中輸入密碼...\n\n"
            )
        else:
            full_command = command.split()
            self.view.set_result(f"執行指令：{command}\n\n")

        # 建立並啟動工作執行緒
        self.worker = CommandWorker(full_command)
        self.worker.output_ready.connect(self._on_output)
        self.worker.finished_signal.connect(self._on_finished)
        self.worker.start()

    def _stop_command(self):
        """停止執行"""
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.view.append_result("\n🛑 使用者強制停止")

    def _on_output(self, line: str):
        """即時處理輸出"""
        self.last_result += line
        self.view.append_result(line)

    def _on_finished(self, full_output: str):
        """執行完成處理"""
        self.view.set_running(False)
        if full_output:
            self.view.append_result("\n✅ 執行完成")

    def _take_screenshot(self):
        """擷取結果截圖"""
        if not self.project_path:
            QMessageBox.warning(self.view, "錯誤", "專案路徑未設定，無法儲存截圖")
            return

        # 取得檢測項目資料夾（支援多目標）
        item_folder = self.pm.get_item_folder(
            self.item_id, self.item_name,
            targets=self.targets, target=self.target, is_shared=self.is_shared
        )
        report_dir = os.path.join(self.project_path, item_folder)
        os.makedirs(report_dir, exist_ok=True)

        # 擷取 result_text 的截圖 (完整內容)
        result_widget = self.view.result_text

        # 直接讀取設定 (可由子類別覆寫或直接修改此處數值)
        width = self._get_screenshot_width()

        original_document = result_widget.document()

        # 複製一份 Document 以免影響原來畫面
        document = original_document.clone()

        # 設定寬度以進行重排 (Reflow)
        document.setTextWidth(width)

        # 強制將文字顏色改為黑色 (確保在白底上清晰可見)
        cursor = QTextCursor(document)
        cursor.select(QTextCursor.Document)
        fmt = QTextCharFormat()
        fmt.setForeground(QColor("black"))
        cursor.mergeCharFormat(fmt)

        # 計算完整尺寸
        height = int(document.size().height())

        if height == 0:
            height = 100

        # 建立 Pixmap 並填滿白色背景
        pixmap = QPixmap(width, height)
        pixmap.fill(QColor("white"))

        # 繪製完整文字內容
        painter = QPainter(pixmap)
        document.drawContents(painter)
        painter.end()

        # 產生標題：{tool}_{command}掃描結果
        tool_name = self._get_tool_name()
        # cmd_short = self.last_command[:30] if self.last_command else ""
        title = f"{tool_name}_掃描結果"
        safe_title = sanitize_filename(title)

        # 產生檔名：{yyyymmdd_hhmm}_img_{title}.png
        timestamp = datetime.now().strftime(DATE_FMT_PY_FILENAME_SHORT)
        filename = f"{timestamp}_img_{safe_title}.png"
        filepath = os.path.join(report_dir, filename)

        # 如果檔案已存在，加上秒數時間戳避免覆蓋
        if os.path.exists(filepath):
            ts_sec = datetime.now().strftime("%H%M%S")
            filename = f"{timestamp}_img_{safe_title}_{ts_sec}.png"
            filepath = os.path.join(report_dir, filename)

        # 儲存截圖
        pixmap.save(filepath, "PNG")

        # 直接加入到附件列表
        if self.view.attachment_list:
            self.view.attachment_list.add_attachment(filepath, title, "image")

        QMessageBox.information(
            self.view, "截圖成功", f"完整截圖已儲存並加入佐證資料：\n{filename}"
        )

    def _save_log(self):
        """儲存 log 紀錄並加入佐證資料"""
        if not self.project_path:
            QMessageBox.warning(self.view, "錯誤", "專案路徑未設定，無法儲存 log")
            return

        if not self.last_result:
            QMessageBox.warning(self.view, "錯誤", "沒有執行結果可儲存")
            return

        # 取得檢測項目資料夾（支援多目標）
        item_folder = self.pm.get_item_folder(
            self.item_id, self.item_name,
            targets=self.targets, target=self.target, is_shared=self.is_shared
        )
        report_dir = os.path.join(self.project_path, item_folder)
        os.makedirs(report_dir, exist_ok=True)

        # 產生標題：{tool}_{command}執行紀錄
        tool_name = self._get_tool_name()
        cmd_short = self.last_command[:30] if self.last_command else ""
        title = f"{tool_name}_{cmd_short}執行紀錄"
        safe_title = sanitize_filename(title)

        # 產生檔名：{yyyymmdd_hhmm}_log_{title}.txt
        timestamp = datetime.now().strftime(DATE_FMT_PY_FILENAME_SHORT)
        filename = f"{timestamp}_log_{safe_title}.txt"
        filepath = os.path.join(report_dir, filename)

        # 如果檔案已存在，加上秒數時間戳避免覆蓋
        if os.path.exists(filepath):
            ts_sec = datetime.now().strftime("%H%M%S")
            filename = f"{timestamp}_log_{safe_title}_{ts_sec}.txt"
            filepath = os.path.join(report_dir, filename)

        # 儲存 log
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self._get_log_header())
            f.write(f"# 時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# 指令：{self.last_command}\n")
            f.write(f"# ===================================\n\n")
            f.write(self.last_result)

        # 加入到附件列表 (使用 type: "log" 和 command 欄位)
        if self.view.attachment_list:
            self.view.attachment_list.add_attachment_with_extra(
                filepath, title, "log", {"command": self.last_command}
            )

        QMessageBox.information(
            self.view, "儲存成功", f"Log 已儲存並加入佐證資料：\n{filename}"
        )

    def get_result(self) -> Dict:
        """覆寫：繼承基本結果"""
        return super().get_result()

    # ----- 子類別可覆寫的方法 -----

    def _get_tool_name(self) -> str:
        """子類別覆寫：工具名稱 (用於檔名)"""
        return "command"

    def _get_screenshot_title(self, timestamp: str) -> str:
        """子類別覆寫：截圖建議標題"""
        return f"指令執行結果 ({timestamp})"

    def _get_log_header(self) -> str:
        """子類別覆寫：Log 檔案標頭"""
        return "# 指令執行紀錄\n"

    def _needs_root(self, command: str) -> bool:
        """子類別覆寫：判斷是否需要 root 權限"""
        return False

    def _get_screenshot_width(self) -> int:
        """子類別覆寫：截圖寬度 (px)"""
        return 650

    def _get_command_data_key(self) -> str:
        """子類別覆寫：資料儲存的 key 前綴"""
        return "command"

    def _load_command_data(self, data):
        """子類別覆寫：載入專用資料"""
        data_key = self._get_command_data_key()
        self.last_command = data.get(f"{data_key}_command", "")
        self.log_path = data.get(f"{data_key}_result", "")

        if self.last_command:
            self.view.command_edit.setText(self.last_command)

        # 從 log 檔案讀取結果
        if self.log_path and self.project_path:
            log_full_path = os.path.join(self.project_path, self.log_path)
            if os.path.exists(log_full_path):
                try:
                    with open(log_full_path, "r", encoding="utf-8") as f:
                        self.last_result = f.read()
                    self.view.set_result(self.last_result)
                except Exception:
                    pass


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 測試用假資料
    dummy_config = {
        "id": "test_cmd",
        "name": "獨立測試視窗",
        "logic": "AND",
        "checklist": [{"id": "chk1", "content": "測試檢查點"}],
    }

    # 直接實例化 Tool (這樣按鈕才有作用)
    tool = CommandTestTool(dummy_config, {}, "target_test")
    tool.set_project_path(os.path.join(os.path.expanduser("~"), "Desktop"))

    tool.get_widget().resize(1200, 800)  # 調整視窗大小以便檢視
    tool.get_widget().show()
    sys.exit(app.exec())
