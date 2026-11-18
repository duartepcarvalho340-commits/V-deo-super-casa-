#!/usr/bin/env bash
# Panic & Profit Reel pipeline setup (English only). Usage: bash setup.sh <project_dir>
set -e
P=${1:-$PWD}; mkdir -p "$P"/{assets/fonts,assets/voice,code,audio/stems,exports,previews}; P=$(cd "$P" && pwd)
(apt-get install -y -q libegl1 libgl1 >/dev/null 2>&1 || (apt-get update -q >/dev/null && apt-get install -y -q libegl1 libgl1 >/dev/null)) || true
pip install -q skia-python kokoro-onnx soundfile scipy opencv-python-headless fonttools brotli 2>&1 | grep -v WARNING || true
# English voice: Kokoro v1.0 (Apache-2.0, commercial use OK). Voices shared across projects in ~/.cache.
V=$HOME/.cache/pp-voice; mkdir -p "$V"
for f in kokoro-v1.0.onnx voices-v1.0.bin; do
  [ -s "$V/$f" ] || curl -sSL -o "$V/$f" "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/$f"
  ln -sf "$V/$f" "$P/assets/voice/$f"
done
# Brand fonts: Inter (preinstalled) + Fraunces (SIL OFL) from npm @fontsource
cp /usr/share/fonts/opentype/inter/{Inter-Regular,Inter-Medium,Inter-SemiBold,Inter-Bold}.otf "$P/assets/fonts/" 2>/dev/null || true
( cd /tmp && rm -rf package && npm pack @fontsource/fraunces@5.1.0 >/dev/null 2>&1 && tar xzf fontsource-fraunces-5.1.0.tgz && python3 - "$P" <<'PY'
import sys
from fontTools.ttLib import TTFont
for w in (300, 500, 700, 800):
    for st in ("normal", "italic"):
        try:
            f = TTFont(f"package/files/fraunces-latin-{w}-{st}.woff"); f.flavor = None
            f.save(f"{sys.argv[1]}/assets/fonts/Fraunces-{w}{'-Italic' if st=='italic' else ''}.ttf")
        except Exception as e: print("skip", w, st, e)
PY
) || true
ls "$P/assets/fonts"; echo "setup ok -> $P"
