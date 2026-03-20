# Challenge 01: Find the Hidden Mesh

## 難易度: ★☆☆

## 問題

`targets/webgl_scene/index.html` を開き、WebGLシーンを解析してください。
シーン内には視覚的に見えない隠しメッシュが存在します。
その隠しメッシュの **頂点数** を答えてください。

## フラグ形式

```
FLAG{vertex_count_NNN}
```

NNN = 頂点数（3桁、左ゼロパディング）

## 手順

1. `python -m http.server 8080` でWebシーンを起動
2. Chrome で `http://localhost:8080/targets/webgl_scene/` を開く
3. Spector.js で WebGL フレームをキャプチャ
4. ドローコールを一覧して、scale=0 のオブジェクトを特定
5. 頂点数を確認してフラグを submit

## ヒント

- Spector.js の「Commands」タブを確認
- `drawArrays` の `count` パラメータに注目
- 通常キューブの頂点数は 36（6面 × 6頂点）

## 採点

```bash
python ctf/challenge01_find_hidden_mesh/verify.py "FLAG{vertex_count_072}"
```
