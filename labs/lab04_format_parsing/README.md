# Lab 4: Assimpと独自フォーマットパーサー

## 概要

Assimp（Open Asset Import Library）を使った標準フォーマットの読み込みと、
本キットの独自フォーマット S3D を解析・デコードします。

## ステップ

### Step 1: Assimp で OBJ を読み込む

```python
import pyassimp

scene = pyassimp.load("targets/dx11_viewer/models/cube.obj")
for mesh in scene.meshes:
    print(f"頂点数: {len(mesh.vertices)}")
    print(f"面数: {len(mesh.faces)}")
    print(f"頂点[0]: {mesh.vertices[0]}")
pyassimp.release(scene)
```

### Step 2: S3D フォーマット仕様を読む

`targets/custom_format/format_spec.md` を開いて仕様を確認します。

主要フィールド：
- Magic: `S3D\x00`（4バイト）
- Version: uint32 LE
- Vertex count: uint32 LE
- Flags: uint32 LE（XOR/圧縮/チェックサムのビットフラグ）

### Step 3: format_analyzer.py でバイナリを解析

```bash
cd /c/_dev/repos/3d-security-lab
python -c "
from tools.format_analyzer import FormatAnalyzer
fa = FormatAnalyzer()
result = fa.analyze('targets/custom_format/samples/model_easy.s3d')
print(result)
"
```

### Step 4: viewer.py でデコード

```bash
python targets/custom_format/viewer.py targets/custom_format/samples/model_easy.s3d
python targets/custom_format/viewer.py targets/custom_format/samples/model_medium.s3d
```

### Step 5: 自力でデコーダを実装する

`format_spec.md` を参考に、独自のデコーダを実装してみましょう：

```python
import struct

with open("model_medium.s3d", "rb") as f:
    data = f.read()

magic = data[0:4]
version, vertex_count, flags = struct.unpack_from("<III", data, 4)
print(f"頂点数: {vertex_count}, フラグ: {flags:#010x}")
```

## 期待される理解

- バイナリファイルのパース手法（struct モジュール）
- XOR難読化の解除方法
- zlib 圧縮の検出と展開
