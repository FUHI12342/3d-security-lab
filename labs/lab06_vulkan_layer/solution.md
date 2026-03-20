# Lab 6 解答・解説

## Dispatch テーブルの仕組み

Vulkan はローダー経由で呼び出しを dispatch します：

```
vkCmdDraw(commandBuffer, ...) {
    // commandBuffer に埋め込まれた dispatch テーブルを参照
    commandBuffer->dispatch_table->CmdDraw(commandBuffer, ...);
}
```

レイヤーは自分の dispatch テーブルを挿入することでインターセプトします。

## 完全なレイヤー実装の骨格

```cpp
#include <vulkan/vulkan.h>
#include <unordered_map>
#include <mutex>

// dispatch テーブルのキャッシュ
static std::mutex g_lock;
static std::unordered_map<void*, VkLayerDispatchTable> g_device_dispatch;

VkResult VKAPI_CALL layer_vkCreateDevice(
    VkPhysicalDevice physicalDevice,
    const VkDeviceCreateInfo* pCreateInfo,
    const VkAllocationCallbacks* pAllocator,
    VkDevice* pDevice)
{
    // チェーン内の次のレイヤー/ドライバを取得
    PFN_vkGetDeviceProcAddr gdpa = ...;
    VkResult result = fpCreateDevice(physicalDevice, pCreateInfo, ...);

    // dispatch テーブルを保存
    VkLayerDispatchTable dispatch;
    layer_init_device_dispatch_table(*pDevice, &dispatch, gdpa);
    {
        std::lock_guard<std::mutex> lock(g_lock);
        g_device_dispatch[GetDispatchKey(*pDevice)] = dispatch;
    }
    return result;
}

void VKAPI_CALL layer_vkCmdDrawIndexed(
    VkCommandBuffer commandBuffer,
    uint32_t indexCount, uint32_t instanceCount,
    uint32_t firstIndex, int32_t vertexOffset, uint32_t firstInstance)
{
    printf("[Layer] DrawIndexed: %u indices\n", indexCount);

    // 次のレイヤーに渡す
    auto& dispatch = g_device_dispatch[GetDispatchKey(commandBuffer)];
    dispatch.CmdDrawIndexed(commandBuffer, indexCount, instanceCount,
                             firstIndex, vertexOffset, firstInstance);
}
```

## Lab 5 vs Lab 6 の設計比較

| 観点 | Lab 5 (Detours/vtable) | Lab 6 (Vulkan Layer) |
|------|----------------------|---------------------|
| 公式サポート | なし（非公式） | あり（Khronos仕様） |
| 安定性 | ドライバ更新で壊れる可能性 | 仕様準拠で安定 |
| 適用範囲 | DX11/OpenGL | Vulkan専用 |
| セットアップ | DLLインジェクション必要 | 環境変数のみ |
| デバッグ | 困難 | SDK提供ツールで容易 |
