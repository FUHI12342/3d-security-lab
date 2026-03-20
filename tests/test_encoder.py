"""
tests/test_encoder.py

S3Dエンコーダー/デコーダーの往復テスト。
encode → decode の一貫性を検証する。
"""

from __future__ import annotations

import hashlib
import struct

import pytest

from targets.custom_format.encoder import (
    FLAG_CHECKSUM,
    FLAG_XOR,
    FLAG_ZLIB,
    MAGIC,
    S3DModel,
    Vertex,
    _compute_xor_key,
    _make_cube_model,
    _xor_data,
    decode,
    encode,
    generate_samples,
)


@pytest.fixture
def cube_model() -> S3DModel:
    """キューブモデルのフィクスチャ。"""
    return _make_cube_model()


@pytest.fixture
def simple_model() -> S3DModel:
    """シンプルな三角形モデル（3頂点）。"""
    vertices = (
        Vertex(position=(0.0, 0.0, 0.0), normal=(0.0, 0.0, 1.0), uv=(0.0, 0.0)),
        Vertex(position=(1.0, 0.0, 0.0), normal=(0.0, 0.0, 1.0), uv=(1.0, 0.0)),
        Vertex(position=(0.5, 1.0, 0.0), normal=(0.0, 0.0, 1.0), uv=(0.5, 1.0)),
    )
    return S3DModel(vertices=vertices)


class TestVertex:
    """Vertex データクラスのテスト。"""

    def test_to_bytes_length(self) -> None:
        """to_bytes() が32バイトを返す。"""
        vtx = Vertex(position=(1.0, 2.0, 3.0))
        assert len(vtx.to_bytes()) == 32

    def test_roundtrip(self) -> None:
        """to_bytes() → from_bytes() の往復で同じ値になる。"""
        vtx = Vertex(
            position=(1.5, -2.3, 0.7),
            normal=(0.0, 1.0, 0.0),
            uv=(0.25, 0.75),
        )
        data = vtx.to_bytes()
        restored = Vertex.from_bytes(data)
        assert restored.position == pytest.approx(vtx.position)
        assert restored.normal == pytest.approx(vtx.normal)
        assert restored.uv == pytest.approx(vtx.uv)

    def test_immutable(self) -> None:
        """Vertex は不変（frozen dataclass）。"""
        vtx = Vertex(position=(1.0, 2.0, 3.0))
        with pytest.raises(Exception):  # FrozenInstanceError
            vtx.position = (0.0, 0.0, 0.0)  # type: ignore[misc]

    def test_default_normal(self) -> None:
        """デフォルト法線は (0, 0, 1)。"""
        vtx = Vertex(position=(0.0, 0.0, 0.0))
        assert vtx.normal == (0.0, 0.0, 1.0)


class TestXorKey:
    """XOR キー生成のテスト。"""

    def test_xor_key_deterministic(self) -> None:
        """同じ入力で常に同じキーを返す。"""
        key1 = _compute_xor_key(1)
        key2 = _compute_xor_key(1)
        assert key1 == key2

    def test_different_versions_different_keys(self) -> None:
        """異なるバージョンは異なるキーを返す。"""
        key1 = _compute_xor_key(1)
        key2 = _compute_xor_key(2)
        assert key1 != key2

    def test_xor_key_from_sha256(self) -> None:
        """XOR キーが SHA256 の先頭4バイトから導出される。"""
        version_bytes = struct.pack("<I", 1)
        expected_digest = hashlib.sha256(MAGIC + version_bytes).digest()
        expected_key = struct.unpack("<I", expected_digest[:4])[0]
        assert _compute_xor_key(1) == expected_key


class TestXorData:
    """_xor_data() のテスト。"""

    def test_xor_invertible(self) -> None:
        """XOR は可逆（同じキーで2回適用すると元に戻る）。"""
        data = b"\xde\xad\xbe\xef" * 8
        key = 0x12345678
        encrypted = _xor_data(data, key)
        decrypted = _xor_data(encrypted, key)
        assert decrypted == data

    def test_xor_changes_data(self) -> None:
        """XOR 適用でデータが変化する（キーが0でない限り）。"""
        data = b"\x00" * 16
        key = 0x01020304
        result = _xor_data(data, key)
        assert result != data

    def test_xor_key_zero_identity(self) -> None:
        """XOR キー = 0 の場合データが変化しない。"""
        data = b"\xde\xad\xbe\xef" * 4
        result = _xor_data(data, 0)
        assert result == data


