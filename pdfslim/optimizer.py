from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Iterable

import fitz
import numpy as np
from PIL import Image
from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, DictionaryObject


ProgressCallback = Callable[[float, str], None]


@dataclass(frozen=True)
class CandidatePreset:
    name: str
    quality: int | None
    max_dpi: int | None


@dataclass
class VisualMetrics:
    minimum_ssim: float
    average_ssim: float
    maximum_mae: float
    minimum_psnr: float
    pages_compared: int


@dataclass
class DocumentSnapshot:
    pages: int
    page_geometry: list[tuple[float, float, int]]
    text_hashes: list[str]
    annotations: list[dict[str, int]]
    form_fields: list[str]
    outlines: int
    attachments: list[str]


@dataclass
class CandidateResult:
    preset: str
    path: str
    size_bytes: int
    reduction_percent: float
    structural_ok: bool
    visual_ok: bool
    visual: VisualMetrics | None
    reason: str


@dataclass
class OptimizationResult:
    input_path: str
    output_path: str
    original_bytes: int
    optimized_bytes: int
    reduction_percent: float
    selected_preset: str
    candidates: list[CandidateResult]
    report_path: str
    warning: str | None = None


PRESETS = {
    "conservador": [
        CandidatePreset("Estructural", None, None),
        CandidatePreset("JPEG Q50", 50, None),
        CandidatePreset("JPEG Q40", 40, None),
    ],
    "equilibrado": [
        CandidatePreset("Estructural", None, None),
        CandidatePreset("JPEG Q40", 40, None),
        CandidatePreset("JPEG Q30", 30, None),
        CandidatePreset("JPEG Q25", 25, None),
        CandidatePreset("JPEG Q22", 22, None),
    ],
    "maximo": [
        CandidatePreset("Estructural", None, None),
        CandidatePreset("JPEG Q50", 50, None),
        CandidatePreset("JPEG Q35", 35, None),
        CandidatePreset("JPEG Q25", 25, None),
        CandidatePreset("JPEG Q22", 22, None),
        CandidatePreset("JPEG Q20", 20, None),
        CandidatePreset("JPEG Q18", 18, None),
        CandidatePreset("JPEG Q16", 16, None),
        CandidatePreset("JPEG Q14", 14, None),
    ],
}


def _notify(callback: ProgressCallback | None, value: float, message: str) -> None:
    if callback:
        callback(max(0.0, min(1.0, value)), message)


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()


def _outline_count(items: Iterable[object]) -> int:
    count = 0
    for item in items:
        if isinstance(item, list):
            count += _outline_count(item)
        else:
            count += 1
    return count


def snapshot_document(path: Path) -> DocumentSnapshot:
    reader = PdfReader(str(path), strict=False)
    geometry: list[tuple[float, float, int]] = []
    text_hashes: list[str] = []
    annotations: list[dict[str, int]] = []

    for page in reader.pages:
        geometry.append(
            (
                round(float(page.mediabox.width), 2),
                round(float(page.mediabox.height), 2),
                int(page.get("/Rotate", 0) or 0),
            )
        )
        text_hashes.append(_hash_text(page.extract_text() or ""))
        counts: dict[str, int] = {}
        for annotation_ref in page.get("/Annots", ArrayObject()):
            try:
                annotation = annotation_ref.get_object()
                subtype = str(annotation.get("/Subtype", "/Unknown"))
                counts[subtype] = counts.get(subtype, 0) + 1
            except Exception:
                counts["/Unreadable"] = counts.get("/Unreadable", 0) + 1
        annotations.append(counts)

    try:
        fields = sorted((reader.get_fields() or {}).keys())
    except Exception:
        fields = []
    try:
        outlines = _outline_count(reader.outline)
    except Exception:
        outlines = 0
    try:
        attachments = sorted(reader.attachments.keys())
    except Exception:
        attachments = []

    return DocumentSnapshot(
        pages=len(reader.pages),
        page_geometry=geometry,
        text_hashes=text_hashes,
        annotations=annotations,
        form_fields=fields,
        outlines=outlines,
        attachments=attachments,
    )


def _has_sensitive_features(snapshot: DocumentSnapshot) -> bool:
    return bool(
        snapshot.form_fields
        or snapshot.attachments
        or snapshot.outlines
        or any(page_counts for page_counts in snapshot.annotations)
    )


