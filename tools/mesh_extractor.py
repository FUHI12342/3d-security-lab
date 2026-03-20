"""
tools/mesh_extractor.py

RenderDoc Python API を使ったメッシュ自動抽出ツール。

機能:
- キャプチャファイル (.rdc) を開く
- ドローコール列挙
- 頂点バッファ・インデックスバッファ抽出
- テクスチャ抽出

注意: renderdoc モジュールが未インストールの場合はスタブ動作
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# renderdoc Python API を遅延インポート
try:
    import renderdoc as rd
    HAS_RENDERDOC = True
except ImportError:
    HAS_RENDERDOC = False


@dataclass(frozen=True)
class DrawCallInfo:
    """ドローコール情報を表す不変データクラス。"""
    event_id: int
    name: str
    vertex_count: int
    index_count: int
    instance_count: int

    def summary(self) -> str:
        """サマリーを返す。"""
        return (
            f"EID={self.event_id:4d}: {self.name} "
            f"(verts={self.vertex_count}, indices={self.index_count})"
        )


@dataclass(frozen=True)
class ExtractedMesh:
    """抽出されたメッシュデータを表す不変データクラス。"""
    event_id: int
    vertex_data: bytes
    index_data: Optional[bytes]
    vertex_count: int
    stride: int


@dataclass(frozen=True)
class ExtractionResult:
    """抽出結果全体を表す不変データクラス。"""
    rdc_path: str
    draw_calls: tuple[DrawCallInfo, ...]
    meshes: tuple[ExtractedMesh, ...]
    is_stub: bool  # renderdoc未インストール時はTrue


class MeshExtractor:
    """RenderDoc API を使ったメッシュ抽出クラス。"""

    def extract(self, rdc_path: str | Path) -> ExtractionResult:
        """
        RenderDocキャプチャからメッシュを抽出する。

        Args:
            rdc_path: .rdcキャプチャファイルのパス

        Returns:
            ExtractionResult インスタンス
        """
        path = Path(rdc_path)

        if not HAS_RENDERDOC:
            return self._stub_result(str(path))

        return self._do_extract(path)

    def _stub_result(self, rdc_path: str) -> ExtractionResult:
        """renderdoc未インストール時のスタブ結果を返す。"""
        print("[MeshExtractor] renderdoc モジュールが未インストールです")
        print("  RenderDoc をインストール後、Python API を有効化してください")
        print("  https://renderdoc.org/docs/python_api/index.html")

        # スタブのドローコール情報
        stub_draw_calls = (
            DrawCallInfo(
                event_id=1,
                name="[Stub] Draw(36)",
                vertex_count=0,
                index_count=36,
                instance_count=1,
            ),
        )
        return ExtractionResult(
            rdc_path=rdc_path,
            draw_calls=stub_draw_calls,
            meshes=(),
            is_stub=True,
        )

    def _do_extract(self, rdc_path: Path) -> ExtractionResult:
        """実際のRenderDoc API を使った抽出処理。"""
        # RenderDoc API の初期化
        rd.InitialiseReplay(rd.GlobalEnvironment(), [])

        # キャプチャファイルを開く
        cap = rd.OpenCaptureFile()
        result = cap.OpenFile(str(rdc_path), "", None)
        if result != rd.ResultCode.Succeeded:
            raise RuntimeError(f"キャプチャファイルを開けません: {rdc_path}")

        if not cap.LocalReplaySupport():
            raise RuntimeError("ローカルリプレイがサポートされていません")

        controller, _ = cap.OpenCapture(rd.ReplayOptions(), None)

        try:
            return self._extract_from_controller(str(rdc_path), controller)
        finally:
            controller.Shutdown()
            cap.Shutdown()

    def _extract_from_controller(
        self,
        rdc_path: str,
        controller: object,
    ) -> ExtractionResult:
        """コントローラーからドローコールとメッシュを抽出する。"""
        draw_calls: list[DrawCallInfo] = []
        meshes: list[ExtractedMesh] = []

        # ドローコール列挙
        for draw in controller.GetDrawcalls():  # type: ignore[attr-defined]
            info = DrawCallInfo(
                event_id=draw.eventId,
                name=draw.name,
                vertex_count=draw.numIndices if draw.flags & rd.DrawFlags.Indexed else draw.numIndices,
                index_count=draw.numIndices,
                instance_count=draw.numInstances,
            )
            draw_calls.append(info)

            # 頂点バッファを抽出
            controller.SetFrameEvent(draw.eventId, False)  # type: ignore[attr-defined]
            state = controller.GetPipelineState()  # type: ignore[attr-defined]

            vb_inputs = state.GetVBuffers()
            if vb_inputs:
                vb = vb_inputs[0]
                vb_data = controller.GetBufferData(  # type: ignore[attr-defined]
                    vb.resourceId, vb.byteOffset, 0
                )
                meshes.append(ExtractedMesh(
                    event_id=draw.eventId,
                    vertex_data=bytes(vb_data),
                    index_data=None,
                    vertex_count=draw.numIndices,
                    stride=vb.byteStride,
                ))

        return ExtractionResult(
            rdc_path=rdc_path,
            draw_calls=tuple(draw_calls),
            meshes=tuple(meshes),
            is_stub=False,
        )
