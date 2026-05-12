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
W_HEADER_BYTES = 16       # leet v1 format: b"LEET" + version + reserved + rows + cols
W_DEFAULT_DATA_BYTES = 16384  # 128 * 32 * 4 — varies with embedding_dim


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
    if src_size < W_HEADER_BYTES:
        print(
            f"ERROR: {src} is {src_size} bytes — too small to be a valid W.bin",
            file=sys.stderr,
        )
        sys.exit(1)
    # Validate magic bytes
    with open(src, "rb") as f:
        magic = f.read(4)
    if magic != b"LEET":
        print(
            f"ERROR: {src} has invalid magic bytes {magic!r} — run train_w.py to regenerate",
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

    if dst_size >= W_HEADER_BYTES and (dst_size - W_HEADER_BYTES) % (32 * 4) == 0:
        embedding_dim = (dst_size - W_HEADER_BYTES) // (32 * 4)
        print(f"  Validation:  OK — {dst_size} bytes (32×{embedding_dim} float32, format v1)")
    else:
        print(f"  Validation:  WARNING — unexpected size {dst_size}", file=sys.stderr)


if __name__ == "__main__":
    main()
