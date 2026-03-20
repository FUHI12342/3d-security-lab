"""
scripts/create_shortcut.py

デスクトップショートカット作成スクリプト（Windows/macOS/Linux対応）。
"""

from __future__ import annotations

import os
import platform
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def create_windows_shortcut() -> None:
    """Windows 用 .bat ショートカットを作成する。"""
    desktop = Path.home() / "Desktop"
    shortcut_path = desktop / "3D Security Lab.bat"

    content = f"""@echo off
cd /d "{PROJECT_ROOT}"
python scripts/setup_environment.py
pause
"""
    shortcut_path.write_text(content, encoding="utf-8")
    print(f"Windowsショートカット作成: {shortcut_path}")


def create_macos_shortcut() -> None:
    """macOS 用 .command ファイルを作成する。"""
    desktop = Path.home() / "Desktop"
    shortcut_path = desktop / "3D Security Lab.command"

    content = f"""#!/bin/bash
cd "{PROJECT_ROOT}"
python3 scripts/setup_environment.py
read -p "Press Enter to close..."
"""
    shortcut_path.write_text(content, encoding="utf-8")
    os.chmod(shortcut_path, 0o755)
    print(f"macOSショートカット作成: {shortcut_path}")


def create_linux_shortcut() -> None:
    """Linux 用 .desktop ファイルを作成する。"""
    desktop = Path.home() / "Desktop"
    desktop.mkdir(exist_ok=True)
    shortcut_path = desktop / "3d-security-lab.desktop"

    python_path = sys.executable
    content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name=3D Security Lab
Comment=セキュリティ教育用3Dモデル解析キット
Exec=bash -c "cd '{PROJECT_ROOT}' && {python_path} scripts/setup_environment.py; read"
Terminal=true
Categories=Education;Security;
"""
    shortcut_path.write_text(content, encoding="utf-8")
    os.chmod(shortcut_path, 0o755)
    print(f"Linuxショートカット作成: {shortcut_path}")


def main() -> None:
    """プラットフォームに応じたショートカットを作成する。"""
    system = platform.system()
    print(f"プラットフォーム: {system}")
    print(f"プロジェクトルート: {PROJECT_ROOT}")

    if system == "Windows":
        create_windows_shortcut()
    elif system == "Darwin":
        create_macos_shortcut()
    elif system == "Linux":
        create_linux_shortcut()
    else:
        print(f"[警告] 未サポートのプラットフォーム: {system}")
        print("手動でショートカットを作成してください")


if __name__ == "__main__":
    main()
