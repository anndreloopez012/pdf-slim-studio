$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Venv = Join-Path $ProjectRoot ".venv-windows-build"
$Python = Join-Path $Venv "Scripts\python.exe"
$BuildRoot = Join-Path $ProjectRoot "build\windows"
$DistRoot = Join-Path $ProjectRoot "dist\windows"
$PortableRoot = Join-Path $DistRoot "portable"
$Icon = Join-Path $BuildRoot "AppIcon.ico"
$AppDir = Join-Path $PortableRoot "PDF Slim Studio"
$AppExe = Join-Path $AppDir "PDF Slim Studio.exe"
$Version = "1.0.0"

Write-Host "== PDF Slim Studio: compilación Windows ==" -ForegroundColor Green

if (-not (Get-Command py -ErrorAction SilentlyContinue) -and -not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Instala Python 3.11 o 3.12 de 64 bits antes de continuar."
}

if (-not (Test-Path $Python)) {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3.12 -m venv $Venv
        if ($LASTEXITCODE -ne 0) { & py -3 -m venv $Venv }
    } else {
        & python -m venv $Venv
    }
}

& $Python -m pip install --upgrade pip
& $Python -m pip install -r (Join-Path $ProjectRoot "requirements.txt") "pyinstaller>=6.18,<7" "pytest>=8,<10"

& $Python -m pytest -q (Join-Path $ProjectRoot "tests")
if ($LASTEXITCODE -ne 0) { throw "Las pruebas fallaron." }

if (Test-Path $BuildRoot) { Remove-Item $BuildRoot -Recurse -Force }
if (Test-Path $DistRoot) { Remove-Item $DistRoot -Recurse -Force }
New-Item -ItemType Directory -Force -Path $BuildRoot, $PortableRoot | Out-Null

$env:QT_QPA_PLATFORM = "offscreen"
& $Python (Join-Path $PSScriptRoot "render_icon.py") (Join-Path $ProjectRoot "packaging\icon.svg") $Icon
Remove-Item Env:QT_QPA_PLATFORM

Push-Location $ProjectRoot
try {
    & $Python -m PyInstaller `
        --noconfirm `
        --clean `
        --windowed `
        --name "PDF Slim Studio" `
        --icon $Icon `
        --exclude-module tkinter `
        --exclude-module pytest `
        --distpath $PortableRoot `
        --workpath (Join-Path $BuildRoot "work") `
        --specpath (Join-Path $BuildRoot "spec") `
        (Join-Path $ProjectRoot "app.py")
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller no pudo crear la aplicación." }
} finally {
    Pop-Location
}

$env:QT_QPA_PLATFORM = "offscreen"
$smoke = Start-Process -FilePath $AppExe -ArgumentList "--smoke-test" -Wait -PassThru
Remove-Item Env:QT_QPA_PLATFORM
if ($smoke.ExitCode -ne 0) { throw "La aplicación empaquetada no superó la prueba de arranque." }

$IsccCandidates = @(
    "${env:ProgramFiles(x86)}\Inno Setup 7\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 7\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
)
$Iscc = $IsccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $Iscc) {
    throw "Falta Inno Setup. Instálalo con: winget install JRSoftware.InnoSetup"
}

$Iss = Join-Path $PSScriptRoot "installer.iss"
& $Iscc "/DAppSource=$AppDir" "/DOutputDir=$DistRoot" "/DSetupIcon=$Icon" $Iss
if ($LASTEXITCODE -ne 0) { throw "Inno Setup no pudo crear el instalador." }

$PortableZip = Join-Path $DistRoot "PDF-Slim-Studio-Portable-$Version-x64.zip"
Compress-Archive -Path $AppDir -DestinationPath $PortableZip -CompressionLevel Optimal

$Setup = Join-Path $DistRoot "PDF-Slim-Studio-Setup-$Version-x64.exe"
$Hashes = @(
    (Get-FileHash $Setup -Algorithm SHA256),
    (Get-FileHash $PortableZip -Algorithm SHA256)
)
$Hashes | ForEach-Object { "$($_.Hash.ToLower())  $([IO.Path]::GetFileName($_.Path))" } |
    Set-Content -Encoding ASCII (Join-Path $DistRoot "SHA256SUMS.txt")

Write-Host ""
Write-Host "Instalador creado: $Setup" -ForegroundColor Green
Write-Host "Portable creado:  $PortableZip" -ForegroundColor Green
