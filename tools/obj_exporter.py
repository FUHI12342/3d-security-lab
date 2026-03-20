"""
tools/obj_exporter.py

頂点データを Wavefront OBJ および glTF 2.0 形式にエクスポートする。

対応フォーマット:
- Wavefront OBJ (.obj)
- glTF 2.0 JSON + binary buffer (.gltf + .bin)
"""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from tools.vertex_decoder import DecodedVertex


@dataclass(frozen=True)
class ExportMetadata:
    """エクスポートメタデータを表す不変データクラス。"""
    source: str
    vertex_count: int
    format: str  # "OBJ" or "glTF"
    output_path: str


def _build_obj_lines(
    vertices: list[DecodedVertex],
    object_name: str = "extracted_mesh",
) -> list[str]:
    """OBJフォーマットの行リストを構築する。"""
    lines: list[str] = [
        f"# Wavefront OBJ - 3D Security Lab Export",
        f"# 頂点数: {len(vertices)}",
        f"o {object_name}",
        "",
    ]

    # 頂点座標
    for vtx in vertices:
        x, y, z = vtx.position
        lines.append(f"v {x:.6f} {y:.6f} {z:.6f}")

    # 法線（あれば）
    has_normals = any(v.normal is not None for v in vertices)
    if has_normals:
        lines.append("")
        for vtx in vertices:
            if vtx.normal is not None:
                nx, ny, nz = vtx.normal
            else:
                nx, ny, nz = 0.0, 0.0, 1.0
            lines.append(f"vn {nx:.6f} {ny:.6f} {nz:.6f}")

    # UV座標（あれば）
    has_uvs = any(v.uv is not None for v in vertices)
    if has_uvs:
        lines.append("")
        for vtx in vertices:
            if vtx.uv is not None:
                u, v_coord = vtx.uv
            else:
                u, v_coord = 0.0, 0.0
            lines.append(f"vt {u:.6f} {v_coord:.6f}")

    # 面定義（3頂点ずつ三角形）
    lines.append("")
    n = len(vertices)
    for i in range(0, n - 2, 3):
        v0, v1, v2 = i + 1, i + 2, i + 3  # OBJは1-indexed
        if has_normals and has_uvs:
            lines.append(f"f {v0}/{v0}/{v0} {v1}/{v1}/{v1} {v2}/{v2}/{v2}")
        elif has_uvs:
            lines.append(f"f {v0}/{v0} {v1}/{v1} {v2}/{v2}")
        elif has_normals:
            lines.append(f"f {v0}//{v0} {v1}//{v1} {v2}//{v2}")
        else:
            lines.append(f"f {v0} {v1} {v2}")

    return lines


def _build_gltf(
    vertices: list[DecodedVertex],
    bin_filename: str,
) -> tuple[dict, bytes]:
    """
    glTF 2.0 JSON と binary buffer を構築する。

    Returns:
        (gltf_dict, binary_bytes) のタプル
    """
    # バイナリバッファ構築（position のみ）
    positions: list[float] = []
    for vtx in vertices:
        positions.extend(vtx.position)

    bin_data = struct.pack(f"<{len(positions)}f", *positions)
    byte_length = len(bin_data)

    # 頂点座標の最小・最大値（glTF Accessor に必要）
    xs = [vtx.position[0] for vtx in vertices]
    ys = [vtx.position[1] for vtx in vertices]
    zs = [vtx.position[2] for vtx in vertices]
    min_pos = [min(xs), min(ys), min(zs)]
    max_pos = [max(xs), max(ys), max(zs)]

    gltf: dict = {
        "asset": {
            "version": "2.0",
            "generator": "3D Security Lab obj_exporter.py",
        },
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0}],
        "meshes": [
            {
                "name": "extracted_mesh",
                "primitives": [
                    {
                        "attributes": {"POSITION": 0},
                        "mode": 4,  # TRIANGLES
                    }
                ],
            }
        ],
        "accessors": [
            {
                "bufferView": 0,
                "componentType": 5126,  # FLOAT
                "count": len(vertices),
                "type": "VEC3",
                "min": min_pos,
                "max": max_pos,
            }
        ],
        "bufferViews": [
            {
                "buffer": 0,
                "byteOffset": 0,
                "byteLength": byte_length,
                "target": 34962,  # ARRAY_BUFFER
            }
        ],
        "buffers": [
            {
                "uri": bin_filename,
                "byteLength": byte_length,
            }
        ],
    }

    # UV があれば追加
    has_uvs = any(v.uv is not None for v in vertices)
    if has_uvs:
        uv_data: list[float] = []
        for vtx in vertices:
            if vtx.uv is not None:
                uv_data.extend(vtx.uv)
            else:
                uv_data.extend([0.0, 0.0])

        uv_bytes = struct.pack(f"<{len(uv_data)}f", *uv_data)
        uv_offset = byte_length
        byte_length += len(uv_bytes)
        bin_data += uv_bytes

        gltf["accessors"].append({
            "bufferView": 1,
            "componentType": 5126,  # FLOAT
            "count": len(vertices),
            "type": "VEC2",
        })
        gltf["bufferViews"].append({
            "buffer": 0,
            "byteOffset": uv_offset,
            "byteLength": len(uv_bytes),
            "target": 34962,
        })
        gltf["meshes"][0]["primitives"][0]["attributes"]["TEXCOORD_0"] = 1
        gltf["buffers"][0]["byteLength"] = byte_length

    return gltf, bin_data


class ObjExporter:
    """頂点データのエクスポータークラス。"""

    def export_obj(
        self,
        vertices: list[DecodedVertex],
        output_path: str | Path,
        object_name: str = "extracted_mesh",
        source: str = "3D Security Lab",
    ) -> ExportMetadata:
        """
        頂点データを Wavefront OBJ 形式でエクスポートする。

        Args:
            vertices: エクスポートする頂点リスト
            output_path: 出力OBJファイルパス
            object_name: OBJオブジェクト名
            source: エクスポート元の説明

        Returns:
            ExportMetadata インスタンス
        """
        if not vertices:
            raise ValueError("エクスポートする頂点がありません")

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        lines = _build_obj_lines(vertices, object_name)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        return ExportMetadata(
            source=source,
            vertex_count=len(vertices),
            format="OBJ",
            output_path=str(path),
        )

    def export_gltf(
        self,
        vertices: list[DecodedVertex],
        output_path: str | Path,
        source: str = "3D Security Lab",
    ) -> ExportMetadata:
        """
        頂点データを glTF 2.0 形式でエクスポートする。

        Args:
            vertices: エクスポートする頂点リスト
            output_path: 出力.gltfファイルパス（.bin は同じディレクトリに生成）
            source: エクスポート元の説明

        Returns:
            ExportMetadata インスタンス
        """
        if not vertices:
            raise ValueError("エクスポートする頂点がありません")

        gltf_path = Path(output_path)
        gltf_path.parent.mkdir(parents=True, exist_ok=True)

        bin_filename = gltf_path.stem + ".bin"
        bin_path = gltf_path.parent / bin_filename

        gltf_dict, bin_data = _build_gltf(vertices, bin_filename)

        # JSON と binary を書き出す
        gltf_path.write_text(
            json.dumps(gltf_dict, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        bin_path.write_bytes(bin_data)

        return ExportMetadata(
            source=source,
            vertex_count=len(vertices),
            format="glTF",
            output_path=str(gltf_path),
        )
