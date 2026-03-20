# テスト一覧

## テスト実行方法

```bash
pytest tests/ -v
pytest tests/ -v --cov=tools --cov=targets --cov-report=html
```

---

## test_format_analyzer.py (12テスト)

| テスト名 | 検証内容 |
|---------|---------|
| `TestComputeEntropy::test_empty_data_returns_zero` | 空データはエントロピー0 |
| `TestComputeEntropy::test_uniform_data_max_entropy` | 均一分布は最大エントロピー |
| `TestComputeEntropy::test_constant_data_zero_entropy` | 単一バイトはエントロピー0 |
| `TestComputeEntropy::test_two_values_entropy` | 2値均等混在はエントロピー1.0 |
| `TestComputeEntropy::test_compressed_data_high_entropy` | 圧縮データは高エントロピー |
| `TestComputeEntropy::test_plain_text_low_entropy` | テキストは低エントロピー |
| `TestFormatAnalyzer::test_detect_s3d_magic` | S3Dマジックバイト検出 |
| `TestFormatAnalyzer::test_detect_png_magic` | PNGマジックバイト検出 |
| `TestFormatAnalyzer::test_detect_zlib_magic` | zlibマジックバイト検出 |
| `TestFormatAnalyzer::test_unknown_format_returns_none` | 不明フォーマットはNone |
| `TestFormatAnalyzer::test_file_size_correct` | ファイルサイズ正確 |
| `TestFormatAnalyzer::test_entropy_classification_for_random` | ランダムデータの分類 |
| `TestFormatAnalyzer::test_alignment_guess_for_s3d` | S3Dアライメント推定 |
| `TestFormatAnalyzer::test_hexdump_format` | hexdump形式 |
| `TestFormatAnalyzer::test_hexdump_nonprintable_as_dot` | 非印字文字はドット |
| `TestFormatAnalyzer::test_summary_contains_key_info` | summary()のキー情報 |
| `TestFormatAnalyzer::test_analyze_file` | 実ファイル解析 |

---

## test_vertex_decoder.py (15テスト)

| テスト名 | 検証内容 |
|---------|---------|
| `TestVertexFormat::test_p3_stride` | Position only ストライド = 12 |
| `TestVertexFormat::test_p3n3_stride` | Position+Normal ストライド = 24 |
| `TestVertexFormat::test_p3n3u2_stride` | Position+Normal+UV ストライド = 32 |
| `TestVertexFormat::test_p3n3u2c4_stride` | 全フィールド ストライド = 48 |
| `TestVertexFormat::test_float_count` | float_count が正しい |
| `TestDecodedVertex::test_to_dict_position_only` | position only の辞書変換 |
| `TestDecodedVertex::test_to_dict_full` | 全フィールドの辞書変換 |
| `TestDecodedVertex::test_immutable` | 不変性の確認 |
| `TestVertexDecoder::test_decode_p3_format` | Position only デコード |
| `TestVertexDecoder::test_decode_p3n3u2_format` | 32バイトフォーマットデコード |
| `TestVertexDecoder::test_auto_detect_format` | フォーマット自動検出 |
| `TestVertexDecoder::test_empty_data_raises` | 空データのエラー |
| `TestVertexDecoder::test_too_short_data_raises` | 短すぎるデータのエラー |
| `TestVertexDecoder::test_decode_with_offset` | オフセット指定デコード |
| `TestVertexDecoder::test_decode_with_custom_stride` | カスタムストライドデコード |
| `TestVertexDecoder::test_invalid_stride_raises` | 不正ストライドのエラー |
| `TestVertexDecoder::test_summary_contains_info` | summary()の内容 |
| `TestVertexDecoder::test_p3n3u2c4_format` | 48バイトフォーマット |

---

## test_vram_forensics.py (12テスト)

| テスト名 | 検証内容 |
|---------|---------|
| `TestComputeRgbaConfidence::test_fully_opaque_rgba_high_confidence` | 不透明RGBAの高confidence |
| `TestComputeRgbaConfidence::test_too_short_data_returns_zero` | 短すぎるデータは0 |
| `TestComputeRgbaConfidence::test_uniform_color_has_low_confidence` | 単色の低confidence |
| `TestScanImageHeaders::test_detect_png_header` | PNGヘッダー検出 |
| `TestScanImageHeaders::test_detect_multiple_headers` | 複数ヘッダー検出 |
| `TestScanImageHeaders::test_no_headers_returns_empty` | ヘッダーなしは空リスト |
| `TestVramForensics::test_scan_image_headers_from_bytes` | バイト列からスキャン |
| `TestVramForensics::test_scan_framebuffers_detects_candidate` | フレームバッファ候補検出 |
| `TestVramForensics::test_reconstruct_framebuffer_raises_on_short_data` | 短データのエラー |
| `TestVramForensics::test_reconstruct_framebuffer_without_pillow` | Pillow未インストール時 |
| `TestVramForensics::test_candidate_summary` | FramebufferCandidate.summary() |

---

## test_obj_exporter.py (15テスト)

