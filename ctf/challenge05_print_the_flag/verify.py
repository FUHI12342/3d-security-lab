"""
ctf/challenge05_print_the_flag/verify.py

Challenge 05 の自動採点スクリプト。
3Dテキストモデルをデコードして文字列を読み取ることで得られるフラグを検証する。
"""

from __future__ import annotations

import hashlib
import hmac
import sys

# フラグのSHA256ハッシュ（事前計算済み、平文は保存しない）
EXPECTED_HASH: str = "0f6da03a6dbbcb0b665e4b61bdd952afa7971aac778b4aa7ebb833d749a603cb"


def verify(submission: str) -> bool:
    """提出フラグを検証する（タイミング安全な比較）。"""
    submitted_hash = hashlib.sha256(submission.strip().encode()).hexdigest()
    return hmac.compare_digest(submitted_hash, EXPECTED_HASH)


def main() -> None:
    """CLIエントリポイント。"""
    if len(sys.argv) > 1:
        answer = sys.argv[1]
    else:
        answer = input("Flag: ")

    if verify(answer):
        print("Correct! Challenge 05 passed!")
        sys.exit(0)
    else:
        print("Incorrect. Try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()