def _target_size(image: Image.Image, page_width: float, page_height: float, max_dpi: int | None) -> tuple[int, int]:
    if max_dpi is None:
        return image.size
    max_width = max(1, round(page_width / 72.0 * max_dpi))
    max_height = max(1, round(page_height / 72.0 * max_dpi))
    ratio = min(1.0, max_width / image.width, max_height / image.height)
    return max(1, round(image.width * ratio)), max(1, round(image.height * ratio))


def _write_candidate(input_path: Path, output_path: Path, preset: CandidatePreset) -> None:
    writer = PdfWriter(clone_from=str(input_path))
    replaced: set[tuple[int, int]] = set()

    if preset.quality is not None:
        for page in writer.pages:
            for pdf_image in page.images:
                reference = pdf_image.indirect_reference
                if reference is None:
                    continue
                identity = (reference.idnum, reference.generation)
                if identity in replaced:
                    continue
                replaced.add(identity)

                image = pdf_image.image
                if image.width * image.height < 120_000:
                    continue
                if image.mode not in ("RGB", "L"):
                    image = image.convert("RGB")
                target = _target_size(
                    image,
                    float(page.mediabox.width),
                    float(page.mediabox.height),
                    preset.max_dpi,
                )
                if target != image.size:
                    image = image.resize(target, Image.Resampling.LANCZOS)
                pdf_image.replace(
                    image,
                    quality=preset.quality,
                    optimize=True,
                    progressive=True,
                    subsampling=1,
                )

    for page in writer.pages:
        try:
            page.compress_content_streams(level=9)
        except Exception:
            pass
    try:
        writer.compress_identical_objects(remove_identicals=True, remove_orphans=True)
    except Exception:
        pass
    with output_path.open("wb") as handle:
        writer.write(handle)


def _render_page(document: fitz.Document, page_number: int, dpi: int = 120) -> np.ndarray:
    page = document.load_page(page_number)
    pixmap = page.get_pixmap(dpi=dpi, colorspace=fitz.csRGB, alpha=False)
    return np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(pixmap.height, pixmap.width, 3)


