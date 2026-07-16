#!/bin/zsh
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="$PROJECT_ROOT/.venv/bin/python"
APP_NAME="PDF Slim Studio"
VERSION="1.0.0"
BUNDLE_ID="com.softplus.pdfslimstudio"
BUILD_ROOT="$PROJECT_ROOT/build/macos"
RELEASE_ROOT="$PROJECT_ROOT/dist/macos"
APP_PATH="$BUILD_ROOT/app/$APP_NAME.app"
DMG_PATH="$RELEASE_ROOT/PDF-Slim-Studio-$VERSION-Apple-Silicon.dmg"
ZIP_PATH="$RELEASE_ROOT/PDF-Slim-Studio-$VERSION-Apple-Silicon.zip"
ICON_WORK="$BUILD_ROOT/icon"
ICONSET="$ICON_WORK/AppIcon.iconset"
ICNS="$ICON_WORK/AppIcon.icns"

if [[ ! -x "$PYTHON" ]]; then
  echo "Falta .venv. Ejecuta primero ./run.command"
  exit 1
fi

"$PYTHON" -m pip install --quiet "pyinstaller>=6.18,<7"

rm -rf "$BUILD_ROOT" "$RELEASE_ROOT"
mkdir -p "$ICONSET" "$RELEASE_ROOT"

QT_QPA_PLATFORM=offscreen "$PYTHON" "$PROJECT_ROOT/packaging/render_icon.py" \
  "$PROJECT_ROOT/packaging/icon.svg" "$ICON_WORK/AppIcon-1024.png"

for size in 16 32 128 256 512; do
  /usr/bin/sips -z "$size" "$size" "$ICON_WORK/AppIcon-1024.png" \
    --out "$ICONSET/icon_${size}x${size}.png" >/dev/null
  double=$((size * 2))
  /usr/bin/sips -z "$double" "$double" "$ICON_WORK/AppIcon-1024.png" \
    --out "$ICONSET/icon_${size}x${size}@2x.png" >/dev/null
done
/usr/bin/iconutil -c icns "$ICONSET" -o "$ICNS"

cd "$PROJECT_ROOT"
"$PYTHON" -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name "$APP_NAME" \
  --icon "$ICNS" \
  --osx-bundle-identifier "$BUNDLE_ID" \
  --target-arch arm64 \
  --exclude-module tkinter \
  --exclude-module pytest \
  --distpath "$BUILD_ROOT/app" \
  --workpath "$BUILD_ROOT/work" \
  --specpath "$BUILD_ROOT/spec" \
  "$PROJECT_ROOT/app.py"

/usr/libexec/PlistBuddy -c "Add :CFBundleShortVersionString string $VERSION" "$APP_PATH/Contents/Info.plist" 2>/dev/null \
  || /usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString $VERSION" "$APP_PATH/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Add :CFBundleVersion string 1" "$APP_PATH/Contents/Info.plist" 2>/dev/null \
  || /usr/libexec/PlistBuddy -c "Set :CFBundleVersion 1" "$APP_PATH/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Add :LSMinimumSystemVersion string 13.0" "$APP_PATH/Contents/Info.plist" 2>/dev/null \
  || /usr/libexec/PlistBuddy -c "Set :LSMinimumSystemVersion 13.0" "$APP_PATH/Contents/Info.plist"

/usr/sbin/dot_clean -m "$APP_PATH"
/usr/bin/xattr -cr "$APP_PATH"
/usr/bin/codesign --force --deep --sign - "$APP_PATH"
/usr/bin/codesign --verify --deep --strict --verbose=2 "$APP_PATH"

QT_QPA_PLATFORM=offscreen "$APP_PATH/Contents/MacOS/$APP_NAME" --smoke-test

STAGING="$BUILD_ROOT/dmg-staging"
mkdir -p "$STAGING"
/usr/bin/ditto "$APP_PATH" "$STAGING/$APP_NAME.app"
ln -s /Applications "$STAGING/Applications"
/usr/bin/ditto "$PROJECT_ROOT/packaging/INSTRUCCIONES.txt" "$STAGING/LEEME - Instalación.txt"

/usr/bin/hdiutil create \
  -volname "$APP_NAME" \
  -srcfolder "$STAGING" \
  -ov \
  -format UDZO \
  "$DMG_PATH"

/usr/bin/ditto -c -k --sequesterRsrc --keepParent "$APP_PATH" "$ZIP_PATH"

cd "$RELEASE_ROOT"
/usr/bin/shasum -a 256 "$(basename "$DMG_PATH")" "$(basename "$ZIP_PATH")" > SHA256SUMS.txt

echo ""
echo "Instalador creado: $DMG_PATH"
echo "Aplicación creada: $APP_PATH"
echo "ZIP de respaldo: $ZIP_PATH"
