"""
ctf/challenge04_shader_secrets/verify.py

Challenge 04 の自動採点スクリプト。
シェーダーuniformに埋め込まれた文字列がフラグ。
"""

from __future__ import annotations

import hashlib
import hmac
import sys

# フラグのSHA256ハッシュ（事前計算済み、平文は保存しない）
EXPECTED_HASH: str = "b7d57325643ce406314d023916575c9b90bfbd057611c86d62dde4df123ab036"


def verify(submission: str) -> bool:
    """提出フラグを検証する。"""
    submitted_hash = hashlib.sha256(submission.strip().encode()).hexdigest()
    return hmac.compare_digest(submitted_hash, EXPECTED_HASH)


def main() -> None:
    """CLIエントリポイント。"""
    if len(sys.argv) > 1:
        answer = sys.argv[1]
    else:
        answer = input("Flag: ")

    if verify(answer):
        print("Correct! Challenge 04 passed!")
        sys.exit(0)
    else:
        print("Incorrect. Try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()
