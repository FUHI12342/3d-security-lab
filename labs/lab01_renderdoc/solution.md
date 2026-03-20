# Lab 1 解答・解説

## 頂点バッファのレイアウト

`targets/dx11_viewer/main.py` のキューブは以下の頂点フォーマット：

```
stride = 32 bytes
  offset  0: position  (float32 x3 = 12 bytes)
  offset 12: normal    (float32 x3 = 12 bytes)
  offset 24: uv        (float32 x2 =  8 bytes)
```

## 頂点数の解説

キューブ6面 × 4頂点/面 = **24頂点**
インデックスバッファで6面 × 2三角形 × 3頂点 = **36インデックス**

## エクスポート手順

RenderDoc Mesh Viewer:
1. ドローコール選択 → VS In タブ
2. File > Export Mesh → CSV を選択
3. 出力されたCSVに `Position.x, Position.y, Position.z` カラムがあることを確認

## バイナリ解読の例

頂点バッファの先頭16進数：
```
00 00 80 BF  00 00 80 BF  00 00 00 00  ...
```

IEEE 754 float32:
- `00 00 80 BF` = -1.0f  (x)
- `00 00 80 BF` = -1.0f  (y)
- `00 00 00 00` =  0.0f  (z)

→ 頂点位置 (-1, -1, 0) を意味する

## シェーダーコード確認

Pipeline State > Fragment Shader でGLSLソースを確認：
```glsl
// fragment.glsl が表示される
out vec4 fragColor;
void main() {
    fragColor = vec4(1.0, 0.5, 0.0, 1.0);
}
```
