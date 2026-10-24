# ui/gui_renderer.py
import math
import tkinter as tk
from typing import Any, Callable, Dict, List, Optional, Tuple

from board import Board, TileType
from state import Action, GameState, Orientation
from ui.gui_config import (
    CAM_VEC,
    COLORS,
    Point2D,
    Point3D,
    TILE_THICKNESS,
    VEC_C,
    VEC_R,
    VEC_Z,
)


class BloxorzRenderer:
    """
    Engine dựng hình 2.5D cho bàn cờ Bloxorz trên Tkinter Canvas:
    - Chuyển đổi tọa độ không gian 3D (r, c, z) sang tọa độ màn hình 2D.
    - Xử lý chiều sâu Painter's Algorithm cho cả gạch sàn lẫn khối hộp đang xoay/rơi.
    """

    def __init__(self, canvas: tk.Canvas) -> None:
        self.canvas = canvas
        self.scale: float = 1.0
        self.origin_x: float = 200.0
        self.origin_y: float = 200.0

    def project(self, r: float, c: float, z: float = 0.0) -> Point2D:
        x = self.origin_x + self.scale * (c * VEC_C[0] + r * VEC_R[0] + z * VEC_Z[0])
        y = self.origin_y + self.scale * (c * VEC_C[1] + r * VEC_R[1] + z * VEC_Z[1])
        return (x, y)

    def cam_depth(self, r: float, c: float, z: float) -> float:
        return CAM_VEC[0] * r + CAM_VEC[1] * c + CAM_VEC[2] * z

    def compute_camera_transform(self, cw: int, ch: int, rows: int, cols: int) -> None:
        safe_rows, safe_cols = max(rows, 1), max(cols, 1)
        sample_points: List[Point2D] = []
        for r in (0.0, float(safe_rows)):
            for c in (0.0, float(safe_cols)):
                for z in (-TILE_THICKNESS, 2.2):
                    px = c * VEC_C[0] + r * VEC_R[0] + z * VEC_Z[0]
                    py = c * VEC_C[1] + r * VEC_R[1] + z * VEC_Z[1]
                    sample_points.append((px, py))

        min_x = min(p[0] for p in sample_points)
        max_x = max(p[0] for p in sample_points)
        min_y = min(p[1] for p in sample_points)
        max_y = max(p[1] for p in sample_points)

        span_x = max(max_x - min_x, 1.0)
        span_y = max(max_y - min_y, 1.0)

        margin_x, margin_y = 90.0, 110.0
        scale_x = (cw - 2 * margin_x) / span_x
        scale_y = (ch - 2 * margin_y) / span_y
        self.scale = max(0.55, min(1.35, scale_x, scale_y))

        center_raw_x = (min_x + max_x) / 2.0
        center_raw_y = (min_y + max_y) / 2.0
        self.origin_x = cw / 2.0 - center_raw_x * self.scale
        self.origin_y = ch / 2.0 - center_raw_y * self.scale + 15.0

    def _draw_poly(
        self,
        points: List[Point2D],
        fill: str,
        outline: str = "",
        width: int = 1,
        dash: Tuple[int, ...] = (),
    ) -> None:
        flat = [coord for pt in points for coord in pt]
        if dash:
            self.canvas.create_polygon(*flat, fill=fill, outline=outline, width=width, dash=dash)
        else:
            self.canvas.create_polygon(*flat, fill=fill, outline=outline, width=width)

    def _lerp_tile_point(self, r: int, c: int, u: float, v: float, z: float = 0.0) -> Point2D:
        return self.project(r + u, c + v, z)

    def rotate_point_3d(
        self,
        pt: Point3D,
        r0: float,
        c0: float,
        r1: float,
        c1: float,
        z0: float,
        direction: Optional[str],
        theta: float,
        offset: Point3D = (0.0, 0.0, 0.0),
    ) -> Point3D:
        r, c, z = pt
        if direction and abs(theta) > 1e-6:
            cos_t = math.cos(theta)
            sin_t = math.sin(theta)
            dz = z - z0

            if direction == Action.UP:
                dr = r - r0
                r = r0 + dr * cos_t - dz * sin_t
                z = z0 + dr * sin_t + dz * cos_t
            elif direction == Action.DOWN:
                dr = r - r1
                r = r1 + dr * cos_t + dz * sin_t
                z = z0 - dr * sin_t + dz * cos_t
            elif direction == Action.LEFT:
                dc = c - c0
                c = c0 + dc * cos_t - dz * sin_t
                z = z0 + dc * sin_t + dz * cos_t
            elif direction == Action.RIGHT:
                dc = c - c1
                c = c1 + dc * cos_t + dz * sin_t
                z = z0 - dc * sin_t + dz * cos_t

        return (r + offset[0], c + offset[1], z + offset[2])

    def draw_3d_cuboid_rotated(
        self,
        r0: float,
        c0: float,
        r1: float,
        c1: float,
        z0: float,
        z1: float,
        direction: Optional[str] = None,
        theta: float = 0.0,
        offset: Point3D = (0.0, 0.0, 0.0),
        top_color: Optional[str] = None,
        left_color: Optional[str] = None,
        front_color: Optional[str] = None,
        border_color: Optional[str] = None,
        rust_texture: bool = True,
    ) -> None:
        if z1 <= z0 + 1e-4:
            return

        top_col = top_color or COLORS["block_top"]
        left_col = left_color or COLORS["block_left"]
        front_col = front_color or COLORS["block_front"]
        bot_col = COLORS["block_bottom"]
        bdr_col = border_color or COLORS["block_border"]

        faces_local = [
            ("TOP", top_col, [(r0, c0, z1), (r0, c1, z1), (r1, c1, z1), (r1, c0, z1)]),
            ("BOTTOM", bot_col, [(r0, c0, z0), (r1, c0, z0), (r1, c1, z0), (r0, c1, z0)]),
            ("FRONT", front_col, [(r1, c0, z1), (r1, c1, z1), (r1, c1, z0), (r1, c0, z0)]),
            ("BACK", front_col, [(r0, c1, z1), (r0, c0, z1), (r0, c0, z0), (r0, c1, z0)]),
            ("LEFT", left_col, [(r0, c0, z1), (r1, c0, z1), (r1, c0, z0), (r0, c0, z0)]),
            ("RIGHT", left_col, [(r1, c1, z1), (r0, c1, z1), (r0, c1, z0), (r1, c1, z0)]),
        ]

        transformed_faces = []
        for fname, fcol, corners in faces_local:
            pts_3d = [
                self.rotate_point_3d(pt, r0, c0, r1, c1, z0, direction, theta, offset)
                for pt in corners
            ]
            avg_r = sum(p[0] for p in pts_3d) * 0.25
            avg_c = sum(p[1] for p in pts_3d) * 0.25
            avg_z = sum(p[2] for p in pts_3d) * 0.25
            depth = self.cam_depth(avg_r, avg_c, avg_z)
            transformed_faces.append((depth, fname, fcol, pts_3d))

        transformed_faces.sort(key=lambda item: item[0])
        visible_faces = transformed_faces[3:]

        for _, fname, fcol, pts_3d in visible_faces:
            pts_2d = [self.project(*p) for p in pts_3d]
            self._draw_poly(pts_2d, fill=fcol, outline=bdr_col, width=2)

            if rust_texture:
                p0, p1, p2, p3 = pts_3d
                if fname in ("TOP", "BOTTOM"):
                    q1 = (
                        p0[0] * 0.65 + p2[0] * 0.35,
                        p0[1] * 0.65 + p2[1] * 0.35,
                        p0[2] * 0.65 + p2[2] * 0.35,
                    )
                    q2 = (
                        p1[0] * 0.60 + p3[0] * 0.40,
                        p1[1] * 0.60 + p3[1] * 0.40,
                        p1[2] * 0.60 + p3[2] * 0.40,
                    )
                    q3 = (
                        p2[0] * 0.70 + p0[0] * 0.30,
                        p2[1] * 0.70 + p0[1] * 0.30,
                        p2[2] * 0.70 + p0[2] * 0.30,
                    )
                    self._draw_poly(
                        [self.project(*q1), self.project(*q2), self.project(*q3)],
                        fill=COLORS["block_rust_light"],
                        outline="",
                    )
                else:
                    a = (
                        p0[0] * 0.65 + p2[0] * 0.35,
                        p0[1] * 0.65 + p2[1] * 0.35,
                        p0[2] * 0.65 + p2[2] * 0.35,
                    )
                    b = (
                        p1[0] * 0.65 + p3[0] * 0.35,
                        p1[1] * 0.65 + p3[1] * 0.35,
                        p1[2] * 0.65 + p3[2] * 0.35,
                    )
                    c_pt = (
                        p2[0] * 0.65 + p0[0] * 0.35,
                        p2[1] * 0.65 + p0[1] * 0.35,
                        p2[2] * 0.65 + p0[2] * 0.35,
                    )
                    d = (
                        p3[0] * 0.65 + p1[0] * 0.35,
                        p3[1] * 0.65 + p1[1] * 0.35,
                        p3[2] * 0.65 + p1[2] * 0.35,
                    )
                    self._draw_poly(
                        [self.project(*a), self.project(*b), self.project(*c_pt), self.project(*d)],
                        fill=COLORS["block_rust_dark"],
                        outline="",
                    )

                self._draw_poly(pts_2d, fill="", outline=bdr_col, width=2)

    def draw_prism(
        self,
        r0: float,
        c0: float,
        r1: float,
        c1: float,
        z_bottom: float,
        z_top: float,
        top_color: str,
        left_color: str,
        front_color: str,
        border_color: str,
        rust_texture: bool = False,
    ) -> None:
        self.draw_3d_cuboid_rotated(
            r0, c0, r1, c1, z_bottom, z_top,
            direction=None, theta=0.0,
            top_color=top_color, left_color=left_color,
            front_color=front_color, border_color=border_color,
            rust_texture=rust_texture,
        )

    def _draw_background_and_hud(
        self,
        cw: int,
        ch: int,
        board_name: str,
        move_count: int,
        game_status: str,
        loss_reason: str,
        is_animating: bool,
        state: GameState,
        anim_state: Optional[Dict[str, Any]],
    ) -> None:
        bands = 42
        for i in range(bands):
            t = i / max(bands - 1, 1)
            if t < 0.35:
                k = t / 0.35
                r, g, b = int(175 + 55 * k), int(28 + 20 * k), 4
            elif t < 0.72:
                k = (t - 0.35) / 0.37
                r, g, b = int(230 - 110 * k), int(48 - 36 * k), 4
            else:
                k = (t - 0.72) / 0.28
                r = int(120 * (1 - k) + 12 * k)
                g = int(12 * (1 - k) + 2 * k)
                b = int(4 * (1 - k) + 2 * k)

            color = f"#{r:02x}{g:02x}{b:02x}"
            y1 = int(i * ch / bands)
            y2 = int((i + 1) * ch / bands) + 1
            self.canvas.create_rectangle(0, y1, cw, y2, fill=color, outline="")

        self.canvas.create_text(
            cw // 2 + 2, 28, text=board_name,
            font=("Segoe UI", 14, "bold"), fill="#1A0400",
        )
        self.canvas.create_text(
            cw // 2, 26, text=board_name,
            font=("Segoe UI", 14, "bold"), fill="#FDE68A",
        )

        hud_right_x = cw - 20
        self.canvas.create_text(
            hud_right_x + 1, 27, text=f"Moves: {move_count:>4}",
            font=("Consolas", 13, "bold"), fill="#F97316", anchor="e",
        )
        self.canvas.create_text(
            hud_right_x, 26, text=f"Moves: {move_count:>4}",
            font=("Consolas", 13, "bold"), fill="#120300", anchor="e",
        )

        if game_status == "WIN":
            status_txt = "★ STAGE COMPLETED! KHỐI ĐÃ LỌT QUA LỖ ĐÍCH XUỐNG DƯỚI PLATFORM! ★"
            status_col = "#4ADE80"
        elif game_status == "LOST" or (anim_state and anim_state["phase"] == "FALL"):
            status_txt = f"✖ {loss_reason} (Nhấn Z để Undo hoặc R để Restart)"
            status_col = "#FCA5A5"
        elif is_animating:
            status_txt = "▶ Đang chạy Animation lời giải của AI Solver..."
            status_col = "#38BDF8"
        elif state.orientation == Orientation.SPLIT:
            status_txt = (
                f"◆ Đang tách 2 khối đơn (Đang điều khiển Khối #{state.active_cube + 1} "
                "- Nhấn SPACE để đổi khối)"
            )
            status_col = "#FDE047"
        else:
            status_txt = "Dùng phím Mũi tên / WASD để lăn khối 2.5D vào lỗ đích"
            status_col = "#FED7AA"

        self.canvas.create_text(
            cw // 2, ch - 22, text=status_txt,
            font=("Segoe UI", 11, "bold"), fill=status_col,
        )

    def _draw_goal_tile(self, r: int, c: int, inner_block_z: Optional[Tuple[float, float]] = None) -> None:
        zb = -TILE_THICKNESS
        t00 = self.project(r, c, 0.0)
        t01 = self.project(r, c + 1, 0.0)
        t11 = self.project(r + 1, c + 1, 0.0)
        t10 = self.project(r + 1, c, 0.0)

        b00 = self.project(r, c, zb)
        b01 = self.project(r, c + 1, zb)
        b11 = self.project(r + 1, c + 1, zb)
        b10 = self.project(r + 1, c, zb)

        self._draw_poly([t00, t01, t11, t10], fill=COLORS["goal_void"], outline=COLORS["floor_border"])
        self._draw_poly([t00, t01, b01, b00], fill=COLORS["goal_wall_back"], outline="#1E293B")
        self._draw_poly([t01, t11, b11, b01], fill=COLORS["goal_wall_right"], outline="#1E293B")

        if inner_block_z is not None:
            iz_bot, iz_top = inner_block_z
            if iz_top > iz_bot + 1e-4:
                self.draw_prism(
                    r, c, r + 1, c + 1,
                    z_bottom=iz_bot, z_top=iz_top,
                    top_color=COLORS["block_top"],
                    left_color=COLORS["block_left"],
                    front_color=COLORS["block_front"],
                    border_color=COLORS["block_border"],
                    rust_texture=True,
                )

        self._draw_poly([t00, t10, b10, b00], fill=COLORS["floor_left"], outline=COLORS["floor_border"])
        self._draw_poly([t10, t11, b11, b10], fill=COLORS["floor_front"], outline=COLORS["floor_border"])
        self._draw_poly([t00, t01, t11, t10], fill="", outline="#1E293B", width=2)

    def _draw_switch_on_tile(self, r: int, c: int, sw_type: str) -> None:
        if sw_type == "soft":
            octagon_uv = [
                (0.35, 0.18), (0.65, 0.18), (0.82, 0.35), (0.82, 0.65),
                (0.65, 0.82), (0.35, 0.82), (0.18, 0.65), (0.18, 0.35),
            ]
            pts_base = [self._lerp_tile_point(r, c, u, v, 0.01) for u, v in octagon_uv]
            pts_top = [self._lerp_tile_point(r, c, u, v, 0.05) for u, v in octagon_uv]
            self._draw_poly(pts_base, fill="#334155", outline="#0F172A", width=2)
            self._draw_poly(pts_top, fill=COLORS["sw_soft_fill"], outline=COLORS["sw_soft_rim"], width=2)

        elif sw_type == "heavy":
            arm1 = [
                self._lerp_tile_point(r, c, 0.16, 0.24, 0.03),
                self._lerp_tile_point(r, c, 0.24, 0.16, 0.03),
                self._lerp_tile_point(r, c, 0.84, 0.76, 0.03),
                self._lerp_tile_point(r, c, 0.76, 0.84, 0.03),
            ]
            arm2 = [
                self._lerp_tile_point(r, c, 0.76, 0.16, 0.03),
                self._lerp_tile_point(r, c, 0.84, 0.24, 0.03),
                self._lerp_tile_point(r, c, 0.24, 0.84, 0.03),
                self._lerp_tile_point(r, c, 0.16, 0.76, 0.03),
            ]
            self._draw_poly(arm1, fill="#475569", outline="#0F172A", width=2)
            self._draw_poly(arm2, fill="#475569", outline="#0F172A", width=2)

        elif sw_type == "split":
            ring_uv = [
                (0.32, 0.16), (0.68, 0.16), (0.84, 0.32), (0.84, 0.68),
                (0.68, 0.84), (0.32, 0.84), (0.16, 0.68), (0.16, 0.32),
            ]
            pts = [self._lerp_tile_point(r, c, u, v, 0.03) for u, v in ring_uv]
            self._draw_poly(pts, fill=COLORS["sw_split_fill"], outline="#3B0764", width=2)
            cx, cy = self._lerp_tile_point(r, c, 0.5, 0.5, 0.05)
            self.canvas.create_text(cx, cy, text="( )", font=("Segoe UI", 10, "bold"), fill="white")

    def _draw_tile_at(
        self,
        board: Board,
        r: int,
        c: int,
        bridges_dict: Dict[Tuple[int, int], bool],
        broken_fragile_cell: Optional[Tuple[int, int]],
        is_falling_or_lost: bool,
        goal_inner_z: Optional[Tuple[float, float]] = None,
    ) -> None:
        if broken_fragile_cell == (r, c) and is_falling_or_lost:
            return

        tile = board.get_tile(r, c)
        if tile == TileType.VOID and (r, c) not in bridges_dict:
            return

        if tile == TileType.BRIDGE or (r, c) in bridges_dict:
            is_open = bridges_dict.get((r, c), False)
            if is_open:
                self.draw_prism(
                    r, c, r + 1, c + 1,
                    -TILE_THICKNESS * 0.7, 0.0,
                    top_color=COLORS["bridge_top"],
                    left_color=COLORS["bridge_left"],
                    front_color=COLORS["bridge_front"],
                    border_color="#082F49",
                )
                for frac in (0.25, 0.5, 0.75):
                    p1 = self._lerp_tile_point(r, c, 0.08, frac, 0.01)
                    p2 = self._lerp_tile_point(r, c, 0.92, frac, 0.01)
                    self.canvas.create_line(p1[0], p1[1], p2[0], p2[1], fill="#0369A1", width=2)
            else:
                t00 = self.project(r + 0.08, c + 0.08, 0.0)
                t01 = self.project(r + 0.08, c + 0.92, 0.0)
                t11 = self.project(r + 0.92, c + 0.92, 0.0)
                t10 = self.project(r + 0.92, c + 0.08, 0.0)
                self._draw_poly([t00, t01, t11, t10], fill="", outline="#F87171", width=1, dash=(3, 3))
            return

        if tile == TileType.GOAL:
            self._draw_goal_tile(r, c, inner_block_z=goal_inner_z)
            return

        if tile == TileType.FRAGILE:
            top_col = COLORS["fragile_top"]
            left_col = COLORS["fragile_left"]
            front_col = COLORS["fragile_front"]
            border_col = "#7C2D12"
        else:
            top_col = COLORS["floor_top"]
            left_col = COLORS["floor_left"]
            front_col = COLORS["floor_front"]
            border_col = COLORS["floor_border"]

        self.draw_prism(
            r, c, r + 1, c + 1,
            -TILE_THICKNESS, 0.0,
            top_color=top_col, left_color=left_col,
            front_color=front_col, border_color=border_col,
        )

        in00 = self._lerp_tile_point(r, c, 0.12, 0.12, 0.0)
        in01 = self._lerp_tile_point(r, c, 0.12, 0.88, 0.0)
        in11 = self._lerp_tile_point(r, c, 0.88, 0.88, 0.0)
        in10 = self._lerp_tile_point(r, c, 0.88, 0.12, 0.0)
        inner_outline = COLORS["fragile_inner"] if tile == TileType.FRAGILE else "#E2E8F0"
        self._draw_poly([in00, in01, in11, in10], fill="", outline=inner_outline, width=1)

        if (r, c) in board.switches or tile in (
            TileType.SOFT_SWITCH,
            TileType.HEAVY_SWITCH,
            TileType.SPLIT_SWITCH,
        ):
            sw = board.switches.get((r, c))
            sw_type = (
                sw.switch_type
                if sw
                else (
                    "soft"
                    if tile == TileType.SOFT_SWITCH
                    else "heavy"
                    if tile == TileType.HEAVY_SWITCH
                    else "split"
                )
            )
            self._draw_switch_on_tile(r, c, sw_type)

    def _draw_failed_overlay(self, failed_cells: Tuple[Tuple[int, int], ...]) -> None:
        for fr, fc in failed_cells:
            t00 = self.project(fr, fc, 0.02)
            t01 = self.project(fr, fc + 1, 0.02)
            t11 = self.project(fr + 1, fc + 1, 0.02)
            t10 = self.project(fr + 1, fc, 0.02)
            self._draw_poly([t00, t01, t11, t10], fill="", outline="#EF4444", width=2, dash=(4, 3))

    def _draw_static_block(self, state: GameState, z_bot: float = 0.0, z_top: float = 2.0) -> None:
        ori = state.orientation
        r, c = state.pos1

        if ori == Orientation.STANDING:
            self.draw_prism(
                r, c, r + 1, c + 1,
                z_bottom=z_bot, z_top=z_top,
                top_color=COLORS["block_top"],
                left_color=COLORS["block_left"],
                front_color=COLORS["block_front"],
                border_color=COLORS["block_border"],
                rust_texture=True,
            )

        elif ori == Orientation.LYING_HORIZONTAL:
            self.draw_prism(
                r, c, r + 1, c + 2,
                z_bottom=0.0, z_top=1.0,
                top_color=COLORS["block_top"],
                left_color=COLORS["block_left"],
                front_color=COLORS["block_front"],
                border_color=COLORS["block_border"],
                rust_texture=True,
            )
            m1 = self.project(r, c + 1, 1.0)
            m2 = self.project(r + 1, c + 1, 1.0)
            m3 = self.project(r + 1, c + 1, 0.0)
            self.canvas.create_line(m1[0], m1[1], m2[0], m2[1], fill="#1F0E06", width=2)
            self.canvas.create_line(m2[0], m2[1], m3[0], m3[1], fill="#1F0E06", width=2)

        elif ori == Orientation.LYING_VERTICAL:
            self.draw_prism(
                r, c, r + 2, c + 1,
                z_bottom=0.0, z_top=1.0,
                top_color=COLORS["block_top"],
                left_color=COLORS["block_left"],
                front_color=COLORS["block_front"],
                border_color=COLORS["block_border"],
                rust_texture=True,
            )
            m1 = self.project(r + 1, c, 1.0)
            m2 = self.project(r + 1, c + 1, 1.0)
            m3 = self.project(r + 1, c, 0.0)
            self.canvas.create_line(m1[0], m1[1], m2[0], m2[1], fill="#1F0E06", width=2)
            self.canvas.create_line(m1[0], m1[1], m3[0], m3[1], fill="#1F0E06", width=2)

        elif ori == Orientation.SPLIT and state.pos2 is not None:
            indexed_cubes = [(0, state.pos1), (1, state.pos2)]
            indexed_cubes.sort(key=lambda item: (item[1][0], -item[1][1]))

            for idx, (cr, cc) in indexed_cubes:
                is_active = idx == state.active_cube
                self.draw_prism(
                    cr, cc, cr + 1, cc + 1,
                    z_bottom=0.0, z_top=1.0,
                    top_color=COLORS["active_top"] if is_active else COLORS["block_top"],
                    left_color=COLORS["active_left"] if is_active else COLORS["block_left"],
                    front_color=COLORS["active_front"] if is_active else COLORS["block_front"],
                    border_color=COLORS["active_border"] if is_active else COLORS["block_border"],
                    rust_texture=True,
                )
                if is_active:
                    top_center = self.project(cr + 0.5, cc + 0.5, 1.35)
                    self.canvas.create_text(
                        top_center[0], top_center[1],
                        text="▼", font=("Segoe UI", 12, "bold"), fill="#FEF08A",
                    )

    def render(
        self,
        board: Board,
        state: GameState,
        game_status: str,
        move_count: int,
        loss_reason: str,
        failed_cells: Tuple[Tuple[int, int], ...],
        broken_fragile_cell: Optional[Tuple[int, int]],
        is_animating: bool,
        anim_state: Optional[Dict[str, Any]],
    ) -> None:
        self.canvas.delete("all")

        cw = max(self.canvas.winfo_width(), 680)
        ch = max(self.canvas.winfo_height(), 460)

        self.compute_camera_transform(cw, ch, board.rows, board.cols)
        self._draw_background_and_hud(
            cw, ch, board.name, move_count, game_status, loss_reason, is_animating, state, anim_state
        )

        bridges_dict = dict(state.bridges_status)
        phase = anim_state["phase"] if anim_state else None
        is_falling_or_lost = game_status == "LOST" or phase == "FALL"

        # 1. TRƯỜNG HỢP TỤT HỐ ĐÍCH (SINK) HOẶC ĐÃ THẮNG (WIN)
        if phase == "SINK" or (phase is None and game_status == "WIN"):
            gr, gc = board.goal
            if phase == "SINK" and anim_state is not None:
                t = anim_state["step"] / max(anim_state["total_steps"], 1)
                ease = t * t * (3.0 - 2.0 * t)
                z_bot = -2.18 * ease
                z_top = z_bot + 2.0
            else:
                z_bot, z_top = -2.18, -0.18

            under_z_top = min(-TILE_THICKNESS, z_top)
            if under_z_top > z_bot + 1e-4:
                self.draw_prism(
                    gr, gc, gr + 1, gc + 1,
                    z_bottom=z_bot, z_top=under_z_top,
                    top_color=COLORS["block_top"],
                    left_color=COLORS["block_left"],
                    front_color=COLORS["block_front"],
                    border_color=COLORS["block_border"],
                    rust_texture=True,
                )

            hole_z_bot = max(-TILE_THICKNESS, z_bot)
            hole_z_top = min(0.0, z_top)
            inner_z = (hole_z_bot, hole_z_top) if hole_z_top > hole_z_bot + 1e-4 else None

            for r in range(board.rows):
                for c in range(board.cols - 1, -1, -1):
                    self._draw_tile_at(
                        board, r, c, bridges_dict, broken_fragile_cell, is_falling_or_lost,
                        goal_inner_z=inner_z if (r, c) == (gr, gc) else None,
                    )

            if z_top > 1e-4:
                above_z_bot = max(0.0, z_bot)
                self.draw_prism(
                    gr, gc, gr + 1, gc + 1,
                    z_bottom=above_z_bot, z_top=z_top,
                    top_color=COLORS["block_top"],
                    left_color=COLORS["block_left"],
                    front_color=COLORS["block_front"],
                    border_color=COLORS["block_border"],
                    rust_texture=True,
                )
            return

        # 2. TRƯỜNG HỢP RƠI KHỎI MÀN CHƠI / VỠ GẠCH MỎNG (FALL)
        if phase == "FALL" and anim_state is not None:
            t = anim_state["step"] / max(anim_state["total_steps"], 1)
            r0, c0, r1, c1, z0, z1 = anim_state["fall_box"]
            tip_dir = anim_state["tip_dir"]
            status = anim_state["status"]
            remain_pos = anim_state["remain_pos"]

            dz_fall = -6.2 * (t * t)
            theta_fall = t * (math.pi * 0.55) if status != "FRAGILE" else t * (math.pi * 0.22)

            drift = 0.35 * t
            dr_off = -drift if tip_dir == Action.UP else (drift if tip_dir == Action.DOWN else 0.0)
            dc_off = -drift if tip_dir == Action.LEFT else (drift if tip_dir == Action.RIGHT else 0.0)
            offset_3d = (dr_off, dc_off, dz_fall)

            center_r = (r0 + r1) * 0.5 + dr_off
            center_c = (c0 + c1) * 0.5 + dc_off
            center_z = (z0 + z1) * 0.5 + dz_fall

            render_queue: List[Tuple[float, int, Callable[[], None]]] = []

            for r in range(board.rows):
                for c in range(board.cols - 1, -1, -1):
                    tile_depth = self.cam_depth(r + 0.5, c + 0.5, -TILE_THICKNESS * 0.5)
                    render_queue.append((
                        tile_depth,
                        0,
                        lambda rr=r, cc=c: self._draw_tile_at(
                            board, rr, cc, bridges_dict, broken_fragile_cell, is_falling_or_lost
                        ),
                    ))

            if remain_pos is not None:
                rem_r, rem_c = remain_pos
                rem_depth = self.cam_depth(rem_r + 0.5, rem_c + 0.5, 0.5)
                render_queue.append((
                    rem_depth,
                    1,
                    lambda: self.draw_prism(
                        rem_r, rem_c, rem_r + 1, rem_c + 1, 0.0, 1.0,
                        top_color=COLORS["block_top"],
                        left_color=COLORS["block_left"],
                        front_color=COLORS["block_front"],
                        border_color=COLORS["block_border"],
                        rust_texture=True,
                    ),
                ))

            if status == "FRAGILE" and broken_fragile_cell is not None:
                fr, fc = broken_fragile_cell
                frag_z_off = dz_fall * 1.25 - 0.15
                frag_depth = self.cam_depth(fr + 0.5, fc + 0.5, frag_z_off - 0.1)
                render_queue.append((
                    frag_depth,
                    2,
                    lambda: self.draw_3d_cuboid_rotated(
                        fr, fc, fr + 1, fc + 1,
                        -TILE_THICKNESS, 0.0,
                        direction=tip_dir,
                        theta=theta_fall * 1.4,
                        offset=(0.0, 0.0, frag_z_off),
                        top_color=COLORS["fragile_top"],
                        left_color=COLORS["fragile_left"],
                        front_color=COLORS["fragile_front"],
                        border_color="#7C2D12",
                        rust_texture=False,
                    ),
                ))

            fall_depth = self.cam_depth(center_r, center_c, center_z)
            render_queue.append((
                fall_depth,
                3,
                lambda: self.draw_3d_cuboid_rotated(
                    r0, c0, r1, c1, z0, z1,
                    direction=tip_dir,
                    theta=theta_fall,
                    offset=offset_3d,
                    rust_texture=True,
                ),
            ))

            render_queue.sort(key=lambda item: (item[0], item[1]))
            for _, _, draw_fn in render_queue:
                draw_fn()

            self._draw_failed_overlay(failed_cells)
            return

        # 3. TRƯỜNG HỢP LĂN TRÊN SÀN (ROLL) HOẶC ĐỨNG YÊN BÌNH THƯỜNG
        for r in range(board.rows):
            for c in range(board.cols - 1, -1, -1):
                self._draw_tile_at(board, r, c, bridges_dict, broken_fragile_cell, is_falling_or_lost)

        if game_status == "LOST":
            self._draw_failed_overlay(failed_cells)
            return

        if phase == "ROLL" and anim_state is not None:
            t = anim_state["step"] / max(anim_state["total_steps"], 1)
            ease_t = t * t * (3.0 - 2.0 * t)
            theta = ease_t * (math.pi * 0.5)

            r0, c0, r1, c1, z0, z1 = anim_state["start_box"]
            action = anim_state["action"]
            static_pos = anim_state["static_pos"]

            if static_pos is not None:
                sr, sc = static_pos
                static_depth = self.cam_depth(sr + 0.5, sc + 0.5, 0.5)
                rot_center = self.rotate_point_3d(
                    ((r0 + r1) * 0.5, (c0 + c1) * 0.5, (z0 + z1) * 0.5),
                    r0, c0, r1, c1, z0, action, theta,
                )
                moving_depth = self.cam_depth(*rot_center)

                def draw_static() -> None:
                    self.draw_prism(
                        sr, sc, sr + 1, sc + 1, 0.0, 1.0,
                        top_color=COLORS["block_top"],
                        left_color=COLORS["block_left"],
                        front_color=COLORS["block_front"],
                        border_color=COLORS["block_border"],
                        rust_texture=True,
                    )

                def draw_moving() -> None:
                    self.draw_3d_cuboid_rotated(
                        r0, c0, r1, c1, z0, z1,
                        direction=action, theta=theta,
                        top_color=COLORS["active_top"],
                        left_color=COLORS["active_left"],
                        front_color=COLORS["active_front"],
                        border_color=COLORS["active_border"],
                        rust_texture=True,
                    )

                if static_depth <= moving_depth:
                    draw_static()
                    draw_moving()
                else:
                    draw_moving()
                    draw_static()
            else:
                self.draw_3d_cuboid_rotated(
                    r0, c0, r1, c1, z0, z1,
                    direction=action, theta=theta,
                    rust_texture=True,
                )
            return

        self._draw_static_block(state)