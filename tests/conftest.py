"""
tests/conftest.py

pytest 共通フィクスチャ。
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

import pytest

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(scope="session")
def project_root() -> Path:
    """プロジェクトルートのパスを返すフィクスチャ。"""
    return PROJECT_ROOT


@pytest.fixture
def sample_vertex_data_p3() -> bytes:
    """Position only (float32 x3) の頂点データサンプル。"""
    vertices = [
        (0.0, 0.0, 0.0),
        (1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
        (1.0, 1.0, 0.0),
    ]
    data = b""
    for v in vertices:
        data += struct.pack("<3f", *v)
    return data


@pytest.fixture
def sample_vertex_data_p3n3u2() -> bytes:
    """Position + Normal + UV (float32 x8) の頂点データサンプル。"""
    vertices = [
        # pos              normal          uv
        (-1.0, -1.0, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0),
        ( 1.0, -1.0, 1.0, 0.0, 0.0, 1.0, 1.0, 0.0),
        ( 1.0,  1.0, 1.0, 0.0, 0.0, 1.0, 1.0, 1.0),
        (-1.0,  1.0, 1.0, 0.0, 0.0, 1.0, 0.0, 1.0),
    ]
    data = b""
    for v in vertices:
        data += struct.pack("<8f", *v)
    return data


@pytest.fixture
def sample_vram_dump_small() -> bytes:
    """小さなVRAMダンプのサンプル（テスト用）。"""
    # 8×8 RGBA8888 フレームバッファを単純なランダムデータの中に埋め込む
    import secrets

    fb_width, fb_height = 8, 8
    fb_size = fb_width * fb_height * 4

    # フレームバッファ（アルファ=255で規則的なパターン）
    fb = bytearray(fb_size)
    for i in range(0, fb_size, 4):
        fb[i] = 128      # R
        fb[i + 1] = 64   # G
        fb[i + 2] = 200  # B
        fb[i + 3] = 255  # A (fully opaque)

    # ランダムデータ + フレームバッファ
    prefix = secrets.token_bytes(256)
    suffix = secrets.token_bytes(256)
    return prefix + bytes(fb) + suffix
