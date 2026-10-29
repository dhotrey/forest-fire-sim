#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"

powerpoint="${1:-/home/aryan/Downloads/COSC3500 - Milestone 2.pptx}"

# Extract the original screenshots before rendering the methodology scene.
.venv/bin/python - "$powerpoint" <<'PY'
import sys
from pathlib import Path
from zipfile import ZipFile

with ZipFile(sys.argv[1]) as archive:
    for source, name in (("image3.png", "node-info.png"), ("image4.png", "build-info.png")):
        Path("assets/intro", name).write_bytes(archive.read("ppt/media/" + source))
PY

for source in s7_avx.py s8_neighbours.py s9_fire_mask.py s10_rng_checks.py s11_pack_masks.py; do
    case "$source" in
        s7_avx.py) scene=S7AVX ;;
        s8_neighbours.py) scene=S8Neighbours ;;
        s9_fire_mask.py) scene=S9FireMask ;;
        s10_rng_checks.py) scene=S10RNGChecks ;;
        s11_pack_masks.py) scene=S11PackMasks ;;
    esac
    .venv/bin/manim render -r 1920,1080 --fps 30 "$source" "$scene"
done

.venv/bin/manim render -r 1920,1080 --fps 30 final_slides.py \
    S3Methodology S9RuleMasks S10Blending S11AVXResults S12OpenMP \
    S13Scaling S14Combined S15Reflection S16AIDisclosure S17Bibliography
.venv/bin/python port_intro.py "$powerpoint"
