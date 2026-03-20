# Challenge 04: Shader Secrets

## 難易度: ★★★

## 問題

`scene.html` の WebGL シーンには、シェーダーに **秘密の文字列** が隠されています。
その文字列を見つけてください。

## フラグ形式

```
FLAG{shader_secret_XXXXXXXX}
```

## 手順

1. `http://localhost:8080/ctf/challenge04_shader_secrets/scene.html` を Chrome で開く
2. 以下のいずれかの方法で解析：
   - **Spector.js**: キャプチャ後、Shader タブでソースを確認
   - **Chrome DevTools**: Sources タブ → JavaScript を確認
   - **WebGL Inspector**: シェーダープログラムを確認
3. シェーダーの `uniform` 変数またはコメントを探す

## ヒント

- `gl.getUniformLocation()` で設定される uniform を探す
- JavaScript ソースに直接書かれている可能性も
- シェーダーコードのコメントに注目

## 採点

```bash
python ctf/challenge04_shader_secrets/verify.py "FLAG{shader_secret_Xk9mP2rQ}"
```
