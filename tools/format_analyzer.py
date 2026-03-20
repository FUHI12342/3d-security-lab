"""
tools/format_analyzer.py

バイナリファイルの構造解析ヘルパー。

機能:
- マジックバイトによるフォーマット識別
- エントロピー計算（圧縮/暗号化の検出）
- 繰り返しパターン・アライメントの推定
- hexdump表示
"""

from __future__ import annotations

import math
import struct
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# 既知マジックバイトのデータベース
KNOWN_MAGIC: dict[bytes, str] = {
    b"\x89PNG": "PNG画像",
    b"BM": "BMPビットマップ",
    b"\x00\x00\x00\x0cjP": "JPEG2000",
    b"\xff\xd8\xff": "JPEG画像",
    b"GIF87a": "GIF画像（87a）",
    b"GIF89a": "GIF画像（89a）",
    b"DDS ": "DirectDraw Surface",
    b"PK\x03\x04": "ZIP / glTF-GLB / JAR",
    b"\x1f\x8b": "gzip圧縮",
    b"BZh": "bzip2圧縮",
    b"\xfd7zXZ": "XZ圧縮",
    b"x\x9c": "zlib (デフォルト圧縮)",
    b"x\x01": "zlib (高速圧縮)",
    b"x\xda": "zlib (最高圧縮)",
    b"S3D\x00": "S3D Security3D フォーマット",
    b"glTF": "glTF バイナリ (.glb)",
    b"OBJ ": "Wavefront OBJ",
    b"RIFF": "RIFF コンテナ (WAV/AVI等)",
    b"\x7fELF": "ELF実行形式",
    b"MZ": "PE/DOS実行形式 (Windows)",
    b"\xca\xfe\xba\xbe": "Mach-O Fat Binary",
    b"\xce\xfa\xed\xfe": "Mach-O 32bit LE",
    b"\xcf\xfa\xed\xfe": "Mach-O 64bit LE",
}


@dataclass(frozen=True)
class AnalysisResult:
    """バイナリ解析結果を表す不変データクラス。"""
    file_path: str
    file_size: int
    detected_format: Optional[str]
    magic_bytes: bytes
    entropy: float
    entropy_classification: str
    repeated_patterns: list[tuple[bytes, int]]
    alignment_guess: int
    header_fields: dict[str, int]

    def summary(self) -> str:
        """解析結果のサマリーを文字列で返す。"""
        lines = [
            f"ファイル   : {self.file_path}",
            f"サイズ     : {self.file_size:,} bytes",
            f"フォーマット: {self.detected_format or '不明'}",
            f"マジック   : {self.magic_bytes.hex()} ({self.magic_bytes!r})",
            f"エントロピー: {self.entropy:.4f} bits/byte ({self.entropy_classification})",
            f"アライメント推定: {self.alignment_guess} bytes",
        ]
        if self.repeated_patterns:
            lines.append("繰り返しパターン:")
            for pattern, count in self.repeated_patterns[:3]:
                lines.append(f"  {pattern.hex()} × {count}回")
        return "\n".join(lines)


def compute_entropy(data: bytes) -> float:
    """
    Shannon エントロピーを計算する (bits/byte, 0.0〜8.0)。

    Args:
        data: 解析対象のバイト列

    Returns:
        エントロピー値（bits/byte）
    """
    if not data:
        return 0.0
    count = Counter(data)
    length = len(data)
    entropy = 0.0
    for freq in count.values():
        prob = freq / length
        entropy -= prob * math.log2(prob)
    return entropy


def _classify_entropy(entropy: float) -> str:
    """エントロピー値を分類する。"""
    if entropy < 1.0:
        return "ほぼ定数データ"
    if entropy < 4.0:
        return "構造化データ（テキスト/座標等）"
    if entropy < 6.5:
        return "軽度難読化 or XOR"
    if entropy < 7.5:
        return "中程度圧縮 or 難読化"
    return "高エントロピー（圧縮/暗号化の可能性）"


def _detect_format(data: bytes) -> Optional[str]:
    """マジックバイトでフォーマットを識別する。"""
    for magic, name in KNOWN_MAGIC.items():
        if data[:len(magic)] == magic:
            return name
    return None


def _find_repeated_patterns(data: bytes, pattern_size: int = 4, min_count: int = 3) -> list[tuple[bytes, int]]:
    """
    指定サイズの繰り返しパターンを検出する。

    Args:
        data: 解析対象
        pattern_size: パターンサイズ（bytes）
        min_count: 最小繰り返し回数

    Returns:
        (パターン, 出現回数) のリスト（出現回数の降順）
    """
    counts: Counter[bytes] = Counter()
    for i in range(0, len(data) - pattern_size + 1, pattern_size):
        pattern = data[i:i + pattern_size]
        counts[pattern] += 1

    return [
        (pattern, count)
        for pattern, count in counts.most_common(10)
        if count >= min_count and pattern != b"\x00" * pattern_size
    ]


