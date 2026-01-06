"""
主應用程式視窗模組
"""

import os
from functools import partial

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QScrollArea,
    QFileDialog,
    QMessageBox,
    QInputDialog,
    QLineEdit,
    QStatusBar,
    QSizePolicy,
    QDialog,
    QApplication,
)
from PySide6.QtGui import QShortcut, QKeySequence

from constants import (
    PROJECT_TYPE_FULL,
    PROJECT_TYPE_ADHOC,
    DEFAULT_DESKTOP_PATH,
    STATUS_NOT_TESTED,
    TARGETS,
    COLOR_BTN_ACTIVE,
    COLOR_BG_DEFAULT,
    COLOR_BG_PASS,
    COLOR_BG_FAIL,
    COLOR_BG_NA,
    COLOR_TEXT_GRAY,
    COLOR_TEXT_PASS,
    COLOR_TEXT_FAIL,
    COLOR_TEXT_WHITE,
)
from core.project_manager import ProjectManager
from dialogs.version_dialog import VersionSelectionDialog
from dialogs.migration_dialog import MigrationReportDialog
from pages.overview import OverviewPage
from pages.test_page import UniversalTestPage
from pages.quick_selector import QuickTestSelector
from pages.project_form import ProjectFormController
from windows.bordered_window import BorderedMainWindow


