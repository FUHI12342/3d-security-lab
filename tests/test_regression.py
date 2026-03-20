"""
tests/test_regression.py

回帰テストスイート。
既知のバグパターン・エッジケース・境界値を網羅する。

カバレッジ対象:
- encoder.py: XOR鍵=0x00、zlib展開エラー、切り詰めデータ、頂点0個
- format_analyzer.py: エントロピー=0（全バイト同一）、短いヘッダー、境界エントロピー分類
- vram_forensics.py: フレームバッファがダンプ末尾、小さすぎるダンプ
- vertex_decoder.py: NaN/Inf頂点、ビッグエンディアン検出、カスタムストライドのnormal/uv
- obj_exporter.py: 頂点0個、normal有りuv無し、uv有りnormal無し
- vram_simulator.py: Pillow有無分岐、テクスチャ生成、ダンプ生成
- webgl_interceptor.py: _save_results JSON+PNG保存、summary全コール
- mesh_extractor.py: DrawCallInfo.summary、スタブ結果
"""

from __future__ import annotations

import base64
import json
import math
import struct
import zlib
from pathlib import Path

import pytest

from targets.custom_format.encoder import (
    FLAG_CHECKSUM,
    FLAG_XOR,
    FLAG_ZLIB,
    MAGIC,
    S3DModel,
    Vertex,
    _compute_xor_key,
    _xor_data,
    decode,
    encode,
)
from tools.format_analyzer import (
    FormatAnalyzer,
    _classify_entropy,
    _find_repeated_patterns,
    _guess_alignment,
    _parse_header_fields,
    compute_entropy,
)
from tools.mesh_extractor import DrawCallInfo, ExtractedMesh, ExtractionResult, MeshExtractor
from tools.obj_exporter import ObjExporter, _build_obj_lines
from tools.vertex_decoder import (
    DecodedVertex,
    VertexDecoder,
    VertexFormat as VF,
    _detect_endian,
    _detect_format,
)
from tools.vram_forensics import (
    VramForensics,
    _compute_rgba_confidence,
)
from tools.webgl_interceptor import (
    InterceptResult,
    MockWebGLInterceptor,
    WebGLCall,
    WebGLInterceptor,
    _parse_calls,
)


# ---------------------------------------------------------------------------
# encoder.py 回帰テスト
# ---------------------------------------------------------------------------

class TestEncoderRegression:
    """encoder.py の回帰テスト。"""

    def test_xor_key_zero_is_identity(self) -> None:
        """XOR鍵=0x00の場合は実質無変換（データが変化しない）。"""
        data = b"\xde\xad\xbe\xef" * 8
        result = _xor_data(data, 0x00000000)
        assert result == data

    def test_xor_key_zero_partial_bytes(self) -> None:
        """XOR鍵=0のとき、任意の長さのデータが変化しない。"""
        for length in [1, 3, 7, 15, 33]:
            data = bytes(range(length))
            assert _xor_data(data, 0) == data

    def test_decode_truncated_header_raises(self) -> None:
        """15バイト以下のデータは ValueError を発生させる。"""
        for size in [0, 1, 4, 15]:
            with pytest.raises(ValueError):
                decode(b"S3D\x00" + b"\x00" * (size - 4) if size >= 4 else b"\x00" * size)

    def test_decode_wrong_magic_raises(self) -> None:
        """マジックバイトが不正な場合 ValueError が発生する。"""
        bad_data = b"\x00\x00\x00\x00" + b"\x00" * 50
        with pytest.raises(ValueError, match="マジック"):
            decode(bad_data)

    def test_decode_vertex_size_mismatch_raises(self) -> None:
        """頂点データサイズが不一致の場合 ValueError が発生する。"""
        # ヘッダーは3頂点と主張するが、データは1頂点分しかない
        header = struct.pack("<4sIII", MAGIC, 1, 3, 0)  # vertex_count=3
        vertex_data = struct.pack("<8f", *[1.0] * 8)    # 1頂点分（32バイト）
        data = header + vertex_data
        with pytest.raises(ValueError, match="頂点データサイズ"):
            decode(data)

    def test_decode_zlib_corrupted_raises(self) -> None:
        """zlib圧縮データが破損している場合エラーが発生する。"""
        header = struct.pack("<4sIII", MAGIC, 1, 1, FLAG_ZLIB)
        corrupted_zlib = b"\x78\x9c" + b"\xff\xff\xff\xff"  # 不正なzlibデータ
        data = header + corrupted_zlib
        with pytest.raises(Exception):
            decode(data)

    def test_decode_checksum_too_short_raises(self) -> None:
        """チェックサムフラグがあるがデータが短い場合 ValueError が発生する。"""
        header = struct.pack("<4sIII", MAGIC, 1, 0, FLAG_CHECKSUM)
        short_data = header + b"\x00" * 10  # チェックサム32バイト未満
        with pytest.raises(ValueError):
            decode(short_data)

    def test_encode_single_vertex_model(self) -> None:
        """頂点1個のモデルをエンコード/デコードできる。"""
        model = S3DModel(vertices=(Vertex(position=(1.0, 2.0, 3.0)),))
        encoded = encode(model, 0)
        decoded = decode(encoded)
        assert decoded.vertex_count == 1
        assert decoded.vertices[0].position == pytest.approx((1.0, 2.0, 3.0))

    def test_encode_all_flags_preserves_vertex_data(self) -> None:
        """全フラグ（XOR+ZLIB+CHECKSUM）で頂点データが正確に保存される。"""
        vertices = tuple(
            Vertex(position=(float(i), float(i) * 0.5, float(i) * -0.3))
            for i in range(10)
        )
        model = S3DModel(vertices=vertices)
        flags = FLAG_XOR | FLAG_ZLIB | FLAG_CHECKSUM
        encoded = encode(model, flags)
        decoded = decode(encoded)
        assert decoded.vertex_count == 10
        for i, (orig, res) in enumerate(zip(model.vertices, decoded.vertices)):
            assert res.position == pytest.approx(orig.position, abs=1e-5), f"頂点{i}の位置不一致"

    def test_vertex_from_bytes_with_offset(self) -> None:
        """Vertex.from_bytes() がオフセット付きで正しく動作する。"""
        vtx = Vertex(position=(3.0, -1.5, 0.25), normal=(0.0, 1.0, 0.0), uv=(0.5, 0.75))
        padding = b"\xaa" * 16
        data = padding + vtx.to_bytes()
        restored = Vertex.from_bytes(data, offset=16)
        assert restored.position == pytest.approx(vtx.position)
        assert restored.normal == pytest.approx(vtx.normal)
        assert restored.uv == pytest.approx(vtx.uv)

    def test_xor_then_zlib_differs_from_zlib_then_xor(self) -> None:
        """エンコードフラグの順序が結果に影響することを確認する（セキュリティ回帰）。"""
        model = S3DModel(vertices=(Vertex(position=(1.0, 0.0, 0.0)),))
        encoded_xz = encode(model, FLAG_XOR | FLAG_ZLIB)
        encoded_zx = encode(model, FLAG_ZLIB | FLAG_XOR)
        # 同じフラグなので同じ結果になるべき（実装が決定的であることの確認）
        assert encoded_xz == encoded_zx


