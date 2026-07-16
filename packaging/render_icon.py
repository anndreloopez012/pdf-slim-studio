from pathlib import Path
import sys

from PySide6.QtCore import QByteArray, QSize
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("Uso: render_icon.py entrada.svg salida.png")
    source = Path(sys.argv[1])
    destination = Path(sys.argv[2])
    renderer = QSvgRenderer(QByteArray(source.read_bytes()))
    if not renderer.isValid():
        raise SystemExit(f"SVG inválido: {source}")
    image = QImage(QSize(1024, 1024), QImage.Format.Format_ARGB32)
    image.fill(0)
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not image.save(str(destination), "PNG"):
        raise SystemExit(f"No se pudo guardar {destination}")


if __name__ == "__main__":
    main()
