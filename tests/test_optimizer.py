from pathlib import Path

from PIL import Image
from pypdf import PdfReader, PdfWriter

from pdfslim.optimizer import _page_metrics, snapshot_document


def test_page_metrics_identical() -> None:
    import numpy as np

    page = np.full((80, 80), 240, dtype=np.uint8)
    ssim, mae, psnr = _page_metrics(page, page.copy())
    assert ssim == 1.0
    assert mae == 0.0
    assert psnr == 99.0


def test_snapshot_round_trip(tmp_path: Path) -> None:
    image_path = tmp_path / "page.png"
    Image.new("RGB", (300, 400), "white").save(image_path)
    source = tmp_path / "source.pdf"
    Image.open(image_path).save(source, "PDF", resolution=100)

    reader = PdfReader(source)
    writer = PdfWriter(clone_from=reader)
    copy = tmp_path / "copy.pdf"
    writer.write(copy)

    assert snapshot_document(source) == snapshot_document(copy)
