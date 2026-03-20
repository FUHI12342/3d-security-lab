# Custom Format Target

## 概要

独自バイナリ3Dフォーマット S3D の実装。
Lab 4 のフォーマット解析演習と CTF Challenge 2 の対象。

## ファイル構成

- `format_spec.md` — フォーマット仕様書（一部意図的に不完全）
- `encoder.py` — エンコーダー（サンプルファイル生成）
- `viewer.py` — デコーダー + 可視化
- `samples/` — サンプルファイル（`generate_samples.py` で生成）

## サンプルファイル生成

```bash
python scripts/generate_samples.py
# または
python targets/custom_format/encoder.py
```

## フォーマット概要

```
Header (16 bytes):
  [0:4]   Magic: "S3D\x00"
  [4:8]   Version: uint32 LE
  [8:12]  Vertex count: uint32 LE
  [12:16] Flags: uint32 LE

Vertex (32 bytes each):
  [0:12]  Position float32 x3
  [12:24] Normal   float32 x3
  [24:32] UV       float32 x2
```

## 使い方

```bash
# デコードして表示
python targets/custom_format/viewer.py targets/custom_format/samples/model_easy.s3d

# 可視化なし
python targets/custom_format/viewer.py targets/custom_format/samples/model_medium.s3d --no-vis
```