class MainApp(BorderedMainWindow):
    """主應用程式視窗"""

    def __init__(self, config_mgr):
        super().__init__()
        self.config_mgr = config_mgr
        self.pm = ProjectManager()
        self.test_ui_elements = {}
        self.current_font_size = 10

        self.pm.photo_received.connect(self.on_photo_received)

        self.config = self._get_initial_config()

        # 設定主視窗大小
        self.resize(1400, 900)

        # UI 初始化
        self.cw = QWidget()
        self.setCentralWidget(self.cw)
        self.main_l = QVBoxLayout(self.cw)

        self.setStatusBar(QStatusBar(self))
        self.statusBar().showMessage("就緒")

        self._init_menu()

        self.tabs = QTabWidget()
        self.main_l.addWidget(self.tabs)
        self._init_zoom()

        if self.config:
            self.rebuild_ui_from_config()
            self._set_ui_locked(True)
            self.setWindowTitle("無人機資安檢測工具 (請從選單建立或開啟專案)")
        else:
            QMessageBox.warning(
                self, "警告", "找不到任何規範設定檔，請檢查 configs 資料夾。"
            )
            self._set_ui_locked(True)

    def _get_initial_config(self):
        configs = self.config_mgr.list_available_configs()
        if configs:
            try:
                return self.config_mgr.load_config(configs[0]["path"])
            except:
                return None
        return None

    def _set_ui_locked(self, locked: bool):
        self.tabs.setEnabled(not locked)
        self.a_edit.setEnabled(not locked)
        self.a_merge.setEnabled(not locked)
        if not locked and self.tabs.count() > 0:
            self.tabs.setCurrentIndex(0)

    def rebuild_ui_from_config(self):
        if not self.config:
            return

        std_name = self.config.get(
            "standard_name", self.config.get("standard_version", "Unknown")
        )
        if self.pm.current_project_path:
            proj_name = self.pm.project_data.get("info", {}).get(
                "project_name", "未命名"
            )
            self.setWindowTitle(f"無人機資安檢測工具 - {proj_name} [{std_name}]")
        else:
            self.setWindowTitle(f"無人機資安檢測工具 - {std_name}")

        self.pm.set_standard_config(self.config)

        self.tabs.clear()
        self.test_ui_elements = {}

        self.overview = OverviewPage(self.pm, self.config)
        self.tabs.addTab(self.overview, "總覽 Overview")
        self.tabs.currentChanged.connect(
            lambda i: self.overview.refresh_data() if i == 0 else None
        )
        self.pm.data_changed.connect(self.refresh_ui)

        for sec in self.config.get("test_standards", []):
            p = QWidget()
            v = QVBoxLayout(p)
            v.addWidget(QLabel(f"<h3>{sec['section_name']}</h3>"))
            scr = QScrollArea()
            scr.setWidgetResizable(True)
            v.addWidget(scr)
            cont = QWidget()
            cv = QVBoxLayout(cont)
            scr.setWidget(cont)

            for item in sec["items"]:
                row = QWidget()
                rh = QHBoxLayout(row)
                rh.setContentsMargins(0, 5, 0, 5)

                btn = QPushButton(f"{item['id']} {item['name']}")
                btn.setFixedHeight(40)
                btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                btn.clicked.connect(partial(self.open_test, item))

                st_cont = QWidget()
                st_l = QHBoxLayout(st_cont)
                st_l.setContentsMargins(0, 0, 0, 0)
                st_cont.setFixedWidth(240)
                rh.addWidget(btn)
                rh.addWidget(st_cont)
                cv.addWidget(row)

                uid = item.get("uid", item.get("id"))
                self.test_ui_elements[uid] = (btn, st_l, item, row)

            cv.addStretch()
            self.tabs.addTab(p, sec["section_id"])

        self.update_font()

    def _init_menu(self):
        mb = self.menuBar()

        f_menu = mb.addMenu("檔案")
        f_menu.addAction("📝 新建專案", self.on_new)
        f_menu.addAction("📂 開啟專案", self.on_open)
        f_menu.addSeparator()
        self.a_edit = f_menu.addAction("編輯專案資訊", self.on_edit)

        t_menu = mb.addMenu("工具")
        t_menu.addAction("🔧 各別檢測模式 (Ad-Hoc)", self.on_adhoc)
        t_menu.addSeparator()
        self.a_save_as_ver = t_menu.addAction(
            "🔄 另存專案為不同版本規範", self.on_save_as_new_version
        )
        self.a_save_as_ver.setEnabled(False)
        t_menu.addSeparator()
        self.a_merge = t_menu.addAction(
            "匯入各別檢測結果 (Merge Ad-Hoc)", self.on_merge
        )

    def _init_zoom(self):
        self.shortcut_zoom_in = QShortcut(QKeySequence.ZoomIn, self)
        self.shortcut_zoom_in.activated.connect(self.zoom_in)
        self.shortcut_zoom_in_alt = QShortcut(QKeySequence("Ctrl+="), self)
        self.shortcut_zoom_in_alt.activated.connect(self.zoom_in)
        self.shortcut_zoom_out = QShortcut(QKeySequence.ZoomOut, self)
        self.shortcut_zoom_out.activated.connect(self.zoom_out)

    def zoom_in(self):
        if self.current_font_size < 30:
            self.current_font_size += 2
            self.update_font()

    def zoom_out(self):
        if self.current_font_size > 8:
            self.current_font_size -= 2
            self.update_font()

    def update_font(self):
        font_family = '"Microsoft JhengHei", "Segoe UI", sans-serif'
        QApplication.instance().setStyleSheet(
            f"QWidget {{ font-size: {self.current_font_size}pt; font-family: {font_family}; }}"
        )

    def on_new(self):
        sel_dialog = VersionSelectionDialog(self.config_mgr, self)
        if sel_dialog.exec() != QDialog.Accepted or not sel_dialog.selected_config:
            return

        selected_config = sel_dialog.selected_config

        c = ProjectFormController(self, selected_config)
        d = c.run()
        if d:
            self.config = selected_config
            self.rebuild_ui_from_config()

            ok, r = self.pm.create_project(d)
            if ok:
                self.project_ready()
            else:
                QMessageBox.warning(self, "建立失敗", r)

    def on_open(self):
        dialog = QFileDialog(self, "選專案")
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setOption(QFileDialog.DontUseNativeDialog, True)
        dialog.setDirectory(DEFAULT_DESKTOP_PATH)

        if dialog.exec() == QDialog.Accepted:
            selected = dialog.selectedFiles()
            if selected:
                folder_path = selected[0]
                proj_std = self.pm.peek_project_standard(folder_path)

                if proj_std:
                    target_config = self.config_mgr.find_config_by_name(proj_std)
                    if target_config:
                        self.config = target_config
                        self.rebuild_ui_from_config()
                    else:
                        ret = QMessageBox.question(
                            self,
                            "規範遺失",
                            f"專案使用規範：{proj_std}\n系統找不到此規範檔。\n是否嘗試使用目前載入的規範開啟？",
                            QMessageBox.Yes | QMessageBox.No,
                        )
                        if ret == QMessageBox.No:
                            return
                else:
                    QMessageBox.warning(
                        self, "警告", "無法識別專案規範版本，將使用目前版本開啟。"
                    )

                ok, m = self.pm.load_project(folder_path)
                if ok:
                    self.project_ready()
                else:
                    QMessageBox.warning(self, "載入失敗", m)

    def on_adhoc(self):
        QMessageBox.information(
            self,
            "各別檢測模式說明",
            "【注意】\n\n各別檢測模式 (Ad-Hoc) 產生的結果，\n"
            "日後僅能合併至「完全相同規範版本」的完整專案中。\n\n"
            "請確認您選擇的規範版本與目標專案一致。",
        )

        sel_dialog = VersionSelectionDialog(self.config_mgr, self)
        if sel_dialog.exec() != QDialog.Accepted or not sel_dialog.selected_config:
            return

        selected_config = sel_dialog.selected_config

        d = QuickTestSelector(self, selected_config)
        s, p = d.run()
        if s and p:
            self.config = selected_config
            self.rebuild_ui_from_config()

            ok, r = self.pm.create_ad_hoc_project(s, p)
            if ok:
                self.project_ready()
            else:
                QMessageBox.warning(self, "建立失敗", r)

    def on_edit(self):
        if not self.pm.current_project_path:
            return

        p_type = self.pm.get_current_project_type()

        if p_type == PROJECT_TYPE_ADHOC:
            self.edit_adhoc_items()
        else:
            c = ProjectFormController(
                self, self.config, self.pm.project_data.get("info", {})
            )
            d = c.run()
            if d and self.pm.update_info(d):
                QMessageBox.information(self, "OK", "已更新")
                self.overview.refresh_data()

    def on_save_as_new_version(self):
        if not self.pm.current_project_path:
            return

        sel_dialog = VersionSelectionDialog(self.config_mgr, self)
        if sel_dialog.exec() != QDialog.Accepted or not sel_dialog.selected_config:
            return

        new_config = sel_dialog.selected_config
        new_std_name = new_config.get("standard_name", "NewVer")

        try:
            report = self.pm.calculate_migration_impact(new_config)
            report_dialog = MigrationReportDialog(self, report)
            if report_dialog.exec() != QDialog.Accepted:
                return

            current_name = self.pm.project_data.get("info", {}).get(
                "project_name", "Project"
            )
            default_new_name = f"{current_name}_{new_std_name}"

            new_name, ok = QInputDialog.getText(
                self,
                "另存新版本專案",
                "請輸入新專案名稱 (將建立新資料夾)：",
                QLineEdit.Normal,
                default_new_name,
            )

            if ok and new_name:
                success, msg = self.pm.fork_project_to_new_version(
                    new_name, new_config, report
                )

                if success:
                    QMessageBox.information(
                        self,
                        "成功",
                        f"已建立新專案：{new_name}\n\n系統將自動切換至新專案。",
                    )

                    new_project_path = msg
                    ok_load, err_load = self.pm.load_project(new_project_path)

                    if ok_load:
                        self.config = new_config
                        self.rebuild_ui_from_config()
                        self.project_ready()
                    else:
                        QMessageBox.warning(
                            self, "載入失敗", f"新專案建立成功但載入失敗：{err_load}"
                        )
                else:
                    QMessageBox.critical(self, "建立失敗", msg)

        except ValueError as e:
            QMessageBox.critical(self, "錯誤", f"遷移計算失敗：\n{str(e)}")

    def edit_adhoc_items(self):
        current_whitelist = self.pm.project_data.get("info", {}).get("target_items", [])

        d = QuickTestSelector(self, self.config)

        for i in range(d.list_widget.count()):
            item = d.list_widget.item(i)
            uid = item.data(Qt.UserRole)
            if uid in current_whitelist:
                item.setCheckState(Qt.Checked)

        new_selected, _ = d.run()

        if new_selected is not None:
            removed_items = set(current_whitelist) - set(new_selected)

            if removed_items:
                ret = QMessageBox.question(
                    self,
                    "確認移除",
                    f"您取消了 {len(removed_items)} 個測項。\n"
                    "這些測項的現有檢測結果將被永久刪除！\n\n確定要繼續嗎？",
                    QMessageBox.Yes | QMessageBox.No,
                )
                if ret == QMessageBox.No:
                    return

            self.pm.update_adhoc_items(new_selected, removed_items)
            self.refresh_ui()
            self.rebuild_ui_from_config()
            self.project_ready()
            QMessageBox.information(self, "更新完成", "檢測項目已更新。")

    def on_switch_version(self):
        if not self.pm.current_project_path:
            return
        sel_dialog = VersionSelectionDialog(self.config_mgr, self)
        if sel_dialog.exec() != QDialog.Accepted or not sel_dialog.selected_config:
            return
        new_config = sel_dialog.selected_config
        try:
            report = self.pm.calculate_migration_impact(new_config)
            report_dialog = MigrationReportDialog(self, report)
            if report_dialog.exec() == QDialog.Accepted:
                self.pm.apply_version_switch(new_config, report)
                self.config = new_config
                self.rebuild_ui_from_config()
                self.project_ready()
                QMessageBox.information(self, "成功", "版本切換完成，舊設定已備份。")
        except ValueError as e:
            QMessageBox.critical(self, "遷移失敗", f"無法切換至此版本：\n{str(e)}")

    def on_restore_snapshot(self):
        snaps = self.pm.list_snapshots()
        if not snaps:
            QMessageBox.information(self, "無快照", "目前沒有備份快照。")
            return
        item, ok = QInputDialog.getItem(
            self, "還原快照", "請選擇要還原的時間點：", snaps, 0, False
        )
        if ok and item:
            if (
                QMessageBox.question(self, "確認", "還原將覆蓋目前的進度，確定嗎？")
                == QMessageBox.Yes
            ):
                ok, msg = self.pm.restore_snapshot(item)
                if ok:
                    std_name = self.pm.project_data.get("standard_name")
                    target_config = self.config_mgr.find_config_by_name(std_name)
                    if target_config:
                        self.config = target_config
                        self.rebuild_ui_from_config()
                        self.project_ready()
                        QMessageBox.information(self, "成功", "專案已還原")
                    else:
                        QMessageBox.warning(
                            self, "警告", "還原成功，但找不到對應的規範 JSON。"
                        )
                else:
                    QMessageBox.warning(self, "失敗", msg)

    def on_merge(self):
        d = QFileDialog.getExistingDirectory(self, "選匯入目錄")
        if d:
            ok, msg = self.pm.merge_external_project(d)
            if ok:
                QMessageBox.information(self, "OK", msg)
            else:
                QMessageBox.warning(self, "Fail", msg)

    def project_ready(self):
        self._set_ui_locked(False)
        self.refresh_ui()
        self.tabs.setCurrentIndex(0)

        std_name = self.config.get("standard_name", "Unknown")
        proj_name = self.pm.project_data.get("info", {}).get("project_name", "未命名")
        p_type = self.pm.get_current_project_type()

        if p_type == PROJECT_TYPE_ADHOC:
            self.setWindowTitle(
                f"無人機資安檢測工具 [各別檢測模式] - {proj_name} [{std_name}]"
            )
        else:
            self.setWindowTitle(f"無人機資安檢測工具 - {proj_name} [{std_name}]")

    def refresh_ui(self):
        self.overview.refresh_data()
        self.update_status()
        self.update_tab_visibility()

        has_proj = self.pm.current_project_path is not None
        p_type = self.pm.get_current_project_type()

        self.a_edit.setEnabled(has_proj)
        self.a_merge.setEnabled(has_proj)

        if has_proj and p_type == PROJECT_TYPE_FULL:
            self.a_save_as_ver.setEnabled(True)
        else:
            self.a_save_as_ver.setEnabled(False)

        if has_proj and p_type == PROJECT_TYPE_ADHOC:
            self.a_edit.setEnabled(True)
            self.a_edit.setText("編輯檢測項目 (Ad-Hoc)")
            self.a_merge.setEnabled(False)
        else:
            self.a_edit.setText("編輯專案資訊")

    def update_status(self):
        for uid, (btn, layout, conf, row) in self.test_ui_elements.items():
            target_id = conf.get("uid", conf.get("id"))

            if not self.pm.is_item_visible(target_id):
                row.hide()
                continue
            row.show()

            status_map = self.pm.get_test_status_detail(conf)
            is_any = any(s != STATUS_NOT_TESTED for s in status_map.values())
            if is_any:
                btn.setStyleSheet(
                    f"QPushButton {{ background-color: {COLOR_BTN_ACTIVE}; color: white; font-weight: bold; }}"
                )
            else:
                btn.setStyleSheet("")

            while layout.count():
                layout.takeAt(0).widget().deleteLater()
            for t, s in status_map.items():
                lbl = QLabel(f"{t}: {s}" if len(status_map) > 1 else s)
                lbl.setAlignment(Qt.AlignCenter)
                lbl.setFixedHeight(30)
                c = COLOR_BG_DEFAULT
                tc = COLOR_TEXT_GRAY
                if s == "Pass":
                    c = COLOR_BG_PASS
                    tc = COLOR_TEXT_PASS
                elif s == "Fail":
                    c = COLOR_BG_FAIL
                    tc = COLOR_TEXT_FAIL
                elif s == "N/A":
                    c = COLOR_BG_NA
                    tc = COLOR_TEXT_WHITE

                lbl.setStyleSheet(
                    f"background-color:{c}; color:{tc}; border-radius:4px; font-weight:bold;"
                )
                layout.addWidget(lbl)

    def update_tab_visibility(self):
        if not self.pm.current_project_path:
            return
        for i, sec in enumerate(self.config.get("test_standards", [])):
            t_idx = i + 1
            sec_id = sec["section_id"]
            is_visible = self.pm.is_section_visible(sec_id)
            self.tabs.setTabEnabled(t_idx, is_visible)
            self.tabs.setTabText(
                t_idx, sec["section_name"] + (" (未啟用)" if not is_visible else "")
            )

    def open_test(self, item):
        self.win = QWidget()
        self.win.setWindowTitle(f"檢測 {item['id']} {item['name']}")
        self.win.resize(1200, 800)
        l = QVBoxLayout(self.win)
        l.addWidget(UniversalTestPage(item, self.pm))
        self.win.show()

    @Slot(str, str, str)
    def on_photo_received(self, target_id, category, path):
        filename = os.path.basename(path)
        msg = f"✅ 已收到照片：[{target_id} - {category}] {filename}"
        self.statusBar().showMessage(msg, 5000)

        if target_id in TARGETS:
            self.refresh_ui()
