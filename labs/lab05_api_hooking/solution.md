# Lab 5 解答・解説

## vtable フッキングの仕組み

DirectX の COM インターフェースはvtableポインタを持ちます：

```
ID3D11DeviceContext vtable layout (抜粋):
  [0]  QueryInterface
  [1]  AddRef
  [2]  Release
  ...
  [12] Draw
  [13] Map
  [14] Unmap
  ...
  [20] DrawIndexed
```

vtable の該当エントリを書き換えることでフックできます：

```cpp
// vtable フッキング例（Detours不要）
void** vtable = *(void***)deviceContext;
DWORD oldProtect;
VirtualProtect(&vtable[20], sizeof(void*), PAGE_READWRITE, &oldProtect);
Real_DrawIndexed = (DrawIndexed_t)vtable[20];
vtable[20] = (void*)Hook_DrawIndexed;
VirtualProtect(&vtable[20], sizeof(void*), oldProtect, &oldProtect);
```

## 頂点データのダンプ例

```cpp
struct Vertex {
    float pos[3];
    float normal[3];
    float uv[2];
};

HRESULT WINAPI Hook_DrawIndexed(ID3D11DeviceContext* ctx,
    UINT IndexCount, UINT StartIndex, INT BaseVertex)
{
    // 現在バインドされているVBOを取得
    ID3D11Buffer* vb = nullptr;
    UINT stride, offset;
    ctx->IAGetVertexBuffers(0, 1, &vb, &stride, &offset);

    if (vb && stride == sizeof(Vertex)) {
        D3D11_BUFFER_DESC desc;
        vb->GetDesc(&desc);

        // ステージングバッファにコピー
        // ... (Map/UnmapはD3D11_MAP_READの場合StagingバッファのみOK)
    }
    return Real_DrawIndexed(ctx, IndexCount, StartIndex, BaseVertex);
}
```

## Detours vs vtable フッキング

| 方法 | メリット | デメリット |
|------|---------|----------|
| Detours (inline) | 任意の関数に適用可 | ASM書き換えが必要 |
| vtable | シンプル、COM向き | インターフェースごとに異なる |
| IAT | 静的リンク向き | 動的ロードには効かない |