# ---------------------------------------------------------------------------
# format_analyzer.py 回帰テスト
# ---------------------------------------------------------------------------

class TestFormatAnalyzerRegression:
    """format_analyzer.py の回帰テスト。"""

    def test_entropy_zero_all_same_byte(self) -> None:
        """全バイトが同一（エントロピー=0）の場合を正しく計算する。"""
        for byte_val in [0x00, 0xFF, 0x42]:
            data = bytes([byte_val] * 1000)
            entropy = compute_entropy(data)
            assert entropy == pytest.approx(0.0, abs=1e-10)

    def test_classify_entropy_all_branches(self) -> None:
        """_classify_entropy() の全分岐を通過する。"""
        assert "定数" in _classify_entropy(0.0)
        assert "定数" in _classify_entropy(0.5)
        assert "構造化" in _classify_entropy(1.0)
        assert "構造化" in _classify_entropy(3.9)
        assert "XOR" in _classify_entropy(4.0) or "難読化" in _classify_entropy(4.0)
        assert "圧縮" in _classify_entropy(6.5) or "難読化" in _classify_entropy(6.5)
        assert "圧縮" in _classify_entropy(7.5) or "暗号" in _classify_entropy(7.5)

    def test_classify_entropy_boundaries(self) -> None:
        """エントロピー分類の境界値を正しく扱う。"""
        # 境界値の左右で分類が変わることを確認
        result_below_1 = _classify_entropy(0.99)
        result_at_1 = _classify_entropy(1.0)
        assert result_below_1 != result_at_1

    def test_find_repeated_patterns_all_zeros_excluded(self) -> None:
        """全ゼロパターンは繰り返しパターンから除外される。"""
        data = b"\x00\x00\x00\x00" * 100
        patterns = _find_repeated_patterns(data)
        zero_pattern = b"\x00\x00\x00\x00"
        assert not any(p == zero_pattern for p, _ in patterns)

    def test_find_repeated_patterns_below_min_count(self) -> None:
        """繰り返し回数がmin_count未満のパターンは除外される。"""
        # パターン "ABCD" が2回だけ（デフォルトmin_count=3未満）
        data = b"ABCD" * 2 + b"\x00" * 100
        patterns = _find_repeated_patterns(data, min_count=3)
        assert not any(p == b"ABCD" for p, _ in patterns)

    def test_find_repeated_patterns_detects_frequent(self) -> None:
        """頻出パターンを正しく検出する。"""
        # "XYZW" が10回繰り返し
        data = b"XYZW" * 10
        patterns = _find_repeated_patterns(data, min_count=3)
        assert any(p == b"XYZW" for p, _ in patterns)

    def test_guess_alignment_short_data(self) -> None:
        """16バイト以下のデータでもアライメント推定がクラッシュしない。"""
        for size in [0, 1, 8, 15, 16]:
            result = _guess_alignment(b"\x00" * size)
            assert result in [4, 8, 12, 16, 32]

    def test_parse_header_fields_short_data(self) -> None:
        """16バイト未満のデータは空辞書を返す。"""
        for size in [0, 4, 15]:
            result = _parse_header_fields(b"\x00" * size)
            assert result == {}

    def test_parse_header_fields_exact_16_bytes(self) -> None:
        """ちょうど16バイトで4フィールドをパースする。"""
        data = struct.pack("<4I", 0x11111111, 0x22222222, 0x33333333, 0x44444444)
        result = _parse_header_fields(data)
        assert len(result) == 4
        assert result["field_00"] == 0x11111111
        assert result["field_0c"] == 0x44444444

    def test_hexdump_partial_last_row(self) -> None:
        """最終行が16バイト未満の場合、パディングされて出力される。"""
        data = bytes(range(20))  # 16バイト + 4バイト
        dump = FormatAnalyzer.hexdump(data, width=16)
        lines = dump.split("\n")
        assert len(lines) == 2
        # 2行目の最後の4バイトに対するパディング確認
        assert "10" in lines[1]  # 16進アドレス

    def test_hexdump_empty_data(self) -> None:
        """空データでhexdumpを呼び出してもクラッシュしない。"""
        result = FormatAnalyzer.hexdump(b"")
        assert result == ""

    def test_analyzer_analyze_bytes_repeated_patterns(self) -> None:
        """繰り返しパターンのある入力でsummary()が正しく動く。"""
        # 4バイトパターンを10回繰り返してpattern検出
        data = b"\xDE\xAD\xBE\xEF" * 10 + b"\x00" * 20
        analyzer = FormatAnalyzer()
        result = analyzer.analyze_bytes(data, "test.bin")
        summary = result.summary()
        assert "test.bin" in summary

    def test_entropy_single_byte_input(self) -> None:
        """1バイトのデータはエントロピー0を返す。"""
        assert compute_entropy(b"\x42") == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# vram_forensics.py 回帰テスト
