# セットアップ・利用ガイド

## 動作環境

| 項目 | 要件 |
|------|------|
| OS | Windows 10/11, macOS 12+, Ubuntu 22.04+ |
| Python | 3.10 以上 |
| GPU | DirectX 11 / OpenGL 4.1 / Vulkan 1.0 対応（LabによってはCPUのみ可） |

## インストール手順

### 1. リポジトリの取得

```bash
git clone https://github.com/your-org/3d-security-lab.git
cd 3d-security-lab
```

### 2. Python 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 3. 環境確認

```bash
python scripts/setup_environment.py
```

### 4. サンプルファイルの生成

```bash
python scripts/generate_samples.py
```

### 5. テストの実行

```bash
pytest tests/ -v
pytest tests/ -v --cov=tools --cov=targets --cov-report=html
```

---

## Lab 1 の実行方法

```bash
# RenderDoc をインストール後
pip install moderngl pygame
python targets/dx11_viewer/main.py
# → RenderDoc で F12 キーでキャプチャ
```

## Lab 3 の実行方法

```bash
# Chrome + Spector.js をインストール後
cd targets/webgl_scene
python -m http.server 8080
# → http://localhost:8080/ をChromeで開く
```

## CTF の実行方法

```bash
# サンプル生成が必要
python scripts/generate_samples.py

# 各チャレンジに挑戦
# フラグを見つけたら verify.py に入力
python ctf/challenge01_find_hidden_mesh/verify.py
python ctf/challenge02_decode_custom_format/verify.py
python ctf/challenge03_vram_recovery/verify.py
python ctf/challenge04_shader_secrets/verify.py
```

---

## ツールの使い方

### format_analyzer.py

```python
from tools.format_analyzer import FormatAnalyzer

fa = FormatAnalyzer()
result = fa.analyze("targets/custom_format/samples/model_medium.s3d")
print(result.summary())
print(fa.hexdump(open("model.s3d", "rb").read(), length=64))
```

### vertex_decoder.py

```python
from tools.vertex_decoder import VertexDecoder, VertexFormat

vd = VertexDecoder()
with open("vertex_buffer.bin", "rb") as f:
    data = f.read()
result = vd.decode(data, fmt=VertexFormat.POSITION_NORMAL_UV_F32x8)
print(result.summary())
for vtx in result.vertices[:5]:
    print(vtx.position)
```

### vram_forensics.py

```python
from tools.vram_forensics import VramForensics

vf = VramForensics()
candidates = vf.scan_framebuffers("vram_dump.bin", width=256, height=256)
for c in candidates[:3]:
    print(c.summary())
if candidates:
    vf.reconstruct_framebuffer("vram_dump.bin", candidates[0].offset, 256, 256, "output.png")
```

### obj_exporter.py

```python
from tools.obj_exporter import ObjExporter
from tools.vertex_decoder import VertexDecoder

vd = VertexDecoder()
result = vd.decode(open("vbo.bin", "rb").read())

exporter = ObjExporter()
exporter.export_obj(list(result.vertices), "output.obj")
exporter.export_gltf(list(result.vertices), "output.gltf")
```

---

## トラブルシューティング

### ImportError: No module named 'PIL'

```bash
pip install Pillow
```

### ImportError: No module named 'matplotlib'

```bash
pip install matplotlib
```

### Playwright が動かない

```bash
pip install playwright
playwright install chromium
```

### S3Dファイルが見つからない

```bash
python scripts/generate_samples.py
```
