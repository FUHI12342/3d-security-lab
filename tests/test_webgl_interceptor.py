"""
tests/test_webgl_interceptor.py

WebGLInterceptor のユニットテスト。
MockWebGLInterceptor を使ってPlaywright不要でテストする。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.webgl_interceptor import (
    InterceptResult,
    MockWebGLInterceptor,
    WebGLCall,
    WebGLInterceptor,
    _parse_calls,
)


class TestWebGLCall:
    """WebGLCall データクラスのテスト。"""

    def test_default_values(self) -> None:
        """デフォルト値が正しく設定される。"""
        call = WebGLCall(call_type="drawArrays", mode=4, count=36, timestamp=1000)
        assert call.first == 0
        assert call.index_type is None
        assert call.offset == 0

    def test_immutable(self) -> None:
        """WebGLCall は不変（frozen dataclass）。"""
        call = WebGLCall(call_type="drawArrays", mode=4, count=36, timestamp=1000)
        with pytest.raises(Exception):
            call.count = 0  # type: ignore[misc]


class TestParseCallsJson:
    """_parse_calls() のテスト。"""

    def test_parse_draw_arrays(self) -> None:
        """drawArrays コールをパースできる。"""
        raw = json.dumps([
            {"type": "drawArrays", "mode": 4, "count": 36, "first": 0, "timestamp": 1000}
        ])
        calls = _parse_calls(raw)
        assert len(calls) == 1
        assert calls[0].call_type == "drawArrays"
        assert calls[0].count == 36

    def test_parse_draw_elements(self) -> None:
        """drawElements コールをパースできる。"""
        raw = json.dumps([
            {"type": "drawElements", "mode": 4, "count": 36, "indexType": 5125, "offset": 0, "timestamp": 1000}
        ])
        calls = _parse_calls(raw)
        assert len(calls) == 1
        assert calls[0].call_type == "drawElements"
        assert calls[0].index_type == 5125

    def test_parse_multiple_calls(self) -> None:
        """複数コールをパースできる。"""
        raw = json.dumps([
            {"type": "drawArrays", "mode": 4, "count": 36, "timestamp": 1000},
            {"type": "drawArrays", "mode": 4, "count": 72, "timestamp": 1016},
        ])
        calls = _parse_calls(raw)
        assert len(calls) == 2
        assert calls[1].count == 72

    def test_parse_empty_array(self) -> None:
        """空配列はエラーなく処理できる。"""
        calls = _parse_calls("[]")
        assert len(calls) == 0

    def test_parse_invalid_json_returns_empty(self) -> None:
        """不正JSON は空タプルを返す。"""
        calls = _parse_calls("not json")
        assert len(calls) == 0

    def test_parse_none_returns_empty(self) -> None:
        """None は空タプルを返す。"""
        calls = _parse_calls(None)  # type: ignore[arg-type]
        assert len(calls) == 0


class TestInterceptResult:
    """InterceptResult データクラスのテスト。"""

    def test_summary_contains_url(self) -> None:
        """summary() が URL を含む。"""
        result = InterceptResult(
            url="http://localhost:8080/test",
            calls=(WebGLCall(call_type="drawArrays", mode=4, count=36, timestamp=0),),
            framebuffer_data_url=None,
            draw_call_count=1,
            total_vertices=36,
        )
        summary = result.summary()
        assert "http://localhost:8080/test" in summary
        assert "1" in summary

    def test_summary_contains_draw_calls(self) -> None:
        """summary() がドローコール情報を含む。"""
        calls = (
            WebGLCall(call_type="drawArrays", mode=4, count=36, timestamp=0),
            WebGLCall(call_type="drawArrays", mode=4, count=72, timestamp=16),
        )
        result = InterceptResult(
            url="http://test",
            calls=calls,
            framebuffer_data_url=None,
            draw_call_count=2,
            total_vertices=108,
        )
        summary = result.summary()
        assert "2" in summary
        assert "36" in summary


class TestMockWebGLInterceptor:
    """MockWebGLInterceptor のテスト。"""

    def setup_method(self) -> None:
        self.interceptor = MockWebGLInterceptor()

    def test_capture_returns_result(self) -> None:
        """capture() が InterceptResult を返す。"""
        result = self.interceptor.capture("http://localhost:8080/test")
        assert isinstance(result, InterceptResult)

    def test_capture_has_draw_calls(self) -> None:
        """モックが2つのドローコールを返す。"""
        result = self.interceptor.capture("http://test")
        assert result.draw_call_count == 2

    def test_capture_correct_vertex_counts(self) -> None:
        """モックが正しい頂点数を返す（36 + 72 = 108）。"""
        result = self.interceptor.capture("http://test")
        assert result.total_vertices == 108

    def test_capture_url_preserved(self) -> None:
        """指定したURLが結果に保持される。"""
        url = "http://localhost:8080/scene"
        result = self.interceptor.capture(url)
        assert result.url == url

    def test_capture_saves_to_output_dir(self, tmp_path) -> None:
        """output_dir を指定しても Mock では保存処理はスキップ（エラーなし）。"""
        # MockはPlaywright不使用なのでファイル保存は行わない
        result = self.interceptor.capture("http://test", output_dir=tmp_path)
        assert result is not None


class TestWebGLInterceptorWithoutPlaywright:
    """Playwright 未インストール時の WebGLInterceptor のテスト。"""

    def test_capture_without_playwright_returns_none(self, monkeypatch) -> None:
        """Playwright 未インストール時は None を返す。"""
        import tools.webgl_interceptor as wgi_module
        monkeypatch.setattr(wgi_module, "HAS_PLAYWRIGHT", False)

        interceptor = wgi_module.WebGLInterceptor()
        result = interceptor.capture("http://localhost:8080/test")
        assert result is None
