"""Reduce the ABAv3 coarse parcellation to a small array the app can load instantly.

Run once. The source atlas is 456x512x320 float32 at 25um - 308 MB in memory, which is
far more than a region-coloured map needs. Halving each axis and storing the labels as
uint8 gives ~264 KB while preserving every region's volume.

    pixi run python demo/prepare_atlas.py
"""

import gzip
import struct
from pathlib import Path

import numpy as np

SOURCE_ATLAS = Path(
    "~/lightsheet/mouse_app_lecanemab_ki3_aggregated/derivatives/spimquant-v0.9.0/"
    "tpl-ABAv3/tpl-ABAv3_seg-coarse_dseg.nii.gz"
).expanduser()
OUTPUT_ATLAS = Path(__file__).parent / "atlas_coarse_half.npz"

NIFTI_DTYPES = {2: "u1", 4: "<i2", 8: "<i4", 16: "<f4", 64: "<f8", 512: "<u2", 768: "<u4"}


def read_nifti(path):
    with gzip.open(path, "rb") as handle:
        raw = handle.read()
    header = raw[:348]
    dim = struct.unpack("<8h", header[40:56])
    datatype = struct.unpack("<h", header[70:72])[0]
    voxel_offset = int(struct.unpack("<f", header[108:112])[0])
    shape = tuple(dim[1 : 1 + dim[0]])
    values = np.frombuffer(
        raw[voxel_offset:], dtype=np.dtype(NIFTI_DTYPES[datatype]), count=int(np.prod(shape))
    )
    return values.reshape(shape, order="F")


if __name__ == "__main__":
    labels = read_nifti(SOURCE_ATLAS)
    reduced = np.ascontiguousarray(labels[::2, ::2, ::2].astype(np.uint8))
    np.savez_compressed(OUTPUT_ATLAS, labels=reduced)
    print(f"Read {SOURCE_ATLAS} {labels.shape} ({labels.nbytes / 1e6:.0f} MB in memory)")
    print(f"Wrote {OUTPUT_ATLAS} {reduced.shape} ({OUTPUT_ATLAS.stat().st_size / 1e3:.0f} KB)")
    print(f"Labels kept: {sorted(np.unique(reduced).tolist())}")
