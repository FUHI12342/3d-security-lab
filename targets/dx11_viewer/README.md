# DX11 Viewer Target

## 概要

Python + moderngl を使った簡易3Dビューア。
RenderDoc / apitrace のキャプチャ対象として設計されています。

## 起動方法

```bash
pip install moderngl pygame
python targets/dx11_viewer/main.py
```

## 頂点フォーマット

```
stride = 32 bytes
  offset  0: position  (float32 x3)
  offset 12: normal    (float32 x3)
  offset 24: uv        (float32 x2)
```

頂点数: 24（6面 × 4頂点）
インデックス数: 36（6面 × 2三角形 × 3頂点）

## ファイル構成

- `main.py` — メインビューアロジック
- `shaders/vertex.glsl` — 頂点シェーダー
- `shaders/fragment.glsl` — フラグメントシェーダー
- `models/cube.obj` — Wavefront OBJ サンプルモデル
