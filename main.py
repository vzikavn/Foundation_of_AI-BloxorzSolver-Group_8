import os
import sys
import tkinter as tk
from board import discover_levels
from gui import BloxorzGUI


def main() -> None:
    levels_dir = "levels"
    os.makedirs(levels_dir, exist_ok=True)

    # 1. Tự động quét tất cả các file .json do bạn đưa vào thư mục levels/
    level_paths = discover_levels(levels_dir)

    # 2. Hỗ trợ truyền đường dẫn file JSON từ tham số dòng lệnh (nếu có)
    if len(sys.argv) > 1:
        custom_path = sys.argv[1]
        if os.path.isfile(custom_path) and custom_path not in level_paths:
            level_paths.insert(0, custom_path)

    # 3. Khởi chạy giao diện Bloxorz 2.5D
    root = tk.Tk()
    app = BloxorzGUI(root, level_paths, levels_dir=levels_dir)
    root.mainloop()


if __name__ == "__main__":
    main()