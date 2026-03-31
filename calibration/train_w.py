"""
Step 2: Train W matrix (128 → 32) using Ridge regression.
Input:  data/dataset.jsonl
Output: data/W.npy  (numpy, shape [128, 32])
        data/W.bin  (raw float32 binary, 128*32*4 = 16384 bytes)

Usage:
    python train_w.py
"""

import json
import os
import struct
import sys

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error


DATASET_PATH = "data/dataset.jsonl"
W_NPY_PATH = "data/W.npy"
W_BIN_PATH = "data/W.bin"


def load_dataset(path: str):
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"  WARNING: skipping malformed line {i+1}: {e}", file=sys.stderr)
    return records


def main():
    if not os.path.exists(DATASET_PATH):
        print(f"ERROR: {DATASET_PATH} not found. Run generate_dataset.py first.", file=sys.stderr)
        sys.exit(1)

    records = load_dataset(DATASET_PATH)
    N = len(records)
    print(f"Dataset size: {N} records")

    if N < 5:
        print("ERROR: dataset too small (< 5 records)", file=sys.stderr)
        sys.exit(1)

    X = np.array([r["emb"] for r in records], dtype=np.float64)   # [N, 128]
    Y = np.array([r["sem"] for r in records], dtype=np.float64)   # [N, 32]
    U = np.array([r["unc"] for r in records], dtype=np.float64)   # [N, 32]

    assert X.shape == (N, 128), f"Expected X shape ({N}, 128), got {X.shape}"
    assert Y.shape == (N, 32),  f"Expected Y shape ({N}, 32), got {Y.shape}"
    assert U.shape == (N, 32),  f"Expected U shape ({N}, 32), got {U.shape}"

    # Train/val split
    X_train, X_val, Y_train, Y_val, U_train, U_val = train_test_split(
        X, Y, U, test_size=0.2, random_state=42
    )
    n_train = len(X_train)
    n_val = len(X_val)
    print(f"Train: {n_train} | Val: {n_val}")

    # Fit one Ridge per axis using per-sample weights derived from unc
    # sample_weight[i] = 1 - unc[i, axis] (lower uncertainty → higher weight)
    W = np.zeros((128, 32), dtype=np.float64)
    val_preds = np.zeros((n_val, 32), dtype=np.float64)

    print("Training Ridge(alpha=0.01) per axis...")
    for axis in range(32):
        sw = 1.0 - U_train[:, axis]
        sw = np.clip(sw, 0.0, 1.0)
        # Avoid all-zero weights
        if sw.sum() < 1e-9:
            sw = np.ones(n_train)

        ridge = Ridge(alpha=0.01)
        ridge.fit(X_train, Y_train[:, axis], sample_weight=sw)
        W[:, axis] = ridge.coef_
        val_preds[:, axis] = ridge.predict(X_val)

    # Post-process: min-max normalization per column so output lands in [0, 1]
    # We find the theoretical min/max over all inputs in train+val combined
    all_raw = np.vstack([X_train @ W, X_val @ W])   # [N, 32]
    col_min = all_raw.min(axis=0)   # [32]
    col_max = all_raw.max(axis=0)   # [32]
    col_range = col_max - col_min
    col_range[col_range < 1e-9] = 1.0  # avoid division by zero

    # Transform W so that: output_norm = (X @ W - col_min) / col_range
    # Equivalent to: W_norm = W / col_range  (applied per column)
    # and a bias: -col_min / col_range. We embed the bias into W by augmenting X
    # with a ones column — but to keep W shape [128, 32] we absorb the bias
    # by adding a bias term encoded into row 0 of W via a constant trick.
    # Simpler: store (W, col_min, col_range) but spec says only W.npy + W.bin.
    # Therefore: we bake the normalization into W using a two-step adjustment.
    # We refit with normalized targets instead.

    # Better approach: normalize Y targets to [0,1] per column of Y (already [0,1])
    # and refit. Y is already [0,1] so normalization of W output post-hoc via
    # column-wise affine is the right approach. We save the raw W and rely on
    # clipping during inference (as specified: sem = (X @ W).clip(0, 1)).

    # For spec compliance (clip only), we scale W columns so typical output ≈ [0,1]
    scale = 1.0 / col_range  # [32]
    W_norm = W * scale[np.newaxis, :]  # broadcast over rows

    # Adjust val_preds with normalized W
    val_preds_norm = (X_val @ W_norm).clip(0.0, 1.0)

    # Compute MAE per axis
    mae_per_axis = mean_absolute_error(Y_val, val_preds_norm, multioutput="raw_values")
    print(f"\nValidation MAE per axis (clipped output):")

    axis_names = [
        "via", "correspondencia", "vibracao", "polaridade", "ritmo",
        "causa_efeito", "genero", "sistema", "estado", "processo",
        "relacao", "sinal", "estabilidade", "valencia_ont", "verificabilidade",
        "temporalidade", "completude", "causalidade", "reversibilidade", "carga",
        "origem", "valencia_epist", "urgencia", "impacto", "acao",
        "valor", "anomalia", "afeto", "dependencia", "vetor_temporal",
        "natureza", "valencia_acao",
    ]

    sorted_idx = np.argsort(mae_per_axis)
    best3 = sorted_idx[:3]
    worst3 = sorted_idx[-3:][::-1]

    print(f"  Mean MAE: {mae_per_axis.mean():.4f}")
    print(f"\n  Top 3 BEST axes (lowest MAE):")
    for idx in best3:
        print(f"    [{idx:2d}] {axis_names[idx]:<20s}  MAE={mae_per_axis[idx]:.4f}")
    print(f"\n  Top 3 WORST axes (highest MAE):")
    for idx in worst3:
        print(f"    [{idx:2d}] {axis_names[idx]:<20s}  MAE={mae_per_axis[idx]:.4f}")

    # Save W.npy
    W_out = W_norm.astype(np.float32)
    os.makedirs("data", exist_ok=True)
    np.save(W_NPY_PATH, W_out)
    npy_size = os.path.getsize(W_NPY_PATH)
    print(f"\nSaved {W_NPY_PATH}  ({npy_size} bytes, shape {W_out.shape})")

    # Save W.bin — raw float32 little-endian, exactly 128*32*4 = 16384 bytes
    W_flat = W_out.flatten(order="C")   # row-major, shape [4096]
    assert len(W_flat) == 128 * 32, f"Expected 4096 floats, got {len(W_flat)}"

    with open(W_BIN_PATH, "wb") as f:
        f.write(struct.pack(f"<{len(W_flat)}f", *W_flat))

    bin_size = os.path.getsize(W_BIN_PATH)
    assert bin_size == 16384, f"W.bin size {bin_size} != 16384"
    print(f"Saved {W_BIN_PATH}  ({bin_size} bytes)")
    print("\nDone.")


if __name__ == "__main__":
    main()
