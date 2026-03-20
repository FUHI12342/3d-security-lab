# Lab 4 解答・解説

## model_easy.s3d のデコード手順

```python
import struct

with open("targets/custom_format/samples/model_easy.s3d", "rb") as f:
    raw = f.read()

# ヘッダーパース（16バイト）
magic = raw[0:4]        # b'S3D\x00'
version, n_verts, flags = struct.unpack_from("<III", raw, 4)

# フラグ確認
xor_enabled = bool(flags & 0x1)
zlib_enabled = bool(flags & 0x2)
checksum_enabled = bool(flags & 0x4)

print(f"頂点数: {n_verts}, XOR: {xor_enabled}, zlib: {zlib_enabled}")

# 頂点データ（flags=0x0 の場合は生データ）
vertex_data = raw[16:]
vertices = []
for i in range(n_verts):
    pos_x, pos_y, pos_z = struct.unpack_from("<fff", vertex_data, i * 32)
    vertices.append((pos_x, pos_y, pos_z))
```

## model_medium.s3d の XOR キー計算

```python
import hashlib, struct

magic = b'S3D\x00'
version = 1  # uint32 LE

# XOR キー = SHA256(magic + version_bytes) の先頭4バイト
version_bytes = struct.pack("<I", version)
xor_key_bytes = hashlib.sha256(magic + version_bytes).digest()[:4]
xor_key = struct.unpack("<I", xor_key_bytes)[0]
print(f"XOR key: {xor_key:#010x}")
```

## エントロピーの解釈

| エントロピー値 | 推定内容 |
|--------------|---------|
| 0.0 〜 1.0 | ほぼ定数データ |
| 1.0 〜 5.0 | 構造化データ（頂点座標など） |
| 5.0 〜 7.0 | XOR難読化 |
| 7.5 〜 8.0 | 圧縮または暗号化 |

## チェックサム検証

```python
import hashlib

# 末尾32バイトがSHA256
body = raw[:-32]
expected_hash = raw[-32:]
actual_hash = hashlib.sha256(body).digest()
assert actual_hash == expected_hash, "チェックサム不一致"
```