| テスト名 | 検証内容 |
|---------|---------|
| `TestBuildObjLines::test_contains_vertex_positions` | OBJに頂点座標が含まれる |
| `TestBuildObjLines::test_contains_normals_when_present` | 法線がある場合vn行あり |
| `TestBuildObjLines::test_contains_uvs_when_present` | UVがある場合vt行あり |
| `TestBuildObjLines::test_no_normals_when_absent` | 法線なし時vn行なし |
| `TestBuildObjLines::test_object_name` | オブジェクト名が含まれる |
| `TestBuildObjLines::test_face_definition` | 面定義が含まれる |
| `TestBuildGltf::test_gltf_version` | glTFバージョン2.0 |
| `TestBuildGltf::test_buffer_size_correct` | バッファサイズ正確 |
| `TestBuildGltf::test_accessor_count` | アクセッサ頂点数 |
| `TestBuildGltf::test_min_max_positions` | min/max設定 |
| `TestObjExporter::test_export_obj_creates_file` | OBJファイル作成 |
| `TestObjExporter::test_export_obj_content_valid` | OBJ内容の妥当性 |
| `TestObjExporter::test_export_gltf_creates_files` | glTFファイル作成 |
| `TestObjExporter::test_export_gltf_valid_json` | glTFのJSON妥当性 |
| `TestObjExporter::test_export_creates_parent_dirs` | 親ディレクトリ作成 |

---

## test_encoder.py (22テスト)

| テスト名 | 検証内容 |
|---------|---------|
| `TestVertex::test_to_bytes_length` | Vertex.to_bytes()が32バイト |
| `TestVertex::test_roundtrip` | to_bytes()→from_bytes()往復 |
| `TestVertex::test_immutable` | Vertexの不変性 |
| `TestXorKey::test_xor_key_deterministic` | XORキーの決定論性 |
| `TestXorKey::test_different_versions_different_keys` | バージョン別キー |
| `TestXorData::test_xor_invertible` | XORの可逆性 |
| `TestXorData::test_xor_changes_data` | XORでデータが変化 |
| `TestEncodeDecode::test_plain_roundtrip` | 平文往復 |
| `TestEncodeDecode::test_xor_roundtrip` | XOR往復 |
| `TestEncodeDecode::test_zlib_roundtrip` | zlib往復 |
| `TestEncodeDecode::test_checksum_roundtrip` | チェックサム往復 |
| `TestEncodeDecode::test_full_flags_roundtrip` | 全フラグ往復 |
| `TestEncodeDecode::test_magic_bytes_correct` | マジックバイト確認 |
| `TestEncodeDecode::test_vertex_count_in_header` | ヘッダー頂点数 |
| `TestEncodeDecode::test_invalid_magic_raises` | 不正マジックのエラー |
| `TestEncodeDecode::test_short_data_raises` | 短データのエラー |
| `TestEncodeDecode::test_checksum_mismatch_raises` | チェックサム不一致のエラー |
| `TestEncodeDecode::test_cube_model_vertex_count` | キューブの頂点数=24 |
| `TestGenerateSamples::test_generates_three_files` | 3ファイル生成 |
| `TestGenerateSamples::test_easy_is_plain` | easy.s3dは平文 |
| `TestGenerateSamples::test_medium_has_xor` | medium.s3dはXOR |
| `TestGenerateSamples::test_all_files_decodable` | 全ファイルデコード可能 |

---

## test_ctf_verify.py (16テスト)

| テスト名 | 検証内容 |
|---------|---------|
| `TestChallenge01Verify::test_correct_flag` | Challenge 01 正答 |
| `TestChallenge01Verify::test_wrong_flag` | Challenge 01 誤答 |
| `TestChallenge01Verify::test_empty_string` | 空文字列は False |
| `TestChallenge01Verify::test_case_sensitive` | 大文字小文字区別 |
| `TestChallenge01Verify::test_whitespace_stripped` | 空白トリム |
| `TestChallenge02Verify::test_correct_flag` | Challenge 02 正答 |
| `TestChallenge02Verify::test_wrong_coordinate` | Challenge 02 誤答 |
| `TestChallenge03Verify::test_correct_flag` | Challenge 03 正答 |
| `TestChallenge03Verify::test_wrong_text` | Challenge 03 誤答 |
| `TestChallenge04Verify::test_correct_flag` | Challenge 04 正答 |
| `TestChallenge04Verify::test_wrong_secret` | Challenge 04 誤答 |
| `TestChallenge04Verify::test_whitespace_stripped` | 空白トリム |

---

## test_webgl_interceptor.py (15テスト)

| テスト名 | 検証内容 |
|---------|---------|
| `TestWebGLCall::test_default_values` | デフォルト値確認 |
| `TestWebGLCall::test_immutable` | 不変性確認 |
| `TestParseCallsJson::test_parse_draw_arrays` | drawArraysパース |
| `TestParseCallsJson::test_parse_draw_elements` | drawElementsパース |
| `TestParseCallsJson::test_parse_multiple_calls` | 複数コールパース |
| `TestParseCallsJson::test_parse_empty_array` | 空配列パース |
| `TestParseCallsJson::test_parse_invalid_json_returns_empty` | 不正JSON処理 |
| `TestInterceptResult::test_summary_contains_url` | summary()のURL |
| `TestInterceptResult::test_summary_contains_draw_calls` | summary()のドローコール |
| `TestMockWebGLInterceptor::test_capture_returns_result` | モックキャプチャ結果 |
| `TestMockWebGLInterceptor::test_capture_has_draw_calls` | モックのドローコール数 |
| `TestMockWebGLInterceptor::test_capture_correct_vertex_counts` | モックの頂点数 |
| `TestWebGLInterceptorWithoutPlaywright::test_capture_without_playwright_returns_none` | Playwright未インストール |

---

## カバレッジ目標

- 全体: 80% 以上
- `tools/`: 90% 以上
- `targets/custom_format/encoder.py`: 95% 以上
