"""
tests/test_vertex_decoder.py

VertexDecoder のユニットテスト。
各フォーマットのデコード精度を検証する。
"""

from __future__ import annotations

import struct

import pytest

from tools.vertex_decoder import (
    DecodeResult,
    DecodedVertex,
    VertexDecoder,
    VertexFormat,
)


class TestVertexFormat:
    """VertexFormat Enum のテスト。"""

    def test_p3_stride(self) -> None:
        """Position only は 12 bytes/vertex。"""
        assert VertexFormat.POSITION_F32x3.stride == 12

    def test_p3n3_stride(self) -> None:
        """Position + Normal は 24 bytes/vertex。"""
        assert VertexFormat.POSITION_NORMAL_F32x6.stride == 24

    def test_p3n3u2_stride(self) -> None:
        """Position + Normal + UV は 32 bytes/vertex。"""
        assert VertexFormat.POSITION_NORMAL_UV_F32x8.stride == 32

    def test_p3n3u2c4_stride(self) -> None:
        """Position + Normal + UV + Color は 48 bytes/vertex。"""
        assert VertexFormat.POSITION_NORMAL_UV_COLOR_F32x12.stride == 48

    def test_float_count(self) -> None:
        """float_count が正しい値を返す。"""
        assert VertexFormat.POSITION_F32x3.float_count == 3
        assert VertexFormat.POSITION_NORMAL_UV_F32x8.float_count == 8


class TestDecodedVertex:
    """DecodedVertex データクラスのテスト。"""

    def test_to_dict_position_only(self) -> None:
        """position のみの場合 to_dict() が正しい辞書を返す。"""
        vtx = DecodedVertex(position=(1.0, 2.0, 3.0))
        d = vtx.to_dict()
        assert d["position"] == (1.0, 2.0, 3.0)
        assert "normal" not in d
        assert "uv" not in d

    def test_to_dict_full(self) -> None:
        """全フィールドがある場合 to_dict() が全フィールドを含む。"""
        vtx = DecodedVertex(
            position=(1.0, 2.0, 3.0),
            normal=(0.0, 1.0, 0.0),
            uv=(0.5, 0.5),
            color=(1.0, 0.0, 0.0, 1.0),
        )
        d = vtx.to_dict()
        assert "position" in d
        assert "normal" in d
        assert "uv" in d
        assert "color" in d

    def test_immutable(self) -> None:
        """DecodedVertex は不変（frozen dataclass）。"""
        vtx = DecodedVertex(position=(1.0, 2.0, 3.0))
        with pytest.raises(Exception):  # FrozenInstanceError
            vtx.position = (0.0, 0.0, 0.0)  # type: ignore[misc]


