"""
tools/stl_exporter.py

STLエクスポーター — 抽出した3Dデータを3Dプリント可能なSTL形式に変換

対応入力:
  - OBJ形式（obj_exporter.pyの出力）
  - 頂点データ（vertex_decoder.pyの出力）
  - S3Dカスタム形式（encoder.pyのデコード結果）
  - glTF/GLB形式

出力:
  - STL ASCII形式
  - STL Binary形式（推奨、ファイルサイズ小）
"""

from __future__ import annotations

import json
import math
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# --- データクラス ---

@dataclass(frozen=True)
class Triangle:
    """三角形面（STLの基本単位）。"""
    v1: tuple[float, float, float]
    v2: tuple[float, float, float]
    v3: tuple[float, float, float]
    normal: tuple[float, float, float]


@dataclass(frozen=True)
class STLMesh:
    """STLメッシュデータ。"""
    name: str
    triangles: tuple[Triangle, ...]

    @property
    def triangle_count(self) -> int:
        """三角形数を返す。"""
        return len(self.triangles)

    @property
    def bounding_box(
        self,
    ) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
        """
        バウンディングボックスを返す。

        Returns:
            (min_point, max_point) の2タプル
        """
        if not self.triangles:
            return ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))

        xs: list[float] = []
        ys: list[float] = []
        zs: list[float] = []
        for tri in self.triangles:
            for v in (tri.v1, tri.v2, tri.v3):
                xs.append(v[0])
                ys.append(v[1])
                zs.append(v[2])

        return (
            (min(xs), min(ys), min(zs)),
            (max(xs), max(ys), max(zs)),
        )


# --- ヘルパー関数 ---

def _cross(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
) -> tuple[float, float, float]:
    """3Dベクトルの外積を計算する。"""
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _sub(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
) -> tuple[float, float, float]:
    """3Dベクトルの差を返す。"""
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _normalize(v: tuple[float, float, float]) -> tuple[float, float, float]:
    """ベクトルを正規化する。ゼロベクトルはそのまま返す。"""
    length = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)
    if length < 1e-10:
        return v
    return (v[0] / length, v[1] / length, v[2] / length)


def _parse_obj_text(text: str) -> STLMesh:
    """OBJテキストをパースしてSTLMeshを返す内部ヘルパー。"""
    raw_verts: list[tuple[float, float, float]] = []
    raw_normals: list[tuple[float, float, float]] = []
    triangles: list[Triangle] = []

    for line in text.splitlines():
        parts = line.strip().split()
        if not parts:
            continue

        if parts[0] == "v" and len(parts) >= 4:
            raw_verts.append((float(parts[1]), float(parts[2]), float(parts[3])))

        elif parts[0] == "vn" and len(parts) >= 4:
            raw_normals.append(
                (float(parts[1]), float(parts[2]), float(parts[3]))
            )

        elif parts[0] == "f" and len(parts) >= 4:
            # 頂点インデックスをパース（"v", "v/t", "v/t/n", "v//n" 形式対応）
            def _parse_face_vertex(token: str) -> tuple[int, Optional[int]]:
                """face トークンから (頂点インデックス, 法線インデックス) を返す。"""
                subs = token.split("/")
                vi = int(subs[0]) - 1  # 0-indexed に変換
                ni: Optional[int] = None
                if len(subs) >= 3 and subs[2]:
                    ni = int(subs[2]) - 1
                return vi, ni

            face_tokens = parts[1:]
            parsed = [_parse_face_vertex(t) for t in face_tokens]

            # fan triangulation（4角面以上を三角形に分割）
            for i in range(1, len(parsed) - 1):
                vi0, ni0 = parsed[0]
                vi1, ni1 = parsed[i]
                vi2, ni2 = parsed[i + 1]

                # インデックスが範囲外なら skip
                if (
                    vi0 < 0 or vi0 >= len(raw_verts)
                    or vi1 < 0 or vi1 >= len(raw_verts)
                    or vi2 < 0 or vi2 >= len(raw_verts)
                ):
                    continue

                v1 = raw_verts[vi0]
                v2 = raw_verts[vi1]
                v3 = raw_verts[vi2]

                # 法線: OBJに vn があれば利用、なければ外積計算
                if (
                    ni0 is not None
                    and raw_normals
                    and 0 <= ni0 < len(raw_normals)
                ):
                    normal = _normalize(raw_normals[ni0])
                else:
                    normal = STLExporter.compute_normal(v1, v2, v3)

                triangles.append(Triangle(v1=v1, v2=v2, v3=v3, normal=normal))

    return STLMesh(name="obj_mesh", triangles=tuple(triangles))


