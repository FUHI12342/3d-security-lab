# Lab 3 解答・解説

## 隠しメッシュの特定方法

three.js は `scale.set(0, 0, 0)` したオブジェクトも WebGL 上では描画コールを発行します（culling されない場合）。

Spector.js でのドローコール一覧：

```
drawArrays(TRIANGLES, 0, 36)   ← 通常キューブ（36頂点）
drawArrays(TRIANGLES, 0, 72)   ← 隠しメッシュ（72頂点）
```

## 隠しメッシュのマトリクス確認

Spector.js の Commands タブ → uniformMatrix4fv を確認：

```javascript
// 通常キューブのmodel matrix
[1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]  // scale=1

// 隠しメッシュのmodel matrix
[0,0,0,0, 0,0,0,0, 0,0,0,0, 0,0,0,1]  // scale=0 (縮退)
```

## DevTools でのバッファ確認

```javascript
// Chrome DevToolsコンソールで実行
const gl = document.querySelector('canvas').getContext('webgl2');
const buf = gl.createBuffer();
// ... getBufferSubData で内容を取得
```

## CTF Challenge 1 のヒント

Spector.js で頂点数 72 のドローコールを見つけたら、
`FLAG{vertex_count_072}` を verify.py に入力してみましょう。
