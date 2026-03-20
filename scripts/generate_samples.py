"""
scripts/generate_samples.py

サンプルモデル・VRAMダンプ・CTFファイルを一括生成するスクリプト。

生成するファイル:
- targets/custom_format/samples/model_easy.s3d
- targets/custom_format/samples/model_medium.s3d
- targets/custom_format/samples/model_hard.s3d
- targets/gpu_memory/samples/vram_dump.bin
- ctf/challenge02_decode_custom_format/mystery.s3d
- ctf/challenge03_vram_recovery/dump.bin
"""

from __future__ import annotations

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from targets.custom_format.encoder import FLAG_XOR, generate_samples
from targets.gpu_memory.vram_simulator import generate_vram_dump


def main() -> None:
    """全サンプルファイルを生成する。"""
    print("3D Security Lab - Sample file generation")
    print("=" * 50)

    # S3Dサンプルファイル
    print("\n[1/4] Generating S3D sample models...")
    samples_dir = PROJECT_ROOT / "targets" / "custom_format" / "samples"
    generated = generate_samples(samples_dir)
    for name, path in generated.items():
        size = path.stat().st_size
        print(f"  Generated: {path.relative_to(PROJECT_ROOT)} ({size} bytes)")

    # VRAMダンプ
    print("\n[2/4] Generating VRAM dump...")
    vram_path = PROJECT_ROOT / "targets" / "gpu_memory" / "samples" / "vram_dump.bin"
    generate_vram_dump(vram_path)
    print(f"  Generated: {vram_path.relative_to(PROJECT_ROOT)} ({vram_path.stat().st_size:,} bytes)")

    # CTF Challenge 02 の mystery.s3d（XOR難読化版）
    print("\n[3/4] Generating CTF Challenge 02 mystery.s3d...")
    ctf02_dir = PROJECT_ROOT / "ctf" / "challenge02_decode_custom_format"
    ctf02_dir.mkdir(parents=True, exist_ok=True)

    # model_medium.s3d と同じ内容（XOR難読化）を mystery.s3d として配置
    from targets.custom_format.encoder import _make_cube_model, encode
    model = _make_cube_model()
    mystery_data = encode(model, FLAG_XOR)
    mystery_path = ctf02_dir / "mystery.s3d"
    mystery_path.write_bytes(mystery_data)
    print(f"  Generated: {mystery_path.relative_to(PROJECT_ROOT)} ({len(mystery_data)} bytes)")

    # CTF Challenge 03 の dump.bin
    print("\n[4/4] Generating CTF Challenge 03 dump.bin...")
    ctf03_dir = PROJECT_ROOT / "ctf" / "challenge03_vram_recovery"
    ctf03_dir.mkdir(parents=True, exist_ok=True)
    dump_path = ctf03_dir / "dump.bin"
    generate_vram_dump(dump_path)
    print(f"  Generated: {dump_path.relative_to(PROJECT_ROOT)} ({dump_path.stat().st_size:,} bytes)")

    print("\nAll sample files generated!")
    print("To start CTF: python ctf/challengeXX_*/verify.py")


if __name__ == "__main__":
    main()