def _read_gltf_accessor(
    accessors: list[dict],
    buffer_views: list[dict],
    buffers_data: list[bytes],
    accessor_index: int,
) -> list[tuple[float, ...]]:
    """glTFアクセッサーから浮動小数点データを読み取る。"""
    acc = accessors[accessor_index]
    bv = buffer_views[acc["bufferView"]]
    buffer_data = buffers_data[bv.get("buffer", 0)]

    byte_offset = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
    count = acc["count"]

    type_sizes = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}
    component_count = type_sizes.get(acc["type"], 1)
    component_type = acc["componentType"]

    if component_type == 5126:  # FLOAT
        fmt = f"<{component_count}f"
        item_size = component_count * 4
    elif component_type == 5123:  # UNSIGNED_SHORT
        fmt = f"<{component_count}H"
        item_size = component_count * 2
    elif component_type == 5125:  # UNSIGNED_INT
        fmt = f"<{component_count}I"
        item_size = component_count * 4
    elif component_type == 5121:  # UNSIGNED_BYTE
        fmt = f"<{component_count}B"
        item_size = component_count * 1
    else:
        raise ValueError(f"未対応のcomponentType: {component_type}")

    result: list[tuple[float, ...]] = []
    for i in range(count):
        offset = byte_offset + i * item_size
        values = struct.unpack_from(fmt, buffer_data, offset)
        result.append(values)

    return result


# --- メインクラス ---

