"""
tools/stl_converter.py

STL変換CLIツール — 各種3DフォーマットをSTLに変換する。

使用例:
  python -m tools.stl_converter input.obj output.stl
  python -m tools.stl_converter input.s3d output.stl --scale 50
  python -m tools.stl_converter input.obj output.stl --ascii --validate
  python -m tools.stl_converter input.gltf output.stl --center --info
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _load_mesh(input_path: Path, exporter):  # type: ignore[no-untyped-def]
    """入力ファイルの拡張子に応じて適切なローダーを呼ぶ。"""
    suffix = input_path.suffix.lower()

    if suffix == ".obj":
        return exporter.from_obj_file(input_path)
    elif suffix == ".s3d":
        return exporter.from_s3d_file(input_path)
    elif suffix in (".gltf", ".glb"):
        return exporter.from_gltf_file(input_path)
    else:
        print(
            f"ERROR: 未対応の入力形式です: {suffix}\n"
            "対応形式: .obj, .s3d, .gltf, .glb",
            file=sys.stderr,
        )
        sys.exit(1)


def main() -> None:
    """CLIエントリポイント。"""
    parser = argparse.ArgumentParser(
        description="3DファイルをSTLに変換（3Dプリント用）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python -m tools.stl_converter model.obj output.stl
  python -m tools.stl_converter model.s3d output.stl --scale 50 --center
  python -m tools.stl_converter model.obj output.stl --ascii --validate
  python -m tools.stl_converter model.gltf output.stl --info
        """,
    )
    parser.add_argument(
        "input",
        help="入力ファイル (.obj, .s3d, .gltf, .glb)",
    )
    parser.add_argument(
        "output",
        nargs="?",
        default=None,
        help="出力STLファイルパス（--info 使用時は省略可）",
    )
    parser.add_argument(
        "--ascii",
        action="store_true",
        help="ASCII形式で出力（デフォルト: Binary）",
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=0.0,
        help="スケール調整（mm単位の最大辺長、0=変換なし）",
    )
    parser.add_argument(
        "--center",
        action="store_true",
        help="原点に中心移動",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="3Dプリント適性チェック実行",
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="メッシュ情報表示のみ（変換しない）",
    )

    args = parser.parse_args()

    # --info 以外では output は必須
    if not args.info and args.output is None:
        parser.error("output を指定してください（--info の場合は省略可）")

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: 入力ファイルが存在しません: {input_path}", file=sys.stderr)
        sys.exit(1)

    # STLExporter をインポート
    try:
        from tools.stl_exporter import STLExporter  # noqa: PLC0415
    except ImportError:
        # スクリプト直接実行時のフォールバック
        import sys as _sys
        from pathlib import Path as _Path
        _sys.path.insert(0, str(_Path(__file__).parent.parent))
        from tools.stl_exporter import STLExporter  # noqa: PLC0415

    exporter = STLExporter()

    # ファイル読み込み
    print(f"読み込み中: {input_path}")
    try:
        mesh = _load_mesh(input_path, exporter)
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"  メッシュ名: {mesh.name}")
    print(f"  三角形数: {mesh.triangle_count}")

    bb_min, bb_max = mesh.bounding_box
    dims = (
        bb_max[0] - bb_min[0],
        bb_max[1] - bb_min[1],
        bb_max[2] - bb_min[2],
    )
    print(
        f"  バウンディングボックス: "
        f"{dims[0]:.3f} x {dims[1]:.3f} x {dims[2]:.3f}"
    )

    # バリデーション
    if args.validate or args.info:
        print("\n3Dプリント適性チェック:")
        warnings = exporter.validate_for_printing(mesh)
        if warnings:
            for w in warnings:
                print(f"  {w}")
        else:
            print("  問題なし。3Dプリント可能です。")

    # --info のみの場合はここで終了
    if args.info:
        return

    # スケール調整
    if args.scale > 0:
        mesh = STLExporter.scale_to_mm(mesh, args.scale)
        bb_min2, bb_max2 = mesh.bounding_box
        dims2 = (
            bb_max2[0] - bb_min2[0],
            bb_max2[1] - bb_min2[1],
            bb_max2[2] - bb_min2[2],
        )
        print(
            f"\nスケール後: {dims2[0]:.3f} x {dims2[1]:.3f} x {dims2[2]:.3f} mm"
        )

    # 原点移動
    if args.center:
        mesh = STLExporter.center_origin(mesh)
        print("原点に中心移動しました。")

    # 出力
    output_path = Path(args.output)
    print(f"\n出力中: {output_path}")

    try:
        if args.ascii:
            out = exporter.export_ascii(mesh, output_path)
            fmt = "ASCII"
        else:
            out = exporter.export_binary(mesh, output_path)
            fmt = "Binary"
    except OSError as e:
        print(f"ERROR: 出力に失敗しました: {e}", file=sys.stderr)
        sys.exit(1)

    file_size = out.stat().st_size
    print(
        f"完了: {out} ({fmt} STL, {file_size:,} bytes, "
        f"{mesh.triangle_count} 三角形)"
    )


if __name__ == "__main__":
    main()
