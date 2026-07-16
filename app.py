from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from pdfslim.optimizer import OptimizationResult, optimize_pdf


def human_size(value: int) -> str:
    size = float(value)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


class OptimizationWorker(QThread):
    progress = Signal(float, str)
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, input_path: str, output_path: str, mode: str) -> None:
        super().__init__()
        self.input_path = input_path
        self.output_path = output_path
        self.mode = mode

    def run(self) -> None:
        try:
            result = optimize_pdf(
                self.input_path,
                self.output_path,
                mode=self.mode,
                progress=lambda value, text: self.progress.emit(value, text),
            )
            self.completed.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))


class Card(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("card")
        self.setFrameShape(QFrame.Shape.NoFrame)


class PdfSlimWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PDF Slim Studio")
        self.resize(960, 690)
        self.setMinimumSize(820, 620)
        self.input_path = ""
        self.output_path = ""
        self.result: OptimizationResult | None = None
        self.worker: OptimizationWorker | None = None
        self.mode_group = QButtonGroup(self)
        self._build_ui()

    def _label(self, text: str, css_class: str = "") -> QLabel:
        label = QLabel(text)
        if css_class:
            label.setProperty("class", css_class)
        label.setWordWrap(True)
        return label

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(46, 34, 46, 32)
        outer.setSpacing(0)

        outer.addWidget(self._label("COMPRESIÓN LOCAL · PRIVADA · VERIFICADA", "eyebrow"))
        outer.addWidget(self._label("PDF Slim Studio", "title"))
        subtitle = self._label(
            "Reduce documentos escaneados y conserva una copia validada del original.",
            "muted",
        )
        subtitle.setContentsMargins(0, 3, 0, 24)
        outer.addWidget(subtitle)

        columns = QHBoxLayout()
        columns.setSpacing(24)
        outer.addLayout(columns, 1)

        left = Card()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(26, 24, 26, 24)
        left_layout.setSpacing(10)
        columns.addWidget(left, 3)

        left_layout.addWidget(self._label("1  Documento", "section"))
        self.file_label = self._label("Ningún PDF seleccionado", "body")
        self.file_label.setMinimumHeight(46)
        left_layout.addWidget(self.file_label)
        choose_input = QPushButton("Elegir PDF")
        choose_input.setProperty("kind", "secondary")
        choose_input.setMinimumHeight(40)
        choose_input.clicked.connect(self._choose_input)
        left_layout.addWidget(choose_input, 0, Qt.AlignmentFlag.AlignLeft)
        left_layout.addWidget(self._divider())

        left_layout.addWidget(self._label("2  Intensidad", "section"))
        modes = [
            ("Conservador", "conservador", "Menos variantes, control estricto."),
            ("Equilibrado", "equilibrado", "Buena relación entre tiempo y reducción."),
            ("Máximo verificado", "maximo", "Agota variantes y elige la menor aprobada."),
        ]
        for title, value, description in modes:
            radio = QRadioButton(title)
            radio.setProperty("mode", value)
            self.mode_group.addButton(radio)
            left_layout.addWidget(radio)
            detail = self._label(description, "modeDetail")
            detail.setContentsMargins(25, -5, 0, 3)
            left_layout.addWidget(detail)
            if value == "maximo":
                radio.setChecked(True)

        left_layout.addWidget(self._divider())
        left_layout.addWidget(self._label("3  Guardar como", "section"))
        self.output_label = self._label("Se propondrá junto al original", "muted")
        left_layout.addWidget(self.output_label)
        choose_output = QPushButton("Cambiar destino")
        choose_output.setProperty("kind", "secondary")
        choose_output.setMinimumHeight(40)
        choose_output.clicked.connect(self._choose_output)
        left_layout.addWidget(choose_output, 0, Qt.AlignmentFlag.AlignLeft)
        left_layout.addStretch()

        right = Card()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(26, 24, 26, 24)
        right_layout.setSpacing(10)
        columns.addWidget(right, 2)

        right_layout.addWidget(self._label("RESULTADO", "overline"))
        self.metric_label = self._label("—", "metric")
        right_layout.addWidget(self.metric_label)
        self.summary = self._label("La reducción aparecerá aquí.", "body")
        right_layout.addWidget(self.summary)
        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        right_layout.addWidget(self.progress)
        self.status = self._label("Listo para analizar un documento", "muted")
        self.status.setMinimumHeight(52)
        right_layout.addWidget(self.status)
        right_layout.addSpacing(12)
        for text in (
            "✓ Páginas y geometría",
            "✓ Texto y anotaciones",
            "✓ Comparación RGB por página",
        ):
            right_layout.addWidget(self._label(text, "check"))
        right_layout.addStretch()
        self.open_button = QPushButton("Mostrar archivo")
        self.open_button.setProperty("kind", "secondary")
        self.open_button.setMinimumHeight(40)
        self.open_button.setEnabled(False)
        self.open_button.clicked.connect(self._show_output)
        right_layout.addWidget(self.open_button, 0, Qt.AlignmentFlag.AlignLeft)

        self.run_button = QPushButton("Optimizar y verificar")
        self.run_button.setProperty("kind", "primary")
        self.run_button.setMinimumHeight(48)
        self.run_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.run_button.clicked.connect(self._start)
        outer.addSpacing(24)
        outer.addWidget(self.run_button)

    def _divider(self) -> QFrame:
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setProperty("class", "divider")
        divider.setContentsMargins(0, 10, 0, 10)
        return divider

    def _selected_mode(self) -> str:
        checked = self.mode_group.checkedButton()
        return str(checked.property("mode")) if checked else "maximo"

    def _choose_input(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(self, "Elegir PDF", "", "Documentos PDF (*.pdf)")
        if not selected:
            return
        source = Path(selected)
        self.input_path = selected
        self.output_path = str(source.with_name(f"{source.stem} - optimizado.pdf"))
        self.file_label.setText(f"{source.name}\n{human_size(source.stat().st_size)}")
        self.output_label.setText(self.output_path)

    def _choose_output(self) -> None:
        initial = self.output_path or "documento-optimizado.pdf"
        selected, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar PDF optimizado",
            initial,
            "Documentos PDF (*.pdf)",
        )
        if selected:
            if not selected.lower().endswith(".pdf"):
                selected += ".pdf"
            self.output_path = selected
            self.output_label.setText(selected)

    def _start(self) -> None:
        if not self.input_path:
            QMessageBox.information(self, "Selecciona un PDF", "Primero elige el documento que deseas optimizar.")
            return
        if not self.output_path:
            self._choose_output()
            if not self.output_path:
                return
        self.result = None
        self.metric_label.setText("…")
        self.summary.setText("Generando y comparando variantes seguras.")
        self.status.setText("Preparando análisis…")
        self.progress.setValue(10)
        self.run_button.setEnabled(False)
        self.open_button.setEnabled(False)
        self.worker = OptimizationWorker(self.input_path, self.output_path, self._selected_mode())
        self.worker.progress.connect(self._on_progress)
        self.worker.completed.connect(self._display_result)
        self.worker.failed.connect(self._display_error)
        self.worker.start()

    def _on_progress(self, value: float, text: str) -> None:
        self.progress.setValue(round(value * 1000))
        self.status.setText(text)

    def _display_result(self, result: OptimizationResult) -> None:
        self.result = result
        self.progress.setValue(1000)
        self.metric_label.setText(f"−{result.reduction_percent:.1f}%")
        self.summary.setText(
            f"{human_size(result.original_bytes)} → {human_size(result.optimized_bytes)}\n"
            f"Perfil elegido: {result.selected_preset}"
        )
        self.status.setText(result.warning or "Aprobado: estructura y apariencia dentro del umbral seguro.")
        self.run_button.setEnabled(True)
        self.open_button.setEnabled(True)

    def _display_error(self, message: str) -> None:
        self.run_button.setEnabled(True)
        self.status.setText("No se pudo completar")
        QMessageBox.critical(self, "Error de optimización", message)

    def _show_output(self) -> None:
        if not self.result:
            return
        path = self.result.output_path
        if sys.platform == "darwin":
            subprocess.run(["open", "-R", path], check=False)
        elif os.name == "nt":
            os.startfile(path)  # type: ignore[attr-defined]
        else:
            subprocess.run(["xdg-open", str(Path(path).parent)], check=False)


STYLESHEET = """
QWidget#root { background: #F4F1EA; color: #17231F; }
QLabel { color: #17231F; font-size: 14px; }
QLabel[class="eyebrow"] { color: #156B51; font-size: 11px; font-weight: 700; letter-spacing: 1px; }
QLabel[class="title"] { font-size: 36px; font-weight: 750; }
QLabel[class="muted"], QLabel[class="modeDetail"] { color: #68736E; font-size: 13px; }
QLabel[class="section"] { font-size: 15px; font-weight: 700; }
QLabel[class="overline"] { color: #68736E; font-size: 11px; font-weight: 700; }
QLabel[class="metric"] { color: #156B51; font-size: 42px; font-weight: 800; }
QLabel[class="check"] { color: #156B51; font-size: 13px; font-weight: 600; }
QFrame#card { background: #FFFEFA; border: 1px solid #DFDED6; border-radius: 16px; }
QFrame[class="divider"] { color: #DFDED6; background: #DFDED6; max-height: 1px; }
QRadioButton { spacing: 9px; font-size: 14px; font-weight: 600; }
QRadioButton::indicator { width: 17px; height: 17px; }
QRadioButton::indicator:checked { background: #156B51; border: 4px solid #D9EADF; border-radius: 8px; }
QRadioButton::indicator:unchecked { background: #FFFEFA; border: 2px solid #9AA49F; border-radius: 8px; }
QPushButton { border: 0; border-radius: 9px; font-size: 14px; font-weight: 650; padding: 10px 17px; }
QPushButton[kind="secondary"] { background: #D9EADF; color: #17231F; }
QPushButton[kind="secondary"]:hover { background: #C7DFD0; }
QPushButton[kind="primary"] { background: #156B51; color: white; padding: 14px 22px; font-size: 15px; }
QPushButton[kind="primary"]:hover { background: #0F5943; }
QPushButton:disabled { background: #B8C5C0; color: #F1F4F2; }
QProgressBar { background: #E4E2DA; border: 0; border-radius: 4px; height: 8px; }
QProgressBar::chunk { background: #E5763A; border-radius: 4px; }
"""


def main() -> int:
    smoke_test = "--smoke-test" in sys.argv
    if smoke_test:
        sys.argv.remove("--smoke-test")
    app = QApplication(sys.argv)
    app.setApplicationName("PDF Slim Studio")
    app.setFont(QFont("Avenir Next", 12))
    app.setStyleSheet(STYLESHEET)
    window = PdfSlimWindow()
    if smoke_test:
        window.show()
        app.processEvents()
        if window.windowTitle() != "PDF Slim Studio":
            return 1
        window.close()
        return 0
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