class STLExporter:
    """STLエクスポーター。"""

    def from_vertices(
        self,
        vertices: list,
        indices: Optional[list[int]] = None,
    ) -> STLMesh:
        """
        頂点データ + インデックス → STLMesh

        インデックスなしの場合: 3頂点ずつ三角形として解釈
        インデックスありの場合: インデックスで三角形を構成
        法線: 外積で自動計算

        Args:
            vertices: 頂点リスト。各要素は (x,y,z) タプル、または
                      position 属性を持つ DecodedVertex / Vertex オブジェクト
            indices: 三角形インデックスリスト（3の倍数）

        Returns:
            STLMesh インスタンス
        """
        # 位置座標を正規化
        positions: list[tuple[float, float, float]] = []
        for v in vertices:
            if isinstance(v, (tuple, list)):
                positions.append((float(v[0]), float(v[1]), float(v[2])))
            else:
                # DecodedVertex / Vertex 等、position 属性を持つオブジェクト
                p = v.position
                positions.append((float(p[0]), float(p[1]), float(p[2])))

        triangles: list[Triangle] = []

        if indices is not None:
            # インデックスリストで三角形を構成
            for i in range(0, len(indices) - 2, 3):
                i0, i1, i2 = indices[i], indices[i + 1], indices[i + 2]
                if i0 < len(positions) and i1 < len(positions) and i2 < len(positions):
                    v1 = positions[i0]
                    v2 = positions[i1]
                    v3 = positions[i2]
                    normal = self.compute_normal(v1, v2, v3)
                    triangles.append(Triangle(v1=v1, v2=v2, v3=v3, normal=normal))
        else:
            # 3頂点ずつ三角形として解釈
            for i in range(0, len(positions) - 2, 3):
                v1 = positions[i]
                v2 = positions[i + 1]
                v3 = positions[i + 2]
                normal = self.compute_normal(v1, v2, v3)
                triangles.append(Triangle(v1=v1, v2=v2, v3=v3, normal=normal))

        return STLMesh(name="mesh", triangles=tuple(triangles))

    def from_obj_file(self, obj_path: str | Path) -> STLMesh:
        """
        OBJファイル → STLMesh

        - v（頂点）とf（面）を読み取り
        - 4角面以上は fan triangulation で分割
        - vn（法線）があれば利用、なければ外積計算

        Args:
            obj_path: OBJファイルパス

        Returns:
            STLMesh インスタンス

        Raises:
            FileNotFoundError: ファイルが存在しない場合
            ValueError: ファイルに有効な三角形がない場合
        """
        path = Path(obj_path)
        if not path.exists():
            raise FileNotFoundError(f"OBJファイルが見つかりません: {path}")

        text = path.read_text(encoding="utf-8", errors="replace")
        mesh = _parse_obj_text(text)

        # ファイル名をメッシュ名に設定
        return STLMesh(name=path.stem, triangles=mesh.triangles)

    def from_s3d_file(self, s3d_path: str | Path) -> STLMesh:
        """
        S3Dカスタム形式 → STLMesh

        encoder.py の decode() でデコードしてから変換。

        Args:
            s3d_path: S3Dファイルパス

        Returns:
            STLMesh インスタンス

        Raises:
            FileNotFoundError: ファイルが存在しない場合
        """
        path = Path(s3d_path)
        if not path.exists():
            raise FileNotFoundError(f"S3Dファイルが見つかりません: {path}")

        # encoder.py の decode() を使用（循環インポート回避のため遅延）
        import sys
        import os
        project_root = Path(__file__).parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))

        from targets.custom_format.encoder import decode  # noqa: PLC0415

        data = path.read_bytes()
        model = decode(data)

        # S3D Vertex → position タプルリスト
        positions: list[tuple[float, float, float]] = [
            v.position for v in model.vertices
        ]

        return self.from_vertices(positions)

    def from_gltf_file(self, gltf_path: str | Path) -> STLMesh:
        """
        glTF/GLB → STLMesh

        JSON構造からメッシュデータを抽出し、バイナリバッファから頂点を取得。

        Args:
            gltf_path: glTF(.gltf または .glb) ファイルパス

        Returns:
            STLMesh インスタンス

        Raises:
            FileNotFoundError: ファイルが存在しない場合
            ValueError: 対応外の形式の場合
        """
        path = Path(gltf_path)
        if not path.exists():
            raise FileNotFoundError(f"glTFファイルが見つかりません: {path}")

        suffix = path.suffix.lower()

        if suffix == ".glb":
            gltf_dict, buffers_data = _parse_glb(path)
        else:
            gltf_dict = json.loads(path.read_text(encoding="utf-8"))
            buffers_data = _load_gltf_buffers(gltf_dict, path.parent)

        return _gltf_to_stl_mesh(gltf_dict, buffers_data, path.stem)

    def export_ascii(self, mesh: STLMesh, output_path: str | Path) -> Path:
        """
        ASCII STL形式で出力。

        形式:
          solid name
            facet normal ni nj nk
              outer loop
                vertex v1x v1y v1z
                vertex v2x v2y v2z
                vertex v3x v3y v3z
              endloop
            endfacet
          endsolid name

        Args:
            mesh: 出力するSTLMesh
            output_path: 出力ファイルパス

        Returns:
            出力ファイルの Path オブジェクト
        """
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        lines: list[str] = [f"solid {mesh.name}"]
        for tri in mesh.triangles:
            n = tri.normal
            lines.append(
                f"  facet normal {n[0]:.6e} {n[1]:.6e} {n[2]:.6e}"
            )
            lines.append("    outer loop")
            for v in (tri.v1, tri.v2, tri.v3):
                lines.append(f"      vertex {v[0]:.6e} {v[1]:.6e} {v[2]:.6e}")
            lines.append("    endloop")
            lines.append("  endfacet")
        lines.append(f"endsolid {mesh.name}")

        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return out

    def export_binary(self, mesh: STLMesh, output_path: str | Path) -> Path:
        """
        Binary STL形式で出力（推奨）。

        バイナリ構造:
          Header: 80 bytes（任意テキスト）
          Triangle count: uint32
          Per triangle:
            Normal: float32 x3
            Vertex1: float32 x3
            Vertex2: float32 x3
            Vertex3: float32 x3
            Attribute byte count: uint16 (通常0)

        Args:
            mesh: 出力するSTLMesh
            output_path: 出力ファイルパス

        Returns:
            出力ファイルの Path オブジェクト
        """
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        # 80バイトヘッダー（ASCII）
        header_text = f"Binary STL - 3D Security Lab - {mesh.name}"
        header = header_text.encode("ascii", errors="replace")[:80].ljust(80, b"\x00")

        # 三角形数（uint32 LE）
        count_bytes = struct.pack("<I", mesh.triangle_count)

        # 各三角形: 12 floats (normal x3, v1 x3, v2 x3, v3 x3) + uint16
        triangles_bytes = bytearray()
        for tri in mesh.triangles:
            triangles_bytes += struct.pack(
                "<12fH",
                tri.normal[0], tri.normal[1], tri.normal[2],
                tri.v1[0], tri.v1[1], tri.v1[2],
                tri.v2[0], tri.v2[1], tri.v2[2],
                tri.v3[0], tri.v3[1], tri.v3[2],
                0,  # attribute byte count
            )

        out.write_bytes(header + count_bytes + bytes(triangles_bytes))
        return out

    def validate_for_printing(self, mesh: STLMesh) -> list[str]:
        """
        3Dプリント適性チェック。

        チェック項目:
        - 三角形数 > 0
        - デジェネレート三角形（面積0）の検出
        - 法線の一貫性（表裏）
        - バウンディングボックスサイズ
        - 非マニフォールドエッジの検出（簡易）
        - NaN/Inf座標の検出

        Args:
            mesh: チェック対象の STLMesh

        Returns:
            警告メッセージのリスト（空なら問題なし）
        """
        warnings: list[str] = []

        # 三角形数チェック
        if mesh.triangle_count == 0:
            warnings.append("ERROR: 三角形が0個です。メッシュが空です。")
            return warnings  # これ以上チェック不可

        degenerate_count = 0
        nan_inf_count = 0
        negative_normal_count = 0

        # エッジ → 三角形インデックスのマップ（非マニフォールド検出用）
        edge_map: dict[tuple, list[int]] = {}

        for idx, tri in enumerate(mesh.triangles):
            # NaN/Inf チェック
            all_coords = [
                tri.v1[0], tri.v1[1], tri.v1[2],
                tri.v2[0], tri.v2[1], tri.v2[2],
                tri.v3[0], tri.v3[1], tri.v3[2],
                tri.normal[0], tri.normal[1], tri.normal[2],
            ]
            if any(math.isnan(c) or math.isinf(c) for c in all_coords):
                nan_inf_count += 1
                continue

            # デジェネレート三角形チェック（面積 ≈ 0）
            edge1 = _sub(tri.v2, tri.v1)
            edge2 = _sub(tri.v3, tri.v1)
            cross = _cross(edge1, edge2)
            area_sq = cross[0] ** 2 + cross[1] ** 2 + cross[2] ** 2
            if area_sq < 1e-20:
                degenerate_count += 1

            # 法線と計算法線の一貫性チェック
            computed_n = self.compute_normal(tri.v1, tri.v2, tri.v3)
            dot = (
                tri.normal[0] * computed_n[0]
                + tri.normal[1] * computed_n[1]
                + tri.normal[2] * computed_n[2]
            )
            # 法線が逆向き（ドット積が負）
            if dot < -0.1:
                negative_normal_count += 1

            # エッジ追加（非マニフォールド簡易チェック用）
            verts = (tri.v1, tri.v2, tri.v3)
            for i in range(3):
                e_start = verts[i]
                e_end = verts[(i + 1) % 3]
                # 向きに依存しないキー（両方向を同一視）
                key = tuple(sorted([e_start, e_end]))
                edge_map.setdefault(key, []).append(idx)  # type: ignore[arg-type]

        if nan_inf_count > 0:
            warnings.append(
                f"ERROR: NaN または Inf を含む座標が {nan_inf_count} 個の三角形に存在します。"
            )

        if degenerate_count > 0:
            warnings.append(
                f"WARNING: デジェネレート三角形（面積≒0）が {degenerate_count} 個あります。"
            )

        if negative_normal_count > 0:
            warnings.append(
                f"WARNING: 法線が不一致な三角形が {negative_normal_count} 個あります。"
                " 表裏が逆の可能性があります。"
            )

        # 非マニフォールドエッジ検出（2つ以上の三角形で共有されない、または3つ以上）
        non_manifold = [k for k, v in edge_map.items() if len(v) != 2]
        if non_manifold:
            warnings.append(
                f"WARNING: 非マニフォールドエッジが {len(non_manifold)} 個あります。"
                " 印刷時に問題が発生する可能性があります。"
            )

        # バウンディングボックスサイズチェック
        bb_min, bb_max = mesh.bounding_box
        dims = [
            bb_max[0] - bb_min[0],
            bb_max[1] - bb_min[1],
            bb_max[2] - bb_min[2],
        ]
        max_dim = max(dims)
        if max_dim < 0.001:
            warnings.append(
                f"WARNING: メッシュが非常に小さいです（最大辺: {max_dim:.6f}）。"
                " スケールを確認してください。"
            )
        elif max_dim > 500.0:
            warnings.append(
                f"WARNING: メッシュが大きすぎる可能性があります（最大辺: {max_dim:.1f}mm）。"
                " 一般的な3Dプリンターの造形範囲を確認してください。"
            )

        return warnings

    @staticmethod
    def compute_normal(
        v1: tuple[float, float, float],
        v2: tuple[float, float, float],
        v3: tuple[float, float, float],
    ) -> tuple[float, float, float]:
        """外積で法線ベクトルを計算（正規化済み）。"""
        edge1 = _sub(v2, v1)
        edge2 = _sub(v3, v1)
        cross = _cross(edge1, edge2)
        return _normalize(cross)

    @staticmethod
    def scale_to_mm(mesh: STLMesh, target_size_mm: float = 100.0) -> STLMesh:
        """
        3Dプリント用にスケール調整。

        バウンディングボックスの最大辺を target_size_mm に正規化する。

        Args:
            mesh: スケール対象のメッシュ
            target_size_mm: 目標サイズ（mm）

        Returns:
            スケール後の新しい STLMesh
        """
        if not mesh.triangles:
            return mesh

        bb_min, bb_max = mesh.bounding_box
        dims = [
            bb_max[0] - bb_min[0],
            bb_max[1] - bb_min[1],
            bb_max[2] - bb_min[2],
        ]
        max_dim = max(dims)

        if max_dim < 1e-10:
            return mesh

        scale = target_size_mm / max_dim

        def _scale_v(v: tuple[float, float, float]) -> tuple[float, float, float]:
            return (v[0] * scale, v[1] * scale, v[2] * scale)

        new_triangles = tuple(
            Triangle(
                v1=_scale_v(tri.v1),
                v2=_scale_v(tri.v2),
                v3=_scale_v(tri.v3),
                normal=tri.normal,  # 法線はスケール不変
            )
            for tri in mesh.triangles
        )

        return STLMesh(name=mesh.name, triangles=new_triangles)

    @staticmethod
    def center_origin(mesh: STLMesh) -> STLMesh:
        """
        メッシュの重心を原点に移動。

        バウンディングボックスの中心を (0, 0, 0) に移動する。

        Args:
            mesh: 変換対象のメッシュ

        Returns:
            移動後の新しい STLMesh
        """
        if not mesh.triangles:
            return mesh

        bb_min, bb_max = mesh.bounding_box
        cx = (bb_min[0] + bb_max[0]) / 2.0
        cy = (bb_min[1] + bb_max[1]) / 2.0
        cz = (bb_min[2] + bb_max[2]) / 2.0

        def _shift_v(v: tuple[float, float, float]) -> tuple[float, float, float]:
            return (v[0] - cx, v[1] - cy, v[2] - cz)

        new_triangles = tuple(
            Triangle(
                v1=_shift_v(tri.v1),
                v2=_shift_v(tri.v2),
                v3=_shift_v(tri.v3),
                normal=tri.normal,
            )
            for tri in mesh.triangles
        )

        return STLMesh(name=mesh.name, triangles=new_triangles)


