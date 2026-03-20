"""
tools/webgl_interceptor.py

Playwright を使った WebGL コマンドインターセプター。

機能:
- JavaScript注入でWebGLコールをフック
- drawArrays / drawElements の引数キャプチャ
- テクスチャの readPixels
- 結果を JSON + PNG で保存

注意: Playwright が未インストールの場合はスキップ（テスト互換）
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Playwright を遅延インポート（未インストール時でもモジュールロード可能）
try:
    from playwright.sync_api import Page, sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False


# WebGLコールをインターセプトするJavaScriptコード
_INTERCEPT_JS = """
(() => {
  if (window.__webgl_intercepted) return;
  window.__webgl_intercepted = true;
  window.__webgl_calls = [];

  const canvas = document.querySelector('canvas');
  if (!canvas) return;

  const gl = canvas.getContext('webgl') || canvas.getContext('webgl2');
  if (!gl) return;

  const originalDrawArrays = gl.drawArrays.bind(gl);
  gl.drawArrays = function(mode, first, count) {
    window.__webgl_calls.push({
      type: 'drawArrays',
      mode: mode,
      first: first,
      count: count,
      timestamp: Date.now()
    });
    return originalDrawArrays(mode, first, count);
  };

  const originalDrawElements = gl.drawElements.bind(gl);
  gl.drawElements = function(mode, count, type, offset) {
    window.__webgl_calls.push({
      type: 'drawElements',
      mode: mode,
      count: count,
      indexType: type,
      offset: offset,
      timestamp: Date.now()
    });
    return originalDrawElements(mode, count, type, offset);
  };

  console.log('[WebGL Interceptor] Hooked drawArrays and drawElements');
})();
"""

# キャプチャしたデータを取得するJavaScript
_COLLECT_JS = """
(() => {
  return JSON.stringify(window.__webgl_calls || []);
})();
"""

# フレームバッファをキャプチャするJavaScript
_CAPTURE_FRAMEBUFFER_JS = """
(() => {
  const canvas = document.querySelector('canvas');
  if (!canvas) return null;
  return canvas.toDataURL('image/png');
})();
"""


@dataclass(frozen=True)
class WebGLCall:
    """キャプチャした WebGL コールを表す不変データクラス。"""
    call_type: str
    mode: int
    count: int
    timestamp: int
    first: int = 0
    index_type: Optional[int] = None
    offset: int = 0


@dataclass(frozen=True)
class InterceptResult:
    """インターセプト結果を表す不変データクラス。"""
    url: str
    calls: tuple[WebGLCall, ...]
    framebuffer_data_url: Optional[str]
    draw_call_count: int
    total_vertices: int

    def summary(self) -> str:
        """サマリーを返す。"""
        lines = [
            f"URL: {self.url}",
            f"ドローコール数: {self.draw_call_count}",
            f"合計頂点/インデックス数: {self.total_vertices}",
        ]
        for i, call in enumerate(self.calls):
            lines.append(f"  [{i:2d}] {call.call_type}: count={call.count}, mode={call.mode}")
        return "\n".join(lines)


def _parse_calls(raw_json: str) -> tuple[WebGLCall, ...]:
    """JSON文字列をWebGLCallのタプルにパースする。"""
    try:
        items = json.loads(raw_json)
    except (json.JSONDecodeError, TypeError):
        return ()

    calls: list[WebGLCall] = []
    for item in items:
        calls.append(WebGLCall(
            call_type=item.get("type", "unknown"),
            mode=item.get("mode", 0),
            count=item.get("count", 0),
            timestamp=item.get("timestamp", 0),
            first=item.get("first", 0),
            index_type=item.get("indexType"),
            offset=item.get("offset", 0),
        ))
    return tuple(calls)


class WebGLInterceptor:
    """Playwright を使った WebGL インターセプタークラス。"""

    def capture(
        self,
        url: str,
        wait_ms: int = 2000,
        output_dir: Optional[str | Path] = None,
    ) -> Optional[InterceptResult]:
        """
        指定URLのWebGLシーンをキャプチャする。

        Args:
            url: 対象URL（http://... または file://...）
            wait_ms: ページロード後の待機時間（ミリ秒）
            output_dir: 出力ディレクトリ（None の場合は保存しない）

        Returns:
            InterceptResult（Playwright未インストール時は None）
        """
        if not HAS_PLAYWRIGHT:
            print("[WebGLInterceptor] Playwright が未インストールのためスキップします")
            print("  インストール: pip install playwright && playwright install chromium")
            return None

        return self._do_capture(url, wait_ms, output_dir)

    def _do_capture(
        self,
        url: str,
        wait_ms: int,
        output_dir: Optional[str | Path],
    ) -> InterceptResult:
        """実際のキャプチャ処理（Playwright必須）。"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # インターセプトスクリプトをページロード前に注入
            page.add_init_script(_INTERCEPT_JS)
            page.goto(url, wait_until="networkidle")
            page.wait_for_timeout(wait_ms)

            # コールを収集
            raw_json = page.evaluate(_COLLECT_JS)
            calls = _parse_calls(raw_json or "[]")

            # フレームバッファをキャプチャ
            fb_data_url: Optional[str] = page.evaluate(_CAPTURE_FRAMEBUFFER_JS)

            browser.close()

        # 統計
        total_vertices = sum(c.count for c in calls)

        result = InterceptResult(
            url=url,
            calls=calls,
            framebuffer_data_url=fb_data_url,
            draw_call_count=len(calls),
            total_vertices=total_vertices,
        )

        # 出力保存
        if output_dir is not None:
            self._save_results(result, Path(output_dir))

        return result

    @staticmethod
    def _save_results(result: InterceptResult, output_dir: Path) -> None:
        """解析結果をJSONとPNGで保存する。"""
        output_dir.mkdir(parents=True, exist_ok=True)

        # JSON保存
        calls_data = [
            {
                "type": c.call_type,
                "mode": c.mode,
                "count": c.count,
                "first": c.first,
                "index_type": c.index_type,
                "offset": c.offset,
            }
            for c in result.calls
        ]
        json_path = output_dir / "webgl_calls.json"
        json_path.write_text(
            json.dumps({"url": result.url, "calls": calls_data}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"WebGLコール保存: {json_path}")

        # PNG保存
        if result.framebuffer_data_url:
            import base64
            header, b64data = result.framebuffer_data_url.split(",", 1)
            png_bytes = base64.b64decode(b64data)
            png_path = output_dir / "framebuffer.png"
            png_path.write_bytes(png_bytes)
            print(f"フレームバッファ保存: {png_path}")


class MockWebGLInterceptor:
    """
    テスト用モックインターセプター（Playwright不要）。
    単体テストで使用する。
    """

    def capture(
        self,
        url: str,
        wait_ms: int = 0,
        output_dir: Optional[str | Path] = None,
    ) -> InterceptResult:
        """モックキャプチャを返す。"""
        mock_calls = (
            WebGLCall(call_type="drawArrays", mode=4, count=36, timestamp=1000),
            WebGLCall(call_type="drawArrays", mode=4, count=72, timestamp=1016),
        )
        return InterceptResult(
            url=url,
            calls=mock_calls,
            framebuffer_data_url=None,
            draw_call_count=len(mock_calls),
            total_vertices=sum(c.count for c in mock_calls),
        )
