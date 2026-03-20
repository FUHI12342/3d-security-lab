# カリキュラム概要

## 3D Security Lab ハンズオン教材

本教材では、3DグラフィックスAPIの解析手法を6つのラボを通じて体系的に学びます。

## 学習の流れ

```
Lab 1 (RenderDoc)    → GPUパイプライン基礎の理解
Lab 2 (apitrace)     → APIコールレベルの解析
Lab 3 (Spector.js)   → WebGL特有の解析手法
Lab 4 (フォーマット)  → バイナリ解析・パーサー実装
Lab 5 (APIフッキング) → 動的インターセプト技術
Lab 6 (Vulkanレイヤ) → 低レベルAPI操作
```

## 前提知識

- プログラミング基礎（Python推奨）
- 3Dグラフィックスの基本概念（頂点、ポリゴン、シェーダー）
- バイナリデータの読み方

## 環境要件

| ツール | バージョン | 必須/推奨 |
|--------|-----------|-----------|
| Python | 3.10+ | 必須 |
| RenderDoc | 1.x | Lab 1 必須 |
| apitrace | 9.x+ | Lab 2 必須 |
| Chrome/Edge | 最新 | Lab 3 必須 |
| Visual Studio | 2022 | Lab 5 必須（Windows） |
| Vulkan SDK | 1.3+ | Lab 6 必須 |

## CTFへの接続

各Labを完了するとCTF演習（`ctf/`）に挑戦できます。
