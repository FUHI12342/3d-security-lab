"""
ctf/challenge02_decode_custom_format/verify.py

Challenge 02 の自動採点スクリプト。
mystery.s3d の最初の頂点X座標がフラグ。
"""

from __future__ import annotations

import hashlib
import hmac
import sys

# フラグのSHA256ハッシュ（事前計算済み、平文は保存しない）
EXPECTED_HASH: str = "2618d4acc143ad018b28ce216338ea466c269cca823a2459d974de540cd3571b"


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
        print("Correct! Challenge 02 passed!")
        sys.exit(0)
    else:
        print("Incorrect. Try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()
