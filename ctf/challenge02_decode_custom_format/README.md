# Challenge 02: Decode Custom Format

## 難易度: ★★☆

## 問題

`mystery.s3d` は独自バイナリフォーマットで保存された3Dモデルです。
このファイルをデコードし、**最初の頂点の X 座標** を答えてください。

## フラグ形式

```
FLAG{x_coordinate_X.XXX}
```

X.XXX = X座標を小数点3桁に丸めた値（例: -1.000）

## 手順

1. `tools/format_analyzer.py` でバイナリ構造を確認
2. `targets/custom_format/format_spec.md` でフォーマット仕様を確認
3. エントロピーを見てどの難読化が使われているか推定
4. デコーダーを実装して頂点座標を取得
5. X座標を `FLAG{x_coordinate_X.XXX}` 形式で submit

## ヒント

- エントロピー値が 5〜7 なら XOR 難読化の可能性が高い
- XOR キーは `SHA256(magic + version_bytes)[0:4]`
- `targets/custom_format/viewer.py` を参考にしてよい

## 採点

```bash
python ctf/challenge02_decode_custom_format/verify.py "FLAG{x_coordinate_-1.000}"
```
