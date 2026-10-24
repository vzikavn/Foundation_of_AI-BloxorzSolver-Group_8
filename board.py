# board.py
import json
import os
import re
from typing import List, Tuple, Dict, Optional
from state import GameState, Orientation, Action


class TileType:
    """Mã định danh các loại ô trên lưới bàn cờ."""
    VOID = 0          # Ô trống (rơi ra ngoài là thua)
    FLOOR = 1         # Ô sàn thường
    GOAL = 2          # Ô đích (chỉ thắng khi khối 1x1x2 STANDING trên ô này)
    FRAGILE = 3       # Ô gạch cam dễ vỡ (vỡ nếu khối 1x1x2 STANDING đè lên)
    BRIDGE = 4        # Ô cầu (đóng = VOID, mở = FLOOR)
    SOFT_SWITCH = 5   # Công tắc mềm (hình tròn - chạm bất kỳ phần nào cũng kích hoạt)
    HEAVY_SWITCH = 6  # Công tắc nặng (hình chữ X - chỉ kích hoạt khi 1x1x2 STANDING)
    SPLIT_SWITCH = 7  # Công tắc phân tách (hình () - tách thành 2 khối 1x1x1 khi STANDING)


class SwitchConfig:
    """Lưu cấu hình chi tiết của một công tắc trong màn chơi."""
    def __init__(
        self,
        pos: Tuple[int, int],
        switch_type: str,
        mode: str = "toggle",
        bridges: Optional[List[Tuple[int, int]]] = None,
        target_state: bool = True,
        split_positions: Optional[Tuple[Tuple[int, int], Tuple[int, int]]] = None
    ):
        self.pos = (int(pos[0]), int(pos[1]))
        self.switch_type = switch_type.lower()  # "soft", "heavy", "split"
        self.mode = mode.lower()                # "toggle" hoặc "permanent"
        self.bridges = [(int(b[0]), int(b[1])) for b in (bridges or [])]
        self.target_state = bool(target_state)
        self.split_positions = (
            ((int(split_positions[0][0]), int(split_positions[0][1])),
             (int(split_positions[1][0]), int(split_positions[1][1])))
            if split_positions else None
        )