# --- glTF/GLB パーサーヘルパー ---

def _parse_glb(path: Path) -> tuple[dict, list[bytes]]:
    """GLBバイナリを読み込み (gltf_dict, [buffer_bytes]) を返す。"""
    data = path.read_bytes()

    # GLB ヘッダー: magic(4) + version(4) + length(4)
    if len(data) < 12:
        raise ValueError("GLBファイルが短すぎます")
    magic, version, total_length = struct.unpack_from("<III", data, 0)
    if magic != 0x46546C67:  # "glTF"
        raise ValueError(f"GLBマジックバイト不一致: {hex(magic)}")

    offset = 12
    json_data: bytes = b""
    bin_data: bytes = b""

    while offset < total_length:
        if offset + 8 > len(data):
            break
        chunk_length, chunk_type = struct.unpack_from("<II", data, offset)
        offset += 8
        chunk_data = data[offset: offset + chunk_length]
        offset += chunk_length

        if chunk_type == 0x4E4F534A:  # JSON chunk
            json_data = chunk_data
        elif chunk_type == 0x004E4942:  # BIN chunk
            bin_data = chunk_data

    gltf_dict = json.loads(json_data.decode("utf-8"))
    return gltf_dict, [bin_data]


def _load_gltf_buffers(gltf_dict: dict, base_dir: Path) -> list[bytes]:
    """glTF JSON から外部バッファを読み込む。"""
    buffers_data: list[bytes] = []
    for buf in gltf_dict.get("buffers", []):
        uri = buf.get("uri", "")
        if uri.startswith("data:"):
            # Data URI (base64)
            import base64
            _, encoded = uri.split(",", 1)
            buffers_data.append(base64.b64decode(encoded))
        else:
            buf_path = base_dir / uri
            if buf_path.exists():
                buffers_data.append(buf_path.read_bytes())
            else:
                buffers_data.append(b"")
    return buffers_data