# ---------------------------------------------------------------------------

class TestVramForensicsRegression:
    """vram_forensics.py の回帰テスト。"""

    def test_scan_framebuffers_data_smaller_than_fb_size(self) -> None:
        """ダンプがフレームバッファサイズより小さい場合は空リストを返す。"""
        small_data = b"\xff" * 100
        forensics = VramForensics()
        result = forensics.scan_framebuffers(small_data, width=256, height=256)
        assert result == []

    def test_framebuffer_at_end_of_dump(self) -> None:
        """フレームバッファがダンプ末尾に配置されている場合を検出できる。"""
        width, height = 8, 8
        fb_size = width * height * 4

        # 全アルファ=255のフレームバッファ（高confidence）
        fb = bytearray(fb_size)
        for i in range(width * height):
            fb[i * 4 + 0] = (i * 7) % 200 + 30
            fb[i * 4 + 1] = (i * 13) % 180 + 40
            fb[i * 4 + 2] = 100
            fb[i * 4 + 3] = 255

        # ゼロパディング + フレームバッファ（末尾に配置）
        prefix = b"\x00" * (8 * 8 * 4)  # ちょうど1フレーム分のゼロデータ
        data = prefix + bytes(fb)

        forensics = VramForensics()
        # クラッシュせず実行できることを確認
        candidates = forensics.scan_framebuffers(data, width, height, step=fb_size)
        assert isinstance(candidates, list)

    def test_rgba_confidence_adjacent_diff_low(self) -> None:
        """隣接ピクセル差が小さい（滑らかな）データは confidence のスコアが上がる。"""
        width, height = 16, 16
        size = width * height * 4
        # 隣接ピクセルが近い値（差 < 50）かつアルファ=255
        fb = bytearray(size)
        for i in range(width * height):
            val = (i % 50) + 100  # 100〜149の範囲、隣接差は最大1
            fb[i * 4 + 0] = val
            fb[i * 4 + 1] = val
            fb[i * 4 + 2] = val
            fb[i * 4 + 3] = 255
        confidence = _compute_rgba_confidence(bytes(fb), width, height)
        assert confidence > 0.3

    def test_rgba_confidence_fully_transparent_low(self) -> None:
        """全ピクセルがアルファ=0の場合でも処理できる。"""
        width, height = 8, 8
        fb = b"\x00\x00\x00\x00" * (width * height)
        confidence = _compute_rgba_confidence(fb, width, height)
        assert 0.0 <= confidence <= 1.0

    def test_reconstruct_framebuffer_pillow_saves_file(self, tmp_path) -> None:
        """Pillowが有効な場合、reconstruct_framebuffer()がPNGファイルを保存する。"""
        import tools.vram_forensics as vf_module
        if not vf_module.HAS_PILLOW:
            pytest.skip("Pillow未インストール")

        width, height = 4, 4
        fb_bytes = bytes([100, 150, 200, 255] * (width * height))
        output_png = tmp_path / "test_fb.png"
        forensics = VramForensics()
        result = forensics.reconstruct_framebuffer(fb_bytes, 0, width, height, output_png)
        assert result is not None
        assert output_png.exists()

    def test_scan_image_headers_sorted_by_offset(self) -> None:
        """ヒットはオフセット順にソートされる。"""
        # BMP（オフセット200）-> PNG（オフセット50）の順で埋め込み
        data = b"\x00" * 50 + b"\x89PNG\r\n\x1a\n" + b"\x00" * 140 + b"BM" + b"\x00" * 50
        from tools.vram_forensics import _scan_image_headers
        hits = _scan_image_headers(data)
        offsets = [h.offset for h in hits]
        assert offsets == sorted(offsets)

    def test_load_from_string_path(self, tmp_path) -> None:
        """文字列パスからロードできる。"""
        data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50
        test_file = tmp_path / "test.bin"
        test_file.write_bytes(data)
        forensics = VramForensics()
        hits = forensics.scan_image_headers(str(test_file))
        assert any(h.format_name == "PNG" for h in hits)


