# state.py
from typing import Tuple, Optional, FrozenSet


class Orientation:
    """Định nghĩa 4 trạng thái định hướng của khối trong Bloxorz."""
    STANDING = "STANDING"                 # Đứng thẳng 1x1x2 trên 1 ô (r, c)
    LYING_HORIZONTAL = "LYING_HORIZONTAL" # Nằm ngang trên 2 ô (r, c) và (r, c+1)
    LYING_VERTICAL = "LYING_VERTICAL"     # Nằm dọc trên 2 ô (r, c) và (r+1, c)
    SPLIT = "SPLIT"                       # Tách thành 2 khối 1x1x1 tại pos1 và pos2


class Action:
    """Các hành động hợp lệ trong trò chơi."""
    UP = "UP"
    DOWN = "DOWN"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    SPACE = "SPACE"  # Đổi khối điều khiển khi đang ở trạng thái SPLIT

    DIRECTIONAL = (UP, DOWN, LEFT, RIGHT)
    ALL = (UP, DOWN, LEFT, RIGHT, SPACE)


class GameState:
    """
    Biểu diễn trạng thái hoàn chỉnh và bất biến (immutable) của trò chơi Bloxorz.
    Hỗ trợ đầy đủ __hash__ và __eq__ để lưu vào tập visited (set/dict) khi chạy AI Solver.
    
    Quy ước tọa độ chuẩn hóa:
    - STANDING: pos1 = (r, c), pos2 = None, active_cube = 0
    - LYING_HORIZONTAL: pos1 = (r, c) (ô bên trái, chiếm thêm (r, c+1)), pos2 = None, active_cube = 0
    - LYING_VERTICAL: pos1 = (r, c) (ô bên trên, chiếm thêm (r+1, c)), pos2 = None, active_cube = 0
    - SPLIT: pos1 = (r1, c1), pos2 = (r2, c2), active_cube = 0 (điều khiển pos1) hoặc 1 (điều khiển pos2)
    """

    __slots__ = ("pos1", "orientation", "pos2", "active_cube", "bridges_status", "_hash")

    def __init__(
        self,
        pos1: Tuple[int, int],
        orientation: str,
        bridges_status: FrozenSet[Tuple[Tuple[int, int], bool]],
        pos2: Optional[Tuple[int, int]] = None,
        active_cube: int = 0
    ):
        if orientation != Orientation.SPLIT:
            pos2 = None
            active_cube = 0

        object.__setattr__(self, "pos1", (int(pos1[0]), int(pos1[1])))
        object.__setattr__(self, "orientation", orientation)
        object.__setattr__(
            self,
            "pos2",
            (int(pos2[0]), int(pos2[1])) if pos2 is not None else None
        )
        object.__setattr__(self, "active_cube", int(active_cube))
        object.__setattr__(self, "bridges_status", frozenset(bridges_status))
        object.__setattr__(
            self,
            "_hash",
            hash((self.pos1, self.orientation, self.pos2, self.active_cube, self.bridges_status))
        )

    def __setattr__(self, key, value):
        raise AttributeError("GameState là đối tượng bất biến (immutable), không thể sửa đổi trực tiếp.")

    def __hash__(self) -> int:
        return self._hash

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, GameState):
            return False
        return (
            self._hash == other._hash
            and self.pos1 == other.pos1
            and self.orientation == other.orientation
            and self.pos2 == other.pos2
            and self.active_cube == other.active_cube
            and self.bridges_status == other.bridges_status
        )

    def __repr__(self) -> str:
        if self.orientation == Orientation.SPLIT:
            return (
                f"GameState(SPLIT, pos1={self.pos1}, pos2={self.pos2}, "
                f"active={self.active_cube}, bridges={dict(self.bridges_status)})"
            )
        return (
            f"GameState({self.orientation}, pos={self.pos1}, "
            f"bridges={dict(self.bridges_status)})"
        )

    def get_occupied_cells(self) -> Tuple[Tuple[int, int], ...]:
        """Trả về danh sách các tọa độ (r, c) mà khối đang chiếm giữ trên bàn cờ."""
        r, c = self.pos1
        if self.orientation == Orientation.STANDING:
            return ((r, c),)
        elif self.orientation == Orientation.LYING_HORIZONTAL:
            return ((r, c), (r, c + 1))
        elif self.orientation == Orientation.LYING_VERTICAL:
            return ((r, c), (r + 1, c))
        elif self.orientation == Orientation.SPLIT and self.pos2 is not None:
            return (self.pos1, self.pos2)
        return ((r, c),)

    def is_bridge_open(self, cell: Tuple[int, int]) -> bool:
        """Kiểm tra trạng thái mở (True) hay đóng (False) của một ô cầu."""
        for b_pos, is_open in self.bridges_status:
            if b_pos == cell:
                return is_open
        return False