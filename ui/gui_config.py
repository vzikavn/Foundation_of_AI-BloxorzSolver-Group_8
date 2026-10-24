# ui/gui_config.py
from typing import Dict, Tuple

Point2D = Tuple[float, float]
Point3D = Tuple[float, float, float]

# Hệ trục chiếu 2.5D
VEC_C: Point2D = (46.0, -10.5)
VEC_R: Point2D = (16.0, 28.0)
VEC_Z: Point2D = (0.0, -40.0)
TILE_THICKNESS: float = 0.22

# Vector hướng nhìn của Camera trong hệ trục (r, c, z) dùng cho Painter's Algorithm
CAM_VEC: Point3D = (46.0, -16.0, 36.4)

# Cấu hình thời gian Animation (~60 FPS) & Tốc độ Replay mặc định 250 ms
FRAME_MS: int = 16
ROLL_FRAMES: int = 9
SINK_FRAMES: int = 14
FALL_FRAMES: int = 18
DEFAULT_REPLAY_SPEED_MS: int = 250

# Bảng màu giao diện và vật liệu 3D
COLORS: Dict[str, str] = {
    "bg_root": "#141414",
    "bg_panel": "#1B1B1B",
    "menu_bg": "#202020",
    "menu_header": "#181818",
    "menu_active_bg": "#2B2B2B",
    "menu_hover_bg": "#383838",
    "menu_border": "#333333",
    "fg_text": "#F1F5F9",
    "fg_sub": "#9CA3AF",
    # Màu gạch sàn thường
    "floor_top": "#D6D9DF",
    "floor_left": "#737A86",
    "floor_front": "#98A0AC",
    "floor_border": "#4A505A",
    # Màu gạch mỏng dễ vỡ (Fragile)
    "fragile_top": "#F97316",
    "fragile_left": "#9A3412",
    "fragile_front": "#C2410C",
    "fragile_inner": "#FFEDD5",
    # Màu cầu (Bridge)
    "bridge_top": "#38BDF8",
    "bridge_left": "#0369A1",
    "bridge_front": "#0284C7",
    # Màu lỗ đích 3D (Goal Hole)
    "goal_void": "#0F0402",
    "goal_wall_back": "#3F444E",
    "goal_wall_right": "#525864",
    # Màu công tắc (Switches)
    "sw_soft_fill": "#94A3B8",
    "sw_soft_rim": "#1E293B",
    "sw_split_fill": "#A855F7",
    # Màu khối Bloxorz (Đồng gỉ sét)
    "block_top": "#8C4A27",
    "block_left": "#432212",
    "block_front": "#68351B",
    "block_bottom": "#2A140A",
    "block_rust_light": "#B86538",
    "block_rust_dark": "#2E160B",
    "block_border": "#1F0E06",
    # Màu khối đơn khi tách (SPLIT)
    "active_top": "#D97706",
    "active_left": "#78350F",
    "active_front": "#B45309",
    "active_border": "#FEF08A",
}
