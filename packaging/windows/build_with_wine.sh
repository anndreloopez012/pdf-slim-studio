#!/usr/bin/env bash
set -euo pipefail

WIN_PY='C:\Python312\python.exe'
ROOT='Z:\workspace'
DIST='/workspace/dist/windows-docker'
BUILD='/workspace/build/windows-docker'

rm -rf "$DIST" "$BUILD"
mkdir -p "$DIST" "$BUILD"

xvfb-run -a wine "$WIN_PY" -m pip install \
  -r "${ROOT}\\requirements.txt" "pyinstaller>=6.18,<7" "pytest>=8,<10"
xvfb-run -a wine "$WIN_PY" -m pytest -q "${ROOT}\\tests"
xvfb-run -a wine "$WIN_PY" "${ROOT}\\packaging\\windows\\render_icon.py" \
  "${ROOT}\\packaging\\icon.svg" "${ROOT}\\build\\windows-docker\\AppIcon.ico"
xvfb-run -a wine "$WIN_PY" -m PyInstaller \
  --noconfirm --clean --windowed \
  --name "PDF Slim Studio" \
  --icon "${ROOT}\\build\\windows-docker\\AppIcon.ico" \
  --exclude-module tkinter --exclude-module pytest \
  --distpath "${ROOT}\\dist\\windows-docker" \
  --workpath "${ROOT}\\build\\windows-docker\\work" \
  --specpath "${ROOT}\\build\\windows-docker\\spec" \
  "${ROOT}\\app.py"

QT_QPA_PLATFORM=offscreen xvfb-run -a wine \
  "${ROOT}\\dist\\windows-docker\\PDF Slim Studio\\PDF Slim Studio.exe" --smoke-test

ISCC='C:\Program Files (x86)\Inno Setup 6\ISCC.exe'
xvfb-run -a wine "$ISCC" \
  "/DAppSource=${ROOT}\\dist\\windows-docker\\PDF Slim Studio" \
  "/DOutputDir=${ROOT}\\dist\\windows-docker" \
  "/DSetupIcon=${ROOT}\\build\\windows-docker\\AppIcon.ico" \
  "${ROOT}\\packaging\\windows\\installer.iss"

cd "$DIST"
find "PDF Slim Studio" -name .DS_Store -delete
7z a -tzip "PDF-Slim-Studio-Portable-1.0.0-x64.zip" "PDF Slim Studio" >/dev/null
sha256sum "PDF-Slim-Studio-Setup-1.0.0-x64.exe" \
  "PDF Slim Studio/PDF Slim Studio.exe" \
  "PDF-Slim-Studio-Portable-1.0.0-x64.zip" > SHA256SUMS.txt

echo "Windows portable build created under dist/windows-docker/"
