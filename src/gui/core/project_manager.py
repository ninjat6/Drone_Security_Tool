"""
專案管理模組
"""

import os
import json
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QObject, Signal

from constants import (
    PROJECT_SETTINGS_FILENAME,
    PROJECT_TYPE_FULL,
    PROJECT_TYPE_ADHOC,
    DEFAULT_TESTER_NAME,
    DEFAULT_ADHOC_PREFIX,
    DATE_FMT_PY_DATE,
    DATE_FMT_PY_DATETIME,
    DATE_FMT_PY_FILENAME,
    DATE_FMT_PY_FILENAME_SHORT,
    DIR_IMAGES,
    DIR_REPORTS,
    DIR_TRASH,
    TARGET_UAV,
    TARGET_GCS,
    TARGETS,
    STATUS_PASS,
    STATUS_FAIL,
    STATUS_NA,
    STATUS_UNCHECKED,
    STATUS_NOT_TESTED,
    STATUS_UNKNOWN,
    sanitize_filename,
)
from infrastructure.photo_server import PhotoServer


class ProjectManager(QObject):
    """專案管理器 - 負責專案的建立、載入、儲存和資料管理"""

    data_changed = Signal()
    photo_received = Signal(str, str, str)

    def __init__(self):
        super().__init__()
        self.current_project_path: Optional[str] = None
        self.project_data: Dict = {}
        self.settings_filename = PROJECT_SETTINGS_FILENAME
        self.std_config: Dict = {}
        self.server = PhotoServer(port=8000)
        self.server.photo_received.connect(self.handle_mobile_photo)

    def set_standard_config(self, config):
        self.std_config = config

    """
        # def save_snapshot(self, note="backup"):
        #     if not self.current_project_path:
        #         return False
        #     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        #     std_name = self.project_data.get("standard_name", "unknown").replace(" ", "_")
        #     filename = f"snapshot_{std_name}_{timestamp}_{note}.json"
        #     src = os.path.join(self.current_project_path, self.settings_filename)
        #     dst = os.path.join(self.current_project_path, filename)
        #     try:
        #         shutil.copy2(src, dst)
        #         return True, filename
        #     except Exception as e:
        #         return False, str(e)

        # def list_snapshots(self) -> List[str]:
        #     if not self.current_project_path:
        #         return []
        #     snaps = []
        #     for f in os.listdir(self.current_project_path):
        #         if f.startswith("snapshot_") and f.endswith(".json"):
        #             snaps.append(f)
        #     snaps.sort(reverse=True)
        #     return snaps

        # def restore_snapshot(self, snapshot_filename):
        #     if not self.current_project_path:
        #         return False
        #     src = os.path.join(self.current_project_path, snapshot_filename)
        #     dst = os.path.join(self.current_project_path, self.settings_filename)
        #     try:
        #         shutil.copy2(src, dst)
        #         return self.load_project(self.current_project_path)
        #     except Exception as e:
        #         return False, str(e)
    """

    def calculate_migration_impact(self, new_config) -> List[Dict]:
        report = []
        current_tests = self.project_data.get("tests", {})
        new_uids = set()

        if "test_standards" not in new_config:
            raise ValueError("無效的規範設定檔 (缺少 test_standards)")

        for section in new_config.get("test_standards", []):
            for item in section.get("items", []):
                uid = item.get("uid")
                if not uid:
                    raise ValueError(f"新規範中發現缺少 UID 的項目: {item.get('name')}")
                new_uids.add(uid)
                status = "NEW"
                msg = "新規範新增項目"
                if uid in current_tests:
                    old_data = current_tests[uid]
                    old_ver = "unknown"
                    for t in TARGETS:
                        if t in old_data and "criteria_version_snapshot" in old_data[t]:
                            old_ver = old_data[t]["criteria_version_snapshot"]
                            break
                    new_ver = item.get("criteria_version")

                    if old_ver == new_ver:
                        status = "MATCH"
                        msg = "標準未變，完全沿用"
                    else:
                        status = "RESET"
                        msg = f"標準變更 ({old_ver} -> {new_ver})，需重判"

                report.append(
                    {"uid": uid, "name": item.get("name"), "status": status, "msg": msg}
                )

        for uid in current_tests.keys():
            if uid not in new_uids and uid != "__meta__":
                report.append(
                    {
                        "uid": uid,
                        "name": f"Unknown ({uid})",
                        "status": "REMOVE",
                        "msg": "新規範已移除此項目",
                    }
                )

        return report

    """
        # def apply_version_switch(self, new_config, migration_report):
        #     self.save_snapshot("before_switch")
        #     old_tests_data = self.project_data.get("tests", {})
        #     new_tests_data = {}
        #     new_item_map = {}
        #     for sec in new_config["test_standards"]:
        #         for item in sec["items"]:
        #             new_item_map[item["uid"]] = item

        #     for row in migration_report:
        #         uid = row["uid"]
        #         status = row["status"]
        #         if status == "REMOVE":
        #             continue
        #         new_item_def = new_item_map.get(uid)
        #         new_ver = (
        #             new_item_def.get("criteria_version") if new_item_def else "unknown"
        #         )

        #         if status == "NEW":
        #             new_tests_data[uid] = {}  # 初始化
        #         elif status == "MATCH":
        #             new_tests_data[uid] = old_tests_data[uid].copy()
        #         elif status == "RESET":
        #             if uid in old_tests_data:
        #                 old_entry = old_tests_data[uid]
        #                 new_entry = {}
        #                 for target in TARGETS:
        #                     if target in old_entry:
        #                         new_entry[target] = {}
        #                         new_entry[target]["attachments"] = old_entry[target].get(
        #                             "attachments", []
        #                         )
        #                         new_entry[target]["result"] = STATUS_UNCHECKED
        #                         new_entry[target]["criteria_version_snapshot"] = new_ver

        #                 # 複製 Meta
        #                 if "__meta__" in old_entry:
        #                     new_entry["__meta__"] = old_entry["__meta__"].copy()

        #                 new_tests_data[uid] = new_entry

        #     self.project_data["standard_name"] = new_config.get("standard_name")
        #     self.project_data["standard_version"] = new_config.get("standard_version")
        #     self.project_data["tests"] = new_tests_data
        #     self.set_standard_config(new_config)
        #     self.save_all()
        #     self.data_changed.emit()
    """

    def handle_mobile_photo(self, target_id, category, full_path):
        if self.current_project_path:
            rel_path = os.path.relpath(full_path, self.current_project_path)
            rel_path = rel_path.replace("\\", "/")
        else:
            rel_path = full_path
        if target_id in TARGETS:
            info_key = f"{target_id}_{category}_path"
            self.update_info({info_key: rel_path})
        self.photo_received.emit(target_id, category, rel_path)

    def generate_mobile_link(
        self, target_id, target_name, is_report=False
    ) -> Optional[str]:
        if not self.current_project_path:
            return None
        if not self.server.is_running():
            self.server.start()
        save_dir = os.path.join(self.current_project_path, DIR_IMAGES)
        self.server.set_save_directory(save_dir)
        token = self.server.generate_token(target_id, target_name, is_report)
        ip = self.server.get_local_ip()
        return f"http://{ip}:{self.server.port}/upload?token={token}"

    def stop_server(self):
        self.server.stop()

    def get_current_project_type(self) -> str:
        return self.project_data.get("info", {}).get("project_type", PROJECT_TYPE_FULL)

    def is_item_visible(self, item_id) -> bool:
        if not self.current_project_path:
            return False
        info = self.project_data.get("info", {})
        p_type = info.get("project_type", PROJECT_TYPE_FULL)
        if p_type == PROJECT_TYPE_ADHOC:
            whitelist = info.get("target_items", [])
            return item_id in whitelist
        else:
            scope = info.get("test_scope", [])
            if not scope and "test_scope" not in info:
                return True
            section_id = self._find_section_id_by_item(item_id)
            return section_id in scope

    def is_section_visible(self, section_id) -> bool:
        if not self.current_project_path:
            return False
        info = self.project_data.get("info", {})
        p_type = info.get("project_type", PROJECT_TYPE_FULL)
        if p_type == PROJECT_TYPE_ADHOC:
            whitelist = info.get("target_items", [])
            section_items = self._get_items_in_section(section_id)
            return any(item.get("uid") in whitelist for item in section_items)
        else:
            scope = info.get("test_scope", [])
            if not scope and "test_scope" not in info:
                return True
            return str(section_id) in scope

    def _find_section_id_by_item(self, item_identifier) -> str:
        """根據 ID 或 UID 查找該項目所屬的 section_id"""
        for sec in self.std_config.get("test_standards", []):
            for item in sec["items"]:
                if (
                    item.get("id") == item_identifier
                    or item.get("uid") == item_identifier
                ):
                    return str(sec["section_id"])
        return ""

    def _get_items_in_section(self, section_id) -> List[Dict]:
        for sec in self.std_config.get("test_standards", []):
            if str(sec["section_id"]) == str(section_id):
                return sec["items"]
        return []

    def create_project(self, form_data: dict) -> Tuple[bool, str]:
        raw_base_path = form_data.get("save_path")
        project_name = form_data.get("project_name")
        if not raw_base_path or not project_name:
            return False, "缺少儲存路徑或專案名稱"
        base_path = os.path.abspath(os.path.expanduser(raw_base_path))
        target_folder = os.path.join(base_path, project_name)
        final_path = self._get_unique_path(target_folder)
        form_data["project_name"] = os.path.basename(final_path)
        form_data["project_type"] = PROJECT_TYPE_FULL
        current_std_name = self.std_config.get("standard_name", "Unknown")
        current_std_version = self.std_config.get("standard_version", "Unknown")
        self.project_data = {
            "standard_version": current_std_version,
            "standard_name": current_std_name,
            "info": form_data,
            "tests": {},
        }
        return self._init_folder_and_save(final_path)

    def create_ad_hoc_project(
        self, selected_items: list, save_base_path: str
    ) -> Tuple[bool, str]:
        ts_str = datetime.now().strftime(DATE_FMT_PY_FILENAME_SHORT)
        folder_name = f"QuickTest_{ts_str}"
        target_folder = os.path.join(save_base_path, folder_name)
        final_path = self._get_unique_path(target_folder)
        info_data = {}
        schema = self.std_config.get("project_meta_schema", [])
        for field in schema:
            key = field.get("key")
            f_type = field.get("type")
            if key == "project_name":
                info_data[key] = os.path.basename(final_path)
                continue
            if f_type == "date":
                info_data[key] = datetime.now().strftime(DATE_FMT_PY_DATE)
            elif f_type == "checkbox_group":
                info_data[key] = []
            elif f_type == "path_selector":
                info_data[key] = ""
            elif f_type == "text":
                key_lower = key.lower()
                if "id" in key_lower or "no" in key_lower:
                    info_data[key] = f"{DEFAULT_ADHOC_PREFIX}-{ts_str}"
                elif "tester" in key_lower or "user" in key_lower:
                    info_data[key] = DEFAULT_TESTER_NAME
                else:
                    info_data[key] = "-"
            else:
                info_data[key] = ""
        info_data["project_type"] = PROJECT_TYPE_ADHOC
        info_data["target_items"] = selected_items
        current_std_name = self.std_config.get("standard_name", "Unknown")
        current_std_version = self.std_config.get("standard_version", "Unknown")
        self.project_data = {
            "standard_version": current_std_version,
            "standard_name": current_std_name,
            "info": info_data,
            "tests": {},
        }
        return self._init_folder_and_save(final_path)

    def fork_project_to_new_version(
        self, new_project_name, new_config, migration_report
    ) -> Tuple[bool, str]:
        """另存新檔並升級規範版本"""
        if not self.current_project_path:
            return False, "未開啟專案"

        parent_dir = os.path.dirname(self.current_project_path)
        new_project_path = os.path.join(parent_dir, new_project_name)

        if os.path.exists(new_project_path):
            return False, "目標資料夾已存在，請更換名稱。"

        try:
            os.makedirs(new_project_path)

            # 複製資源資料夾
            for folder in [DIR_IMAGES, DIR_REPORTS]:
                src = os.path.join(self.current_project_path, folder)
                dst = os.path.join(new_project_path, folder)
                if os.path.exists(src):
                    shutil.copytree(src, dst)
                else:
                    os.makedirs(dst)

            # 準備新的專案資料
            old_data = self.project_data
            new_data = {
                "standard_version": new_config.get("standard_version"),
                "standard_name": new_config.get("standard_name"),
                "info": old_data.get("info", {}).copy(),
                "tests": {},
            }
            new_data["info"]["project_name"] = new_project_name

            # 處理測項資料遷移
            old_tests = old_data.get("tests", {})
            new_tests = {}

            uid_to_new_item = {}
            for sec in new_config.get("test_standards", []):
                for item in sec["items"]:
                    uid_to_new_item[item["uid"]] = item

            for row in migration_report:
                uid = row["uid"]
                status = row["status"]

                if status == "REMOVE":
                    continue

                if status == "NEW":
                    new_tests[uid] = {}

                elif status == "MATCH":
                    if uid in old_tests:
                        new_tests[uid] = old_tests[uid].copy()

                elif status == "RESET":
                    if uid in old_tests:
                        old_entry = old_tests[uid]
                        new_entry = {}
                        new_ver = uid_to_new_item[uid].get(
                            "criteria_version", "unknown"
                        )

                        for target in TARGETS:
                            if target in old_entry:
                                new_entry[target] = {}
                                if "attachments" in old_entry[target]:
                                    new_entry[target]["attachments"] = old_entry[
                                        target
                                    ].get("attachments", [])
                                new_entry[target]["result"] = STATUS_UNCHECKED
                                new_entry[target]["criteria_version_snapshot"] = new_ver
                                old_desc = old_entry[target].get("description", "")
                                new_entry[target][
                                    "description"
                                ] = f"[系統] 因規範版本變更 ({old_entry[target].get('criteria_version_snapshot')} -> {new_ver})，請重新判定。\n{old_desc}"

                        new_tests[uid] = new_entry
                        if "__meta__" in old_entry:
                            new_entry["__meta__"] = old_entry["__meta__"].copy()

            new_data["tests"] = new_tests

            # 寫入新的 json 檔案
            new_json_path = os.path.join(new_project_path, self.settings_filename)
            with open(new_json_path, "w", encoding="utf-8") as f:
                json.dump(new_data, f, ensure_ascii=False, indent=4)

            return True, new_project_path

        except Exception as e:
            if os.path.exists(new_project_path):
                shutil.rmtree(new_project_path)
            return False, str(e)

    def _get_unique_path(self, target_folder) -> str:
        final_path = target_folder
        if os.path.exists(final_path):
            i = 1
            while True:
                new_path = f"{target_folder}_{i}"
                if not os.path.exists(new_path):
                    final_path = new_path
                    break
                i += 1
        return final_path

    def _init_folder_and_save(self, path) -> Tuple[bool, str]:
        try:
            os.makedirs(path, exist_ok=True)
            os.makedirs(os.path.join(path, DIR_IMAGES), exist_ok=True)
            os.makedirs(os.path.join(path, DIR_REPORTS), exist_ok=True)
            self.current_project_path = path
            self.save_all()
            return True, path
        except Exception as e:
            return False, str(e)

    def peek_project_standard(self, folder_path: str) -> Optional[str]:
        json_path = os.path.join(folder_path, self.settings_filename)
        if not os.path.exists(json_path):
            return None
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("standard_name")
        except:
            return None

    def load_project(self, folder_path: str) -> Tuple[bool, str]:
        json_path = os.path.join(folder_path, self.settings_filename)
        if not os.path.exists(json_path):
            return False, "找不到專案設定檔"
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                self.project_data = json.load(f)
            self.current_project_path = folder_path
            self.data_changed.emit()
            return True, "讀取成功"
        except Exception as e:
            return False, f"讀取失敗: {e}"


    def get_item_folder(
        self,
        item_id: str,
        item_name: str,
        targets: list = None,
        target: str = None,
        is_shared: bool = False,
    ) -> str:
        """
        取得檢測項目的佐證資料夾路徑
        
        Args:
            item_id: 檢測項目 ID (如 6.2.1)
            item_name: 檢測項目名稱 (如 身分鑑別)
            targets: 測項的目標列表 (如 ["UAV", "GCS"])
            target: 目前的目標 (如 "UAV", "GCS", "Shared")
            is_shared: 是否為共用模式
        
        Returns:
            相對路徑：
            - 單一目標: reports/{item_id}_{item_name}/
            - 多目標分開: reports/{item_id}_{item_name}/{target}/
            - 多目標共用: reports/{item_id}_{item_name}/Shared/
        """
        safe_name = sanitize_filename(item_name)
        base_folder = f"{item_id}_{safe_name}"
        
        # 判斷是否為多目標
        is_multi_target = targets and len(targets) > 1
        
        if is_multi_target:
            if is_shared or target == "Shared":
                return os.path.join(DIR_REPORTS, base_folder, "Shared")
            elif target:
                return os.path.join(DIR_REPORTS, base_folder, target)
            else:
                # 預設使用第一個 target
                return os.path.join(DIR_REPORTS, base_folder, targets[0])
        else:
            # 單一目標，直接放根目錄
            return os.path.join(DIR_REPORTS, base_folder)

    def import_attachment(
        self,
        src_path: str,
        item_id: str,
        item_name: str,
        file_type: str = "img",
        title: str = "",
        targets: list = None,
        target: str = None,
        is_shared: bool = False,
    ) -> Optional[str]:
        """
        匯入佐證資料到檢測項目資料夾
        
        Args:
            src_path: 來源檔案路徑
            item_id: 檢測項目 ID (如 6.2.1)
            item_name: 檢測項目名稱 (如 身分鑑別)
            file_type: 檔案類型 (img, log, file)
            title: 檔案標題 (用於檔名)
            targets: 測項的目標列表 (如 ["UAV", "GCS"])
            target: 目前的目標 (如 "UAV", "GCS", "Shared")
            is_shared: 是否為共用模式
        
        Returns:
            相對路徑或 None
        
        檔名格式：{yyyymmdd_hhmm}_{type}_{title}.{ext}
        """
        if not self.current_project_path:
            return None
        
        try:
            # 取得副檔名
            _, ext = os.path.splitext(src_path)
            ext = ext.lower()
            
            # 產生時間戳
            ts = datetime.now().strftime(DATE_FMT_PY_FILENAME_SHORT)
            
            # 處理標題 (如果沒有標題，使用原檔名)
            if not title:
                title = os.path.splitext(os.path.basename(src_path))[0]
            safe_title = sanitize_filename(title)
            
            # 組合檔名
            new_filename = f"{ts}_{file_type}_{safe_title}{ext}"
            
            # 取得目標資料夾（支援多目標）
            item_folder = self.get_item_folder(
                item_id, item_name, targets=targets, target=target, is_shared=is_shared
            )
            target_dir = os.path.join(self.current_project_path, item_folder)
            
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
            
            dest_path = os.path.join(target_dir, new_filename)
            
            # 如果檔案已存在，加上秒數時間戳
            if os.path.exists(dest_path):
                ts_sec = datetime.now().strftime("%H%M%S")
                base, ext = os.path.splitext(new_filename)
                new_filename = f"{base}_{ts_sec}{ext}"
                dest_path = os.path.join(target_dir, new_filename)
            
            shutil.copy2(src_path, dest_path)
            
            # 回傳相對路徑
            rel_path = os.path.relpath(dest_path, self.current_project_path)
            return rel_path.replace("\\", "/")
            
        except Exception as e:
            print(f"匯入附件失敗: {e}")
            return None

    def move_to_trash(self, file_path: str) -> bool:
        """
        將檔案移動到同層的 trash 資料夾
        
        Args:
            file_path: 絕對路徑或相對於專案的路徑
        
        Returns:
            是否成功
        """
        if not self.current_project_path:
            return False
        
        try:
            # 處理相對路徑
            if not os.path.isabs(file_path):
                file_path = os.path.join(self.current_project_path, file_path)
            
            if not os.path.exists(file_path):
                return False
            
            # 取得檔案所在資料夾和檔名
            file_dir = os.path.dirname(file_path)
            filename = os.path.basename(file_path)
            
            # 建立 trash 資料夾
            trash_dir = os.path.join(file_dir, DIR_TRASH)
            if not os.path.exists(trash_dir):
                os.makedirs(trash_dir)
            
            # 移動檔案
            dest_path = os.path.join(trash_dir, filename)
            
            # 如果 trash 中已有同名檔案，加上時間戳
            if os.path.exists(dest_path):
                ts = datetime.now().strftime(DATE_FMT_PY_FILENAME_SHORT)
                base, ext = os.path.splitext(filename)
                dest_path = os.path.join(trash_dir, f"{base}_{ts}{ext}")
            
            shutil.move(file_path, dest_path)
            return True
            
        except Exception as e:
            print(f"移動到 trash 失敗: {e}")
            return False

    def rename_attachment(self, old_path: str, new_title: str) -> Optional[str]:
        """
        根據新標題重命名附件檔案
        
        檔名格式：{timestamp}_{type}_{title}.{ext}
        只更改 title 部分，保留 timestamp 和 type
        
        Args:
            old_path: 原始檔案路徑（絕對或相對）
            new_title: 新的標題
        
        Returns:
            新的絕對路徑，或 None（如果失敗）
        """
        if not self.current_project_path:
            return None
        
        try:
            # 處理相對路徑
            if not os.path.isabs(old_path):
                old_path = os.path.join(self.current_project_path, old_path)
            
            if not os.path.exists(old_path):
                return None
            
            file_dir = os.path.dirname(old_path)
            old_filename = os.path.basename(old_path)
            
            # 解析原檔名：{timestamp}_{type}_{title}.{ext}
            # 例如：20260108_1615_img_Nmap_掃描結果.png
            base, ext = os.path.splitext(old_filename)
            parts = base.split("_", 2)  # 最多分割成 3 部分
            
            if len(parts) >= 2:
                # 有 timestamp_type 前綴
                timestamp = parts[0]
                file_type = parts[1] if len(parts) > 1 else "img"
            else:
                # 沒有標準格式，使用當前時間
                timestamp = datetime.now().strftime(DATE_FMT_PY_FILENAME_SHORT)
                file_type = "img"
            
            # 產生新檔名
            safe_title = sanitize_filename(new_title)
            new_filename = f"{timestamp}_{file_type}_{safe_title}{ext}"
            new_path = os.path.join(file_dir, new_filename)
            
            # 如果檔名沒變，直接回傳
            if old_path == new_path:
                return old_path
            
            # 如果新檔名已存在，加上秒數時間戳
            if os.path.exists(new_path):
                ts_sec = datetime.now().strftime("%H%M%S")
                new_filename = f"{timestamp}_{file_type}_{safe_title}_{ts_sec}{ext}"
                new_path = os.path.join(file_dir, new_filename)
            
            os.rename(old_path, new_path)
            return new_path
            
        except Exception as e:
            print(f"重命名附件失敗: {e}")
            return None


    def merge_external_project(self, source_folder: str) -> Tuple[bool, str]:
        if not self.current_project_path:
            return False, "請先開啟主專案"
        if self.get_current_project_type() != PROJECT_TYPE_FULL:
            return False, "非完整專案不可合併"

        source_json_path = os.path.join(source_folder, self.settings_filename)
        if not os.path.exists(source_json_path):
            return False, "來源無效 (找不到 project_settings.json)"

        try:
            with open(source_json_path, "r", encoding="utf-8") as f:
                source_data = json.load(f)

            # 檢查類型
            if source_data.get("info", {}).get("project_type") != PROJECT_TYPE_ADHOC:
                return False, "只能合併 Ad-Hoc 類型的專案"

            # 嚴格檢查規範版本
            src_std = source_data.get("standard_name", "")
            curr_std = self.project_data.get("standard_name", "")

            if src_std != curr_std:
                return (
                    False,
                    f"規範版本不符，無法合併！\n\n主專案規範: {curr_std}\n來源檔規範: {src_std}",
                )

            # 複製檔案
            for sub in [DIR_IMAGES, DIR_REPORTS]:
                src_sub_dir = os.path.join(source_folder, sub)
                if not os.path.exists(src_sub_dir):
                    continue
                dest_sub_dir = os.path.join(self.current_project_path, sub)
                if not os.path.exists(dest_sub_dir):
                    os.makedirs(dest_sub_dir)

                for filename in os.listdir(src_sub_dir):
                    s_file = os.path.join(src_sub_dir, filename)
                    d_file = os.path.join(dest_sub_dir, filename)
                    if os.path.exists(d_file):
                        d_file = os.path.join(dest_sub_dir, f"merged_{filename}")
                    if os.path.isfile(s_file):
                        shutil.copy2(s_file, d_file)

            # 合併測試數據
            source_tests = source_data.get("tests", {})
            current_tests = self.project_data.get("tests", {})
            merged_count = 0

            for test_id, targets_data in source_tests.items():
                if test_id not in current_tests:
                    current_tests[test_id] = {}
                for target, result_data in targets_data.items():
                    current_tests[test_id][target] = result_data
                    merged_count += 1

            self.save_all()
            self.data_changed.emit()
            return True, f"成功合併 {merged_count} 筆測項資料"

        except Exception as e:
            return False, f"合併失敗: {str(e)}"

    def update_info(self, new_info):
        if not self.current_project_path:
            return False
        self.project_data.setdefault("info", {}).update(new_info)
        self.save_all()
        self.data_changed.emit()
        return True

    def update_test_result(self, test_uid, target, result_data, is_shared=False):
        if "tests" not in self.project_data:
            self.project_data["tests"] = {}
        if test_uid not in self.project_data["tests"]:
            self.project_data["tests"][test_uid] = {}
        self.project_data["tests"][test_uid][target] = result_data
        self.project_data["tests"][test_uid][target][
            "last_updated"
        ] = datetime.now().strftime(DATE_FMT_PY_DATETIME)
        meta = self.project_data["tests"][test_uid].setdefault("__meta__", {})
        meta["is_shared"] = is_shared
        self.save_all()
        self.data_changed.emit()

    def get_test_result(self, test_uid, target, is_shared=False):
        """取得測項結果"""
        tests = self.project_data.get("tests", {})
        item_data = tests.get(test_uid, {})
        # 如果是共用模式，TestPage 傳入的 target 可能是 "Shared"
        # 這裡直接回傳對應 target 的資料即可
        return item_data.get(target, {})

    def update_adhoc_items(self, new_whitelist, removed_items):
        """更新 Ad-Hoc 白名單，並刪除被移除項目的資料"""
        if not self.current_project_path:
            return

        self.project_data.setdefault("info", {})["target_items"] = new_whitelist

        tests_data = self.project_data.get("tests", {})
        for uid in removed_items:
            if uid in tests_data:
                del tests_data[uid]
                print(f"Deleted data for: {uid}")

        self.save_all()
        self.data_changed.emit()

    def get_test_meta(self, test_uid):
        return self.project_data.get("tests", {}).get(test_uid, {}).get("__meta__", {})

    def update_test_meta(self, test_uid, target, meta_update: dict):
        """
        更新測項的 meta 資料
        
        Args:
            test_uid: 測項 UID
            target: 目標 (UAV, GCS, Shared)
            meta_update: 要更新的 meta 欄位
        """
        if "tests" not in self.project_data:
            self.project_data["tests"] = {}
        if test_uid not in self.project_data["tests"]:
            self.project_data["tests"][test_uid] = {}
        if "__meta__" not in self.project_data["tests"][test_uid]:
            self.project_data["tests"][test_uid]["__meta__"] = {}
        
        self.project_data["tests"][test_uid]["__meta__"].update(meta_update)
        self.save_all()
        self.data_changed.emit()

    def save_all(self):
        if not self.current_project_path:
            return False, "No Path"
        path = os.path.join(self.current_project_path, self.settings_filename)
        temp_path = path + ".tmp"
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self.project_data, f, ensure_ascii=False, indent=4)
                f.flush()
                os.fsync(f.fileno())

            if os.path.exists(path):
                os.replace(temp_path, path)
            else:
                os.rename(temp_path, path)

            return True, "Saved"
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return False, str(e)

    def get_test_status_detail(self, item_config) -> Dict[str, str]:
        uid = item_config.get("uid", item_config.get("id"))
        targets = item_config.get("targets", [TARGET_GCS])
        item_data = self.project_data.get("tests", {}).get(uid, {})
        
        # 檢查是否為共用模式
        meta = item_data.get("__meta__", {})
        is_shared = meta.get("is_shared", False)
        
        status_map = {}
        
        if is_shared and len(targets) > 1:
            # 共用模式：使用 Shared 的結果顯示各 target
            shared_data = item_data.get("Shared", {})
            res = shared_data.get("result", STATUS_UNCHECKED)
            
            # 判斷 Shared 的狀態
            if STATUS_UNCHECKED in res:
                shared_status = STATUS_NOT_TESTED
            elif STATUS_PASS in res:
                shared_status = "Pass"
            elif STATUS_FAIL in res:
                shared_status = "Fail"
            elif STATUS_NA in res:
                shared_status = "N/A"
            else:
                shared_status = STATUS_UNKNOWN
            
            # 將同一狀態套用到所有 target
            for t in targets:
                status_map[t] = shared_status
        else:
            # 分開模式：顯示各 target 的狀態
            for t in targets:
                if t not in item_data:
                    status_map[t] = STATUS_NOT_TESTED
                else:
                    res = item_data[t].get("result", STATUS_UNCHECKED)
                    if STATUS_UNCHECKED in res:
                        status_map[t] = STATUS_NOT_TESTED
                    elif STATUS_PASS in res:
                        status_map[t] = "Pass"
                    elif STATUS_FAIL in res:
                        status_map[t] = "Fail"
                    elif STATUS_NA in res:
                        status_map[t] = "N/A"
                    else:
                        status_map[t] = STATUS_UNKNOWN
        return status_map

    def is_test_fully_completed(self, item_config) -> bool:
        uid = item_config.get("uid", item_config.get("id"))
        targets = item_config.get("targets", [TARGET_GCS])
        saved = self.project_data.get("tests", {}).get(uid, {})
        for t in targets:
            if t not in saved:
                return False
            if STATUS_UNCHECKED in saved[t].get("result", STATUS_UNCHECKED):
                return False
        return True
