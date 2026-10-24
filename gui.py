# gui.py
import os
import tkinter as tk
from tkinter import messagebox
from typing import Any, Callable, Dict, List, Optional, Tuple

from board import Board
import solver
from state import Action, GameState, Orientation
from ui import (
    BloxorzRenderer,
    COLORS,
    ControlPanel,
    DEFAULT_REPLAY_SPEED_MS,
    FALL_FRAMES,
    FRAME_MS,
    ROLL_FRAMES,
    SINK_FRAMES,
)


class BloxorzGUI:
    """
    Bộ điều phối trung tâm (Controller) của ứng dụng Bloxorz 2.5D:
    - Kết nối dữ liệu màn chơi (Board, GameState) với BloxorzRenderer và ControlPanel trong package `ui`.
    - Quản lý sự kiện bàn phím, Undo/Restart, Animation 3D (ROLL, SINK, FALL)
      và chạy Replay lời giải từ AI Solver ở tốc độ cố định 250 ms/bước.
    """

    def __init__(self, root: tk.Tk, level_paths: List[str], levels_dir: str = "levels") -> None:
        self.root = root
        self.root.title("Bloxorz 2.5D - AI Solver Framework")
        self.root.geometry("1160x700")
        self.root.minsize(980, 620)
        self.root.configure(bg=COLORS["bg_root"])

        self.levels_dir = levels_dir
        self.level_paths: List[str] = list(level_paths)
        self.level_titles: Dict[str, str] = {}
        self.current_level_path: Optional[str] = self.level_paths[0] if self.level_paths else None

        if self.current_level_path and os.path.isfile(self.current_level_path):
            self.board = Board.from_json(self.current_level_path)
        else:
            self.board = self._create_empty_placeholder_board()

        self.state: GameState = self.board.get_initial_state()
        self.history: List[Tuple[GameState, int]] = []
        self.move_count: int = 0
        self.game_status: str = "PLAYING"
        self.loss_reason: str = ""
        self.failed_cells: Tuple[Tuple[int, int], ...] = ()

        # Tốc độ lăn Replay mặc định 250 ms
        self.is_animating: bool = False
        self.anim_after_id: Optional[str] = None
        self.anim_speed_ms: int = DEFAULT_REPLAY_SPEED_MS

        # Quản lý Animation 3D (ROLL, SINK, FALL)
        self.transition_after_id: Optional[str] = None
        self.anim_state: Optional[Dict[str, Any]] = None
        self.broken_fragile_cell: Optional[Tuple[int, int]] = None

        self._refresh_level_metadata()
        self._build_layout()
        self._bind_keys()

        if self.current_level_path:
            self.load_level(self.current_level_path)
        else:
            self.panel.rebuild_level_selector(
                self.level_paths, self.level_titles, self.current_level_path
            )
            self.draw()

    @staticmethod
    def _create_empty_placeholder_board() -> Board:
        return Board(
            name="Chưa có file Level JSON",
            grid=[[1, 1, 2]],
            start=(0, 0),
            goal=(0, 2),
            initial_bridges={},
            switches={},
        )

    def _refresh_level_metadata(self) -> None:
        self.level_titles.clear()
        for path in self.level_paths:
            try:
                b = Board.from_json(path)
                self.level_titles[path] = b.name
            except Exception:
                self.level_titles[path] = os.path.basename(path)

    def _build_layout(self) -> None:
        main_frame = tk.Frame(self.root, bg=COLORS["bg_root"])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left_frame = tk.Frame(main_frame, bg=COLORS["bg_root"])
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(
            left_frame,
            width=820,
            height=580,
            bg="#3B0700",
            highlightthickness=1,
            highlightbackground="#333333",
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", lambda _event: self.draw())

        ControlPanel.build_legend_bar(left_frame)

        self.renderer = BloxorzRenderer(self.canvas)
        self.panel = ControlPanel(
            parent=main_frame,
            root=self.root,
            on_select_level=self.load_level,
            on_restart=self.restart_level,
            on_undo=self.undo_move,
            on_run_solver=self.run_solver,
        )

    def _bind_keys(self) -> None:
        key_map = {
            "<Up>": Action.UP, "<w>": Action.UP, "<W>": Action.UP,
            "<Down>": Action.DOWN, "<s>": Action.DOWN, "<S>": Action.DOWN,
            "<Left>": Action.LEFT, "<a>": Action.LEFT, "<A>": Action.LEFT,
            "<Right>": Action.RIGHT, "<d>": Action.RIGHT, "<D>": Action.RIGHT,
            "<space>": Action.SPACE,
        }
        for key_seq, act in key_map.items():
            self.root.bind(key_seq, lambda _event, a=act: self.handle_manual_action(a))

        self.root.bind("<r>", lambda _event: self.restart_level())
        self.root.bind("<R>", lambda _event: self.restart_level())
        self.root.bind("<z>", lambda _event: self.undo_move())
        self.root.bind("<Z>", lambda _event: self.undo_move())
        self.root.bind("<BackSpace>", lambda _event: self.undo_move())

    def stop_animation(self) -> None:
        if self.anim_after_id is not None:
            self.root.after_cancel(self.anim_after_id)
            self.anim_after_id = None
        if self.transition_after_id is not None:
            self.root.after_cancel(self.transition_after_id)
            self.transition_after_id = None
        self.is_animating = False
        self.anim_state = None

    def load_level(self, filepath: str) -> None:
        self.stop_animation()
        try:
            self.board = Board.from_json(filepath)
            self.current_level_path = filepath
            if filepath not in self.level_paths:
                self.level_paths.append(filepath)
            self.level_titles[filepath] = self.board.name

            self.panel.rebuild_level_selector(
                self.level_paths, self.level_titles, self.current_level_path
            )
            self.restart_level()
            self.panel.set_solution_text("Chưa chạy Solver.")
        except Exception as e:
            messagebox.showerror("Lỗi tải màn chơi", f"Không thể đọc file JSON:\n{e}")

    def restart_level(self) -> None:
        self.stop_animation()
        self.state = self.board.get_initial_state()
        self.history.clear()
        self.move_count = 0
        self.game_status = "PLAYING"
        self.loss_reason = ""
        self.failed_cells = ()
        self.broken_fragile_cell = None
        self.draw()

    def undo_move(self) -> None:
        if self.is_animating or self.anim_state is not None or not self.history:
            return
        self.state, self.move_count = self.history.pop()
        self.game_status = "PLAYING"
        self.loss_reason = ""
        self.failed_cells = ()
        self.broken_fragile_cell = None
        self.draw()

    def handle_manual_action(self, action: str) -> None:
        if self.is_animating or self.anim_state is not None or self.game_status != "PLAYING":
            return
        self._step_action(action)

    @staticmethod
    def _get_box_bounds(
        pos: Tuple[int, int], ori: str
    ) -> Tuple[float, float, float, float, float, float]:
        r, c = float(pos[0]), float(pos[1])
        if ori == Orientation.STANDING:
            return (r, c, r + 1.0, c + 1.0, 0.0, 2.0)
        elif ori == Orientation.LYING_HORIZONTAL:
            return (r, c, r + 1.0, c + 2.0, 0.0, 1.0)
        elif ori == Orientation.LYING_VERTICAL:
            return (r, c, r + 2.0, c + 1.0, 0.0, 1.0)
        return (r, c, r + 1.0, c + 1.0, 0.0, 1.0)

    def _compute_fall_tip_direction(
        self,
        raw_pos1: Tuple[int, int],
        raw_ori: str,
        raw_pos2: Optional[Tuple[int, int]],
        active_cube: int,
        action: str,
        bridges_dict: Dict[Tuple[int, int], bool],
    ) -> Tuple[str, Tuple[int, int]]:
        if raw_ori == Orientation.LYING_HORIZONTAL:
            c_left = raw_pos1
            c_right = (raw_pos1[0], raw_pos1[1] + 1)
            sup_left = self.board.is_cell_supported(c_left[0], c_left[1], bridges_dict)
            sup_right = self.board.is_cell_supported(c_right[0], c_right[1], bridges_dict)
            if sup_left and not sup_right:
                return Action.RIGHT, c_right
            if sup_right and not sup_left:
                return Action.LEFT, c_left
        elif raw_ori == Orientation.LYING_VERTICAL:
            c_top = raw_pos1
            c_bot = (raw_pos1[0] + 1, raw_pos1[1])
            sup_top = self.board.is_cell_supported(c_top[0], c_top[1], bridges_dict)
            sup_bot = self.board.is_cell_supported(c_bot[0], c_bot[1], bridges_dict)
            if sup_top and not sup_bot:
                return Action.DOWN, c_bot
            if sup_bot and not sup_top:
                return Action.UP, c_top
        elif raw_ori == Orientation.SPLIT and raw_pos2 is not None:
            moved = raw_pos1 if active_cube == 0 else raw_pos2
            return action, moved

        return action, raw_pos1

    def _step_action(self, action: str, on_complete: Optional[Callable[[], None]] = None) -> None:
        if action == Action.SPACE and self.state.orientation != Orientation.SPLIT:
            if on_complete:
                on_complete()
            return

        prev_state = self.state
        self.history.append((prev_state, self.move_count))
        next_state, status = self.board.simulate_move(prev_state, action)

        if action == Action.SPACE:
            if next_state is not None:
                self.state = next_state
            self.draw()
            if on_complete:
                on_complete()
            return

        self.move_count += 1

        if prev_state.orientation == Orientation.SPLIT and prev_state.pos2 is not None:
            active_idx = prev_state.active_cube
            moving_pos = prev_state.pos1 if active_idx == 0 else prev_state.pos2
            static_pos: Optional[Tuple[int, int]] = (
                prev_state.pos2 if active_idx == 0 else prev_state.pos1
            )
            start_box = (
                float(moving_pos[0]), float(moving_pos[1]),
                float(moving_pos[0] + 1), float(moving_pos[1] + 1),
                0.0, 1.0,
            )
        else:
            static_pos = None
            start_box = self._get_box_bounds(prev_state.pos1, prev_state.orientation)

        roll_frames = max(4, min(ROLL_FRAMES, int(self.anim_speed_ms / (FRAME_MS * 1.6))))

        self.anim_state = {
            "phase": "ROLL",
            "action": action,
            "start_box": start_box,
            "static_pos": static_pos,
            "active_cube": prev_state.active_cube,
            "is_split": prev_state.orientation == Orientation.SPLIT,
            "step": 0,
            "total_steps": roll_frames,
            "next_state": next_state,
            "status": status,
            "prev_state": prev_state,
            "on_complete": on_complete,
        }
        self._tick_transition()

    def _tick_transition(self) -> None:
        if self.anim_state is None:
            return

        phase = self.anim_state["phase"]
        self.anim_state["step"] += 1
        step = self.anim_state["step"]
        total = self.anim_state["total_steps"]

        if phase == "ROLL":
            if step < total:
                self.draw()
                self.transition_after_id = self.root.after(FRAME_MS, self._tick_transition)
                return

            next_state: Optional[GameState] = self.anim_state["next_state"]
            status: str = self.anim_state["status"]
            prev_state: GameState = self.anim_state["prev_state"]
            action: str = self.anim_state["action"]
            on_complete: Optional[Callable[[], None]] = self.anim_state["on_complete"]

            if next_state is not None and status == "OK":
                self.state = next_state
                self.anim_state = None
                self.draw()
                if on_complete:
                    on_complete()
                return

            if next_state is not None and status == "WIN":
                self.state = next_state
                self.game_status = "WIN"
                self.anim_state = {
                    "phase": "SINK",
                    "step": 0,
                    "total_steps": SINK_FRAMES,
                    "on_complete": on_complete,
                }
                self.draw()
                self.transition_after_id = self.root.after(FRAME_MS, self._tick_transition)
                return

            raw_pos1, raw_ori, raw_pos2, _, _ = self.board._compute_raw_roll(prev_state, action)
            bridges_dict = dict(prev_state.bridges_status)

            if raw_ori == Orientation.STANDING:
                self.failed_cells = (raw_pos1,)
            elif raw_ori == Orientation.LYING_HORIZONTAL:
                self.failed_cells = (raw_pos1, (raw_pos1[0], raw_pos1[1] + 1))
            elif raw_ori == Orientation.LYING_VERTICAL:
                self.failed_cells = (raw_pos1, (raw_pos1[0] + 1, raw_pos1[1]))
            else:
                self.failed_cells = (raw_pos1, raw_pos2) if raw_pos2 else (raw_pos1,)

            if status == "FRAGILE":
                self.loss_reason = "THUA! Gạch mỏng (Fragile) bị vỡ khi đứng thẳng!"
                self.broken_fragile_cell = raw_pos1
            else:
                self.loss_reason = "THUA! Khối đã lăn rơi khỏi platform!"
                self.broken_fragile_cell = None

            tip_dir, primary_fall_cell = self._compute_fall_tip_direction(
                raw_pos1, raw_ori, raw_pos2, prev_state.active_cube, action, bridges_dict
            )

            if raw_ori == Orientation.SPLIT and raw_pos2 is not None:
                fall_pos = raw_pos1 if prev_state.active_cube == 0 else raw_pos2
                remain_pos: Optional[Tuple[int, int]] = (
                    raw_pos2 if prev_state.active_cube == 0 else raw_pos1
                )
                fall_box = (
                    float(fall_pos[0]), float(fall_pos[1]),
                    float(fall_pos[0] + 1), float(fall_pos[1] + 1),
                    0.0, 1.0,
                )
            else:
                remain_pos = None
                fall_box = self._get_box_bounds(raw_pos1, raw_ori)

            self.anim_state = {
                "phase": "FALL",
                "step": 0,
                "total_steps": FALL_FRAMES,
                "fall_box": fall_box,
                "remain_pos": remain_pos,
                "tip_dir": tip_dir,
                "primary_cell": primary_fall_cell,
                "status": status,
                "on_complete": on_complete,
            }
            self.draw()
            self.transition_after_id = self.root.after(FRAME_MS, self._tick_transition)
            return

        if phase in ("SINK", "FALL"):
            if step < total:
                self.draw()
                self.transition_after_id = self.root.after(FRAME_MS, self._tick_transition)
                return

            on_complete = self.anim_state["on_complete"]
            if phase == "FALL":
                self.game_status = "LOST"
            self.anim_state = None
            self.draw()
            if on_complete:
                on_complete()

    def run_solver(self, alg_code: str) -> None:
        self.restart_level()

        solver_map = {
            "BFS": solver.solve_bfs,
            "DFS": solver.solve_dfs,
            "UCS": solver.solve_ucs,
            "ASTAR": solver.solve_astar,
        }
        result = solver_map[alg_code](self.board, self.state)
        actions: List[str] = result.get("actions", [])

        self.panel.update_solver_metrics(result, alg_code, len(actions))

        if not actions:
            self.panel.set_solution_text("Không tìm thấy lời giải (hoặc chưa cài đặt).")
            messagebox.showinfo(
                "Thông báo Solver",
                f"Hàm {alg_code} chưa trả về danh sách bước đi.\n"
                "Hãy hoàn thiện phần TODO trong file solver.py!",
            )
            return

        self.panel.set_solution_text(" -> ".join(actions))
        self.is_animating = True
        self._animate_solution(actions, 0)

    def _animate_solution(self, actions: List[str], index: int) -> None:
        if not self.is_animating or index >= len(actions) or self.game_status != "PLAYING":
            self.is_animating = False
            self.draw()
            return

        def after_step() -> None:
            if not self.is_animating:
                return
            if self.game_status == "PLAYING" and index + 1 < len(actions):
                pause_ms = max(25, self.anim_speed_ms - ROLL_FRAMES * FRAME_MS)
                self.anim_after_id = self.root.after(
                    pause_ms,
                    lambda: self._animate_solution(actions, index + 1),
                )
            else:
                self.is_animating = False
                self.draw()

        self._step_action(actions[index], on_complete=after_step)

    def draw(self) -> None:
        self.renderer.render(
            board=self.board,
            state=self.state,
            game_status=self.game_status,
            move_count=self.move_count,
            loss_reason=self.loss_reason,
            failed_cells=self.failed_cells,
            broken_fragile_cell=self.broken_fragile_cell,
            is_animating=self.is_animating,
            anim_state=self.anim_state,
        )