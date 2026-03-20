# Challenge 03: VRAM Recovery

## 難易度: ★★☆

## 問題

`dump.bin` は仮想GPUのVRAMダンプです。
このダンプ内に埋め込まれた **フレームバッファ画像** を復元し、
画像に描かれた **文字列** を答えてください。

## フラグ形式

```
FLAG{text_in_image}
```

text_in_image = 画像内に描かれたテキスト（大文字英数字）

## 手順

1. `tools/format_analyzer.py` でダンプ全体のエントロピーを確認
2. `tools/vram_forensics.py` の `scan_framebuffers()` を使ってフレームバッファを探索
3. 見つかった候補を `reconstruct_framebuffer()` で画像として出力
4. 画像を開いてテキストを読む
5. `FLAG{text_in_image}` 形式で submit

## ヒント

- フレームバッファの解像度は 256×256 ピクセル
- フォーマットは RGBA8888（4バイト/ピクセル）
- スキャンステップを 4096 バイトに設定すると効率的

## コマンド例

```python
from tools.vram_forensics import VramForensics
vf = VramForensics()
candidates = vf.scan_framebuffers("dump.bin", width=256, height=256)
for c in candidates[:3]:
    print(c.summary())
vf.reconstruct_framebuffer("dump.bin", candidates[0].offset, 256, 256, "output.png")
```

## 採点

```bash
python ctf/challenge03_vram_recovery/verify.py "FLAG{3DSEC}"
```
