# CTF 演習問題

## ルール

1. 各チャレンジのフラグは `FLAG{...}` 形式
2. `verify.py` にフラグを渡して正誤確認
3. ヒントは `labs/` の対応するLabを参照
4. 答えを直接コードから読むのは NG（本番と同じ姿勢で）

## チャレンジ一覧

| Challenge | 難易度 | 対応Lab | テーマ |
|-----------|--------|---------|--------|
| 01 | ★☆☆ | Lab 3 | WebGLシーンから隠しメッシュを抽出 |
| 02 | ★★☆ | Lab 4 | 独自フォーマットの3Dモデルをデコード |
| 03 | ★★☆ | - | VRAMダンプからテクスチャを復元 |
| 04 | ★★★ | Lab 3 | シェーダーに隠された秘密を見つける |

## 採点方法

```bash
# verify.py に直接フラグを渡す
python ctf/challenge01_find_hidden_mesh/verify.py "FLAG{vertex_count_072}"

# または対話入力
python ctf/challenge01_find_hidden_mesh/verify.py
Flag: FLAG{vertex_count_072}
```

## 前準備

```bash
# サンプルファイルを生成してからチャレンジを始めること
python scripts/generate_samples.py
```
