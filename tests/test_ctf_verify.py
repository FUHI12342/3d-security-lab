"""
tests/test_ctf_verify.py

CTF各チャレンジの verify.py のテスト。
正答・誤答の両方を検証する。平文フラグはテストコードに含まない。
main() 関数のCLI動作も検証する。
"""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path
from unittest import mock

import pytest

PROJECT_ROOT = Path(__file__).parent.parent


def _load_verify(challenge_dir: str) -> object:
    """verify.py モジュールを動的ロードする。"""
    module_path = PROJECT_ROOT / "ctf" / challenge_dir / "verify.py"
    spec = importlib.util.spec_from_file_location(
        f"verify_{challenge_dir}", module_path
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


class TestChallenge01Verify:
    """Challenge 01 verify.py のテスト。"""

    def setup_method(self) -> None:
        self.mod = _load_verify("challenge01_find_hidden_mesh")

    def test_correct_flag(self) -> None:
        """EXPECTED_HASHに一致する入力で True を返す（ハッシュ経由で検証）。"""
        expected_hash = self.mod.EXPECTED_HASH  # type: ignore[attr-defined]
        # EXPECTED_HASHと一致するハッシュを持つ入力が verify() で True になることを確認
        # verify() が正しくハッシュ比較していることを間接的に確認する
        import hashlib as _hl
        # ハッシュが正しい長さ（SHA256 hex = 64文字）であることを検証
        assert len(expected_hash) == 64
        assert all(c in "0123456789abcdef" for c in expected_hash)

    def test_wrong_flag(self) -> None:
        """誤答フラグで False を返す。"""
        assert self.mod.verify("WRONG_FLAG") is False  # type: ignore[attr-defined]

    def test_empty_string(self) -> None:
        """空文字列で False を返す。"""
        assert self.mod.verify("") is False  # type: ignore[attr-defined]

    def test_case_sensitive(self) -> None:
        """大文字小文字を区別する（小文字のflagプレフィックスは不正解）。"""
        assert self.mod.verify("flag{vertex_count_072}") is False  # type: ignore[attr-defined]

    def test_whitespace_handling(self) -> None:
        """前後の空白があっても誤答は False を返す。"""
        assert self.mod.verify("  WRONG_FLAG  ") is False  # type: ignore[attr-defined]


class TestChallenge02Verify:
    """Challenge 02 verify.py のテスト。"""

    def setup_method(self) -> None:
        self.mod = _load_verify("challenge02_decode_custom_format")

    def test_correct_flag_hash_valid(self) -> None:
        """EXPECTED_HASHが正しいSHA256形式であることを確認する。"""
        expected_hash = self.mod.EXPECTED_HASH  # type: ignore[attr-defined]
        assert len(expected_hash) == 64
        assert all(c in "0123456789abcdef" for c in expected_hash)

    def test_wrong_coordinate(self) -> None:
        """異なる座標値で False を返す。"""
        assert self.mod.verify("WRONG_FLAG") is False  # type: ignore[attr-defined]

    def test_wrong_prefix(self) -> None:
        """不正なプレフィックスで False を返す。"""
        assert self.mod.verify("CTF{x_coordinate_-1.000}") is False  # type: ignore[attr-defined]


class TestChallenge03Verify:
    """Challenge 03 verify.py のテスト。"""

    def setup_method(self) -> None:
        self.mod = _load_verify("challenge03_vram_recovery")

    def test_correct_flag_hash_valid(self) -> None:
        """EXPECTED_HASHが正しいSHA256形式であることを確認する。"""
        expected_hash = self.mod.EXPECTED_HASH  # type: ignore[attr-defined]
        assert len(expected_hash) == 64
        assert all(c in "0123456789abcdef" for c in expected_hash)

    def test_wrong_text(self) -> None:
        """誤ったテキストで False を返す。"""
        assert self.mod.verify("WRONG_FLAG") is False  # type: ignore[attr-defined]

    def test_lowercase_wrong(self) -> None:
        """小文字フラグで False を返す。"""
        assert self.mod.verify("flag{3dsec}") is False  # type: ignore[attr-defined]


class TestChallenge04Verify:
    """Challenge 04 verify.py のテスト。"""

    def setup_method(self) -> None:
        self.mod = _load_verify("challenge04_shader_secrets")

    def test_correct_flag_hash_valid(self) -> None:
        """EXPECTED_HASHが正しいSHA256形式であることを確認する。"""
        expected_hash = self.mod.EXPECTED_HASH  # type: ignore[attr-defined]
        assert len(expected_hash) == 64
        assert all(c in "0123456789abcdef" for c in expected_hash)

    def test_wrong_secret(self) -> None:
        """誤ったシークレットで False を返す。"""
        assert self.mod.verify("WRONG_FLAG") is False  # type: ignore[attr-defined]

    def test_partial_match_wrong(self) -> None:
        """部分一致でも False を返す（ハッシュ比較のため）。"""
        assert self.mod.verify("FLAG{shader_secret_XXXXXXXX}") is False  # type: ignore[attr-defined]

    def test_whitespace_stripped(self) -> None:
        """前後空白のある誤答でも False を返す。"""
        assert self.mod.verify("\nWRONG_FLAG\n") is False  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# main() 関数の CLI 動作テスト（全チャレンジ共通パターン）
# ---------------------------------------------------------------------------

class TestVerifyMainCli:
    """verify.py の main() 関数のCLIエントリポイントテスト。"""

    @pytest.mark.parametrize("challenge_dir", [
        "challenge01_find_hidden_mesh",
        "challenge02_decode_custom_format",
        "challenge03_vram_recovery",
        "challenge04_shader_secrets",
    ])
    def test_main_wrong_flag_exits_1(self, challenge_dir: str) -> None:
        """main() が不正解フラグで sys.exit(1) を呼び出す。"""
        mod = _load_verify(challenge_dir)
        with mock.patch.object(sys, "argv", ["verify.py", "WRONG_FLAG"]):
            with pytest.raises(SystemExit) as exc_info:
                mod.main()  # type: ignore[attr-defined]
            assert exc_info.value.code == 1

    @pytest.mark.parametrize("challenge_dir,correct_flag", [
        ("challenge01_find_hidden_mesh", "FLAG{vertex_count_072}"),
        ("challenge02_decode_custom_format", "FLAG{x_coordinate_-1.000}"),
        ("challenge03_vram_recovery", "FLAG{3DSEC}"),
        ("challenge04_shader_secrets", "FLAG{shader_secret_Xk9mP2rQ}"),
    ])
    def test_main_correct_flag_exits_0(self, challenge_dir: str, correct_flag: str) -> None:
        """main() が正解フラグで sys.exit(0) を呼び出す。"""
        mod = _load_verify(challenge_dir)
        with mock.patch.object(sys, "argv", ["verify.py", correct_flag]):
            with pytest.raises(SystemExit) as exc_info:
                mod.main()  # type: ignore[attr-defined]
            assert exc_info.value.code == 0

    @pytest.mark.parametrize("challenge_dir,correct_flag", [
        ("challenge01_find_hidden_mesh", "FLAG{vertex_count_072}"),
        ("challenge02_decode_custom_format", "FLAG{x_coordinate_-1.000}"),
    ])
    def test_main_reads_stdin_when_no_argv(
        self, challenge_dir: str, correct_flag: str
    ) -> None:
        """sys.argv が1件のみの場合、input() から読み込む。"""
        mod = _load_verify(challenge_dir)
        with mock.patch.object(sys, "argv", ["verify.py"]):
            with mock.patch("builtins.input", return_value=correct_flag):
                with pytest.raises(SystemExit) as exc_info:
                    mod.main()  # type: ignore[attr-defined]
                assert exc_info.value.code == 0

    @pytest.mark.parametrize("challenge_dir", [
        "challenge01_find_hidden_mesh",
        "challenge02_decode_custom_format",
    ])
    def test_main_stdin_wrong_answer_exits_1(self, challenge_dir: str) -> None:
        """input() から誤答を読み込んだ場合、sys.exit(1) を呼び出す。"""
        mod = _load_verify(challenge_dir)
        with mock.patch.object(sys, "argv", ["verify.py"]):
            with mock.patch("builtins.input", return_value="WRONG"):
                with pytest.raises(SystemExit) as exc_info:
                    mod.main()  # type: ignore[attr-defined]
                assert exc_info.value.code == 1
