# Lab 7: 抽出した3Dデータを3Dプリントする

## 概要

デジタルフォレンジクスで復元した3Dモデルデータを、実際に3Dプリント可能な
STL形式に変換する手順を学びます。

## 学習目標

- 3Dモデルデータの座標系と単位を理解する
- STL形式（ASCII/Binary）の構造を理解する
- 3Dプリント適性（マニフォールド、法線一貫性）を学ぶ
- デジタルフォレンジクスで復元したデータの物理化を体験する

## 前提条件

- Lab 4（S3Dフォーマット解析）を完了していること
- Python 3.10 以上

## 演習

### Step 1: Lab 4 で解析した S3D モデルをデコードする

```python
import sys
sys.path.insert(0, '/c/_dev/repos/3d-security-lab')

from targets.custom_format.encoder import decode
from pathlib import Path

# サンプルモデルを読み込む
data = Path('targets/custom_format/samples/model_easy.s3d').read_bytes()
model = decode(data)

print(f"頂点数: {model.vertex_count}")
print(f"バージョン: {model.version}")
print(f"最初の頂点: {model.vertices[0]}")
```

### Step 2: STLExporter で変換する

```python
from tools.stl_exporter import STLExporter

exporter = STLExporter()

# S3Dファイルから直接変換
mesh = exporter.from_s3d_file('targets/custom_format/samples/model_easy.s3d')

print(f"メッシュ名: {mesh.name}")
print(f"三角形数: {mesh.triangle_count}")
print(f"バウンディングボックス: {mesh.bounding_box}")
```

### Step 3: validate_for_printing() で適性チェックする

```python
warnings = exporter.validate_for_printing(mesh)

if warnings:
    print("警告:")
    for w in warnings:
        print(f"  {w}")
else:
    print("問題なし。3Dプリント可能です。")
```

### Step 4: scale_to_mm() で印刷サイズに調整する

```python
# 最大辺を 50mm に正規化
scaled_mesh = STLExporter.scale_to_mm(mesh, target_size_mm=50.0)

# 原点に中心移動
centered_mesh = STLExporter.center_origin(scaled_mesh)

bb_min, bb_max = centered_mesh.bounding_box
dims = (
    bb_max[0] - bb_min[0],
    bb_max[1] - bb_min[1],
    bb_max[2] - bb_min[2],
)
print(f"調整後サイズ: {dims[0]:.1f} x {dims[1]:.1f} x {dims[2]:.1f} mm")
```

### Step 5: STL ファイルに出力する

```python
from pathlib import Path

output_dir = Path('/tmp/lab07_output')
output_dir.mkdir(exist_ok=True)

# Binary STL（推奨）
bin_path = exporter.export_binary(centered_mesh, output_dir / 'model.stl')
print(f"Binary STL: {bin_path} ({bin_path.stat().st_size} bytes)")

# ASCII STL（確認用）
ascii_path = exporter.export_ascii(centered_mesh, output_dir / 'model_ascii.stl')
print(f"ASCII STL: {ascii_path}")

# ASCII の内容を確認
content = ascii_path.read_text()
print("\\n最初の20行:")
for line in content.splitlines()[:20]:
    print(f"  {line}")
```

### Step 6: CLIツールで変換する

コマンドラインから直接変換することも可能です：

```bash
# S3D → STL（スケール50mm、バリデーション付き）
python -m tools.stl_converter \
    targets/custom_format/samples/model_easy.s3d \
    /tmp/model_easy.stl \
    --scale 50 \
    --center \
    --validate

# OBJ → STL
python -m tools.stl_converter \
    targets/dx11_viewer/models/cube.obj \
    /tmp/cube.stl \
    --scale 30

# ファイル情報のみ表示（変換しない）
python -m tools.stl_converter \
    targets/custom_format/samples/model_hard.s3d \
    --info
```

### Step 7: （オプション）STLビューアで確認する

変換した STL ファイルを以下のツールで確認：

- **ブラウザ**: [viewstl.com](https://www.viewstl.com/) にファイルをドロップ
- **Windows**: 3D Builder（標準搭載）
- **オープンソース**: [MeshLab](https://www.meshlab.net/)

## 発展演習

### OBJ ファイルからの変換

```python
# OBJファイルがある場合
mesh_from_obj = exporter.from_obj_file('targets/dx11_viewer/models/cube.obj')
```

### glTF ファイルからの変換

```python
# ObjExporter で生成した glTF を STL に変換
from tools.obj_exporter import ObjExporter
from tools.vertex_decoder import DecodedVertex

vertices = [
    DecodedVertex(position=(0.0, 0.0, 0.0)),
    DecodedVertex(position=(1.0, 0.0, 0.0)),
    DecodedVertex(position=(0.5, 1.0, 0.0)),
]

obj_exp = ObjExporter()
obj_exp.export_gltf(vertices, '/tmp/test.gltf')

# glTF → STL
mesh_from_gltf = exporter.from_gltf_file('/tmp/test.gltf')
print(f"glTF 三角形数: {mesh_from_gltf.triangle_count}")
```

### 頂点データから直接変換

```python
from tools.vertex_decoder import VertexDecoder, VertexFormat
import struct

# 頂点データを直接デコードして STL 化
raw_data = struct.pack('<9f',
    0.0, 0.0, 0.0,
    1.0, 0.0, 0.0,
    0.5, 1.0, 0.0,
)
decoder = VertexDecoder()
result = decoder.decode(raw_data, fmt=VertexFormat.POSITION_F32x3)

mesh = exporter.from_vertices(list(result.vertices))
print(f"デコード結果: {mesh.triangle_count} 三角形")
```

## STL フォーマットの理解

### ASCII STL 構造

```
solid mesh_name
  facet normal 0.000000e+00 0.000000e+00 1.000000e+00
    outer loop
      vertex 0.000000e+00 0.000000e+00 0.000000e+00
      vertex 1.000000e+00 0.000000e+00 0.000000e+00
      vertex 5.000000e-01 1.000000e+00 0.000000e+00
    endloop
  endfacet
endsolid mesh_name
```

### Binary STL 構造

| フィールド | サイズ | 説明 |
|-----------|--------|------|
| Header | 80 bytes | 任意テキスト |
| Triangle count | 4 bytes (uint32) | 三角形数 |
| Normal | 12 bytes (3×float32) | 法線ベクトル |
| Vertex 1, 2, 3 | 12 bytes each | 各頂点座標 |
| Attribute | 2 bytes (uint16) | 通常0 |

1三角形あたり 50 bytes = 12 + 12×3 + 2

## 3Dプリント適性チェック項目

| チェック | 説明 |
|---------|------|
| 三角形数 | 0個はNG |
| デジェネレート三角形 | 面積≒0の三角形はスライサーで問題 |
| 法線の一貫性 | 表裏が混在すると中空構造が不正 |
| バウンディングボックス | 極端に小さい/大きいと印刷不可 |
| 非マニフォールドエッジ | エッジが2三角形で共有されない場合 |
| NaN/Inf座標 | 数値不正 |
