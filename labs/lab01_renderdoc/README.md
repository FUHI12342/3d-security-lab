# Lab 1: RenderDocでGPUパイプラインを理解する

## 概要

RenderDocを使ってOpenGL/Vulkanアプリのフレームをキャプチャし、
GPUパイプライン（頂点シェーダー → ラスタライズ → フラグメントシェーダー）の
各ステージを可視化します。

## 対象アプリ

`targets/dx11_viewer/main.py` — Python + moderngl で動作する簡易3Dビューア

## ステップ

### Step 1: RenderDocをインストールする

https://renderdoc.org/builds からダウンロードしてインストール。

### Step 2: アプリを起動してキャプチャする

1. RenderDoc を起動
2. File > Launch Application
3. `python main.py` を指定して起動
4. F12 キーでフレームキャプチャ

### Step 3: パイプラインを探索する

キャプチャを開いたら：
- **Mesh Viewer**: 頂点バッファの内容を確認
- **Texture Viewer**: レンダリングされたテクスチャを確認
- **Pipeline State**: 各シェーダーステージの状態確認
- **Shader Viewer**: GLSL/HLSLソースを表示

### Step 4: 頂点データを抽出する

Mesh Viewerから：
1. VS In タブで入力頂点を表示
2. VS Out タブでシェーダー処理後の頂点を表示
3. Export Mesh でCSV/OBJ形式にエクスポート

## 期待される理解

- GPUパイプラインの各ステージの役割
- 頂点バッファのレイアウト（stride, offset）
- シェーダーコードとGPU実行の対応関係
