"""
tools/vram_forensics.py

VRAMダンプのフォレンジクス解析ツール。

機能:
- 既知の画像ヘッダー（PNG/BMP/DDS）をスキャン
- RGBA8888パターンのヒューリスティック検出
- 指定解像度でのフレームバッファ再構成
- PILで画像として出力
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    from PIL import Image
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False


# 既知の画像マジックバイト
IMAGE_MAGIC: list[tuple[bytes, str]] = [
    (b"\x89PNG\r\n\x1a\n", "PNG"),
    (b"BM", "BMP"),
    (b"DDS ", "DDS"),
    (b"\xff\xd8\xff", "JPEG"),
    (b"GIF89a", "GIF89a"),
    (b"GIF87a", "GIF87a"),
]

# RGBA8888 の最小ブロックサイズ（8x8ピクセル × 4バイト）
MIN_RGBA_BLOCK = 8 * 8 * 4

# ファイルサイズ上限（M-3: DoS対策）
MAX_DUMP_SIZE: int = 512 * 1024 * 1024  # 512 MB


@dataclass(frozen=True)
class FramebufferCandidate:
    """フレームバッファ候補を表す不変データクラス。"""
    offset: int
    width: int
    height: int
    format: str  # "RGBA8888"
    confidence: float  # 0.0〜1.0

    def summary(self) -> str:
        """サマリーを返す。"""
        return (
            f"offset=0x{self.offset:08X}, "
            f"{self.width}x{self.height} {self.format}, "
            f"confidence={self.confidence:.2f}"
        )


@dataclass(frozen=True)
class ImageHit:
    """既知フォーマットのヒットを表す不変データクラス。"""
    offset: int
    format_name: str
    magic: bytes


def _compute_rgba_confidence(data: bytes, width: int, height: int) -> float:
    """
    RGBA8888データとして妥当かをヒューリスティックで評価する（0.0〜1.0）。

    評価基準:
    - アルファチャンネルが主に 255 または 0 であること
    - RGB値が広く分布していること
    - 隣接ピクセルの相関が高いこと（急激な変化が少ない）
    """
    size = width * height * 4
    if len(data) < size:
        return 0.0

    chunk = data[:size]
    score = 0.0

    # アルファチャンネルの統計
    alphas = [chunk[i + 3] for i in range(0, size, 4)]
    alpha_255_ratio = sum(1 for a in alphas if a == 255) / len(alphas)
    alpha_0_ratio = sum(1 for a in alphas if a == 0) / len(alphas)

    # 多くのピクセルがアルファ=255（不透明）ならフレームバッファらしい
    if alpha_255_ratio > 0.7:
        score += 0.4
    elif alpha_255_ratio + alpha_0_ratio > 0.8:
        score += 0.2

    # RGB値の分散（単色でないこと）
    r_vals = [chunk[i] for i in range(0, min(size, 1024), 4)]
    g_vals = [chunk[i + 1] for i in range(0, min(size, 1024), 4)]
    b_vals = [chunk[i + 2] for i in range(0, min(size, 1024), 4)]

    r_variance = len(set(r_vals)) / 256
    g_variance = len(set(g_vals)) / 256
    b_variance = len(set(b_vals)) / 256
    avg_variance = (r_variance + g_variance + b_variance) / 3

    # 適度な分散があるとフレームバッファらしい
    if 0.1 < avg_variance < 0.9:
        score += 0.4

    # 隣接ピクセルの差分（急激な変化が少ない = フレームバッファらしい）
    adjacent_diffs = 0
    for i in range(0, min(size - 4, 400), 4):
        diff = abs(chunk[i] - chunk[i + 4])
        if diff < 50:
            adjacent_diffs += 1
    if adjacent_diffs > 80:
        score += 0.2

    return min(score, 1.0)


def _scan_image_headers(data: bytes) -> list[ImageHit]:
    """
    既知の画像ヘッダーをスキャンする。

    Args:
        data: スキャン対象データ

    Returns:
        ImageHit のリスト
    """
    hits: list[ImageHit] = []
    for magic, fmt_name in IMAGE_MAGIC:
        offset = 0
        while True:
            idx = data.find(magic, offset)
            if idx == -1:
                break
            hits.append(ImageHit(offset=idx, format_name=fmt_name, magic=magic))
            offset = idx + 1
    return sorted(hits, key=lambda h: h.offset)


class VramForensics:
    """VRAMダンプのフォレンジクス解析クラス。"""

    def scan_image_headers(self, data_or_path: bytes | str | Path) -> list[ImageHit]:
        """
        VRAMダンプ内の既知画像ヘッダーをスキャンする。

        Args:
            data_or_path: バイト列またはファイルパス

        Returns:
            ImageHit のリスト
        """
        data = self._load(data_or_path)
        return _scan_image_headers(data)

    def scan_framebuffers(
        self,
        data_or_path: bytes | str | Path,
        width: int,
        height: int,
        step: int = 4096,
    ) -> list[FramebufferCandidate]:
        """
        指定解像度のフレームバッファを探索する。

        Args:
            data_or_path: バイト列またはファイルパス
            width: フレームバッファ幅（pixels）
            height: フレームバッファ高さ（pixels）
            step: スキャンステップ（バイト単位、4096=4KBアライメント）

        Returns:
            FramebufferCandidate のリスト（confidence 降順）
        """
        data = self._load(data_or_path)
        fb_size = width * height * 4
        candidates: list[FramebufferCandidate] = []

        if len(data) < fb_size:
            return candidates

        for offset in range(0, len(data) - fb_size + 1, step):
            chunk = data[offset:offset + fb_size]
            confidence = _compute_rgba_confidence(chunk, width, height)
            if confidence > 0.3:
                candidates.append(FramebufferCandidate(
                    offset=offset,
                    width=width,
                    height=height,
                    format="RGBA8888",
                    confidence=confidence,
                ))

        return sorted(candidates, key=lambda c: c.confidence, reverse=True)

    def reconstruct_framebuffer(
        self,
        data_or_path: bytes | str | Path,
        offset: int,
        width: int,
        height: int,
        output_path: Optional[str | Path] = None,
    ) -> Optional[object]:
        """
        VRAMダンプからフレームバッファをRGBA画像として復元する。

        Args:
            data_or_path: バイト列またはファイルパス
            offset: フレームバッファの開始オフセット
            width: フレームバッファ幅
            height: フレームバッファ高さ
            output_path: 出力PNGパス（None の場合は保存しない）

        Returns:
            PIL Image オブジェクト（Pillow未インストールの場合は None）
        """
        data = self._load(data_or_path)
        fb_size = width * height * 4

        if offset + fb_size > len(data):
            raise ValueError(
                f"オフセット {offset:#x} + {fb_size} bytes がダンプサイズを超えています"
            )

        fb_bytes = data[offset:offset + fb_size]

        if not HAS_PILLOW:
            print("[警告] Pillow がインストールされていないため画像復元をスキップします")
            return None

        img = Image.frombytes("RGBA", (width, height), fb_bytes)

        if output_path is not None:
            img.save(str(output_path))
            print(f"フレームバッファ保存: {output_path}")

        return img

    @staticmethod
    def _load(source: bytes | str | Path) -> bytes:
        """バイト列またはファイルパスからデータをロードする。"""
        if isinstance(source, bytes):
            if len(source) > MAX_DUMP_SIZE:
                raise ValueError(
                    f"ダンプサイズが上限を超えています: {len(source)} > {MAX_DUMP_SIZE} bytes"
                )
            return source
        path = Path(source)
        file_size = path.stat().st_size
        if file_size > MAX_DUMP_SIZE:
            raise ValueError(
                f"ファイルサイズが上限を超えています: {file_size} > {MAX_DUMP_SIZE} bytes"
            )
        return path.read_bytes()
