# Lab 2: apitraceでAPIコールをトレースする

## 概要

apitraceを使ってOpenGLアプリのAPIコールをすべてキャプチャし、
リプレイ・解析を行います。

## ステップ

### Step 1: apitraceのインストール

```bash
# Linux
sudo apt install apitrace

# macOS
brew install apitrace

# Windows: https://github.com/apitrace/apitrace/releases
```

### Step 2: トレース取得

```bash
apitrace trace python targets/dx11_viewer/main.py
# → dx11_viewer.trace が生成される
```

### Step 3: トレースの確認

```bash
# コール一覧を表示
apitrace dump dx11_viewer.trace | head -50

# 特定コールをフィルタ
apitrace dump dx11_viewer.trace | grep glDrawElements
```

### Step 4: リプレイ

```bash
# リプレイ（再現実行）
apitrace replay dx11_viewer.trace

# 特定フレームまで実行して停止
apitrace replay --snapshot=frame_0001.png dx11_viewer.trace
```

### Step 5: qapitrace GUIで解析

```bash
qapitrace dx11_viewer.trace
```

GUIでは各コールの引数・戻り値・GPU状態を確認できます。

## 期待される理解

- OpenGLステートマシンの動作
- glBufferData でのVRAMへのデータ転送タイミング
- glDrawElements の引数（頂点数、インデックス型、オフセット）
