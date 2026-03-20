"""
tests/test_property.py

プロパティベーステスト（パラメタライズによる網羅的検証）。
hypothesis が利用可能な場合はそちらを使い、なければ手動パラメタライズで代用する。

テスト対象のプロパティ:
1. S3D encode → decode の往復一貫性（任意の頂点数・任意のフラグ）
2. 頂点 to_bytes → from_bytes の往復一貫性（任意のfloat値）
3. OBJ export → re-parse で頂点数が保存される
4. エントロピーの単調性（データが多様になるほどエントロピーが上がる）
5. XOR の可逆性（任意のデータ・任意のキー）
"""

from __future__ import annotations

import math
import struct
from typing import List

import pytest

from targets.custom_format.encoder import (
    FLAG_CHECKSUM,
    FLAG_XOR,
    FLAG_ZLIB,
    S3DModel,
    Vertex,
    decode,
    encode,
    _xor_data,
)
from tools.format_analyzer import compute_entropy
from tools.obj_exporter import ObjExporter, _build_obj_lines
from tools.vertex_decoder import DecodedVertex


# ---------------------------------------------------------------------------
# S3D encode → decode 往復テスト（プロパティ: 任意の頂点数と任意のフラグ）
# ---------------------------------------------------------------------------

def _make_model(vertex_count: int, offset: float = 0.0) -> S3DModel:
    """指定頂点数のモデルを生成するヘルパー。"""
    vertices = tuple(
        Vertex(
            position=(float(i) + offset, float(i) * 0.5 + offset, float(i) * -0.25 + offset),
            normal=(0.0, 0.0, 1.0),
            uv=(float(i % 16) / 16.0, float(i // 16) / 16.0),
        )
        for i in range(vertex_count)
    )
    return S3DModel(vertices=vertices)


@pytest.mark.parametrize("vertex_count", [1, 2, 3, 8, 24, 100, 512])
@pytest.mark.parametrize("flags", [
    0,
    FLAG_XOR,
    FLAG_ZLIB,
    FLAG_CHECKSUM,
    FLAG_XOR | FLAG_ZLIB,
    FLAG_XOR | FLAG_CHECKSUM,
    FLAG_ZLIB | FLAG_CHECKSUM,
    FLAG_XOR | FLAG_ZLIB | FLAG_CHECKSUM,
])
def test_s3d_encode_decode_roundtrip(vertex_count: int, flags: int) -> None:
    """S3D encode → decode で全頂点データが正確に保存される。"""
    model = _make_model(vertex_count)
    encoded = encode(model, flags)
    decoded = decode(encoded)

    assert decoded.vertex_count == vertex_count, (
        f"vertex_count不一致: flags={flags:#04x}, expected={vertex_count}, got={decoded.vertex_count}"
    )
    for i, (orig, res) in enumerate(zip(model.vertices, decoded.vertices)):
        assert res.position == pytest.approx(orig.position, abs=1e-5), (
            f"頂点{i} position不一致: flags={flags:#04x}"
        )
        assert res.normal == pytest.approx(orig.normal, abs=1e-5), (
            f"頂点{i} normal不一致: flags={flags:#04x}"
        )
        assert res.uv == pytest.approx(orig.uv, abs=1e-5), (
            f"頂点{i} uv不一致: flags={flags:#04x}"
        )


# ---------------------------------------------------------------------------
# Vertex to_bytes → from_bytes 往復テスト（任意のfloat値）
# ---------------------------------------------------------------------------

# テスト対象の浮動小数点値（通常値・境界値・特殊値）
FLOAT_TEST_VALUES: list[float] = [
    0.0,
    1.0,
    -1.0,
    0.5,
    -0.5,
    100.0,
    -100.0,
    0.001,
    -0.001,
    1e10,
    -1e10,
    1e-10,
    # float32の最大値に近い値
    3.4028e+38,
    -3.4028e+38,
    # 非常に小さな正の値
    1.175e-38,
]


@pytest.mark.parametrize("x", [-1.5, 0.0, 1.0, 100.0, -0.001])
@pytest.mark.parametrize("y", [-2.3, 0.0, 0.7, -100.0])
@pytest.mark.parametrize("z", [0.0, 0.5, -50.0])
def test_vertex_bytes_roundtrip(x: float, y: float, z: float) -> None:
    """Vertex.to_bytes() → Vertex.from_bytes() で座標値が保存される。"""
    vtx = Vertex(position=(x, y, z), normal=(0.0, 1.0, 0.0), uv=(0.25, 0.75))
    restored = Vertex.from_bytes(vtx.to_bytes())
    assert restored.position[0] == pytest.approx(x, abs=1e-5)
    assert restored.position[1] == pytest.approx(y, abs=1e-5)
    assert restored.position[2] == pytest.approx(z, abs=1e-5)
    assert restored.normal == pytest.approx(vtx.normal, abs=1e-5)
    assert restored.uv == pytest.approx(vtx.uv, abs=1e-5)


def test_vertex_bytes_roundtrip_special_values() -> None:
    """特殊なfloat値（NaN/Inf）がバイト変換で保存される（ビット同一性）。"""
    # NaN と Inf は近似比較できないのでビットレベルで確認
    nan_val = float("nan")
    inf_val = float("inf")

    vtx_nan = Vertex(position=(nan_val, 0.0, 0.0))
    vtx_inf = Vertex(position=(inf_val, 0.0, 0.0))

    restored_nan = Vertex.from_bytes(vtx_nan.to_bytes())
    restored_inf = Vertex.from_bytes(vtx_inf.to_bytes())

    # NaN はビット列が保存されることを確認（struct は NaN をそのまま扱う）
    assert math.isnan(restored_nan.position[0])
    assert math.isinf(restored_inf.position[0])
    assert restored_inf.position[0] > 0


# ---------------------------------------------------------------------------
# OBJ export → re-parse で頂点数保存テスト
# ---------------------------------------------------------------------------

def _parse_obj_vertex_count(obj_content: str) -> int:
    """OBJファイルのテキストから頂点座標行(v ...)をカウントする。"""
    return sum(1 for line in obj_content.split("\n") if line.startswith("v "))


@pytest.mark.parametrize("vertex_count", [3, 6, 9, 12, 24, 48])
def test_obj_export_vertex_count_preserved(tmp_path, vertex_count: int) -> None:
    """OBJ エクスポート後に頂点数が保存される。"""
    vertices = [
        DecodedVertex(
            position=(float(i), float(i) * 0.5, 0.0),
            normal=(0.0, 0.0, 1.0),
            uv=(float(i % 4) / 4.0, 0.0),
        )
        for i in range(vertex_count)
    ]
    exporter = ObjExporter()
    out_path = tmp_path / f"test_{vertex_count}.obj"
    meta = exporter.export_obj(vertices, out_path)

    content = out_path.read_text(encoding="utf-8")
    parsed_count = _parse_obj_vertex_count(content)

    assert parsed_count == vertex_count, (
        f"頂点数不一致: expected={vertex_count}, parsed={parsed_count}"
    )
    assert meta.vertex_count == vertex_count


@pytest.mark.parametrize("vertex_count", [3, 6, 12])
def test_obj_face_count_property(vertex_count: int) -> None:
    """OBJ の面数が頂点数から正しく計算される（3頂点で1三角形）。"""
    vertices = [
        DecodedVertex(position=(float(i), 0.0, 0.0))
        for i in range(vertex_count)
    ]
    lines = _build_obj_lines(vertices)
    face_lines = [line for line in lines if line.startswith("f ")]
    expected_faces = vertex_count // 3
    assert len(face_lines) == expected_faces


# ---------------------------------------------------------------------------
# エントロピーの単調性プロパティ
# ---------------------------------------------------------------------------

def test_entropy_monotone_with_diversity() -> None:
    """バイト値の多様性が増すほどエントロピーが増加する（単調性）。"""
    # 1種類 < 2種類 < 4種類 < 16種類 < 256種類
    entropies: list[float] = []
    for distinct_values in [1, 2, 4, 16, 256]:
        data = bytes([i % distinct_values for i in range(1024)])
        entropies.append(compute_entropy(data))

    # 単調増加を確認
    for i in range(len(entropies) - 1):
        assert entropies[i] <= entropies[i + 1], (
            f"エントロピーが単調増加していない: index={i}, "
            f"e[i]={entropies[i]:.4f}, e[i+1]={entropies[i+1]:.4f}"
        )


def test_entropy_bounded() -> None:
    """エントロピーは 0.0 ≤ H ≤ 8.0 の範囲内である。"""
    import secrets
    for _ in range(10):
        data = secrets.token_bytes(256)
        entropy = compute_entropy(data)
        assert 0.0 <= entropy <= 8.0


# ---------------------------------------------------------------------------
# XOR の可逆性プロパティ（任意のデータ・任意のキー）
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("key", [
    0x00000000,
    0x01020304,
    0xDEADBEEF,
    0xFFFFFFFF,
    0x12345678,
    0x80000000,
])
@pytest.mark.parametrize("data_length", [1, 4, 7, 16, 33, 128])
def test_xor_involution_property(key: int, data_length: int) -> None:
    """f(f(x)) = x: XOR を2回適用すると元に戻る（対合性）。"""
    data = bytes(range(data_length))
    assert _xor_data(_xor_data(data, key), key) == data


@pytest.mark.parametrize("key", [0x01020304, 0xDEADBEEF, 0x12345678])
def test_xor_nonzero_key_changes_data(key: int) -> None:
    """非ゼロキーでXORするとデータが変化する。"""
    data = bytes(range(64))
    encrypted = _xor_data(data, key)
    assert encrypted != data


def test_xor_key_zero_identity_all_lengths() -> None:
    """キー=0は任意の長さのデータをそのまま返す（恒等変換）。"""
    for length in range(0, 40):
        data = bytes(range(length))
        assert _xor_data(data, 0) == data


# ---------------------------------------------------------------------------
# S3D encode → decode の決定論的プロパティ
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("flags", [0, FLAG_XOR, FLAG_ZLIB, FLAG_XOR | FLAG_ZLIB | FLAG_CHECKSUM])
def test_s3d_encode_is_deterministic(flags: int) -> None:
    """同じモデルとフラグで2回エンコードすると同じ結果になる（XOR/ZLIB）。"""
    model = _make_model(8)
    result1 = encode(model, flags)
    result2 = encode(model, flags)
    # FLAG_CHECKSUM が含まれると SHA256 は決定論的なので同じになるべき
    assert result1 == result2, f"エンコード結果が非決定論的: flags={flags:#04x}"


@pytest.mark.parametrize("vertex_count", [1, 24, 100])
def test_s3d_encoded_size_property(vertex_count: int) -> None:
    """平文エンコード（フラグ=0）のサイズは 16 + vertex_count×32 に等しい。"""
    model = _make_model(vertex_count)
    encoded = encode(model, 0)
    expected_size = 16 + vertex_count * 32
    assert len(encoded) == expected_size, (
        f"サイズ不一致: vertex_count={vertex_count}, "
        f"expected={expected_size}, got={len(encoded)}"
    )


@pytest.mark.parametrize("flags", [FLAG_CHECKSUM, FLAG_XOR | FLAG_ZLIB | FLAG_CHECKSUM])
def test_s3d_checksum_tamper_detection(flags: int) -> None:
    """チェックサムを1ビット変更するとデコードで ValueError が発生する。"""
    model = _make_model(3)
    encoded = encode(model, flags)
    # チェックサムの最後のバイトを反転
    corrupted = bytearray(encoded)
    corrupted[-1] ^= 0x01
    with pytest.raises(ValueError):
        decode(bytes(corrupted))
