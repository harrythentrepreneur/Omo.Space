# phonics_maker/audio_generation/qr_generator.py
"""
QR code generator for book audio listen pages.

Generates a clean QR code image that can be embedded in the
back cover of the PDF, linking to /listen/{bookId}.
"""

import io
from pathlib import Path
from typing import Optional

try:
    import qrcode
    from qrcode.image.styledpil import StyledPilImage
    from qrcode.image.styles.moduledrawers import RoundedModuleDrawer
    from qrcode.image.styles.colormasks import SolidFillColorMask
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False

from app.core.config.logger import logger


def generate_listen_qr(
    url: str,
    output_path: str,
    size: int = 300,
    fill_color: str = "#1a1a2e",
    back_color: str = "#ffffff",
) -> str:
    """
    Generate a QR code pointing to the audio listen page.
    
    Args:
        url: The full URL (e.g. https://phonicsmaker.com/listen/abc123)
        output_path: Where to save the QR code PNG
        size: Size in pixels (width and height)
        fill_color: Color of the QR modules
        back_color: Background color
        
    Returns:
        Path to the generated QR code image
    """
    if not HAS_QRCODE:
        logger.warning("qrcode package not installed. Generating fallback QR placeholder.")
        return _generate_fallback_qr(output_path, size)
    
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        
        # Try styled QR with rounded modules (more modern look)
        try:
            img = qr.make_image(
                image_factory=StyledPilImage,
                module_drawer=RoundedModuleDrawer(),
                color_mask=SolidFillColorMask(
                    back_color=(255, 255, 255),
                    front_color=_hex_to_rgb(fill_color),
                ),
            )
        except Exception:
            # Fallback to basic QR code
            img = qr.make_image(fill_color=fill_color, back_color=back_color)
        
        # Resize to target size
        img = img.resize((size, size))
        
        # Save
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path, format="PNG")
        
        logger.info(f"QR code generated: {output_path} ({size}x{size}px)")
        return output_path
        
    except Exception as e:
        logger.error(f"QR generation failed: {e}")
        return _generate_fallback_qr(output_path, size)


def _generate_fallback_qr(output_path: str, size: int = 300) -> str:
    """
    Generate a simple placeholder image if qrcode package is not available.
    Uses a basic PIL image with text.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        img = Image.new("RGB", (size, size), "#ffffff")
        draw = ImageDraw.Draw(img)
        
        # Draw a border
        draw.rectangle(
            [(10, 10), (size - 10, size - 10)],
            outline="#1a1a2e",
            width=3,
        )
        
        # Draw placeholder text
        draw.text(
            (size // 2, size // 2),
            "📱 SCAN ME",
            fill="#1a1a2e",
            anchor="mm",
        )
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path, format="PNG")
        return output_path
        
    except ImportError:
        # If even PIL isn't available, create a minimal 1x1 PNG
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        # Minimal valid PNG (1x1 white pixel)
        minimal_png = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00'
            b'\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00'
            b'\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        with open(output_path, "wb") as f:
            f.write(minimal_png)
        return output_path


def _hex_to_rgb(hex_color: str) -> tuple:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
