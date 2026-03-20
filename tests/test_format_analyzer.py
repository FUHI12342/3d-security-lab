"""
tests/test_format_analyzer.py

FormatAnalyzer のユニットテスト。
"""

from __future__ import annotations

import math
import struct

import pytest

from tools.format_analyzer import (
    KNOWN_MAGIC,
    FormatAnalyzer,
    compute_entropy,
)


class TestComputeEntropy:
    """compute_entropy() のテスト。"""

    def test_empty_data_returns_zero(self) -> None:
        """空データはエントロピー0を返す。"""
        assert compute_entropy(b"") == 0.0

    def test_uniform_data_max_entropy(self) -> None:
        """全バイトが異なる（均一分布）場合は最大エントロピーに近い。"""
        data = bytes(range(256))
        entropy = compute_entropy(data)
        assert entropy == pytest.approx(8.0, abs=0.01)

    def test_constant_data_zero_entropy(self) -> None:
        """単一バイト繰り返しはエントロピー0。"""
        data = b"\x00" * 1000
        entropy = compute_entropy(data)
        assert entropy == pytest.approx(0.0, abs=0.001)

    def test_two_values_entropy(self) -> None:
        """2値均等混在の場合エントロピー = 1.0。"""
        data = b"\x00\xff" * 500
        entropy = compute_entropy(data)
        assert entropy == pytest.approx(1.0, abs=0.01)

    def test_compressed_data_high_entropy(self) -> None:
        """zlib圧縮データは非圧縮テキストより高エントロピー。"""
        import zlib
        original = b"Hello, World! " * 100
        compressed = zlib.compress(original)
        plain_entropy = compute_entropy(original)
        compressed_entropy = compute_entropy(compressed)
        # 圧縮後はバイト分布が均一化されるため元データより高エントロピーになる
        assert compressed_entropy > plain_entropy

    def test_plain_text_low_entropy(self) -> None:
        """ASCII テキストは低エントロピー。"""
        text = b"abcdefghijklmnopqrstuvwxyz " * 100
        entropy = compute_entropy(text)
        assert entropy < 6.0


class TestFormatAnalyzer:
    """FormatAnalyzer クラスのテスト。"""

    def setup_method(self) -> None:
        self.analyzer = FormatAnalyzer()

    def test_detect_s3d_magic(self) -> None:
        """S3D マジックバイトを正しく検出する。"""
        data = b"S3D\x00" + b"\x00" * 100
        result = self.analyzer.analyze_bytes(data, "test.s3d")
        assert result.detected_format == "S3D Security3D フォーマット"

    def test_detect_png_magic(self) -> None:
        """PNG マジックバイトを正しく検出する。"""
        data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        result = self.analyzer.analyze_bytes(data)
        assert result.detected_format == "PNG画像"

    def test_detect_zlib_magic(self) -> None:
        """zlib マジックバイトを正しく検出する。"""
        data = b"x\x9c" + b"\x00" * 100
        result = self.analyzer.analyze_bytes(data)
        assert result.detected_format is not None
        assert "zlib" in result.detected_format

    def test_unknown_format_returns_none(self) -> None:
        """不明なフォーマットは None を返す。"""
        data = b"\xde\xad\xbe\xef" + b"\xca\xfe" * 50
        result = self.analyzer.analyze_bytes(data)
        assert result.detected_format is None

    def test_file_size_correct(self) -> None:
        """ファイルサイズが正確に返る。"""
        data = b"\x89PNG\r\n\x1a\n" + b"\xab" * 200
        result = self.analyzer.analyze_bytes(data)
        assert result.file_size == len(data)

    def test_entropy_classification_for_random(self) -> None:
        """高エントロピーデータは圧縮/暗号化として分類される。"""
        import secrets
        data = secrets.token_bytes(1024)
        result = self.analyzer.analyze_bytes(data)
        assert result.entropy > 7.0
        assert "圧縮" in result.entropy_classification or "暗号" in result.entropy_classification

    def test_alignment_guess_for_s3d(self) -> None:
        """S3D データ（32バイトストライド）のアライメントを推定する。"""
        # ヘッダー16バイト + 頂点データ（32バイト × n）
        header = b"S3D\x00" + struct.pack("<III", 1, 4, 0)
        vertex_data = struct.pack("<8f", *[1.0] * 8) * 4
        data = header + vertex_data
        result = self.analyzer.analyze_bytes(data)
        assert result.alignment_guess in [4, 8, 16, 32]

    def test_hexdump_format(self) -> None:
        """hexdump が正しいフォーマットで出力される。"""
        data = bytes(range(32))
        dump = FormatAnalyzer.hexdump(data, width=16)
        lines = dump.split("\n")
        assert len(lines) == 2
        assert "00000000" in lines[0]
        # ASCII 部分に | が含まれる
        assert "|" in lines[0]

    def test_hexdump_nonprintable_as_dot(self) -> None:
        """非印字文字はドットで表示される。"""
        data = b"\x00\x01\x02\x03" + b"ABCD"
        dump = FormatAnalyzer.hexdump(data)
        assert "....ABCD" in dump

    def test_summary_contains_key_info(self) -> None:
        """summary() がキー情報を含む。"""
        data = b"S3D\x00" + b"\x00" * 100
        result = self.analyzer.analyze_bytes(data, "model.s3d")
        summary = result.summary()
        assert "model.s3d" in summary
        assert "S3D" in summary

    def test_analyze_file(self, tmp_path, project_root) -> None:
        """実ファイルを analyze() できる。"""
        test_file = tmp_path / "test.bin"
        test_file.write_bytes(b"S3D\x00" + b"\x00" * 50)
        result = self.analyzer.analyze(test_file)
        assert result.file_size == 54
        assert result.detected_format == "S3D Security3D フォーマット"
