# 3D Security Lab

セキュリティ教育用3Dモデル解析キット

## 概要

本キットは、3DグラフィックスAPIやモデルフォーマットのセキュリティ解析手法を学ぶための教育用リポジトリです。
GPUパイプラインの仕組みを理解し、ツールを使ったデバッグ・解析スキルを習得します。

## 対象者

- セキュリティ研究者（グラフィックス系）
- ゲームセキュリティに興味のあるエンジニア
- CTF参加者
- 3DグラフィックスAPIを学ぶ開発者

## 構成

```
labs/         ハンズオン教材（Lab 1〜6）
targets/      解析対象サンプルアプリ
tools/        教育用ユーティリティ
ctf/          CTF形式の演習問題
scripts/      セットアップスクリプト
tests/        pytestテストスイート
docs/         仕様書・マニュアル
```

## クイックスタート

```bash
# 依存関係インストール
pip install -r requirements.txt

# 環境確認
python scripts/setup_environment.py

# サンプルファイル生成
python scripts/generate_samples.py

# テスト実行
pytest tests/ -v
```

## ラボ一覧

| Lab | テーマ | ツール |
|-----|--------|--------|
| Lab 1 | RenderDocでGPUパイプラインを理解する | RenderDoc |
| Lab 2 | apitraceでAPIコールをトレースする | apitrace |
| Lab 3 | Spector.jsでWebGLシーンを解析する | Spector.js |
| Lab 4 | Assimpと独自フォーマットパーサー | Assimp, 本キット tools/ |
| Lab 5 | Microsoft DetoursでAPIフッキング | Detours |
| Lab 6 | Vulkan Layerの仕組みと自作 | Vulkan SDK |

## CTF演習

| Challenge | 難易度 | テーマ |
|-----------|--------|--------|
| 01 | 初級 | WebGLシーンから隠しメッシュを抽出 |
| 02 | 中級 | 独自バイナリ形式のデコード |
| 03 | 中級 | VRAMダンプからテクスチャ復元 |
| 04 | 上級 | シェーダーに隠された秘密 |

## 法的注意

本キットは教育・研究目的専用です。詳細は [docs/LEGAL.md](docs/LEGAL.md) を参照してください。
第三者ソフトウェアへの無断適用は禁止です。

## ライセンス

MIT License - 詳細は [LICENSE](LICENSE) を参照