class Board:
    """
    Quản lý cấu trúc bàn cờ, tải màn chơi từ JSON và cung cấp hàm chuyển trạng thái
    cho cả người chơi thủ công lẫn các thuật toán tìm kiếm AI.
    """

    def __init__(
        self,
        name: str,
        grid: List[List[int]],
        start: Tuple[int, int],
        goal: Tuple[int, int],
        initial_bridges: Dict[Tuple[int, int], bool],
        switches: Dict[Tuple[int, int], SwitchConfig]
    ):
        self.name = name
        self.grid = grid
        self.rows = len(grid)
        self.cols = len(grid[0]) if self.rows > 0 else 0
        self.start = (int(start[0]), int(start[1]))
        self.goal = (int(goal[0]), int(goal[1]))
        self.initial_bridges = initial_bridges
        self.switches = switches

    @classmethod
    def from_json(cls, filepath: str) -> "Board":
        """Đọc và khởi tạo đối tượng Board từ file JSON do người dùng thiết kế."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        name = data.get("name", os.path.splitext(os.path.basename(filepath))[0])
        grid = data["grid"]
        start = tuple(data["start"])
        goal = tuple(data["goal"])

        initial_bridges: Dict[Tuple[int, int], bool] = {}
        for key, status in data.get("bridges", {}).items():
            r_str, c_str = key.split(",")
            initial_bridges[(int(r_str.strip()), int(c_str.strip()))] = bool(status)

        switches: Dict[Tuple[int, int], SwitchConfig] = {}
        for sw in data.get("switches", []):
            pos = (int(sw["pos"][0]), int(sw["pos"][1]))
            sw_cfg = SwitchConfig(
                pos=pos,
                switch_type=sw["type"],
                mode=sw.get("mode", "toggle"),
                bridges=sw.get("bridges", []),
                target_state=sw.get("target_state", True),
                split_positions=sw.get("split_positions", None)
            )
            switches[pos] = sw_cfg

        return cls(name, grid, start, goal, initial_bridges, switches)

    def get_initial_state(self) -> GameState:
        """Trả về trạng thái khởi đầu của màn chơi."""
        bridges_frozenset = frozenset(self.initial_bridges.items())
        return GameState(
            pos1=self.start,
            orientation=Orientation.STANDING,
            bridges_status=bridges_frozenset
        )

    def is_goal(self, state: GameState) -> bool:
        """
        Kiểm tra điều kiện Thắng:
        Khối 1x1x2 phải ở trạng thái STANDING ngay trên ô đích (goal).
        """
        return (
            state.orientation == Orientation.STANDING
            and state.pos1 == self.goal
        )

    def get_tile(self, r: int, c: int) -> int:
        """Lấy loại ô tại tọa độ (r, c). Nếu ngoài biên trả về VOID."""
        if 0 <= r < self.rows and 0 <= c < self.cols:
            return self.grid[r][c]
        return TileType.VOID

    def is_cell_supported(
        self,
        r: int,
        c: int,
        bridges_dict: Dict[Tuple[int, int], bool]
    ) -> bool:
        """Kiểm tra một ô có nâng đỡ được khối hay không (không phải VOID hoặc cầu đang đóng)."""
        tile = self.get_tile(r, c)
        if tile == TileType.VOID:
            return False
        if tile == TileType.BRIDGE or (r, c) in bridges_dict:
            return bridges_dict.get((r, c), False)
        return True

    def _compute_raw_roll(
        self,
        state: GameState,
        action: str
    ) -> Tuple[Tuple[int, int], str, Optional[Tuple[int, int]], int, Tuple[Tuple[int, int], ...]]:
        """
        Tính toán vị trí và hướng mới sau khi lăn theo hướng `action` (chưa xét công tắc phân tách).
        Trả về: (new_pos1, new_orientation, new_pos2, new_active_cube, newly_pressed_cells)
        """
        r, c = state.pos1
        ori = state.orientation

        if ori == Orientation.STANDING:
            if action == Action.UP:
                new_pos1, new_ori = (r - 2, c), Orientation.LYING_VERTICAL
                pressed = ((r - 2, c), (r - 1, c))
            elif action == Action.DOWN:
                new_pos1, new_ori = (r + 1, c), Orientation.LYING_VERTICAL
                pressed = ((r + 1, c), (r + 2, c))
            elif action == Action.LEFT:
                new_pos1, new_ori = (r, c - 2), Orientation.LYING_HORIZONTAL
                pressed = ((r, c - 2), (r, c - 1))
            elif action == Action.RIGHT:
                new_pos1, new_ori = (r, c + 1), Orientation.LYING_HORIZONTAL
                pressed = ((r, c + 1), (r, c + 2))
            else:
                return state.pos1, ori, None, 0, ()
            return new_pos1, new_ori, None, 0, pressed

        elif ori == Orientation.LYING_HORIZONTAL:
            if action == Action.LEFT:
                new_pos1, new_ori = (r, c - 1), Orientation.STANDING
                pressed = ((r, c - 1),)
            elif action == Action.RIGHT:
                new_pos1, new_ori = (r, c + 2), Orientation.STANDING
                pressed = ((r, c + 2),)
            elif action == Action.UP:
                new_pos1, new_ori = (r - 1, c), Orientation.LYING_HORIZONTAL
                pressed = ((r - 1, c), (r - 1, c + 1))
            elif action == Action.DOWN:
                new_pos1, new_ori = (r + 1, c), Orientation.LYING_HORIZONTAL
                pressed = ((r + 1, c), (r + 1, c + 1))
            else:
                return state.pos1, ori, None, 0, ()
            return new_pos1, new_ori, None, 0, pressed

        elif ori == Orientation.LYING_VERTICAL:
            if action == Action.UP:
                new_pos1, new_ori = (r - 1, c), Orientation.STANDING
                pressed = ((r - 1, c),)
            elif action == Action.DOWN:
                new_pos1, new_ori = (r + 2, c), Orientation.STANDING
                pressed = ((r + 2, c),)
            elif action == Action.LEFT:
                new_pos1, new_ori = (r, c - 1), Orientation.LYING_VERTICAL
                pressed = ((r, c - 1), (r + 1, c - 1))
            elif action == Action.RIGHT:
                new_pos1, new_ori = (r, c + 1), Orientation.LYING_VERTICAL
                pressed = ((r, c + 1), (r + 1, c + 1))
            else:
                return state.pos1, ori, None, 0, ()
            return new_pos1, new_ori, None, 0, pressed

        elif ori == Orientation.SPLIT and state.pos2 is not None:
            if action == Action.SPACE:
                return state.pos1, Orientation.SPLIT, state.pos2, 1 - state.active_cube, ()

            dr, dc = 0, 0
            if action == Action.UP:
                dr = -1
            elif action == Action.DOWN:
                dr = 1
            elif action == Action.LEFT:
                dc = -1
            elif action == Action.RIGHT:
                dc = 1

            if state.active_cube == 0:
                moved_pos = (state.pos1[0] + dr, state.pos1[1] + dc)
                other_pos = state.pos2
                new_pos1, new_pos2 = moved_pos, other_pos
            else:
                moved_pos = (state.pos2[0] + dr, state.pos2[1] + dc)
                other_pos = state.pos1
                new_pos1, new_pos2 = other_pos, moved_pos

            pressed = (moved_pos,)

            # Tự động gộp lại khi 2 khối 1x1x1 di chuyển đến 2 ô liền kề nhau
            r1, c1 = new_pos1
            r2, c2 = new_pos2
            if r1 == r2 and abs(c1 - c2) == 1:
                merged_pos = (r1, min(c1, c2))
                return merged_pos, Orientation.LYING_HORIZONTAL, None, 0, pressed
            elif c1 == c2 and abs(r1 - r2) == 1:
                merged_pos = (min(r1, r2), c1)
                return merged_pos, Orientation.LYING_VERTICAL, None, 0, pressed

            return new_pos1, Orientation.SPLIT, new_pos2, state.active_cube, pressed

        return state.pos1, ori, state.pos2, state.active_cube, ()

    def _activate_bridge_switch(
        self,
        sw: SwitchConfig,
        bridges_dict: Dict[Tuple[int, int], bool]
    ) -> None:
        """Cập nhật trạng thái đóng/mở của các cầu liên kết với công tắc."""
        for b_pos in sw.bridges:
            if sw.mode == "toggle":
                bridges_dict[b_pos] = not bridges_dict.get(b_pos, False)
            elif sw.mode == "permanent":
                bridges_dict[b_pos] = sw.target_state

    def simulate_move(
        self,
        state: GameState,
        action: str
    ) -> Tuple[Optional[GameState], str]:
        """Mô phỏng một bước di chuyển từ `state` với hành động `action`."""
        if action == Action.SPACE:
            if state.orientation != Orientation.SPLIT:
                return None, "INVALID_SPACE"
            next_state = GameState(
                pos1=state.pos1,
                orientation=Orientation.SPLIT,
                bridges_status=state.bridges_status,
                pos2=state.pos2,
                active_cube=1 - state.active_cube
            )
            return next_state, "OK"

        if action not in Action.DIRECTIONAL:
            return None, "INVALID_ACTION"

        new_pos1, new_ori, new_pos2, new_active, pressed_cells = self._compute_raw_roll(state, action)
        bridges_dict = dict(state.bridges_status)

        if new_ori == Orientation.STANDING:
            occupied = (new_pos1,)
        elif new_ori == Orientation.LYING_HORIZONTAL:
            occupied = (new_pos1, (new_pos1[0], new_pos1[1] + 1))
        elif new_ori == Orientation.LYING_VERTICAL:
            occupied = (new_pos1, (new_pos1[0] + 1, new_pos1[1]))
        else:
            occupied = (new_pos1, new_pos2)

        # 1. Kiểm tra rơi xuống Void hoặc cầu đang đóng
        for (r, c) in occupied:
            if not self.is_cell_supported(r, c, bridges_dict):
                return None, "VOID"

        # 2. Kiểm tra ô Fragile
        if new_ori == Orientation.STANDING:
            r, c = new_pos1
            if self.get_tile(r, c) == TileType.FRAGILE:
                return None, "FRAGILE"

        # 3. Kiểm tra kích hoạt công tắc
        for cell in pressed_cells:
            if cell in self.switches:
                sw = self.switches[cell]
                if sw.switch_type == "soft":
                    self._activate_bridge_switch(sw, bridges_dict)
                elif sw.switch_type == "heavy":
                    if new_ori == Orientation.STANDING:
                        self._activate_bridge_switch(sw, bridges_dict)
                elif sw.switch_type == "split":
                    if new_ori == Orientation.STANDING and sw.split_positions is not None:
                        sp1, sp2 = sw.split_positions
                        if (
                            not self.is_cell_supported(sp1[0], sp1[1], bridges_dict)
                            or not self.is_cell_supported(sp2[0], sp2[1], bridges_dict)
                        ):
                            return None, "VOID"
                        new_pos1, new_pos2 = sp1, sp2
                        new_ori = Orientation.SPLIT
                        new_active = 0
                        for sp in (sp1, sp2):
                            if sp in self.switches and self.switches[sp].switch_type == "soft":
                                self._activate_bridge_switch(self.switches[sp], bridges_dict)

        # 4. Đảm bảo khối vẫn được nâng đỡ sau khi cầu đổi trạng thái
        final_occupied = (
            (new_pos1, new_pos2)
            if new_ori == Orientation.SPLIT
            else occupied
        )
        for (r, c) in final_occupied:
            if not self.is_cell_supported(r, c, bridges_dict):
                return None, "VOID"

        next_state = GameState(
            pos1=new_pos1,
            orientation=new_ori,
            bridges_status=frozenset(bridges_dict.items()),
            pos2=new_pos2,
            active_cube=new_active
        )

        if self.is_goal(next_state):
            return next_state, "WIN"
        return next_state, "OK"

    def get_valid_moves(self, state: GameState) -> List[Tuple[str, GameState]]:
        """Trả về danh sách các cặp (action, next_state) hợp lệ từ trạng thái `state`."""
        valid_moves: List[Tuple[str, GameState]] = []
        candidate_actions = (
            Action.ALL if state.orientation == Orientation.SPLIT else Action.DIRECTIONAL
        )

        for action in candidate_actions:
            next_state, status = self.simulate_move(state, action)
            if next_state is not None and status in ("OK", "WIN"):
                valid_moves.append((action, next_state))

        return valid_moves


def _natural_sort_key(path: str):
    """Hỗ trợ sắp xếp tên file theo thứ tự tự nhiên (ví dụ: level1, level2, ..., level10)."""
    basename = os.path.basename(path)
    return [
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", basename)
    ]


def discover_levels(levels_dir: str = "levels") -> List[str]:
    """
    Quét thư mục `levels_dir` để lấy danh sách tất cả các file .json do người dùng đưa vào.
    Không tự tạo bất kỳ file mẫu nào.
    """
    if not os.path.isdir(levels_dir):
        return []

    paths = [
        os.path.join(levels_dir, fname)
        for fname in os.listdir(levels_dir)
        if fname.lower().endswith(".json") and os.path.isfile(os.path.join(levels_dir, fname))
    ]
    paths.sort(key=_natural_sort_key)
    return paths