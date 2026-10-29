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
    Engine dựng hình 2.5D phong cách Texture Đá Cổ Điển (Ancient Stone & Bronze):
    - Sinh vân đá, vết nứt, rêu phong, mạch vữa, ván cầu và đinh tán cố định theo tọa độ (r, c).
    - Xử lý bóng đổ 3D dưới đáy sàn và khung chạm khắc nổi trên từng mặt khối hộp.
    """

    def __init__(self, canvas: tk.Canvas) -> None:
        self.canvas = canvas
        self.scale: float = 1.0
        self.origin_x: float = 200.0
        self.origin_y: float = 200.0

    # =========================================================================
    # PHÉP CHIẾU 3D & HÀM NỘI SUY HÌNH HỌC
    # =========================================================================

    def project(self, r: float, c: float, z: float = 0.0) -> Point2D:
        x = self.origin_x + self.scale * (c * VEC_C[0] + r * VEC_R[0] + z * VEC_Z[0])
        y = self.origin_y + self.scale * (c * VEC_C[1] + r * VEC_R[1] + z * VEC_Z[1])
        return (x, y)

    def cam_depth(self, r: float, c: float, z: float) -> float:
        return CAM_VEC[0] * r + CAM_VEC[1] * c + CAM_VEC[2] * z

    @staticmethod
    def _tile_hash(r: int, c: int) -> int:
        """Hàm băm tất định theo tọa độ (r, c) để giữ nguyên vân đá ở mọi khung hình."""
        h = (r * 73856093) ^ (c * 19349663)
        return abs(h) % 997

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
        stipple: str = "",
    ) -> None:
        flat = [coord for pt in points for coord in pt]
        kwargs: Dict[str, Any] = {"fill": fill, "outline": outline, "width": width}
        if dash:
            kwargs["dash"] = dash
        if stipple:
            kwargs["stipple"] = stipple
        self.canvas.create_polygon(*flat, **kwargs)

    def _lerp_tile_point(self, r: int, c: int, u: float, v: float, z: float = 0.0) -> Point2D:
        return self.project(r + u, c + v, z)

    @staticmethod
    def _bilerp_3d(
        p0: Point3D, p1: Point3D, p2: Point3D, p3: Point3D, u: float, v: float
    ) -> Point3D:
        """Nội suy song tuyến tính một điểm (u, v) nằm trên mặt tứ giác 3D (p0, p1, p2, p3)."""
        w0 = (1.0 - u) * (1.0 - v)
        w1 = u * (1.0 - v)
        w2 = u * v
        w3 = (1.0 - u) * v
        return (
            p0[0] * w0 + p1[0] * w1 + p2[0] * w2 + p3[0] * w3,
            p0[1] * w0 + p1[1] * w1 + p2[1] * w2 + p3[1] * w3,
            p0[2] * w0 + p1[2] * w1 + p2[2] * w2 + p3[2] * w3,
        )

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

    # =========================================================================
    # DỰNG HÌNH KHỐI HỘP 3D CÓ TEXTURE ĐỒNG CỔ & KHUNG CHẠM KHẮC
    # =========================================================================

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
                # 1. Vẽ khung chạm khắc chìm (Recessed Stone/Bronze Panel) trên mỗi mặt khối
                in_pts_3d = [
                    self._bilerp_3d(p0, p1, p2, p3, 0.14, 0.14),
                    self._bilerp_3d(p0, p1, p2, p3, 0.86, 0.14),
                    self._bilerp_3d(p0, p1, p2, p3, 0.86, 0.86),
                    self._bilerp_3d(p0, p1, p2, p3, 0.14, 0.86),
                ]
                in_pts_2d = [self.project(*p) for p in in_pts_3d]
                panel_col = (
                    COLORS["active_panel"]
                    if top_col == COLORS["active_top"]
                    else COLORS["block_panel"]
                )
                self._draw_poly(
                    in_pts_2d,
                    fill=panel_col,
                    outline=COLORS["block_rust_dark"],
                    width=1,
                    stipple="gray50",
                )

                # 2. Vẽ mảng gỉ đồng & rêu cổ (Patina / Weathered Rust)
                if fname in ("TOP", "BOTTOM"):
                    q1 = self._bilerp_3d(p0, p1, p2, p3, 0.22, 0.25)
                    q2 = self._bilerp_3d(p0, p1, p2, p3, 0.75, 0.30)
                    q3 = self._bilerp_3d(p0, p1, p2, p3, 0.55, 0.78)
                    self._draw_poly(
                        [self.project(*q1), self.project(*q2), self.project(*q3)],
                        fill=COLORS["block_rust_light"],
                        outline="",
                        stipple="gray50",
                    )
                else:
                    a = self._bilerp_3d(p0, p1, p2, p3, 0.20, 0.25)
                    b = self._bilerp_3d(p0, p1, p2, p3, 0.80, 0.25)
                    c_pt = self._bilerp_3d(p0, p1, p2, p3, 0.72, 0.75)
                    d = self._bilerp_3d(p0, p1, p2, p3, 0.28, 0.75)
                    self._draw_poly(
                        [self.project(*a), self.project(*b), self.project(*c_pt), self.project(*d)],
                        fill=COLORS["block_rust_dark"],
                        outline="",
                        stipple="gray50",
                    )
                    # Đường gân chia đôi mặt bên tạo cảm giác 2 khối đá ghép lại
                    m_left = self.project(*self._bilerp_3d(p0, p1, p2, p3, 0.0, 0.5))
                    m_right = self.project(*self._bilerp_3d(p0, p1, p2, p3, 1.0, 0.5))
                    self.canvas.create_line(
                        m_left[0], m_left[1], m_right[0], m_right[1],
                        fill=COLORS["block_border"], width=1,
                    )

                # Viền ngoài sắc nét của khối
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

    # =========================================================================
    # VẼ NỀN HANG ĐỘNG ĐỀN CỔ & KHUNG HUD CHẠM KHẮC
    # =========================================================================

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
        # 1. Nền địa tầng đá tối (Subterranean Temple Cavern)
        bands = 40
        for i in range(bands):
            t = i / max(bands - 1, 1)
            # Chuyển từ nâu đá ấm cổ điển ở tâm sang đen sâu ở rìa
            dist_center = abs(t - 0.45) * 1.8
            k = min(1.0, dist_center)
            r = int(42 * (1.0 - k) + 12 * k)
            g = int(34 * (1.0 - k) + 10 * k)
            b = int(26 * (1.0 - k) + 8 * k)

            color = f"#{r:02x}{g:02x}{b:02x}"
            y1 = int(i * ch / bands)
            y2 = int((i + 1) * ch / bands) + 1
            self.canvas.create_rectangle(0, y1, cw, y2, fill=color, outline="")

        # 2. Vân đá ngang mờ trên vách hang động
        for y_frac in (0.15, 0.32, 0.68, 0.84):
            yy = int(ch * y_frac)
            self.canvas.create_line(0, yy, cw, yy, fill="#16120E", width=2)

        # 3. Quầng sáng đuốc ấm (Torchlight Glow) dưới khu vực bàn cờ
        glow_w, glow_h = int(cw * 0.36), int(ch * 0.28)
        cx, cy = cw // 2, int(ch * 0.52)
        self.canvas.create_oval(
            cx - glow_w, cy - glow_h, cx + glow_w, cy + glow_h,
            fill="#33261A", outline="", stipple="gray25",
        )

        # 4. Thanh Header bằng phiến đá khắc viền đồng
        self.canvas.create_rectangle(
            14, 10, cw - 14, 46,
            fill="#1A1612", outline=COLORS["menu_border"], width=2,
        )
        self.canvas.create_line(16, 44, cw - 16, 44, fill="#0D0B09", width=1)

        # Tiêu đề màn chơi ở giữa
        self.canvas.create_text(
            cw // 2 + 2, 29, text=f"❖  {board_name.upper()}  ❖",
            font=("Georgia", 13, "bold"), fill="#090705",
        )
        self.canvas.create_text(
            cw // 2, 27, text=f"❖  {board_name.upper()}  ❖",
            font=("Georgia", 13, "bold"), fill=COLORS["gold_accent"],
        )

        # Số bước đi (Moves) ở góc phải
        hud_right_x = cw - 28
        self.canvas.create_text(
            hud_right_x + 1, 29, text=f"MOVES: {move_count:>3}",
            font=("Consolas", 13, "bold"), fill="#090705", anchor="e",
        )
        self.canvas.create_text(
            hud_right_x, 27, text=f"MOVES: {move_count:>3}",
            font=("Consolas", 13, "bold"), fill=COLORS["fg_text"], anchor="e",
        )

        # 5. Thanh trạng thái dưới đáy
        if game_status == "WIN":
            status_txt = "★ STAGE COMPLETED! KHỐI ĐÃ LỌT QUA BỆ THỜ ĐÍCH! ★"
            status_col = "#84CC16"
        elif game_status == "LOST" or (anim_state and anim_state["phase"] == "FALL"):
            status_txt = f"✖ {loss_reason} (Nhấn Z để Undo hoặc R để Restart)"
            status_col = "#F87171"
        elif is_animating:
            status_txt = "▶ Đang phát lại lời giải của AI Solver..."
            status_col = "#68B8AD"
        elif state.orientation == Orientation.SPLIT:
            status_txt = (
                f"◆ Đang tách 2 khối đơn (Đang điều khiển Khối #{state.active_cube + 1} "
                "- Nhấn SPACE để đổi khối)"
            )
            status_col = COLORS["gold_accent"]
        else:
            status_txt = "Dùng phím Mũi tên / WASD để lăn khối đá cổ vào bệ thờ đích"
            status_col = COLORS["fg_sub"]

        self.canvas.create_rectangle(
            cw // 2 - 290, ch - 38, cw // 2 + 290, ch - 10,
            fill="#161310", outline=COLORS["menu_border"], width=1,
        )
        self.canvas.create_text(
            cw // 2, ch - 24, text=status_txt,
            font=("Segoe UI", 10, "bold"), fill=status_col,
        )

    # =========================================================================
    # TEXTURE CHO TỪNG LOẠI Ô GẠCH TRÊN BÀN CỜ
    # =========================================================================

    def _draw_tile_drop_shadow(self, r: int, c: int) -> None:
        """Vẽ bóng đổ 3D dưới đáy viên gạch giúp mặt sàn nổi hẳn lên khỏi nền hang động."""
        sh_z = -TILE_THICKNESS - 0.14
        s00 = self.project(r + 0.10, c - 0.08, sh_z)
        s01 = self.project(r + 0.10, c + 0.92, sh_z)
        s11 = self.project(r + 1.10, c + 0.92, sh_z)
        s10 = self.project(r + 1.10, c - 0.08, sh_z)
        self._draw_poly([s00, s01, s11, s10], fill="#070605", outline="", stipple="gray50")

    def _draw_stone_side_strata(self, r: int, c: int, z_bot: float) -> None:
        """Vẽ đường vân địa tầng ngang trên vách đá bên trái và phía trước của viên gạch."""
        z_mid = z_bot * 0.52
        p_left_a = self.project(r, c, z_mid)
        p_left_b = self.project(r + 1, c, z_mid)
        p_front_b = self.project(r + 1, c + 1, z_mid)
        self.canvas.create_line(
            p_left_a[0], p_left_a[1], p_left_b[0], p_left_b[1],
            fill=COLORS["floor_border"], width=1,
        )
        self.canvas.create_line(
            p_left_b[0], p_left_b[1], p_front_b[0], p_front_b[1],
            fill=COLORS["floor_border"], width=1,
        )

    def _draw_floor_stone_texture(self, r: int, c: int) -> None:
        """Vẽ chi tiết bề mặt đá cổ (vát cạnh, hạt nhám, rêu phong & vết nứt) cho ô sàn thường."""
        h = self._tile_hash(r, c)

        # 1. Phiến đá vát chìm bên trong (Recessed Bevel Slab)
        in00 = self._lerp_tile_point(r, c, 0.11, 0.11, 0.0)
        in01 = self._lerp_tile_point(r, c, 0.11, 0.89, 0.0)
        in11 = self._lerp_tile_point(r, c, 0.89, 0.89, 0.0)
        in10 = self._lerp_tile_point(r, c, 0.89, 0.11, 0.0)
        self._draw_poly([in00, in01, in11, in10], fill=COLORS["floor_bevel"], outline="")

        # Viền sáng (Highlight) và viền tối (Shadow) tạo độ lồi lõm như đá đục
        self.canvas.create_line(
            in00[0], in00[1], in01[0], in01[1], in11[0], in11[1],
            fill=COLORS["floor_highlight"], width=1,
        )
        self.canvas.create_line(
            in00[0], in00[1], in10[0], in10[1], in11[0], in11[1],
            fill=COLORS["floor_left"], width=1,
        )

        # 2. Mảng đá phong hóa / rêu mờ (Weathered Stone & Moss Patch)
        if h % 3 == 0:
            p1 = self._lerp_tile_point(r, c, 0.18, 0.22, 0.0)
            p2 = self._lerp_tile_point(r, c, 0.24, 0.72, 0.0)
            p3 = self._lerp_tile_point(r, c, 0.65, 0.60, 0.0)
            p4 = self._lerp_tile_point(r, c, 0.52, 0.18, 0.0)
            patch_col = COLORS["floor_moss"] if (h % 6 == 0) else COLORS["floor_patch"]
            self._draw_poly([p1, p2, p3, p4], fill=patch_col, outline="", stipple="gray25")
        elif h % 3 == 1:
            p1 = self._lerp_tile_point(r, c, 0.42, 0.35, 0.0)
            p2 = self._lerp_tile_point(r, c, 0.82, 0.28, 0.0)
            p3 = self._lerp_tile_point(r, c, 0.84, 0.82, 0.0)
            p4 = self._lerp_tile_point(r, c, 0.48, 0.76, 0.0)
            self._draw_poly([p1, p2, p3, p4], fill=COLORS["floor_patch"], outline="", stipple="gray25")

        # 3. Vết nứt đá tự nhiên (Deterministic Stone Cracks)
        variant = h % 5
        if variant == 0:
            c1 = self._lerp_tile_point(r, c, 0.12, 0.35, 0.0)
            c2 = self._lerp_tile_point(r, c, 0.38, 0.48, 0.0)
            c3 = self._lerp_tile_point(r, c, 0.55, 0.36, 0.0)
            self.canvas.create_line(
                c1[0], c1[1], c2[0], c2[1], c3[0], c3[1],
                fill=COLORS["floor_crack"], width=1,
            )
        elif variant == 1:
            c1 = self._lerp_tile_point(r, c, 0.88, 0.62, 0.0)
            c2 = self._lerp_tile_point(r, c, 0.60, 0.52, 0.0)
            c3 = self._lerp_tile_point(r, c, 0.44, 0.74, 0.0)
            self.canvas.create_line(
                c1[0], c1[1], c2[0], c2[1], c3[0], c3[1],
                fill=COLORS["floor_crack"], width=1,
            )
        elif variant == 2:
            # Vết mẻ ở góc gạch (Chipped Corner)
            ch1 = self._lerp_tile_point(r, c, 0.0, 0.82, 0.0)
            ch2 = self._lerp_tile_point(r, c, 0.0, 1.0, 0.0)
            ch3 = self._lerp_tile_point(r, c, 0.18, 1.0, 0.0)
            self._draw_poly([ch1, ch2, ch3], fill=COLORS["floor_border"], outline="")

    def _draw_fragile_terracotta_texture(self, r: int, c: int) -> None:
        """Vẽ bề mặt gạch đất nung rạn nứt mạnh cho ô Fragile (dễ vỡ)."""
        in00 = self._lerp_tile_point(r, c, 0.12, 0.12, 0.0)
        in01 = self._lerp_tile_point(r, c, 0.12, 0.88, 0.0)
        in11 = self._lerp_tile_point(r, c, 0.88, 0.88, 0.0)
        in10 = self._lerp_tile_point(r, c, 0.88, 0.12, 0.0)
        self._draw_poly(
            [in00, in01, in11, in10],
            fill=COLORS["fragile_inner"],
            outline=COLORS["fragile_highlight"],
            width=1,
            stipple="gray50",
        )

        # Vết nứt chân chim cắt chéo từ tâm ra 4 cạnh báo hiệu gạch rỗng sắp sập
        k1 = self._lerp_tile_point(r, c, 0.10, 0.22, 0.0)
        k2 = self._lerp_tile_point(r, c, 0.42, 0.46, 0.0)
        k3 = self._lerp_tile_point(r, c, 0.62, 0.40, 0.0)
        k4 = self._lerp_tile_point(r, c, 0.90, 0.78, 0.0)
        k5 = self._lerp_tile_point(r, c, 0.24, 0.84, 0.0)
        k6 = self._lerp_tile_point(r, c, 0.78, 0.16, 0.0)

        self.canvas.create_line(
            k1[0], k1[1], k2[0], k2[1], k3[0], k3[1], k4[0], k4[1],
            fill=COLORS["fragile_crack"], width=2,
        )
        self.canvas.create_line(
            k5[0], k5[1], k2[0], k2[1], k3[0], k3[1], k6[0], k6[1],
            fill=COLORS["fragile_crack"], width=1,
        )

    def _draw_bridge_tile(self, r: int, c: int, is_open: bool) -> None:
        if is_open:
            self._draw_tile_drop_shadow(r, c)
            # Khung dầm cầu bên dưới
            self.draw_prism(
                r, c, r + 1, c + 1,
                -TILE_THICKNESS * 0.65, 0.0,
                top_color=COLORS["bridge_top"],
                left_color=COLORS["bridge_left"],
                front_color=COLORS["bridge_front"],
                border_color="#1F150D",
            )
            # 2 thanh nẹp đồng ngọc bích dọc theo mép cầu
            for u_start, u_end in ((0.04, 0.15), (0.85, 0.96)):
                r00 = self._lerp_tile_point(r, c, u_start, 0.02, 0.01)
                r01 = self._lerp_tile_point(r, c, u_start, 0.98, 0.01)
                r11 = self._lerp_tile_point(r, c, u_end, 0.98, 0.01)
                r10 = self._lerp_tile_point(r, c, u_end, 0.02, 0.01)
                self._draw_poly([r00, r01, r11, r10], fill=COLORS["bridge_rail"], outline="#1A3330")

            # 3 tấm ván cầu ghép ngang có khe hở và mạch cổ ngữ phát sáng
            for v_start, v_end in ((0.08, 0.33), (0.38, 0.62), (0.67, 0.92)):
                p00 = self._lerp_tile_point(r, c, 0.15, v_start, 0.01)
                p01 = self._lerp_tile_point(r, c, 0.15, v_end, 0.01)
                p11 = self._lerp_tile_point(r, c, 0.85, v_end, 0.01)
                p10 = self._lerp_tile_point(r, c, 0.85, v_start, 0.01)
                self._draw_poly(
                    [p00, p01, p11, p10],
                    fill=COLORS["bridge_plank"],
                    outline="#2B1D12",
                    width=1,
                )
                v_mid = (v_start + v_end) * 0.5
                m1 = self._lerp_tile_point(r, c, 0.22, v_mid, 0.02)
                m2 = self._lerp_tile_point(r, c, 0.78, v_mid, 0.02)
                self.canvas.create_line(m1[0], m1[1], m2[0], m2[1], fill=COLORS["bridge_rune"], width=1)
        else:
            # Khi cầu đóng: vẽ 4 ngàm đá góc chữ L định vị vị trí cầu
            corners = [
                (0.06, 0.06, 0.24, 0.24),
                (0.06, 0.76, 0.24, 0.94),
                (0.76, 0.06, 0.94, 0.24),
                (0.76, 0.76, 0.94, 0.94),
            ]
            for u0, v0, u1, v1 in corners:
                c00 = self._lerp_tile_point(r, c, u0, v0, 0.0)
                c01 = self._lerp_tile_point(r, c, u0, v1, 0.0)
                c11 = self._lerp_tile_point(r, c, u1, v1, 0.0)
                c10 = self._lerp_tile_point(r, c, u1, v0, 0.0)
                self._draw_poly(
                    [c00, c01, c11, c10],
                    fill=COLORS["bridge_closed_bracket"],
                    outline=COLORS["bridge_closed_rune"],
                    width=1,
                )

    def _draw_goal_tile(self, r: int, c: int, inner_block_z: Optional[Tuple[float, float]] = None) -> None:
        self._draw_tile_drop_shadow(r, c)
        zb = -TILE_THICKNESS
        t00 = self.project(r, c, 0.0)
        t01 = self.project(r, c + 1, 0.0)
        t11 = self.project(r + 1, c + 1, 0.0)
        t10 = self.project(r + 1, c, 0.0)

        b00 = self.project(r, c, zb)
        b01 = self.project(r, c + 1, zb)
        b11 = self.project(r + 1, c + 1, zb)
        b10 = self.project(r + 1, c, zb)

        # 1. Hố vực sâu và 2 vách đá xây gạch phía sau
        self._draw_poly([t00, t01, t11, t10], fill=COLORS["goal_void"], outline=COLORS["floor_border"])
        self._draw_poly([t00, t01, b01, b00], fill=COLORS["goal_wall_back"], outline="#14110E")
        self._draw_poly([t01, t11, b11, b01], fill=COLORS["goal_wall_right"], outline="#14110E")

        # Đường mạch gạch bên trong lòng giếng đích
        z_step = zb * 0.5
        s00 = self.project(r, c, z_step)
        s01 = self.project(r, c + 1, z_step)
        s11 = self.project(r + 1, c + 1, z_step)
        self.canvas.create_line(s00[0], s00[1], s01[0], s01[1], s11[0], s11[1], fill="#14110E", width=1)

        # 2. Nếu khối đang chui qua lỗ đích
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

        # 3. Vách ngoài và viền bệ thờ khắc cổ ngữ vàng
        self._draw_poly([t00, t10, b10, b00], fill=COLORS["floor_left"], outline=COLORS["floor_border"])
        self._draw_poly([t10, t11, b11, b10], fill=COLORS["floor_front"], outline=COLORS["floor_border"])
        self._draw_stone_side_strata(r, c, zb)

        rim_in = [
            self._lerp_tile_point(r, c, 0.08, 0.08, 0.01),
            self._lerp_tile_point(r, c, 0.08, 0.92, 0.01),
            self._lerp_tile_point(r, c, 0.92, 0.92, 0.01),
            self._lerp_tile_point(r, c, 0.92, 0.08, 0.01),
        ]
        self._draw_poly(rim_in, fill="", outline=COLORS["goal_rune"], width=2)
        self._draw_poly([t00, t01, t11, t10], fill="", outline=COLORS["floor_border"], width=2)

    def _draw_switch_on_tile(self, r: int, c: int, sw_type: str) -> None:
        if sw_type == "soft":
            # Hốc đá bát giác chìm + Đĩa đồng cổ + 4 đinh tán
            octagon_uv = [
                (0.34, 0.16), (0.66, 0.16), (0.84, 0.34), (0.84, 0.66),
                (0.66, 0.84), (0.34, 0.84), (0.16, 0.66), (0.16, 0.34),
            ]
            inner_uv = [
                (0.40, 0.28), (0.60, 0.28), (0.72, 0.40), (0.72, 0.60),
                (0.60, 0.72), (0.40, 0.72), (0.28, 0.60), (0.28, 0.40),
            ]
            pts_base = [self._lerp_tile_point(r, c, u, v, 0.01) for u, v in octagon_uv]
            pts_top = [self._lerp_tile_point(r, c, u, v, 0.05) for u, v in octagon_uv]
            pts_inner = [self._lerp_tile_point(r, c, u, v, 0.06) for u, v in inner_uv]
            self._draw_poly(pts_base, fill=COLORS["sw_socket"], outline=COLORS["sw_soft_rim"], width=2)
            self._draw_poly(pts_top, fill=COLORS["sw_soft_fill"], outline=COLORS["sw_soft_rim"], width=2)
            self._draw_poly(pts_inner, fill=COLORS["sw_soft_inner"], outline=COLORS["gold_accent"], width=1)

        elif sw_type == "heavy":
            # Đế đá tối + Đe sắt/đồng chữ X nổi 3D
            pad = [
                self._lerp_tile_point(r, c, 0.14, 0.14, 0.01),
                self._lerp_tile_point(r, c, 0.14, 0.86, 0.01),
                self._lerp_tile_point(r, c, 0.86, 0.86, 0.01),
                self._lerp_tile_point(r, c, 0.86, 0.14, 0.01),
            ]
            self._draw_poly(pad, fill=COLORS["sw_socket"], outline=COLORS["floor_border"], width=1)

            arm1 = [
                self._lerp_tile_point(r, c, 0.16, 0.26, 0.05),
                self._lerp_tile_point(r, c, 0.26, 0.16, 0.05),
                self._lerp_tile_point(r, c, 0.84, 0.74, 0.05),
                self._lerp_tile_point(r, c, 0.74, 0.84, 0.05),
            ]
            arm2 = [
                self._lerp_tile_point(r, c, 0.74, 0.16, 0.05),
                self._lerp_tile_point(r, c, 0.84, 0.26, 0.05),
                self._lerp_tile_point(r, c, 0.26, 0.84, 0.05),
                self._lerp_tile_point(r, c, 0.16, 0.74, 0.05),
            ]
            self._draw_poly(arm1, fill=COLORS["sw_heavy_top"], outline="#1B1E21", width=2)
            self._draw_poly(arm2, fill=COLORS["sw_heavy_top"], outline="#1B1E21", width=2)
            center_bolt = [
                self._lerp_tile_point(r, c, 0.43, 0.43, 0.06),
                self._lerp_tile_point(r, c, 0.43, 0.57, 0.06),
                self._lerp_tile_point(r, c, 0.57, 0.57, 0.06),
                self._lerp_tile_point(r, c, 0.57, 0.43, 0.06),
            ]
            self._draw_poly(center_bolt, fill=COLORS["gold_accent"], outline="#1B1E21", width=1)

        elif sw_type == "split":
            ring_uv = [
                (0.32, 0.15), (0.68, 0.15), (0.85, 0.32), (0.85, 0.68),
                (0.68, 0.85), (0.32, 0.85), (0.15, 0.68), (0.15, 0.32),
            ]
            pts_base = [self._lerp_tile_point(r, c, u, v, 0.01) for u, v in ring_uv]
            pts_top = [self._lerp_tile_point(r, c, u, v, 0.05) for u, v in ring_uv]
            self._draw_poly(pts_base, fill=COLORS["sw_split_base"], outline="#160F1D", width=2)
            self._draw_poly(
                pts_top,
                fill=COLORS["sw_split_fill"],
                outline=COLORS["sw_split_glow"],
                width=2,
            )

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
            self._draw_bridge_tile(r, c, is_open)
            return

        if tile == TileType.GOAL:
            self._draw_goal_tile(r, c, inner_block_z=goal_inner_z)
            return

        self._draw_tile_drop_shadow(r, c)

        if tile == TileType.FRAGILE:
            self.draw_prism(
                r, c, r + 1, c + 1,
                -TILE_THICKNESS * 0.82, 0.0,
                top_color=COLORS["fragile_top"],
                left_color=COLORS["fragile_left"],
                front_color=COLORS["fragile_front"],
                border_color=COLORS["fragile_border"],
            )
            self._draw_fragile_terracotta_texture(r, c)
        else:
            self.draw_prism(
                r, c, r + 1, c + 1,
                -TILE_THICKNESS, 0.0,
                top_color=COLORS["floor_top"],
                left_color=COLORS["floor_left"],
                front_color=COLORS["floor_front"],
                border_color=COLORS["floor_border"],
            )
            self._draw_stone_side_strata(r, c, -TILE_THICKNESS)
            self._draw_floor_stone_texture(r, c)

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
            self.canvas.create_line(m1[0], m1[1], m2[0], m2[1], fill=COLORS["block_border"], width=2)
            self.canvas.create_line(m2[0], m2[1], m3[0], m3[1], fill=COLORS["block_border"], width=2)

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
            self.canvas.create_line(m1[0], m1[1], m2[0], m2[1], fill=COLORS["block_border"], width=2)
            self.canvas.create_line(m1[0], m1[1], m3[0], m3[1], fill=COLORS["block_border"], width=2)

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
                        text="❖", font=("Segoe UI Symbol", 12, "bold"), fill=COLORS["active_border"],
                    )

    # =========================================================================
    # HÀM RENDER TỔNG THỂ
    # =========================================================================

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
                        -TILE_THICKNESS * 0.82, 0.0,
                        direction=tip_dir,
                        theta=theta_fall * 1.4,
                        offset=(0.0, 0.0, frag_z_off),
                        top_color=COLORS["fragile_top"],
                        left_color=COLORS["fragile_left"],
                        front_color=COLORS["fragile_front"],
                        border_color=COLORS["fragile_border"],
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
