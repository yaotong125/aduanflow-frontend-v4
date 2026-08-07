import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger("aduanflow")


def _find_tesseract_cmd() -> str:
    """Locate the Tesseract OCR engine binary across common install paths."""
    env_cmd = os.getenv("TESSERACT_CMD")
    if env_cmd and os.path.exists(env_cmd):
        return env_cmd
    candidates = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Tesseract-OCR", "tesseract.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Tesseract-OCR", "tesseract.exe"),
        "/usr/bin/tesseract",
        "/usr/local/bin/tesseract",
    ]
    for p in candidates:
        if p and os.path.exists(p):
            return p
    return ""


def _pil_from_pixmap(pix):
    from PIL import Image
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def _render_page_to_png(page) -> bytes:
    """Render a PyMuPDF page to a PNG in memory (300 DPI) for OCR engines."""
    import io
    pix = page.get_pixmap(dpi=300)
    img = _pil_from_pixmap(pix)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _ocr_rapid(doc) -> str:
    """OCR using RapidOCR (pure Python, ONNX CPU). No system binary required."""
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError:
        return ""
    try:
        engine = RapidOCR()
    except Exception as exc:
        logger.warning(f"[PdfExtractor] RapidOCR init failed: {exc}")
        return ""
    pages = []
    for page_idx in range(len(doc)):
        page = doc.load_page(page_idx)
        png_bytes = _render_page_to_png(page)
        result, _ = engine(png_bytes)
        if result:
            pages.append("\n".join(line[1] for line in result))
    return "\n".join(p for p in pages if p).strip()


def _ocr_tesseract(doc) -> str:
    """OCR using system Tesseract via pytesseract (fast, small) if binary exists."""
    try:
        import pytesseract
    except ImportError:
        return ""
    tesseract_cmd = _find_tesseract_cmd()
    if not tesseract_cmd:
        return ""
    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    pages = []
    for page_idx in range(len(doc)):
        pix = doc.load_page(page_idx).get_pixmap(dpi=300)
        img = _pil_from_pixmap(pix)
        pages.append(pytesseract.image_to_string(img))
    return "\n".join(p for p in pages if p).strip()


def _ocr_pdf_via_image(doc) -> str:
    """OCR fallback for scanned PDFs (no text layer).

    Prefers RapidOCR (pure Python / ONNX, deployable without system deps);
    falls back to system Tesseract if available. Returns '' if neither exists
    so the pipeline never hard-crashes on a scanned/unsupported file.
    """
    text = _ocr_rapid(doc)
    if text:
        return text
    text = _ocr_tesseract(doc)
    if text:
        return text
    logger.warning("[PdfExtractor] No usable OCR engine. Standard PDFs processed; scanned pages returned empty.")
    return ""


def pdf_text_from_bytes(pdf_bytes: bytes) -> str:
    """
    Extract text from a PDF document using PyMuPDF.
    Falls back to Tesseract OCR for scanned/image-based PDFs.
    Exposed as a tool that the LLM agent may call (the 'PDF/OCR' Pdf skill).
    """
    if not pdf_bytes:
        return ""
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        logger.error(f"[PdfExtractor] PyMuPDF not available: {exc}")
        return ""

    tmp_path = None
    try:
        # Write to a temp file so PyMuPDF can open it reliably
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name

        doc = fitz.open(tmp_path)
        pages_text = []
        for page_idx in range(len(doc)):
            page = doc.load_page(page_idx)
            pages_text.append(page.get_text("text"))
        text = "\n".join(pages_text).strip()
        if not text:
            logger.info("[PdfExtractor] No text layer; applying OCR (RapidOCR/Tesseract) for scanned PDF.")
            text = _ocr_pdf_via_image(doc)
        doc.close()
        return text
    except Exception as exc:
        logger.warning(f"[PdfExtractor] Failed to parse PDF: {exc}")
        return ""
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass