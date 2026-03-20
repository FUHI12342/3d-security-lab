# 3D Security Lab — ツール仕様書

## tools/format_analyzer.py

### FormatAnalyzer クラス

| メソッド | 入力 | 出力 | 説明 |
|---------|------|------|------|
| `analyze(file_path)` | `str\|Path` | `AnalysisResult` | ファイルを解析 |
| `analyze_bytes(data, name)` | `bytes, str` | `AnalysisResult` | バイト列を解析 |
| `hexdump(data, offset, length, width)` | `bytes, int, int, int` | `str` | hexdump文字列生成 |

### compute_entropy(data) → float

Shannon エントロピーを計算する（bits/byte, 0.0〜8.0）。

### AnalysisResult（frozen dataclass）

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `file_path` | `str` | ファイルパス |
| `file_size` | `int` | バイトサイズ |
| `detected_format` | `str\|None` | 検出フォーマット |
| `magic_bytes` | `bytes` | 先頭8バイト |
| `entropy` | `float` | エントロピー値 |
| `entropy_classification` | `str` | エントロピー分類 |
| `repeated_patterns` | `list` | 繰り返しパターン |
| `alignment_guess` | `int` | アライメント推定 |
| `header_fields` | `dict` | ヘッダーフィールド |

---

## tools/vertex_decoder.py

### VertexDecoder クラス

| メソッド | 入力 | 出力 | 説明 |
|---------|------|------|------|
| `decode(data, fmt, stride, offset, endian)` | 各種オプション | `DecodeResult` | 頂点バッファをデコード |
| `decode_with_custom_stride(data, stride, ...)` | `bytes, int` | `DecodeResult` | カスタムストライドでデコード |

### VertexFormat（Enum）

| 値 | ストライド | 説明 |
|----|----------|------|
| `POSITION_F32x3` | 12 bytes | 座標のみ |
| `POSITION_NORMAL_F32x6` | 24 bytes | 座標 + 法線 |
| `POSITION_NORMAL_UV_F32x8` | 32 bytes | 座標 + 法線 + UV |
| `POSITION_NORMAL_UV_COLOR_F32x12` | 48 bytes | 座標 + 法線 + UV + カラー |

---

## tools/vram_forensics.py

### VramForensics クラス

| メソッド | 入力 | 出力 | 説明 |
|---------|------|------|------|
| `scan_image_headers(data)` | `bytes\|Path` | `list[ImageHit]` | 既知画像ヘッダーをスキャン |
| `scan_framebuffers(data, width, height, step)` | 各種 | `list[FramebufferCandidate]` | フレームバッファを探索 |
| `reconstruct_framebuffer(data, offset, width, height, output)` | 各種 | `Image\|None` | フレームバッファを画像として出力 |

---

## tools/obj_exporter.py

### ObjExporter クラス

| メソッド | 入力 | 出力 | 説明 |
|---------|------|------|------|
| `export_obj(vertices, path, name, source)` | 各種 | `ExportMetadata` | OBJ形式でエクスポート |
| `export_gltf(vertices, path, source)` | 各種 | `ExportMetadata` | glTF 2.0形式でエクスポート |

---

## S3D フォーマット仕様

詳細は `targets/custom_format/format_spec.md` を参照。

| フィールド | サイズ | 説明 |
|-----------|--------|------|
| magic | 4 bytes | `S3D\x00` |
| version | 4 bytes uint32 LE | バージョン番号 |
| vertex_count | 4 bytes uint32 LE | 頂点数 |
| flags | 4 bytes uint32 LE | 機能フラグ |
| vertex_data | 32×N bytes | 頂点データ（N=vertex_count） |
| [checksum] | 32 bytes | SHA256（オプション） |