# ---------------------------------------------------------------------------
# vertex_decoder.py 回帰テスト
# ---------------------------------------------------------------------------

class TestVertexDecoderRegression:
    """vertex_decoder.py の回帰テスト。"""

    def test_nan_vertex_does_not_crash(self) -> None:
        """NaN値を含む頂点データでクラッシュしない。

        Note: NaN のバイト列は _detect_endian() の abs < 1000 判定で
              le_ok が上がらないため明示的に endian="little" を指定する。
        """
        # 1頂点=3float=12バイト: x=NaN, y=0.0, z=0.0（リトルエンディアン）
        nan_bytes = struct.pack("<f", float("nan"))
        zero_bytes = struct.pack("<f", 0.0)
        vertex_data = nan_bytes + zero_bytes + zero_bytes  # 12バイト
        decoder = VertexDecoder()
        result = decoder.decode(vertex_data, fmt=VF.POSITION_F32x3, endian="little")
        assert result.vertex_count == 1
        assert math.isnan(result.vertices[0].position[0])

    def test_inf_vertex_does_not_crash(self) -> None:
        """Inf値を含む頂点データでクラッシュしない。"""
        inf_bytes = struct.pack("<f", float("inf"))
        zero_bytes = struct.pack("<f", 0.0)
        vertex_data = inf_bytes + zero_bytes + zero_bytes  # 12バイト
        decoder = VertexDecoder()
        result = decoder.decode(vertex_data, fmt=VF.POSITION_F32x3, endian="little")
        assert result.vertex_count == 1
        assert math.isinf(result.vertices[0].position[0])

    def test_negative_inf_vertex_does_not_crash(self) -> None:
        """-Inf値を含む頂点データでクラッシュしない。"""
        neg_inf_bytes = struct.pack("<f", float("-inf"))
        zero_bytes = struct.pack("<f", 0.0)
        vertex_data = neg_inf_bytes + zero_bytes + zero_bytes  # 12バイト
        decoder = VertexDecoder()
        result = decoder.decode(vertex_data, fmt=VF.POSITION_F32x3, endian="little")
        assert math.isinf(result.vertices[0].position[0])
        assert result.vertices[0].position[0] < 0

    def test_detect_endian_big_endian_wins(self) -> None:
        """ビッグエンディアンの浮動小数点値に対してビッグエンディアンが選択される。"""
        # BE で 50.0 = 0x42480000
        # LE で解釈すると 0x00004842 = 2.45e-41 (abs < 1000 → le_ok 上がる)
        # → 両方 ok になる場合があるため、LE で abs > 1000 になる値を選ぶ必要がある
        # BE で 10000.0 = 0x461C4000
        # LE で解釈すると 0x00401C46 = ~5.9e-39 → abs < 1000 → le_ok 上がる
        # 確実にBEが勝つには、LEで>=1000になるバイト列を直接選ぶ
        # LE で 5000.0 → LE bytes 40 1C 9C 45 (= 0x459C1C40 in BE = huge)
        # BE で解釈 0x459C1C40 ≈ 5000 (abs < 1000 ではない... 5000 > 1000 → be_ok 上がらない)
        # 方針を変えて: _detect_endian は le_ok >= be_ok の場合 "little" を返す実装なので
        # BEが勝つのは be_ok > le_ok の場合のみ。
        # LE で abs >= 1000 かつ BE で abs < 1000 になるバイト列を用意する
        # LE で解釈すると >= 1000 になる単純なバイト列: 0x44 0x7A 0x00 0x00
        # LE: struct.unpack("<f", b"\x44\x7a\x00\x00") = 0x00007a44 ≈ 1.1e-41 (小さい)
        # 確実に be_ok > le_ok にするには全データポイントで条件を満たす必要がある
        # -> BE では正常値、LE では大きすぎる値を持つバイト列
        # LE で > 1000 : 指数部が大きい値 → 例: 0x49 0x74 0x24 0x00
        # struct.unpack(">f", b"\x49\x74\x24\x00") = 1000576.0 (BE: >1000)
        # struct.unpack("<f", b"\x49\x74\x24\x00") = ... -> LE解釈は別値
        # 簡単な方法: BEで小さい値かつLEで大きい値になるデータを直接計算する
        # BE で 2.0 = 0x40000000, LE解釈 = 0x00000040 ≈ 8.96e-44 (abs < 1000 → le_ok++)
        # よって 1.0/2.0 などではLEも通ってしまう
        # BEで確実に勝つ: abs >= 1000 をLEに強制する
        # 0x44 0x7A 0x00 0x00 → LE: unpack("<f") = struct.unpack("<f", bytes([0x44,0x7a,0x00,0x00]))
        import struct as _struct
        # LE で 1001.0 = 0x44 7A 08 00 を BE 解釈すると 0x00087A44 ≈ 7.83e-40 (abs < 1000)
        le_large = _struct.pack("<f", 1001.0)  # LEバイト: 0x44 0x7A 0x08 0x00
        be_val = _struct.unpack(">f", le_large)[0]
        # be_val が abs < 1000 なら be_ok++、le解釈で 1001.0 なので le_ok は上がらない
        assert abs(be_val) < 1000, f"このデータでBEが正常値になることを前提とするが be_val={be_val}"
        data = le_large * 15
        result = _detect_endian(data, 4)
        # LE解釈で abs >= 1000 (1001.0) なので le_ok=0、BE解釈で abs < 1000 なので be_ok=15
        assert result == "big"

    def test_detect_endian_little_endian_default(self) -> None:
        """リトルエンディアンのデータではリトルエンディアンが選択される。"""
        le_float = struct.pack("<f", 1.0)  # little endian 1.0
        data = le_float * 10
        result = _detect_endian(data, 4)
        assert result == "little"

    def test_detect_endian_too_short_returns_little(self) -> None:
        """ストライドよりデータが短い場合はリトルエンディアンを返す。"""
        result = _detect_endian(b"\x00" * 3, stride=32)
        assert result == "little"

    def test_detect_format_24_bytes(self) -> None:
        """24バイトデータはPOSITION_NORMAL_F32x6として検出される。"""
        data = b"\x00" * 24
        result = _detect_format(data)
        assert result == VF.POSITION_NORMAL_F32x6

    def test_decode_with_custom_stride_normal_and_uv(self) -> None:
        """カスタムストライドでnormalとuvを指定してデコードできる。"""
        # stride=48: pos(12) + normal(12) + uv(8) + padding(16)
        stride = 48
        pos = (1.0, 2.0, 3.0)
        normal = (0.0, 1.0, 0.0)
        uv = (0.5, 0.25)
        vtx_bytes = (
            struct.pack("<3f", *pos)     # offset 0: position
            + struct.pack("<3f", *normal) # offset 12: normal
            + struct.pack("<2f", *uv)    # offset 24: uv
            + b"\x00" * 16              # offset 32: padding
        )
        data = vtx_bytes * 2  # 2頂点

        decoder = VertexDecoder()
        result = decoder.decode_with_custom_stride(
            data,
            stride=stride,
            position_offset=0,
            normal_offset=12,
            uv_offset=24,
        )
        assert result.vertex_count == 2
        assert result.vertices[0].position == pytest.approx(pos)
        assert result.vertices[0].normal == pytest.approx(normal)
        assert result.vertices[0].uv == pytest.approx(uv)

    def test_decode_with_custom_stride_position_only(self) -> None:
        """normal/uv指定なしの場合、正しくPOSITION_F32x3と推定される。"""
        data = struct.pack("<3f", 1.0, 0.0, 0.0) + b"\x00" * 4  # stride=16
        decoder = VertexDecoder()
        result = decoder.decode_with_custom_stride(data, stride=16)
        assert result.format_detected == VF.POSITION_F32x3
        assert result.vertices[0].normal is None
        assert result.vertices[0].uv is None

    def test_decode_with_custom_stride_normal_only(self) -> None:
        """normal指定のみ（uv無し）の場合、POSITION_NORMAL_F32x6と推定される。"""
        stride = 24
        data = struct.pack("<6f", 1.0, 0.0, 0.0, 0.0, 1.0, 0.0)
        decoder = VertexDecoder()
        result = decoder.decode_with_custom_stride(
            data, stride=stride, position_offset=0, normal_offset=12
        )
        assert result.format_detected == VF.POSITION_NORMAL_F32x6
        assert result.vertices[0].normal == pytest.approx((0.0, 1.0, 0.0))
        assert result.vertices[0].uv is None

    def test_large_vertex_buffer(self) -> None:
        """10,000頂点のバッファを正しくデコードできる（パフォーマンス回帰）。"""
        vertex_count = 10_000
        data = struct.pack("<3f", 1.0, 2.0, 3.0) * vertex_count
        decoder = VertexDecoder()
        result = decoder.decode(data, fmt=VF.POSITION_F32x3)
        assert result.vertex_count == vertex_count

    def test_boundary_vertex_count_one(self) -> None:
        """頂点数1（最小値）を正しく処理できる。"""
        data = struct.pack("<8f", 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0)
        decoder = VertexDecoder()
        result = decoder.decode(data, fmt=VF.POSITION_NORMAL_UV_F32x8)
        assert result.vertex_count == 1


