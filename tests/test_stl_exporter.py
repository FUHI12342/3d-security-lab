"""
tests/test_stl_exporter.py

STLExporter のユニットテスト。
カバレッジ 90% 以上を目標とする。
"""

from __future__ import annotations

import math
import struct
import sys
from pathlib import Path

import pytest

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.stl_exporter import (
    STLExporter,
    STLMesh,
    Triangle,
    _cross,
    _normalize,
    _parse_obj_text,
    _sub,
)


# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------

@pytest.fixture
def exporter() -> STLExporter:
    """STLExporter インスタンス。"""
    return STLExporter()


@pytest.fixture
def single_triangle() -> STLMesh:
    """単純な1三角形メッシュ。"""
    v1 = (0.0, 0.0, 0.0)
    v2 = (1.0, 0.0, 0.0)
    v3 = (0.5, 1.0, 0.0)
    normal = STLExporter.compute_normal(v1, v2, v3)
    tri = Triangle(v1=v1, v2=v2, v3=v3, normal=normal)
    return STLMesh(name="test_triangle", triangles=(tri,))


@pytest.fixture
def cube_mesh() -> STLMesh:
    """簡易キューブメッシュ（12三角形）。"""
    exporter = STLExporter()
    vertices = [
        # 上面（Z=1）
        (0.0, 0.0, 1.0), (1.0, 0.0, 1.0), (1.0, 1.0, 1.0),
        (0.0, 0.0, 1.0), (1.0, 1.0, 1.0), (0.0, 1.0, 1.0),
        # 下面（Z=0）
        (0.0, 0.0, 0.0), (1.0, 1.0, 0.0), (1.0, 0.0, 0.0),
        (0.0, 0.0, 0.0), (0.0, 1.0, 0.0), (1.0, 1.0, 0.0),
        # 前面（Y=0）
        (0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 0.0, 1.0),
        (0.0, 0.0, 0.0), (1.0, 0.0, 1.0), (0.0, 0.0, 1.0),
        # 背面（Y=1）
        (1.0, 1.0, 0.0), (0.0, 1.0, 0.0), (0.0, 1.0, 1.0),
        (1.0, 1.0, 0.0), (0.0, 1.0, 1.0), (1.0, 1.0, 1.0),
        # 左面（X=0）
        (0.0, 1.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 1.0),
        (0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (0.0, 1.0, 1.0),
        # 右面（X=1）
        (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (1.0, 1.0, 1.0),
        (1.0, 0.0, 0.0), (1.0, 1.0, 1.0), (1.0, 0.0, 1.0),
    ]
    return exporter.from_vertices(vertices)


@pytest.fixture
def sample_obj_text() -> str:
    """OBJテキストサンプル。"""
    return """\
# Test OBJ
o triangle
v 0.0 0.0 0.0
v 1.0 0.0 0.0
v 0.5 1.0 0.0
vn 0.0 0.0 1.0
vn 0.0 0.0 1.0
vn 0.0 0.0 1.0
f 1//1 2//2 3//3
"""


@pytest.fixture
def sample_obj_file(tmp_path: Path, sample_obj_text: str) -> Path:
    """一時OBJファイル。"""
    obj_path = tmp_path / "sample.obj"
    obj_path.write_text(sample_obj_text, encoding="utf-8")
    return obj_path


@pytest.fixture
def quad_obj_file(tmp_path: Path) -> Path:
    """4角面を含む OBJ ファイル（fan triangulation テスト用）。"""
    text = """\
o quad
v 0.0 0.0 0.0
v 1.0 0.0 0.0
v 1.0 1.0 0.0
v 0.0 1.0 0.0
f 1 2 3 4
"""
    path = tmp_path / "quad.obj"
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def s3d_file(tmp_path: Path) -> Path:
    """S3Dサンプルファイルパス（プロジェクト内）。"""
    return PROJECT_ROOT / "targets" / "custom_format" / "samples" / "model_easy.s3d"


@pytest.fixture
def gltf_file(tmp_path: Path) -> Path:
    """シンプルな glTF ファイルを生成して返す。"""
    import json as _json

    # 1三角形の頂点データ
    positions = [
        0.0, 0.0, 0.0,
        1.0, 0.0, 0.0,
        0.5, 1.0, 0.0,
    ]
    bin_data = struct.pack(f"<{len(positions)}f", *positions)
    byte_length = len(bin_data)

    gltf = {
        "asset": {"version": "2.0"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0}],
        "meshes": [
            {
                "name": "test_mesh",
                "primitives": [
                    {
                        "attributes": {"POSITION": 0},
                        "mode": 4,
                    }
                ],
            }
        ],
        "accessors": [
            {
                "bufferView": 0,
                "componentType": 5126,
                "count": 3,
                "type": "VEC3",
                "min": [0.0, 0.0, 0.0],
                "max": [1.0, 1.0, 0.0],
            }
        ],
        "bufferViews": [
            {
                "buffer": 0,
                "byteOffset": 0,
                "byteLength": byte_length,
            }
        ],
        "buffers": [
            {
                "uri": "test.bin",
                "byteLength": byte_length,
            }
        ],
    }

    gltf_path = tmp_path / "test.gltf"
    bin_path = tmp_path / "test.bin"
    gltf_path.write_text(_json.dumps(gltf), encoding="utf-8")
    bin_path.write_bytes(bin_data)
    return gltf_path


# ---------------------------------------------------------------------------
# compute_normal テスト
# ---------------------------------------------------------------------------

class TestComputeNormal:
    """compute_normal() の精度テスト。"""

    def test_xy_plane_triangle_points_z_plus(self) -> None:
        """XY平面上の三角形の法線が (0,0,1) になる。"""
        v1 = (0.0, 0.0, 0.0)
        v2 = (1.0, 0.0, 0.0)
        v3 = (0.0, 1.0, 0.0)
        n = STLExporter.compute_normal(v1, v2, v3)
        assert n[0] == pytest.approx(0.0, abs=1e-6)
        assert n[1] == pytest.approx(0.0, abs=1e-6)
        assert n[2] == pytest.approx(1.0, abs=1e-6)

    def test_xz_plane_triangle(self) -> None:
        """XZ平面上の三角形の法線が Y 方向になる。"""
        v1 = (0.0, 0.0, 0.0)
        v2 = (1.0, 0.0, 0.0)
        v3 = (0.0, 0.0, 1.0)
        n = STLExporter.compute_normal(v1, v2, v3)
        assert abs(n[1]) == pytest.approx(1.0, abs=1e-6)

    def test_normalized_output(self) -> None:
        """法線ベクトルが単位長になる。"""
        v1 = (0.0, 0.0, 0.0)
        v2 = (3.0, 0.0, 0.0)
        v3 = (0.0, 4.0, 0.0)
        n = STLExporter.compute_normal(v1, v2, v3)
        length = math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2)
        assert length == pytest.approx(1.0, abs=1e-6)

    def test_degenerate_triangle_returns_tuple(self) -> None:
        """縮退三角形でも例外を起こさずタプルを返す。"""
        v1 = (0.0, 0.0, 0.0)
        v2 = (0.0, 0.0, 0.0)
        v3 = (0.0, 0.0, 0.0)
        n = STLExporter.compute_normal(v1, v2, v3)
        assert len(n) == 3

    def test_reversed_winding_gives_opposite_normal(self) -> None:
        """頂点の巻き順を逆にすると法線も逆になる。"""
        v1 = (0.0, 0.0, 0.0)
        v2 = (1.0, 0.0, 0.0)
        v3 = (0.0, 1.0, 0.0)
        n_cw = STLExporter.compute_normal(v1, v2, v3)
        n_ccw = STLExporter.compute_normal(v1, v3, v2)
        assert n_cw[2] == pytest.approx(-n_ccw[2], abs=1e-6)