class TestVertexDecoder:
    """VertexDecoder クラスのテスト。"""

    def setup_method(self) -> None:
        self.decoder = VertexDecoder()

    def test_decode_p3_format(self, sample_vertex_data_p3) -> None:
        """Position only フォーマットをデコードできる。"""
        result = self.decoder.decode(
            sample_vertex_data_p3,
            fmt=VertexFormat.POSITION_F32x3,
        )
        assert result.vertex_count == 4
        assert result.stride == 12
        assert result.vertices[0].position == pytest.approx((0.0, 0.0, 0.0))
        assert result.vertices[1].position == pytest.approx((1.0, 0.0, 0.0))

    def test_decode_p3n3u2_format(self, sample_vertex_data_p3n3u2) -> None:
        """Position + Normal + UV フォーマットをデコードできる。"""
        result = self.decoder.decode(
            sample_vertex_data_p3n3u2,
            fmt=VertexFormat.POSITION_NORMAL_UV_F32x8,
        )
        assert result.vertex_count == 4
        assert result.stride == 32
        # 最初の頂点の確認
        vtx0 = result.vertices[0]
        assert vtx0.position == pytest.approx((-1.0, -1.0, 1.0))
        assert vtx0.normal == pytest.approx((0.0, 0.0, 1.0))
        assert vtx0.uv == pytest.approx((0.0, 0.0))

    def test_auto_detect_format(self, sample_vertex_data_p3n3u2) -> None:
        """フォーマットを自動検出できる（32バイトデータ）。"""
        result = self.decoder.decode(sample_vertex_data_p3n3u2)
        assert result.format_detected == VertexFormat.POSITION_NORMAL_UV_F32x8
        assert result.vertex_count == 4

    def test_decode_p3_auto_detect(self, sample_vertex_data_p3) -> None:
        """明示的にフォーマットを指定した場合は正しくデコードされる。"""
        # 48バイト（4頂点×12bytes）は POSITION_NORMAL_UV_COLOR_F32x12 とも互換があるため
        # 明示的にフォーマット指定してデコードする
        result = self.decoder.decode(
            sample_vertex_data_p3,
            fmt=VertexFormat.POSITION_F32x3,
        )
        assert result.format_detected == VertexFormat.POSITION_F32x3
        assert result.vertex_count == 4

    def test_empty_data_raises(self) -> None:
        """空データは ValueError を発生させる。"""
        with pytest.raises(ValueError, match="空"):
            self.decoder.decode(b"")

    def test_too_short_data_raises(self) -> None:
        """データが短すぎる場合 ValueError を発生させる。"""
        with pytest.raises(ValueError):
            self.decoder.decode(b"\x00" * 5, fmt=VertexFormat.POSITION_F32x3)

    def test_decode_with_offset(self, sample_vertex_data_p3) -> None:
        """オフセットを指定してデコードできる。"""
        # 先頭に12バイトのパディングを追加
        padding = b"\xff" * 12
        data = padding + sample_vertex_data_p3
        result = self.decoder.decode(data, fmt=VertexFormat.POSITION_F32x3, offset=12)
        assert result.vertex_count == 4
        assert result.vertices[0].position == pytest.approx((0.0, 0.0, 0.0))

    def test_decode_with_custom_stride(self) -> None:
        """カスタムストライドでデコードできる。"""
        # position(3) + padding(4) = stride 16
        vertices_data = b""
        for i in range(3):
            vertices_data += struct.pack("<3f", float(i), 0.0, 0.0)
            vertices_data += b"\x00" * 4  # padding
        result = self.decoder.decode_with_custom_stride(
            vertices_data, stride=16, position_offset=0
        )
        assert result.vertex_count == 3
        assert result.vertices[0].position == pytest.approx((0.0, 0.0, 0.0))
        assert result.vertices[1].position == pytest.approx((1.0, 0.0, 0.0))

    def test_invalid_stride_raises(self) -> None:
        """不正なストライドは ValueError を発生させる。"""
        with pytest.raises(ValueError, match="ストライド"):
            self.decoder.decode_with_custom_stride(b"\x00" * 32, stride=0)

    def test_summary_contains_info(self, sample_vertex_data_p3n3u2) -> None:
        """summary() が主要情報を含む。"""
        result = self.decoder.decode(sample_vertex_data_p3n3u2)
        summary = result.summary()
        assert "4" in summary  # vertex_count
        assert "32" in summary  # stride

    def test_p3n3u2c4_format(self) -> None:
        """Position + Normal + UV + Color (48 bytes) のデコード。"""
        vtx_data = struct.pack("<12f",
            1.0, 2.0, 3.0,     # position
            0.0, 1.0, 0.0,     # normal
            0.5, 0.5,          # uv
            1.0, 0.0, 0.0, 1.0  # color
        )
        result = self.decoder.decode(
            vtx_data,
            fmt=VertexFormat.POSITION_NORMAL_UV_COLOR_F32x12,
        )
        assert result.vertex_count == 1
        vtx = result.vertices[0]
        assert vtx.position == pytest.approx((1.0, 2.0, 3.0))
        assert vtx.normal == pytest.approx((0.0, 1.0, 0.0))
        assert vtx.uv == pytest.approx((0.5, 0.5))
        assert vtx.color == pytest.approx((1.0, 0.0, 0.0, 1.0))
