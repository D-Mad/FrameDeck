#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
BUILD_ROOT="$ROOT/build-linux"
VENV="$BUILD_ROOT/venv"
APPDIR="$BUILD_ROOT/FrameDeck.AppDir"
TOOLS="$BUILD_ROOT/tools"
OUTPUT="$ROOT/dist/FrameDeck-Ubuntu-x86_64.AppImage"

python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/python" -m pip install -r "$ROOT/requirements-linux.txt"
"$VENV/bin/python" "$ROOT/scripts/fetch_aces12.py"
"$VENV/bin/python" -m PyInstaller --noconfirm --clean "$ROOT/framedeck-linux.spec"

rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/lib" "$TOOLS" "$ROOT/dist"
cp -a "$ROOT/dist/FrameDeck" "$APPDIR/usr/lib/framedeck"
cp "$ROOT/packaging/appimage/AppRun" "$APPDIR/AppRun"
cp "$ROOT/packaging/appimage/framedeck.desktop" "$APPDIR/framedeck.desktop"
cp "$ROOT/resources/icons/framedeck.png" "$APPDIR/framedeck.png"
chmod +x "$APPDIR/AppRun" "$APPDIR/usr/lib/framedeck/FrameDeck"

APPIMAGETOOL="$TOOLS/appimagetool-x86_64.AppImage"
if [[ ! -x "$APPIMAGETOOL" ]]; then
    curl -L --fail --retry 3 \
        -o "$APPIMAGETOOL" \
        https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
    chmod +x "$APPIMAGETOOL"
fi

rm -f "$OUTPUT"
ARCH=x86_64 "$APPIMAGETOOL" --appimage-extract-and-run "$APPDIR" "$OUTPUT"
chmod +x "$OUTPUT"
sha256sum "$OUTPUT" | tee "$OUTPUT.sha256"
echo "Built: $OUTPUT"
