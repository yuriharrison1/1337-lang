"""
Step 4: Export W.bin to service location.

Usage:
    python export_w.py [--dest ../leet-service/W.bin]
"""

import argparse
import os
import shutil
import sys
from datetime import datetime


W_BIN_SRC = "data/W.bin"
EXPECTED_BYTES = 16384  # 128 * 32 * 4


def main():
    parser = argparse.ArgumentParser(description="Export W.bin to service location.")
    parser.add_argument(
        "--dest",
        default="../leet-service/W.bin",
        help="Destination path for W.bin (default: ../leet-service/W.bin)",
    )
    args = parser.parse_args()

    src = W_BIN_SRC
    dst = args.dest

    # Validate source
    if not os.path.exists(src):
        print(f"ERROR: {src} not found. Run train_w.py first.", file=sys.stderr)
        sys.exit(1)

    src_size = os.path.getsize(src)
    if src_size != EXPECTED_BYTES:
        print(
            f"ERROR: {src} is {src_size} bytes, expected {EXPECTED_BYTES}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Ensure destination directory exists
    dst_dir = os.path.dirname(dst)
    if dst_dir:
        os.makedirs(dst_dir, exist_ok=True)

    shutil.copy2(src, dst)

    dst_size = os.path.getsize(dst)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"Export complete:")
    print(f"  Source:      {os.path.abspath(src)}")
    print(f"  Destination: {os.path.abspath(dst)}")
    print(f"  File size:   {dst_size} bytes ({dst_size // 1024} KB)")
    print(f"  Timestamp:   {timestamp}")

    if dst_size == EXPECTED_BYTES:
        print(f"  Validation:  OK — {EXPECTED_BYTES} bytes (128x32 float32)")
    else:
        print(f"  Validation:  WARNING — unexpected size {dst_size}", file=sys.stderr)


if __name__ == "__main__":
    main()
