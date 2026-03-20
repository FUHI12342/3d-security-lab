# Lab 2 解答・解説

## 主要なAPIコール一覧（期待値）

```
glGenVertexArrays(1, &vao)
glBindVertexArray(vao)
glGenBuffers(1, &vbo)
glBindBuffer(GL_ARRAY_BUFFER, vbo)
glBufferData(GL_ARRAY_BUFFER, 768, data, GL_STATIC_DRAW)  # 24頂点 × 32バイト
glGenBuffers(1, &ibo)
glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ibo)
glBufferData(GL_ELEMENT_ARRAY_BUFFER, 144, data, GL_STATIC_DRAW)  # 36インデックス × 4バイト
...（毎フレーム）
glDrawElements(GL_TRIANGLES, 36, GL_UNSIGNED_INT, 0)
```

## バッファサイズの計算

- 頂点バッファ: 24頂点 × 32バイト/頂点 = **768バイト**
- インデックスバッファ: 36 × sizeof(uint32) = **144バイト**

## トレース編集による改ざん

```bash
# トレースをJSONに変換（独自ツール）
apitrace dump --json dx11_viewer.trace > trace.json

# 頂点データを編集してバイナリに戻す（高度な発展課題）
```

## LD_PRELOAD の仕組み（Linux）

```c
// libGL.so の glDrawElements をフック
void glDrawElements(GLenum mode, GLsizei count, ...) {
    log_call("glDrawElements", count);  // ログ記録
    real_glDrawElements(mode, count, ...);  // 元の関数を呼ぶ
}
```

→ これが apitrace の基本原理。Lab 5 でより深く学びます。