class TestEncodeDecode:
    """エンコード/デコードの往復テスト。"""

    def test_plain_roundtrip(self, simple_model) -> None:
        """フラグ=0（平文）での往復テスト。"""
        encoded = encode(simple_model, 0)
        decoded = decode(encoded)
        assert decoded.vertex_count == simple_model.vertex_count
        assert decoded.vertices[0].position == pytest.approx(simple_model.vertices[0].position)

    def test_xor_roundtrip(self, simple_model) -> None:
        """XOR難読化での往復テスト。"""
        encoded = encode(simple_model, FLAG_XOR)
        decoded = decode(encoded)
        assert decoded.vertex_count == simple_model.vertex_count
        assert decoded.vertices[0].position == pytest.approx(simple_model.vertices[0].position)

    def test_zlib_roundtrip(self, simple_model) -> None:
        """zlib圧縮での往復テスト。"""
        encoded = encode(simple_model, FLAG_ZLIB)
        decoded = decode(encoded)
        assert decoded.vertex_count == simple_model.vertex_count

    def test_checksum_roundtrip(self, simple_model) -> None:
        """SHA256チェックサムでの往復テスト。"""
        encoded = encode(simple_model, FLAG_CHECKSUM)
        decoded = decode(encoded)
        assert decoded.vertex_count == simple_model.vertex_count

    def test_full_flags_roundtrip(self, simple_model) -> None:
        """XOR + zlib + チェックサム（全フラグ）での往復テスト。"""
        flags = FLAG_XOR | FLAG_ZLIB | FLAG_CHECKSUM
        encoded = encode(simple_model, flags)
        decoded = decode(encoded)
        assert decoded.vertex_count == simple_model.vertex_count
        for i, vtx in enumerate(simple_model.vertices):
            assert decoded.vertices[i].position == pytest.approx(vtx.position, abs=1e-5)

    def test_magic_bytes_correct(self, simple_model) -> None:
        """エンコード結果の先頭マジックが正しい。"""
        encoded = encode(simple_model, 0)
        assert encoded[:4] == MAGIC

    def test_vertex_count_in_header(self, simple_model) -> None:
        """ヘッダーの頂点数フィールドが正しい。"""
        encoded = encode(simple_model, 0)
        _, _, vertex_count, _ = struct.unpack_from("<4sIII", encoded)
        assert vertex_count == simple_model.vertex_count

    def test_invalid_magic_raises(self) -> None:
        """不正なマジックバイトで ValueError が発生する。"""
        bad_data = b"BAD\x00" + b"\x00" * 50
        with pytest.raises(ValueError, match="マジック"):
            decode(bad_data)

    def test_short_data_raises(self) -> None:
        """データが短すぎる場合 ValueError が発生する。"""
        with pytest.raises(ValueError):
            decode(b"S3D\x00")

    def test_checksum_mismatch_raises(self, simple_model) -> None:
        """チェックサム不一致で ValueError が発生する。"""
        encoded = encode(simple_model, FLAG_CHECKSUM)
        # チェックサムを破壊する
        corrupted = bytearray(encoded)
        corrupted[-1] ^= 0xFF
        with pytest.raises(ValueError, match="チェックサム"):
            decode(bytes(corrupted))

    def test_cube_model_vertex_count(self, cube_model) -> None:
        """キューブモデルが24頂点を持つ。"""
        assert cube_model.vertex_count == 24

    def test_cube_model_encode_size(self, cube_model) -> None:
        """キューブの平文エンコードサイズ = 16(ヘッダー) + 24×32(頂点) = 784 bytes。"""
        encoded = encode(cube_model, 0)
        assert len(encoded) == 16 + 24 * 32


class TestGenerateSamples:
    """generate_samples() のテスト。"""

    def test_generates_three_files(self, tmp_path) -> None:
        """3つのサンプルファイルを生成する。"""
        result = generate_samples(tmp_path)
        assert len(result) == 3

    def test_easy_is_plain(self, tmp_path) -> None:
        """model_easy.s3d は平文（フラグ=0）。"""
        generate_samples(tmp_path)
        data = (tmp_path / "model_easy.s3d").read_bytes()
        _, _, _, flags = struct.unpack_from("<4sIII", data)
        assert flags == 0

    def test_medium_has_xor(self, tmp_path) -> None:
        """model_medium.s3d はXOR難読化（bit0=1）。"""
        generate_samples(tmp_path)
        data = (tmp_path / "model_medium.s3d").read_bytes()
        _, _, _, flags = struct.unpack_from("<4sIII", data)
        assert flags & FLAG_XOR

    def test_hard_has_all_flags(self, tmp_path) -> None:
        """model_hard.s3d は全フラグ（bit0|1|2）。"""
        generate_samples(tmp_path)
        data = (tmp_path / "model_hard.s3d").read_bytes()
        _, _, _, flags = struct.unpack_from("<4sIII", data)
        assert flags & FLAG_XOR
        assert flags & FLAG_ZLIB
        assert flags & FLAG_CHECKSUM

    def test_all_files_decodable(self, tmp_path) -> None:
        """生成した全ファイルがデコード可能。"""
        result = generate_samples(tmp_path)
        for name, path in result.items():
            data = path.read_bytes()
            model = decode(data)
            assert model.vertex_count == 24, f"{name}: 頂点数不一致"
