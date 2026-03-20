# GPU Memory Target

## 概要

仮想VRAMダンプシミュレータ。CTF Challenge 3 の対象ファイルを生成します。

実際のGPUメモリには触れず、教育目的のダミーデータのみを扱います。

## 生成

```bash
python scripts/generate_samples.py
# または
python targets/gpu_memory/vram_simulator.py
```

## ダンプ構造

| オフセット | サイズ | 内容 |
|-----------|--------|------|
| 0x000000 | 4MB | ランダムデータ（VRAMダンプ全体） |
| 0x040000 | 16KB | テクスチャ断片（64×64 RGBA8888） |
| 0x180000 | 256KB | フレームバッファ（256×256 RGBA8888） |

## 解析ツール

```bash
python -c "
from tools.vram_forensics import VramForensics
vf = VramForensics()
results = vf.scan_framebuffers('targets/gpu_memory/samples/vram_dump.bin', width=256, height=256)
for r in results:
    print(r)
"
```
