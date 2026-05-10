from __future__ import annotations
from pathlib import Path

def ocr_image(file_path: str) -> str:
    ext = Path(file_path).suffix.lower()
    if ext not in (".png", ".jpg", ".jpeg", ".bmp", ".webp"):
        raise ValueError(f"Unsupported image: {ext}")
    try:
        from paddleocr import PaddleOCR
        ocr = PaddleOCR(lang="ch", use_angle_cls=True, show_log=False)
        result = ocr.ocr(file_path)
        lines = []
        for page in result:
            if page:
                for line in page:
                    if line and len(line) > 1:
                        text = line[1][0] if isinstance(line[1], (list,tuple)) else str(line[1])
                        if text.strip():
                            lines.append(text.strip())
        return chr(10).join(lines) if lines else "(no text detected)"
    except ImportError:
        raise ImportError("Install paddleocr: pip install paddleocr")
