# Lab 5 学習目標

## 知識目標

1. **APIフッキングの手法**
   - IAT（Import Address Table）フッキング
   - vtable フッキング（COM/DirectX向け）
   - inline フッキング（Detours方式）

2. **DirectX COM インターフェース**
   - ID3D11DeviceContext の vtable レイアウト
   - QueryInterface による実装取得

3. **プロセス間通信**
   - CreateRemoteThread によるDLLインジェクション
   - 名前付きパイプ / 共有メモリでのデータ転送

## 達成確認チェックリスト

- [ ] Detours DLL をビルドできた
- [ ] dx11_viewer プロセスにインジェクションできた
- [ ] DrawIndexed の呼び出しをOutputDebugStringでログできた
- [ ] 頂点バッファの内容を読み取れた

## 発展課題（上級）

- 読み取った頂点データをOBJファイルにリアルタイムダンプする
- フック DLL から UE4/Unity ゲームの頂点を取得する（自己所有のゲームで）
- Vulkan Layer との設計比較を行う（Lab 6 の準備）