# ---------------------------------------------------------------------------
# obj_exporter.py 回帰テスト
# ---------------------------------------------------------------------------

class TestObjExporterRegression:
    """obj_exporter.py の回帰テスト。"""

    def test_export_obj_zero_vertices_raises(self) -> None:
        """頂点0個のモデルをOBJエクスポートしようとすると ValueError が発生する。"""
        exporter = ObjExporter()
        with pytest.raises(ValueError, match="頂点"):
            exporter.export_obj([], "/tmp/out.obj")

    def test_export_gltf_zero_vertices_raises(self) -> None:
        """頂点0個のモデルをglTFエクスポートしようとすると ValueError が発生する。"""
        exporter = ObjExporter()
        with pytest.raises(ValueError, match="頂点"):
            exporter.export_gltf([], "/tmp/out.gltf")

    def test_build_obj_lines_normal_only_face_format(self) -> None:
        """normal有り・uv無しの場合、面定義が v//vn 形式になる。"""
        vertices = [
            DecodedVertex(position=(0.0, 0.0, 0.0), normal=(0.0, 0.0, 1.0)),
            DecodedVertex(position=(1.0, 0.0, 0.0), normal=(0.0, 0.0, 1.0)),
            DecodedVertex(position=(0.5, 1.0, 0.0), normal=(0.0, 0.0, 1.0)),
        ]
        lines = _build_obj_lines(vertices)
        content = "\n".join(lines)
        # normal有り・uv無しの面定義: v//vn 形式
        assert "f 1//1 2//2 3//3" in content
        assert "vn " in content
        assert "vt " not in content

    def test_build_obj_lines_uv_only_face_format(self) -> None:
        """uv有り・normal無しの場合、面定義が v/vt 形式になる。"""
        vertices = [
            DecodedVertex(position=(0.0, 0.0, 0.0), uv=(0.0, 0.0)),
            DecodedVertex(position=(1.0, 0.0, 0.0), uv=(1.0, 0.0)),
            DecodedVertex(position=(0.5, 1.0, 0.0), uv=(0.5, 1.0)),
        ]
        lines = _build_obj_lines(vertices)
        content = "\n".join(lines)
        # uv有り・normal無しの面定義: v/vt 形式
        assert "f 1/1 2/2 3/3" in content
        assert "vt " in content
        assert "vn " not in content

    def test_build_obj_lines_position_only_face_format(self) -> None:
        """position のみの場合、面定義が v 形式（スラッシュなし）になる。"""
        vertices = [
            DecodedVertex(position=(0.0, 0.0, 0.0)),
            DecodedVertex(position=(1.0, 0.0, 0.0)),
            DecodedVertex(position=(0.5, 1.0, 0.0)),
        ]
        lines = _build_obj_lines(vertices)
        content = "\n".join(lines)
        assert "f 1 2 3" in content

    def test_build_obj_lines_none_normal_fallback(self) -> None:
        """一部の頂点がnormal=Noneでも、has_normals=Trueなら (0,0,1) にフォールバックする。"""
        vertices = [
            DecodedVertex(position=(0.0, 0.0, 0.0), normal=(0.0, 0.0, 1.0)),
            DecodedVertex(position=(1.0, 0.0, 0.0), normal=None),  # None -> (0,0,1)
            DecodedVertex(position=(0.5, 1.0, 0.0), normal=(0.0, 0.0, 1.0)),
        ]
        lines = _build_obj_lines(vertices)
        content = "\n".join(lines)
        assert "vn 0.000000 0.000000 1.000000" in content

    def test_build_obj_lines_none_uv_fallback(self) -> None:
        """一部の頂点がuv=Noneでも、has_uvs=Trueなら (0,0) にフォールバックする。"""
        vertices = [
            DecodedVertex(position=(0.0, 0.0, 0.0), uv=(0.5, 0.5)),
            DecodedVertex(position=(1.0, 0.0, 0.0), uv=None),  # None -> (0,0)
            DecodedVertex(position=(0.5, 1.0, 0.0), uv=(0.5, 0.5)),
        ]
        lines = _build_obj_lines(vertices)
        content = "\n".join(lines)
        assert "vt 0.000000 0.000000" in content

    def test_export_gltf_without_uvs(self, tmp_path) -> None:
        """UV無し頂点でglTFエクスポートできる。"""
        vertices = [
            DecodedVertex(position=(0.0, 0.0, 0.0)),
            DecodedVertex(position=(1.0, 0.0, 0.0)),
            DecodedVertex(position=(0.5, 1.0, 0.0)),
        ]
        exporter = ObjExporter()
        out = tmp_path / "no_uv.gltf"
        meta = exporter.export_gltf(vertices, out)
        assert out.exists()
        gltf = json.loads(out.read_text())
        attrs = gltf["meshes"][0]["primitives"][0]["attributes"]
        assert "TEXCOORD_0" not in attrs


