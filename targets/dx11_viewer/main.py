"""
targets/dx11_viewer/main.py

Python + moderngl を使った簡易3Dビューア。
Lab 1 (RenderDoc) および Lab 2 (apitrace) のキャプチャ対象。
"""

from __future__ import annotations

import math
import struct
from pathlib import Path

# moderngl が未インストールの場合でも import だけは試みる（テスト用スタブ）
try:
    import moderngl
    import pygame
    HAS_MODERNGL = True
except ImportError:
    HAS_MODERNGL = False


# ---- 頂点データ定義 ------------------------------------------------

# キューブの頂点: position(3) + normal(3) + uv(2) = 8 floats = 32 bytes
_CUBE_VERTICES: list[tuple[float, ...]] = [
    # 前面 (z=+1)
    (-1, -1,  1,  0,  0,  1,  0.0, 0.0),
    ( 1, -1,  1,  0,  0,  1,  1.0, 0.0),
    ( 1,  1,  1,  0,  0,  1,  1.0, 1.0),
    (-1,  1,  1,  0,  0,  1,  0.0, 1.0),
    # 後面 (z=-1)
    ( 1, -1, -1,  0,  0, -1,  0.0, 0.0),
    (-1, -1, -1,  0,  0, -1,  1.0, 0.0),
    (-1,  1, -1,  0,  0, -1,  1.0, 1.0),
    ( 1,  1, -1,  0,  0, -1,  0.0, 1.0),
    # 上面 (y=+1)
    (-1,  1,  1,  0,  1,  0,  0.0, 0.0),
    ( 1,  1,  1,  0,  1,  0,  1.0, 0.0),
    ( 1,  1, -1,  0,  1,  0,  1.0, 1.0),
    (-1,  1, -1,  0,  1,  0,  0.0, 1.0),
    # 下面 (y=-1)
    (-1, -1, -1,  0, -1,  0,  0.0, 0.0),
    ( 1, -1, -1,  0, -1,  0,  1.0, 0.0),
    ( 1, -1,  1,  0, -1,  0,  1.0, 1.0),
    (-1, -1,  1,  0, -1,  0,  0.0, 1.0),
    # 右面 (x=+1)
    ( 1, -1,  1,  1,  0,  0,  0.0, 0.0),
    ( 1, -1, -1,  1,  0,  0,  1.0, 0.0),
    ( 1,  1, -1,  1,  0,  0,  1.0, 1.0),
    ( 1,  1,  1,  1,  0,  0,  0.0, 1.0),
    # 左面 (x=-1)
    (-1, -1, -1, -1,  0,  0,  0.0, 0.0),
    (-1, -1,  1, -1,  0,  0,  1.0, 0.0),
    (-1,  1,  1, -1,  0,  0,  1.0, 1.0),
    (-1,  1, -1, -1,  0,  0,  0.0, 1.0),
]

# 各面を2三角形で分割するインデックス（6面 × 4頂点 → 6面 × 6インデックス）
_CUBE_INDICES: list[int] = []
for face in range(6):
    base = face * 4
    _CUBE_INDICES.extend([
        base, base + 1, base + 2,
        base, base + 2, base + 3,
    ])


def build_vertex_buffer() -> bytes:
    """頂点データを packed bytes に変換する。"""
    buf = bytearray()
    for vtx in _CUBE_VERTICES:
        buf += struct.pack("<8f", *vtx)
    return bytes(buf)


def build_index_buffer() -> bytes:
    """インデックスデータを packed bytes に変換する。"""
    return struct.pack(f"<{len(_CUBE_INDICES)}I", *_CUBE_INDICES)


def load_shader(name: str) -> str:
    """シェーダーファイルをロードする。"""
    shader_path = Path(__file__).parent / "shaders" / name
    if shader_path.exists():
        return shader_path.read_text(encoding="utf-8")
    # フォールバック：組み込みシェーダー
    if name == "vertex.glsl":
        return _FALLBACK_VERT
    return _FALLBACK_FRAG


_FALLBACK_VERT = """
#version 330 core
in vec3 in_position;
in vec3 in_normal;
in vec2 in_uv;
uniform mat4 u_mvp;
out vec3 v_normal;
out vec2 v_uv;
void main() {
    gl_Position = u_mvp * vec4(in_position, 1.0);
    v_normal = in_normal;
    v_uv = in_uv;
}
"""

_FALLBACK_FRAG = """
#version 330 core
in vec3 v_normal;
in vec2 v_uv;
out vec4 fragColor;
void main() {
    vec3 light = normalize(vec3(1.0, 2.0, 3.0));
    float diff = max(dot(normalize(v_normal), light), 0.1);
    fragColor = vec4(vec3(1.0, 0.5, 0.0) * diff, 1.0);
}
"""


def make_mvp(angle_rad: float) -> list[float]:
    """簡易MVPマトリクスを生成する（Y軸回転）。"""
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    # 回転行列（Y軸）× 透視投影（簡易）
    # 列優先 (column-major)
    return [
        cos_a, 0.0, -sin_a, 0.0,
        0.0,   1.0,  0.0,   0.0,
        sin_a, 0.0,  cos_a, 0.0,
        0.0,   0.0, -5.0,   1.0,
    ]


def run_viewer() -> None:
    """ビューアを起動してウィンドウを表示する。"""
    if not HAS_MODERNGL:
        print("[dx11_viewer] moderngl/pygame が未インストールのため起動をスキップ")
        return

    pygame.init()
    pygame.display.set_mode((800, 600), pygame.OPENGL | pygame.DOUBLEBUF)
    pygame.display.set_caption("3D Security Lab - DX11 Viewer Target")

    ctx = moderngl.create_context()
    ctx.enable(moderngl.DEPTH_TEST)

    prog = ctx.program(
        vertex_shader=load_shader("vertex.glsl"),
        fragment_shader=load_shader("fragment.glsl"),
    )

    vbo = ctx.buffer(build_vertex_buffer())
    ibo = ctx.buffer(build_index_buffer())

    vao = ctx.vertex_array(
        prog,
        [(vbo, "3f 3f 2f", "in_position", "in_normal", "in_uv")],
        ibo,
    )

    clock = pygame.time.Clock()
    angle = 0.0

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        ctx.clear(0.1, 0.1, 0.15)
        angle += 0.01

        if "u_mvp" in prog:
            prog["u_mvp"].write(struct.pack("<16f", *make_mvp(angle)))

        vao.render(moderngl.TRIANGLES)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    run_viewer()
