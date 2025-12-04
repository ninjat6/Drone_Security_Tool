import os
import sys


def get_project_root()-> str:
    """
    取得專案的根目錄絕對路徑 (HACKRF_PROJECT)。
    HACKRF_PROJECT/
    └── src/
        └── hackrf/
            └── tools/
                └── utils.py  <-- this file
    return: str
    """
    # 取得 utils.py 的絕對路徑
    current_file = os.path.abspath(__file__)
    # print(current_file)
    
    # 往上跳 3 層: tools -> hackrf -> src -> HACKRF_PROJECT
    # 註：如果你的目錄結構改變，這裡的層數需要對應調整
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
    
    return project_root


if __name__ == "__main__":
    pass