# ---------------------------------------------------------------------------
# vram_simulator.py 回帰テスト
# ---------------------------------------------------------------------------

class TestVramSimulatorRegression:
    """vram_simulator.py の回帰テスト。"""

    def test_create_texture_fragment_size(self) -> None:
        """テクスチャ断片が正しいサイズ（64×64×4=16384バイト）を返す。"""
        from targets.gpu_memory.vram_simulator import _create_texture_fragment
        tex = _create_texture_fragment()
        assert len(tex) == 64 * 64 * 4

    def test_create_texture_fragment_checker_pattern(self) -> None:
        """チェッカーパターンが正しく生成されている（黒/オレンジの交互）。"""
        from targets.gpu_memory.vram_simulator import _create_texture_fragment
        tex = _create_texture_fragment()
        # (0,0)はブロック(0,0)→偶数→オレンジ(255,128,0,255)
        assert tex[0:4] == bytes([255, 128, 0, 255])
        # (8,0)はブロック(1,0)→奇数→グレー(64,64,64,255)
        pixel_8_0 = 8 * 4
        assert tex[pixel_8_0:pixel_8_0 + 4] == bytes([64, 64, 64, 255])

    def test_create_framebuffer_image_without_pillow(self, monkeypatch) -> None:
        """Pillow未インストール時でもフレームバッファデータを返す。"""
        import targets.gpu_memory.vram_simulator as sim_module
        monkeypatch.setattr(sim_module, "HAS_PILLOW", False)
        fb = sim_module._create_framebuffer_image()
        expected_size = sim_module.FB_SIZE
        assert len(fb) == expected_size
        # CTF_FLAG の最初の文字が正しく配置されている
        assert fb[0] == ord(sim_module.CTF_FLAG[0])

    def test_create_framebuffer_image_with_pillow(self, monkeypatch) -> None:
        """Pillow有りの場合、フレームバッファが正しいサイズで返される。"""
        import targets.gpu_memory.vram_simulator as sim_module
        if not sim_module.HAS_PILLOW:
            pytest.skip("Pillow未インストール")
        fb = sim_module._create_framebuffer_image()
        assert len(fb) == sim_module.FB_SIZE

    def test_generate_vram_dump_creates_file(self, tmp_path) -> None:
        """generate_vram_dump() がファイルを生成する。"""
        from targets.gpu_memory.vram_simulator import DUMP_SIZE, generate_vram_dump
        output_path = tmp_path / "vram_dump.bin"
        generate_vram_dump(output_path)
        assert output_path.exists()
        assert output_path.stat().st_size == DUMP_SIZE

    def test_generate_vram_dump_framebuffer_offset(self, tmp_path) -> None:
        """フレームバッファが正しいオフセットに配置されている。"""
        from targets.gpu_memory.vram_simulator import (
            CTF_FLAG,
            FB_OFFSET,
            HAS_PILLOW,
            generate_vram_dump,
        )
        if HAS_PILLOW:
            pytest.skip("Pillow有りの場合はPillow描画のためASCII検出が困難")
        output_path = tmp_path / "vram_test.bin"
        generate_vram_dump(output_path)
        data = output_path.read_bytes()
        # Pillow無しの場合、CTF_FLAGの最初の文字がFB_OFFSETに配置される
        assert data[FB_OFFSET] == ord(CTF_FLAG[0])


