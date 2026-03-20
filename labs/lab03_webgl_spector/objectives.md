# Lab 3 学習目標

## 知識目標

1. **WebGLとOpenGLの違い**
   - セキュリティモデル（Same-Origin Policy）
   - JavaScript からのバッファアクセス制限

2. **Spector.js の動作原理**
   - WebGLContext のプロトタイプメソッドをラップ
   - コール前後のGPU状態スナップショット

3. **隠しオブジェクトの検出**
   - scale=0 で非表示でも WebGL には頂点データが存在する
   - visibility:hidden / opacity:0 との違い

## 達成確認チェックリスト

- [ ] Spector.js でフレームキャプチャできた
- [ ] drawArrays/drawElements のコール数を確認できた
- [ ] 隠しメッシュのドローコールを特定できた
- [ ] 隠しメッシュの頂点数を特定できた（CTF Challenge 1 への道）

## 発展課題

- Chrome DevTools の「Layers」タブでレンダリングレイヤーを確認
- WebGL Inspector（旧ツール）との機能比較
- `readPixels` を使ってフレームバッファをJSから取得するコードを書く