# ---------------------------------------------------------------------------
# from_vertices テスト
# ---------------------------------------------------------------------------

class TestFromVertices:
    """from_vertices() のテスト。"""

    def test_three_vertices_no_indices(self, exporter: STLExporter) -> None:
        """インデックスなし: 3頂点で1三角形。"""
        verts = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.5, 1.0, 0.0)]
        mesh = exporter.from_vertices(verts)
        assert mesh.triangle_count == 1

    def test_six_vertices_two_triangles(self, exporter: STLExporter) -> None:
        """6頂点で2三角形（インデックスなし）。"""
        verts = [
            (0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.5, 1.0, 0.0),
            (2.0, 0.0, 0.0), (3.0, 0.0, 0.0), (2.5, 1.0, 0.0),
        ]
        mesh = exporter.from_vertices(verts)
        assert mesh.triangle_count == 2

    def test_with_indices(self, exporter: STLExporter) -> None:
        """インデックスあり: 正しい三角形が生成される。"""
        verts = [
            (0.0, 0.0, 0.0),
            (1.0, 0.0, 0.0),
            (0.5, 1.0, 0.0),
            (1.5, 1.0, 0.0),
        ]
        indices = [0, 1, 2, 1, 3, 2]
        mesh = exporter.from_vertices(verts, indices=indices)
        assert mesh.triangle_count == 2

    def test_decoded_vertex_objects(self, exporter: STLExporter) -> None:
        """DecodedVertex オブジェクトを受け付ける。"""
        from tools.vertex_decoder import DecodedVertex  # noqa: PLC0415
        verts = [
            DecodedVertex(position=(0.0, 0.0, 0.0)),
            DecodedVertex(position=(1.0, 0.0, 0.0)),
            DecodedVertex(position=(0.5, 1.0, 0.0)),
        ]
        mesh = exporter.from_vertices(verts)
        assert mesh.triangle_count == 1

    def test_s3d_vertex_objects(self, exporter: STLExporter) -> None:
        """S3D Vertex オブジェクトを受け付ける。"""
        from targets.custom_format.encoder import Vertex  # noqa: PLC0415
        verts = [
            Vertex(position=(0.0, 0.0, 0.0)),
            Vertex(position=(1.0, 0.0, 0.0)),
            Vertex(position=(0.5, 1.0, 0.0)),
        ]
        mesh = exporter.from_vertices(verts)
        assert mesh.triangle_count == 1

    def test_normals_computed(self, exporter: STLExporter) -> None:
        """法線が自動計算される。"""
        verts = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.5, 1.0, 0.0)]
        mesh = exporter.from_vertices(verts)
        tri = mesh.triangles[0]
        assert len(tri.normal) == 3
        length = math.sqrt(sum(c ** 2 for c in tri.normal))
        assert length == pytest.approx(1.0, abs=1e-5)

    def test_empty_returns_zero_triangles(self, exporter: STLExporter) -> None:
        """空頂点リストは三角形0のメッシュを返す。"""
        mesh = exporter.from_vertices([])
        assert mesh.triangle_count == 0

    def test_indices_out_of_range_skipped(self, exporter: STLExporter) -> None:
        """範囲外インデックスはスキップされる（例外なし）。"""
        verts = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.5, 1.0, 0.0)]
        indices = [0, 1, 2, 0, 1, 99]  # 99 は範囲外
        mesh = exporter.from_vertices(verts, indices=indices)
        assert mesh.triangle_count == 1  # 有効な1三角形のみ


# ---------------------------------------------------------------------------
# from_obj_file テスト
# ---------------------------------------------------------------------------

