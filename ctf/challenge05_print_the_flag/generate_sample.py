"""
ctf/challenge05_print_the_flag/generate_sample.py

mystery_print.s3d サンプルファイルを生成するスクリプト。

初回セットアップ時や再生成が必要なときに実行する:
  cd /c/_dev/repos/3d-security-lab
  python ctf/challenge05_print_the_flag/generate_sample.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from targets.custom_format.encoder import FLAG_CHECKSUM, FLAG_XOR, FLAG_ZLIB
from targets.custom_format.text3d_generator import generate_text_s3d


def main() -> None:
    """mystery_print.s3d を生成する。"""
    output_dir = Path(__file__).parent
    output_path = output_dir / "mystery_print.s3d"

    # "SEC3D" の3Dテキストを S3D 形式にエンコード
    # XOR + ZLIB + CHECKSUM フラグを使用（チャレンジ難度を高める）
    data = generate_text_s3d(
        text="SEC3D",
        extrude_height=2.0,
        dot_size=1.0,
        flags=FLAG_XOR | FLAG_ZLIB | FLAG_CHECKSUM,
    )

    output_path.write_bytes(data)
    print(f"Generated: {output_path} ({len(data)} bytes)")

    # 検証
    from targets.custom_format.encoder import decode  # noqa: PLC0415
    model = decode(data)
    print(f"Vertex count: {model.vertex_count}")
    print("Sample file generated successfully.")


if __name__ == "__main__":
    main()