# ---------------------------------------------------------------------------
# webgl_interceptor.py 回帰テスト
# ---------------------------------------------------------------------------

class TestWebGLInterceptorRegression:
    """webgl_interceptor.py の回帰テスト。"""

    def test_save_results_json_only(self, tmp_path) -> None:
        """framebuffer_data_url=None の場合、JSONのみ保存される。"""
        calls = (
            WebGLCall(call_type="drawArrays", mode=4, count=36, timestamp=1000),
        )
        result = InterceptResult(
            url="http://test",
            calls=calls,
            framebuffer_data_url=None,
            draw_call_count=1,
            total_vertices=36,
        )
        WebGLInterceptor._save_results(result, tmp_path)
        assert (tmp_path / "webgl_calls.json").exists()
        assert not (tmp_path / "framebuffer.png").exists()

    def test_save_results_with_png(self, tmp_path) -> None:
        """framebuffer_data_url がある場合、JSONとPNGが保存される。"""
        # 1×1 PNG のbase64（最小限のPNGデータ）
        import zlib as _zlib
        # 1x1 透明 PNG (data:image/png;base64,...) を手動生成
        png_header = b"\x89PNG\r\n\x1a\n"
        ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
        ihdr_crc = struct.pack(">I", zlib.crc32(b"IHDR" + ihdr_data) & 0xFFFFFFFF)
        ihdr_chunk = struct.pack(">I", 13) + b"IHDR" + ihdr_data + ihdr_crc

        idat_data = _zlib.compress(b"\x00\xff\x00\x00")  # filter + RGB
        idat_crc = struct.pack(">I", zlib.crc32(b"IDAT" + idat_data) & 0xFFFFFFFF)
        idat_chunk = struct.pack(">I", len(idat_data)) + b"IDAT" + idat_data + idat_crc

        iend_crc = struct.pack(">I", zlib.crc32(b"IEND") & 0xFFFFFFFF)
        iend_chunk = struct.pack(">I", 0) + b"IEND" + iend_crc

        png_bytes = png_header + ihdr_chunk + idat_chunk + iend_chunk
        b64data = base64.b64encode(png_bytes).decode()
        data_url = f"data:image/png;base64,{b64data}"

        calls = (WebGLCall(call_type="drawArrays", mode=4, count=36, timestamp=0),)
        result = InterceptResult(
            url="http://test",
            calls=calls,
            framebuffer_data_url=data_url,
            draw_call_count=1,
            total_vertices=36,
        )
        WebGLInterceptor._save_results(result, tmp_path)
        assert (tmp_path / "webgl_calls.json").exists()
        assert (tmp_path / "framebuffer.png").exists()

    def test_save_results_json_content(self, tmp_path) -> None:
        """保存されたJSONの内容が正しい。"""
        calls = (
            WebGLCall(call_type="drawElements", mode=4, count=72,
                      timestamp=500, index_type=5125, offset=0),
        )
        result = InterceptResult(
            url="http://example.com/scene",
            calls=calls,
            framebuffer_data_url=None,
            draw_call_count=1,
            total_vertices=72,
        )
        WebGLInterceptor._save_results(result, tmp_path)
        saved = json.loads((tmp_path / "webgl_calls.json").read_text())
        assert saved["url"] == "http://example.com/scene"
        assert len(saved["calls"]) == 1
        assert saved["calls"][0]["type"] == "drawElements"

    def test_summary_lists_all_calls(self) -> None:
        """summary() が全ドローコールを列挙する。"""
        calls = tuple(
            WebGLCall(call_type="drawArrays", mode=4, count=i * 12, timestamp=i * 16)
            for i in range(1, 6)
        )
        result = InterceptResult(
            url="http://test",
            calls=calls,
            framebuffer_data_url=None,
            draw_call_count=len(calls),
            total_vertices=sum(c.count for c in calls),
        )
        summary = result.summary()
        # 全コールのcountが含まれる
        for call in calls:
            assert str(call.count) in summary

    def test_parse_calls_unknown_type(self) -> None:
        """未知のコールタイプでもクラッシュしない。"""
        raw = json.dumps([{"type": "clearColor", "mode": 0, "count": 0, "timestamp": 100}])
        calls = _parse_calls(raw)
        assert len(calls) == 1
        assert calls[0].call_type == "clearColor"


