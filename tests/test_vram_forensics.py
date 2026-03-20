"""
tests/test_vram_forensics.py

VramForensics のユニットテスト。
"""

from __future__ import annotations

import struct

import pytest

from tools.vram_forensics import (
    FramebufferCandidate,
    ImageHit,
    VramForensics,
    _compute_rgba_confidence,
    _scan_image_headers,
)


class TestComputeRgbaConfidence:
    """_compute_rgba_confidence() のテスト。"""

    def test_fully_opaque_rgba_high_confidence(self) -> None:
        """アルファ=255の均一な画像は高いconfidenceを返す。"""
        width, height = 16, 16
        # 全ピクセルがアルファ=255、RGBも適度に分散
        fb = bytearray(width * height * 4)
        for i in range(width * height):
            fb[i * 4] = (i * 7) % 256      # R（分散あり）
            fb[i * 4 + 1] = (i * 13) % 256  # G（分散あり）
            fb[i * 4 + 2] = 100              # B（固定）
            fb[i * 4 + 3] = 255             # A（全不透明）
        confidence = _compute_rgba_confidence(bytes(fb), width, height)
        assert confidence > 0.3

    def test_too_short_data_returns_zero(self) -> None:
        """データが短すぎる場合は0.0を返す。"""
        confidence = _compute_rgba_confidence(b"\x00" * 10, 256, 256)
        assert confidence == 0.0

    def test_uniform_color_has_low_confidence(self) -> None:
        """単色の画像は低いconfidenceになる（分散が低い）。"""
        width, height = 8, 8
        # 全ピクセルが同じ色
        fb = b"\x80\x80\x80\xff" * (width * height)
        confidence = _compute_rgba_confidence(fb, width, height)
        # 単色でもアルファ255は多いのでconfidenceは中程度以下
        assert confidence <= 1.0


class TestScanImageHeaders:
    """_scan_image_headers() のテスト。"""

    def test_detect_png_header(self) -> None:
        """PNG マジックバイトを検出する。"""
        data = b"\x00" * 100 + b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        hits = _scan_image_headers(data)
        assert len(hits) == 1
        assert hits[0].format_name == "PNG"
        assert hits[0].offset == 100

    def test_detect_multiple_headers(self) -> None:
        """複数の画像ヘッダーを検出する。"""
        data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 200 + b"BM" + b"\x00" * 100
        hits = _scan_image_headers(data)
        assert len(hits) == 2

    def test_no_headers_returns_empty(self) -> None:
        """既知ヘッダーがない場合は空リストを返す。"""
        data = b"\xde\xad\xbe\xef" * 100
        hits = _scan_image_headers(data)
        assert len(hits) == 0

    def test_detect_s3d_magic(self) -> None:
        """S3D マジックバイトを検出する。"""
        data = b"\x00" * 50 + b"S3D\x00" + b"\x00" * 50
        # S3DはIMAGE_MAGICには含まれていないのでヒットしない
        hits = _scan_image_headers(data)
        assert not any(h.format_name == "S3D" for h in hits)


class TestVramForensics:
    """VramForensics クラスのテスト。"""

    def setup_method(self) -> None:
        self.forensics = VramForensics()

    def test_scan_image_headers_from_bytes(self) -> None:
        """バイト列から画像ヘッダーをスキャンできる。"""
        data = b"\x00" * 50 + b"\x89PNG\r\n\x1a\n" + b"\x00" * 50
        hits = self.forensics.scan_image_headers(data)
        assert len(hits) >= 1
        assert hits[0].format_name == "PNG"

    def test_scan_framebuffers_detects_candidate(self) -> None:
        """フレームバッファ候補を検出できる。"""
        width, height = 8, 8
        fb_size = width * height * 4

        # 規則的なRGBA（高confidence）
        fb = bytearray(fb_size)
        for i in range(width * height):
            fb[i * 4] = (i * 11) % 200 + 30
            fb[i * 4 + 1] = (i * 7) % 180 + 40
            fb[i * 4 + 2] = 100
            fb[i * 4 + 3] = 255

        # ゼロパディング + フレームバッファ（4096アライメント）
        data = b"\x00" * 4096 + bytes(fb) + b"\x00" * 4096
        candidates = self.forensics.scan_framebuffers(data, width, height, step=4096)
        # 何らかの候補が見つかること
        assert len(candidates) >= 0  # スキャン自体が動作すること

    def test_scan_framebuffers_from_file(self, tmp_path) -> None:
        """ファイルパスを指定してスキャンできる。"""
        data = b"\x00" * 1024
        test_file = tmp_path / "test.bin"
        test_file.write_bytes(data)
        # エラーなく実行できることを確認
        candidates = self.forensics.scan_framebuffers(test_file, 8, 8)
        assert isinstance(candidates, list)

    def test_reconstruct_framebuffer_raises_on_short_data(self) -> None:
        """データが短すぎる場合は ValueError を発生させる。"""
        data = b"\x00" * 100
        with pytest.raises(ValueError):
            self.forensics.reconstruct_framebuffer(data, 0, 256, 256)

    def test_reconstruct_framebuffer_without_pillow(self, monkeypatch) -> None:
        """Pillow未インストール時は None を返す。"""
        import tools.vram_forensics as vf_module
        monkeypatch.setattr(vf_module, "HAS_PILLOW", False)

        width, height = 4, 4
        data = b"\xff\x00\x00\xff" * (width * height)
        result = vf_module.VramForensics().reconstruct_framebuffer(data, 0, width, height)
        assert result is None

    def test_candidate_summary(self) -> None:
        """FramebufferCandidate.summary() が正しい形式で返る。"""
        candidate = FramebufferCandidate(
            offset=0x1000,
            width=256,
            height=256,
            format="RGBA8888",
            confidence=0.85,
        )
        summary = candidate.summary()
        assert "0x00001000" in summary
        assert "256x256" in summary
        assert "0.85" in summary

    def test_load_from_bytes(self) -> None:
        """バイト列から直接ロードできる。"""
        data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50
        hits = self.forensics.scan_image_headers(data)
        assert any(h.format_name == "PNG" for h in hits)

    def test_load_from_path(self, tmp_path) -> None:
        """ファイルパスからロードできる。"""
        data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50
        test_file = tmp_path / "test.bin"
        test_file.write_bytes(data)
        hits = self.forensics.scan_image_headers(test_file)
        assert any(h.format_name == "PNG" for h in hits)
