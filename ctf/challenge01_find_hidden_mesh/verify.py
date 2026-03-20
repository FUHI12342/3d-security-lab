"""
ctf/challenge01_find_hidden_mesh/verify.py

Challenge 01 の自動採点スクリプト。
SHA256ハッシュ比較で正誤を検証する（平文フラグを直接比較しない）。
"""

from __future__ import annotations

import hashlib
import hmac
import sys

# フラグのSHA256ハッシュ（事前計算済み、平文は保存しない）
EXPECTED_HASH: str = "93a04fcd97041398282e0932974b839960c1353918cc94dd21de86ec6647b7cb"


def verify(submission: str) -> bool:
    """
    提出フラグをSHA256で検証する。

    Args:
        submission: ユーザーが提出したフラグ文字列

    Returns:
        正解なら True
    """
    submitted_hash = hashlib.sha256(submission.strip().encode()).hexdigest()
    return hmac.compare_digest(submitted_hash, EXPECTED_HASH)


def main() -> None:
    """CLIエントリポイント。"""
    if len(sys.argv) > 1:
        answer = sys.argv[1]
    else:
        answer = input("Flag: ")

    if verify(answer):
        print("Correct! Challenge 01 passed!")
        sys.exit(0)
    else:
        print("Incorrect. Try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()
