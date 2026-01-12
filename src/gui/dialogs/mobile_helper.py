"""
手機助手對話框
顯示 QR Code 讓手機掃描連線
"""

import qrcode
from io import BytesIO

from PySide6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QApplication,
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

from dialogs.bordered_dialog import BorderedDialog


class MobileHelperDialog(BorderedDialog):
    """
    手機助手浮動視窗
    顯示 QR Code 和連線狀態
    """

    def __init__(self, parent, pm, config):
        super().__init__(parent)
        self.pm = pm
        self.config = config
        self.setWindowTitle("📱 手機助手")
        self.resize(300, 450)
        self._init_ui()
        self._start_server()

    def _init_ui(self):
        # 使用 BorderedDialog 的 _content_layout
        layout = self._content_layout
        layout.setSpacing(12)

        # QR Code
        self.qr_label = QLabel()
        self.qr_label.setFixedSize(200, 200)
        self.qr_label.setAlignment(Qt.AlignCenter)
        self.qr_label.setStyleSheet("border: 2px solid #ddd; border-radius: 8px; background: white;")
        layout.addWidget(self.qr_label, alignment=Qt.AlignCenter)

        # IP 選擇 (下拉選單)
        url_label = QLabel("選擇網路介面：")
        url_label.setStyleSheet("font-size: 11px; color: #888;")
        layout.addWidget(url_label)
        
        from PySide6.QtWidgets import QComboBox
        self.ip_combo = QComboBox()
        # 設定 ComboBox 樣式
        self.ip_combo.setStyleSheet("""
            QComboBox {
                font-size: 12px;
                color: #F0F0F0;
                background-color: #2a2a2a;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 8px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                color: #F0F0F0;
                background-color: #2a2a2a;
                border: 1px solid #555;
                selection-background-color: #444;
                selection-color: #F0F0F0;
                outline: none;
                padding: 0px;
                margin: 0px;
            }
            QComboBox QAbstractItemView::item {
                padding: 8px;
                min-height: 24px;
                background-color: #2a2a2a;
                color: #F0F0F0;
                border: none;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #444;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #5D5D5D;
            }
        """)
        # 額外設定：解決視窗邊框白邊問題 (設定容器視窗屬性)
        # 注意：setStyleSheet 只能影響 widget 本身，對於 Window 容器需要清除預設樣式
        popup = self.ip_combo.view().window()
        popup.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        popup.setAttribute(Qt.WA_TranslucentBackground)
        popup.setStyleSheet("background-color: #2a2a2a; border: 1px solid #555;")
        
        self.ip_combo.currentTextChanged.connect(self._on_ip_changed)
        layout.addWidget(self.ip_combo)
        
        self.url_input = QLineEdit()
        self.url_input.setReadOnly(True)
        self.url_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #555;
                border-radius: 4px;
                background: #2a2a2a;
                color: #fff;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.url_input)
        
        # 複製按鈕
        copy_btn = QPushButton("📋 複製網址")
        copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        copy_btn.clicked.connect(self._copy_url)
        layout.addWidget(copy_btn)

        # 狀態
        self.status_label = QLabel("🟢 服務已啟動")
        self.status_label.setStyleSheet("font-size: 12px; color: #28a745; font-weight: bold;")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        # 停止按鈕
        self.stop_btn = QPushButton("停止服務")
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        self.stop_btn.clicked.connect(self._stop_server)
        layout.addWidget(self.stop_btn)

    def _copy_url(self):
        """複製網址到剪貼簿"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.url_input.text())
        self.status_label.setText("✅ 已複製到剪貼簿")
        self.status_label.setStyleSheet("font-size: 12px; color: #28a745; font-weight: bold;")

    def _start_server(self):
        """啟動伺服器並顯示 QR Code"""
        # 設定專案資訊
        items = self._get_items_for_mobile()
        self.pm.server.set_project(
            self.pm.current_project_path,
            self.pm.get_project_name(),
            items
        )
        
        # 啟動伺服器
        if not self.pm.server.is_running():
            self.pm.server.start()
        
        # 填充 IP 選項
        self.ip_combo.clear()
        all_ips = self.pm.server.get_all_ips()
        for ip in all_ips:
            self.ip_combo.addItem(ip)
        
        # 顯示 QR Code (使用第一個 IP)
        if all_ips:
            self._update_url_and_qr(all_ips[0])
        
        self.status_label.setText("🟢 服務已啟動（在所有介面監聽）")
        self.status_label.setStyleSheet("font-size: 12px; color: #28a745; font-weight: bold;")
        self.stop_btn.setText("停止服務")
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        try:
            self.stop_btn.clicked.disconnect()
        except:
            pass
        self.stop_btn.clicked.connect(self._stop_server)

    def _stop_server(self):
        """停止伺服器"""
        self.pm.server.stop()
        self.status_label.setText("🔴 服務已停止")
        self.status_label.setStyleSheet("font-size: 12px; color: #dc3545; font-weight: bold;")
        self.qr_label.clear()
        self.qr_label.setText("服務已停止")
        self.stop_btn.setText("重新啟動")
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        try:
            self.stop_btn.clicked.disconnect()
        except:
            pass
        self.stop_btn.clicked.connect(self._start_server)

    def _get_items_for_mobile(self):
        """取得測項列表（簡化版本給手機使用）"""
        items = []
        if not self.config:
            return items
        
        for section in self.config.get("test_standards", []):
            for item in section.get("items", []):
                # 檢查是否可見
                item_uid = item.get("uid", item.get("id"))
                if not self.pm.is_item_visible(item_uid):
                    continue
                
                items.append({
                    "uid": item_uid,
                    "id": item.get("id", ""),
                    "name": item.get("name", ""),
                    "targets": item.get("targets", ["UAV"]),
                })
        
        return items

    def _on_ip_changed(self, ip):
        """當用戶選擇不同 IP 時更新 QR Code"""
        if ip:
            self._update_url_and_qr(ip)
    
    def _update_url_and_qr(self, ip):
        """更新 URL 和 QR Code"""
        url = f"http://{ip}:{self.pm.server.port}/"
        self.url_input.setText(url)
        self._show_qr(url)

    def _show_qr(self, url: str):
        """顯示 QR Code"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=5,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        
        pixmap = QPixmap()
        pixmap.loadFromData(buffer.read())
        self.qr_label.setPixmap(pixmap.scaled(
            180, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation
        ))

    def closeEvent(self, event):
        """關閉視窗時停止伺服器"""
        if self.pm.server.is_running():
            self.pm.server.stop()
        super().closeEvent(event)
