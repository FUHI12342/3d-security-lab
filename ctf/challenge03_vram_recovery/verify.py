"""
ctf/challenge03_vram_recovery/verify.py

Challenge 03 の自動採点スクリプト。
VRAMダンプから復元した画像内のテキストがフラグ。
"""

from __future__ import annotations

import hashlib
import hmac
import sys

# フラグのSHA256ハッシュ（事前計算済み、平文は保存しない）
EXPECTED_HASH: str = "5d3c3226e231401b0eefd2dc67a024d1cdeec4a711dcb2c475b8547de475a5dc"


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
        print("Correct! Challenge 03 passed!")
        sys.exit(0)
    else:
        print("Incorrect. Try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()
