# Lab 6 学習目標

## 知識目標

1. **Vulkan アーキテクチャ**
   - Instance / Device の分離
   - Dispatch テーブルの仕組み
   - Layer の有効化方法（環境変数、vk_layer_settings.txt）

2. **レイヤー実装スキル**
   - vkGetInstanceProcAddr のオーバーライド
   - 次のレイヤーへの dispatch
   - スレッドセーフな実装パターン

3. **解析応用**
   - vkCmdDrawIndexed 引数のログ
   - バッファ内容の読み取り（Staging Buffer コピー）
   - レンダーパス構造の解析

## 達成確認チェックリスト

- [ ] Vulkan SDK をインストールした
- [ ] 最小レイヤーをビルドできた
- [ ] vkCmdDraw をインターセプトしてログを出力できた
- [ ] DX11フッキング（Lab 5）との設計の違いを説明できた

## 発展課題

- Vulkan Memory Allocator と連携してVRAMアドレスを追跡
- RenderDoc の内部実装（Vulkan Layer として実装されている）を読む
- VK_LAYER_KHRONOS_validation の動作を逆張りする
