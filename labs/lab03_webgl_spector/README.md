# Lab 3: Spector.jsでWebGLシーンを解析する

## 概要

Chrome拡張機能 Spector.js を使って、WebGLアプリのフレームキャプチャと
バッファ内容の解析を行います。

## 対象アプリ

`targets/webgl_scene/index.html` — three.js で構築されたWebGLシーン

## ステップ

### Step 1: Spector.js インストール

Chrome Web Store から「Spector.js」をインストール：
https://chrome.google.com/webstore/detail/spectorjs/denbgaamihkadbghdceggmchnflmhpmk

### Step 2: WebGLシーンを開く

```bash
# ローカルサーバーを起動
cd targets/webgl_scene
python -m http.server 8080
# → http://localhost:8080/ をChromeで開く
```

### Step 3: フレームキャプチャ

1. Spector.js アイコンをクリック
2. 「Start Capture」を押す
3. シーンが1フレーム描画されたら「Stop Capture」
4. キャプチャリストから確認

### Step 4: バッファを探索する

- **Commands タブ**: 全WebGLコマンド一覧
- **Buffers タブ**: VBO の生データを確認
  - drawArrays/drawElements の引数を確認
- **Textures タブ**: バインドされたテクスチャを確認

### Step 5: 隠しメッシュを発見する

注目すべき点：
- drawArrays が何回呼ばれているか？
- 各コールの `count` パラメータは？
- transformMatrix が scale(0,0,0) になっているドローコールは？

## 期待される理解

- WebGLコンテキストの状態管理
- three.js が内部でどのようなWebGLコールを生成するか
- scale=0 で非表示でもVRAM上に頂点データが存在すること
