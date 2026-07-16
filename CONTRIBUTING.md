# Contribuir a PDF Slim Studio

Gracias por ayudar a mejorar el proyecto. Buscamos cambios pequeños, verificables y fáciles de revisar.

## Flujo de ramas

- `main`: versiones estables publicadas.
- `dev`: integración de la siguiente versión.
- `feature/<descripcion>`: nuevas funciones creadas desde `dev`.
- `fix/<descripcion>`: correcciones creadas desde `dev`.
- `release/<version>`: preparación opcional de una publicación.

Los cambios normales deben dirigirse a `dev`. La promoción de `dev` a `main` se realiza mediante un pull request de versión.

## Preparar el entorno

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install pytest
pytest -q
```

En Windows activa el entorno con `.venv\Scripts\activate`.

## Antes de enviar un cambio

1. Abre una incidencia para cambios grandes o modificaciones de los umbrales visuales.
2. Crea una rama desde `dev`.
3. Mantén cada commit enfocado en una sola intención.
4. Añade o actualiza pruebas cuando cambie el comportamiento.
5. Ejecuta `pytest -q`.
6. Confirma que ningún PDF privado, archivo generado o informe de validación esté incluido.
7. Abre un pull request hacia `dev` y explica el impacto visual y funcional.

## Criterios para optimización PDF

Una mejora de compresión debe conservar las validaciones existentes o justificar con evidencia cualquier cambio de umbral. Incluye, cuando sea posible:

- tipo de PDF utilizado en la prueba;
- tamaño antes y después;
- páginas comparadas;
- métricas SSIM, MAE y PSNR;
- funciones del documento verificadas;
- casos donde la optimización debe rechazarse.

No publiques documentos reales con datos personales. Utiliza archivos sintéticos o anonimizados.

## Pull requests

El pull request debe indicar qué cambia, por qué es necesario, cómo se probó y qué riesgos permanecen. Las ramas protegidas requieren revisión y pruebas satisfactorias antes de fusionar.
