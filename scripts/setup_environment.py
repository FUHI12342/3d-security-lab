"""
scripts/setup_environment.py

環境セットアップスクリプト。
必要なツール・ライブラリのインストール状況を確認する。
"""

from __future__ import annotations

import importlib
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CheckResult:
    """チェック結果を表す不変データクラス。"""
    name: str
    available: bool
    version: Optional[str]
    note: str = ""


def _check_python_module(module_name: str, display_name: str, note: str = "") -> CheckResult:
    """Pythonモジュールのインストール確認。"""
    try:
        mod = importlib.import_module(module_name)
        version = getattr(mod, "__version__", "installed")
        return CheckResult(name=display_name, available=True, version=version, note=note)
    except ImportError:
        return CheckResult(name=display_name, available=False, version=None, note=note)


def _check_command(cmd: str, display_name: str, note: str = "") -> CheckResult:
    """外部コマンドの存在確認。"""
    path = shutil.which(cmd)
    if path:
        try:
            result = subprocess.run(
                [cmd, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            version_line = (result.stdout + result.stderr).splitlines()[0][:60]
            return CheckResult(name=display_name, available=True, version=version_line, note=note)
        except (subprocess.TimeoutExpired, IndexError, OSError):
            return CheckResult(name=display_name, available=True, version="(バージョン不明)", note=note)
    return CheckResult(name=display_name, available=False, version=None, note=note)


def run_checks() -> list[CheckResult]:
    """全チェックを実行してリストを返す。"""
    checks: list[CheckResult] = []

    print("=" * 60)
    print("3D Security Lab — 環境チェック")
    print("=" * 60)

    # Python バージョン
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    py_ok = sys.version_info >= (3, 10)
    checks.append(CheckResult(
        name="Python 3.10+",
        available=py_ok,
        version=py_ver,
        note="必須",
    ))

    # 必須Pythonパッケージ
    required_modules = [
        ("numpy", "NumPy", "必須"),
        ("PIL", "Pillow", "必須（VRAMフォレンジクス用）"),
        ("matplotlib", "Matplotlib", "推奨（S3Dビューア可視化）"),
        ("pytest", "pytest", "必須（テスト実行）"),
    ]
    for module, name, note in required_modules:
        checks.append(_check_python_module(module, name, note))

    # オプションPythonパッケージ
    optional_modules = [
        ("playwright", "Playwright", "オプション（WebGLインターセプト）"),
        ("moderngl", "moderngl", "オプション（DX11ビューア）"),
        ("pygame", "pygame", "オプション（DX11ビューア）"),
    ]
    for module, name, note in optional_modules:
        checks.append(_check_python_module(module, name, note))

    # 外部ツール
    external_tools = [
        ("renderdoccmd", "RenderDoc", "オプション（Lab 1）"),
        ("apitrace", "apitrace", "オプション（Lab 2）"),
        ("git", "git", "推奨"),
    ]
    for cmd, name, note in external_tools:
        checks.append(_check_command(cmd, name, note))

    return checks


def print_results(checks: list[CheckResult]) -> None:
    """チェック結果を表示する。"""
    ok_count = sum(1 for c in checks if c.available)
    total = len(checks)

    for check in checks:
        status = "OK" if check.available else "NG"
        symbol = "[OK]" if check.available else "[--]"
        version_str = f" ({check.version})" if check.version else ""
        note_str = f"  # {check.note}" if check.note else ""
        print(f"  {symbol} {check.name}{version_str}{note_str}")

    print()
    print(f"結果: {ok_count}/{total} チェック通過")

    if ok_count == total:
        print("全チェック通過！演習を開始できます。")
    else:
        failed = [c for c in checks if not c.available]
        print("以下をインストールしてください:")
        for c in failed:
            if c.note and "必須" in c.note:
                print(f"  pip install {c.name.lower()}")


if __name__ == "__main__":
    results = run_checks()
    print()
    print_results(results)
