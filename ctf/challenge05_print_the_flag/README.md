# Challenge 5: Print the Flag

## 難易度: ★★★

## 問題

`mystery_print.s3d` ファイルには **3Dテキストモデル** が隠されています。
このモデルをSTLに変換し、3Dビューアで確認して文字列を読み取ってください。

テキストは立体的に押し出されています。**上面（Z+ 方向）から見ると読めます。**

## フラグ形式

```
FLAG{XXXXXXXX}
```

## 手順

### Step 1: S3Dファイルをデコードして確認

```bash
# ファイル情報を表示
python -m tools.stl_converter ctf/challenge05_print_the_flag/mystery_print.s3d --info
```

### Step 2: STLに変換

```bash
# STLに変換（スケール100mm、中心移動）
python -m tools.stl_converter \
    ctf/challenge05_print_the_flag/mystery_print.s3d \
    ctf/challenge05_print_the_flag/output.stl \
    --scale 100 \
    --center \
    --validate
```

### Step 3: STLビューアで確認

変換した `output.stl` を以下のツールで開く：
- **Windows**: [3D Builder](https://apps.microsoft.com/store/detail/3d-builder/9WZDNCRFJ3T6) (無料)
- **ブラウザ**: [viewstl.com](https://www.viewstl.com/) にファイルをドロップ
- **Python**: `python targets/custom_format/viewer.py` + STL表示機能

### Step 4: 文字列を読む

**上面（Z軸の正方向）から見ると**、文字が読めます。

### Step 5: フラグを提出

```bash
python ctf/challenge05_print_the_flag/verify.py "FLAG{XXXXXXXX}"
```

## ヒント

- 文字は5x7ドットマトリクスフォントで描かれている
- 各ドットは立方体として押し出されている
- テキストは英大文字のみ（スペースなし）
- `STLExporter.from_s3d_file()` を使うと手動デコードできる

## 採点

```bash
cd /c/_dev/repos/3d-security-lab
python ctf/challenge05_print_the_flag/verify.py "FLAG{...}"
```
