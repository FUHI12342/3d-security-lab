"""
tools/vertex_decoder.py

頂点バッファデコーダー。各種頂点フォーマットに対応。

対応フォーマット:
- POSITION_F32x3           (12 bytes/vertex)
- POSITION_NORMAL_F32x6    (24 bytes/vertex)
- POSITION_NORMAL_UV_F32x8 (32 bytes/vertex)
- POSITION_NORMAL_UV_COLOR_F32x12 (48 bytes/vertex)
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class VertexFormat(Enum):
    """頂点フォーマット定義。"""
    POSITION_F32x3 = "3f"           # 12 bytes
    POSITION_NORMAL_F32x6 = "6f"    # 24 bytes
    POSITION_NORMAL_UV_F32x8 = "8f" # 32 bytes
    POSITION_NORMAL_UV_COLOR_F32x12 = "12f"  # 48 bytes

    @property
    def stride(self) -> int:
        """1頂点のバイト数を返す。"""
        return struct.calcsize("<" + self.value)

    @property
    def float_count(self) -> int:
        """1頂点のfloat数を返す。"""
        return int(self.value.replace("f", ""))


@dataclass(frozen=True)
class DecodedVertex:
    """デコードされた頂点データを表す不変データクラス。"""
    position: tuple[float, float, float]
    normal: Optional[tuple[float, float, float]] = None
    uv: Optional[tuple[float, float]] = None
    color: Optional[tuple[float, float, float, float]] = None

    def to_dict(self) -> dict[str, object]:
        """辞書形式に変換する。"""
        result: dict[str, object] = {"position": self.position}
        if self.normal is not None:
            result["normal"] = self.normal
        if self.uv is not None:
            result["uv"] = self.uv
        if self.color is not None:
            result["color"] = self.color
        return result


@dataclass(frozen=True)
class DecodeResult:
    """デコード結果全体を表す不変データクラス。"""
    vertices: tuple[DecodedVertex, ...]
    format_detected: VertexFormat
    stride: int
    vertex_count: int
    endian: str  # "little" or "big"

    def summary(self) -> str:
        """サマリーを返す。"""
        return (
            f"頂点数: {self.vertex_count}, "
            f"フォーマット: {self.format_detected.name}, "
            f"ストライド: {self.stride} bytes, "
            f"エンディアン: {self.endian}"
        )


def _detect_endian(data: bytes, stride: int) -> str:
    """
    エンディアンを推定する。
    浮動小数点の範囲（-100〜100）に収まる解釈を優先する。
    """
    if len(data) < stride:
        return "little"

    le_ok = 0
    be_ok = 0

    for i in range(min(len(data) // stride, 10)):
        offset = i * stride
        try:
            le_val = struct.unpack_from("<f", data, offset)[0]
            be_val = struct.unpack_from(">f", data, offset)[0]
            if abs(le_val) < 1000:
                le_ok += 1
            if abs(be_val) < 1000:
                be_ok += 1
        except struct.error:
            pass

    return "little" if le_ok >= be_ok else "big"


def _detect_format(data: bytes) -> VertexFormat:
    """
    バイト列から頂点フォーマットを自動検出する。
    データサイズから最も適合するフォーマットを選ぶ。
    """
    size = len(data)

    # 各フォーマットで割り切れるかチェック
    for fmt in [
        VertexFormat.POSITION_NORMAL_UV_F32x8,    # 32 bytes
        VertexFormat.POSITION_NORMAL_UV_COLOR_F32x12,  # 48 bytes
        VertexFormat.POSITION_NORMAL_F32x6,        # 24 bytes
        VertexFormat.POSITION_F32x3,               # 12 bytes
    ]:
        if size % fmt.stride == 0 and size >= fmt.stride:
            return fmt

    return VertexFormat.POSITION_F32x3


def _parse_floats(data: bytes, offset: int, count: int, endian: str) -> tuple[float, ...]:
    """指定オフセットからfloat列を読む。"""
    fmt_char = "<" if endian == "little" else ">"
    return struct.unpack_from(f"{fmt_char}{count}f", data, offset)


def _decode_vertex(
    data: bytes,
    offset: int,
    fmt: VertexFormat,
    endian: str,
) -> DecodedVertex:
    """1頂点をデコードする。"""
    floats = _parse_floats(data, offset, fmt.float_count, endian)

    if fmt == VertexFormat.POSITION_F32x3:
        return DecodedVertex(position=(floats[0], floats[1], floats[2]))

    elif fmt == VertexFormat.POSITION_NORMAL_F32x6:
        return DecodedVertex(
            position=(floats[0], floats[1], floats[2]),
            normal=(floats[3], floats[4], floats[5]),
        )

    elif fmt == VertexFormat.POSITION_NORMAL_UV_F32x8:
        return DecodedVertex(
            position=(floats[0], floats[1], floats[2]),
            normal=(floats[3], floats[4], floats[5]),
            uv=(floats[6], floats[7]),
        )

    elif fmt == VertexFormat.POSITION_NORMAL_UV_COLOR_F32x12:
        return DecodedVertex(
            position=(floats[0], floats[1], floats[2]),
            normal=(floats[3], floats[4], floats[5]),
            uv=(floats[6], floats[7]),
            color=(floats[8], floats[9], floats[10], floats[11]),
        )

    # フォールバック（到達しない）
    return DecodedVertex(position=(floats[0], floats[1], floats[2]))


class VertexDecoder:
    """頂点バッファデコーダークラス。"""

    def decode(
        self,
        data: bytes,
        fmt: Optional[VertexFormat] = None,
        stride: Optional[int] = None,
        offset: int = 0,
        endian: Optional[str] = None,
    ) -> DecodeResult:
        """
        頂点バッファをデコードする。

        Args:
            data: 頂点バッファのバイト列
            fmt: 頂点フォーマット（None の場合は自動検出）
            stride: バイトストライド（None の場合は fmt から自動計算）
            offset: 開始バイトオフセット
            endian: "little" or "big"（None の場合は自動検出）

        Returns:
            DecodeResult インスタンス

        Raises:
            ValueError: データが不正な場合
        """
        payload = data[offset:]

        if not payload:
            raise ValueError("デコード対象データが空です")

        # フォーマット自動検出
        detected_fmt = fmt if fmt is not None else _detect_format(payload)
        actual_stride = stride if stride is not None else detected_fmt.stride
        detected_endian = endian if endian is not None else _detect_endian(payload, actual_stride)

        if len(payload) < actual_stride:
            raise ValueError(
                f"データが短すぎます: {len(payload)} bytes < stride {actual_stride}"
            )

        vertex_count = len(payload) // actual_stride

        vertices = tuple(
            _decode_vertex(payload, i * actual_stride, detected_fmt, detected_endian)
            for i in range(vertex_count)
        )

        return DecodeResult(
            vertices=vertices,
            format_detected=detected_fmt,
            stride=actual_stride,
            vertex_count=vertex_count,
            endian=detected_endian,
        )

    def decode_with_custom_stride(
        self,
        data: bytes,
        stride: int,
        position_offset: int = 0,
        normal_offset: Optional[int] = None,
        uv_offset: Optional[int] = None,
    ) -> DecodeResult:
        """
        カスタムストライドとオフセットで頂点データをデコードする。

        Args:
            data: 頂点バッファ
            stride: 1頂点のバイト数
            position_offset: 位置データのオフセット
            normal_offset: 法線データのオフセット（None で省略）
            uv_offset: UVデータのオフセット（None で省略）

        Returns:
            DecodeResult インスタンス
        """
        if stride <= 0:
            raise ValueError(f"ストライドが不正です: {stride}")
        if len(data) < stride:
            raise ValueError(f"データが短すぎます: {len(data)} < {stride}")

        vertex_count = len(data) // stride
        vertices: list[DecodedVertex] = []

        for i in range(vertex_count):
            base = i * stride

            pos = struct.unpack_from("<3f", data, base + position_offset)
            normal = None
            uv = None

            if normal_offset is not None and base + normal_offset + 12 <= len(data):
                normal = struct.unpack_from("<3f", data, base + normal_offset)

            if uv_offset is not None and base + uv_offset + 8 <= len(data):
                uv = struct.unpack_from("<2f", data, base + uv_offset)

            vertices.append(DecodedVertex(
                position=(pos[0], pos[1], pos[2]),
                normal=normal,
                uv=uv,
            ))

        # フォーマットを推定
        if uv_offset is not None:
            detected_fmt = VertexFormat.POSITION_NORMAL_UV_F32x8
        elif normal_offset is not None:
            detected_fmt = VertexFormat.POSITION_NORMAL_F32x6
        else:
            detected_fmt = VertexFormat.POSITION_F32x3

        return DecodeResult(
            vertices=tuple(vertices),
            format_detected=detected_fmt,
            stride=stride,
            vertex_count=vertex_count,
            endian="little",
        )
