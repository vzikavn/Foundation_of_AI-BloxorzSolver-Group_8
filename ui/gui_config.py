# ui/gui_config.py
from typing import Dict, Tuple

Point2D = Tuple[float, float]
Point3D = Tuple[float, float, float]

# Hệ trục chiếu 2.5D
VEC_C: Point2D = (46.0, -10.5)
VEC_R: Point2D = (16.0, 28.0)
VEC_Z: Point2D = (0.0, -40.0)
TILE_THICKNESS: float = 0.24

# Vector hướng nhìn của Camera trong hệ trục (r, c, z) dùng cho Painter's Algorithm
CAM_VEC: Point3D = (46.0, -16.0, 36.4)

# Cấu hình thời gian Animation (~60 FPS) & Tốc độ Replay mặc định 250 ms
FRAME_MS: int = 16
ROLL_FRAMES: int = 9
SINK_FRAMES: int = 14
FALL_FRAMES: int = 18
DEFAULT_REPLAY_SPEED_MS: int = 250

# Bảng màu Texture Đá Cổ Điển & Đồng Cổ (Ancient Stone & Bronze Ruins)
COLORS: Dict[str, str] = {
    # Màu nền UI & Bảng điều khiển bằng đá khắc
    "bg_root": "#0E0C0A",
    "bg_panel": "#181512",
    "menu_bg": "#211D19",
    "menu_header": "#14110E",
    "menu_active_bg": "#362F28",
    "menu_hover_bg": "#2C2620",
    "menu_border": "#4A4036",
    "gold_accent": "#D4A359",
    "fg_text": "#EAE0C8",
    "fg_sub": "#A39682",
    # Gạch sàn thường: Đá vôi phong hóa (Weathered Limestone)
    "floor_top": "#A69B8D",
    "floor_bevel": "#94897B",
    "floor_patch": "#83786B",
    "floor_moss": "#78806A",
    "floor_left": "#595247",
    "floor_front": "#756C5E",
    "floor_border": "#2A2520",
    "floor_highlight": "#C2B8A8",
    "floor_crack": "#3D352E",
    # Gạch mỏng dễ vỡ (Fragile): Đất nung cổ rạn nứt (Cracked Terracotta)
    "fragile_top": "#B85D43",
    "fragile_inner": "#9E4730",
    "fragile_left": "#632819",
    "fragile_front": "#823824",
    "fragile_border": "#33130B",
    "fragile_crack": "#240B05",
    "fragile_highlight": "#D98268",
    # Cầu cổ đại (Bridge): Ván gỗ lim & Khung đồng ngọc bích
    "bridge_top": "#6E5239",
    "bridge_plank": "#856548",
    "bridge_left": "#3D2B1C",
    "bridge_front": "#523B27",
    "bridge_rail": "#467A73",
    "bridge_rune": "#68B8AD",
    "bridge_closed_bracket": "#5C5044",
    "bridge_closed_rune": "#9E523B",
    # Lỗ đích 3D (Ancient Altar Abyss)
    "goal_void": "#050403",
    "goal_rim": "#8C8070",
    "goal_wall_back": "#2E2822",
    "goal_wall_right": "#423A31",
    "goal_rune": "#E0AD5A",
    # Công tắc cổ đại (Ancient Switches)
    "sw_socket": "#26211C",
    "sw_soft_fill": "#A88454",
    "sw_soft_inner": "#7D5E36",
    "sw_soft_rim": "#2B1F11",
    "sw_heavy_top": "#7A8288",
    "sw_heavy_side": "#454B50",
    "sw_split_base": "#3B0764",
    "sw_split_fill": "#9333EA",
    "sw_split_glow": "#581C87",
    # Khối Bloxorz: Cột đá bọc đồng cổ (Ancient Bronze Monolith)
    "block_top": "#8C5832",
    "block_left": "#422713",
    "block_front": "#633C1F",
    "block_bottom": "#241308",
    "block_panel": "#704423",
    "block_rust_light": "#B5794A",
    "block_rust_dark": "#331C0C",
    "block_patina": "#4E6E5D",
    "block_border": "#1C0F06",
    # Khối đơn khi tách (SPLIT - Khối Vàng Hổ Phách Cổ Ngữ)
    "active_top": "#C98A32",
    "active_left": "#6E4611",
    "active_front": "#9E681E",
    "active_panel": "#AD7322",
    "active_border": "#F5D08A",
}