def _page_metrics(original: np.ndarray, candidate: np.ndarray) -> tuple[float, float, float]:
    if original.shape != candidate.shape:
        return 0.0, 1.0, 0.0
    left = original.astype(np.float64)
    right = candidate.astype(np.float64)
    diff = left - right
    mae = float(np.mean(np.abs(diff)) / 255.0)
    mse = float(np.mean(diff * diff))
    psnr = 99.0 if mse == 0 else float(20 * math.log10(255.0 / math.sqrt(mse)))

    if left.ndim == 3:
        left = 0.2126 * left[:, :, 0] + 0.7152 * left[:, :, 1] + 0.0722 * left[:, :, 2]
        right = 0.2126 * right[:, :, 0] + 0.7152 * right[:, :, 1] + 0.0722 * right[:, :, 2]

    # Local SSIM over 8x8 blocks: sensitive to text edges while remaining fast.
    height = original.shape[0] - original.shape[0] % 8
    width = original.shape[1] - original.shape[1] % 8
    a = left[:height, :width].reshape(height // 8, 8, width // 8, 8).transpose(0, 2, 1, 3)
    b = right[:height, :width].reshape(height // 8, 8, width // 8, 8).transpose(0, 2, 1, 3)
    mu_a = a.mean(axis=(2, 3))
    mu_b = b.mean(axis=(2, 3))
    var_a = a.var(axis=(2, 3))
    var_b = b.var(axis=(2, 3))
    covariance = ((a - mu_a[..., None, None]) * (b - mu_b[..., None, None])).mean(axis=(2, 3))
    c1 = (0.01 * 255) ** 2
    c2 = (0.03 * 255) ** 2
    score = ((2 * mu_a * mu_b + c1) * (2 * covariance + c2)) / (
        (mu_a * mu_a + mu_b * mu_b + c1) * (var_a + var_b + c2)
    )
    return float(np.mean(score)), mae, psnr


def compare_visuals(original_path: Path, candidate_path: Path) -> VisualMetrics:
    original = fitz.open(original_path)
    candidate = fitz.open(candidate_path)
    if original.page_count != candidate.page_count:
        return VisualMetrics(0.0, 0.0, 1.0, 0.0, 0)
    scores: list[float] = []
    maes: list[float] = []
    psnrs: list[float] = []
    try:
        for page_number in range(original.page_count):
            score, mae, psnr = _page_metrics(
                _render_page(original, page_number),
                _render_page(candidate, page_number),
            )
            scores.append(score)
            maes.append(mae)
            psnrs.append(psnr)
    finally:
        original.close()
        candidate.close()
    return VisualMetrics(
        minimum_ssim=min(scores),
        average_ssim=sum(scores) / len(scores),
        maximum_mae=max(maes),
        minimum_psnr=min(psnrs),
        pages_compared=len(scores),
    )


def _visual_passes(metrics: VisualMetrics) -> bool:
    return (
        metrics.minimum_ssim >= 0.990
        and metrics.average_ssim >= 0.995
        and metrics.maximum_mae <= 0.008
        and metrics.minimum_psnr >= 36.0
    )


def _write_report(result: OptimizationResult) -> None:
    report = asdict(result)
    Path(result.report_path).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


def optimize_pdf(
    input_path: str | os.PathLike[str],
    output_path: str | os.PathLike[str],
    mode: str = "maximo",
    progress: ProgressCallback | None = None,
) -> OptimizationResult:
    source = Path(input_path).expanduser().resolve()
    destination = Path(output_path).expanduser().resolve()
    if not source.exists() or source.suffix.lower() != ".pdf":
        raise ValueError("Selecciona un archivo PDF válido.")
    if source == destination:
        raise ValueError("La salida debe ser diferente del archivo original.")
    if mode not in PRESETS:
        raise ValueError(f"Modo desconocido: {mode}")
    destination.parent.mkdir(parents=True, exist_ok=True)

    _notify(progress, 0.02, "Analizando estructura y funciones…")
    original_snapshot = snapshot_document(source)
    original_size = source.stat().st_size
    presets = PRESETS[mode]
    warning = None
    if _has_sensitive_features(original_snapshot):
        presets = [PRESETS[mode][0]]
        warning = (
            "El PDF contiene anotaciones, marcadores, adjuntos o formularios. "
            "Se aplicó únicamente optimización estructural para no arriesgar su funcionalidad."
        )

    results: list[CandidateResult] = []
    valid_paths: list[tuple[Path, CandidatePreset, int]] = []
    with tempfile.TemporaryDirectory(prefix="pdfslim-") as temp_dir:
        temp_root = Path(temp_dir)
        for index, preset in enumerate(presets):
            start = 0.05 + (index / max(1, len(presets))) * 0.88
            _notify(progress, start, f"Probando {preset.name}…")
            candidate_path = temp_root / f"candidate-{index}.pdf"
            try:
                _write_candidate(source, candidate_path, preset)
                candidate_snapshot = snapshot_document(candidate_path)
                structural_ok = candidate_snapshot == original_snapshot
                if not structural_ok:
                    metrics = None
                    visual_ok = False
                    reason = "Cambió la estructura funcional; candidato descartado."
                else:
                    metrics = compare_visuals(source, candidate_path)
                    visual_ok = _visual_passes(metrics)
                    reason = "Validación completa superada." if visual_ok else "Diferencia visual sobre el umbral seguro."
                size = candidate_path.stat().st_size
                reduction = (1 - size / original_size) * 100
                results.append(
                    CandidateResult(
                        preset=preset.name,
                        path=str(candidate_path),
                        size_bytes=size,
                        reduction_percent=reduction,
                        structural_ok=structural_ok,
                        visual_ok=visual_ok,
                        visual=metrics,
                        reason=reason,
                    )
                )
                if structural_ok and visual_ok and size < original_size:
                    valid_paths.append((candidate_path, preset, size))
            except Exception as exc:
                results.append(
                    CandidateResult(
                        preset=preset.name,
                        path=str(candidate_path),
                        size_bytes=0,
                        reduction_percent=0.0,
                        structural_ok=False,
                        visual_ok=False,
                        visual=None,
                        reason=f"No se pudo generar: {exc}",
                    )
                )

        if valid_paths:
            selected_path, selected_preset, selected_size = min(valid_paths, key=lambda item: item[2])
            shutil.copy2(selected_path, destination)
        else:
            selected_preset = CandidatePreset("Original sin cambios", None, None)
            selected_size = original_size
            shutil.copy2(source, destination)
            warning = warning or "No hubo una reducción segura; se conservó una copia idéntica del original."

    # Temporary paths are useful during processing only; avoid publishing stale locations.
    for candidate in results:
        candidate.path = ""
    report_path = destination.with_suffix(".validation.json")
    result = OptimizationResult(
        input_path=str(source),
        output_path=str(destination),
        original_bytes=original_size,
        optimized_bytes=selected_size,
        reduction_percent=(1 - selected_size / original_size) * 100,
        selected_preset=selected_preset.name,
        candidates=results,
        report_path=str(report_path),
        warning=warning,
    )
    _write_report(result)
    _notify(progress, 1.0, "Optimización y validación completadas")
    return result
