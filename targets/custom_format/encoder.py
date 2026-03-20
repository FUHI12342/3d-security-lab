"""
targets/custom_format/encoder.py

S3D (Security 3D) フォーマットのエンコーダー。
教育用独自バイナリフォーマットのエンコード処理を実装する。

フォーマット仕様: format_spec.md を参照
"""

from __future__ import annotations

import hashlib
import secrets
import struct
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

# --- 定数 ---
MAGIC: bytes = b"S3D\x00"
FORMAT_VERSION: int = 1
VERTEX_STRIDE: int = 32  # bytes per vertex (3+3+2 floats × 4 bytes)
VERTEX_FLOATS: int = 8   # floats per vertex

# セキュリティ制限
MAX_VERTEX_COUNT: int = 10_000_000   # 頂点数上限（M-2: メモリ枯渇対策）

# フラグ定義
FLAG_XOR: int = 0x01
FLAG_ZLIB: int = 0x02
FLAG_CHECKSUM: int = 0x04


@dataclass(frozen=True)
class Vertex:
    """1頂点を表す不変データクラス。"""
    position: tuple[float, float, float]
    normal: tuple[float, float, float] = (0.0, 0.0, 1.0)
    uv: tuple[float, float] = (0.0, 0.0)

    def to_bytes(self) -> bytes:
        """32バイトのバイナリ表現に変換する。"""
        return struct.pack(
            "<8f",
            *self.position,
            *self.normal,
            *self.uv,
        )

    @classmethod
    def from_bytes(cls, data: bytes, offset: int = 0) -> "Vertex":
        """32バイトのバイナリから頂点を復元する。"""
        floats = struct.unpack_from("<8f", data, offset)
        return cls(
            position=(floats[0], floats[1], floats[2]),
            normal=(floats[3], floats[4], floats[5]),
            uv=(floats[6], floats[7]),
        )


@dataclass(frozen=True)
class S3DModel:
    """S3Dモデルデータを表す不変データクラス。"""
    vertices: tuple[Vertex, ...]
    version: int = FORMAT_VERSION

    # クラス変数として型ヒントを追加
    _CUBE: ClassVar[tuple[Vertex, ...]]

    @property
    def vertex_count(self) -> int:
        """頂点数を返す。"""
        return len(self.vertices)

    def to_vertex_bytes(self) -> bytes:
        """全頂点データをバイト列に変換する。"""
        return b"".join(v.to_bytes() for v in self.vertices)


def _compute_xor_key(version: int) -> int:
    """XORキーをSHA256から導出する。"""
    version_bytes = struct.pack("<I", version)
    digest = hashlib.sha256(MAGIC + version_bytes).digest()
    return struct.unpack("<I", digest[:4])[0]


def _xor_data(data: bytes, key: int) -> bytes:
    """4バイトXORキーでデータを難読化/復号する。"""
    key_bytes = struct.pack("<I", key)
    result = bytearray(len(data))
    for i, byte in enumerate(data):
        result[i] = byte ^ key_bytes[i % 4]
    return bytes(result)


def encode(model: S3DModel, flags: int = 0) -> bytes:
    """
    S3DModelをバイナリにエンコードする。

    Args:
        model: エンコード対象のモデル
        flags: エンコードフラグ (FLAG_XOR | FLAG_ZLIB | FLAG_CHECKSUM の組み合わせ)

    Returns:
        エンコードされたバイナリデータ
    """
    # 頂点データを生成
    vertex_data: bytes = model.to_vertex_bytes()

    # XOR難読化（bit0）
    if flags & FLAG_XOR:
        xor_key = _compute_xor_key(model.version)
        vertex_data = _xor_data(vertex_data, xor_key)

    # zlib圧縮（bit1）
    if flags & FLAG_ZLIB:
        vertex_data = zlib.compress(vertex_data, level=9)

    # ヘッダー生成（16バイト）
    header = struct.pack(
        "<4sIII",
        MAGIC,
        model.version,
        model.vertex_count,
        flags,
    )

    body = header + vertex_data

    # SHA256チェックサム（bit2）
    if flags & FLAG_CHECKSUM:
        checksum = hashlib.sha256(body).digest()
        body = body + checksum

    return body