def _gltf_to_stl_mesh(
    gltf_dict: dict,
    buffers_data: list[bytes],
    name: str,
) -> STLMesh:
    """glTF辞書からSTLMeshを構築する。"""
    accessors = gltf_dict.get("accessors", [])
    buffer_views = gltf_dict.get("bufferViews", [])
    meshes = gltf_dict.get("meshes", [])

    if not meshes:
        raise ValueError("glTFにメッシュが含まれていません")

    triangles: list[Triangle] = []
    exporter = STLExporter()

    for mesh_def in meshes:
        for prim in mesh_def.get("primitives", []):
            attributes = prim.get("attributes", {})
            pos_idx = attributes.get("POSITION")
            if pos_idx is None:
                continue

            pos_data = _read_gltf_accessor(
                accessors, buffer_views, buffers_data, pos_idx
            )
            positions: list[tuple[float, float, float]] = [
                (float(p[0]), float(p[1]), float(p[2])) for p in pos_data
            ]

            # インデックスバッファ
            indices_idx = prim.get("indices")
            if indices_idx is not None:
                raw_indices = _read_gltf_accessor(
                    accessors, buffer_views, buffers_data, indices_idx
                )
                indices = [int(i[0]) for i in raw_indices]
            else:
                indices = list(range(len(positions)))

            # 三角形を構築
            for i in range(0, len(indices) - 2, 3):
                i0, i1, i2 = indices[i], indices[i + 1], indices[i + 2]
                if i0 < len(positions) and i1 < len(positions) and i2 < len(positions):
                    v1 = positions[i0]
                    v2 = positions[i1]
                    v3 = positions[i2]
                    normal = exporter.compute_normal(v1, v2, v3)
                    triangles.append(Triangle(v1=v1, v2=v2, v3=v3, normal=normal))

    return STLMesh(name=name, triangles=tuple(triangles))
