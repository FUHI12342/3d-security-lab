# Lab 6: Vulkan Layerの仕組みと自作

## 概要

Vulkan の Validation Layer / Explicit Layer の仕組みを理解し、
簡単な解析レイヤーを自作します。

## 前提環境

- Vulkan SDK (https://vulkan.lunarg.com/)
- CMake 3.20+
- C++17 対応コンパイラ

## ステップ

### Step 1: Vulkan Layer の仕組み

Vulkan は公式に「Layer」という仕組みを提供します：

```
アプリ
  ↓ vkCreateInstance
[Layer A] ← 解析/ログ/検証
  ↓
[Layer B]
  ↓
Vulkan Driver (GPU)
```

設定ファイル（JSON）を `VK_LAYER_PATH` に配置するだけでロードされます。

### Step 2: 最小レイヤーの実装

```cpp
// layer_intercept.cpp
#include <vulkan/vulkan.h>
#include <vulkan/vk_layer.h>

// vkCmdDraw をインターセプト
VKAPI_ATTR void VKAPI_CALL intercept_vkCmdDraw(
    VkCommandBuffer commandBuffer,
    uint32_t vertexCount, uint32_t instanceCount,
    uint32_t firstVertex, uint32_t firstInstance)
{
    printf("[Layer] vkCmdDraw: %u vertices\n", vertexCount);
    // 次のレイヤー/ドライバに渡す
    pfn_vkCmdDraw(commandBuffer, vertexCount, instanceCount,
                  firstVertex, firstInstance);
}
```

### Step 3: レイヤーマニフェスト（JSON）

```json
{
    "file_format_version": "1.0.0",
    "layer": {
        "name": "VK_LAYER_SECURITY_LAB_intercept",
        "type": "GLOBAL",
        "library_path": "./libVkLayerIntercept.so",
        "api_version": "1.3.0",
        "implementation_version": "1",
        "description": "Security Lab Intercept Layer"
    }
}
```

### Step 4: 有効化

```bash
export VK_LAYER_PATH=/path/to/layer
export VK_INSTANCE_LAYERS=VK_LAYER_SECURITY_LAB_intercept
./your_vulkan_app
```

## 期待される理解

- Vulkan Layer の intercept chain
- GetInstanceProcAddr / GetDeviceProcAddr
- Dispatch table の操作