def _guess_alignment(data: bytes) -> int:
    """
    頂点データのアライメントを推定する。
    4, 8, 12, 16, 32 バイト境界で uniform 分布を確認する。
    """
    candidates = [4, 8, 12, 16, 32]
    best = 4

    # ヘッダー後のデータを解析（先頭16バイトをスキップ）
    payload = data[16:] if len(data) > 16 else data

    for stride in candidates:
        if len(payload) % stride == 0:
            best = stride

    return best


def _parse_header_fields(data: bytes) -> dict[str, int]:
    """
    先頭 16 バイトを汎用的にパースしてフィールドを返す。
    """
    if len(data) < 16:
        return {}

    fields: dict[str, int] = {}
    # 4バイトLEのフィールドを読み取る（汎用的なヘッダー解析）
    for i in range(0, min(16, len(data)), 4):
        value = struct.unpack_from("<I", data, i)[0]
        fields[f"field_{i:02x}"] = value

    return fields


# ファイルサイズ上限（M-4: DoS対策）
_MAX_ANALYSIS_SIZE: int = 64 * 1024 * 1024  # 64 MB


class FormatAnalyzer:
    """バイナリファイル構造解析クラス。"""

    def analyze(self, file_path: str | Path) -> AnalysisResult:
        """
        ファイルを解析してAnalysisResultを返す。

        Args:
            file_path: 解析対象ファイルのパス

        Returns:
            AnalysisResult インスタンス

        Raises:
            ValueError: ファイルサイズが上限を超えている場合
        """
        path = Path(file_path)
        file_size = path.stat().st_size
        if file_size > _MAX_ANALYSIS_SIZE:
            raise ValueError(
                f"ファイルサイズが上限を超えています: {file_size} > {_MAX_ANALYSIS_SIZE} bytes"
            )
        data = path.read_bytes()

        magic = data[:8]
        entropy = compute_entropy(data)
        classification = _classify_entropy(entropy)
        detected_format = _detect_format(data)
        patterns = _find_repeated_patterns(data)
        alignment = _guess_alignment(data)
        header_fields = _parse_header_fields(data)

        return AnalysisResult(
            file_path=str(path),
            file_size=len(data),
            detected_format=detected_format,
            magic_bytes=magic,
            entropy=entropy,
            entropy_classification=classification,
            repeated_patterns=patterns,
            alignment_guess=alignment,
            header_fields=header_fields,
        )

    def analyze_bytes(self, data: bytes, name: str = "<bytes>") -> AnalysisResult:
        """
        バイト列を直接解析する。

        Args:
            data: 解析対象バイト列
            name: 表示用ファイル名

        Returns:
            AnalysisResult インスタンス
        """
        magic = data[:8]
        entropy = compute_entropy(data)
        classification = _classify_entropy(entropy)
        detected_format = _detect_format(data)
        patterns = _find_repeated_patterns(data)
        alignment = _guess_alignment(data)
        header_fields = _parse_header_fields(data)

        return AnalysisResult(
            file_path=name,
            file_size=len(data),
            detected_format=detected_format,
            magic_bytes=magic,
            entropy=entropy,
            entropy_classification=classification,
            repeated_patterns=patterns,
            alignment_guess=alignment,
            header_fields=header_fields,
        )

    @staticmethod
    def hexdump(data: bytes, offset: int = 0, length: int = 256, width: int = 16) -> str:
        """
        hexdump形式の文字列を生成する。

        Args:
            data: 表示するバイト列
            offset: 開始オフセット
            length: 表示バイト数
            width: 1行あたりのバイト数

        Returns:
            hexdump文字列
        """
        chunk = data[offset:offset + length]
        lines: list[str] = []

        for i in range(0, len(chunk), width):
            row = chunk[i:i + width]
            addr = offset + i
            hex_part = " ".join(f"{b:02x}" for b in row)
            # 右側にASCII表示（印字可能文字のみ）
            ascii_part = "".join(
                chr(b) if 0x20 <= b <= 0x7e else "."
                for b in row
            )
            # 16バイト未満の行をパディング
            hex_padded = hex_part.ljust(width * 3 - 1)
            lines.append(f"{addr:08x}  {hex_padded}  |{ascii_part}|")

        return "\n".join(lines)
