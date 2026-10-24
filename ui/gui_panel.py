# ui/gui_panel.py
import os
import tkinter as tk
from typing import Any, Callable, Dict, List, Optional

from ui.gui_config import COLORS


class ControlPanel:
    """
    Quản lý bảng điều khiển bên phải (Sidebar):
    - Danh sách cuộn chọn màn chơi (hiển thị trực tiếp toàn bộ level trong thư mục levels/).
    - Nút Restart / Undo.
    - Các nút chạy thuật toán AI Solver (BFS, DFS, UCS, A*).
    - Bảng thống kê kết quả thực thi và chuỗi bước giải.
    """

    def __init__(
        self,
        parent: tk.Widget,
        root: tk.Tk,
        on_select_level: Callable[[str], None],
        on_restart: Callable[[], None],
        on_undo: Callable[[], None],
        on_run_solver: Callable[[str], None],
    ) -> None:
        self.root = root
        self.on_select_level = on_select_level
        self.on_restart = on_restart
        self.on_undo = on_undo
        self.on_run_solver = on_run_solver

        self.frame = tk.Frame(parent, bg=COLORS["bg_panel"], width=310, padx=12, pady=12)
        self.frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        self.frame.pack_propagate(False)

        self._build_level_selector()
        self._build_game_controls()
        self._build_solver_buttons()
        self._build_metrics_section()

    @staticmethod
    def build_legend_bar(parent: tk.Widget) -> None:
        legend_frame = tk.Frame(parent, bg=COLORS["bg_panel"], padx=10, pady=7)
        legend_frame.pack(fill=tk.X, pady=(8, 0))
        legend_text = (
            "Chú thích 2.5D:  [Đá xám] Sàn thường  |  [Cam đất] Gạch mỏng (Fragile)  |  "
            "[Xanh lam] Cầu (Bridge)  |  [Đĩa tròn] Soft Switch  |  "
            "[Chữ X] Heavy Switch  |  [Vòng ( )] Split Switch  |  [Hố sâu] Ô Đích (Goal)"
        )
        tk.Label(
            legend_frame,
            text=legend_text,
            font=("Segoe UI", 9),
            bg=COLORS["bg_panel"],
            fg="#E5E7EB",
        ).pack()

    def _build_level_selector(self) -> None:
        tk.Label(
            self.frame,
            text="DANH SÁCH MÀN CHƠI",
            font=("Segoe UI", 10, "bold"),
            bg=COLORS["bg_panel"],
            fg="#FBBF24",
        ).pack(anchor="w", pady=(0, 4))

        selector_container = tk.Frame(
            self.frame,
            bg=COLORS["menu_bg"],
            highlightthickness=1,
            highlightbackground=COLORS["menu_border"],
        )
        selector_container.pack(fill=tk.X, pady=(0, 10))

        self.level_list_canvas = tk.Canvas(
            selector_container,
            bg=COLORS["menu_bg"],
            height=220,
            highlightthickness=0,
            bd=0,
        )
        self.level_scrollbar = tk.Scrollbar(
            selector_container, orient=tk.VERTICAL, command=self.level_list_canvas.yview
        )
        self.level_items_frame = tk.Frame(self.level_list_canvas, bg=COLORS["menu_bg"])

        self.level_items_frame.bind(
            "<Configure>",
            lambda _e: self.level_list_canvas.configure(
                scrollregion=self.level_list_canvas.bbox("all")
            ),
        )
        self.level_canvas_window = self.level_list_canvas.create_window(
            (0, 0), window=self.level_items_frame, anchor="nw"
        )
        self.level_list_canvas.bind(
            "<Configure>",
            lambda e: self.level_list_canvas.itemconfig(self.level_canvas_window, width=e.width),
        )
        self.level_list_canvas.configure(yscrollcommand=self.level_scrollbar.set)

        self.level_list_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.level_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.level_list_canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _build_game_controls(self) -> None:
        ctrl_row = tk.Frame(self.frame, bg=COLORS["bg_panel"])
        ctrl_row.pack(fill=tk.X, pady=(2, 6))

        btn_restart = tk.Button(
            ctrl_row,
            text="🔄 Restart (R)",
            font=("Segoe UI", 9, "bold"),
            bg="#B45309",
            fg="white",
            activebackground="#D97706",
            activeforeground="white",
            relief=tk.FLAT,
            pady=5,
            cursor="hand2",
            command=self.on_restart,
        )
        btn_restart.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))

        btn_undo = tk.Button(
            ctrl_row,
            text="↩ Undo (Z)",
            font=("Segoe UI", 9, "bold"),
            bg="#374151",
            fg="white",
            activebackground="#4B5563",
            activeforeground="white",
            relief=tk.FLAT,
            pady=5,
            cursor="hand2",
            command=self.on_undo,
        )
        btn_undo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(3, 0))

        tk.Frame(self.frame, bg="#333333", height=1).pack(fill=tk.X, pady=6)

    def _build_solver_buttons(self) -> None:
        tk.Label(
            self.frame,
            text="AI SOLVERS",
            font=("Segoe UI", 10, "bold"),
            bg=COLORS["bg_panel"],
            fg="#FBBF24",
        ).pack(anchor="w", pady=(0, 4))

        solvers_grid = tk.Frame(self.frame, bg=COLORS["bg_panel"])
        solvers_grid.pack(fill=tk.X)

        solvers_cfg = [
            ("▶ Solve BFS", "BFS", "#15803D", 0, 0),
            ("▶ Solve DFS", "DFS", "#1D4ED8", 0, 1),
            ("▶ Solve UCS", "UCS", "#6D28D9", 1, 0),
            ("▶ Solve A*", "ASTAR", "#BE185D", 1, 1),
        ]
        solvers_grid.columnconfigure(0, weight=1)
        solvers_grid.columnconfigure(1, weight=1)

        for label, alg_code, color, r_idx, c_idx in solvers_cfg:
            btn = tk.Button(
                solvers_grid,
                text=label,
                font=("Segoe UI", 9, "bold"),
                bg=color,
                fg="white",
                relief=tk.FLAT,
                pady=5,
                cursor="hand2",
                command=lambda code=alg_code: self.on_run_solver(code),
            )
            btn.grid(
                row=r_idx,
                column=c_idx,
                sticky="ew",
                padx=(0 if c_idx == 0 else 3, 3 if c_idx == 0 else 0),
                pady=2,
            )

        tk.Frame(self.frame, bg="#333333", height=1).pack(fill=tk.X, pady=8)

    def _build_metrics_section(self) -> None:
        tk.Label(
            self.frame,
            text="THỐNG KÊ SOLVER",
            font=("Segoe UI", 9, "bold"),
            bg=COLORS["bg_panel"],
            fg="#FBBF24",
        ).pack(anchor="w")

        self.lbl_metrics = tk.Label(
            self.frame,
            text="Thuật toán: -\nThời gian:  -\nBộ nhớ đỉnh: -\nNút mở rộng: -\nSố bước giải: -",
            font=("Consolas", 9),
            bg="#111111",
            fg="#E5E7EB",
            justify=tk.LEFT,
            anchor="nw",
            padx=8,
            pady=5,
        )
        self.lbl_metrics.pack(fill=tk.X, pady=(3, 6))

        tk.Label(
            self.frame,
            text="Chuỗi bước đi (Solution Path):",
            font=("Segoe UI", 8, "bold"),
            bg=COLORS["bg_panel"],
            fg=COLORS["fg_sub"],
        ).pack(anchor="w")

        self.txt_solution = tk.Text(
            self.frame,
            height=4,
            font=("Consolas", 9),
            bg="#111111",
            fg="#38BDF8",
            wrap=tk.WORD,
            relief=tk.FLAT,
            padx=6,
            pady=4,
            state=tk.DISABLED,
        )
        self.txt_solution.pack(fill=tk.BOTH, expand=True, pady=(2, 4))

    def _on_mousewheel(self, event: tk.Event) -> None:
        widget = self.root.winfo_containing(event.x_root, event.y_root)
        if widget is not None and str(widget).startswith(str(self.level_list_canvas)):
            self.level_list_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def rebuild_level_selector(
        self,
        level_paths: List[str],
        level_titles: Dict[str, str],
        current_level_path: Optional[str],
    ) -> None:
        for child in self.level_items_frame.winfo_children():
            child.destroy()

        if not level_paths:
            empty_lbl = tk.Label(
                self.level_items_frame,
                text="  Chưa có file level (.json) trong thư mục levels/.",
                font=("Segoe UI", 9),
                bg=COLORS["menu_bg"],
                fg="#F87171",
                justify=tk.LEFT,
                anchor="w",
                pady=12,
            )
            empty_lbl.pack(fill=tk.X)
            return

        for path in level_paths:
            is_current = path == current_level_path
            title = level_titles.get(path, os.path.basename(path))

            bg_col = COLORS["menu_active_bg"] if is_current else COLORS["menu_bg"]
            fg_col = "#FFFFFF" if is_current else "#E5E7EB"
            icon_txt = "▶" if is_current else "•"
            icon_col = "#60A5FA" if is_current else "#6B7280"
            font_style = ("Segoe UI", 10, "bold") if is_current else ("Segoe UI", 10)

            row_frame = tk.Frame(
                self.level_items_frame,
                bg=bg_col,
                padx=10,
                pady=7,
                cursor="hand2",
            )
            row_frame.pack(fill=tk.X)

            icon_lbl = tk.Label(
                row_frame,
                text=icon_txt,
                font=("Segoe UI Symbol", 9, "bold"),
                bg=bg_col,
                fg=icon_col,
                cursor="hand2",
            )
            icon_lbl.pack(side=tk.LEFT, padx=(0, 8))

            text_lbl = tk.Label(
                row_frame,
                text=title,
                font=font_style,
                bg=bg_col,
                fg=fg_col,
                anchor="w",
                cursor="hand2",
            )
            text_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

            widgets = (row_frame, icon_lbl, text_lbl)

            def on_enter(
                _e: tk.Event,
                rf: tk.Frame = row_frame,
                il: tk.Label = icon_lbl,
                tl: tk.Label = text_lbl,
            ) -> None:
                for w in (rf, il, tl):
                    w.config(bg=COLORS["menu_hover_bg"])
                tl.config(fg="#FFFFFF")

            def on_leave(
                _e: tk.Event,
                rf: tk.Frame = row_frame,
                il: tk.Label = icon_lbl,
                tl: tk.Label = text_lbl,
                default_bg: str = bg_col,
                default_fg: str = fg_col,
            ) -> None:
                for w in (rf, il, tl):
                    w.config(bg=default_bg)
                tl.config(fg=default_fg)

            def on_click(_e: tk.Event, target_path: str = path) -> None:
                if target_path != current_level_path:
                    self.on_select_level(target_path)

            for w in widgets:
                w.bind("<Enter>", on_enter)
                w.bind("<Leave>", on_leave)
                w.bind("<Button-1>", on_click)

    def update_solver_metrics(self, result: Dict[str, Any], alg_code: str, actions_len: int) -> None:
        self.lbl_metrics.config(
            text=(
                f"Thuật toán: {result.get('algorithm', alg_code)}\n"
                f"Thời gian:  {result.get('time_sec', 0.0) * 1000:.2f} ms\n"
                f"Bộ nhớ đỉnh: {result.get('memory_kb', 0.0):.2f} KB\n"
                f"Nút mở rộng: {result.get('expanded_nodes', 0)}\n"
                f"Số bước giải: {actions_len}"
            )
        )

    def set_solution_text(self, text: str) -> None:
        self.txt_solution.config(state=tk.NORMAL)
        self.txt_solution.delete("1.0", tk.END)
        self.txt_solution.insert(tk.END, text)
        self.txt_solution.config(state=tk.DISABLED)
