<p align="center">
  <img src="packaging/icon.svg" alt="PDF Slim Studio" width="132">
</p>

<h1 align="center">PDF Slim Studio</h1>

<p align="center">
  Reduce el tamaño de documentos PDF localmente y conserva solo los resultados que superan validaciones estructurales y visuales.
</p>

<p align="center">
  <a href="https://github.com/anndreloopez012/pdf-slim-studio/actions/workflows/ci.yml"><img alt="Pruebas" src="https://github.com/anndreloopez012/pdf-slim-studio/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://github.com/anndreloopez012/pdf-slim-studio/releases/latest"><img alt="Última versión" src="https://img.shields.io/github/v/release/anndreloopez012/pdf-slim-studio?display_name=tag&sort=semver"></a>
  <a href="LICENSE"><img alt="Licencia MIT" src="https://img.shields.io/badge/licencia-MIT-156B51"></a>
  <img alt="Python 3.11+" src="https://img.shields.io/badge/Python-3.11%2B-E5763A">
</p>

## Descargar

No necesitas instalar Python ni herramientas de desarrollo.

| Sistema | Instalador recomendado | Alternativa portable |
|---|---|---|
| Windows 10/11 x64 | [Descargar instalador `.exe`](https://github.com/anndreloopez012/pdf-slim-studio/releases/download/v1.0.0/PDF-Slim-Studio-Setup-1.0.0-x64.exe) | [Descargar ZIP portable](https://github.com/anndreloopez012/pdf-slim-studio/releases/download/v1.0.0/PDF-Slim-Studio-Portable-1.0.0-x64.zip) |
| macOS 13+ · Apple Silicon | [Descargar instalador `.dmg`](https://github.com/anndreloopez012/pdf-slim-studio/releases/download/v1.0.0/PDF-Slim-Studio-1.0.0-Apple-Silicon.dmg) | [Descargar aplicación ZIP](https://github.com/anndreloopez012/pdf-slim-studio/releases/download/v1.0.0/PDF-Slim-Studio-1.0.0-Apple-Silicon.zip) |

También puedes consultar [todas las versiones publicadas](https://github.com/anndreloopez012/pdf-slim-studio/releases).

> Los instaladores comunitarios no están firmados con certificados comerciales. Windows SmartScreen o Gatekeeper pueden solicitar una confirmación adicional durante el primer inicio.

## Cómo funciona

```text
PDF original
    │
    ├── análisis de páginas, texto y funciones
    ├── generación de variantes de compresión
    ├── validación estructural
    ├── comparación visual de todas las páginas
    └── selección del archivo aprobado más pequeño
```

La aplicación nunca sobrescribe el documento original. Cada resultado incluye un informe `*.validation.json` con el perfil elegido, las variantes evaluadas y sus métricas.

### Validaciones incluidas

- Número de páginas, geometría, rotación y orden.
- Texto extraíble por página.
- Anotaciones, formularios, marcadores y adjuntos.
- Comparación visual RGB de todas las páginas mediante SSIM, error absoluto y PSNR.
- Conservación automática del original cuando ninguna variante cumple los umbrales.
- Procesamiento completamente local: los documentos no se envían a servicios externos.

## Perfiles de optimización

| Perfil | Uso recomendado |
|---|---|
| Conservador | Documentos sensibles o cuando prima la cautela. |
| Equilibrado | Uso cotidiano con buena relación entre tiempo y reducción. |
| Máximo verificado | Prueba más variantes y elige la menor que supera la validación. |

La reducción depende del contenido. Los PDF escaneados suelen ofrecer más margen; un documento vectorial o previamente optimizado puede reducirse poco o conservarse sin cambios.

## Ejecutar desde el código fuente

```bash
git clone https://github.com/anndreloopez012/pdf-slim-studio.git
cd pdf-slim-studio
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
python app.py
```

También puedes usar la terminal:

```bash
python cli.py entrada.pdf salida.pdf --mode maximo
```

## Construir instaladores

### Windows

Con Python 3.12 e Inno Setup instalados:

```powershell
.\packaging\windows\build_windows.ps1
```

Como alternativa reproducible desde macOS o Linux:

```bash
docker compose -f docker-compose.windows.yml build
docker compose -f docker-compose.windows.yml run --rm windows-builder
```

### macOS Apple Silicon

```bash
./run.command
./packaging/build_macos.sh
```

Los resultados quedan en `dist/windows/`, `dist/windows-docker/` o `dist/macos/` según el método utilizado.

## Contribuir

Las mejoras son bienvenidas, especialmente nuevos métodos de optimización, validaciones más precisas, soporte para más tipos de PDF y mejoras de accesibilidad.

Consulta [CONTRIBUTING.md](CONTRIBUTING.md) antes de abrir un pull request. El flujo del proyecto es:

```text
feature/* → dev → main → release
```

`main` y `dev` están protegidas; todos los cambios deben pasar por pull request y pruebas automatizadas.

## Seguridad y privacidad

No adjuntes documentos privados, contratos, firmas ni datos personales a incidencias públicas. Para reportar una vulnerabilidad consulta [SECURITY.md](SECURITY.md).

## Licencia

Distribuido bajo la [licencia MIT](LICENSE).
