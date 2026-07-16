from __future__ import annotations

import argparse
from pathlib import Path

from pdfslim.optimizer import optimize_pdf


def main() -> None:
    parser = argparse.ArgumentParser(description="Optimiza y valida un PDF localmente.")
    parser.add_argument("input", help="PDF de entrada")
    parser.add_argument("output", nargs="?", help="PDF de salida")
    parser.add_argument("--mode", choices=("conservador", "equilibrado", "maximo"), default="maximo")
    args = parser.parse_args()
    source = Path(args.input)
    output = Path(args.output) if args.output else source.with_name(f"{source.stem} - optimizado.pdf")

    result = optimize_pdf(
        source,
        output,
        mode=args.mode,
        progress=lambda value, text: print(f"[{value * 100:5.1f}%] {text}"),
    )
    print(f"\nResultado: {result.output_path}")
    print(f"Reducción: {result.reduction_percent:.1f}%")
    print(f"Perfil: {result.selected_preset}")
    print(f"Informe: {result.report_path}")
    if result.warning:
        print(f"Aviso: {result.warning}")


if __name__ == "__main__":
    main()