class TestFromObjFile:
    """from_obj_file() のテスト。"""

    def test_basic_triangle(
        self, exporter: STLExporter, sample_obj_file: Path
    ) -> None:
        """基本的なOBJファイルから1三角形が生成される。"""
        mesh = exporter.from_obj_file(sample_obj_file)
        assert mesh.triangle_count >= 1

    def test_mesh_name_from_filename(
        self, exporter: STLExporter, sample_obj_file: Path
    ) -> None:
        """メッシュ名がファイル名（拡張子なし）になる。"""
        mesh = exporter.from_obj_file(sample_obj_file)
        assert mesh.name == "sample"

    def test_quad_fan_triangulation(
        self, exporter: STLExporter, quad_obj_file: Path
    ) -> None:
        """4角面が2三角形に分割される（fan triangulation）。"""
        mesh = exporter.from_obj_file(quad_obj_file)
        assert mesh.triangle_count == 2

    def test_missing_file_raises(self, exporter: STLExporter) -> None:
        """存在しないファイルは FileNotFoundError を発生させる。"""
        with pytest.raises(FileNotFoundError):
            exporter.from_obj_file("/nonexistent/path/model.obj")

    def test_uses_vn_normals(
        self, exporter: STLExporter, sample_obj_file: Path
    ) -> None:
        """vn 法線がある場合はそれを使用する。"""
        mesh = exporter.from_obj_file(sample_obj_file)
        tri = mesh.triangles[0]
        # vn が (0,0,1) なのでそれに近い法線
        assert tri.normal[2] == pytest.approx(1.0, abs=1e-5)

    def test_obj_without_normals(
        self, exporter: STLExporter, tmp_path: Path
    ) -> None:
        """vn なしOBJでも外積で法線が計算される。"""
        text = "v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n"
        p = tmp_path / "no_norm.obj"
        p.write_text(text)
        mesh = exporter.from_obj_file(p)
        assert mesh.triangle_count == 1
        length = math.sqrt(sum(c ** 2 for c in mesh.triangles[0].normal))
        assert length == pytest.approx(1.0, abs=1e-5)

    def test_vertex_uv_format(
        self, exporter: STLExporter, tmp_path: Path
    ) -> None:
        """v/t/n 形式のface定義を正しく処理する。"""
        text = (
            "v 0 0 0\nv 1 0 0\nv 0 1 0\n"
            "vt 0 0\nvt 1 0\nvt 0 1\n"
            "vn 0 0 1\nvn 0 0 1\nvn 0 0 1\n"
            "f 1/1/1 2/2/2 3/3/3\n"
        )
        p = tmp_path / "vt.obj"
        p.write_text(text)
        mesh = exporter.from_obj_file(p)
        assert mesh.triangle_count == 1


# ---------------------------------------------------------------------------
# from_s3d_file テスト
# ---------------------------------------------------------------------------

class TestFromS3dFile:
    """from_s3d_file() のテスト。"""

    def test_easy_s3d_loads(
        self, exporter: STLExporter, s3d_file: Path
    ) -> None:
        """model_easy.s3d が正しくロードされる。"""
        if not s3d_file.exists():
            pytest.skip("サンプルS3Dファイルが存在しません")
        mesh = exporter.from_s3d_file(s3d_file)
        assert mesh.triangle_count > 0

    def test_s3d_triangles_have_normals(
        self, exporter: STLExporter, s3d_file: Path
    ) -> None:
        """全三角形に法線が設定されている。"""
        if not s3d_file.exists():
            pytest.skip("サンプルS3Dファイルが存在しません")
        mesh = exporter.from_s3d_file(s3d_file)
        for tri in mesh.triangles:
            assert len(tri.normal) == 3

    def test_missing_s3d_raises(self, exporter: STLExporter) -> None:
        """存在しないS3Dファイルは FileNotFoundError。"""
        with pytest.raises(FileNotFoundError):
            exporter.from_s3d_file("/nonexistent/path/model.s3d")

    def test_encoded_s3d(self, exporter: STLExporter, tmp_path: Path) -> None:
        """エンコード済みS3Dファイルを正しくデコードできる。"""
        from targets.custom_format.encoder import (  # noqa: PLC0415
            FLAG_XOR,
            S3DModel,
            Vertex,
            encode,
        )
        verts = (
            Vertex(position=(0.0, 0.0, 0.0)),
            Vertex(position=(1.0, 0.0, 0.0)),
            Vertex(position=(0.5, 1.0, 0.0)),
        )
        model = S3DModel(vertices=verts)
        data = encode(model, FLAG_XOR)
        s3d_path = tmp_path / "encoded.s3d"
        s3d_path.write_bytes(data)

        mesh = exporter.from_s3d_file(s3d_path)
        assert mesh.triangle_count >= 1


# ---------------------------------------------------------------------------
# from_gltf_file テスト
# ---------------------------------------------------------------------------

class TestFromGltfFile:
    """from_gltf_file() のテスト。"""

    def test_gltf_loads(
        self, exporter: STLExporter, gltf_file: Path
    ) -> None:
        """glTFファイルから三角形が生成される。"""
        mesh = exporter.from_gltf_file(gltf_file)
        assert mesh.triangle_count == 1

    def test_gltf_mesh_name(
        self, exporter: STLExporter, gltf_file: Path
    ) -> None:
        """メッシュ名がファイル名になる。"""
        mesh = exporter.from_gltf_file(gltf_file)
        assert mesh.name == "test"

    def test_gltf_with_indices(
        self, exporter: STLExporter, tmp_path: Path
    ) -> None:
        """インデックスバッファを持つ glTF を正しく処理する。"""
        import json as _json

        positions = [
            0.0, 0.0, 0.0,
            1.0, 0.0, 0.0,
            0.5, 1.0, 0.0,
            1.0, 1.0, 0.0,
        ]
        indices_list = [0, 1, 2, 1, 3, 2]

        pos_bytes = struct.pack(f"<{len(positions)}f", *positions)
        idx_bytes = struct.pack(f"<{len(indices_list)}H", *indices_list)
        total_bin = pos_bytes + idx_bytes

        gltf = {
            "asset": {"version": "2.0"},
            "scene": 0,
            "scenes": [{"nodes": [0]}],
            "nodes": [{"mesh": 0}],
            "meshes": [{"name": "m", "primitives": [
                {"attributes": {"POSITION": 0}, "indices": 1, "mode": 4}
            ]}],
            "accessors": [
                {
                    "bufferView": 0, "componentType": 5126,
                    "count": 4, "type": "VEC3",
                    "min": [0.0, 0.0, 0.0], "max": [1.0, 1.0, 0.0],
                },
                {
                    "bufferView": 1, "componentType": 5123,
                    "count": 6, "type": "SCALAR",
                },
            ],
            "bufferViews": [
                {"buffer": 0, "byteOffset": 0, "byteLength": len(pos_bytes)},
                {"buffer": 0, "byteOffset": len(pos_bytes), "byteLength": len(idx_bytes)},
            ],
            "buffers": [{"uri": "i.bin", "byteLength": len(total_bin)}],
        }
        p = tmp_path / "idx.gltf"
        (tmp_path / "i.bin").write_bytes(total_bin)
        p.write_text(_json.dumps(gltf))
        mesh = exporter.from_gltf_file(p)
        assert mesh.triangle_count == 2

    def test_missing_gltf_raises(self, exporter: STLExporter) -> None:
        """存在しないglTFは FileNotFoundError。"""
        with pytest.raises(FileNotFoundError):
            exporter.from_gltf_file("/nonexistent/model.gltf")

    def test_gltf_no_meshes_raises(
        self, exporter: STLExporter, tmp_path: Path
    ) -> None:
        """メッシュがないglTFは ValueError。"""
        import json as _json
        gltf = {"asset": {"version": "2.0"}, "meshes": []}
        p = tmp_path / "empty.gltf"
        p.write_text(_json.dumps(gltf))
        with pytest.raises(ValueError, match="メッシュ"):
            exporter.from_gltf_file(p)


# ---------------------------------------------------------------------------
# export_ascii テスト
# ---------------------------------------------------------------------------

class TestExportAscii:
    """export_ascii() のテスト。"""

    def test_creates_file(
        self,
        exporter: STLExporter,
        single_triangle: STLMesh,
        tmp_path: Path,
    ) -> None:
        """ファイルが作成される。"""
        out = tmp_path / "test.stl"
        result = exporter.export_ascii(single_triangle, out)
        assert result.exists()

    def test_starts_with_solid(
        self,
        exporter: STLExporter,
        single_triangle: STLMesh,
        tmp_path: Path,
    ) -> None:
        """ASCII STL は 'solid' で始まる。"""
        out = tmp_path / "test.stl"
        exporter.export_ascii(single_triangle, out)
        content = out.read_text()
        assert content.startswith("solid ")

    def test_ends_with_endsolid(
        self,
        exporter: STLExporter,
        single_triangle: STLMesh,
        tmp_path: Path,
    ) -> None:
        """ASCII STL は 'endsolid' で終わる。"""
        out = tmp_path / "test.stl"
        exporter.export_ascii(single_triangle, out)
        content = out.read_text().strip()
        assert content.endswith(f"endsolid {single_triangle.name}")

    def test_contains_facet_normal(
        self,
        exporter: STLExporter,
        single_triangle: STLMesh,
        tmp_path: Path,
    ) -> None:
        """facet normal 行が含まれる。"""
        out = tmp_path / "test.stl"
        exporter.export_ascii(single_triangle, out)
        assert "facet normal" in out.read_text()

    def test_contains_vertex_lines(
        self,
        exporter: STLExporter,
        single_triangle: STLMesh,
        tmp_path: Path,
    ) -> None:
        """vertex 行が含まれる。"""
        out = tmp_path / "test.stl"
        exporter.export_ascii(single_triangle, out)
        content = out.read_text()
        assert content.count("vertex") == 3

    def test_roundtrip_vertex_count(
        self,
        exporter: STLExporter,
        single_triangle: STLMesh,
        tmp_path: Path,
    ) -> None:
        """ASCII STL を再パースして頂点数が一致する。"""
        out = tmp_path / "test.stl"
        exporter.export_ascii(single_triangle, out)

        # 手動でパース
        content = out.read_text()
        vertex_lines = [l for l in content.splitlines() if "vertex" in l and "vertex " in l]
        assert len(vertex_lines) == single_triangle.triangle_count * 3

    def test_creates_parent_dirs(
        self,
        exporter: STLExporter,
        single_triangle: STLMesh,
        tmp_path: Path,
    ) -> None:
        """存在しない親ディレクトリも作成する。"""
        out = tmp_path / "a" / "b" / "test.stl"
        exporter.export_ascii(single_triangle, out)
        assert out.exists()

    def test_returns_path_object(
        self,
        exporter: STLExporter,
        single_triangle: STLMesh,
        tmp_path: Path,
    ) -> None:
        """Path オブジェクトを返す。"""
        out = tmp_path / "test.stl"
        result = exporter.export_ascii(single_triangle, out)
        assert isinstance(result, Path)


# ---------------------------------------------------------------------------
# export_binary テスト
# ---------------------------------------------------------------------------

class TestExportBinary:
    """export_binary() のテスト。"""

    def test_creates_file(
        self,
        exporter: STLExporter,
        single_triangle: STLMesh,
        tmp_path: Path,
    ) -> None:
        """ファイルが作成される。"""
        out = tmp_path / "test.stl"
        result = exporter.export_binary(single_triangle, out)
        assert result.exists()

    def test_header_80_bytes(
        self,
        exporter: STLExporter,
        single_triangle: STLMesh,
        tmp_path: Path,
    ) -> None:
        """ヘッダーが 80 bytes である。"""
        out = tmp_path / "test.stl"
        exporter.export_binary(single_triangle, out)
        data = out.read_bytes()
        # Binary STL: 80 bytes header + 4 bytes count + N * 50 bytes
        assert len(data) >= 84

    def test_triangle_count_in_header(
        self,
        exporter: STLExporter,
        single_triangle: STLMesh,
        tmp_path: Path,
    ) -> None:
        """バイナリ内の三角形数が正しい。"""
        out = tmp_path / "test.stl"
        exporter.export_binary(single_triangle, out)
        data = out.read_bytes()
        count = struct.unpack_from("<I", data, 80)[0]
        assert count == single_triangle.triangle_count

    def test_file_size_correct(
        self,
        exporter: STLExporter,
        single_triangle: STLMesh,
        tmp_path: Path,
    ) -> None:
        """ファイルサイズが正しい（80 + 4 + N×50）。"""
        out = tmp_path / "test.stl"
        exporter.export_binary(single_triangle, out)
        expected_size = 80 + 4 + single_triangle.triangle_count * 50
        assert out.stat().st_size == expected_size

    def test_roundtrip_vertex_count(
        self,
        exporter: STLExporter,
        cube_mesh: STLMesh,
        tmp_path: Path,
    ) -> None:
        """Binary STL を再パースして三角形数が一致する。"""
        out = tmp_path / "cube.stl"
        exporter.export_binary(cube_mesh, out)
        data = out.read_bytes()
        tri_count = struct.unpack_from("<I", data, 80)[0]
        assert tri_count == cube_mesh.triangle_count

    def test_vertex_data_preserved(
        self,
        exporter: STLExporter,
        single_triangle: STLMesh,
        tmp_path: Path,
    ) -> None:
        """頂点データがバイナリに正しく保存される。"""
        out = tmp_path / "test.stl"
        exporter.export_binary(single_triangle, out)
        data = out.read_bytes()

        # 最初の三角形のデータオフセット: 80 + 4 = 84
        # normal(12) + v1(12) + v2(12) + v3(12) + attr(2) = 50 bytes
        offset = 84
        normal_x = struct.unpack_from("<f", data, offset)[0]
        tri = single_triangle.triangles[0]
        assert normal_x == pytest.approx(tri.normal[0], abs=1e-6)

    def test_creates_parent_dirs(
        self,
        exporter: STLExporter,
        single_triangle: STLMesh,
        tmp_path: Path,
    ) -> None:
        """親ディレクトリを自動作成する。"""
        out = tmp_path / "sub" / "test.stl"
        exporter.export_binary(single_triangle, out)
        assert out.exists()


# ---------------------------------------------------------------------------
# validate_for_printing テスト
# ---------------------------------------------------------------------------

class TestValidateForPrinting:
    """validate_for_printing() のテスト。"""

    def test_valid_mesh_no_warnings(
        self,
        exporter: STLExporter,
        single_triangle: STLMesh,
    ) -> None:
        """正常なメッシュは警告なし（または最小限）。"""
        warnings = exporter.validate_for_printing(single_triangle)
        errors = [w for w in warnings if w.startswith("ERROR")]
        assert not errors

    def test_empty_mesh_error(self, exporter: STLExporter) -> None:
        """空メッシュはエラー。"""
        empty = STLMesh(name="empty", triangles=())
        warnings = exporter.validate_for_printing(empty)
        assert any("ERROR" in w and "0" in w for w in warnings)

    def test_degenerate_triangle_detected(self, exporter: STLExporter) -> None:
        """デジェネレート三角形（面積0）が検出される。"""
        v = (1.0, 0.0, 0.0)
        degenerate = Triangle(v1=v, v2=v, v3=v, normal=(0.0, 0.0, 1.0))
        mesh = STLMesh(name="degen", triangles=(degenerate,))
        warnings = exporter.validate_for_printing(mesh)
        assert any("デジェネレート" in w for w in warnings)

    def test_nan_coordinate_detected(self, exporter: STLExporter) -> None:
        """NaN座標が検出される。"""
        nan_tri = Triangle(
            v1=(float("nan"), 0.0, 0.0),
            v2=(1.0, 0.0, 0.0),
            v3=(0.5, 1.0, 0.0),
            normal=(0.0, 0.0, 1.0),
        )
        mesh = STLMesh(name="nan", triangles=(nan_tri,))
        warnings = exporter.validate_for_printing(mesh)
        assert any("NaN" in w or "Inf" in w for w in warnings)

    def test_inf_coordinate_detected(self, exporter: STLExporter) -> None:
        """Inf座標が検出される。"""
        inf_tri = Triangle(
            v1=(float("inf"), 0.0, 0.0),
            v2=(1.0, 0.0, 0.0),
            v3=(0.5, 1.0, 0.0),
            normal=(0.0, 0.0, 1.0),
        )
        mesh = STLMesh(name="inf", triangles=(inf_tri,))
        warnings = exporter.validate_for_printing(mesh)
        assert any("Inf" in w or "NaN" in w for w in warnings)

    def test_tiny_mesh_warning(self, exporter: STLExporter) -> None:
        """極端に小さいメッシュは警告。"""
        v1 = (0.0, 0.0, 0.0)
        v2 = (0.000001, 0.0, 0.0)
        v3 = (0.0, 0.000001, 0.0)
        normal = STLExporter.compute_normal(v1, v2, v3)
        tri = Triangle(v1=v1, v2=v2, v3=v3, normal=normal)
        mesh = STLMesh(name="tiny", triangles=(tri,))
        warnings = exporter.validate_for_printing(mesh)
        assert any("小さい" in w for w in warnings)

    def test_large_mesh_warning(self, exporter: STLExporter) -> None:
        """500mm超のメッシュは警告。"""
        v1 = (0.0, 0.0, 0.0)
        v2 = (600.0, 0.0, 0.0)
        v3 = (300.0, 100.0, 0.0)
        normal = STLExporter.compute_normal(v1, v2, v3)
        tri = Triangle(v1=v1, v2=v2, v3=v3, normal=normal)
        mesh = STLMesh(name="large", triangles=(tri,))
        warnings = exporter.validate_for_printing(mesh)
        assert any("大きすぎ" in w for w in warnings)

    def test_normal_inconsistency_detected(self, exporter: STLExporter) -> None:
        """逆向き法線が検出される。"""
        v1 = (0.0, 0.0, 0.0)
        v2 = (1.0, 0.0, 0.0)
        v3 = (0.5, 1.0, 0.0)
        # 意図的に逆向きの法線を設定
        wrong_normal = (0.0, 0.0, -1.0)
        tri = Triangle(v1=v1, v2=v2, v3=v3, normal=wrong_normal)
        mesh = STLMesh(name="flipped", triangles=(tri,))
        warnings = exporter.validate_for_printing(mesh)
        assert any("法線" in w for w in warnings)

    def test_valid_cube_returns_list(
        self, exporter: STLExporter, cube_mesh: STLMesh
    ) -> None:
        """有効なキューブメッシュはリストを返す（型チェック）。"""
        result = exporter.validate_for_printing(cube_mesh)
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# scale_to_mm テスト
# ---------------------------------------------------------------------------

class TestScaleToMm:
    """scale_to_mm() のテスト。"""

    def test_bounding_box_max_dim_equals_target(
        self, single_triangle: STLMesh
    ) -> None:
        """スケール後のバウンディングボックス最大辺が目標値になる。"""
        scaled = STLExporter.scale_to_mm(single_triangle, target_size_mm=50.0)
        bb_min, bb_max = scaled.bounding_box
        dims = [bb_max[i] - bb_min[i] for i in range(3)]
        max_dim = max(dims)
        assert max_dim == pytest.approx(50.0, rel=1e-5)

    def test_returns_new_mesh(self, single_triangle: STLMesh) -> None:
        """元のメッシュとは異なるオブジェクトを返す（イミュータブル）。"""
        scaled = STLExporter.scale_to_mm(single_triangle, 100.0)
        assert scaled is not single_triangle

    def test_triangle_count_preserved(self, single_triangle: STLMesh) -> None:
        """三角形数は変わらない。"""
        scaled = STLExporter.scale_to_mm(single_triangle, 100.0)
        assert scaled.triangle_count == single_triangle.triangle_count

    def test_empty_mesh_unchanged(self) -> None:
        """空メッシュはそのまま返す。"""
        empty = STLMesh(name="empty", triangles=())
        result = STLExporter.scale_to_mm(empty, 100.0)
        assert result.triangle_count == 0

    def test_scale_100mm(self, cube_mesh: STLMesh) -> None:
        """キューブを 100mm にスケールする。"""
        scaled = STLExporter.scale_to_mm(cube_mesh, 100.0)
        bb_min, bb_max = scaled.bounding_box
        dims = [bb_max[i] - bb_min[i] for i in range(3)]
        assert max(dims) == pytest.approx(100.0, rel=1e-5)

    def test_normal_unchanged_after_scale(self, single_triangle: STLMesh) -> None:
        """スケール後も法線ベクトルは変わらない。"""
        scaled = STLExporter.scale_to_mm(single_triangle, 200.0)
        orig_n = single_triangle.triangles[0].normal
        scaled_n = scaled.triangles[0].normal
        for i in range(3):
            assert orig_n[i] == pytest.approx(scaled_n[i], abs=1e-6)


# ---------------------------------------------------------------------------
# center_origin テスト
# ---------------------------------------------------------------------------

class TestCenterOrigin:
    """center_origin() のテスト。"""

    def test_center_is_at_origin(self, cube_mesh: STLMesh) -> None:
        """重心が原点（バウンディングボックス中心が0）になる。"""
        centered = STLExporter.center_origin(cube_mesh)
        bb_min, bb_max = centered.bounding_box
        cx = (bb_min[0] + bb_max[0]) / 2.0
        cy = (bb_min[1] + bb_max[1]) / 2.0
        cz = (bb_min[2] + bb_max[2]) / 2.0
        assert cx == pytest.approx(0.0, abs=1e-5)
        assert cy == pytest.approx(0.0, abs=1e-5)
        assert cz == pytest.approx(0.0, abs=1e-5)

    def test_triangle_count_preserved(self, cube_mesh: STLMesh) -> None:
        """三角形数は変わらない。"""
        centered = STLExporter.center_origin(cube_mesh)
        assert centered.triangle_count == cube_mesh.triangle_count

    def test_returns_new_mesh(self, cube_mesh: STLMesh) -> None:
        """元のメッシュとは異なるオブジェクトを返す。"""
        centered = STLExporter.center_origin(cube_mesh)
        assert centered is not cube_mesh

    def test_empty_mesh_unchanged(self) -> None:
        """空メッシュはそのまま返す。"""
        empty = STLMesh(name="empty", triangles=())
        result = STLExporter.center_origin(empty)
        assert result.triangle_count == 0

    def test_dimensions_preserved(self, cube_mesh: STLMesh) -> None:
        """中心移動後もサイズは変わらない。"""
        centered = STLExporter.center_origin(cube_mesh)
        bb_min_o, bb_max_o = cube_mesh.bounding_box
        bb_min_c, bb_max_c = centered.bounding_box
        for i in range(3):
            dim_orig = bb_max_o[i] - bb_min_o[i]
            dim_cent = bb_max_c[i] - bb_min_c[i]
            assert dim_orig == pytest.approx(dim_cent, abs=1e-5)


# ---------------------------------------------------------------------------
# STLMesh プロパティテスト
# ---------------------------------------------------------------------------

class TestSTLMesh:
    """STLMesh のプロパティテスト。"""

    def test_triangle_count_property(self, single_triangle: STLMesh) -> None:
        """triangle_count が正しい。"""
        assert single_triangle.triangle_count == 1

    def test_bounding_box_single_triangle(
        self, single_triangle: STLMesh
    ) -> None:
        """バウンディングボックスが正しい。"""
        bb_min, bb_max = single_triangle.bounding_box
        assert bb_min[0] == pytest.approx(0.0, abs=1e-6)
        assert bb_max[0] == pytest.approx(1.0, abs=1e-6)

    def test_bounding_box_empty_mesh(self) -> None:
        """空メッシュのバウンディングボックスはゼロ。"""
        empty = STLMesh(name="empty", triangles=())
        bb = empty.bounding_box
        assert bb == ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))

    def test_frozen_immutable(self, single_triangle: STLMesh) -> None:
        """frozen dataclass なので変更不可。"""
        with pytest.raises((AttributeError, TypeError)):
            single_triangle.name = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 往復テスト（OBJ → STL → 再パース）