def decode(data: bytes) -> S3DModel:
    """
    バイナリからS3DModelにデコードする。

    Args:
        data: デコード対象のバイナリデータ

    Returns:
        デコードされたS3DModel

    Raises:
        ValueError: フォーマットが不正な場合
    """
    if len(data) < 16:
        raise ValueError(f"データが短すぎます: {len(data)} bytes")

    # マジックバイト確認
    if data[:4] != MAGIC:
        raise ValueError(f"不正なマジックバイト: {data[:4]!r}")

    # ヘッダーパース
    _magic, version, vertex_count, flags = struct.unpack_from("<4sIII", data, 0)

    # 頂点数上限チェック（M-2: メモリ枯渇対策）
    if vertex_count > MAX_VERTEX_COUNT:
        raise ValueError(
            f"頂点数が上限を超えています: {vertex_count} > {MAX_VERTEX_COUNT}"
        )

    # チェックサム検証（bit2）
    if flags & FLAG_CHECKSUM:
        if len(data) < 32:
            raise ValueError("チェックサムフィールドが短すぎます")
        body = data[:-32]
        expected_checksum = data[-32:]
        actual_checksum = hashlib.sha256(body).digest()
        if actual_checksum != expected_checksum:
            raise ValueError("SHA256チェックサム不一致")
        vertex_data = body[16:]
    else:
        vertex_data = data[16:]

    # zlib展開（bit1）
    if flags & FLAG_ZLIB:
        expected_size = vertex_count * VERTEX_STRIDE
        vertex_data = zlib.decompress(vertex_data)
        if len(vertex_data) > expected_size * 2:
            raise ValueError("展開データが想定外に大きい（zlib bomb の可能性）")

    # XOR復号（bit0）
    if flags & FLAG_XOR:
        xor_key = _compute_xor_key(version)
        vertex_data = _xor_data(vertex_data, xor_key)

    # 頂点サイズ検証
    expected_size = vertex_count * VERTEX_STRIDE
    if len(vertex_data) != expected_size:
        raise ValueError(
            f"頂点データサイズ不一致: expected {expected_size}, got {len(vertex_data)}"
        )

    # 頂点リスト構築
    vertices = tuple(
        Vertex.from_bytes(vertex_data, i * VERTEX_STRIDE)
        for i in range(vertex_count)
    )

    return S3DModel(vertices=vertices, version=version)


def _make_cube_model() -> S3DModel:
    """教育用サンプルキューブモデルを生成する。"""
    vertices: list[Vertex] = []
    # 6面 × 4頂点 = 24頂点
    face_data = [
        # (法線, 4頂点のUV付き座標)
        ((0, 0, 1), [(-1,-1,1), (1,-1,1), (1,1,1), (-1,1,1)]),
        ((0, 0,-1), [(1,-1,-1), (-1,-1,-1), (-1,1,-1), (1,1,-1)]),
        ((0, 1, 0), [(-1,1,1), (1,1,1), (1,1,-1), (-1,1,-1)]),
        ((0,-1, 0), [(-1,-1,-1), (1,-1,-1), (1,-1,1), (-1,-1,1)]),
        ((1, 0, 0), [(1,-1,1), (1,-1,-1), (1,1,-1), (1,1,1)]),
        ((-1,0, 0), [(-1,-1,-1), (-1,-1,1), (-1,1,1), (-1,1,-1)]),
    ]
    uvs = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]

    for normal, positions in face_data:
        for i, pos in enumerate(positions):
            vertices.append(Vertex(
                position=tuple(float(c) for c in pos),  # type: ignore[arg-type]
                normal=tuple(float(c) for c in normal),  # type: ignore[arg-type]
                uv=uvs[i],
            ))
    return S3DModel(vertices=tuple(vertices))


def generate_samples(output_dir: Path) -> dict[str, Path]:
    """
    3種類のサンプルファイルを生成する。

    Args:
        output_dir: 出力ディレクトリ

    Returns:
        {ファイル名: Pathオブジェクト} の辞書
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    model = _make_cube_model()

    samples: dict[str, int] = {
        "model_easy.s3d": 0x00,                          # 平文
        "model_medium.s3d": FLAG_XOR,                     # XORのみ
        "model_hard.s3d": FLAG_XOR | FLAG_ZLIB | FLAG_CHECKSUM,  # フル
    }

    results: dict[str, Path] = {}
    for filename, flags in samples.items():
        encoded = encode(model, flags)
        out_path = output_dir / filename
        out_path.write_bytes(encoded)
        results[filename] = out_path

    return results


if __name__ == "__main__":
    samples_dir = Path(__file__).parent / "samples"
    generated = generate_samples(samples_dir)
    for name, path in generated.items():
        size = path.stat().st_size
        print(f"Generated: {name} ({size} bytes)")