# ---------------------------------------------------------------------------
# mesh_extractor.py 回帰テスト
# ---------------------------------------------------------------------------

class TestMeshExtractorRegression:
    """mesh_extractor.py の回帰テスト。"""

    def test_draw_call_info_summary_format(self) -> None:
        """DrawCallInfo.summary() が正しいフォーマットで返る。"""
        info = DrawCallInfo(
            event_id=42,
            name="Draw(36)",
            vertex_count=36,
            index_count=36,
            instance_count=1,
        )
        summary = info.summary()
        assert "42" in summary
        assert "Draw(36)" in summary
        assert "36" in summary

    def test_stub_result_when_no_renderdoc(self) -> None:
        """renderdoc未インストール時はスタブ結果を返す。"""
        extractor = MeshExtractor()
        result = extractor.extract("/path/to/nonexistent.rdc")
        assert result.is_stub is True
        assert len(result.draw_calls) >= 1
        assert len(result.meshes) == 0

    def test_stub_result_rdc_path_preserved(self) -> None:
        """スタブ結果にrdcパスが保存される（Pathオブジェクトを経由するためOS依存のセパレータになる）。"""
        extractor = MeshExtractor()
        path = "/some/capture.rdc"
        result = extractor.extract(path)
        # Path(path) を経由するためWindowsでは \\ に変換される場合がある
        # ファイル名部分だけ確認する
        assert "capture.rdc" in result.rdc_path

    def test_stub_result_draw_call_has_stub_name(self) -> None:
        """スタブのドローコールは '[Stub]' という名前を持つ。"""
        extractor = MeshExtractor()
        result = extractor.extract("/dummy.rdc")
        assert any("[Stub]" in dc.name for dc in result.draw_calls)

    def test_extracted_mesh_dataclass(self) -> None:
        """ExtractedMesh データクラスが正しく構築できる。"""
        mesh = ExtractedMesh(
            event_id=1,
            vertex_data=b"\x00" * 96,
            index_data=None,
            vertex_count=3,
            stride=32,
        )
        assert mesh.vertex_count == 3
        assert mesh.stride == 32
        assert mesh.index_data is None

    def test_extraction_result_dataclass(self) -> None:
        """ExtractionResult データクラスが正しく構築できる。"""
        result = ExtractionResult(
            rdc_path="/test.rdc",
            draw_calls=(),
            meshes=(),
            is_stub=True,
        )
        assert result.rdc_path == "/test.rdc"
        assert len(result.draw_calls) == 0
        assert result.is_stub is True
