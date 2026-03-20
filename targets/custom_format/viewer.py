"""
targets/custom_format/viewer.py

S3D フォーマットの正規ビューア。
デコード参考実装 + matplotlib による3D可視化。
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

# encoder モジュールからデコード関数をインポート
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from targets.custom_format.encoder import (
    FLAG_CHECKSUM,
    FLAG_XOR,
    FLAG_ZLIB,
    S3DModel,
    decode,
)


def _describe_flags(flags: int) -> str:
    """フラグを人間が読める形式で説明する。"""
    parts: list[str] = []
    if flags & FLAG_XOR:
        parts.append("XOR難読化")
    if flags & FLAG_ZLIB:
        parts.append("zlib圧縮")
    if flags & FLAG_CHECKSUM:
        parts.append("SHA256チェックサム")
    return " + ".join(parts) if parts else "なし（平文）"


def print_model_info(data: bytes, model: S3DModel) -> None:
    """モデル情報を標準出力に表示する。"""
    # ヘッダーを再パース（表示用）
    _magic, version, vertex_count, flags = struct.unpack_from("<4sIII", data, 0)

    print("=" * 50)
    print("S3D ファイル解析結果")
    print("=" * 50)
    print(f"  マジック  : {_magic!r}")
    print(f"  バージョン: {version}")
    print(f"  頂点数   : {vertex_count}")
    print(f"  フラグ   : {flags:#010x} ({_describe_flags(flags)})")
    print(f"  ファイルサイズ: {len(data)} bytes")
    print()
    print("頂点データ（先頭5頂点）:")
    for i, vtx in enumerate(model.vertices[:5]):
        x, y, z = vtx.position
        print(f"  [{i:2d}] pos=({x:+.3f}, {y:+.3f}, {z:+.3f})")
    if model.vertex_count > 5:
        print(f"  ... 他 {model.vertex_count - 5} 頂点")


def visualize_model(model: S3DModel, title: str = "S3D Model") -> None:
    """matplotlib で3D散布図として可視化する。"""
    try:
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
    except ImportError:
        print("[警告] matplotlib がインストールされていないため可視化をスキップします")
        return

    xs = [v.position[0] for v in model.vertices]
    ys = [v.position[1] for v in model.vertices]
    zs = [v.position[2] for v in model.vertices]

    fig = plt.figure(figsize=(8, 6))
    ax = fig.add_subplot(111, projection="3d")
    ax.scatter(xs, ys, zs, c=zs, cmap="viridis", s=30, alpha=0.8)
    ax.set_title(title)
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Z")
    plt.tight_layout()
    plt.show()


def main() -> None:
    """CLIエントリポイント。"""
    if len(sys.argv) < 2:
        print(f"使い方: python {Path(__file__).name} <file.s3d>")
        sys.exit(1)

    s3d_path = Path(sys.argv[1])
    if not s3d_path.exists():
        print(f"[エラー] ファイルが見つかりません: {s3d_path}")
        sys.exit(1)

    data = s3d_path.read_bytes()

    try:
        model = decode(data)
    except ValueError as exc:
        print(f"[エラー] デコード失敗: {exc}")
        sys.exit(1)

    print_model_info(data, model)

    # 対話モードでなければ可視化スキップ
    if "--no-vis" not in sys.argv:
        visualize_model(model, title=s3d_path.name)


if __name__ == "__main__":
    main()
