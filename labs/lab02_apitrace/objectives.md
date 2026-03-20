# Lab 2 学習目標

## 知識目標

1. **APIトレースの概念**
   - LD_PRELOAD / DLL インジェクション による透過的なフッキング
   - トレースファイルのフォーマット（バイナリエンコード）

2. **OpenGL状態機械の理解**
   - バインドポイント（GL_ARRAY_BUFFER, GL_ELEMENT_ARRAY_BUFFER）
   - VAO（Vertex Array Object）によるレイアウト保存

3. **解析スキル**
   - grep/jq でトレースから特定パターンを抽出
   - フレーム境界（glSwapBuffers）の特定

## 達成確認チェックリスト

- [ ] dx11_viewer.trace を生成できた
- [ ] glDrawElements の引数を確認できた（count=36, type=GL_UNSIGNED_INT）
- [ ] glBufferData でアップロードされたバイト数を確認できた
- [ ] フレーム数を数えられた

## 発展課題

- トレースを編集して頂点位置を改ざんし、リプレイで反映されることを確認
- 別のアプリ（例: glxgears）をトレースしてドローコール数を比較
