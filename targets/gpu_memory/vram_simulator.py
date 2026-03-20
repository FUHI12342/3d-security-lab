"""
targets/gpu_memory/vram_simulator.py

仮想VRAMダンプ生成シミュレータ。
実際のGPUメモリには触れず、教育目的のダミーデータを生成する。

生成内容:
- フレームバッファ (RGBA8888): ランダム背景の中にメッセージを描画
- テクスチャ断片: 中程に埋め込み
- VRAMダンプ全体: ランダムデータで周囲を埋める

CTF Challenge 3 の対象ファイルを生成する。
"""

from __future__ import annotations

import secrets
import struct
from pathlib import Path

# Pillow が必要（テクスチャ生成用）
try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False


# VRAM ダンプのパラメータ
DUMP_SIZE: int = 4 * 1024 * 1024   # 4MB（仮想VRAMの一部）
FB_WIDTH: int = 256
FB_HEIGHT: int = 256
FB_PIXEL_SIZE: int = 4             # RGBA8888 = 4 bytes/pixel
FB_SIZE: int = FB_WIDTH * FB_HEIGHT * FB_PIXEL_SIZE  # 256KB

# フレームバッファの埋め込みオフセット（ランダムでは解析しにくいので固定にしておく）
FB_OFFSET: int = 0x180000  # 1.5MB のオフセットに配置

# CTF フラグ文字列（フレームバッファ内の画像に描画する）
CTF_FLAG: str = "3DSEC"


def _create_framebuffer_image() -> bytes:
    """
    RGBA8888 フレームバッファを生成する。
    CTF フラグ文字列をピクセルに描画する。

    Returns:
        RGBA8888 バイト列 (FB_SIZE bytes)
    """
    if not HAS_PILLOW:
        # Pillow がない場合はダミーデータを返す
        fb = bytearray(FB_SIZE)
        # CTF_FLAG を ASCII バイトとして手動で配置（ヒューリスティック検出用）
        for i, ch in enumerate(CTF_FLAG):
            fb[i] = ord(ch)
        return bytes(fb)

    img = Image.new("RGBA", (FB_WIDTH, FB_HEIGHT), (20, 20, 40, 255))
    draw = ImageDraw.Draw(img)

    # グラデーション背景（ランダム性を持つが規則的なパターン）
    for y in range(FB_HEIGHT):
        for x in range(0, FB_WIDTH, 16):
            r = int((x / FB_WIDTH) * 180) + 20
            g = int((y / FB_HEIGHT) * 100)
            b = 160
            draw.point((x, y), fill=(r, g, b, 255))

    # 枠線
    draw.rectangle([0, 0, FB_WIDTH - 1, FB_HEIGHT - 1], outline=(100, 200, 255, 255), width=2)

    # CTFフラグテキストを描画
    try:
        font = ImageFont.truetype("arial.ttf", 32)
    except (IOError, OSError):
        font = ImageFont.load_default()

    text_bbox = draw.textbbox((0, 0), CTF_FLAG, font=font)
    text_w = text_bbox[2] - text_bbox[0]
    text_h = text_bbox[3] - text_bbox[1]
    text_x = (FB_WIDTH - text_w) // 2
    text_y = (FB_HEIGHT - text_h) // 2

    # 影
    draw.text((text_x + 2, text_y + 2), CTF_FLAG, fill=(0, 0, 0, 200), font=font)
    # 本文（明るい白）
    draw.text((text_x, text_y), CTF_FLAG, fill=(255, 255, 255, 255), font=font)

    # RGBA バイト列に変換
    return img.tobytes("raw", "RGBA")


def _create_texture_fragment() -> bytes:
    """
    テクスチャ断片（64×64 RGBA8888）を生成する。
    """
    size = 64 * 64 * 4
    tex = bytearray(size)
    for y in range(64):
        for x in range(64):
            offset = (y * 64 + x) * 4
            # チェッカーパターン
            if (x // 8 + y // 8) % 2 == 0:
                tex[offset:offset + 4] = [255, 128, 0, 255]
            else:
                tex[offset:offset + 4] = [64, 64, 64, 255]
    return bytes(tex)


def generate_vram_dump(output_path: Path) -> None:
    """
    仮想VRAMダンプを生成してファイルに書き込む。

    Args:
        output_path: 出力ファイルパス
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # ランダムデータで全体を埋める（暗号的に安全なランダム）
    dump = bytearray(secrets.token_bytes(DUMP_SIZE))

    # テクスチャ断片を中程に配置
    tex_frag = _create_texture_fragment()
    tex_offset = 0x40000  # 256KB 地点
    dump[tex_offset:tex_offset + len(tex_frag)] = tex_frag

    # フレームバッファを特定オフセットに埋め込む
    fb_data = _create_framebuffer_image()
    dump[FB_OFFSET:FB_OFFSET + len(fb_data)] = fb_data

    output_path.write_bytes(bytes(dump))
    print(f"VRAM dump generated: {output_path} ({DUMP_SIZE // 1024}KB)")
    print(f"  Framebuffer offset: 0x{FB_OFFSET:08X}, size={FB_SIZE}bytes")
    print(f"  Texture fragment offset: 0x{tex_offset:08X}")
    print(f"  Framebuffer resolution: {FB_WIDTH}x{FB_HEIGHT} RGBA8888")


if __name__ == "__main__":
    output = Path(__file__).parent / "samples" / "vram_dump.bin"
    generate_vram_dump(output)
