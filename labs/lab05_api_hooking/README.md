# Lab 5: Microsoft DetoursでAPIフッキング

## 概要

Microsoft Detours ライブラリを使って、DX11/OpenGL APIコールをインターセプトします。
C++でDLLを作成し、ターゲットプロセスにインジェクションします。

## 前提環境（Windows）

- Visual Studio 2022
- Microsoft Detours NuGet パッケージ
- Windows SDK

## ステップ

### Step 1: Detours のインストール

```
Visual Studio → プロジェクト → NuGetパッケージ管理
→ "Microsoft.Detours" を検索してインストール
```

または vcpkg:
```bash
vcpkg install detours:x64-windows
```

### Step 2: フック DLL の基本構造

```cpp
#include <windows.h>
#include <detours.h>
#include <d3d11.h>

// 元の関数ポインタ
static HRESULT (WINAPI *Real_DrawIndexed)(
    ID3D11DeviceContext* ctx,
    UINT IndexCount, UINT StartIndex, INT BaseVertex) = nullptr;

// フック関数
HRESULT WINAPI Hook_DrawIndexed(
    ID3D11DeviceContext* ctx,
    UINT IndexCount, UINT StartIndex, INT BaseVertex)
{
    // ログ記録
    OutputDebugStringA("[Hook] DrawIndexed called\n");
    // 元の関数を呼ぶ
    return Real_DrawIndexed(ctx, IndexCount, StartIndex, BaseVertex);
}

// DLLエントリポイント
BOOL WINAPI DllMain(HINSTANCE, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) {
        DetourTransactionBegin();
        DetourUpdateThread(GetCurrentThread());
        DetourAttach(&(PVOID&)Real_DrawIndexed, Hook_DrawIndexed);
        DetourTransactionCommit();
    }
    return TRUE;
}
```

### Step 3: インジェクション

```cpp
// インジェクタプロセスから
HANDLE hProc = OpenProcess(PROCESS_ALL_ACCESS, FALSE, targetPID);
LPVOID remoteAddr = VirtualAllocEx(hProc, NULL, dllPathLen, ...);
WriteProcessMemory(hProc, remoteAddr, dllPath, dllPathLen, NULL);
CreateRemoteThread(hProc, NULL, 0,
    (LPTHREAD_START_ROUTINE)LoadLibraryA, remoteAddr, 0, NULL);
```

### Step 4: 頂点バッファの読み取り

フック内で `Map/Unmap` を使ってバッファ内容を読み取ります：

```cpp
D3D11_MAPPED_SUBRESOURCE mapped;
ctx->Map(vertexBuffer, 0, D3D11_MAP_READ, 0, &mapped);
// mapped.pData にデータポインタ
// mapped.RowPitch / DepthPitch
ctx->Unmap(vertexBuffer, 0);
```

## 期待される理解

- DLLインジェクションの仕組み
- vtable フッキング vs IAT フッキングの違い
- COM インターフェースのvtable構造（DirectX）
