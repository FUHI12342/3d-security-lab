# WebGL Scene Target

## 概要

three.js を使った WebGL シーン。CTF Challenge 1, 4 の解析対象です。

## 起動方法

```bash
cd targets/webgl_scene
python -m http.server 8080
# → http://localhost:8080/ をChromeで開く
```

## 含まれる要素

| 要素 | 説明 | CTF |
|------|------|-----|
| 通常キューブ | 回転する可視オブジェクト | - |
| 隠しメッシュ | scale=0で非表示のIcosphere | Challenge 1 |
| シェーダーuniform | u_secretに文字列を埋め込み | Challenge 4 |

## ヒント

- Spector.js でWebGLコマンドをキャプチャしてドローコールを確認
- Chrome DevTools > Sources でJSを確認
- `console.log` に情報が出力されているかも
