from __future__ import annotations

from io import BytesIO

import qrcode
from qrcode.image.pil import PilImage


def generate_qr_png(data: str) -> BytesIO:
    """Generate a QR code PNG image from a string. Returns BytesIO positioned at start."""
    img: PilImage = qrcode.make(data, image_factory=PilImage)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf
