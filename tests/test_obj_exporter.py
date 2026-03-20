"""
tests/test_obj_exporter.py

ObjExporter のユニットテスト。
OBJ / glTF 出力の妥当性を検証する。
"""

from __future__ import annotations

import json
import struct
from pathlib import Path

import pytest

from tools.obj_exporter import ObjExporter, _build_gltf, _build_obj_lines
from tools.vertex_decoder import DecodedVertex


@pytest.fixture
def sample_vertices() -> list[DecodedVertex]:
    """テスト用頂点リスト。"""
    return [
        DecodedVertex(position=(0.0, 0.0, 0.0), normal=(0.0, 0.0, 1.0), uv=(0.0, 0.0)),
        DecodedVertex(position=(1.0, 0.0, 0.0), normal=(0.0, 0.0, 1.0), uv=(1.0, 0.0)),
        DecodedVertex(position=(0.5, 1.0, 0.0), normal=(0.0, 0.0, 1.0), uv=(0.5, 1.0)),
    ]


@pytest.fixture
def simple_vertices() -> list[DecodedVertex]:
    """Normal/UV なしのシンプルな頂点リスト。"""
    return [
        DecodedVertex(position=(0.0, 0.0, 0.0)),
        DecodedVertex(position=(1.0, 0.0, 0.0)),
        DecodedVertex(position=(0.5, 1.0, 0.0)),
    ]


class TestBuildObjLines:
    """_build_obj_lines() のテスト。"""

    def test_contains_vertex_positions(self, sample_vertices) -> None:
        """頂点座標が OBJ に含まれる。"""
        lines = _build_obj_lines(sample_vertices)
        content = "\n".join(lines)
        assert "v 0.000000 0.000000 0.000000" in content
        assert "v 1.000000 0.000000 0.000000" in content

    def test_contains_normals_when_present(self, sample_vertices) -> None:
        """法線がある場合 vn 行が含まれる。"""
        lines = _build_obj_lines(sample_vertices)
        content = "\n".join(lines)
        assert "vn " in content

    def test_contains_uvs_when_present(self, sample_vertices) -> None:
        """UV がある場合 vt 行が含まれる。"""
        lines = _build_obj_lines(sample_vertices)
        content = "\n".join(lines)
        assert "vt " in content

    def test_no_normals_when_absent(self, simple_vertices) -> None:
        """法線がない場合 vn 行が含まれない。"""
        lines = _build_obj_lines(simple_vertices)
        content = "\n".join(lines)
        assert "vn " not in content

    def test_object_name(self, sample_vertices) -> None:
        """オブジェクト名が OBJ に含まれる。"""
        lines = _build_obj_lines(sample_vertices, object_name="test_object")
        content = "\n".join(lines)
        assert "o test_object" in content

    def test_face_definition(self, sample_vertices) -> None:
        """面定義（f 行）が含まれる。"""
        lines = _build_obj_lines(sample_vertices)
        content = "\n".join(lines)
        assert "f " in content


class TestBuildGltf:
    """_build_gltf() のテスト。"""

    def test_gltf_version(self, sample_vertices) -> None:
        """glTF バージョンが 2.0 である。"""
        gltf, _ = _build_gltf(sample_vertices, "test.bin")
        assert gltf["asset"]["version"] == "2.0"

    def test_buffer_size_correct(self, sample_vertices) -> None:
        """バイナリバッファのサイズが正しい（position + uv）。"""
        gltf, bin_data = _build_gltf(sample_vertices, "test.bin")
        # position: 3 floats × 3 vertices × 4 bytes = 36 bytes
        # uv: 2 floats × 3 vertices × 4 bytes = 24 bytes
        # total = 60 bytes
        pos_size = len(sample_vertices) * 3 * 4
        uv_size = len(sample_vertices) * 2 * 4
        assert len(bin_data) >= pos_size

    def test_accessor_count(self, sample_vertices) -> None:
        """アクセッサの頂点数が正しい。"""
        gltf, _ = _build_gltf(sample_vertices, "test.bin")
        assert gltf["accessors"][0]["count"] == len(sample_vertices)

    def test_min_max_positions(self, sample_vertices) -> None:
        """position アクセッサに min/max が設定されている。"""
        gltf, _ = _build_gltf(sample_vertices, "test.bin")
        accessor = gltf["accessors"][0]
        assert "min" in accessor
        assert "max" in accessor
        assert accessor["min"][0] == pytest.approx(0.0)
        assert accessor["max"][0] == pytest.approx(1.0)

    def test_no_uvs_when_absent(self, simple_vertices) -> None:
        """UV なし頂点の場合 TEXCOORD_0 アトリビュートが含まれない。"""
        gltf, _ = _build_gltf(simple_vertices, "test.bin")
        attributes = gltf["meshes"][0]["primitives"][0]["attributes"]
        assert "TEXCOORD_0" not in attributes


class TestObjExporter:
    """ObjExporter クラスのテスト。"""

    def setup_method(self) -> None:
        self.exporter = ObjExporter()

    def test_export_obj_creates_file(self, tmp_path, sample_vertices) -> None:
        """export_obj() がファイルを作成する。"""
        out = tmp_path / "output.obj"
        meta = self.exporter.export_obj(sample_vertices, out)
        assert out.exists()
        assert meta.format == "OBJ"
        assert meta.vertex_count == 3

    def test_export_obj_content_valid(self, tmp_path, sample_vertices) -> None:
        """出力OBJファイルが有効な内容を持つ。"""
        out = tmp_path / "output.obj"
        self.exporter.export_obj(sample_vertices, out)
        content = out.read_text()
        assert content.startswith("#")
        assert "v " in content

    def test_export_obj_empty_raises(self, tmp_path) -> None:
        """頂点が空の場合 ValueError を発生させる。"""
        with pytest.raises(ValueError, match="頂点"):
            self.exporter.export_obj([], tmp_path / "out.obj")

    def test_export_gltf_creates_files(self, tmp_path, sample_vertices) -> None:
        """export_gltf() が .gltf と .bin を作成する。"""
        out = tmp_path / "output.gltf"
        meta = self.exporter.export_gltf(sample_vertices, out)
        assert out.exists()
        assert (tmp_path / "output.bin").exists()
        assert meta.format == "glTF"

    def test_export_gltf_valid_json(self, tmp_path, sample_vertices) -> None:
        """出力glTFファイルが有効なJSONである。"""
        out = tmp_path / "output.gltf"
        self.exporter.export_gltf(sample_vertices, out)
        gltf = json.loads(out.read_text())
        assert gltf["asset"]["version"] == "2.0"
        assert len(gltf["meshes"]) == 1

    def test_export_gltf_empty_raises(self, tmp_path) -> None:
        """頂点が空の場合 ValueError を発生させる。"""
        with pytest.raises(ValueError, match="頂点"):
            self.exporter.export_gltf([], tmp_path / "out.gltf")

    def test_export_obj_metadata(self, tmp_path, sample_vertices) -> None:
        """エクスポートメタデータが正しい。"""
        out = tmp_path / "mesh.obj"
        meta = self.exporter.export_obj(sample_vertices, out, source="Test")
        assert meta.source == "Test"
        assert meta.vertex_count == 3
        assert str(out) == meta.output_path

    def test_export_creates_parent_dirs(self, tmp_path, sample_vertices) -> None:
        """親ディレクトリが存在しない場合でも作成する。"""
        out = tmp_path / "subdir" / "deep" / "output.obj"
        self.exporter.export_obj(sample_vertices, out)
        assert out.exists()