# ---------------------------------------------------------------------------

class TestRoundtrip:
    """OBJ → STL → 再パースの往復テスト。"""

    def test_obj_to_binary_stl_roundtrip(
        self,
        exporter: STLExporter,
        sample_obj_file: Path,
        tmp_path: Path,
    ) -> None:
        """OBJ → Binary STL → 再パース → 三角形数保存。"""
        mesh = exporter.from_obj_file(sample_obj_file)
        out = tmp_path / "rt.stl"
        exporter.export_binary(mesh, out)

        # 再パース
        data = out.read_bytes()
        tri_count = struct.unpack_from("<I", data, 80)[0]
        assert tri_count == mesh.triangle_count

    def test_obj_to_ascii_stl_roundtrip(
        self,
        exporter: STLExporter,
        sample_obj_file: Path,
        tmp_path: Path,
    ) -> None:
        """OBJ → ASCII STL → 再パース → 頂点数保存。"""
        mesh = exporter.from_obj_file(sample_obj_file)
        out = tmp_path / "rt_ascii.stl"
        exporter.export_ascii(mesh, out)

        content = out.read_text()
        vertex_lines = [l for l in content.splitlines() if "      vertex " in l]
        assert len(vertex_lines) == mesh.triangle_count * 3

    def test_vertices_to_binary_stl(
        self, exporter: STLExporter, tmp_path: Path
    ) -> None:
        """頂点リスト → Binary STL → 三角形数確認。"""
        verts = [
            (0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.5, 1.0, 0.0),
            (2.0, 0.0, 0.0), (3.0, 0.0, 0.0), (2.5, 1.0, 0.0),
        ]
        mesh = exporter.from_vertices(verts)
        out = tmp_path / "verts.stl"
        exporter.export_binary(mesh, out)

        data = out.read_bytes()
        tri_count = struct.unpack_from("<I", data, 80)[0]
        assert tri_count == 2

    def test_scale_then_export(
        self, exporter: STLExporter, cube_mesh: STLMesh, tmp_path: Path
    ) -> None:
        """スケール → エクスポート → 三角形数保存。"""
        scaled = STLExporter.scale_to_mm(cube_mesh, 50.0)
        out = tmp_path / "scaled.stl"
        exporter.export_binary(scaled, out)
        data = out.read_bytes()
        tri_count = struct.unpack_from("<I", data, 80)[0]
        assert tri_count == cube_mesh.triangle_count


# ---------------------------------------------------------------------------
# CLIテスト（stl_converter.py の引数パース）
# ---------------------------------------------------------------------------

