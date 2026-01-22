"""
GUI 常數定義模組
包含檔案系統設定、狀態常數、顏色配置、目標定義等
"""

import os

# ==============================================================================
# 檔案系統設定
# ==============================================================================

CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "configs")


ICON_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "icons")

ICON_PATH = os.path.join(ICON_DIR, "UAV_Security_Tool_icon_v4.svg")
CLOSE_ICON_PATH = os.path.join(ICON_DIR, "Close.svg")
MAXIMIZE_ICON_PATH = os.path.join(ICON_DIR, "Maximize.svg")
MINIMIZE_ICON_PATH = os.path.join(ICON_DIR, "Minimize.svg")




PROJECT_SETTINGS_FILENAME = "project_settings.json"
DIR_IMAGES = "images"
DIR_REPORTS = "reports"
DIR_TRASH = "trash"
DEFAULT_DESKTOP_PATH = os.path.join(os.path.expanduser("~"), "Desktop")

# 檔名中不允許的字元
UNSAFE_FILENAME_CHARS = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']


def sanitize_filename(name: str) -> str:
    """將檔名中的特殊字元替換為底線"""
    result = name
    for char in UNSAFE_FILENAME_CHARS:
        result = result.replace(char, "_")
    return result.strip()

# ==============================================================================
# 專案類型與預設值
# ==============================================================================

PROJECT_TYPE_FULL = "full"
PROJECT_TYPE_ADHOC = "ad_hoc"
DEFAULT_TESTER_NAME = "QuickUser"
DEFAULT_ADHOC_PREFIX = "ADHOC"

# ==============================================================================
# 日期格式
# ==============================================================================

DATE_FMT_PY_DATE = "%Y-%m-%d"
DATE_FMT_PY_DATETIME = "%Y-%m-%d %H:%M:%S"
DATE_FMT_PY_FILENAME = "%Y%m%d_%H%M%S"
DATE_FMT_PY_FILENAME_SHORT = "%Y%m%d_%H%M"
DATE_FMT_QT = "yyyy-MM-dd"

# ==============================================================================
# 檢測狀態常數
# ==============================================================================

STATUS_PASS = "合格 (Pass)"
STATUS_FAIL = "不合格 (Fail)"
STATUS_NA = "不適用 (N/A)"
STATUS_UNCHECKED = "未判定"
STATUS_NOT_TESTED = "未檢測"
STATUS_UNKNOWN = "Unknown"

# ==============================================================================
# 顏色配置 (HEX)
# ==============================================================================

# 背景色
COLOR_BG_PASS = "#d4edda"
COLOR_BG_FAIL = "#f8d7da"
COLOR_BG_NA = "#e2e3e5"
COLOR_BG_DEFAULT = "#dddddd"
COLOR_BG_WARN = "#fff3cd"
COLOR_BG_GRAY_LIGHT = "#f5f5f5"
COLOR_BG_THUMBNAIL = "#f0f0f0"
COLOR_BG_TERMINAL = "#2d2d2d"
COLOR_BG_TERMINAL_RESULT = "#1e1e1e"

# 文字色
COLOR_TEXT_PASS = "#155724"
COLOR_TEXT_FAIL = "#721c24"
COLOR_TEXT_NORMAL = "#333333"
COLOR_TEXT_WHITE = "white"
COLOR_TEXT_GRAY = "#666666"
COLOR_TEXT_WARN = "#856404"
COLOR_TEXT_SUBTITLE = "#555555"
COLOR_TEXT_TERMINAL_GREEN = "#00ff00"
COLOR_TEXT_TERMINAL_GRAY = "#d4d4d4"

# 按鈕色
COLOR_BTN_ACTIVE = "#2196F3"
COLOR_BTN_HOVER = "#1976D2"
COLOR_BTN_SUCCESS = "#4CAF50"
COLOR_BTN_DANGER = "#d9534f"
COLOR_BTN_CLOSE_HOVER = "#E81123"

# 邊框色
COLOR_BORDER = "#CCCCCC"
COLOR_BORDER_LIGHT = "#dddddd"
COLOR_CHECKBOX_SHARE = "blue"

# ==============================================================================
# 照片視角與目標定義
# ==============================================================================

TARGET_UAV = "UAV"
TARGET_GCS = "GCS"
TARGETS = [TARGET_UAV, TARGET_GCS]

PHOTO_ANGLES_ORDER = ["front", "back", "side1", "side2", "top", "bottom"]
PHOTO_ANGLES_NAME = {
    "front": "正面 (Front)",
    "back": "背面 (Back)",
    "side1": "側面1 (Side 1)",
    "side2": "側面2 (Side 2)",
    "top": "上方 (Top)",
    "bottom": "下方 (Bottom)",
}


if __name__ == "__main__":
    print(os.path.exists(ICON_DIR))