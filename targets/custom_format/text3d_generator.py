"""
targets/custom_format/text3d_generator.py

文字列を3D押し出しテキストの頂点データに変換するヘルパー。

5x7 ドットマトリクスフォント（ASCII 文字）を使用して、
各ドットを立方体（8頂点、12三角形）として生成する。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

# 5x7 ドットマトリクスフォント定義
# 各文字は 7行 x 5列 のビットマップ（上から下、左から右）
# 1 = ドットあり、0 = ドットなし
_FONT_5X7: dict[str, list[str]] = {
    "A": [
        "01110",
        "10001",
        "10001",
        "11111",
        "10001",
        "10001",
        "10001",
    ],
    "B": [
        "11110",
        "10001",
        "10001",
        "11110",
        "10001",
        "10001",
        "11110",
    ],
    "C": [
        "01110",
        "10001",
        "10000",
        "10000",
        "10000",
        "10001",
        "01110",
    ],
    "D": [
        "11110",
        "10001",
        "10001",
        "10001",
        "10001",
        "10001",
        "11110",
    ],
    "E": [
        "11111",
        "10000",
        "10000",
        "11110",
        "10000",
        "10000",
        "11111",
    ],
    "F": [
        "11111",
        "10000",
        "10000",
        "11110",
        "10000",
        "10000",
        "10000",
    ],
    "G": [
        "01110",
        "10001",
        "10000",
        "10111",
        "10001",
        "10001",
        "01110",
    ],
    "H": [
        "10001",
        "10001",
        "10001",
        "11111",
        "10001",
        "10001",
        "10001",
    ],
    "I": [
        "11111",
        "00100",
        "00100",
        "00100",
        "00100",
        "00100",
        "11111",
    ],
    "J": [
        "11111",
        "00010",
        "00010",
        "00010",
        "00010",
        "10010",
        "01100",
    ],
    "K": [
        "10001",
        "10010",
        "10100",
        "11000",
        "10100",
        "10010",
        "10001",
    ],
    "L": [
        "10000",
        "10000",
        "10000",
        "10000",
        "10000",
        "10000",
        "11111",
    ],
    "M": [
        "10001",
        "11011",
        "10101",
        "10101",
        "10001",
        "10001",
        "10001",
    ],
    "N": [
        "10001",
        "11001",
        "10101",
        "10011",
        "10001",
        "10001",
        "10001",
    ],
    "O": [
        "01110",
        "10001",
        "10001",
        "10001",
        "10001",
        "10001",
        "01110",
    ],
    "P": [
        "11110",
        "10001",
        "10001",
        "11110",
        "10000",
        "10000",
        "10000",
    ],
    "Q": [
        "01110",
        "10001",
        "10001",
        "10001",
        "10101",
        "10010",
        "01101",
    ],
    "R": [
        "11110",
        "10001",
        "10001",
        "11110",
        "10100",
        "10010",
        "10001",
    ],
    "S": [
        "01110",
        "10001",
        "10000",
        "01110",
        "00001",
        "10001",
        "01110",
    ],
    "T": [
        "11111",
        "00100",
        "00100",
        "00100",
        "00100",
        "00100",
        "00100",
    ],
    "U": [
        "10001",
        "10001",
        "10001",
        "10001",
        "10001",
        "10001",
        "01110",
    ],
    "V": [
        "10001",
        "10001",
        "10001",
        "10001",
        "10001",
        "01010",
        "00100",
    ],
    "W": [
        "10001",
        "10001",
        "10001",
        "10101",
        "10101",
        "11011",
        "10001",
    ],
    "X": [
        "10001",
        "10001",
        "01010",
        "00100",
        "01010",
        "10001",
        "10001",
    ],
    "Y": [
        "10001",
        "10001",
        "01010",
        "00100",
        "00100",
        "00100",
        "00100",
    ],
    "Z": [
        "11111",
        "00001",
        "00010",
        "00100",
        "01000",
        "10000",
        "11111",
    ],
    "0": [
        "01110",
        "10001",
        "10011",
        "10101",
        "11001",
        "10001",
        "01110",
    ],
    "1": [
        "00100",
        "01100",
        "00100",
        "00100",
        "00100",
        "00100",
        "11111",
    ],
    "2": [
        "01110",
        "10001",
        "00001",
        "00110",
        "01000",
        "10000",
        "11111",
    ],
    "3": [
        "11111",
        "00001",
        "00010",
        "00110",
        "00001",
        "10001",
        "01110",
    ],
    "4": [
        "00010",
        "00110",
        "01010",
        "10010",
        "11111",
        "00010",
        "00010",
    ],
    "5": [
        "11111",
        "10000",
        "11110",
        "00001",
        "00001",
        "10001",
        "01110",
    ],
    "6": [
        "01110",
        "10000",
        "10000",
        "11110",
        "10001",
        "10001",
        "01110",
    ],
    "7": [
        "11111",
        "00001",
        "00010",
        "00100",
        "01000",
        "01000",
        "01000",
    ],
    "8": [
        "01110",
        "10001",
        "10001",
        "01110",
        "10001",
        "10001",
        "01110",
    ],
    "9": [
        "01110",
        "10001",
        "10001",
        "01111",
        "00001",
        "00001",
        "01110",
    ],
    "{": [
        "00110",
        "00100",
        "00100",
        "01000",
        "00100",
        "00100",
        "00110",
    ],
    "}": [
        "01100",
        "00100",
        "00100",
        "00010",
        "00100",
        "00100",
        "01100",
    ],
    "_": [
        "00000",
        "00000",
        "00000",
        "00000",
        "00000",
        "00000",
        "11111",
    ],
    " ": [
        "00000",
        "00000",
        "00000",
        "00000",
        "00000",
        "00000",
        "00000",
    ],
}

# フォントのサイズ定数
FONT_COLS: int = 5
FONT_ROWS: int = 7
CHAR_SPACING: int = 1  # 文字間のギャップ（ドット数）


@dataclass(frozen=True)
class Vertex3D:
    """3D頂点座標を表す不変データクラス。"""
    x: float
    y: float
    z: float

    def as_tuple(self) -> tuple[float, float, float]:
        """タプルとして返す。"""
        return (self.x, self.y, self.z)


@dataclass(frozen=True)
class Triangle3D:
    """3D三角形を表す不変データクラス。"""
    v1: tuple[float, float, float]
    v2: tuple[float, float, float]
    v3: tuple[float, float, float]


def _make_cube_triangles(
    x: float,
    y: float,
    z_bottom: float,
    z_top: float,
    size: float,
) -> list[Triangle3D]:
    """
    指定位置に立方体（直方体）の三角形リストを生成する。

    立方体の各面を2三角形で表現（合計12三角形）。

    Args:
        x: X座標（左下）
        y: Y座標（下）
        z_bottom: Z座標（底面）
        z_top: Z座標（上面）
        size: XY方向のサイズ

    Returns:
        Triangle3D のリスト（12個）
    """
    x0, x1 = x, x + size
    y0, y1 = y, y + size
    z0, z1 = z_bottom, z_top

    # 8頂点
    v000 = (x0, y0, z0)
    v100 = (x1, y0, z0)
    v010 = (x0, y1, z0)
    v110 = (x1, y1, z0)
    v001 = (x0, y0, z1)
    v101 = (x1, y0, z1)
    v011 = (x0, y1, z1)
    v111 = (x1, y1, z1)

    # 6面 × 2三角形 = 12三角形
    faces: list[Triangle3D] = [
        # 上面（Z+）
        Triangle3D(v001, v101, v111),
        Triangle3D(v001, v111, v011),
        # 下面（Z-）
        Triangle3D(v010, v110, v100),
        Triangle3D(v010, v100, v000),
        # 前面（Y-）
        Triangle3D(v000, v100, v101),
        Triangle3D(v000, v101, v001),
        # 背面（Y+）
        Triangle3D(v110, v010, v011),
        Triangle3D(v110, v011, v111),
        # 左面（X-）
        Triangle3D(v010, v000, v001),
        Triangle3D(v010, v001, v011),
        # 右面（X+）
        Triangle3D(v100, v110, v111),
        Triangle3D(v100, v111, v101),
    ]

    return faces


def generate_text_vertices(
    text: str,
    extrude_height: float = 1.0,
    dot_size: float = 1.0,
    char_spacing_mult: float = 1.0,
) -> list[tuple[float, float, float]]:
    """
    文字列を3D押し出しテキストの頂点リスト（三角形ベース）に変換する。

    各文字は 5x7 ドットマトリクスフォントでレンダリングし、
    各ドットを立方体として押し出す。

    Args:
        text: 変換する文字列（大文字・数字・一部記号対応）
        extrude_height: 押し出し高さ（Z方向）
        dot_size: 各ドットのサイズ（XY方向）
        char_spacing_mult: 文字間隔の倍率

    Returns:
        三角形頂点のフラットリスト（3頂点ずつ1三角形）
    """
    triangles: list[Triangle3D] = []

    char_width = (FONT_COLS + CHAR_SPACING) * dot_size * char_spacing_mult
    cursor_x: float = 0.0

    for char in text.upper():
        glyph = _FONT_5X7.get(char, _FONT_5X7.get(" "))
        if glyph is None:
            cursor_x += char_width
            continue

        for row_idx, row in enumerate(glyph):
            # フォントは上から下で定義されているが、
            # 3D空間ではY+が上なので反転する
            y_pos = (FONT_ROWS - 1 - row_idx) * dot_size
            for col_idx, pixel in enumerate(row):
                if pixel == "1":
                    x_pos = cursor_x + col_idx * dot_size
                    cubes = _make_cube_triangles(
                        x=x_pos,
                        y=y_pos,
                        z_bottom=0.0,
                        z_top=extrude_height,
                        size=dot_size,
                    )
                    triangles.extend(cubes)

        cursor_x += char_width

    # フラットな頂点リストに変換
    vertices: list[tuple[float, float, float]] = []
    for tri in triangles:
        vertices.append(tri.v1)
        vertices.append(tri.v2)
        vertices.append(tri.v3)

    return vertices


def generate_text_s3d(
    text: str,
    extrude_height: float = 2.0,
    dot_size: float = 1.0,
    flags: int = 0,
) -> bytes:
    """
    文字列を3D押し出しテキストとして S3D 形式にエンコードする。

    CTF チャレンジ用のヘルパー関数。

    Args:
        text: 変換する文字列
        extrude_height: 押し出し高さ
        dot_size: ドットサイズ
        flags: S3D エンコードフラグ

    Returns:
        S3D エンコードされたバイト列
    """
    import sys
    from pathlib import Path as _Path

    project_root = _Path(__file__).parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from targets.custom_format.encoder import (  # noqa: PLC0415
        S3DModel,
        Vertex,
        encode,
    )

    raw_vertices = generate_text_vertices(
        text,
        extrude_height=extrude_height,
        dot_size=dot_size,
    )

    # 3頂点ずつ三角形の頂点として S3D Vertex に変換
    # S3D は POSITION_NORMAL_UV_F32x8 形式
    vertices: list[Vertex] = []
    for i in range(0, len(raw_vertices) - 2, 3):
        v1 = raw_vertices[i]
        v2 = raw_vertices[i + 1]
        v3 = raw_vertices[i + 2]

        # 法線を外積で計算
        e1 = (v2[0] - v1[0], v2[1] - v1[1], v2[2] - v1[2])
        e2 = (v3[0] - v1[0], v3[1] - v1[1], v3[2] - v1[2])
        nx = e1[1] * e2[2] - e1[2] * e2[1]
        ny = e1[2] * e2[0] - e1[0] * e2[2]
        nz = e1[0] * e2[1] - e1[1] * e2[0]
        length = (nx ** 2 + ny ** 2 + nz ** 2) ** 0.5
        if length > 1e-10:
            nx, ny, nz = nx / length, ny / length, nz / length
        else:
            nx, ny, nz = 0.0, 0.0, 1.0

        for v in (v1, v2, v3):
            vertices.append(
                Vertex(
                    position=(float(v[0]), float(v[1]), float(v[2])),
                    normal=(nx, ny, nz),
                    uv=(0.0, 0.0),
                )
            )

    model = S3DModel(vertices=tuple(vertices))
    return encode(model, flags)