class TestSTLConverter:
    """stl_converter.py の引数パーステスト。"""

    def test_cli_help(self) -> None:
        """--help が正常終了する。"""
        import subprocess  # noqa: PLC0415
        result = subprocess.run(
            [sys.executable, "-m", "tools.stl_converter", "--help"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0
        assert "STL" in result.stdout

    def test_cli_convert_obj(
        self,
        sample_obj_file: Path,
        tmp_path: Path,
    ) -> None:
        """CLIでOBJからSTLに変換できる。"""
        import subprocess  # noqa: PLC0415
        out = tmp_path / "cli_out.stl"
        result = subprocess.run(
            [
                sys.executable, "-m", "tools.stl_converter",
                str(sample_obj_file), str(out),
            ],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0
        assert out.exists()

    def test_cli_ascii_flag(
        self,
        sample_obj_file: Path,
        tmp_path: Path,
    ) -> None:
        """--ascii フラグでASCII出力になる。"""
        import subprocess  # noqa: PLC0415
        out = tmp_path / "ascii_out.stl"
        result = subprocess.run(
            [
                sys.executable, "-m", "tools.stl_converter",
                str(sample_obj_file), str(out), "--ascii",
            ],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0
        assert out.exists()
        content = out.read_text()
        assert content.startswith("solid ")

    def test_cli_info_flag(
        self,
        sample_obj_file: Path,
        tmp_path: Path,
    ) -> None:
        """--info フラグで情報表示のみ（ファイル不要）。"""
        import subprocess  # noqa: PLC0415
        result = subprocess.run(
            [
                sys.executable, "-m", "tools.stl_converter",
                str(sample_obj_file), "--info",
            ],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0
        assert "三角形数" in result.stdout

    def test_cli_validate_flag(
        self,
        sample_obj_file: Path,
        tmp_path: Path,
    ) -> None:
        """--validate フラグでバリデーション結果が表示される。"""
        import subprocess  # noqa: PLC0415
        out = tmp_path / "validated.stl"
        result = subprocess.run(
            [
                sys.executable, "-m", "tools.stl_converter",
                str(sample_obj_file), str(out), "--validate",
            ],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0
        assert "チェック" in result.stdout

    def test_cli_scale_flag(
        self,
        sample_obj_file: Path,
        tmp_path: Path,
    ) -> None:
        """--scale フラグでスケール調整される。"""
        import subprocess  # noqa: PLC0415
        out = tmp_path / "scaled.stl"
        result = subprocess.run(
            [
                sys.executable, "-m", "tools.stl_converter",
                str(sample_obj_file), str(out), "--scale", "50",
            ],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0
        assert out.exists()

    def test_cli_missing_input(self, tmp_path: Path) -> None:
        """存在しない入力ファイルは終了コード 1。"""
        import subprocess  # noqa: PLC0415
        out = tmp_path / "out.stl"
        result = subprocess.run(
            [
                sys.executable, "-m", "tools.stl_converter",
                "/nonexistent/input.obj", str(out),
            ],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 1

    def test_cli_unsupported_extension(
        self, tmp_path: Path
    ) -> None:
        """未対応拡張子は終了コード 1。"""
        import subprocess  # noqa: PLC0415
        # ダミーファイルを作成
        dummy = tmp_path / "model.fbx"
        dummy.write_text("dummy")
        out = tmp_path / "out.stl"
        result = subprocess.run(
            [
                sys.executable, "-m", "tools.stl_converter",
                str(dummy), str(out),
            ],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 1


# ---------------------------------------------------------------------------
# 内部ヘルパー関数テスト
# ---------------------------------------------------------------------------

class TestHelperFunctions:
    """内部ヘルパー関数のテスト。"""

    def test_cross_product_xy(self) -> None:
        """XY 平面での外積（Z成分が非ゼロ）。"""
        a = (1.0, 0.0, 0.0)
        b = (0.0, 1.0, 0.0)
        result = _cross(a, b)
        assert result == pytest.approx((0.0, 0.0, 1.0), abs=1e-10)

    def test_cross_product_anticommutative(self) -> None:
        """外積の反交換性 a×b = -(b×a)。"""
        a = (1.0, 2.0, 3.0)
        b = (4.0, 5.0, 6.0)
        ab = _cross(a, b)
        ba = _cross(b, a)
        for i in range(3):
            assert ab[i] == pytest.approx(-ba[i], abs=1e-10)

    def test_sub_vector(self) -> None:
        """ベクトル差が正しい。"""
        result = _sub((3.0, 4.0, 5.0), (1.0, 2.0, 3.0))
        assert result == (2.0, 2.0, 2.0)

    def test_normalize_unit_vector(self) -> None:
        """正規化後が単位ベクトルになる。"""
        v = (3.0, 4.0, 0.0)
        result = _normalize(v)
        length = math.sqrt(sum(c ** 2 for c in result))
        assert length == pytest.approx(1.0, abs=1e-10)

    def test_normalize_zero_vector(self) -> None:
        """ゼロベクトルはそのまま返す（例外なし）。"""
        v = (0.0, 0.0, 0.0)
        result = _normalize(v)
        assert result == (0.0, 0.0, 0.0)

    def test_parse_obj_text_basic(self) -> None:
        """基本的な OBJ テキストをパースできる。"""
        text = "v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n"
        mesh = _parse_obj_text(text)
        assert mesh.triangle_count == 1

    def test_parse_obj_text_empty(self) -> None:
        """空テキストは三角形0。"""
        mesh = _parse_obj_text("")
        assert mesh.triangle_count == 0


# ---------------------------------------------------------------------------
# CTF チャレンジ検証テスト
# ---------------------------------------------------------------------------

class TestCTFVerify:
    """CTF challenge05 の verify.py テスト。"""

    def test_correct_flag_verifies(self) -> None:
        """正しいフラグが verify() で True になる。"""
        import sys  # noqa: PLC0415
        sys.path.insert(0, str(PROJECT_ROOT))
        from ctf.challenge05_print_the_flag.verify import verify  # noqa: PLC0415
        assert verify("FLAG{print_SEC3D}") is True

    def test_wrong_flag_fails(self) -> None:
        """間違ったフラグが verify() で False になる。"""
        from ctf.challenge05_print_the_flag.verify import verify  # noqa: PLC0415
        assert verify("FLAG{wrong_flag}") is False

    def test_flag_with_whitespace_stripped(self) -> None:
        """前後の空白は strip() されて検証される。"""
        from ctf.challenge05_print_the_flag.verify import verify  # noqa: PLC0415
        assert verify("  FLAG{print_SEC3D}  ") is True

    def test_empty_flag_fails(self) -> None:
        """空文字列は False。"""
        from ctf.challenge05_print_the_flag.verify import verify  # noqa: PLC0415
        assert verify("") is False


# ---------------------------------------------------------------------------
# text3d_generator テスト
# ---------------------------------------------------------------------------

class TestText3dGenerator:
    """text3d_generator.py のテスト。"""

    def test_generate_text_vertices_nonempty(self) -> None:
        """'A' 文字から頂点リストが生成される。"""
        from targets.custom_format.text3d_generator import (  # noqa: PLC0415
            generate_text_vertices,
        )
        verts = generate_text_vertices("A")
        assert len(verts) > 0

    def test_generate_text_vertices_multiple_of_3(self) -> None:
        """頂点数は3の倍数（三角形ベース）。"""
        from targets.custom_format.text3d_generator import (  # noqa: PLC0415
            generate_text_vertices,
        )
        verts = generate_text_vertices("ABC")
        assert len(verts) % 3 == 0

    def test_generate_text_s3d_produces_bytes(self) -> None:
        """generate_text_s3d() がバイト列を返す。"""
        from targets.custom_format.text3d_generator import (  # noqa: PLC0415
            generate_text_s3d,
        )
        data = generate_text_s3d("SEC3D")
        assert isinstance(data, bytes)
        assert len(data) > 0

    def test_generate_text_s3d_decodable(self) -> None:
        """生成した S3D データが decode() できる。"""
        from targets.custom_format.encoder import decode  # noqa: PLC0415
        from targets.custom_format.text3d_generator import (  # noqa: PLC0415
            generate_text_s3d,
        )
        data = generate_text_s3d("HI")
        model = decode(data)
        assert model.vertex_count > 0

    def test_extrude_height_affects_z(self) -> None:
        """押し出し高さが Z 座標に反映される。"""
        from targets.custom_format.text3d_generator import (  # noqa: PLC0415
            generate_text_vertices,
        )
        verts = generate_text_vertices("I", extrude_height=5.0)
        max_z = max(v[2] for v in verts)
        assert max_z == pytest.approx(5.0, abs=1e-5)

    def test_space_character_produces_no_vertices(self) -> None:
        """スペースのみは頂点なし（またはゼロ）。"""
        from targets.custom_format.text3d_generator import (  # noqa: PLC0415
            generate_text_vertices,
        )
        verts = generate_text_vertices(" ")
        assert len(verts) == 0
